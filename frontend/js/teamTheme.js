/**
 * IPL Team Theme System
 * Official team colors for all 10 IPL teams.
 * When two teams are playing, their colors are applied dynamically
 * to CSS custom properties on :root so the entire UI adapts.
 *
 * Each team has:
 *   primary   – official brand color (used for crest badge backgrounds)
 *   display   – bright/readable variant for TEXT on dark backgrounds
 *   secondary – complementary accent color
 *   text      – text color ON the primary background (for crest text)
 *   probBar   – color for the win probability bar fill
 */

const TEAM_COLORS = {
    CSK: {
        name: 'Chennai Super Kings',
        primary: '#F9CD05',
        display: '#FFD72F',       // bright yellow — readable on dark
        secondary: '#1D418C',
        text: '#0a0a0a',
        probBar: '#F9CD05',
        gradient: 'linear-gradient(135deg, #F9CD05, #e6b800)',
        bg: 'rgba(249, 205, 5, 0.12)',
        border: 'rgba(249, 205, 5, 0.35)',
        glow: 'rgba(249, 205, 5, 0.15)',
    },
    MI: {
        name: 'Mumbai Indians',
        primary: '#004BA0',
        display: '#4A9FE5',       // bright sky blue — readable on dark
        secondary: '#FFD141',
        text: '#ffffff',
        probBar: '#2080D0',
        gradient: 'linear-gradient(135deg, #4A9FE5, #2080D0)',
        bg: 'rgba(0, 75, 160, 0.12)',
        border: 'rgba(74, 159, 229, 0.35)',
        glow: 'rgba(74, 159, 229, 0.15)',
    },
    RCB: {
        name: 'Royal Challengers Bengaluru',
        primary: '#EC1C24',
        display: '#FF4048',       // bright red — already readable
        secondary: '#2B2A29',
        text: '#ffffff',
        probBar: '#EC1C24',
        gradient: 'linear-gradient(135deg, #FF4048, #EC1C24)',
        bg: 'rgba(236, 28, 36, 0.12)',
        border: 'rgba(255, 64, 72, 0.35)',
        glow: 'rgba(255, 64, 72, 0.15)',
    },
    KKR: {
        name: 'Kolkata Knight Riders',
        primary: '#3A225D',
        display: '#A87CE0',       // bright lavender purple — very readable
        secondary: '#F2C028',
        text: '#ffffff',
        probBar: '#7B52B5',
        gradient: 'linear-gradient(135deg, #A87CE0, #7B52B5)',
        bg: 'rgba(168, 124, 224, 0.12)',
        border: 'rgba(168, 124, 224, 0.35)',
        glow: 'rgba(168, 124, 224, 0.15)',
    },
    SRH: {
        name: 'Sunrisers Hyderabad',
        primary: '#FF6600',
        display: '#FF8533',       // bright orange — already readable
        secondary: '#221F21',
        text: '#ffffff',
        probBar: '#FF6600',
        gradient: 'linear-gradient(135deg, #FF8533, #FF6600)',
        bg: 'rgba(255, 102, 0, 0.12)',
        border: 'rgba(255, 133, 51, 0.35)',
        glow: 'rgba(255, 133, 51, 0.15)',
    },
    DC: {
        name: 'Delhi Capitals',
        primary: '#2561AE',
        display: '#5A9AE0',       // bright blue — readable on dark
        secondary: '#D71921',
        text: '#ffffff',
        probBar: '#3578CC',
        gradient: 'linear-gradient(135deg, #5A9AE0, #3578CC)',
        bg: 'rgba(90, 154, 224, 0.12)',
        border: 'rgba(90, 154, 224, 0.35)',
        glow: 'rgba(90, 154, 224, 0.15)',
    },
    PBKS: {
        name: 'Punjab Kings',
        primary: '#DD1F2D',
        display: '#FF4550',       // bright red — already readable
        secondary: '#F2D1A0',
        text: '#ffffff',
        probBar: '#DD1F2D',
        gradient: 'linear-gradient(135deg, #FF4550, #DD1F2D)',
        bg: 'rgba(255, 69, 80, 0.12)',
        border: 'rgba(255, 69, 80, 0.35)',
        glow: 'rgba(255, 69, 80, 0.15)',
    },
    RR: {
        name: 'Rajasthan Royals',
        primary: '#EA1A85',
        display: '#FF4DA6',       // bright pink — already readable
        secondary: '#074EA2',
        text: '#ffffff',
        probBar: '#EA1A85',
        gradient: 'linear-gradient(135deg, #FF4DA6, #EA1A85)',
        bg: 'rgba(255, 77, 166, 0.12)',
        border: 'rgba(255, 77, 166, 0.35)',
        glow: 'rgba(255, 77, 166, 0.15)',
    },
    GT: {
        name: 'Gujarat Titans',
        primary: '#1B2133',       // distinct slate navy
        display: '#00E5FF',       // cyan / teal (highly readable)
        secondary: '#00B4CC',
        text: '#00E5FF',          // cyan text for crest
        probBar: '#00E5FF',
        probText: '#0a0a0a',      // dark text for the cyan prob bar
        gradient: 'linear-gradient(135deg, #24304D, #161D2E)', // Much lighter slate blue, distinctly not black
        bg: 'rgba(0, 229, 255, 0.12)',
        border: 'rgba(0, 229, 255, 0.35)',
        glow: 'rgba(0, 229, 255, 0.15)',
    },
    LSG: {
        name: 'Lucknow Super Giants',
        primary: '#A72056',       // deep burgundy
        display: '#FF82A9',       // bright pinkish-red
        secondary: '#C22B69',
        text: '#ffffff',
        probBar: '#A72056',
        gradient: 'linear-gradient(135deg, #A72056, #631233)',
        bg: 'rgba(167, 32, 86, 0.12)',
        border: 'rgba(167, 32, 86, 0.35)',
        glow: 'rgba(167, 32, 86, 0.15)',
    },
};

