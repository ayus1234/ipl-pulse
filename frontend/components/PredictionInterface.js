import Component from '../js/component.js';
import store from '../js/store.js';
import wsClient from '../js/websocket.js';

export default class PredictionInterface extends Component {
    constructor() {
        super();
        this.state = {
            window: store.getState().predictionWindow,
            user: store.getState().user,
            leaderboard: store.getState().leaderboard,
            selectedOption: null,
            timer: 0
        };

        this.timerInterval = null;

        store.subscribe((state) => {
            if (this.state.window !== state.predictionWindow) {
                this.setState({
                    window: state.predictionWindow,
                    selectedOption: null,
                    timer: state.predictionWindow ? state.predictionWindow.timeLeft : 0
                });

                if (state.predictionWindow) {
                    this.startTimer();
                } else {
                    this.stopTimer();
                }
            }
            if (this.state.user !== state.user) {
                this.setState({ user: state.user });
            }
            if (this.state.leaderboard !== state.leaderboard) {
                this.setState({ leaderboard: state.leaderboard });
            }
        });
    }

    startTimer() {
        this.stopTimer();
        this.timerInterval = setInterval(() => {
            if (this.state.timer > 0) {
                this.setState({ timer: this.state.timer - 1 });
            } else {
                this.stopTimer();
            }
        }, 1000);
    }

    stopTimer() {
        if (this.timerInterval) {
            clearInterval(this.timerInterval);
            this.timerInterval = null;
        }
    }

    submitPrediction(option) {
        if (this.state.timer <= 0 || this.state.selectedOption || !this.state.user) return;

        this.setState({ selectedOption: option });
        wsClient.send({
            type: 'predict',
            prediction: option
        });
    }

    bindEvents() {
        if (!this.element) return;

        const buttons = this.element.querySelectorAll('.predict-btn');
        buttons.forEach(btn => {
            btn.addEventListener('click', (e) => {
                const option = e.target.closest('.predict-btn').dataset.option;
                this.submitPrediction(option);
            });
        });
    }

    render() {
        const { window: predWindow, selectedOption, timer, user, leaderboard } = this.state;

        let userXp = 0, userStreak = 0, userAccuracy = 0;
        if (user && leaderboard) {
            const entry = leaderboard.find(e => e.username === user.username);
            if (entry) {
                userXp = entry.xp || 0;
                userStreak = entry.streak || 0;
                userAccuracy = entry.total > 0 ? Math.round((entry.correct / entry.total) * 100) : 0;
            }
        }

        if (!user) {
            return `
                <div class="panel panel-gate panel-subtle">
                    <div class="prediction-icon">
                        <i class="fas fa-fingerprint"></i>
                    </div>
                    <div class="prediction-heading">Predict the Ball Screen</div>
                    <p class="prediction-copy">
                        Enter a username in the header login to unlock live ball-by-ball predictions and earn stadium XP!
                    </p>
                </div>
            `;
        }

        if (!predWindow) {
            return `
                <div class="panel panel-waiting panel-subtle">
                    <div class="panel-header">
                        <div class="panel-title red">
                            <i class="fas fa-crosshairs"></i> Predict the Ball
                        </div>
                    </div>
                    <div class="prediction-waiting">
                        <div class="prediction-waiting-title">
                            <i class="fas fa-hourglass-half"></i> Waiting for next ball...
                        </div>
                        <p class="panel-body-centered">Prediction window opens before each delivery</p>
                    </div>
                    <div class="panel-footer">
                        <span>XP: <b class="text-cyan">${userXp}</b> Streak: <b class="text-orange"><i class="fas fa-fire"></i> ${userStreak}</b></span>
                        <span>Accuracy: <b>${userAccuracy}%</b></span>
                    </div>
                </div>
            `;
        }

        const progressPercent = predWindow.timeLeft
            ? Math.max(0, Math.min(100, (timer / predWindow.timeLeft) * 100))
            : 0;
        const isCritical = timer <= 3;

        return `
            <div class="panel panel-waiting panel-emphasis">
                <div class="panel-header">
                    <div class="panel-title sky">
                        <i class="fas fa-crosshairs"></i> Predict the Ball
                    </div>
                    <div class="timer-badge ${isCritical ? 'critical' : ''}">
                        <i class="far fa-clock"></i> 00:${timer < 10 ? '0' + timer : timer}
                    </div>
                </div>

                <div class="countdown-track">
                    <div class="countdown-fill ${isCritical ? 'critical' : ''}" style="width:${progressPercent}%;"></div>
                </div>

                <div class="prediction-options">
                    ${predWindow.options.map(opt => {
                        const isSelected = selectedOption === opt.id;
                        const isLocked = selectedOption !== null;
                        const optionClass = [
                            'btn',
                            'btn-grey',
                            'predict-btn',
                            'prediction-option',
                            isSelected ? 'selected' : '',
                            isLocked && !isSelected ? 'dimmed' : ''
                        ].filter(Boolean).join(' ');

                        return `
                            <button class="${optionClass}" data-option="${opt.id}" ${isLocked || timer <= 0 ? 'disabled' : ''}>
                                <div class="prediction-emoji">${opt.emoji || '&#127951;'}</div>
                                <div class="prediction-label">${opt.label}</div>
                            </button>
                        `;
                    }).join('')}
                </div>

                ${selectedOption ? `
                    <div class="prediction-locked">
                        <i class="fas fa-lock"></i> Prediction locked!
                    </div>
                ` : ''}

                <div class="panel-footer">
                    <span>XP: <b class="text-cyan">${userXp}</b> Streak: <b class="text-orange"><i class="fas fa-fire"></i> ${userStreak}</b></span>
                    <span>Accuracy: <b>${userAccuracy}%</b></span>
                </div>
            </div>
        `;
    }
}
