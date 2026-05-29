import Config from './config.js';
import store from './store.js';

function createGuestUserId() {
    if (globalThis.crypto && typeof globalThis.crypto.randomUUID === 'function') {
        return globalThis.crypto.randomUUID();
    }

    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (char) => {
        const rand = Math.floor(Math.random() * 16);
        const value = char === 'x' ? rand : (rand & 0x3) | 0x8;
        return value.toString(16);
    });
}

class WebSocketClient {
    constructor() {
        this.ws = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 10;
        this.baseDelay = 1000;
        this.maxDelay = 30000;
        this.isConnecting = false;
        this.handlers = {};
        this.pendingMessages = [];
        
        // Register default message handlers
        this.registerDefaultHandlers();
    }

    connect() {
        if (this.isConnecting || (this.ws && this.ws.readyState === WebSocket.OPEN)) return;
        
        this.isConnecting = true;
        
        try {
            this.ws = new WebSocket(Config.WS_BASE_URL);
            
            this.ws.onopen = this.onOpen.bind(this);
            this.ws.onmessage = this.onMessage.bind(this);
            this.ws.onclose = this.onClose.bind(this);
            this.ws.onerror = this.onError.bind(this);
        } catch (error) {
            console.error('WebSocket connection error:', error);
            this.isConnecting = false;
            this.scheduleReconnect();
        }
    }

    onOpen() {
        console.log('WebSocket connected');
        this.isConnecting = false;
        this.reconnectAttempts = 0;
        
        // Re-join if we have user context
        const state = store.getState();
        const hasQueuedJoin = this.pendingMessages.some(message => message.type === 'join');
        if (state.user && !hasQueuedJoin) {
            this.send({
                type: 'join',
                username: state.user.username,
                team: state.user.team
            });
        }

        this.flushPendingMessages();
    }

    onMessage(event) {
        try {
            const data = JSON.parse(event.data);
            
            // Handle ping/pong for connection health
            if (data.type === 'ping') {
                this.send({ type: 'pong' });
                return;
            }
            
            const handler = this.handlers[data.type];
            if (handler) {
                handler(data);
            } else {
                console.warn('Unhandled message type:', data.type);
            }
        } catch (error) {
            console.error('Error parsing message:', error, event.data);
        }
    }

    onClose(event) {
        console.log(`WebSocket closed: ${event.code} ${event.reason}`);
        this.ws = null;
        this.isConnecting = false;
        this.scheduleReconnect();
    }

    onError(error) {
        console.error('WebSocket error:', error);
        // onClose will usually follow onError, so we handle reconnect there
    }

    calculateBackoff(attempt) {
        // Exponential backoff with jitter
        const exponentialDelay = this.baseDelay * Math.pow(2, attempt);
        const maxClampedDelay = Math.min(exponentialDelay, this.maxDelay);
        // Add up to 20% jitter
        const jitter = maxClampedDelay * 0.2 * Math.random();
        return maxClampedDelay + jitter;
    }

    scheduleReconnect() {
        if (this.reconnectAttempts >= this.maxReconnectAttempts) {
            console.error('Max reconnect attempts reached');
            return;
        }
        
        const delay = this.calculateBackoff(this.reconnectAttempts);
        this.reconnectAttempts++;
        
        console.log(`Scheduling reconnect attempt ${this.reconnectAttempts} in ${Math.round(delay)}ms`);
        setTimeout(() => this.connect(), delay);
    }