/** Current active teams (so we can query from anywhere) */
let _activeTeam1 = null;
let _activeTeam2 = null;

/**
 * Apply team theme colors as CSS custom properties on :root.
 * Call this whenever the playing teams change.
 * @param {string} team1Code - e.g. 'CSK'
 * @param {string} team2Code - e.g. 'MI'
 */
function applyTeamTheme(team1Code, team2Code) {
    const t1 = TEAM_COLORS[team1Code];
    const t2 = TEAM_COLORS[team2Code];
    if (!t1 || !t2) return;

    // Don't re-apply if same teams
    if (_activeTeam1 === team1Code && _activeTeam2 === team2Code) return;
    _activeTeam1 = team1Code;
    _activeTeam2 = team2Code;

    const root = document.documentElement;

    // Team 1 (batting first) colors
    root.style.setProperty('--team-1-primary', t1.primary);
    root.style.setProperty('--team-1-display', t1.display);
    root.style.setProperty('--team-1-secondary', t1.secondary);
    root.style.setProperty('--team-1-text', t1.text);
    root.style.setProperty('--team-1-gradient', t1.gradient);
    root.style.setProperty('--team-1-bg', t1.bg);
    root.style.setProperty('--team-1-border', t1.border);
    root.style.setProperty('--team-1-glow', t1.glow);

    // Team 2 (batting second) colors
    root.style.setProperty('--team-2-primary', t2.primary);
    root.style.setProperty('--team-2-display', t2.display);
    root.style.setProperty('--team-2-secondary', t2.secondary);
    root.style.setProperty('--team-2-text', t2.text);
    root.style.setProperty('--team-2-gradient', t2.gradient);
    root.style.setProperty('--team-2-bg', t2.bg);
    root.style.setProperty('--team-2-border', t2.border);
    root.style.setProperty('--team-2-glow', t2.glow);

    // Override global accents to blend with the match
    root.style.setProperty('--team-1', t1.display);
    root.style.setProperty('--team-2', t2.display);

    // Scorecard accent gradient (blends both teams)
    root.style.setProperty('--match-gradient',
        `linear-gradient(135deg, ${t1.display}18, transparent 40%, ${t2.display}18)`
    );

    console.log(`[TeamTheme] Applied: ${team1Code} vs ${team2Code}`);
}

/**
 * Get colors for a specific team code.
 * @param {string} teamCode - e.g. 'KKR'
 * @returns {object|null}
 */
function getTeamColors(teamCode) {
    return TEAM_COLORS[teamCode] || null;
}

/**
 * Get currently active team codes.
 * @returns {{ team1: string|null, team2: string|null }}
 */
function getActiveTeams() {
    return { team1: _activeTeam1, team2: _activeTeam2 };
}

export { TEAM_COLORS, applyTeamTheme, getTeamColors, getActiveTeams };
export default { TEAM_COLORS, applyTeamTheme, getTeamColors, getActiveTeams };

