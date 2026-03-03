#!/usr/bin/env python3

# -*- coding: utf-8 -*-
"""
This code creates a database with a list of publications data from Google
Scholar.
The data acquired from GS is Title, Citations, Links and Rank.
It is useful for finding relevant papers by sorting by the number of citations
This example will look for the top 100 papers related to the keyword,
so that you can rank them by the number of citations

As output this program will plot the number of citations in the Y axis and the
rank of the result in the X axis. It also, optionally, export the database to
a .csv file.


"""

import requests
import datetime
import argparse
from typing import Optional, Union

from bs4 import BeautifulSoup
import matplotlib.pyplot as plt
import pandas as pd
from time import sleep
import random
import re
import logging
import sys
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Removed Python 2 compatibility for raw_input; using input() directly

# Default Parameters
KEYWORD = "machine learning"  # Default argument if command line is empty
NRESULTS = 100  # Fetch 100 articles
CSVPATH = Path.cwd()  # Default path as current working directory
SAVECSV = True
SORTBY = "Citations"
PLOT_RESULTS = False
STARTYEAR = None
now = datetime.datetime.now()
ENDYEAR = now.year  # Current year
DEBUG = False  # debug mode
MAX_CSV_FNAME = 255
LANG = "All"


# Websession Parameters
GSCHOLAR_URL = "https://scholar.google.com/scholar?start={}&q={}&hl=en&as_sdt=0,5"
YEAR_RANGE = ""  # &as_ylo={start_year}&as_yhi={end_year}'
# GSCHOLAR_URL_YEAR = GSCHOLAR_URL+YEAR_RANGE
STARTYEAR_URL = "&as_ylo={}"
ENDYEAR_URL = "&as_yhi={}"
LANG_URL = "&lr={}"

ROBOT_KW = ["unusual traffic from your computer network", "not a robot"]

# Set up logging
logging.basicConfig(level=logging.INFO)

# Initialize module logger
logger = logging.getLogger(__name__)


def get_command_line_args():
    # Command line arguments
    parser = argparse.ArgumentParser(description="Arguments")
    parser.add_argument(
        "kw",
        type=str,
        help="""Keyword to be searched. Use double quote followed by simple quote to search for an exact keyword. Example: "'exact keyword'" """,
        default=KEYWORD,
    )
    parser.add_argument(
        "--sortby",
        type=str,
        help='Column to be sorted by. Default is by the columns "Citations", i.e., it will be sorted by the number of citations. If you want to sort by citations per year, use --sortby "cit/year"',
    )
    parser.add_argument(
        "--langfilter",
        nargs="+",
        type=str,
        help="Only languages listed are permitted to pass the filter. List of supported language codes: zh-CN, zh-TW, nl, en, fr, de, it, ja, ko, pl, pt, es, tr",
    )

    parser.add_argument(
        "--nresults",
        type=int,
        help="Number of articles to search on Google Scholar. Default is 100. (carefull with robot checking if value is too high)",
    )
    parser.add_argument(
        "--csvpath",
        type=str,
        help="Path to save the exported csv file. By default it is the current folder",
    )
    parser.add_argument(
        "--notsavecsv",
        action="store_true",
        help="By default results are going to be exported to a csv file. Select this option to just print results but not store them",
    )
    parser.add_argument(
        "--plotresults",
        action="store_true",
        help="Use this flag in order to plot the results with the original rank in the x-axis and the number of citaions in the y-axis. Default is False",
    )
    parser.add_argument(
        "--startyear", type=int, help="Start year when searching. Default is None"
    )
    parser.add_argument(
        "--endyear", type=int, help="End year when searching. Default is current year"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Debug mode. Used for unit testing. It will get pages stored on web archive",
    )

    # Parse and read arguments and assign them to variables if exists
    args, _ = parser.parse_known_args()

    # Check if no arguments were provided and print help if so
    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(0)

    keyword = KEYWORD
    if args.kw:
        keyword = args.kw

    nresults = NRESULTS
    if args.nresults:
        nresults = args.nresults

    csvpath = CSVPATH
    if args.csvpath:
        csvpath = args.csvpath

    save_csv = SAVECSV
    if args.notsavecsv:
        save_csv = False

    sortby = SORTBY
    if args.sortby:
        sortby = args.sortby

    langfilter = LANG
    if args.langfilter:
        langfilter = args.langfilter

    plot_results = False
    if args.plotresults:
        plot_results = True

    start_year = STARTYEAR
    if args.startyear:
        start_year = args.startyear

    end_year = ENDYEAR
    if args.endyear:
        end_year = args.endyear

    debug = DEBUG
    if args.debug:
        debug = True

    return (
        keyword,
        nresults,
        save_csv,
        csvpath,
        sortby,
        langfilter,
        plot_results,
        start_year,
        end_year,
        debug,
    )


