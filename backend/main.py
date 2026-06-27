"""Main pipeline that orchestrates fetching, AI analysis, extraction, and parsing for ScrapeX."""

from __future__ import annotations

from typing import Any, Dict, Optional

try:
    from . import fetcher
    from .extractor import extract_content
    from .parser import parse_html
    from .ai import AIAnalyzer
except ImportError:
    import fetcher
    from extractor import extract_content
    from parser import parse_html
    from ai import AIAnalyzer


def scrape(url: str) -> Optional[Dict[str, Any]]:
    """Run the AI-guided scraping pipeline and return normalized output.

    Pipeline stages:
    1. Fetch HTML from the target URL.
    2. Run AI analysis to determine page architecture and optimal extraction strategy.
    3. Execute extraction and parsing according to AI recommendation ('article', 'table', or 'mixed').
    4. Merge all available results into a single dictionary.

    Args:
        url: Target URL to scrape.

    Returns:
        A dictionary containing normalized scrape results, or None if fetch stage fails.
    """
    print("Fetching...")
    html = fetcher.fetch_html(url)
    if html is None:
        print("Error: Failed to fetch HTML.")
        return None

    # Run AI analysis before parsing/extraction
    print("Running AI analysis...")
    ai_analysis_dict: Optional[Dict[str, Any]] = None
    rec_strategy: str = "mixed"

    try:
        analyzer = AIAnalyzer()
        analysis = analyzer.analyze_page(html, url)
        ai_analysis_dict = analysis.to_dict()
        rec_strategy = (analysis.recommended_strategy or analysis.scrape_strategy or "mixed").lower()
    except Exception as exc:
        print(f"Warning: AI analysis failed during pipeline execution: {exc}")

    print(f"AI Recommended Strategy: {rec_strategy}")

    extracted: Optional[Dict[str, str]] = None
    parsed: Dict[str, Any] = {}

    # Always execute HTML DOM parser to capture structured elements (tables, headings, links)
    try:
        parsed = parse_html(html) or {}
    except Exception as exc:
        print(f"Warning: Parser failed: {exc}")
        parsed = {}

    # Execute text extraction based on AI recommendation
    if "table" in rec_strategy and "article" not in rec_strategy:
        print("Strategy: Table focus. Prioritizing structured DOM elements...")
        # For pure table strategy, run extractor only if text content is missing
        if not parsed.get("paragraphs"):
            try:
                extracted = extract_content(html)
            except Exception as exc:
                print(f"Warning: Extractor fallback failed: {exc}")
    else:
        # For article or mixed focus, run content extractor for clean body text
        print("Strategy: Article/Mixed focus. Running content extractor...")
        try:
            extracted = extract_content(html)
        except Exception as exc:
            print(f"Warning: Extractor failed: {exc}")

    # Decide clean text
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
        "scrape_method": getattr(fetcher, "LAST_FETCH_METHOD", "Unknown"),
    }

    if ai_analysis_dict:
        result["ai_analysis"] = ai_analysis_dict

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
    if "ai_analysis" in result:
        print(f"AI Strategy: {result['ai_analysis'].get('recommended_strategy', 'N/A')}")


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