import { describe, it, beforeEach, mock } from 'node:test';
import assert from 'node:assert';
import { JSDOM } from 'jsdom';

// Setup DOM environment
const dom = new JSDOM(`<!DOCTYPE html><html><body>
    <div id="user-login-container"></div>
    <div id="chart-container"></div>
    <div id="poll-container"></div>
    <div id="profile-modal-container"></div>
    <div id="toast-container"></div>
</body></html>`);
global.document = dom.window.document;
global.window = dom.window;
global.HTMLElement = dom.window.HTMLElement;

// Mock the WebSocket and Store before importing components
import store from '../js/store.js';
import wsClient from '../js/websocket.js';

import UserLogin from '../components/UserLogin.js';
import PollBox from '../components/PollBox.js';
import ToastNotification from '../components/ToastNotification.js';
import UserProfile from '../components/UserProfile.js';
import DataVisualizer from '../components/DataVisualizer.js';

describe('E2E Integration Flows', () => {
    beforeEach(() => {
        [
            'user-login-container',
            'chart-container',
            'poll-container',
            'profile-modal-container',
            'toast-container'
        ].forEach(id => {
            document.getElementById(id).innerHTML = '';
        });

        // Reset Store
        store.state = {
            matchState: null,
            predictionWindow: null,
            user: null,
            poll: null,
            leaderboard: []
        };
        // Reset mocks
        wsClient.send = mock.fn();
        global.fetch = undefined;
    });

    it('Should handle user login to poll voting flow', async () => {
        // Mount Toast Notifier
        const toastNotif = new ToastNotification();
        toastNotif.mount(document.getElementById('toast-container'));
        
        // Mount Login
        const userLogin = new UserLogin();
        userLogin.mount(document.getElementById('user-login-container'));
        
        // Mount Poll
        const pollBox = new PollBox();
        pollBox.mount(document.getElementById('poll-container'));
        
        // Simulate WebSocket incoming Poll
        store.setPoll({
            poll_id: 'poll-123',
            question: 'Who will win this match?',
            options: [
                { id: 'csk', label: 'CSK' },
                { id: 'mi', label: 'MI' }
            ],
            results: { csk: 10, mi: 5 }
        });
        
        // Before login, poll should be disabled and ask for auth
        assert.ok(pollBox.element.innerHTML.includes('Log in to vote!'));
        
        // User logs in
        userLogin.login('TestFan', 'CSK');
        
        // Verify User updated in store and websocket join was sent
        assert.strictEqual(store.getState().user.username, 'TestFan');
        assert.strictEqual(store.getState().user.isGuest, true);
        assert.ok(store.getState().user.user_id);
        assert.strictEqual(wsClient.send.mock.calls.length, 1);
        
        // Poll should now be unlocked (no 'Log in to vote' message)
        assert.strictEqual(pollBox.element.innerHTML.includes('Log in to vote!'), false);
        
        // Mock fetch for Poll Submission
        global.fetch = mock.fn(async () => ({ ok: true }));
        
        // Submit Vote
        await pollBox.submitVote('csk');
        
        // Verify Vote was sent via API
        assert.strictEqual(global.fetch.mock.calls.length, 1);
        assert.ok(global.fetch.mock.calls[0].arguments[0].includes('/polls/poll-123/respond'));
        
        // Verify UI states: Voted
        assert.strictEqual(pollBox.state.votedOption, 'csk');
        
        // Verify Toast was shown
        assert.strictEqual(toastNotif.state.toasts.length, 1);
        assert.strictEqual(toastNotif.state.toasts[0].message, 'Vote submitted successfully!');
    });

    it('Should handle backend string poll options for guest voters', async () => {
        const pollBox = new PollBox();
        pollBox.mount(document.getElementById('poll-container'));

        store.setUser({
            username: 'GuestFan',
            team: 'CSK',
            user_id: '00000000-0000-0000-0000-000000000001',
            isGuest: true
        });
        store.setPoll({
            poll_id: 'poll-strings',
            question: 'Who wins?',
            options: ['CSK', 'MI'],
            results: { CSK: 1, MI: 0 }
        });

        assert.ok(pollBox.element.innerHTML.includes('CSK'));
        assert.ok(pollBox.element.innerHTML.includes('MI'));

        global.fetch = mock.fn(async () => ({ ok: true }));
        await pollBox.submitVote('CSK');

        const request = global.fetch.mock.calls[0].arguments;
        assert.ok(request[0].includes('/polls/poll-strings/respond'));
        assert.deepStrictEqual(JSON.parse(request[1].body), {
            user_id: '00000000-0000-0000-0000-000000000001',
            selected_option: 'CSK'
        });
    });
    
    it('Should toggle User Profile Modal', () => {
        const userProfile = new UserProfile();
        userProfile.mount(document.getElementById('profile-modal-container'));
        
        global.fetch = mock.fn(async () => ({ 
            ok: true, 
            json: async () => ({ total_xp: 500, achievements: [] }) 
        }));
        
        store.setUser({ username: 'Admin', team: 'MI', user_id: '123' });
        
        // Ensure closed initially
        assert.strictEqual(userProfile.state.isOpen, false);
        assert.ok(userProfile.element.outerHTML.includes('display:none'));
        
        // Toggle Open
        userProfile.toggle();
        
        assert.strictEqual(userProfile.state.isOpen, true);
        assert.ok(global.fetch.mock.calls.length >= 1); // should fetch profile data
    });

    it('Should open guest profile from leaderboard without backend fetch', () => {
        const userProfile = new UserProfile();
        userProfile.mount(document.getElementById('profile-modal-container'));

        global.fetch = mock.fn(async () => ({ ok: true }));
        store.updateLeaderboard([{
            username: 'GuestFan',
            team: 'CSK',
            xp: 42,
            streak: 3,
            correct: 2,
            total: 4
        }]);
        store.setUser({
            username: 'GuestFan',
            team: 'CSK',
            user_id: '00000000-0000-0000-0000-000000000001',
            isGuest: true
        });

        userProfile.toggle();

        assert.strictEqual(userProfile.state.isOpen, true);
        assert.strictEqual(global.fetch.mock.calls.length, 0);
        assert.strictEqual(userProfile.state.profileData.total_xp, 42);
        assert.strictEqual(userProfile.state.profileData.accuracy, 50);
    });
});
