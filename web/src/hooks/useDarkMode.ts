import { useCallback } from "react";
import { useLocalStorageState } from "./useLocalStorage";

const THEME_KEY = "citarank_theme_v1";

function computeInitialDarkMode() {
  if (typeof window === "undefined") return false;
  try {
    return window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches;
  } catch {
    return false;
  }
}

export function useDarkMode() {
  const [darkMode, setDarkMode] = useLocalStorageState<boolean>(THEME_KEY, computeInitialDarkMode());

  const toggle = useCallback(() => {
    setDarkMode((prev) => !prev);
  }, [setDarkMode]);

  return { darkMode, setDarkMode, toggle };
}

