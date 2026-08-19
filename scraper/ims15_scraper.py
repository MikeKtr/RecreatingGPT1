"""
IBM IMS 15 Documentation Scraper
Scrapes https://www.ibm.com/docs/en/ims/15.0.0 and saves all pages to a single TXT file.

Requirements:
    pip install requests beautifulsoup4
"""

import time
import re
import sys
from collections import deque
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

# ── Configuration ─────────────────────────────────────────────────────────────

BASE_URL = "https://www.ibm.com/docs/en/ims/15.0.0"
OUTPUT_FILE = "ims15_docs.txt"
REQUEST_DELAY = 1.5          # seconds between requests (be polite)
REQUEST_TIMEOUT = 30         # seconds
MAX_RETRIES = 3

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; IMS-doc-scraper/1.0; "
        "+https://github.com/example/ims-scraper)"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

# Only follow links that stay inside the IMS 15 docs subtree
ALLOWED_PREFIX = "/docs/en/ims/15.0.0"

# CSS selectors to try for the main content area (IBM Docs uses different layouts)
CONTENT_SELECTORS = [
    "main",
    "article",
    '[role="main"]',
    ".ibm-content-body",
    "#content",
    ".bodycopy",
]

# ── Helpers ───────────────────────────────────────────────────────────────────

def get_page(session: requests.Session, url: str) -> BeautifulSoup | None:
    """Fetch a page and return a BeautifulSoup object, or None on failure."""
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = session.get(url, timeout=REQUEST_TIMEOUT, headers=HEADERS)
            if resp.status_code == 200:
                return BeautifulSoup(resp.text, "html.parser")
            if resp.status_code == 429:
                wait = int(resp.headers.get("Retry-After", 60))
                print(f"  [rate-limit] waiting {wait}s …", flush=True)
                time.sleep(wait)
            else:
                print(f"  [HTTP {resp.status_code}] {url}", flush=True)
                return None
        except requests.RequestException as exc:
            print(f"  [error attempt {attempt}/{MAX_RETRIES}] {exc}", flush=True)
            time.sleep(5 * attempt)
    return None


def extract_text(soup: BeautifulSoup) -> str:
    """Extract readable text from the main content area of a page."""
    # Try known content containers first
    content = None
    for selector in CONTENT_SELECTORS:
        content = soup.select_one(selector)
        if content:
            break

    if content is None:
        content = soup.body or soup

    # Remove non-content tags
    for tag in content.select("nav, header, footer, script, style, .feedback, "
                               ".ibm-navigation, .ibm-toc, [aria-hidden='true']"):
        tag.decompose()

    # Convert to plain text: preserve heading levels with #, keep list bullets
    lines = []
    for element in content.descendants:
        if not hasattr(element, "name"):          # NavigableString
            text = element.strip()
            if text:
                lines.append(text)
        elif element.name in ("h1", "h2", "h3", "h4", "h5", "h6"):
            level = int(element.name[1])
            heading = element.get_text(" ", strip=True)
            if heading:
                lines.append("")
                lines.append("#" * level + " " + heading)
                lines.append("")
        elif element.name in ("li",):
            item = element.get_text(" ", strip=True)
            if item:
                lines.append("• " + item)
        elif element.name in ("tr",):
            cells = [td.get_text(" ", strip=True)
                     for td in element.find_all(["th", "td"])]
            if any(cells):
                lines.append(" | ".join(cells))
        elif element.name in ("p", "pre", "code", "blockquote"):
            text = element.get_text(" ", strip=True)
            if text:
                lines.append(text)

    raw = "\n".join(lines)
    # Collapse runs of 3+ blank lines down to 2
    raw = re.sub(r"\n{3,}", "\n\n", raw)
    return raw.strip()


def collect_links(soup: BeautifulSoup, current_url: str) -> list[str]:
    """Return all in-scope doc links found on a page."""
    links = []
    for a in soup.find_all("a", href=True):
        href = a["href"].split("#")[0]          # drop anchors
        full = urljoin(current_url, href)
        parsed = urlparse(full)
        if (parsed.netloc == "www.ibm.com"
                and parsed.path.startswith(ALLOWED_PREFIX)
                and full not in (current_url,)):
            links.append(full)
    return links


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    session = requests.Session()
    session.headers.update(HEADERS)

    visited: set[str] = set()
    queue: deque[str] = deque([BASE_URL])
    page_count = 0

    print(f"Starting scrape of {BASE_URL}")
    print(f"Output → {OUTPUT_FILE}\n")

    with open(OUTPUT_FILE, "w", encoding="utf-8") as out:
        out.write(f"IBM IMS 15.0.0 Documentation\n")
        out.write(f"Source: {BASE_URL}\n")
        out.write("=" * 80 + "\n\n")

        while queue:
            url = queue.popleft()
            if url in visited:
                continue
            visited.add(url)

            print(f"[{page_count + 1:>5}] {url}", flush=True)
            soup = get_page(session, url)
            if soup is None:
                continue

            # Page title
            title_tag = soup.find("title")
            page_title = title_tag.get_text(strip=True) if title_tag else url

            # Extract and write content
            text = extract_text(soup)
            if text:
                out.write(f"\n{'=' * 80}\n")
                out.write(f"PAGE: {page_title}\n")
                out.write(f"URL:  {url}\n")
                out.write(f"{'=' * 80}\n\n")
                out.write(text)
                out.write("\n")
                page_count += 1

            # Enqueue new links
            for link in collect_links(soup, url):
                if link not in visited:
                    queue.append(link)

            time.sleep(REQUEST_DELAY)

    print(f"\nDone. Scraped {page_count} pages → {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