def get_citations(content: str) -> int:
    """Extract number of citations from content using regex."""
    match = re.search(r"Cited by (\d+)", content)
    return int(match.group(1)) if match else 0


def get_year(content: str) -> int:
    """Extract publication year from content using regex."""
    match = re.search(r"\b(19|20)\d{2}\b", content)
    return int(match.group(0)) if match else 0


def setup_driver() -> webdriver.Chrome:
    logger.info("Initializing WebDriver")
    chrome_options = Options()
    chrome_options.add_argument("disable-infobars")
    driver = webdriver.Chrome(options=chrome_options)
    return driver


def get_author(content: str) -> str:
    """Extract the author string from content."""
    clean_content = content.replace("\xa0", " ")
    return clean_content.split(" - ")[0] if clean_content else ""


def get_element(driver, xpath: str, attempts: int = 5, _count: int = 0):
    """Safely find an element by xpath with retries using updated selenium API."""
    try:
        return driver.find_element(By.XPATH, xpath)
    except Exception:
        if _count < attempts:
            sleep(random.uniform(0.5, 3))
            return get_element(driver, xpath, attempts=attempts, _count=_count + 1)
        logger.error("Element not found after %s attempts: %s", attempts, xpath)
        return None


def get_content_with_selenium(url):
    if "driver" not in globals():
        global driver
        driver = setup_driver()
    driver.get(url)

    while True:
        # Wait for a specific element that indicates the page has loaded
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )

        # Get the body element
        el = driver.find_element(By.TAG_NAME, "body")

        c = el.get_attribute("innerHTML")
        if any(kw in el.text for kw in ROBOT_KW):
            input("Solve captcha manually and press enter here to continue...")
        else:
            break

    return c.encode("utf-8")


def format_strings(strings):
    if len(strings) == 1:
        return f"lang_{strings[0]}"
    else:
        return "%7C".join(f"lang_{s}" for s in strings)


def get_pdf_link(div):
    """Extract PDF link from the Google Scholar result if available"""
    try:
        pdf_div = div.find("div", {"class": "gs_ggs gs_fl"})
        if pdf_div:
            a_tag = pdf_div.find("a")
            if a_tag:
                return a_tag.get("href")
    except Exception:
        pass
    return None


