import type { FC } from "react";
import type { SearchParams } from "../lib/searchApi";

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

type Props = {
  params: SearchParams;
  loading: boolean;
  onUpdateParams: (updates: Partial<SearchParams>) => void;
  onRun: () => void;
};

export const SearchForm: FC<Props> = ({ params, loading, onUpdateParams, onRun }) => {
  const currentYear = new Date().getFullYear();

  return (
    <div className="flex flex-col">
      <label htmlFor="keyword" className="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-2">
        Palabras clave
      </label>
      <input
        id="keyword"
        type="text"
        value={params.keyword}
        onChange={(e) => onUpdateParams({ keyword: e.target.value })}
        placeholder='Ej: machine learning, "deep learning" OR "neural networks"'
        className="w-full px-4 py-3 rounded-xl border border-neutral-300 dark:border-neutral-700 bg-white dark:bg-neutral-900 focus:ring-2 focus:ring-[var(--color-accent)] focus:border-transparent outline-none transition"
      />
      <p className="mt-1.5 text-xs text-neutral-500 dark:text-neutral-400">
        Usa comillas para frase exacta. Varios términos con OR, ej.: &quot;tema A&quot; OR &quot;tema B&quot;
      </p>

      <div className="mt-6 space-y-4">
        <div className="flex flex-wrap items-center gap-4">
          <label className="inline-flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={params.exact_phrase}
              onChange={(e) => onUpdateParams({ exact_phrase: e.target.checked })}
              className="rounded border-neutral-400 text-[var(--color-accent)] focus:ring-[var(--color-accent)]"
            />
            <span className="text-sm">Frase exacta</span>
          </label>

          <div className="flex items-center gap-2">
            <span className="text-sm text-neutral-600 dark:text-neutral-400">Ordenar por:</span>
            <select
              value={params.sortby}
              onChange={(e) => onUpdateParams({ sortby: e.target.value as SearchParams["sortby"] })}
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
              onChange={(e) => {
                const v = e.target.value;
                onUpdateParams({ start_year: v === "" ? "" : Number(v) });
              }}
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
              onChange={(e) => {
                const v = e.target.value;
                onUpdateParams({ end_year: v === "" ? "" : Number(v) });
              }}
              className="w-24 px-2 py-1.5 rounded-lg border border-neutral-300 dark:border-neutral-700 bg-white dark:bg-neutral-900 text-sm"
            />
          </div>

          <div className="flex items-center gap-2">
            <label className="text-sm text-neutral-600 dark:text-neutral-400">Nº resultados</label>
            <input
              type="number"
              min={10}
              max={30}
              value={params.nresults}
              onChange={(e) => {
                const n = Number(e.target.value) || 30;
                onUpdateParams({ nresults: Math.min(30, Math.max(10, n)) });
              }}
              className="w-20 px-2 py-1.5 rounded-lg border border-neutral-300 dark:border-neutral-700 bg-white dark:bg-neutral-900 text-sm"
            />
            <span className="text-xs text-neutral-500 dark:text-neutral-400">(máx. 30)</span>
          </div>

          <div className="flex items-center gap-2">
            <span className="text-sm text-neutral-600 dark:text-neutral-400">Descargar como</span>
            <select
              value={params.format}
              onChange={(e) => onUpdateParams({ format: e.target.value as SearchParams["format"] })}
              className="px-3 py-1.5 rounded-lg border border-neutral-300 dark:border-neutral-700 bg-white dark:bg-neutral-900 text-sm"
            >
              <option value="xlsx">Excel (.xlsx)</option>
              <option value="csv">CSV (.csv)</option>
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
                    onUpdateParams({ langfilter: next });
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
          onClick={onRun}
          disabled={loading}
          className="w-full md:w-auto px-8 py-3 rounded-xl font-semibold text-white bg-[var(--color-accent)] hover:bg-[var(--color-accent-hover)] focus:ring-2 focus:ring-offset-2 focus:ring-[var(--color-accent)] disabled:opacity-60 disabled:cursor-not-allowed transition"
        >
          {loading ? "Generando…" : "Buscar y exportar"}
        </button>
      </div>
    </div>
  );
};

