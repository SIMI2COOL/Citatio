import type { FC } from "react";

type Props = {
  darkMode: boolean;
  onToggle: () => void;
};

export const ThemeToggle: FC<Props> = ({ darkMode, onToggle }) => {
  return (
    <button
      type="button"
      onClick={onToggle}
      className="inline-flex items-center justify-center p-2 rounded-xl border border-neutral-200 dark:border-neutral-800 bg-white/70 dark:bg-neutral-900/40 hover:bg-white dark:hover:bg-neutral-900 transition"
      aria-label={darkMode ? "Activar modo claro" : "Activar modo oscuro"}
      title={darkMode ? "Modo claro" : "Modo oscuro"}
    >
      {darkMode ? (
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.657M16 12a4 4 0 11-8 0 4 4 0 018 0z"
          />
        </svg>
      ) : (
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z"
          />
        </svg>
      )}
    </button>
  );
};

