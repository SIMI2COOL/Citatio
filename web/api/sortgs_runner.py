"""
Academic search for Vercel serverless.
Primary: Semantic Scholar API (reliable, no blocking).
Fallback/legacy: Google Scholar scrape (requests + BeautifulSoup); often blocked on server.
Returns (headers, rows) for CSV output.
"""
import datetime
import re
from typing import Any, List, Optional, Tuple, Union
from urllib.parse import quote_plus

import requests
from bs4 import BeautifulSoup

# --- Semantic Scholar API (primary, no key required) ---
SEMANTIC_SCHOLAR_BASE = "https://api.semanticscholar.org/graph/v1/paper/search"
SEMANTIC_SCHOLAR_FIELDS = "title,year,citationCount,authors,url,abstract,venue,openAccessPdf"

# --- Google Scholar (legacy scrape) ---
GSCHOLAR_URL = "https://scholar.google.com/scholar?start={}&q={}&hl=en&as_sdt=0,5"
STARTYEAR_URL = "&as_ylo={}"
ENDYEAR_URL = "&as_yhi={}"
LANG_URL = "&lr={}"
NOW = datetime.datetime.now()

ROBOT_BLOCK_KEYWORDS = [
    "unusual traffic from your computer network",
    "not a robot",
    "sorry, you have been blocked",
    "captcha",
    "automated requests",
]

REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

HEADERS = ["Rank", "Author", "Title", "Citations", "Year", "Publisher", "Venue", "Content", "Source", "PDF", "cit/year"]


def _get_citations(content: str) -> int:
    match = re.search(r"Cited by (\d+)", content)
    return int(match.group(1)) if match else 0


def _get_year(content: str) -> int:
    match = re.search(r"\b(19|20)\d{2}\b", content)
    return int(match.group(0)) if match else 0


def _get_author(content: str) -> str:
    clean = content.replace("\xa0", " ").strip()
    return clean.split(" - ")[0] if clean else ""


def _format_lang(strings: List[str]) -> str:
    if len(strings) == 1:
        return f"lang_{strings[0]}"
    return "%7C".join(f"lang_{s}" for s in strings)


def _get_pdf_link(div) -> Optional[str]:
    try:
        pdf_div = div.find("div", {"class": "gs_ggs gs_fl"})
        if pdf_div:
            a = pdf_div.find("a")
            if a:
                return a.get("href")
    except Exception:
        pass
    return None


def _semantic_scholar_request(
    params: Any, request_timeout: float, max_retries: int = 3
) -> Any:
    """GET Semantic Scholar with retries on 429 (rate limit)."""
    import time

    session = requests.Session()
    session.headers.update({"User-Agent": "AcademicSearch/1.0 (https://github.com/SIMI2COOL/Citatio)"})
    last_error: Optional[Exception] = None
    for attempt in range(max_retries):
        try:
            r = session.get(
                SEMANTIC_SCHOLAR_BASE,
                params=params,
                timeout=request_timeout,
            )
            if r.status_code == 429:
                wait = (2 ** attempt) * 2  # 2s, 4s, 8s
                if attempt < max_retries - 1:
                    time.sleep(wait)
                    continue
                raise RuntimeError(
                    "Demasiadas búsquedas seguidas. Espera un minuto e inténtalo de nuevo."
                ) from None
            r.raise_for_status()
            return r.json()
        except requests.RequestException as e:
            last_error = e
            if hasattr(e, "response") and e.response is not None and e.response.status_code == 429:
                if attempt < max_retries - 1:
                    time.sleep((2 ** attempt) * 2)
                    continue
                raise RuntimeError(
                    "Demasiadas búsquedas seguidas. Espera un minuto e inténtalo de nuevo."
                ) from e
            raise RuntimeError(f"Semantic Scholar API error: {e}") from e
    if last_error:
        raise RuntimeError(f"Semantic Scholar API error: {last_error}") from last_error
    raise RuntimeError("Semantic Scholar request failed") from None


