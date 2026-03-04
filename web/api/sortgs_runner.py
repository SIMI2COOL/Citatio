"""
Google Scholar search via SerpAPI.
Retorna (headers, rows) para CSV.
"""
import datetime
import os
from typing import List, Optional, Tuple, Union

import requests

NOW = datetime.datetime.now()
HEADERS = ["Rank", "Author", "Title", "Citations", "Year", "Venue", "Abstract", "Source", "PDF", "cit/year"]
SERPAPI_URL = "https://serpapi.com/search.json"


def run_search_semantic_scholar(
    keyword: str,
    nresults: int = 100,
    sortby: str = "Citations",
    start_year: Optional[int] = None,
    end_year: Optional[int] = None,
    langfilter: Union[str, list] = "All",
    debug: bool = False,
    delay_seconds: float = 0,
    request_timeout: float = 8,
) -> Tuple[List[str], List[List]]:

    api_key = os.environ.get("SERPAPI_KEY", "").strip()
    if not api_key:
        raise RuntimeError("SERPAPI_KEY no configurada. Agregala como variable de entorno en Vercel.")

    end_year = end_year or NOW.year
    query = keyword.strip().strip("'\"").strip()
    if not query:
        return (HEADERS, [])

    session = requests.Session()
    all_results: List[dict] = []
    start = 0
    # Pedimos como máximo 30 resultados efectivos en la versión web
    target_results = min(nresults, 30)

    while len(all_results) < target_results:
        params = {
            "engine": "google_scholar",
            "q": query,
            "api_key": api_key,
            "num": 10,
            "start": start,
            "hl": "en",
        }
        if start_year:
            params["as_ylo"] = start_year
        if end_year != NOW.year:
            params["as_yhi"] = end_year

        try:
            r = session.get(SERPAPI_URL, params=params, timeout=request_timeout)
            r.raise_for_status()
            data = r.json()
        except Exception as e:
            raise RuntimeError(f"Error al conectar con SerpAPI: {e}")

        if "error" in data:
            raise RuntimeError(f"SerpAPI error: {data['error']}")

        results = data.get("organic_results") or []
        if not results:
            break

        all_results.extend(results)
        start += len(results)

        # SerpAPI devuelve de a 10; si devolvió menos de 10 no hay más páginas
        if len(results) < 10:
            break

    rows = []
    for p in all_results:
        title = (p.get("title") or "No title").strip()

        # Citas
        inline = p.get("inline_links") or {}
        cited_by = inline.get("cited_by") or {}
        citations = int(cited_by.get("total") or 0)

        # Año
        pub_info = p.get("publication_info") or {}
        summary = pub_info.get("summary") or ""
        year = 0
        import re
        m = re.search(r"\b(19|20)\d{2}\b", summary)
        if m:
            year = int(m.group(0))

        # Autores
        authors_list = pub_info.get("authors") or []
        if authors_list:
            author = ", ".join(a.get("name", "") for a in authors_list)
        else:
            # fallback: primer fragmento antes del primer " - " en summary
            author = summary.split(" - ")[0].strip() if summary else "Unknown"

        # Venue
        parts = summary.split(" - ")
        venue = parts[1].strip() if len(parts) >= 2 else "—"

        # Abstract
        abstract = (p.get("snippet") or "—").strip()

        # Links
        url = (p.get("link") or "—").strip()
        resources = p.get("resources") or []
        pdf = next(
            (r["link"] for r in resources if isinstance(r, dict) and "pdf" in (r.get("file_format") or "").lower()),
            "No PDF link"
        )

        denom = max(1, end_year + 1 - min(year or end_year, end_year))
        cit_per_year = round(citations / denom, 1) if year else 0

        rows.append([0, author, title, citations, year, venue, abstract, url, pdf, cit_per_year])

    # Ordenar
    sort_idx = 9 if sortby == "cit/year" else 3
    rows.sort(key=lambda r: r[sort_idx], reverse=True)
    rows = rows[:target_results]
    for i, row in enumerate(rows, 1):
        row[0] = i

    return (HEADERS, rows)
