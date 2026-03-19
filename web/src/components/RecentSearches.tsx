import type { FC } from "react";

type Props = {
  recentSearches: string[];
  onPick: (keyword: string) => void;
  onClose?: () => void;
};

export const RecentSearches: FC<Props> = ({ recentSearches, onPick, onClose }) => {
  return (
    <div className="flex flex-col h-full pt-16 md:pt-6 pb-6 px-4 overflow-y-auto">
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-sm font-semibold text-neutral-500 dark:text-neutral-400 uppercase tracking-wider">
          Búsquedas recientes
        </h2>
        {onClose ? (
          <button
            type="button"
            onClick={onClose}
            className="md:hidden inline-flex items-center justify-center w-8 h-8 rounded-lg border border-neutral-200 dark:border-neutral-800 bg-white/70 dark:bg-neutral-900/40 hover:bg-white dark:hover:bg-neutral-900"
            aria-label="Cerrar"
            title="Cerrar"
          >
            <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        ) : null}
      </div>

      {recentSearches.length === 0 ? (
        <p className="text-xs text-neutral-500 dark:text-neutral-400">
          Aún no hay búsquedas guardadas. Lanza una búsqueda para verlas aquí.
        </p>
      ) : (
        <ul className="space-y-1">
          {recentSearches.map((k) => (
            <li key={k}>
              <button
                type="button"
                onClick={() => {
                  onPick(k);
                  onClose?.();
                }}
                className="w-full text-left px-3 py-2 rounded-xl text-sm border border-transparent hover:border-neutral-200 dark:hover:border-neutral-800 bg-white/60 dark:bg-neutral-900/20 hover:bg-white dark:hover:bg-neutral-900 transition"
              >
                <span className="block text-neutral-800 dark:text-neutral-100 truncate">{k}</span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
};

