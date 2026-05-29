import Component from '../js/component.js';
import store from '../js/store.js';
import { applyTeamTheme, getTeamColors } from '../js/teamTheme.js';

export default class ScoreCard extends Component {
    constructor() {
        super();
        this.state = {
            matchState: store.getState().matchState,
            allMatches: store.getState().allMatches,
            browsedMatchIndex: store.getState().browsedMatchIndex
        };

        store.subscribe((state) => {
            let shouldUpdate = false;
            let nextState = {};
            
            if (JSON.stringify(this.state.matchState) !== JSON.stringify(state.matchState)) {
                shouldUpdate = true;
                nextState.matchState = state.matchState;
            }
            if (this.state.browsedMatchIndex !== state.browsedMatchIndex) {
                shouldUpdate = true;
                nextState.browsedMatchIndex = state.browsedMatchIndex;
            }
            if (this.state.allMatches !== state.allMatches) {
                shouldUpdate = true;
                nextState.allMatches = state.allMatches;
            }
            
            if (shouldUpdate) {
                this.setState(nextState);
            }
        });
    }

    bindEvents() {
        if (!this.element) return;
        
        const prevBtn = this.element.querySelector('.btn-prev-match');
        const nextBtn = this.element.querySelector('.btn-next-match');
        const todayBtn = this.element.querySelector('.btn-today-match');
        
        if (prevBtn) {
            prevBtn.addEventListener('click', () => {
                let { browsedMatchIndex, allMatches } = this.state;
                if (browsedMatchIndex === -1 && allMatches.length > 0) {
                    // Find today's match index first
                    browsedMatchIndex = allMatches.findIndex(m => m.match_id === "155398" || m.status === "live");
                    if (browsedMatchIndex === -1) browsedMatchIndex = allMatches.length - 1;
                }
                if (browsedMatchIndex > 0) {
                    store.setBrowsedMatchIndex(browsedMatchIndex - 1);
                }
            });
        }
        
        if (nextBtn) {
            nextBtn.addEventListener('click', () => {
                let { browsedMatchIndex, allMatches } = this.state;
                if (browsedMatchIndex === -1 && allMatches.length > 0) {
                    browsedMatchIndex = allMatches.findIndex(m => m.match_id === "155398" || m.status === "live");
                    if (browsedMatchIndex === -1) browsedMatchIndex = allMatches.length - 1;
                }
                if (browsedMatchIndex < allMatches.length - 1) {
                    store.setBrowsedMatchIndex(browsedMatchIndex + 1);
                }
            });
        }
        
        if (todayBtn) {
            todayBtn.addEventListener('click', () => {
                store.setBrowsedMatchIndex(-1); // Back to live WebSocket data
            });
        }
    }

    renderBallPill(result) {
        let ballClass = 'ball-pill';
        if (result === 'W') ballClass += ' wicket';
        else if (result === '4' || result === '6') ballClass += ' boundary';
        else if (result !== '-') ballClass += ' run';

        return `<div class="${ballClass}">${result}</div>`;
    }

