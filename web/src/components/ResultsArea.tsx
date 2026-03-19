import type { FC } from "react";
import type { OutputFormat } from "../lib/searchApi";

type Props = {
  error: string | null;
  loading: boolean;
  downloadUrl: string | null;
  format: OutputFormat;
  searchedKeyword: string;
};

function downloadName(searchedKeyword: string, format: OutputFormat) {
  const safe = searchedKeyword.replace(/[\s:]+/g, "_").slice(0, 80) || "scholar_export";
  return `${safe}.${format}`;
}

export const ResultsArea: FC<Props> = ({ error, loading, downloadUrl, format, searchedKeyword }) => {
  return (
    <section className="mt-8" aria-live="polite">
      {error ? (
        <div className="p-4 rounded-xl bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 text-red-800 dark:text-red-200">
          {error}
        </div>
      ) : null}

      {loading ? (
        <div className="flex items-center gap-3 p-4 rounded-xl bg-neutral-100 dark:bg-neutral-800/50">
          <svg className="animate-spin h-6 w-6 text-[var(--color-accent)]" fill="none" viewBox="0 0 24 24" aria-hidden>
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path
              className="opacity-75"
              fill="currentColor"
              d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
            />
          </svg>
          <span>Generando informe… Puede tardar un momento.</span>
        </div>
      ) : null}

      {downloadUrl && !loading ? (
        <div className="p-4 rounded-xl bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800">
          <p className="text-green-800 dark:text-green-200 font-medium mb-2">Informe listo</p>
          <a
            href={downloadUrl}
            download={downloadName(searchedKeyword, format)}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-green-600 text-white hover:bg-green-700 font-medium"
          >
            Descargar {format === "xlsx" ? "Excel" : "CSV"}
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden>
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
            </svg>
          </a>
        </div>
      ) : null}
    </section>
  );
};

