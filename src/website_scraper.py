"""
Async website scraper.
Fetches homepage, /about, /products, /services, /careers pages.
Returns raw text content for LLM analysis.
"""

import asyncio
import logging
import re
from typing import Optional
from urllib.parse import urljoin, urlparse

import aiohttp
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

TARGET_PATHS = ["/", "/about", "/about-us", "/company",
                "/products", "/services", "/careers",
                "/csr", "/sustainability", "/internships"]

MAX_CHARS_PER_PAGE = 3000
MAX_TOTAL_CHARS    = 8000
TIMEOUT_SECS       = 15


def _normalise_url(url: str) -> str:
    url = url.strip()
    if not url:
        return ""
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    return url


def _extract_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()
    text = soup.get_text(separator=" ", strip=True)
    text = re.sub(r"\s+", " ", text)
    return text[:MAX_CHARS_PER_PAGE]


async def _fetch_page(session: aiohttp.ClientSession, url: str) -> Optional[str]:
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=TIMEOUT_SECS),
                               allow_redirects=True) as resp:
            if resp.status == 200:
                html = await resp.text(errors="replace")
                return _extract_text(html)
    except Exception as e:
        logger.debug(f"Failed to fetch {url}: {e}")
    return None


async def scrape_company_website(website_url: str) -> str:
    """
    Scrape key pages of a company website and return concatenated text.
    Returns empty string on failure.
    """
    base = _normalise_url(website_url)
    if not base:
        return ""

    parsed = urlparse(base)
    origin = f"{parsed.scheme}://{parsed.netloc}"

    collected: list[str] = []

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
    }

    connector = aiohttp.TCPConnector(ssl=False)
    async with aiohttp.ClientSession(headers=headers, connector=connector) as session:
        tasks = [_fetch_page(session, urljoin(origin, path)) for path in TARGET_PATHS]
        results = await asyncio.gather(*tasks, return_exceptions=True)

    for result in results:
        if isinstance(result, str) and result.strip():
            collected.append(result)

    combined = " | ".join(collected)
    return combined[:MAX_TOTAL_CHARS]


async def search_company_duckduckgo(query: str) -> str:
    """
    Search DuckDuckGo for a custom query.
    Returns snippet text.
    """
    url   = f"https://html.duckduckgo.com/html/?q={aiohttp.helpers.quote(query)}"

    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"
    }

    try:
        connector = aiohttp.TCPConnector(ssl=False)
        async with aiohttp.ClientSession(headers=headers, connector=connector) as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                if resp.status == 200:
                    html = await resp.text(errors="replace")
                    soup = BeautifulSoup(html, "html.parser")
                    snippets = [s.get_text(strip=True)
                                for s in soup.select(".result__snippet")[:5]]
                    return " | ".join(snippets)[:3000]
    except Exception as e:
        logger.debug(f"DuckDuckGo search failed for query '{query}': {e}")
    return ""

