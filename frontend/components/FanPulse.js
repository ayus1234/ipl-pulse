import Component from '../js/component.js';
import store from '../js/store.js';
import wsClient from '../js/websocket.js';

export default class FanPulse extends Component {
    constructor() {
        super();
        this.state = {
            reactions: store.getState().reactions,
            crowdHype: store.getState().crowdHype,
            user: store.getState().user
        };

        store.subscribe((state) => {
            this.setState({
                reactions: state.reactions,
                crowdHype: state.crowdHype,
                user: state.user
            });
        });
    }

    spawnEmoji(emoji) {
        const span = document.createElement('span');
        span.className = 'floating-emoji';
        span.innerText = emoji;
        span.style.position = 'fixed';
        span.style.bottom = '0';
        span.style.fontSize = '2rem';
        span.style.zIndex = '9999';
        span.style.pointerEvents = 'none';
        const randomX = Math.random() * 80 + 10;
        span.style.left = `${randomX}vw`;

        span.animate([
            { transform: 'translateY(0) scale(1)', opacity: 1 },
            { transform: 'translateY(-100vh) scale(0.3)', opacity: 0 }
        ], {
            duration: 2500,
            easing: 'ease-out'
        });

        document.body.appendChild(span);
        setTimeout(() => span.remove(), 2500);
    }

    bindEvents() {
        if (!this.element) return;

        const reactionBtns = this.element.querySelectorAll('.pulse-btn');
        reactionBtns.forEach(btn => {
            btn.addEventListener('click', () => {
                if (!this.state.user) return;
                const key = btn.getAttribute('data-reaction-key');
                const emoji = btn.getAttribute('data-emoji');
                this.spawnEmoji(emoji);
                wsClient.send({ type: 'react', reaction: key });
            });
        });
    }

    render() {
        const { reactions, crowdHype, user } = this.state;

        const emojiMap = {
            fire: '&#128293;',
            laugh: '&#128514;',
            shock: '&#128558;',
            heart: '&#10084;&#65039;',
            bolt: '&#9889;',
            applause: '&#128079;',
            blast: '&#128165;',
            cricket: '&#127951;'
        };

        let totalCount = 0;
        let topKey = 'fire';
        let topCount = 0;

        Object.keys(emojiMap).forEach(key => {
            const count = reactions && reactions[key] ? reactions[key] : 0;
            totalCount += count;
            if (count > topCount) {
                topCount = count;
                topKey = key;
            }
        });

        return `
            <div class="panel panel-subtle">
                <div class="panel-header">
                    <div class="panel-title orange">
                        <i class="fas fa-fire"></i> Fan Pulse
                    </div>
                </div>

                <div>
                    <div class="hype-row">
                        <span>Crowd Hype</span>
                        <span class="text-cyan">${crowdHype}%</span>
                    </div>
                    <div class="hype-track">
                        <div class="hype-fill" style="width:${crowdHype}%;"></div>
                    </div>
                </div>

                <div class="fan-grid">
                    ${Object.entries(emojiMap).map(([key, emoji]) => {
                        const count = reactions && reactions[key] ? reactions[key] : 0;
                        return `
                            <button class="pulse-btn" data-reaction-key="${key}" data-emoji="${emoji}" ${!user ? 'disabled' : ''}>
                                <div class="pulse-emoji">${emoji}</div>
                                <div class="pulse-count">${count}</div>
                            </button>
                        `;
                    }).join('')}
                </div>

                <div class="panel-footer">
                    <span>Total: <b class="text-main">${totalCount}</b></span>
                    <span>Top: <b class="text-orange">${emojiMap[topKey]} ${topCount}</b></span>
                    <span class="text-green">+1 XP per reaction</span>
                </div>
            </div>
        `;
    }
}
