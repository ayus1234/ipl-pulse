import { describe, it, beforeEach, mock } from 'node:test';
import assert from 'node:assert';
import { JSDOM } from 'jsdom';

// Setup DOM environment
const dom = new JSDOM(`<!DOCTYPE html><html><body><div id="root"></div></body></html>`);
global.document = dom.window.document;
global.window = dom.window;
global.HTMLElement = dom.window.HTMLElement;

// Mock the WebSocket and Store before importing components
import store from '../js/store.js';
import wsClient from '../js/websocket.js';

import ScoreCard from '../components/ScoreCard.js';
import PredictionInterface from '../components/PredictionInterface.js';
import DataVisualizer from '../components/DataVisualizer.js';
import AIQuests from '../components/AIQuests.js';

describe('UI Components', () => {
    beforeEach(() => {
        document.getElementById('root').innerHTML = '';
        store.state = {
            matchState: null,
            predictionWindow: null,
            user: null,
            leaderboard: [],
            quest: null
        };
        // Reset mocks
        wsClient.send = mock.fn();
    });

    // Task 20.1: UI state reflection
    it('ScoreCard should reflect match state changes', () => {
        const scoreCard = new ScoreCard();
        scoreCard.mount(document.getElementById('root'));
        
        // Initial state
        assert.ok(scoreCard.element.innerHTML.includes('Waiting for match data'));
        
        // Update state
        store.updateMatchState({
            team1: 'CSK',
            team2: 'MI',
            total_score: 120,
            wickets: 3,
            overs: 12.4,
            current_run_rate: 9.6,
            target: 0,
            match_status: 'live',
            current_batsmen: ['Dhoni', 'Jadeja'],
            current_bowler: 'Bumrah'
        });
        
        // Ensure UI reflects the new state
        const html = scoreCard.element.innerHTML;
        assert.ok(html.includes('120/3'));
        assert.ok(html.includes('Overs: 12.4'));
        assert.ok(html.includes('Dhoni'));
        assert.ok(html.includes('Bumrah'));
        assert.ok(html.includes('CSK'));
    });

    // Task 21.1: Countdown timer state
    it('PredictionInterface should handle countdown timer', async () => {
        const interface_ui = new PredictionInterface();
        interface_ui.mount(document.getElementById('root'));
        
        store.setUser({ username: 'testuser', team: 'CSK' });
        
        // Start window
        store.setPredictionWindow({
            options: [{ id: 'dot', label: 'Dot Ball', xp: 10 }],
            timeLeft: 3
        });
        
        assert.strictEqual(interface_ui.state.timer, 3);
        
        // Wait 1.1 seconds for timer to tick
        await new Promise(r => setTimeout(r, 1100));
        assert.strictEqual(interface_ui.state.timer, 2);
        
        // Close window
        store.setPredictionWindow(null);
        assert.strictEqual(interface_ui.timerInterval, null);
    });

    // Task 21.2: Prediction submission state
    it('PredictionInterface should lock state after submission', () => {
        const interface_ui = new PredictionInterface();
        interface_ui.mount(document.getElementById('root'));
        
        store.setUser({ username: 'testuser', team: 'CSK' });
        store.setPredictionWindow({
            options: [{ id: 'six', label: 'Six', xp: 50 }],
            timeLeft: 10
        });
        
        // Submit prediction
        interface_ui.submitPrediction('six');
        
        // Verify state is locked
        assert.strictEqual(interface_ui.state.selectedOption, 'six');
        assert.strictEqual(wsClient.send.mock.calls.length, 1);
        assert.deepStrictEqual(wsClient.send.mock.calls[0].arguments[0], {
            type: 'predict',
            prediction: 'six'
        });
        
        // Ensure UI shows locked message
        const html = interface_ui.element.innerHTML;
        assert.ok(html.includes('Prediction locked!'));
        
        // Submit again should be ignored
        interface_ui.submitPrediction('four');
        assert.strictEqual(interface_ui.state.selectedOption, 'six'); // still six
        assert.strictEqual(wsClient.send.mock.calls.length, 1); // Not called again
    });

    it('DataVisualizer should update momentum for each ball', () => {
        const dataViz = new DataVisualizer();
        dataViz.mount(document.getElementById('root'));

        store.updateMatchState({
            total_balls: 1,
            momentum: 48,
            momentum_history: [48]
        });

        const firstPoints = dataViz.element.querySelector('.momentum-line').getAttribute('points');
        assert.ok(dataViz.element.innerHTML.includes('Current: 48/100'));

        store.updateMatchState({
            total_balls: 2,
            momentum: 56,
            momentum_history: [48, 56]
        });

        const secondPoints = dataViz.element.querySelector('.momentum-line').getAttribute('points');
        assert.notStrictEqual(firstPoints, secondPoints);
        assert.ok(dataViz.element.innerHTML.includes('Current: 56/100'));
        assert.ok(dataViz.element.innerHTML.includes('Ball 2'));
    });

    it('AIQuests should request and render generated quests', () => {
        const quests = new AIQuests();
        quests.mount(document.getElementById('root'));

        store.setUser({ username: 'testuser', team: 'CSK' });

        const generateBtn = quests.element.querySelector('.generate-quest-btn');
        generateBtn.click();

        assert.strictEqual(wsClient.send.mock.calls.length, 1);
        assert.deepStrictEqual(wsClient.send.mock.calls[0].arguments[0], {
            type: 'generate_quest'
        });
        assert.ok(quests.element.innerHTML.includes('Generating Quest...'));

        store.setQuest({
            id: 'dot_ball',
            label: 'Predict a Dot Ball on the next delivery!',
            reward: 30
        });

        assert.ok(quests.element.innerHTML.includes('Active Quest'));
        assert.ok(quests.element.innerHTML.includes('Predict a Dot Ball'));
    });
});
