import { describe, it, beforeEach } from 'node:test';
import assert from 'node:assert';
import storage from '../js/storage.js';

// Mock localStorage for Node.js environment
global.localStorage = {
    _data: {},
    getItem(key) { return this._data[key] || null; },
    setItem(key, value) { this._data[key] = String(value); },
    removeItem(key) { delete this._data[key]; },
    get length() { return Object.keys(this._data).length; },
    key(i) { return Object.keys(this._data)[i]; },
    clear() { this._data = {}; }
};

describe('Storage Wrapper', () => {
    beforeEach(() => {
        global.localStorage.clear();
    });

    it('should set and get values correctly', () => {
        const success = storage.set('test_key', { a: 1, b: 'two' });
        assert.strictEqual(success, true);
        
        const retrieved = storage.get('test_key');
        assert.deepStrictEqual(retrieved, { a: 1, b: 'two' });
        
        // Check prefix is actually used
        assert.ok(global.localStorage.getItem('ipl_pulse_test_key'));
    });

    it('should return default value for missing keys', () => {
        const retrieved = storage.get('missing_key', 'fallback');
        assert.strictEqual(retrieved, 'fallback');
    });

    it('should clear only items with specific prefix', () => {
        storage.set('key1', 'value1');
        storage.set('key2', 'value2');
        global.localStorage.setItem('other_app_key', 'value3');
        
        storage.clear();
        
        assert.strictEqual(storage.get('key1'), null);
        assert.strictEqual(storage.get('key2'), null);
        assert.strictEqual(global.localStorage.getItem('other_app_key'), 'value3');
    });
});
