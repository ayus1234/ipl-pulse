// Application State Management (Observer Pattern)

class Store {
    constructor(initialState = {}) {
        this.state = {
            user: null, // { username, team, token }
            matchState: null, // { status, team1, team2, ... }
            leaderboard: [],
            chat: [],
            reactions: {},
            poll: null,
            predictionWindow: null, // { options, timeLeft }
            crowdHype: 0,
            isAuto: true,
            interval: 8,
            quest: null,
            aiSuggestion: null, // { prediction, label, reason, confidence, phase, batsman, bowler }
            allMatches: [], // combined schedule and history
            browsedMatchIndex: -1, // -1 means live match, otherwise index in allMatches
            ...initialState
        };
        this.listeners = [];
    }

    // Subscribe to state changes
    subscribe(listener) {
        this.listeners.push(listener);
        return () => {
            this.listeners = this.listeners.filter(l => l !== listener);
        };
    }

    // Notify all listeners
    _notify() {
        this.listeners.forEach(listener => listener(this.state));
    }

    // Get current state
    getState() {
        return this.state;
    }

    // Update state (shallow merge)
    setState(newState) {
        this.state = { ...this.state, ...newState };
        this._notify();
    }

    // Actions
    setUser(user) {
        this.setState({ user });
    }

    updateMatchState(matchState) {
        this.setState({ matchState });
    }

    updateLeaderboard(leaderboard) {
        this.setState({ leaderboard });
    }

    addChatMessage(message) {
        const chat = [...this.state.chat, message];
        if (chat.length > 200) chat.shift();
        this.setState({ chat });
    }

    setChatHistory(chat) {
        this.setState({ chat });
    }

    updateReactions(reactions) {
        this.setState({ reactions });
    }

    setPredictionWindow(windowData) {
        this.setState({ predictionWindow: windowData });
    }
    
    setPoll(poll) {
        this.setState({ poll });
    }

    setCrowdHype(crowdHype) {
        this.setState({ crowdHype });
    }

    setSimulationState(isAuto, interval) {
        this.setState({ isAuto, interval });
    }

    setQuest(quest) {
        this.setState({ quest });
    }

    setAiSuggestion(aiSuggestion) {
        this.setState({ aiSuggestion });
    }

    setAllMatches(matches) {
        this.setState({ allMatches: matches });
    }

    setBrowsedMatchIndex(index) {
        this.setState({ browsedMatchIndex: index });
    }
}

const store = new Store();
export default store;

