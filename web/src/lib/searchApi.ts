import { useMutation } from "@tanstack/react-query";

export type SortBy = "Citations" | "cit/year";
export type OutputFormat = "xlsx" | "csv";

export interface SearchParams {
  keyword: string;
  exact_phrase: boolean;
  sortby: SortBy;
  start_year: number | "";
  end_year: number | "";
  langfilter: string[];
  nresults: number;
  format: OutputFormat;
}

export interface SearchDownload {
  blob: Blob;
  contentType: string;
  fileName: string;
}

function parseFilenameFromContentDisposition(value: string | null): string | null {
  if (!value) return null;
  // Example: attachment; filename="foo.csv"
  const m = value.match(/filename="?([^\";]+)"?/i);
  return m?.[1] ?? null;
}

async function postSearch(params: SearchParams): Promise<SearchDownload> {
  const keyword = params.keyword.trim();
  if (!keyword) throw new Error("Introduce al menos una palabra clave.");

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

  const res = await fetch("/api/search", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

  const contentType = res.headers.get("content-type") || "";

  if (!res.ok) {
    const text = await res.text();
    try {
      const j = JSON.parse(text) as { error?: string };
      throw new Error(typeof j?.error === "string" ? j.error : `Error ${res.status}`);
    } catch {
      throw new Error(text || `Error ${res.status}`);
    }
  }

  const isCsv = contentType.includes("text/csv") || contentType.includes("application/csv");
  const isXlsx =
    contentType.includes("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet");

  if (!isCsv && !isXlsx) {
    const text = await res.text();
    let msg = "La respuesta no es un archivo de búsqueda válido.";
    if (text.slice(0, 50).includes("<") || text.slice(0, 50).includes("html")) {
      msg = "Se recibió una página en lugar del CSV/Excel. Configura la API.";
    }
    try {
      const j = JSON.parse(text) as { error?: string };
      if (typeof j?.error === "string") msg = j.error;
    } catch {
      // ignore
    }
    throw new Error(msg);
  }

  const blob = await res.blob();
  const fileName =
    parseFilenameFromContentDisposition(res.headers.get("content-disposition")) ??
    `${keyword.replace(/[\s:]+/g, "_").slice(0, 80)}.${params.format}`;

  return { blob, contentType, fileName };
}

export function useSearchMutation() {
  return useMutation({
    mutationFn: postSearch,
  });
}

