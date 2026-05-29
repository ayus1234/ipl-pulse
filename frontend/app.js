import wsClient from './js/websocket.js';
import ScoreCard from './components/ScoreCard.js';
import PredictionInterface from './components/PredictionInterface.js';
import Leaderboard from './components/Leaderboard.js';
import ChatBox from './components/ChatBox.js';
import UserLogin from './components/UserLogin.js';
import ToastNotification from './components/ToastNotification.js';
import PollBox from './components/PollBox.js';
import UserProfile from './components/UserProfile.js';
import DataVisualizer from './components/DataVisualizer.js';
import MatchControls from './components/MatchControls.js';
import FanPulse from './components/FanPulse.js';
import AIQuests from './components/AIQuests.js';

import Config from './js/config.js';
import store from './js/store.js';

// Application Bootstrap
const init = async () => {
    // Fetch all matches for navigation
    try {
        const [historyRes, scheduleRes] = await Promise.all([
            fetch(`${Config.API_BASE_URL.replace(/\/api$/, '')}/api/matches/history`),
            fetch(`${Config.API_BASE_URL.replace(/\/api$/, '')}/api/matches/schedule`)
        ]);
        
        let allMatches = [];
        if (historyRes.ok) {
            const history = await historyRes.json();
            // history is newest first, reverse to make it chronological
            allMatches = allMatches.concat(history.reverse());
        }
        if (scheduleRes.ok) {
            const schedule = await scheduleRes.json();
            allMatches = allMatches.concat(schedule);
        }
        
        // Find today's live/scheduled match index (Qualifier 2)
        // Default to the last match in history if no today match
        let currentIndex = allMatches.findIndex(m => m.match_id === "155398" || m.status === "live");
        if (currentIndex === -1) {
            currentIndex = allMatches.length > 0 ? allMatches.findIndex(m => m.status === "scheduled") : -1;
            if (currentIndex === -1) currentIndex = allMatches.length - 1;
        }
        
        store.setAllMatches(allMatches);
        // We do NOT set browsedMatchIndex here because -1 means "live"
    } catch (e) {
        console.error("Failed to load match schedule", e);
    }

    // LEFT COLUMN
    const scoreCard = new ScoreCard();
    scoreCard.mount(document.getElementById('score-card-container'));

    // CENTER COLUMN
    const matchControls = new MatchControls();
    matchControls.mount(document.getElementById('controls-container'));

    const predictionInterface = new PredictionInterface();
    predictionInterface.mount(document.getElementById('prediction-container'));

    const dataViz = new DataVisualizer();
    dataViz.mount(document.getElementById('chart-container'));

    // RIGHT COLUMN
    const fanPulse = new FanPulse();
    fanPulse.mount(document.getElementById('fan-pulse-container'));

    const aiQuests = new AIQuests();
    aiQuests.mount(document.getElementById('quests-container'));

    const leaderboard = new Leaderboard();
    leaderboard.mount(document.getElementById('leaderboard-container'));

    // HEADER
    const userLogin = new UserLogin();
    userLogin.mount(document.getElementById('user-login-container'));

    // GLOBAL OVERLAYS
    const toastNotif = new ToastNotification();
    toastNotif.mount(document.getElementById('toast-container'));

    const userProfile = new UserProfile();
    userProfile.mount(document.getElementById('profile-modal-container'));

    // HIDDEN MOUNTS (still functional via WebSocket)
    const chatBox = new ChatBox();
    chatBox.mount(document.getElementById('chat-container'));

    const pollBox = new PollBox();
    pollBox.mount(document.getElementById('poll-container'));

    // Connect WebSocket
    wsClient.connect();
};

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
} else {
    init();
}
