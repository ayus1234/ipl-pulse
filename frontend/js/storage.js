// Local Storage Wrapper

class Storage {
    constructor(prefix = 'ipl_pulse_') {
        this.prefix = prefix;
    }

    _getKey(key) {
        return this.prefix + key;
    }

    get(key, defaultValue = null) {
        try {
            const item = localStorage.getItem(this._getKey(key));
            return item ? JSON.parse(item) : defaultValue;
        } catch (error) {
            console.error('Error reading from localStorage', error);
            return defaultValue;
        }
    }

    set(key, value) {
        try {
            localStorage.setItem(this._getKey(key), JSON.stringify(value));
            return true;
        } catch (error) {
            console.error('Error writing to localStorage', error);
            return false;
        }
    }

    remove(key) {
        try {
            localStorage.removeItem(this._getKey(key));
            return true;
        } catch (error) {
            console.error('Error removing from localStorage', error);
            return false;
        }
    }

    clear() {
        try {
            // Only clear items with our prefix
            const keysToRemove = [];
            for (let i = 0; i < localStorage.length; i++) {
                const k = localStorage.key(i);
                if (k.startsWith(this.prefix)) {
                    keysToRemove.push(k);
                }
            }
            keysToRemove.forEach(k => localStorage.removeItem(k));
            return true;
        } catch (error) {
            console.error('Error clearing localStorage', error);
            return false;
        }
    }
}

const storage = new Storage();
export default storage;
