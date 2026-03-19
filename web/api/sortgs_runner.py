"""
Google Scholar search by scraping HTML.

Returns `(headers, rows)` with a stable column order expected by `web/api/search.py`
and the React frontend:
["Rank", "Author", "Title", "Citations", "Year", "Venue", "Abstract", "Source", "PDF", "cit/year"]
"""

import datetime
import re
import time
from typing import List, Optional, Tuple, Union

import requests
from bs4 import BeautifulSoup

NOW = datetime.datetime.now()
HEADERS = [
    "Rank",
    "Author",
    "Title",
    "Citations",
    "Year",
    "Venue",
    "Abstract",
    "Source",
    "PDF",
    "cit/year",
]

GSCHOLAR_URL = "https://scholar.google.com/scholar?start={}&q={}&hl=en&as_sdt=0,5"
STARTYEAR_URL = "&as_ylo={}"
ENDYEAR_URL = "&as_yhi={}"
LANG_URL = "&lr={}"

ROBOT_KW = ["unusual traffic from your computer network", "not a robot"]


def _get_citations(content: str) -> int:
    match = re.search(r"Cited by (\d+)", content)
    return int(match.group(1)) if match else 0


def _get_year(content: str) -> int:
    match = re.search(r"\b(19|20)\d{2}\b", content)
    return int(match.group(0)) if match else 0


def _get_author(gs_a_text: str) -> str:
    clean = (gs_a_text or "").replace("\xa0", " ").strip()
    return clean.split(" - ")[0] if clean else ""


def _format_lang(langs: List[str]) -> str:
    # Google Scholar expects: lang_x|lang_y
    if len(langs) == 1:
        return f"lang_{langs[0]}"
    return "%7C".join(f"lang_{s}" for s in langs)


def _get_pdf_link(div) -> Optional[str]:
    try:
        pdf_div = div.find("div", {"class": "gs_ggs gs_fl"})
        if not pdf_div:
            return None
        a_tag = pdf_div.find("a")
        return a_tag.get("href") if a_tag else None
    except Exception:
        return None


def run_search_semantic_scholar(
    keyword: str,
    nresults: int = 100,
    sortby: str = "Citations",
    start_year: Optional[int] = None,
    end_year: Optional[int] = None,
    langfilter: Union[str, list] = "All",
    debug: bool = False,
    delay_seconds: float = 0,
    request_timeout: float = 10,
) -> Tuple[List[str], List[List]]:
    """
    Scrape Google Scholar results pages.

    Note: Vercel serverless may be blocked by Google Scholar (CAPTCHA). We raise a
    friendly error so the UI can show what happened.
    """
    end_year = end_year or NOW.year
    query = keyword.strip().strip("'\"").strip()
    if not query:
        return (HEADERS, [])

    main_url = GSCHOLAR_URL
    if start_year:
        main_url = main_url + STARTYEAR_URL.format(start_year)
    if end_year != NOW.year:
        main_url = main_url + ENDYEAR_URL.format(end_year)
    if langfilter != "All" and isinstance(langfilter, list) and langfilter:
        main_url = main_url + LANG_URL.format(_format_lang([str(x) for x in langfilter]))
    if debug:
        # Useful for unit testing without hitting Scholar repeatedly.
        main_url = "https://web.archive.org/web/20210314203256/" + main_url

    session = requests.Session()
    headers: List[str] = HEADERS
    rows: List[List] = []

    # Scholar paginates in blocks of 10 results.
    target_results = max(10, nresults)
    for n in range(0, target_results, 10):
        page_url = main_url.format(str(n), query.replace(" ", "+"))
        try:
            resp = session.get(page_url, timeout=request_timeout)
            resp.raise_for_status()
            html = resp.text
        except Exception as e:
            raise RuntimeError(f"Error al solicitar Google Scholar: {e}") from e

        lowered = html.lower()
        if any(kw in lowered for kw in ROBOT_KW):
            raise RuntimeError(
                "Google Scholar bloqueó el acceso (CAPTCHA/robot check). "
                "Espera un momento y vuelve a intentar, o prueba con menos búsquedas."
            )

        soup = BeautifulSoup(html, "html.parser")
        result_divs = soup.find_all("div", {"class": "gs_or"})
        if not result_divs:
            break

        for div in result_divs:
            gs_a = div.find("div", {"class": "gs_a"})
            gs_a_text = gs_a.get_text(" ", strip=True) if gs_a else ""

            h3 = div.find("h3")
            a_tag = h3.find("a") if h3 else None
            title = a_tag.get_text(" ", strip=True) if a_tag else "Could not catch title"
            source = a_tag.get("href") if a_tag and a_tag.has_attr("href") else ""

            citations = _get_citations(str(div))
            year = _get_year(gs_a_text)
            author = _get_author(gs_a_text) or "Unknown"

            # Venue: in Scholar this comes from the "Author - Venue, Year" text line.
            parts = gs_a_text.split(" - ")
            venue = parts[1].strip() if len(parts) >= 2 else "—"

            content_div = div.find("div", {"class": "gs_rs"})
            abstract = content_div.get_text(" ", strip=True) if content_div else "Content not found"

            pdf_link = _get_pdf_link(div) or "No PDF link"

            denom = max(1, end_year + 1 - min(year, end_year))
            cit_per_year = int(round(citations / denom, 0)) if year else 0

            rows.append([0, author, title, citations, year, venue, abstract, source, pdf_link, cit_per_year])

            if len(rows) >= target_results:
                break

        if delay_seconds > 0:
            time.sleep(delay_seconds)

        if len(rows) >= target_results:
            break

    # Sort rows by selected column.
    try:
        sort_idx = 9 if sortby == "cit/year" else 3
        rows.sort(key=lambda r: r[sort_idx], reverse=True)
    except Exception:
        rows.sort(key=lambda r: r[3], reverse=True)

    rows = rows[:target_results]
    for i, row in enumerate(rows, 1):
        row[0] = i

    return (headers, rows)

