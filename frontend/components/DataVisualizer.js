import Component from '../js/component.js';
import store from '../js/store.js';

export default class DataVisualizer extends Component {
    constructor() {
        super();
        this.state = {
            matchState: store.getState().matchState
        };

        store.subscribe((state) => {
            if (this.state.matchState !== state.matchState) {
                this.state = { ...this.state, matchState: state.matchState };
                this.updateChart();
            }
        });
    }

    bindEvents() {
        this.updateChart();
    }

    getMomentumSeries(matchState) {
        if (!matchState) return [];

        const history = Array.isArray(matchState.momentum_history)
            ? matchState.momentum_history
            : [];

        if (history.length > 0) {
            return history.slice(-24).map(value => Number(value));
        }

        const momentum = Number(matchState.momentum);
        return Number.isFinite(momentum) ? [momentum] : [];
    }

    getPointString(series) {
        if (series.length === 0) return '';
        if (series.length === 1) return `0,${100 - series[0]} 100,${100 - series[0]}`;

        return series.map((value, index) => {
            const x = (index / (series.length - 1)) * 100;
            const y = 100 - Math.max(0, Math.min(100, value));
            return `${x.toFixed(2)},${y.toFixed(2)}`;
        }).join(' ');
    }

    updateChart() {
        if (!this.element) return;

        const { matchState } = this.state;
        const series = this.getMomentumSeries(matchState);
        const points = this.getPointString(series);
        const currentMom = series.length > 0 ? Math.round(series[series.length - 1]) : 0;

        const line = this.element.querySelector('.momentum-line');
        const area = this.element.querySelector('.momentum-area');
        const dot = this.element.querySelector('.momentum-dot');
        const placeholder = this.element.querySelector('.chart-placeholder');
        const current = this.element.querySelector('.momentum-current');
        const start = this.element.querySelector('.momentum-start');

        if (line) line.setAttribute('points', points);
        if (area) {
            area.setAttribute('points', points ? `0,100 ${points} 100,100` : '');
        }
        if (dot && series.length > 0) {
            const lastPoint = points.split(' ').pop().split(',');
            dot.setAttribute('cx', lastPoint[0]);
            dot.setAttribute('cy', lastPoint[1]);
        }
        if (placeholder) {
            placeholder.classList.toggle('is-hidden', series.length > 1);
        }
        if (current) {
            current.textContent = `Current: ${currentMom}/100`;
        }
        if (start && matchState && matchState.total_balls !== undefined) {
            start.textContent = `Ball ${matchState.total_balls}`;
        }
    }

    render() {
        const { matchState } = this.state;
        const series = this.getMomentumSeries(matchState);
        const points = this.getPointString(series);
        const currentMom = series.length > 0 ? Math.round(series[series.length - 1]) : 0;
        const ballLabel = matchState && matchState.total_balls !== undefined
            ? `Ball ${matchState.total_balls}`
            : 'Match Start';

        return `
            <div class="panel panel-subtle chart-panel">
                <div class="panel-header">
                    <div class="panel-title purple">
                        <i class="fas fa-chart-line"></i> Momentum Graph
                    </div>
                    <div class="chart-legend">
                        <span class="legend-item"><span class="legend-dot six"></span> Batting swing</span>
                        <span class="legend-item"><span class="legend-dot four"></span> Boundary</span>
                        <span class="legend-item"><span class="legend-dot wicket"></span> Wicket</span>
                    </div>
                </div>

                <div class="chart-area">
                    <div class="chart-axis">
                        <span>Batting up</span>
                        <span>50</span>
                        <span>Bowling down</span>
                    </div>
                    <div class="chart-container">
                        <svg class="momentum-svg" viewBox="0 0 100 100" preserveAspectRatio="none" role="img" aria-label="Momentum trend">
                            <line class="momentum-grid-line" x1="0" x2="100" y1="20" y2="20"></line>
                            <line class="momentum-grid-line" x1="0" x2="100" y1="40" y2="40"></line>
                            <line class="momentum-midline" x1="0" x2="100" y1="50" y2="50"></line>
                            <line class="momentum-grid-line" x1="0" x2="100" y1="60" y2="60"></line>
                            <line class="momentum-grid-line" x1="0" x2="100" y1="80" y2="80"></line>
                            <polygon class="momentum-area" points="${points ? `0,100 ${points} 100,100` : ''}"></polygon>
                            <polyline class="momentum-line" points="${points}"></polyline>
                            <circle class="momentum-dot" cx="0" cy="${100 - currentMom}" r="1.6"></circle>
                        </svg>
                        <div class="chart-placeholder ${series.length > 1 ? 'is-hidden' : ''}">Momentum graph builds ball by ball...</div>
                    </div>
                </div>

                <div class="panel-footer">
                    <span class="momentum-start">${ballLabel}</span>
                    <span class="text-cyan momentum-current">Current: ${currentMom}/100</span>
                </div>
            </div>
        `;
    }
}