def run_search_semantic_scholar(
    keyword: str,
    nresults: int = 10,
    sortby: str = "Citations",
    start_year: Optional[int] = None,
    end_year: Optional[int] = None,
    langfilter: Union[str, list] = "All",
    debug: bool = False,
    delay_seconds: float = 0,
    request_timeout: float = 15,
) -> Tuple[List[str], List[List]]:
    """Search via Semantic Scholar API. No scraping, no blocking. Same (headers, rows) format."""
    if end_year is None:
        end_year = NOW.year

    query = keyword.strip()
    if not query:
        return (HEADERS, [])

    # No filtrar manualmente: Semantic Scholar ya rankea por relevancia.
    # Filtrar por "all terms in text" descartaba papers válidos con abstracts en otro idioma.

    params: Any = {
        "query": query,
        "limit": 100,
        "offset": 0,
        "fields": SEMANTIC_SCHOLAR_FIELDS,
    }
    if start_year is not None and end_year is not None:
        params["year"] = f"{start_year}-{end_year}"

    all_data: List[Any] = []
    rows_so_far: List[List] = []
    while True:
        params["offset"] = len(all_data)
        params["limit"] = 100
        try:
            data = _semantic_scholar_request(params, request_timeout)
        except RuntimeError:
            raise
        except ValueError as e:
            raise RuntimeError(f"Invalid response from Semantic Scholar: {e}") from e

        papers = data.get("data") or []
        if not papers:
            break
        all_data.extend(papers)
        # Build filtered rows to see if we have enough; keep fetching until we do or API has no more.
        rows_so_far = []
        for p in all_data:
            title = (p.get("title") or "No title").strip()
            abstract = (p.get("abstract") or "").strip() or "—"
            year_val = p.get("year")
            year = int(year_val) if year_val is not None else 0
            citations = int(p.get("citationCount") or 0)
            authors_list = p.get("authors") or []
            author = ", ".join((a.get("name") or "").strip() for a in authors_list) if authors_list else "Unknown"
            venue = (p.get("venue") or "—").strip()
            url = (p.get("url") or "").strip() or "—"
            oa = p.get("openAccessPdf")
            pdf = (oa.get("url") if isinstance(oa, dict) and oa else None) or "No PDF link"
            if pdf and pdf != "No PDF link":
                pdf = str(pdf).strip()
            denom = end_year + 1 - min(year or 0, end_year)
            cit_per_year = int(round(citations / denom)) if denom > 0 else 0
            rows_so_far.append([len(rows_so_far) + 1, author, title, citations, year, "—", venue, abstract, url, pdf, cit_per_year])
        if len(rows_so_far) >= nresults or len(papers) < params["limit"]:
            break
        if delay_seconds > 0:
            import time
            time.sleep(delay_seconds)

    rows = rows_so_far[:nresults]
    sort_idx = 10 if sortby == "cit/year" else 3
    rows.sort(key=lambda r: (r[sort_idx], r[3]), reverse=True)
    for i, row in enumerate(rows, 1):
        row[0] = i
    return (HEADERS, rows)


def run_search(
    keyword: str,
    nresults: int = 10,
    sortby: str = "Citations",
    start_year: Optional[int] = None,
    end_year: Optional[int] = None,
    langfilter: Union[str, list] = "All",
    debug: bool = False,
    delay_seconds: float = 0,
    request_timeout: float = 15,
) -> Tuple[List[str], List[List]]:
    """Run Scholar search. Returns (headers, rows) for CSV. No pandas."""
    from time import sleep

    if end_year is None:
        end_year = NOW.year

    url = GSCHOLAR_URL
    if start_year:
        url = url + STARTYEAR_URL.format(start_year)
    if end_year != NOW.year:
        url = url + ENDYEAR_URL.format(end_year)
    if langfilter != "All" and isinstance(langfilter, list):
        url = url + LANG_URL.format(_format_lang(langfilter))
    if debug:
        url = "https://web.archive.org/web/20210314203256/" + GSCHOLAR_URL

    session = requests.Session()
    session.headers.update(REQUEST_HEADERS)
    rows: List[List] = []
    rank = 0

    # Encode query for URL (spaces as +, special chars escaped).
    query_encoded = quote_plus(keyword)

    for n in range(0, nresults, 10):
        page_url = url.format(str(n), query_encoded)
        try:
            page = session.get(page_url, timeout=request_timeout)
            c = page.content
        except Exception as e:
            raise RuntimeError(f"Request failed: {e}") from e

        try:
            page_text = c.decode("utf-8", errors="replace")
        except Exception:
            page_text = c.decode("ISO-8859-1", errors="replace")
        if any(block_kw in page_text.lower() for block_kw in ROBOT_BLOCK_KEYWORDS):
            raise RuntimeError(
                "Google Scholar está bloqueando peticiones automáticas (CAPTCHA/límite). "
                "Prueba más tarde, con otra red o con menos búsquedas seguidas."
            )

        soup = BeautifulSoup(c, "html.parser", from_encoding="utf-8")
        # Match result divs: class can be "gs_or" or "gs_r gs_or gs_scl"
        for div in soup.findAll("div", {"class": re.compile(r"gs_or")}):
            rank += 1
            try:
                link = div.find("h3").find("a").get("href")
            except Exception:
                link = "Look manually at: " + page_url
            try:
                title = div.find("h3").find("a").text
            except Exception:
                title = "Could not catch title"
            try:
                citations = _get_citations(str(div))
            except Exception:
                citations = 0
            try:
                year = _get_year(div.find("div", {"class": "gs_a"}).text)
            except Exception:
                year = 0
            try:
                author = _get_author(div.find("div", {"class": "gs_a"}).text)
            except Exception:
                author = "Author not found"
            try:
                publisher = div.find("div", {"class": "gs_a"}).text.split("-")[-1]
            except Exception:
                publisher = "Publisher not found"
            try:
                venue = " ".join(
                    div.find("div", {"class": "gs_a"}).text.split("-")[-2].split(",")[:-1]
                )
            except Exception:
                venue = "Venue not found"
            try:
                content_div = div.find("div", {"class": "gs_rs"})
                content = content_div.text if content_div else "Content not found"
            except Exception:
                content = "Content not found"
            pdf = _get_pdf_link(div) or "No PDF link"

            denom = end_year + 1 - min(year, end_year)
            cit_per_year = int(round(citations / denom)) if denom > 0 else 0
            rows.append([rank, author, title, citations, year, publisher, venue, content, link, pdf, cit_per_year])
        if delay_seconds > 0:
            sleep(delay_seconds)

    # Sort: 3=Citations, 10=cit/year
    sort_idx = 10 if sortby == "cit/year" else 3
    rows.sort(key=lambda r: r[sort_idx], reverse=True)
    for i, row in enumerate(rows, 1):
        row[0] = i
    return (HEADERS, rows)
