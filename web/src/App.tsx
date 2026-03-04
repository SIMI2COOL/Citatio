import { useCallback, useEffect, useState } from "react";
import type { FormEvent } from "react";

const API_BASE = "/api";

const LANG_OPTIONS: { code: string; label: string }[] = [
  { code: "en", label: "English" },
  { code: "es", label: "Español" },
  { code: "pt", label: "Português" },
  { code: "fr", label: "Français" },
  { code: "de", label: "Deutsch" },
  { code: "it", label: "Italiano" },
  { code: "zh-CN", label: "中文" },
  { code: "ja", label: "日本語" },
  { code: "ko", label: "한국어" },
  { code: "nl", label: "Nederlands" },
  { code: "pl", label: "Polski" },
  { code: "tr", label: "Türkçe" },
];

const RECENT_SEARCHES_KEY = "citerank_recent_searches_v1";
const AUTH_STORAGE_KEY = "citerank_auth_v1";
const ACCESS_PASSWORD = "reydelasbusquedas";

export interface SearchParams {
  keyword: string;
  exact_phrase: boolean;
  sortby: "Citations" | "cit/year";
  start_year: number | "";
  end_year: number | "";
  langfilter: string[];
  nresults: number;
  format: "xlsx" | "csv";
}

const defaultParams: SearchParams = {
  keyword: "",
  exact_phrase: false,
  sortby: "Citations",
  start_year: "",
  end_year: "",
  langfilter: [],
  nresults: 100,
  format: "csv",
};

