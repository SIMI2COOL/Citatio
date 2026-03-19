import { useCallback, useState } from "react";

import { ResultsArea } from "./components/ResultsArea";
import { RecentSearches } from "./components/RecentSearches";
import { SearchForm } from "./components/SearchForm";
import { ThemeToggle } from "./components/ThemeToggle";
import { useDarkMode } from "./hooks/useDarkMode";
import { useLocalStorageState } from "./hooks/useLocalStorage";
import { useSearchMutation, type OutputFormat, type SearchParams } from "./lib/searchApi";

const RECENT_SEARCHES_KEY = "citarank_recent_searches_v1";

const defaultParams: SearchParams = {
  keyword: "",
  exact_phrase: false,
  sortby: "Citations",
  start_year: "",
  end_year: "",
  langfilter: [],
  nresults: 30,
  format: "csv",
};

export default function App() {
  const [params, setParams] = useState<SearchParams>(defaultParams);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [downloadUrl, setDownloadUrl] = useState<string | null>(null);
  const [searchedKeyword, setSearchedKeyword] = useState<string>("");
  const [sidebarOpen, setSidebarOpen] = useState(false);

  const [recentSearches, setRecentSearches] = useLocalStorageState<string[]>(RECENT_SEARCHES_KEY, []);
  const { darkMode, toggle } = useDarkMode();

  // Keep Tailwind `dark:` styles in sync with the stored theme.
  if (typeof window !== "undefined") {
    const hasDarkClass = document.documentElement.classList.contains("dark");
    if (darkMode && !hasDarkClass) document.documentElement.classList.add("dark");
    if (!darkMode && hasDarkClass) document.documentElement.classList.remove("dark");
  }

  const searchMutation = useSearchMutation();

  const updateParams = useCallback((updates: Partial<SearchParams>) => {
    setParams((p) => ({ ...p, ...updates }));
    setError(null);
    setDownloadUrl((prev) => {
      if (prev) URL.revokeObjectURL(prev);
      return null;
    });
    setSearchedKeyword("");
  }, []);

  const runSearch = useCallback(async () => {
    const keyword = params.keyword.trim();
    if (!keyword) {
      setError("Introduce al menos una palabra clave.");
      return;
    }

    setLoading(true);
    setError(null);
    setDownloadUrl((prev) => {
      if (prev) URL.revokeObjectURL(prev);
      return null;
    });

    try {
      setSearchedKeyword(keyword);
      const { blob } = await searchMutation.mutateAsync(params);
      const url = URL.createObjectURL(blob);
      setDownloadUrl(url);

      // Save recent searches (top 5, unique).
      setRecentSearches((prev) => {
        const next = [keyword, ...prev.filter((k) => k !== keyword)];
        return next.slice(0, 5);
      });
    } catch (e) {
      setError(e instanceof Error ? e.message : "Error al generar el informe.");
    } finally {
      setLoading(false);
    }
  }, [params, searchMutation, setRecentSearches]);

  const format: OutputFormat = params.format;

  return (
    <div className="min-h-screen bg-neutral-50 text-neutral-900 dark:bg-neutral-950 dark:text-neutral-100 flex flex-col md:flex-row">
      {/* Sidebar */}
      <aside
        className={`
          fixed inset-y-0 left-0 z-40 w-72 bg-white/95 dark:bg-neutral-900/95 border-r border-neutral-200 dark:border-neutral-800
          shadow-lg md:shadow-none
          transform transition-transform duration-200 ease-out
          md:relative md:transform-none
          ${sidebarOpen ? "translate-x-0" : "-translate-x-full md:translate-x-0"}
        `}
      >
        <RecentSearches
          recentSearches={recentSearches}
          onPick={(kw) => {
            updateParams({ keyword: kw });
            setSidebarOpen(false);
          }}
          onClose={() => setSidebarOpen(false)}
        />
      </aside>

      {/* Main */}
      <div className="flex-1 flex flex-col">
        <header className="sticky top-0 z-10 bg-neutral-50/70 dark:bg-neutral-950/70 backdrop-blur border-b border-neutral-200 dark:border-neutral-800">
          <div className="flex items-center justify-between px-4 py-3 max-w-3xl mx-auto w-full">
            <div className="flex items-center gap-3">
              <button
                type="button"
                className="md:hidden inline-flex items-center justify-center w-10 h-10 rounded-xl border border-neutral-200 dark:border-neutral-800 bg-white/70 dark:bg-neutral-900/40 hover:bg-white dark:hover:bg-neutral-900"
                onClick={() => setSidebarOpen(true)}
                aria-label="Abrir búsquedas recientes"
              >
                <svg className="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                  <path strokeLinejoin="round" d="M4 6h16M4 12h16M4 18h16" />
                </svg>
              </button>

              <img src="/logo.svg" alt="" className="h-9 w-9 flex-shrink-0" />
              <div>
                <p className="text-xs uppercase tracking-widest text-neutral-500 dark:text-neutral-400">Scholar export</p>
                <h1 className="text-lg font-semibold" style={{ fontFamily: '"Playfair Display", serif' }}>
                  Citarank
                </h1>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <ThemeToggle darkMode={darkMode} onToggle={toggle} />
            </div>
          </div>
        </header>

        <main className="flex-1 px-4 py-6 max-w-3xl mx-auto w-full">
          <div className="bg-white/70 dark:bg-neutral-900/30 border border-neutral-200 dark:border-neutral-800 rounded-3xl p-5 md:p-6 shadow-sm">
            <SearchForm params={params} loading={loading} onUpdateParams={updateParams} onRun={runSearch} />
          </div>

          <ResultsArea
            error={error}
            loading={loading}
            downloadUrl={downloadUrl}
            format={format}
            searchedKeyword={searchedKeyword}
          />
        </main>
      </div>
    </div>
  );
}

