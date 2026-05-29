import Component from '../js/component.js';
import store from '../js/store.js';
import wsClient from '../js/websocket.js';
import storage from '../js/storage.js';

const GUEST_USER_ID_KEY = 'guest_user_id';

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

function getGuestUserId() {
    if (typeof localStorage === 'undefined') {
        return createGuestUserId();
    }

    const existing = storage.get(GUEST_USER_ID_KEY);
    if (existing) return existing;

    const generated = createGuestUserId();
    storage.set(GUEST_USER_ID_KEY, generated);
    return generated;
}

export default class UserLogin extends Component {
    constructor() {
        super();
        this.state = {
            user: store.getState().user,
            matchState: store.getState().matchState
        };

        store.subscribe((state) => {
            let changed = false;
            if (this.state.user !== state.user) {
                this.state.user = state.user;
                changed = true;
            }
            if (this.state.matchState !== state.matchState) {
                this.state.matchState = state.matchState;
                changed = true;
            }
            if (changed) {
                this.setState(this.state);
            }
        });
    }

    login(username, team) {
        const cleanUsername = (username || '').trim();
        const fallbackTeam = this.state.matchState ? this.state.matchState.team1 : 'CSK';
        const selectedTeam = team || fallbackTeam;

        if (cleanUsername.length < 3) {
            if (typeof window !== 'undefined' && window.showToast) {
                window.showToast('Username must be at least 3 characters', 'error');
            }
            return false;
        }

        store.setUser({
            username: cleanUsername,
            team: selectedTeam,
            user_id: getGuestUserId(),
            isGuest: true
        });

        wsClient.send({
            type: 'join',
            username: cleanUsername,
            team: selectedTeam
        });

        return true;
    }

    bindEvents() {
        if (!this.element) return;

        const joinBtn = this.element.querySelector('.join-btn');
        const usernameInput = this.element.querySelector('#username-input');
        const teamSelect = this.element.querySelector('#team-select');
        
        const handleJoin = () => {
            const username = usernameInput ? usernameInput.value.trim() : '';
            const fallbackTeam = this.state.matchState ? this.state.matchState.team1 : 'CSK';
            const team = teamSelect ? teamSelect.value : fallbackTeam;
            this.login(username, team);
        };

        if (joinBtn) {
            joinBtn.addEventListener('click', handleJoin);
        }
        
        if (usernameInput) {
            usernameInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') handleJoin();
            });
        }
        
        const profileBadge = this.element.querySelector('.avatar-badge');
        if (profileBadge && window.toggleUserProfile) {
            profileBadge.addEventListener('click', window.toggleUserProfile);
        }
    }

    render() {
        const { user, matchState } = this.state;

        if (user) {
            const teamClass = matchState && user.team === matchState.team2 ? 'team-b' : 'team-a';
            return `
                <div class="avatar-badge" title="Click to view profile">
                    <div class="icon ${teamClass}">
                        <i class="fas fa-user"></i>
                    </div>
                    <div class="info">
                        <span class="name">${user.username}</span>
                        <span class="team">${user.team} Fan</span>
                    </div>
                </div>
            `;
        }

        let team1Val = 'CSK';
        let team1Name = 'Chennai Super Kings (CSK)';
        let team2Val = 'MI';
        let team2Name = 'Mumbai Indians (MI)';
        
        if (matchState && matchState.team1_data && matchState.team2_data) {
            team1Val = matchState.team1;
            team1Name = matchState.team1_data.name;
            team2Val = matchState.team2;
            team2Name = matchState.team2_data.name;
        } else if (matchState) {
            team1Val = matchState.team1;
            team1Name = matchState.team1;
            team2Val = matchState.team2;
            team2Name = matchState.team2;
        }

        return `
            <div class="login-card">
                <div class="login-form" style="flex-shrink: 1; min-width: 0;">
                    <input type="text" id="username-input" style="width: 130px;" placeholder="Username" autocomplete="off" />
                    <span style="color: #8b9bb4; font-size: 0.85rem; margin-left: 4px; margin-right: 2px;">Supporting:</span>
                    <select id="team-select">
                        <option value="${team1Val}">${team1Name}</option>
                        <option value="${team2Val}">${team2Name}</option>
                    </select>
                    <button class="primary-btn join-btn" style="padding: 6px 12px;">Join</button>
                </div>
            </div>
        `;
    }
}
