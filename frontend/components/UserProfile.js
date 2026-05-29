import Component from '../js/component.js';
import store from '../js/store.js';
import Config from '../js/config.js';

export default class UserProfile extends Component {
    constructor() {
        super();
        this.state = {
            user: store.getState().user,
            profileData: null,
            loading: false,
            isOpen: false
        };

        store.subscribe((state) => {
            if (this.state.user !== state.user) {
                this.setState({ user: state.user, profileData: null });
                if (state.user && state.user.user_id && !state.user.isGuest) {
                    this.fetchProfile(state.user.user_id);
                } else if (state.user && state.user.isGuest && this.state.isOpen) {
                    this.loadGuestProfile(state.user);
                }
            }
        });
        
        // Expose open toggle globally for the header button
        window.toggleUserProfile = this.toggle.bind(this);
    }

    buildGuestProfile(user) {
        const state = store.getState();
        const lbEntry = (state.leaderboard || []).find(x => x.username === user.username);
        const total = lbEntry ? (lbEntry.total || 0) : 0;
        const correct = lbEntry ? (lbEntry.correct || 0) : 0;
        const accuracy = total > 0 ? Math.round((correct / total) * 100) : 0;

        return {
            total_xp: lbEntry ? (lbEntry.xp || 0) : 0,
            accuracy,
            total_predictions: total,
            highest_streak: lbEntry ? (lbEntry.streak || 0) : 0,
            achievements: [
                { name: "Active Fan", description: "Joined the live session", icon: "fas fa-plug", tier: "bronze" }
            ]
        };
    }

    loadGuestProfile(user = this.state.user) {
        if (!user) return;
        this.setState({ profileData: this.buildGuestProfile(user), loading: false });
    }

    async fetchProfile(userId) {
        this.setState({ loading: true });
        try {
            const response = await fetch(`${Config.API_BASE_URL}/users/${userId}/profile`);
            if (response.ok) {
                const data = await response.json();
                this.setState({ profileData: data, loading: false });
            } else {
                this.setState({ loading: false });
                if (window.showToast) window.showToast('Failed to load profile', 'error');
            }
        } catch (error) {
            console.error('Error fetching profile:', error);
            this.setState({ loading: false });
        }
    }

    toggle() {
        this.setState({ isOpen: !this.state.isOpen });
        if (this.state.isOpen && this.state.user) {
            if (this.state.user.isGuest) {
                this.loadGuestProfile(this.state.user);
            } else if (this.state.user.user_id) {
                if (!this.state.profileData) {
                    this.fetchProfile(this.state.user.user_id);
                }
            } else {
                this.loadGuestProfile(this.state.user);
            }
        }
    }

    bindEvents() {
        if (!this.element) return;
        
        const closeBtn = this.element.querySelector('.close-modal-btn');
        if (closeBtn) {
            closeBtn.addEventListener('click', () => this.toggle());
        }
        
        const logoutBtn = this.element.querySelector('#logout-btn');
        if (logoutBtn) {
            logoutBtn.addEventListener('click', () => {
                store.setUser(null);
                this.setState({ profileData: null, isOpen: false });
                if (window.showToast) window.showToast('Logged out successfully', 'info');
            });
        }
    }

    render() {
        const { user, profileData, loading, isOpen } = this.state;
        
        if (!isOpen) return `<div class="is-hidden" style="display:none"></div>`;
        
        if (!user) {
            return `
                <div class="modal-overlay">
                    <div class="glass-panel modal-content animate-in">
                        <button class="close-modal-btn"><i class="fas fa-times"></i></button>
                        <h2>Not Logged In</h2>
                        <p>Join the game using the header to view your profile!</p>
                    </div>
                </div>
            `;
        }

        return `
            <div class="modal-overlay">
                <div class="glass-panel modal-content animate-in">
                    <button class="close-modal-btn"><i class="fas fa-times"></i></button>
                    
                    <div class="profile-header">
                        <div class="avatar large"><i class="fas fa-user"></i></div>
                        <h2>${user.username}</h2>
                        <span class="team-badge ${(user.team || 'fan').toLowerCase()}">${user.team || 'Fan'} Fan</span>
                    </div>
                    
                    ${loading ? `<div class="loader"></div>` : 
                      !profileData ? `<p>Unable to load profile data.</p>` : `
                        
                        <div class="profile-stats-grid">
                            <div class="stat-box">
                                <span class="label">Total XP</span>
                                <span class="value">${profileData.total_xp || 0}</span>
                            </div>
                            <div class="stat-box">
                                <span class="label">Accuracy</span>
                                <span class="value">${profileData.accuracy || 0}%</span>
                            </div>
                            <div class="stat-box">
                                <span class="label">Predictions</span>
                                <span class="value">${profileData.total_predictions || 0}</span>
                            </div>
                            <div class="stat-box">
                                <span class="label">Best Streak</span>
                                <span class="value">${profileData.highest_streak || 0}</span>
                            </div>
                        </div>
                        
                        <div class="achievements-section">
                            <h3><i class="fas fa-medal"></i> Badges</h3>
                            <div class="badges-grid">
                                ${!profileData.achievements || profileData.achievements.length === 0 ? 
                                    '<p class="empty-state">No badges earned yet. Keep predicting!</p>' : 
                                    profileData.achievements.map(badge => `
                                        <div class="badge-item" title="${badge.description}">
                                            <div class="badge-icon ${badge.tier || 'bronze'}">
                                                <i class="${badge.icon || 'fas fa-star'}"></i>
                                            </div>
                                            <span class="badge-name">${badge.name}</span>
                                        </div>
                                    `).join('')
                                }
                            </div>
                        </div>
                    `}
                    
                    <div class="profile-actions">
                        <button id="logout-btn" class="secondary-btn">Sign Out</button>
                    </div>
                </div>
            </div>
        `;
    }
}
