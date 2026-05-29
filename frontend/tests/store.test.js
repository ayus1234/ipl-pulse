import { describe, it } from 'node:test';
import assert from 'node:assert';
import store from '../js/store.js';

describe('Store State Management', () => {
    it('should initialize with default state', () => {
        const state = store.getState();
        assert.deepStrictEqual(state.leaderboard, []);
        assert.deepStrictEqual(state.chat, []);
        assert.deepStrictEqual(state.reactions, {});
        assert.strictEqual(state.user, null);
    });

    it('should notify listeners on state change', () => {
        let notified = false;
        const unsubscribe = store.subscribe((state) => {
            notified = true;
            assert.strictEqual(state.user.username, 'testuser');
        });

        store.setUser({ username: 'testuser' });
        assert.strictEqual(notified, true);
        
        unsubscribe();
    });

    it('should limit chat history to 200 messages', () => {
        store.setChatHistory([]);
        for (let i = 0; i < 205; i++) {
            store.addChatMessage({ text: `Message ${i}` });
        }
        
        const state = store.getState();
        assert.strictEqual(state.chat.length, 200);
        // First message should be Message 5
        assert.strictEqual(state.chat[0].text, 'Message 5');
    });
});
