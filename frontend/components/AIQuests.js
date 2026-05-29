import Component from '../js/component.js';
import store from '../js/store.js';
import wsClient from '../js/websocket.js';

export default class AIQuests extends Component {
    constructor() {
        super();
        this.state = {
            quest: store.getState().quest,
            aiSuggestion: store.getState().aiSuggestion,
            user: store.getState().user,
            predictionWindow: store.getState().predictionWindow,
            lastResult: null,  // track the last ball AI result
        };

        store.subscribe((state) => {
            this.setState({
                quest: state.quest,
                aiSuggestion: state.aiSuggestion,
                user: state.user,
                predictionWindow: state.predictionWindow,
            });
        });
    }

    bindEvents() {
        if (!this.element) return;

        const toggleBtn = this.element.querySelector('.ai-toggle-btn');
        if (toggleBtn) {
            toggleBtn.addEventListener('click', () => {
                if (!this.state.user) return;
                wsClient.send({ type: 'generate_quest' });
            });
        }
    }

    render() {
        const { quest, aiSuggestion, user, predictionWindow } = this.state;
        const isActive = quest && quest.active;
        const suggestion = aiSuggestion || (quest && quest.suggestion);
        const stats = quest?.stats || { total: 0, correct: 0, followed: 0, followed_correct: 0 };

        // Not logged in
        if (!user) {
            return `
                <div class="panel panel-subtle text-center">
                    <div class="panel-header">
                        <div class="panel-title sky">
                            <i class="fas fa-robot"></i> AI MATCH QUESTS
                        </div>
                    </div>
                    <p class="text-gold" style="padding: 12px 0;">
                        <i class="fas fa-lock"></i> Log in to unlock AI predictions!
                    </p>
                </div>
            `;
        }

        // AI not activated yet
        if (!isActive) {
            return `
                <div class="panel panel-subtle">
                    <div class="panel-header">
                        <div class="panel-title sky">
                            <i class="fas fa-robot"></i> AI MATCH QUESTS
                        </div>
                        <span class="micro-chip text-cyan">+15 XP bonus</span>
                    </div>
                    <div class="quest-empty" style="text-align: center; padding: 12px 0;">
                        <p style="color: var(--text-secondary); font-size: 12px; margin-bottom: 10px;">
                            Activate AI predictions — get smart suggestions each ball and earn bonus XP when correct!
                        </p>
                        <button class="ai-toggle-btn">
                            <i class="fas fa-magic"></i> Activate AI Assistant
                        </button>
                    </div>
                </div>
            `;
        }

        // AI accuracy stats
        const aiAccuracy = stats.total > 0 ? Math.round((stats.correct / stats.total) * 100) : 0;
        const followedCount = stats.followed || 0;
        const followedCorrect = stats.followed_correct || 0;

        // Emoji map for predictions
        const emojiMap = {
            dot: '⚫', single: '1️⃣', two: '2️⃣',
            boundary: '🏏', six: '6️⃣', wicket: '🔴'
        };

        // Build the suggestion card
        const hasSuggestion = suggestion && suggestion.prediction;
        const hasPredWindow = !!predictionWindow;

        return `
            <div class="panel panel-subtle ai-quest-panel ${hasPredWindow ? 'ai-live' : ''}">
                <div class="panel-header">
                    <div class="panel-title sky">
                        <i class="fas fa-robot"></i> AI MATCH QUESTS
                    </div>
                    <button class="ai-toggle-btn ai-deactivate" title="Turn off AI assistant">
                        <i class="fas fa-power-off"></i>
                    </button>
                </div>

                ${hasSuggestion ? `
                    <div class="ai-suggestion-card ${hasPredWindow ? 'pulse-glow' : ''}">
                        <div class="ai-suggestion-header">
                            <span class="ai-chip"><i class="fas fa-brain"></i> AI Prediction</span>
                            <span class="ai-confidence">${suggestion.confidence || 50}%</span>
                        </div>
                        <div class="ai-suggestion-body">
                            <div class="ai-pick-emoji">${emojiMap[suggestion.prediction] || '🎯'}</div>
                            <div class="ai-pick-info">
                                <div class="ai-pick-label">${suggestion.label || suggestion.prediction}</div>
                                <div class="ai-pick-reason">${suggestion.reason || 'Analyzing match context...'}</div>
                            </div>
                        </div>
                        ${hasPredWindow ? `
                            <div class="ai-follow-hint">
                                <i class="fas fa-hand-pointer"></i> Follow this pick for <span class="text-green">+15 bonus XP</span>
                            </div>
                        ` : `
                            <div class="ai-waiting">
                                <i class="fas fa-hourglass-half"></i> Waiting for next delivery...
                            </div>
                        `}
                    </div>
                ` : `
                    <div class="ai-suggestion-card">
                        <div class="ai-waiting" style="padding: 16px; text-align: center;">
                            <i class="fas fa-satellite-dish fa-spin" style="margin-right: 6px;"></i>
                            AI analyzing match... waiting for first ball
                        </div>
                    </div>
                `}

                <div class="ai-stats-bar">
                    <div class="ai-stat">
                        <span class="ai-stat-label">AI Accuracy</span>
                        <span class="ai-stat-value ${aiAccuracy > 50 ? 'text-green' : 'text-gold'}">${aiAccuracy}%</span>
                    </div>
                    <div class="ai-stat">
                        <span class="ai-stat-label">Balls</span>
                        <span class="ai-stat-value">${stats.total}</span>
                    </div>
                    <div class="ai-stat">
                        <span class="ai-stat-label">Followed</span>
                        <span class="ai-stat-value">${followedCount}</span>
                    </div>
                    <div class="ai-stat">
                        <span class="ai-stat-label">Wins</span>
                        <span class="ai-stat-value text-green">${followedCorrect}</span>
                    </div>
                </div>
            </div>
        `;
    }
}