    send(message) {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify(message));
            return true;
        }

        this.pendingMessages.push(message);
        if (!this.isConnecting && !this.ws) {
            this.connect();
        }
        return false;
    }

    flushPendingMessages() {
        if (!this.ws || this.ws.readyState !== WebSocket.OPEN) return;

        const messages = [...this.pendingMessages];
        this.pendingMessages = [];
        messages.forEach(message => {
            this.ws.send(JSON.stringify(message));
        });
    }
    
    // Register a handler for a specific message type
    on(type, handler) {
        this.handlers[type] = handler;
    }
    
    // Register handlers that dispatch to the store
    registerDefaultHandlers() {
        this.on('connected', (data) => {
            if (data.state) store.updateMatchState(data.state);
            if (data.leaderboard) store.updateLeaderboard(data.leaderboard);
            if (data.chat) store.setChatHistory(data.chat);
            if (data.reactions) store.updateReactions(data.reactions);
            if (data.crowd_hype !== undefined) store.setCrowdHype(data.crowd_hype);
            if (data.is_auto !== undefined && data.interval !== undefined) {
                store.setSimulationState(data.is_auto, data.interval);
            }
        });

        this.on('joined', (data) => {
            const currentUser = store.getState().user || {};
            store.setUser({
                ...currentUser,
                username: data.username || currentUser.username,
                team: data.team || currentUser.team || 'CSK',
                user_id: currentUser.user_id || data.user_id || createGuestUserId(),
                isGuest: currentUser.isGuest !== undefined ? currentUser.isGuest : true
            });
        });

        this.on('user_joined', (data) => {
            if (data.leaderboard) store.updateLeaderboard(data.leaderboard);
        });

        this.on('match_starting', (data) => {
            if (data.state) store.updateMatchState(data.state);
            store.setQuest(null);
            store.setPredictionWindow(null);
        });
        
        this.on('ball_result', (data) => {
            store.updateMatchState(data.state);
            if (data.leaderboard) store.updateLeaderboard(data.leaderboard);
            if (data.reactions) store.updateReactions(data.reactions);
            if (data.crowd_hype !== undefined) store.setCrowdHype(data.crowd_hype);
            
            // Update AI quest stats from prediction results (sent per-user)
            // The stats will be updated when the next prediction_window arrives
            
            // Clear prediction window when ball is bowled
            store.setPredictionWindow(null);
        });
        
        this.on('prediction_window', (data) => {
            store.setPredictionWindow({
                options: data.options,
                timeLeft: data.time_left
            });
            if (data.state) store.updateMatchState(data.state);
            // Update AI suggestion for this ball
            if (data.ai_suggestion) {
                store.setAiSuggestion(data.ai_suggestion);
            }
        });

        this.on('prediction_locked', () => {
            // Prediction buttons lock optimistically in the component.
        });

        this.on('innings_break', (data) => {
            if (data.state) store.updateMatchState(data.state);
            store.setPredictionWindow(null);
        });

        this.on('match_end', (data) => {
            if (data.state) store.updateMatchState(data.state);
            if (data.leaderboard) store.updateLeaderboard(data.leaderboard);
            store.setPredictionWindow(null);
        });
        
        this.on('chat_message', (data) => {
            store.addChatMessage(data.message || data.data);
        });
        
        this.on('chat_history', (data) => {
            store.setChatHistory(data.messages);
        });
        
        this.on('new_poll', (data) => {
            store.setPoll(data.data);
        });
        
        this.on('poll_results', (data) => {
            const state = store.getState();
            if (state.poll && state.poll.poll_id === data.poll_id) {
                store.setPoll({ ...state.poll, results: data.results });
            }
        });
        
        this.on('reaction', (data) => {
            if (data.counts) {
                store.updateReactions(data.counts);
            }
            if (data.crowd_hype !== undefined) {
                store.setCrowdHype(data.crowd_hype);
            }
            if (data.leaderboard) {
                store.updateLeaderboard(data.leaderboard);
            }
        });

        this.on('auto_toggled', (data) => {
            const current = store.getState();
            store.setSimulationState(data.auto, current.interval);
        });

        this.on('interval_changed', (data) => {
            const current = store.getState();
            store.setSimulationState(current.isAuto, data.interval);
        });

        this.on('match_reset', (data) => {
            store.updateMatchState(data.state);
            if (data.reactions) store.updateReactions(data.reactions);
            if (data.crowd_hype !== undefined) store.setCrowdHype(data.crowd_hype);
            if (data.leaderboard !== undefined) store.updateLeaderboard(data.leaderboard);
            store.setQuest(null);
            store.setPredictionWindow(null);
        });

        this.on('quest_generated', (data) => {
            if (data.active) {
                store.setQuest({
                    active: true,
                    suggestion: data.quest?.suggestion || null,
                    stats: data.quest?.stats || {total: 0, correct: 0, followed: 0, followed_correct: 0}
                });
            } else {
                store.setQuest(null);
            }
        });

        this.on('ai_quest_update', (data) => {
            const quest = store.getState().quest;
            if (quest && quest.active) {
                store.setQuest({
                    ...quest,
                    stats: data.stats || quest.stats,
                    suggestion: data.suggestion || quest.suggestion,
                });
            }
        });
    }
}

const wsClient = new WebSocketClient();
export { wsClient, WebSocketClient };
export default wsClient;