export default function App() {
  const [params, setParams] = useState<SearchParams>(defaultParams);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [downloadUrl, setDownloadUrl] = useState<string | null>(null);
  const [searchedKeyword, setSearchedKeyword] = useState<string>("");
  const [recentSearches, setRecentSearches] = useState<string[]>([]);
   const [authorized, setAuthorized] = useState<boolean>(() => {
    if (typeof window === "undefined") return false;
    return window.localStorage.getItem(AUTH_STORAGE_KEY) === "ok";
  });
  const [passwordInput, setPasswordInput] = useState("");
  const [authError, setAuthError] = useState<string | null>(null);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [darkMode, setDarkMode] = useState(() => {
    if (typeof window === "undefined") return false;
    return window.matchMedia("(prefers-color-scheme: dark)").matches;
  });

  const updateParams = useCallback((updates: Partial<SearchParams>) => {
    setParams((p) => ({ ...p, ...updates }));
    setError(null);
    setDownloadUrl(null);
    setSearchedKeyword("");
  }, []);

  const handleAuthSubmit = useCallback(
    (e: FormEvent) => {
      e.preventDefault();
      const value = passwordInput.trim();
      if (!value) {
        setAuthError("Introduce la contraseña.");
        return;
      }
      if (value !== ACCESS_PASSWORD) {
        setAuthError("Contraseña incorrecta.");
        return;
      }
      setAuthorized(true);
      setAuthError(null);
      setPasswordInput("");
    },
    [passwordInput],
  );

  const runSearch = useCallback(async () => {
    const keyword = params.keyword.trim();
    if (!keyword) {
      setError("Introduce al menos una palabra clave.");
      return;
    }
    setLoading(true);
    setError(null);
    setDownloadUrl((prev) => {
      if (prev) {
        URL.revokeObjectURL(prev);
      }
      return null;
    });
    try {
      setSearchedKeyword(keyword);
      const body = {
        keyword,
        exact_phrase: params.exact_phrase,
        sortby: params.sortby,
        start_year: params.start_year === "" ? null : params.start_year,
        end_year: params.end_year === "" ? null : params.end_year,
        langfilter: params.langfilter.length ? params.langfilter : null,
        nresults: params.nresults,
        format: params.format,
      };
      const res = await fetch(`${API_BASE}/search`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      const contentType = res.headers.get("content-type") || "";
      if (!res.ok) {
        const t = await res.text();
        let msg = t || `Error ${res.status}`;
        try {
          const j = JSON.parse(t) as { error?: string };
          if (typeof j?.error === "string") msg = j.error;
        } catch {
          /* use t as msg */
        }
        throw new Error(msg);
      }
      // Solo usar como descarga si la API devolvió un archivo esperado (CSV o Excel), no HTML ni otro contenido
      const isCsv = contentType.includes("text/csv") || contentType.includes("application/csv");
      const isXlsx = contentType.includes("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet");
      if (!isCsv && !isXlsx) {
        const t = await res.text();
        let msg = "La respuesta no es un archivo de búsqueda válido. Comprueba que la API esté activa.";
        try {
          const j = JSON.parse(t) as { error?: string };
          if (typeof j?.error === "string") msg = j.error;
        } catch {
          if (t.slice(0, 50).includes("<!") || t.slice(0, 50).includes("<html")) msg = "Se recibió la página en lugar del CSV. Configura la API (Root Directory = web).";
        }
        throw new Error(msg);
      }
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      setDownloadUrl(url);
      setRecentSearches((prev) => {
        const next = [keyword, ...prev.filter((k) => k !== keyword)];
        return next.slice(0, 5);
      });
    } catch (e) {
      setError(e instanceof Error ? e.message : "Error al generar el informe.");
    } finally {
      setLoading(false);
    }
  }, [params]);

  useEffect(() => {
    if (typeof window === "undefined") return;
    try {
      const raw = window.localStorage.getItem(RECENT_SEARCHES_KEY);
      if (!raw) return;
      const parsed = JSON.parse(raw);
      if (Array.isArray(parsed)) {
        setRecentSearches(parsed.filter((v): v is string => typeof v === "string"));
      }
    } catch {
      // ignore
    }
  }, []);

  useEffect(() => {
    if (typeof window === "undefined") return;
    try {
      window.localStorage.setItem(RECENT_SEARCHES_KEY, JSON.stringify(recentSearches));
    } catch {
      // ignore
    }
  }, [recentSearches]);

  useEffect(() => {
    if (typeof window === "undefined") return;
    if (authorized) {
      window.localStorage.setItem(AUTH_STORAGE_KEY, "ok");
    } else {
      window.localStorage.removeItem(AUTH_STORAGE_KEY);
    }
  }, [authorized]);

  useEffect(() => {
    return () => {
      if (downloadUrl) URL.revokeObjectURL(downloadUrl);
    };
  }, [downloadUrl]);

  useEffect(() => {
    document.documentElement.classList.toggle("dark", darkMode);
  }, [darkMode]);

  const currentYear = new Date().getFullYear();

  if (!authorized) {
    return (
      <div className="min-h-screen bg-neutral-950 text-neutral-100 flex items-center justify-center px-4">
        <div className="max-w-sm w-full bg-neutral-900/90 border border-neutral-700 rounded-2xl p-6 shadow-xl">
          <div className="flex items-center gap-3 mb-4">
            <img src="/logo.svg" alt="" className="h-9 w-9 flex-shrink-0" />
            <div>
              <p className="text-xs uppercase tracking-widest text-neutral-400">Acceso privado</p>
              <h1 className="text-lg font-semibold">Citerank</h1>
            </div>
          </div>
          <p className="text-sm text-neutral-300 mb-4">
            Esta herramienta está protegida. Introduce la contraseña para continuar.
          </p>
          {authError && (
            <div className="mb-3 text-xs text-red-300 bg-red-900/30 border border-red-700 rounded-lg px-3 py-2">
              {authError}
            </div>
          )}
          <form onSubmit={handleAuthSubmit} className="space-y-3">
            <div>
              <label htmlFor="access-password" className="block text-xs font-medium text-neutral-300 mb-1">
                Contraseña
              </label>
              <input
                id="access-password"
                type="password"
                value={passwordInput}
                onChange={(e) => {
                  setPasswordInput(e.target.value);
                  if (authError) setAuthError(null);
                }}
                className="w-full px-3 py-2 rounded-lg bg-neutral-950 border border-neutral-700 text-sm focus:ring-2 focus:ring-[var(--color-accent)] focus:border-transparent outline-none"
                autoComplete="current-password"
              />
            </div>
            <button
              type="submit"
              className="w-full px-4 py-2.5 rounded-lg bg-[var(--color-accent)] hover:bg-[var(--color-accent-hover)] text-sm font-semibold text-white disabled:opacity-60"
            >
              Entrar
            </button>
          </form>
        </div>
      </div>
    );
  }

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
        <div className="flex flex-col h-full pt-16 md:pt-6 pb-6 px-4 overflow-y-auto">
          <h2 className="text-sm font-semibold text-neutral-500 dark:text-neutral-400 uppercase tracking-wider mb-3">
            Búsquedas recientes
          </h2>
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
                      updateParams({ keyword: k });
                      setSidebarOpen(false);
                    }}
                    className="text-left text-sm w-full px-3 py-2 rounded-lg hover:bg-neutral-100 dark:hover:bg-neutral-800 truncate"
                    title={k}
                  >
                    {k}
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      </aside>

      {/* Overlay when sidebar open on mobile */}
      {sidebarOpen && (
        <button
          type="button"
          aria-label="Cerrar panel"
          className="fixed inset-0 z-30 bg-black/20 md:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Main */}
      <main className="flex-1 flex flex-col min-w-0">
        <header className="sticky top-0 z-20 bg-white/90 dark:bg-neutral-900/90 backdrop-blur border-b border-neutral-200 dark:border-neutral-800 px-4 py-3 flex items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <button
              type="button"
              aria-label="Abrir accesos rápidos"
              className="md:hidden p-2 rounded-lg hover:bg-neutral-100 dark:hover:bg-neutral-800"
              onClick={() => setSidebarOpen(true)}
            >
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
              </svg>
            </button>
            <img src="/logo.svg" alt="" className="h-9 w-9 flex-shrink-0" />
            <span className="font-semibold text-lg">Citerank</span>
          </div>
          <button
            type="button"
            aria-label={darkMode ? "Modo claro" : "Modo oscuro"}
            className="p-2 rounded-lg hover:bg-neutral-100 dark:hover:bg-neutral-800"
            onClick={() => setDarkMode((d) => !d)}
          >
            {darkMode ? (
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z" />
              </svg>
            ) : (
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z" />
              </svg>
            )}
          </button>
        </header>

        <div className="flex-1 px-4 py-6 max-w-3xl mx-auto w-full">
          <label htmlFor="keyword" className="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-2">
            Palabras clave
          </label>
          <input
            id="keyword"
            type="text"
            value={params.keyword}
            onChange={(e) => updateParams({ keyword: e.target.value })}
            placeholder='Ej: machine learning, "deep learning" OR "neural networks"'
            className="w-full px-4 py-3 rounded-xl border border-neutral-300 dark:border-neutral-700 bg-white dark:bg-neutral-900 focus:ring-2 focus:ring-[var(--color-accent)] focus:border-transparent outline-none transition"
          />
          <p className="mt-1.5 text-xs text-neutral-500 dark:text-neutral-400">
            Usa comillas para frase exacta. Varios términos con OR, ej.: &quot;tema A&quot; OR &quot;tema B&quot;
          </p>

          {/* Filters */}
          <div className="mt-6 space-y-4">
            <div className="flex flex-wrap items-center gap-4">
              <label className="inline-flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={params.exact_phrase}
                  onChange={(e) => updateParams({ exact_phrase: e.target.checked })}
                  className="rounded border-neutral-400 text-[var(--color-accent)] focus:ring-[var(--color-accent)]"
                />
                <span className="text-sm">Frase exacta</span>
              </label>
              <div className="flex items-center gap-2">
                <span className="text-sm text-neutral-600 dark:text-neutral-400">Ordenar por:</span>
                <select
                  value={params.sortby}
                  onChange={(e) => updateParams({ sortby: e.target.value as SearchParams["sortby"] })}
                  className="px-3 py-1.5 rounded-lg border border-neutral-300 dark:border-neutral-700 bg-white dark:bg-neutral-900 text-sm"
                >
                  <option value="Citations">Citas totales</option>
                  <option value="cit/year">Citas por año</option>
                </select>
              </div>
              <div className="flex items-center gap-2">
                <label className="text-sm text-neutral-600 dark:text-neutral-400">Desde año</label>
                <input
                  type="number"
                  min={1900}
                  max={2100}
                  placeholder="opcional"
                  value={params.start_year === "" ? "" : params.start_year}
                  onChange={(e) =>
                    updateParams({
                      start_year: e.target.value === "" ? "" : Number(e.target.value),
                    })
                  }
                  className="w-24 px-2 py-1.5 rounded-lg border border-neutral-300 dark:border-neutral-700 bg-white dark:bg-neutral-900 text-sm"
                />
              </div>
              <div className="flex items-center gap-2">
                <label className="text-sm text-neutral-600 dark:text-neutral-400">Hasta año</label>
                <input
                  type="number"
                  min={1900}
                  max={2100}
                  placeholder={String(currentYear)}
                  value={params.end_year === "" ? "" : params.end_year}
                  onChange={(e) =>
                    updateParams({
                      end_year: e.target.value === "" ? "" : Number(e.target.value),
                    })
                  }
                  className="w-24 px-2 py-1.5 rounded-lg border border-neutral-300 dark:border-neutral-700 bg-white dark:bg-neutral-900 text-sm"
                />
              </div>
              <div className="flex items-center gap-2">
                <label className="text-sm text-neutral-600 dark:text-neutral-400">Nº resultados</label>
                <input
                  type="number"
                  min={10}
                  max={100}
                  value={params.nresults}
                  onChange={(e) =>
                    updateParams({
                      nresults: Math.min(100, Math.max(10, Number(e.target.value) || 100)),
                    })
                  }
                  className="w-20 px-2 py-1.5 rounded-lg border border-neutral-300 dark:border-neutral-700 bg-white dark:bg-neutral-900 text-sm"
                />
                <span className="text-xs text-neutral-500 dark:text-neutral-400">(máx. 100 en la versión web)</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-sm text-neutral-600 dark:text-neutral-400">Descargar como</span>
                <select
                  value={params.format}
                  onChange={(e) => updateParams({ format: e.target.value as SearchParams["format"] })}
                  className="px-3 py-1.5 rounded-lg border border-neutral-300 dark:border-neutral-700 bg-white dark:bg-neutral-900 text-sm"
                >
                  <option value="xlsx">Excel (.xlsx)</option>
                  <option value="csv">CSV (.csv) — versión web</option>
                </select>
              </div>
            </div>
            <div>
              <span className="text-sm text-neutral-600 dark:text-neutral-400 block mb-2">Idiomas (opcional)</span>
              <div className="flex flex-wrap gap-2">
                {LANG_OPTIONS.map(({ code, label }) => (
                  <label key={code} className="inline-flex items-center gap-1.5 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={params.langfilter.includes(code)}
                      onChange={(e) => {
                        const next = e.target.checked
                          ? [...params.langfilter, code]
                          : params.langfilter.filter((c) => c !== code);
                        updateParams({ langfilter: next });
                      }}
                      className="rounded border-neutral-400 text-[var(--color-accent)] focus:ring-[var(--color-accent)]"
                    />
                    <span className="text-sm">{label}</span>
                  </label>
                ))}
              </div>
            </div>
          </div>

          <div className="mt-6">
            <button
              type="button"
              onClick={runSearch}
              disabled={loading}
              className="w-full md:w-auto px-8 py-3 rounded-xl font-semibold text-white bg-[var(--color-accent)] hover:bg-[var(--color-accent-hover)] focus:ring-2 focus:ring-offset-2 focus:ring-[var(--color-accent)] disabled:opacity-60 disabled:cursor-not-allowed transition"
            >
              {loading ? "Generando…" : "Buscar y exportar"}
            </button>
          </div>

          {/* Results */}
          <section className="mt-8" aria-live="polite">
            {error && (
              <div className="p-4 rounded-xl bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 text-red-800 dark:text-red-200">
                {error}
              </div>
            )}
            {loading && (
              <div className="flex items-center gap-3 p-4 rounded-xl bg-neutral-100 dark:bg-neutral-800/50">
                <svg
                  className="animate-spin h-6 w-6 text-[var(--color-accent)]"
                  fill="none"
                  viewBox="0 0 24 24"
                  aria-hidden
                >
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path
                    className="opacity-75"
                    fill="currentColor"
                    d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                  />
                </svg>
                <span>Generando informe… Puede tardar un momento.</span>
              </div>
            )}
            {downloadUrl && !loading && (
              <div className="p-4 rounded-xl bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800">
                <p className="text-green-800 dark:text-green-200 font-medium mb-2">Informe listo</p>
                <a
                  href={downloadUrl}
                  download={`${searchedKeyword.replace(/[\s:]+/g, "_").slice(0, 80) || "scholar_export"}.${params.format}`}
                  className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-green-600 text-white hover:bg-green-700 font-medium"
                >
                  Descargar {params.format === "xlsx" ? "Excel" : "CSV"}
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                  </svg>
                </a>
              </div>
            )}
          </section>
        </div>
      </main>
    </div>
  );
}
