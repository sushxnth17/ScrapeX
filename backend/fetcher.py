"""Utilities for fetching page HTML using requests with a Playwright fallback."""

from __future__ import annotations

import logging
from typing import Optional

import requests
from playwright.sync_api import sync_playwright

try:
    from backend.exceptions import (
        ScrapeXError,
        FetchError,
        URLValidationError,
        ConnectionTimeoutError,
        ConnectionFailedError,
        HTTPClientError,
        HTTPServerError,
        EmptyOrNonHTMLContentError,
    )
except ImportError:
    from exceptions import (
        ScrapeXError,
        FetchError,
        URLValidationError,
        ConnectionTimeoutError,
        ConnectionFailedError,
        HTTPClientError,
        HTTPServerError,
        EmptyOrNonHTMLContentError,
    )

logger = logging.getLogger(__name__)

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


def fetch_with_requests(url: str) -> str:
    """Fetch HTML using requests for fast static-page retrieval.
    
    Raises specific FetchError subclasses on failure.
    """
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

        # Validate content type
        content_type = response.headers.get("Content-Type", "").lower()
        if content_type and not any(t in content_type for t in ["text/html", "application/xhtml+xml"]):
            raise EmptyOrNonHTMLContentError(f"The target URL did not return a valid HTML document. URL returned non-HTML Content-Type: {content_type}")

        if response.status_code >= 500:
            raise HTTPServerError(response.status_code)

        if response.status_code >= 400:
            raise HTTPClientError(response.status_code)

        # Some sites return challenge pages with non-200 status. If it's valid HTML,
        # pass it through and let parser/extractor decide.
        if _looks_like_html(html):
            if response.status_code != 200:
                print(f"Warning: Non-200 response ({response.status_code}) but HTML was returned")
            return html

        raise EmptyOrNonHTMLContentError("The target URL did not return a valid HTML document. Requests returned empty or non-HTML content")

    except requests.exceptions.Timeout as exc:
        raise ConnectionTimeoutError("Request timed out (15 seconds)") from exc
    except requests.exceptions.ConnectionError as exc:
        raise ConnectionFailedError("Failed to connect to the target server. Requests failed to establish connection.") from exc
    except requests.exceptions.RequestException as exc:
        raise FetchError(f"HTTP request failed: {exc}") from exc


def fetch_with_playwright(url: str) -> str:
    """Fetch HTML using Playwright for JavaScript-heavy or protected pages.
    
    Raises specific FetchError subclasses on failure.
    """
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

            response = page.goto(url, timeout=30000, wait_until="domcontentloaded")
            
            # Validate content type
            if response:
                content_type = response.headers.get("content-type", "").lower()
                if content_type and not any(t in content_type for t in ["text/html", "application/xhtml+xml"]):
                    raise EmptyOrNonHTMLContentError(f"The target URL did not return a valid HTML document. URL returned non-HTML Content-Type: {content_type}")
                    
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

            raise EmptyOrNonHTMLContentError("The target URL did not return a valid HTML document. Playwright returned empty or non-HTML content")
    except Exception as exc:
        if isinstance(exc, EmptyOrNonHTMLContentError):
            raise exc
        if "timeout" in str(exc).lower():
            raise ConnectionTimeoutError("Playwright timed out while loading the page.") from exc
        else:
            raise ConnectionFailedError(f"Failed to connect to the target server. Playwright failed to load page: {exc}") from exc


def fetch_html(url: str) -> str:
    """
    Fetch HTML from a URL with fallback mechanism.
    
    Attempts to fetch HTML using requests first. If that fails, falls back
    to Playwright for JavaScript-heavy websites.
    
    Args:
        url: The URL to fetch
        
    Returns:
        HTML text if successful
        
    Raises:
        URLValidationError, FetchError subclasses
    """
    global LAST_FETCH_METHOD
    LAST_FETCH_METHOD = "Unknown"
    
    # Validate URL
    if not url or not url.strip():
        raise URLValidationError("URL cannot be empty or blank.")
        
    url_stripped = url.strip()
    from urllib.parse import urlparse
    parsed = urlparse(url_stripped)
    
    if not parsed.scheme:
        raise URLValidationError("Invalid URL: Missing scheme (e.g. http:// or https:// is required).")
        
    scheme = parsed.scheme.lower()
    if scheme not in ["http", "https"]:
        raise URLValidationError(f"Invalid URL: Unsupported protocol '{scheme}'. Only http:// and https:// are supported.")
        
    if not parsed.netloc:
        raise URLValidationError("Invalid URL: Missing domain/host name.")
        
    requests_err = None
    
    # Try requests first (faster)
    try:
        html = fetch_with_requests(url_stripped)
        if html:
            print("Fetched using requests")
            LAST_FETCH_METHOD = "Requests"
            return html
    except FetchError as err:
        requests_err = err
    except Exception as err:
        requests_err = FetchError(f"Unexpected requests error: {err}")
    
    # Fallback to Playwright for JS-heavy sites
    print(f"Requests failed ({requests_err}). Trying Playwright...")
    try:
        html = fetch_with_playwright(url_stripped)
        if html:
            print("Fetched using Playwright")
            LAST_FETCH_METHOD = "Playwright"
            return html
    except FetchError as err:
        # If Playwright also fails, raise the Playwright error or the more descriptive one
        logger.warning(f"Playwright fallback also failed: {err}")
        if requests_err:
            raise requests_err
        raise err
    except Exception as err:
        logger.warning(f"Playwright fallback failed with unexpected error: {err}")
        if requests_err:
            raise requests_err
        raise FetchError(f"Failed to fetch content from both methods. Playwright error: {err}")
    
    # If Playwright returned successfully but HTML check somehow bypassed and it was empty/non-HTML
    if requests_err:
        raise requests_err
    raise EmptyOrNonHTMLContentError("Failed to fetch content from both methods.")


if __name__ == "__main__":
    try:
        url = input("Enter the URL to fetch: ").strip()
        
        if not url:
            print("Error: URL cannot be empty")
        else:
            try:
                html = fetch_html(url)
                print(f"\n{'='*60}")
                print("First 500 characters of fetched HTML:")
                print(f"{'='*60}")
                print(html[:500])
            except ScrapeXError as exc:
                print(f"Error: {exc.detail}")
            except Exception as exc:
                print(f"Unexpected error: {exc}")
                
    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user")