def run_search(
    keyword: str,
    nresults: int = NRESULTS,
    sortby: str = SORTBY,
    start_year: Optional[int] = STARTYEAR,
    end_year: Optional[int] = None,
    langfilter: Union[str, list] = LANG,
    debug: bool = DEBUG,
) -> pd.DataFrame:
    """
    Run a Google Scholar search and return results as a sorted DataFrame.
    Can be called programmatically (e.g. from an API) without CLI args.
    """
    if end_year is None:
        end_year = now.year

    logger.info(
        "Running with parameters: Keyword: %s, nresults: %s, sortby: %s, "
        "langfilter: %s, start_year: %s, end_year: %s, debug: %s",
        keyword,
        nresults,
        sortby,
        langfilter,
        start_year,
        end_year,
        debug,
    )

    if start_year:
        gscholar_main_url = GSCHOLAR_URL + STARTYEAR_URL.format(start_year)
    else:
        gscholar_main_url = GSCHOLAR_URL

    if end_year != now.year:
        gscholar_main_url = gscholar_main_url + ENDYEAR_URL.format(end_year)

    if langfilter != "All":
        formatted_filters = format_strings(langfilter)
        gscholar_main_url = gscholar_main_url + LANG_URL.format(formatted_filters)

    if debug:
        gscholar_main_url = "https://web.archive.org/web/20210314203256/" + GSCHOLAR_URL

    session = requests.Session()
    links = []
    title = []
    citations = []
    year = []
    author = []
    venue = []
    publisher = []
    content = []
    pdf_links = []
    rank = [0]

    for n in range(0, nresults, 10):
        url = gscholar_main_url.format(str(n), keyword.replace(" ", "+"))
        if debug:
            logger.debug("Opening URL: %s", url)
        logger.info("Loading next %d results", n + 10)
        page = session.get(url)
        c = page.content
        if any(kw in c.decode("ISO-8859-1") for kw in ROBOT_KW):
            logger.warning("Robot check detected, using Selenium fallback")
            try:
                c = get_content_with_selenium(url)
            except Exception:
                logger.exception("Failed to fetch content with Selenium for URL: %s", url)

        soup = BeautifulSoup(c, "html.parser", from_encoding="utf-8")
        mydivs = soup.findAll("div", {"class": "gs_or"})
        for div in mydivs:
            try:
                links.append(div.find("h3").find("a").get("href"))
            except Exception:
                links.append("Look manually at: " + url)
            try:
                title.append(div.find("h3").find("a").text)
            except Exception:
                title.append("Could not catch title")
            try:
                citations.append(get_citations(str(div.format_string)))
            except Exception:
                logger.warning("Number of citations not found for %s. Appending 0", title[-1])
                citations.append(0)
            try:
                year.append(get_year(div.find("div", {"class": "gs_a"}).text))
            except Exception:
                logger.warning("Year not found for %s, appending 0", title[-1])
                year.append(0)
            try:
                author.append(get_author(div.find("div", {"class": "gs_a"}).text))
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
                venue.append("Venue not fount")
            try:
                content_div = div.find("div", {"class": "gs_rs"})
                content.append(content_div.text if content_div else "Content not found")
            except Exception:
                content.append("Content not found")
            pdf_links.append(get_pdf_link(div) or "No PDF link")
            rank.append(rank[-1] + 1)
        sleep(random.uniform(0.5, 3))

    data = pd.DataFrame(
        list(
            zip(
                author,
                title,
                citations,
                year,
                publisher,
                venue,
                content,
                links,
                pdf_links,
            )
        ),
        index=rank[1:],
        columns=[
            "Author",
            "Title",
            "Citations",
            "Year",
            "Publisher",
            "Venue",
            "Content",
            "Source",
            "PDF",
        ],
    )
    data.index.name = "Rank"
    data["cit/year"] = data["Citations"] / (
        end_year + 1 - data["Year"].clip(upper=end_year)
    )
    data["cit/year"] = data["cit/year"].round(0).astype(int)

    try:
        data_ranked = data.sort_values(by=sortby, ascending=False)
    except Exception as e:
        logger.warning(
            "Sort column '%s' not found. Falling back to 'Citations'", sortby
        )
        data_ranked = data.sort_values(by="Citations", ascending=False)
        logger.debug("Sorting error details: %s", e)

    logger.info("Results:\n%s", data_ranked.to_string())
    return data_ranked


def main():
    (
        keyword,
        number_of_results,
        save_database,
        path,
        sortby_column,
        langfilter,
        plot_results,
        start_year,
        end_year,
        debug,
    ) = get_command_line_args()

    logger.info(
        "Running with parameters: Keyword: %s, Number of results: %s, Save database: %s, "
        "Path: %s, Sort by: %s, Permitted Languages: %s, Plot results: %s, "
        "Start year: %s, End year: %s, Debug: %s",
        keyword,
        number_of_results,
        save_database,
        path,
        sortby_column,
        langfilter,
        plot_results,
        start_year,
        end_year,
        debug,
    )

    data_ranked = run_search(
        keyword=keyword,
        nresults=number_of_results,
        sortby=sortby_column,
        start_year=start_year,
        end_year=end_year,
        langfilter=langfilter,
        debug=debug,
    )

    if plot_results:
        rank_vals = list(range(1, len(data_ranked) + 1))
        plt.plot(rank_vals, data_ranked["Citations"].tolist(), "*")
        plt.ylabel("Number of Citations")
        plt.xlabel("Rank of the keyword on Google Scholar")
        plt.title("Keyword: " + keyword)
        plt.show()

    if save_database:
        csv_file_name = f"{keyword.replace(' ', '_').replace(':', '_')}.csv"
        csv_path = Path(path) / csv_file_name
        if len(csv_path.name) > MAX_CSV_FNAME:
            csv_path = csv_path.with_name(csv_path.name[:MAX_CSV_FNAME])
        data_ranked.to_csv(csv_path, encoding="utf-8")
        logger.info("Results saved to %s", csv_path)


if __name__ == "__main__":
    main()
