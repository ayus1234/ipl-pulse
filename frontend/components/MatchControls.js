import Component from '../js/component.js';
import store from '../js/store.js';
import wsClient from '../js/websocket.js';

export default class MatchControls extends Component {
    constructor() {
        super();
        this.state = {
            matchState: store.getState().matchState,
            isAuto: store.getState().isAuto,
            interval: store.getState().interval,
            leaderboard: store.getState().leaderboard,
            user: store.getState().user
        };

        store.subscribe((state) => {
            this.setState({
                matchState: state.matchState,
                isAuto: state.isAuto,
                interval: state.interval,
                leaderboard: state.leaderboard,
                user: state.user
            });
            this.updateHeaderTelemetry();
        });
    }

    updateHeaderTelemetry() {
        const { matchState, leaderboard } = this.state;

        const needRunsEl = document.getElementById('header-need-runs');
        const needBallsEl = document.getElementById('header-need-balls');
        const fansCountEl = document.getElementById('header-fans-count');
        const mainTitleEl = document.getElementById('main-match-title');

        if (matchState) {
            if (needRunsEl && needBallsEl) {
                if (matchState.innings === 2) {
                    const reqRuns = Math.max(0, matchState.target - matchState.score);
                    needRunsEl.textContent = reqRuns;
                    needBallsEl.textContent = 120 - (matchState.total_balls || 0);
                } else {
                    needRunsEl.textContent = "-";
                    needBallsEl.textContent = matchState.total_balls || 0;
                }
            }
        }

        if (fansCountEl) {
            fansCountEl.textContent = leaderboard ? leaderboard.length + 1 : 1;
        }
    }

    bindEvents() {
        if (!this.element) return;

        const startBtn = this.element.querySelector('.start-btn');
        if (startBtn) {
            startBtn.addEventListener('click', () => {
                wsClient.send({
                    type: 'start_match'
                });
            });
        }

        const nextBtn = this.element.querySelector('.next-btn');
        if (nextBtn) {
            nextBtn.addEventListener('click', () => {
                wsClient.send({ type: 'next_ball' });
            });
        }

        const autoBtn = this.element.querySelector('.auto-btn');
        if (autoBtn) {
            autoBtn.addEventListener('click', () => {
                wsClient.send({
                    type: 'toggle_auto',
                    auto: !this.state.isAuto
                });
            });
        }

        const resetBtn = this.element.querySelector('.reset-btn');
        if (resetBtn) {
            resetBtn.addEventListener('click', () => {
                wsClient.send({ type: 'reset_match' });
            });
        }

        const intervalSelect = this.element.querySelector('.interval-select');
        if (intervalSelect) {
            intervalSelect.addEventListener('change', (e) => {
                wsClient.send({
                    type: 'change_interval',
                    interval: parseInt(e.target.value)
                });
            });
        }
    }

    render() {
        const { matchState, isAuto, interval, leaderboard, user } = this.state;

        let userXp = 0;
        let accuracy = 0;
        if (user && leaderboard) {
            const entry = leaderboard.find(e => e.username === user.username);
            if (entry) {
                userXp = entry.xp || 0;
                accuracy = entry.total > 0 ? Math.round((entry.correct / entry.total) * 100) : 0;
            }
        }

        if (!matchState || matchState.match_status === 'scheduled') {
            return `
                <div class="control-dock">
                    <div class="panel control-start-panel">
                        <div>
                            <div class="control-kicker"><i class="fas fa-shield-halved"></i> Match room</div>
                            <div class="control-title">Ready for first ball</div>
                            <div class="control-subtitle">Start the live simulation to open predictions, fan reactions, and the match command centre.</div>
                        </div>
                        <button class="btn btn-cyan start-btn">
                            <i class="fas fa-play"></i> Start Match
                        </button>
                    </div>
                </div>
            `;
        }

        return `
            <div class="panel match-command-centre">
                <div class="command-grid">
                    <div class="session-card">
                        <div class="control-kicker"><i class="fas fa-tower-broadcast"></i> Match command</div>
                        <div class="status-chip-row">
                            <div class="status-chip live"><i class="fas fa-signal"></i> LIVE</div>
                            <div class="status-chip xp"><i class="fas fa-bolt"></i> ${userXp} XP</div>
                            <div class="status-chip accuracy"><i class="fas fa-bullseye"></i> ${accuracy}% accuracy</div>
                        </div>
                        <div class="control-subtitle">Auto mode handles the broadcast pace. Switch it off to take every delivery manually.</div>
                    </div>

                    <div class="control-grid">
                        <button class="btn btn-cyan next-btn" ${isAuto ? 'disabled' : ''}>
                            <i class="fas fa-play"></i> Next Ball
                        </button>
                        <button class="btn btn-grey auto-btn ${isAuto ? 'auto-active' : ''}">
                            <i class="fas ${isAuto ? 'fa-pause' : 'fa-play'}"></i> ${isAuto ? 'Auto On' : 'Auto Off'}
                        </button>
                        <select class="btn btn-grey interval-select" aria-label="Ball interval">
                            <option value="5" ${interval === 5 ? 'selected' : ''}>5s pace</option>
                            <option value="8" ${interval === 8 ? 'selected' : ''}>8s pace</option>
                            <option value="10" ${interval === 10 ? 'selected' : ''}>10s pace</option>
                            <option value="15" ${interval === 15 ? 'selected' : ''}>15s pace</option>
                        </select>
                        <button class="btn btn-grey reset-btn">
                            <i class="fas fa-sync-alt"></i> Reset
                        </button>
                    </div>
                </div>
            </div>
        `;
    }
}
