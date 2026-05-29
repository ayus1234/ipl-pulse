import Component from '../js/component.js';
import store from '../js/store.js';
import Config from '../js/config.js';

export default class PollBox extends Component {
    constructor() {
        super();
        this.state = {
            poll: store.getState().poll,
            user: store.getState().user,
            votedOption: null
        };

        store.subscribe((state) => {
            if (this.state.poll !== state.poll) {
                // If a new poll arrives, clear voted option
                if (state.poll && (!this.state.poll || this.state.poll.poll_id !== state.poll.poll_id)) {
                    this.setState({ poll: state.poll, votedOption: null });
                } else {
                    this.setState({ poll: state.poll });
                }
            }
            if (this.state.user !== state.user) {
                this.setState({ user: state.user });
            }
        });
    }

    async submitVote(optionId) {
        const { poll, user, votedOption } = this.state;
        if (!poll || !user || votedOption) return;

        try {
            const response = await fetch(`${Config.API_BASE_URL}/polls/${poll.poll_id}/respond`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    user_id: user.user_id || '00000000-0000-0000-0000-000000000000', // Mock UUID if anonymous
                    selected_option: optionId
                })
            });

            if (response.ok) {
                this.setState({ votedOption: optionId });
                if (window.showToast) window.showToast('Vote submitted successfully!', 'success');
            } else {
                if (window.showToast) window.showToast('Failed to submit vote.', 'error');
            }
        } catch (error) {
            console.error('Poll submission error:', error);
            if (window.showToast) window.showToast('Network error while voting.', 'error');
        }
    }

    normalizeOption(option) {
        if (option && typeof option === 'object') {
            const id = option.id || option.value || option.label;
            return {
                id: String(id),
                label: option.label || String(id)
            };
        }

        return {
            id: String(option),
            label: String(option)
        };
    }

    bindEvents() {
        if (!this.element) return;
        
        const buttons = this.element.querySelectorAll('.poll-opt-btn');
        buttons.forEach(btn => {
            btn.addEventListener('click', (e) => {
                const optionId = e.target.closest('.poll-opt-btn').dataset.optionId;
                this.submitVote(optionId);
            });
        });
    }

    render() {
        const { poll, user, votedOption } = this.state;
        
        if (!poll) {
            if (this.element) this.element.style.display = 'none';
            return `<div class="poll-widget-empty"></div>`;
        }
        
        if (this.element) {
            this.element.style.display = 'block';
        }
        
        const totalVotes = Object.values(poll.results || {}).reduce((a, b) => a + b, 0);
        const options = (poll.options || []).map(option => this.normalizeOption(option));
        
        return `
            <div class="glass-panel poll-widget animate-in">
                <div class="widget-header">
                    <h3><i class="fas fa-poll"></i> Live Fan Poll</h3>
                </div>
                
                <div class="poll-question">
                    ${poll.question}
                </div>
                
                <div class="poll-options">
                    ${options.map(opt => {
                        const votes = (poll.results && poll.results[opt.id]) || 0;
                        const percent = totalVotes === 0 ? 0 : Math.round((votes / totalVotes) * 100);
                        const isVoted = votedOption === opt.id;
                        
                        return `
                            <button 
                                class="poll-opt-btn ${isVoted ? 'voted' : ''}" 
                                data-option-id="${opt.id}"
                                ${votedOption || !user ? 'disabled' : ''}
                            >
                                <div class="opt-content">
                                    <span class="opt-label">${opt.label}</span>
                                    ${votedOption ? `<span class="opt-percent">${percent}%</span>` : ''}
                                </div>
                                ${votedOption ? `
                                    <div class="opt-progress-bg">
                                        <div class="opt-progress-fill" style="width: ${percent}%"></div>
                                    </div>
                                ` : ''}
                            </button>
                        `;
                    }).join('')}
                </div>
                
                ${!user ? `
                    <div class="poll-auth-msg">
                        <i class="fas fa-exclamation-circle"></i> Log in to vote! View live results.
                    </div>
                ` : ''}
                <div class="poll-footer"><i class="fas fa-users"></i> ${totalVotes} total votes</div>
            </div>
        `;
    }
}
