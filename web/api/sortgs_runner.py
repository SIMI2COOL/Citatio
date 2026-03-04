"""
Semantic Scholar search — versión simplificada y confiable.
Retorna (headers, rows) para CSV.
"""
import datetime
from typing import List, Optional, Tuple, Union

import requests

NOW = datetime.datetime.now()

HEADERS = ["Rank", "Author", "Title", "Citations", "Year", "Publisher", "Venue", "Content", "Source", "PDF", "cit/year"]

SEMANTIC_SCHOLAR_BASE = "https://api.semanticscholar.org/graph/v1/paper/search"
SEMANTIC_SCHOLAR_FIELDS = "title,year,citationCount,authors,url,abstract,venue,openAccessPdf"


def run_search_semantic_scholar(
    keyword: str,
    nresults: int = 100,
    sortby: str = "Citations",
    start_year: Optional[int] = None,
    end_year: Optional[int] = None,
    langfilter: Union[str, list] = "All",
    debug: bool = False,
    delay_seconds: float = 0,
    request_timeout: float = 25,
) -> Tuple[List[str], List[List]]:

    end_year = end_year or NOW.year
    query = keyword.strip().strip("'\"").strip()
    if not query:
        return (HEADERS, [])

    session = requests.Session()
    session.headers.update({
        "User-Agent": "Citatio/1.0 (https://github.com/SEMI2COOL/Citatio)"
    })

    all_papers = []
    offset = 0
    batch = 100  # máximo permitido por la API

    while len(all_papers) < 500:  # cap de seguridad
        params = {
            "query": query,
            "limit": batch,
            "offset": offset,
            "fields": SEMANTIC_SCHOLAR_FIELDS,
        }
        if start_year and end_year:
            params["year"] = f"{start_year}-{end_year}"
        elif start_year:
            params["year"] = f"{start_year}-{end_year}"

        try:
            r = session.get(SEMANTIC_SCHOLAR_BASE, params=params, timeout=request_timeout)
            if r.status_code == 429:
                raise RuntimeError("Límite de búsquedas alcanzado. Esperá un minuto e intentá de nuevo.")
            r.raise_for_status()
            data = r.json()
        except RuntimeError:
            raise
        except Exception as e:
            raise RuntimeError(f"Error al conectar con Semantic Scholar: {e}")

        papers = data.get("data") or []
        if not papers:
            break

        all_papers.extend(papers)
        offset += len(papers)

        # Si ya tenemos suficientes o la API no tiene más, parar
        if len(papers) < batch:
            break
        if len(all_papers) >= nresults * 3:  # buscar 3x para tener margen al ordenar
            break

    # Construir filas sin filtrar — Semantic Scholar ya es relevante por query
    rows = []
    for p in all_papers:
        title = (p.get("title") or "").strip() or "No title"
        abstract = (p.get("abstract") or "").strip() or "—"
        year_val = p.get("year")
        year = int(year_val) if year_val else 0
        citations = int(p.get("citationCount") or 0)
        authors_list = p.get("authors") or []
        author = ", ".join((a.get("name") or "").strip() for a in authors_list) if authors_list else "Unknown"
        venue = (p.get("venue") or "—").strip()
        url = (p.get("url") or "—").strip()
        oa = p.get("openAccessPdf")
        pdf = (oa.get("url") if isinstance(oa, dict) and oa else None) or "No PDF link"
        denom = max(1, end_year + 1 - min(year or end_year, end_year))
        cit_per_year = round(citations / denom, 1) if year else 0
        rows.append([0, author, title, citations, year, "—", venue, abstract, url, pdf, cit_per_year])

    # Ordenar por lo pedido
    sort_idx = 10 if sortby == "cit/year" else 3
    rows.sort(key=lambda r: r[sort_idx], reverse=True)

    # Tomar solo los N pedidos y asignar rank
    rows = rows[:nresults]
    for i, row in enumerate(rows, 1):
        row[0] = i

    return (HEADERS, rows)
