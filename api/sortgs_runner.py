"""
Self-contained Google Scholar search for Vercel serverless (no dependency on src/sortgs).
Uses only requests, BeautifulSoup, pandas. No selenium. Optional delay between requests.
"""
import datetime
import re
from typing import List, Optional, Union

import pandas as pd
import requests
from bs4 import BeautifulSoup

GSCHOLAR_URL = "https://scholar.google.com/scholar?start={}&q={}&hl=en&as_sdt=0,5"
STARTYEAR_URL = "&as_ylo={}"
ENDYEAR_URL = "&as_yhi={}"
LANG_URL = "&lr={}"
NOW = datetime.datetime.now()


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


def run_search(
    keyword: str,
    nresults: int = 10,
    sortby: str = "Citations",
    start_year: Optional[int] = None,
    end_year: Optional[int] = None,
    langfilter: Union[str, list] = "All",
    debug: bool = False,
    delay_seconds: float = 0,
) -> pd.DataFrame:
    """Run Scholar search; no selenium. delay_seconds=0 for serverless to avoid timeout."""
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
    links, title, citations, year = [], [], [], []
    author, venue, publisher, content, pdf_links = [], [], [], [], []
    rank = [0]

    for n in range(0, nresults, 10):
        page_url = url.format(str(n), keyword.replace(" ", "+"))
        try:
            page = session.get(page_url, timeout=15)
            c = page.content
        except Exception as e:
            raise RuntimeError(f"Request failed: {e}") from e

        soup = BeautifulSoup(c, "html.parser", from_encoding="utf-8")
        for div in soup.findAll("div", {"class": "gs_or"}):
            try:
                links.append(div.find("h3").find("a").get("href"))
            except Exception:
                links.append("Look manually at: " + page_url)
            try:
                title.append(div.find("h3").find("a").text)
            except Exception:
                title.append("Could not catch title")
            try:
                citations.append(_get_citations(str(div)))
            except Exception:
                citations.append(0)
            try:
                year.append(_get_year(div.find("div", {"class": "gs_a"}).text))
            except Exception:
                year.append(0)
            try:
                author.append(_get_author(div.find("div", {"class": "gs_a"}).text))
            except Exception:
                author.append("Author not found")
            try:
                publisher.append(div.find("div", {"class": "gs_a"}).text.split("-")[-1])
            except Exception:
                publisher.append("Publisher not found")
            try:
                venue.append(
                    " ".join(
                        div.find("div", {"class": "gs_a"})
                        .text.split("-")[-2]
                        .split(",")[:-1]
                    )
                )
            except Exception:
                venue.append("Venue not found")
            try:
                content_div = div.find("div", {"class": "gs_rs"})
                content.append(content_div.text if content_div else "Content not found")
            except Exception:
                content.append("Content not found")
            pdf_links.append(_get_pdf_link(div) or "No PDF link")
            rank.append(rank[-1] + 1)
        if delay_seconds > 0:
            sleep(delay_seconds)

    data = pd.DataFrame(
        list(zip(author, title, citations, year, publisher, venue, content, links, pdf_links)),
        index=rank[1:],
        columns=[
            "Author", "Title", "Citations", "Year", "Publisher", "Venue",
            "Content", "Source", "PDF",
        ],
    )
    data.index.name = "Rank"
    data["cit/year"] = data["Citations"] / (
        end_year + 1 - data["Year"].clip(upper=end_year)
    )
    data["cit/year"] = data["cit/year"].round(0).astype(int)
    try:
        data_ranked = data.sort_values(by=sortby, ascending=False)
    except Exception:
        data_ranked = data.sort_values(by="Citations", ascending=False)
    return data_ranked
