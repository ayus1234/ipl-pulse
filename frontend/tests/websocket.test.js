import { describe, it, mock } from 'node:test';
import assert from 'node:assert';
import { WebSocketClient } from '../js/websocket.js';
import store from '../js/store.js';

describe('WebSocketClient Backoff Logic', () => {
    it('should calculate exponential backoff with jitter', () => {
        const client = new WebSocketClient();
        client.baseDelay = 1000;
        client.maxDelay = 30000;
        
        // Attempt 0: 2^0 * 1000 = 1000
        const delay0 = client.calculateBackoff(0);
        assert.ok(delay0 >= 1000 && delay0 <= 1200); // Up to 20% jitter
        
        // Attempt 1: 2^1 * 1000 = 2000
        const delay1 = client.calculateBackoff(1);
        assert.ok(delay1 >= 2000 && delay1 <= 2400);
        
        // Attempt 2: 2^2 * 1000 = 4000
        const delay2 = client.calculateBackoff(2);
        assert.ok(delay2 >= 4000 && delay2 <= 4800);
        
        // Attempt 5: 2^5 * 1000 = 32000 -> capped at 30000
        const delay5 = client.calculateBackoff(5);
        assert.ok(delay5 >= 30000 && delay5 <= 36000); // Capped at maxDelay + jitter
    });

    it('should preserve optimistic guest state when join is acknowledged', () => {
        const client = new WebSocketClient();
        store.state = {
            ...store.state,
            user: {
                username: 'PendingFan',
                team: 'MI',
                user_id: 'guest-id-123',
                isGuest: true
            }
        };

        client.handlers.joined({ username: 'TestFan', team: 'CSK' });

        assert.deepStrictEqual(store.getState().user, {
            username: 'TestFan',
            team: 'CSK',
            user_id: 'guest-id-123',
            isGuest: true
        });
    });

    it('should queue button messages until the socket opens', () => {
        const originalWebSocket = global.WebSocket;
        global.WebSocket = { OPEN: 1 };

        try {
            const client = new WebSocketClient();
            client.connect = mock.fn();

            const sentImmediately = client.send({ type: 'start_match', team1: 'CSK', team2: 'MI' });
            assert.strictEqual(sentImmediately, false);
            assert.strictEqual(client.pendingMessages.length, 1);
            assert.strictEqual(client.connect.mock.calls.length, 1);

            const socketSend = mock.fn();
            client.ws = { readyState: WebSocket.OPEN, send: socketSend };
            client.flushPendingMessages();

            assert.strictEqual(client.pendingMessages.length, 0);
            assert.strictEqual(socketSend.mock.calls.length, 1);
            assert.strictEqual(socketSend.mock.calls[0].arguments[0], JSON.stringify({
                type: 'start_match',
                team1: 'CSK',
                team2: 'MI'
            }));
        } finally {
            global.WebSocket = originalWebSocket;
        }
    });

    it('should store generated quests and mark completed quests from ball results', () => {
        const client = new WebSocketClient();
        store.state = {
            ...store.state,
            user: {
                username: 'QuestFan',
                team: 'CSK',
                user_id: 'guest-id-quest',
                isGuest: true
            },
            quest: null
        };

        client.handlers.quest_generated({
            quest: {
                id: 'dot_ball',
                label: 'Predict a Dot Ball on the next delivery!',
                reward: 30,
                username: 'QuestFan'
            }
        });

        assert.strictEqual(store.getState().quest.id, 'dot_ball');

        client.handlers.ball_result({
            state: { total_balls: 1, momentum: 55, momentum_history: [55] },
            quests: {
                ws123: {
                    id: 'dot_ball',
                    label: 'Predict a Dot Ball on the next delivery!',
                    reward: 30,
                    username: 'QuestFan',
                    completed: true
                }
            }
        });

        assert.strictEqual(store.getState().quest.completed, true);
    });
});
