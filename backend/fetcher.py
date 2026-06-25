"""Utilities for fetching page HTML using requests with a Playwright fallback."""

from __future__ import annotations

from typing import Optional

import requests
from playwright.sync_api import sync_playwright


MIN_HTML_LENGTH = 500
LAST_FETCH_METHOD = "Unknown"
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)


def _looks_like_html(html: str) -> bool:
    """Return True when content appears to be a real HTML document."""
    if not html:
        return False

    text = html.strip()
    if len(text) < MIN_HTML_LENGTH:
        return False

    lower = text.lower()
    return "<html" in lower or "<!doctype html" in lower


def fetch_with_requests(url: str) -> Optional[str]:
    """Fetch HTML using requests for fast static-page retrieval."""
    print(f"Trying requests for: {url}")
    headers = {
        "User-Agent": DEFAULT_USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
    }

    try:
        response = requests.get(url, headers=headers, timeout=15, allow_redirects=True)
        response.encoding = response.apparent_encoding
        html = response.text or ""

        if response.status_code >= 500:
            print(f"Error: HTTP {response.status_code}")
            return None

        # Some sites return challenge pages with non-200 status. If it's valid HTML,
        # pass it through and let parser/extractor decide.
        if _looks_like_html(html):
            if response.status_code != 200:
                print(f"Warning: Non-200 response ({response.status_code}) but HTML was returned")
            return html

        print("Requests returned empty or non-HTML content")
        return None

    except requests.exceptions.Timeout:
        print("Error: Request timed out (15 seconds)")
        return None
    except requests.exceptions.ConnectionError:
        print("Requests failed, trying Playwright...")
        return None
    except requests.exceptions.RequestException as exc:
        print(f"Error: {exc}")
        return None


def fetch_with_playwright(url: str) -> Optional[str]:
    """Fetch HTML using Playwright for JavaScript-heavy or protected pages."""
    print(f"Trying Playwright for: {url}")
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=["--disable-blink-features=AutomationControlled"],
            )
            context = browser.new_context(
                user_agent=DEFAULT_USER_AGENT,
                viewport={"width": 1440, "height": 900},
                locale="en-US",
            )
            page = context.new_page()

            page.goto(url, timeout=30000, wait_until="domcontentloaded")
            page.wait_for_timeout(2500)

            # Trigger potential lazy-loading sections.
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            page.wait_for_timeout(1200)

            html = page.content() or ""
            if _looks_like_html(html):
                return html

            # Retry with a stricter wait strategy before giving up.
            page.reload(timeout=30000, wait_until="networkidle")
            page.wait_for_timeout(1500)
            html = page.content() or ""
            if _looks_like_html(html):
                return html

            print("Error: Playwright returned empty or non-HTML content")
            return None
    except Exception as exc:
        print(f"Error: Playwright failed - {exc}")
        return None


def fetch_html(url: str) -> Optional[str]:
    """
    Fetch HTML from a URL with fallback mechanism.
    
    Attempts to fetch HTML using requests first. If that fails, falls back
    to Playwright for JavaScript-heavy websites.
    
    Args:
        url: The URL to fetch
        
    Returns:
        HTML text if successful, None otherwise
    """
    global LAST_FETCH_METHOD
    LAST_FETCH_METHOD = "Unknown"
    # Validate URL
    if not url.startswith("http"):
        print("Invalid URL. Please include http/https")
        return None
    # Try requests first (faster)
    html = fetch_with_requests(url)
    if html:
        print("Fetched using requests")
        LAST_FETCH_METHOD = "Requests"
        return html
    
    # Fallback to Playwright for JS-heavy sites
    print("Requests failed, trying Playwright...")
    html = fetch_with_playwright(url)
    if html:
        print("Fetched using Playwright")
        LAST_FETCH_METHOD = "Playwright"
        return html
    
    print("Error: Failed to fetch content from both methods")
    return None


if __name__ == "__main__":
    try:
        url = input("Enter the URL to fetch: ").strip()
        
        if not url:
            print("Error: URL cannot be empty")
        else:
            html = fetch_html(url)
            
            if html:
                print(f"\n{'='*60}")
                print("First 500 characters of fetched HTML:")
                print(f"{'='*60}")
                print(html[:500])
            else:
                print("Failed to fetch content")
                
    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user")
