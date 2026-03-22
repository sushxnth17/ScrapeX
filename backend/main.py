"""Main pipeline that orchestrates fetching, extraction, and parsing for ScrapeX."""

from __future__ import annotations

from typing import Any, Dict, Optional

from extractor import extract_content
from fetcher import fetch_html
from parser import parse_html


def scrape(url: str) -> Optional[Dict[str, Any]]:
    """Run the full scraping pipeline and return normalized output.

    Pipeline stages:
    1. Fetch HTML from the target URL.
    2. Extract clean readable content.
    3. Parse structured elements from HTML.
    4. Merge all available results into a single dictionary.

    If fetching fails, returns None. If extraction or parsing fail, returns
    partial data from the stage(s) that succeeded.

    Args:
        url: Target URL to scrape.

    Returns:
        A dictionary containing normalized scrape results, or None if fetch
        stage fails.
    """
    print("Fetching...")
    html = fetch_html(url)
    if html is None:
        print("Error: Failed to fetch HTML.")
        return None

    extracted: Optional[Dict[str, str]] = None
    print("Extracting...")
    try:
        extracted = extract_content(html)
        if extracted is None:
            print("Warning: Content extraction returned no clean text.")
    except Exception as exc:
        print(f"Warning: Extractor failed: {exc}")
        extracted = None

    parsed: Dict[str, Any] = {}
    print("Parsing...")
    try:
        parsed = parse_html(html) or {}
    except Exception as exc:
        print(f"Warning: Parser failed: {exc}")
        parsed = {}

    # Decide clean text (fallback logic)
    if extracted and extracted.get("text"):
        clean_text = extracted["text"]
    else:
        clean_text = " ".join(parsed.get("paragraphs", []))

    result: Dict[str, Any] = {
        "url": url,
        "title": (extracted or {}).get("title") or parsed.get("title", ""),
        "clean_text": clean_text,
        "content_length": len(clean_text),
        "headings": parsed.get("headings", []),
        "paragraphs": parsed.get("paragraphs", []),
        "links": parsed.get("links", []),
        "tables": parsed.get("tables", []),
    }

    print("Done.")
    return result


def _print_summary(result: Dict[str, Any]) -> None:
    """Print a compact summary of scrape results for CLI usage."""
    print(f"URL: {result.get('url', '')}")
    print(f"Title: {result.get('title', '') or 'N/A'}")
    print(f"Content length: {result.get('content_length', 0)}")
    print(f"Headings count: {len(result.get('headings', []))}")
    print(f"Paragraphs count: {len(result.get('paragraphs', []))}")
    print(f"Links count: {len(result.get('links', []))}")
    print(f"Tables count: {len(result.get('tables', []))}")


if __name__ == "__main__":
    """Interactive test block for the main scraping engine."""
    try:
        user_url = input("Enter URL: ").strip()
        if not user_url:
            print("Error: URL cannot be empty.")
        else:
            scrape_result = scrape(user_url)
            if scrape_result is None:
                print("No result returned.")
            else:
                _print_summary(scrape_result)
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")