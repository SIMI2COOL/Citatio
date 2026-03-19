import { useCallback, useSyncExternalStore } from "react";

type Listener = () => void;

// Shared emitter for all `useLocalStorageState` instances in this tab.
const listeners = new Set<Listener>();

function notifyAll() {
  for (const l of listeners) l();
}

function readJson<T>(key: string, fallback: T): T {
  try {
    const raw = window.localStorage.getItem(key);
    if (raw === null) return fallback;
    return JSON.parse(raw) as T;
  } catch {
    return fallback;
  }
}

function writeJson<T>(key: string, value: T) {
  window.localStorage.setItem(key, JSON.stringify(value));
  // Same-tab changes won't fire the browser `storage` event, so we notify manually.
  notifyAll();
}

export function useLocalStorageState<T>(key: string, fallback: T) {
  const subscribe = useCallback(
    (onStoreChange: () => void) => {
      const storageHandler = (e: StorageEvent) => {
        if (e.key === key) onStoreChange();
      };

      window.addEventListener("storage", storageHandler);
      listeners.add(onStoreChange);

      return () => {
        window.removeEventListener("storage", storageHandler);
        listeners.delete(onStoreChange);
      };
    },
    [key],
  );

  const getSnapshot = useCallback(() => readJson<T>(key, fallback), [key, fallback]);
  const getServerSnapshot = useCallback(() => fallback, [fallback]);

  const value = useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot);

  const setValue = useCallback(
    (next: T | ((prev: T) => T)) => {
      const prev = readJson<T>(key, fallback);
      const resolved = typeof next === "function" ? (next as (p: T) => T)(prev) : next;
      writeJson<T>(key, resolved);
    },
    [key, fallback],
  );

  return [value, setValue] as const;
}