    render() {
        let { matchState, allMatches, browsedMatchIndex } = this.state;
        let isBrowsing = false;
        
        if (browsedMatchIndex !== -1 && allMatches && allMatches.length > 0) {
            const match = allMatches[browsedMatchIndex];
            isBrowsing = true;
            // Mock a matchState structure for past/future matches based on DB data
            matchState = {
                team1: match.team1,
                team2: match.team2,
                total_score: match.final_score_team1 ? parseInt(match.final_score_team1.split('/')[0]) : 0,
                wickets: match.final_score_team1 ? parseInt(match.final_score_team1.split('/')[1] || '10') : 0,
                overs: match.status === 'completed' ? 20.0 : 0.0,
                match_status: match.status,
                target: match.final_score_team1 ? parseInt(match.final_score_team1.split('/')[0]) + 1 : 0,
                innings: match.status === 'completed' ? 2 : 1,
                total_balls: match.status === 'completed' ? 120 : 0,
                batting_team: match.team2,
                bowling_team: match.team1,
                match_date: match.match_date,
                winner: match.winner
            };
            if (match.status === 'completed') {
                matchState.team1_final_score = match.final_score_team1;
                matchState.team2_final_score = match.final_score_team2;
            }
        }

        if (!matchState) {
            return `<div class="panel text-center text-muted">Waiting for match data</div>`;
        }

        const {
            team1 = 'CSK',
            team2 = 'MI',
            score,
            total_score,
            wickets,
            overs,
            current_run_rate,
            required_run_rate,
            target,
            match_status,
            current_bowler,
            current_batsman,
            current_batsmen,
            non_striker,
            batsman_runs,
            batsman_balls,
            last_six_balls,
            phase,
            pressure_on,
            innings = 1,
            total_balls,
            win_prob_team1,
            win_prob_team2,
            momentum,
            match_date,
            winner,
            team1_final_score,
            team2_final_score
        } = matchState;

        // Apply team theme colors globally
        applyTeamTheme(team1, team2);

        // Get individual team colors for inline styling
        const t1Colors = getTeamColors(team1);
        const t2Colors = getTeamColors(team2);

        const displayScore = score !== undefined ? score : (total_score || 0);
        const displayWickets = wickets !== undefined ? wickets : 0;
        const displayOvers = overs !== undefined ? overs : '0.0';
        const battingTeam = matchState.batting_team || (innings === 2 ? team2 : team1);
        const bowlingTeam = matchState.bowling_team || (innings === 2 ? team1 : team2);
        const ballsRemaining = total_balls !== undefined ? Math.max(0, 120 - Number(total_balls)) : 120;
        const runsNeeded = innings === 2 && target ? Math.max(0, target - displayScore) : '-';
        const crr = Number(current_run_rate || matchState.run_rate || 0).toFixed(2);
        const rrrValue = Number(required_run_rate || matchState.required_rate || 0).toFixed(2);
        const last6 = Array.isArray(last_six_balls) && last_six_balls.length > 0
            ? last_six_balls.slice(-6)
            : ['-', '-', '-', '-', '-', '-'];
        const team1Prob = win_prob_team1 !== undefined ? win_prob_team1 : 50;
        const team2Prob = win_prob_team2 !== undefined ? win_prob_team2 : 50;
        const activeBatsmen = Array.isArray(current_batsmen) && current_batsmen.length > 0
            ? current_batsmen
            : [current_batsman, non_striker].filter(Boolean);
        const striker = current_batsman || activeBatsmen[0] || 'Yet to bat';
        const partner = activeBatsmen.find(name => name !== striker) || non_striker || '';
        const team1Score = isBrowsing && match_status === 'completed' && team1_final_score ? team1_final_score : (innings === 1 ? `${displayScore}/${displayWickets}` : (target ? `${target - 1}` : '0/0'));
        const team2Score = isBrowsing && match_status === 'completed' && team2_final_score ? team2_final_score : (innings === 2 ? `${displayScore}/${displayWickets}` : '0/0');

        // Team-specific inline colors
        // 'display' = bright readable text on dark bg, 'primary' = crest badge bg, 'probBar' = bar fill
        const t1Display = t1Colors ? t1Colors.display : 'var(--gold)';
        const t1Primary = t1Colors ? t1Colors.primary : '#F9CD05';
        const t1Gradient = t1Colors ? t1Colors.gradient : 'linear-gradient(135deg, #F9CD05, #e6b800)';
        const t1Text = t1Colors ? t1Colors.text : '#0a0a0a';
        const t1ProbBar = t1Colors ? t1Colors.probBar : t1Primary;
        const t1ProbText = t1Colors && t1Colors.probText ? t1Colors.probText : t1Text;
        
        const t2Display = t2Colors ? t2Colors.display : 'var(--sky)';
        const t2Primary = t2Colors ? t2Colors.primary : '#004BA0';
        const t2Gradient = t2Colors ? t2Colors.gradient : 'linear-gradient(135deg, #004BA0, #0066cc)';
        const t2Text = t2Colors ? t2Colors.text : '#ffffff';
        const t2ProbBar = t2Colors ? t2Colors.probBar : t2Primary;
        const t2ProbText = t2Colors && t2Colors.probText ? t2Colors.probText : t2Text;

        return `
            <div class="panel score-hero" style="background: linear-gradient(145deg, ${t1Display}0C, transparent 38%), linear-gradient(225deg, ${t2Display}0C, transparent 38%), linear-gradient(180deg, #101936, #121d3d 50%, #0d152c);">
                <div class="score-hero-body">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                        <button class="btn btn-sm btn-grey btn-prev-match" style="background: rgba(255,255,255,0.1); border:none; padding: 4px 10px; border-radius: 4px;" ${browsedMatchIndex === 0 ? 'disabled' : ''}><i class="fas fa-chevron-left"></i> Prev</button>
                        ${isBrowsing ? `<button class="btn btn-sm btn-cyan btn-today-match" style="padding: 4px 10px;">Back to Live</button>` : ''}
                        <button class="btn btn-sm btn-grey btn-next-match" style="background: rgba(255,255,255,0.1); border:none; padding: 4px 10px; border-radius: 4px;" ${allMatches && browsedMatchIndex === allMatches.length - 1 ? 'disabled' : ''}>Next <i class="fas fa-chevron-right"></i></button>
                    </div>
                    <div class="score-meta">
                        <div>
                            <div class="score-meta-title" style="color: ${t1Display};">IPL Match Centre ${match_date ? '(' + match_date + ')' : ''}</div>
                            <div class="team-name">${team1} vs ${team2}</div>
                            ${winner ? `<div style="font-size: 0.8rem; color: var(--gold); margin-top: 4px;"><i class="fas fa-trophy"></i> ${winner} won</div>` : ''}
                        </div>
                        <div class="live-pill" style="${isBrowsing ? 'background: rgba(255,255,255,0.1); color: #ccc;' : ''}">
                            <span class="dot" style="${isBrowsing ? 'background: #ccc;' : ''}"></span> ${String(match_status || 'scheduled').toUpperCase()}
                        </div>
                    </div>

                    <div class="team-scoreboard">
                        <div class="team-score" style="border-color: ${t1Display}30;">
                            <div class="team-label-row">
                                <div class="team-crest" style="background: ${t1Gradient}; color: ${t1Text}; border: 1px solid rgba(255,255,255,0.15); box-shadow: 0 4px 10px rgba(0,0,0,0.3);">${team1}</div>
                                <div>
                                    <div class="team-name" style="color: ${t1Display};">${team1}</div>
                                    <div class="team-score-sub">${innings === 1 ? 'Batting' : 'First innings'}</div>
                                </div>
                            </div>
                            <div class="team-score-value" style="color: ${t1Display};">${team1Score}</div>
                            <div class="team-score-sub">${innings === 1 ? `Overs: ${displayOvers}` : '20.0 ov'}</div>
                        </div>

                        <div class="vs-pill">VS</div>

                        <div class="team-score right" style="border-color: ${t2Display}30;">
                            <div class="team-label-row">
                                <div>
                                    <div class="team-name" style="color: ${t2Display};">${team2}</div>
                                    <div class="team-score-sub">${innings === 2 ? 'Chasing' : 'Yet to bat'}</div>
                                </div>
                                <div class="team-crest" style="background: ${t2Gradient}; color: ${t2Text}; border: 1px solid rgba(255,255,255,0.15); box-shadow: 0 4px 10px rgba(0,0,0,0.3);">${team2}</div>
                            </div>
                            <div class="team-score-value" style="color: ${t2Display};">${team2Score}</div>
                            <div class="team-score-sub">${innings === 2 ? `Overs: ${displayOvers}` : '0.0 ov'}</div>
                        </div>
                    </div>

                    <div class="innings-line">
                        <div>${battingTeam}: ${displayScore}/${displayWickets}</div>
                        <span>Overs: ${displayOvers}</span>
                    </div>

                    <div class="metric-grid">
                        <div class="metric-tile">
                            <div class="metric-label">Need</div>
                            <div class="metric-value" style="color: ${t2Display};">${runsNeeded}</div>
                            <div class="metric-note">runs</div>
                        </div>
                        <div class="metric-tile">
                            <div class="metric-label">From</div>
                            <div class="metric-value" style="color: ${t1Display};">${innings === 2 ? ballsRemaining : total_balls || 0}</div>
                            <div class="metric-note">balls</div>
                        </div>
                        <div class="metric-tile">
                            <div class="metric-label">CRR</div>
                            <div class="metric-value">${crr}</div>
                        </div>
                        <div class="metric-tile">
                            <div class="metric-label">RRR</div>
                            <div class="metric-value text-green">${innings === 2 ? rrrValue : '-'}</div>
                        </div>
                    </div>

                    <div class="player-grid">
                        <div class="player-card" style="border-left: 3px solid ${t1Display}60;">
                            <div class="player-role" style="color: ${t1Display};"><i class="fas fa-cricket-bat-ball"></i> Batting</div>
                            <div class="player-name">${striker}</div>
                            <div class="player-note">${batsman_runs || 0} (${batsman_balls || 0})${partner ? ` with ${partner}` : ''}</div>
                        </div>
                        <div class="player-card" style="border-left: 3px solid ${t2Display}60;">
                            <div class="player-role bowler" style="color: ${t2Display};"><i class="fas fa-baseball"></i> Bowling</div>
                            <div class="player-name">${current_bowler || 'Bowler pending'}</div>
                            <div class="player-note">${bowlingTeam} attack</div>
                        </div>
                    </div>

                    <div class="ball-strip">
                        <div class="section-label">Last 6 balls</div>
                        <div class="ball-row">
                            ${last6.map(result => this.renderBallPill(result)).join('')}
                        </div>
                    </div>

                    <div class="win-panel">
                        <div class="section-label">Win probability</div>
                        <div class="prob-row">
                            <span style="color: ${t1Display};">${team1}</span>
                            <span style="color: ${t2Display};">${team2}</span>
                        </div>
                        <div class="prob-bar">
                            <div class="prob-a" style="width:${team1Prob}%; background: ${t1ProbBar}; color: ${t1ProbText};">${Math.round(team1Prob)}%</div>
                            <div class="prob-b" style="width:${team2Prob}%; background: ${t2ProbBar}; color: ${t2ProbText};">${Math.round(team2Prob)}%</div>
                        </div>
                        <div class="score-foot">
                            <span>Momentum ${momentum || 50}</span>
                            <span>${pressure_on ? 'Pressure' : 'Normal'}</span>
                            <span>${phase || '-'}</span>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }
}

