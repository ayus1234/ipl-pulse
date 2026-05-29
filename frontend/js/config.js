// Configuration module

// Configuration module

const isLocalhost = typeof window !== 'undefined' && 
    (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1');

const API_BASE_URL = typeof window !== 'undefined' 
    ? `http://${window.location.host}/api`
    : 'http://127.0.0.1:8081/api';

const WS_BASE_URL = typeof window !== 'undefined' 
    ? `ws://${window.location.host}/ws` 
    : 'ws://127.0.0.1:8081/ws';

const Config = {
    API_BASE_URL,
    WS_BASE_URL,
    
    // Application settings
    REFRESH_INTERVALS: {
        LEADERBOARD: 30000, // 30s
        STATS: 60000 // 60s
    },
    
    // Feature flags
    FEATURES: {
        CHAT: true,
        POLLS: true,
        ACHIEVEMENTS: true
    }
};

export default Config;
