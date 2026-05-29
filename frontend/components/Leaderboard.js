import Component from '../js/component.js';
import store from '../js/store.js';

export default class Leaderboard extends Component {
    constructor() {
        super();
        this.state = {
            leaderboard: store.getState().leaderboard,
            user: store.getState().user
        };

        store.subscribe((state) => {
            if (this.state.leaderboard !== state.leaderboard || this.state.user !== state.user) {
                this.setState({ leaderboard: state.leaderboard, user: state.user });
            }
        });
    }

    renderPodiumSlot(entry, rank) {
        if (!entry) return '<div class="podium-step"></div>';

        const rankClass = rank === 1 ? 'first' : rank === 2 ? 'second' : 'third';
        const baseClass = rank === 1 ? 'podium-1' : rank === 2 ? 'podium-2' : 'podium-3';
        const championClass = rank === 1 ? 'champion' : '';

        return `
            <div class="podium-step">
                <div class="podium-avatar ${championClass}">
                    ${entry.team || '?'}
                    <div class="rank-badge ${rankClass}">${rank}</div>
                </div>
                <div class="podium-name">${entry.username}</div>
                <div class="podium-xp">${entry.xp} XP</div>
                <div class="podium-base ${baseClass}"></div>
            </div>
        `;
    }

    render() {
        const { leaderboard, user } = this.state;

        let userRank = '-';
        if (user && leaderboard) {
            const idx = leaderboard.findIndex(e => e.username === user.username);
            if (idx >= 0) userRank = idx + 1;
        }

        if (!leaderboard || leaderboard.length === 0) {
            return `
                <div class="panel panel-subtle">
                    <div class="panel-header">
                        <div class="panel-title gold">
                            <i class="fas fa-trophy"></i> Leaderboard
                        </div>
                    </div>
                    <div class="empty-state">Waiting for stadium predictions...</div>
                </div>
            `;
        }

        const top3 = leaderboard.slice(0, 3);
        const p1 = top3[0] || null;
        const p2 = top3[1] || null;
        const p3 = top3[2] || null;

        return `
            <div class="panel panel-subtle">
                <div class="panel-header">
                    <div class="panel-title gold">
                        <i class="fas fa-trophy"></i> Leaderboard
                    </div>
                    ${user ? `<div class="panel-kicker">Your rank: <b class="text-cyan">#${userRank}</b></div>` : ''}
                </div>

                <div class="podium-container">
                    ${this.renderPodiumSlot(p2, 2)}
                    ${this.renderPodiumSlot(p1, 1)}
                    ${this.renderPodiumSlot(p3, 3)}
                </div>

                <div class="leaderboard-list">
                    ${leaderboard.map((entry, idx) => {
                        const rank = idx + 1;
                        const isSelf = user && entry.username === user.username;

                        return `
                            <div class="leaderboard-row ${isSelf ? 'self' : ''}">
                                <div class="leaderboard-person">
                                    <div class="leaderboard-rank">${rank}</div>
                                    <div class="leaderboard-name">${entry.username}</div>
                                </div>
                                <div class="leaderboard-stats">
                                    <div class="leaderboard-streak">${entry.streak > 2 ? `<i class="fas fa-fire"></i> ${entry.streak}` : ''}</div>
                                    <div class="leaderboard-xp">${entry.xp} XP</div>
                                </div>
                            </div>
                        `;
                    }).join('')}
                </div>
            </div>
        `;
    }
}
