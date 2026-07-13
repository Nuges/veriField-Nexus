// =============================================================================
// VeriField Nexus — Safe LocalStorage Utility
// =============================================================================
// Memory fallback for localStorage when blocked or throwing SecurityError
// (e.g. strict incognito or private browsing mode).
// =============================================================================

const memoryStorage: Record<string, string> = {};

export const safeStorage = {
  getItem(key: string): string | null {
    try {
      if (typeof window !== "undefined" && window.localStorage) {
        return window.localStorage.getItem(key);
      }
    } catch (err) {
      console.warn(`[Storage Warning] Failed to read from localStorage for "${key}":`, err);
    }
    return memoryStorage[key] || null;
  },

  setItem(key: string, value: string): void {
    try {
      if (typeof window !== "undefined" && window.localStorage) {
        window.localStorage.setItem(key, value);
        return;
      }
    } catch (err) {
      console.warn(`[Storage Warning] Failed to write to localStorage for "${key}":`, err);
    }
    memoryStorage[key] = value;
  },

  removeItem(key: string): void {
    try {
      if (typeof window !== "undefined" && window.localStorage) {
        window.localStorage.removeItem(key);
        return;
      }
    } catch (err) {
      console.warn(`[Storage Warning] Failed to remove from localStorage for "${key}":`, err);
    }
    delete memoryStorage[key];
  },

  clear(): void {
    try {
      if (typeof window !== "undefined" && window.localStorage) {
        window.localStorage.clear();
        return;
      }
    } catch (err) {
      console.warn("[Storage Warning] Failed to clear localStorage:", err);
    }
    for (const key in memoryStorage) {
      delete memoryStorage[key];
    }
  }
};
