import Component from '../js/component.js';
import store from '../js/store.js';
import wsClient from '../js/websocket.js';

export default class ChatBox extends Component {
    constructor() {
        super();
        this.state = {
            chat: store.getState().chat,
            user: store.getState().user
        };

        store.subscribe((state) => {
            if (this.state.chat !== state.chat) {
                const oldChat = this.state.chat || [];
                const newChat = state.chat || [];
                
                // Trigger floating emoji if a new single emoji message arrives
                if (newChat.length > oldChat.length) {
                    const newMsg = newChat[newChat.length - 1];
                    const emojis = ['🔥', '👏', '😮', '💔', '🏏'];
                    if (emojis.includes(newMsg.text.trim())) {
                        this.spawnEmoji(newMsg.text.trim());
                    }
                }
                
                this.setState({ chat: state.chat });
                this.scrollToBottom();
            }
            if (this.state.user !== state.user) {
                this.setState({ user: state.user });
            }
        });
    }

    spawnEmoji(emoji) {
        const span = document.createElement('span');
        span.className = 'floating-emoji';
        span.innerText = emoji;
        const randomX = Math.random() * 80 + 10; // 10% to 90% horizontal range
        span.style.left = `${randomX}vw`;
        document.body.appendChild(span);
        
        setTimeout(() => {
            span.remove();
        }, 2500);
    }

    scrollToBottom() {
        if (!this.element) return;
        const msgList = this.element.querySelector('.chat-messages');
        if (msgList) {
            setTimeout(() => {
                msgList.scrollTop = msgList.scrollHeight;
            }, 10);
        }
    }

    sendMessage(text) {
        if (!text.trim() || !this.state.user) return;
        
        wsClient.send({
            type: 'chat',
            text: text.trim()
        });
    }

    bindEvents() {
        if (!this.element) return;
        
        const form = this.element.querySelector('.chat-input-form');
        const input = this.element.querySelector('.chat-input');
        
        if (form && input) {
            form.addEventListener('submit', (e) => {
                e.preventDefault();
                this.sendMessage(input.value);
                input.value = '';
            });
        }

        const reactionBtns = this.element.querySelectorAll('.react-btn');
        reactionBtns.forEach(btn => {
            btn.addEventListener('click', () => {
                const emoji = btn.getAttribute('data-emoji');
                this.sendMessage(emoji);
            });
        });
    }

    render() {
        const { chat, user } = this.state;
        const emojis = ['🔥', '👏', '😮', '💔', '🏏'];
        
        return `
            <div class="glass-panel chat-widget animate-in">
                <div class="widget-header">
                    <h3><i class="fas fa-comments"></i> Stadium Fan Zone</h3>
                </div>
                
                <div class="chat-messages">
                    ${!chat || chat.length === 0 ? 
                        '<div class="empty-state chat-empty">No messages yet. Send a cheer or click a reaction emoji!</div>' : 
                        chat.map(msg => `
                            <div class="chat-msg ${user && user.username === msg.username ? 'self' : ''}">
                                <div class="chat-msg-header">
                                    <span class="chat-user">${msg.username}</span>
                                    <span class="team-badge ${msg.team.toLowerCase()}">${msg.team}</span>
                                </div>
                                <div class="chat-text">${this.escapeHtml(msg.text)}</div>
                            </div>
                        `).join('')
                    }
                </div>
                
                ${user ? `
                    <!-- Premium Quick Reaction Bar -->
                    <div class="reactions-box">
                        ${emojis.map(e => `
                            <button class="react-btn" data-emoji="${e}">${e}</button>
                        `).join('')}
                    </div>
                ` : ''}

                <div class="chat-input-area">
                    ${user ? `
                        <form class="chat-input-form chat-input-wrapper">
                            <input type="text" class="chat-input" placeholder="Type a stadium cheer..." maxlength="200" required>
                            <button type="submit" class="chat-send-btn"><i class="fas fa-paper-plane"></i></button>
                        </form>
                    ` : `
                        <div class="login-prompt">
                            <i class="fas fa-sign-in-alt"></i> Enter a username in the header to join the fan chat!
                        </div>
                    `}
                </div>
            </div>
        `;
    }
    
    escapeHtml(unsafe) {
        return (unsafe || '').replace(/&/g, "&amp;")
             .replace(/</g, "&lt;")
             .replace(/>/g, "&gt;")
             .replace(/"/g, "&quot;")
             .replace(/'/g, "&#039;");
    }
}
