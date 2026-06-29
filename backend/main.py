"""Main pipeline that orchestrates fetching, DOM compression, AI analysis, strategy determination, adaptive extraction, and parsing for ScrapeX."""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

try:
    from . import fetcher
    from .extractor import extract_content
    from .parser import parse_html
    from .ai import AIAnalysis, AIAnalyzer, DOMCompressor, Strategy, StrategyEngine
except ImportError:
    import fetcher
    from extractor import extract_content
    from parser import parse_html
    from ai import AIAnalysis, AIAnalyzer, DOMCompressor, Strategy, StrategyEngine

logger = logging.getLogger(__name__)


def scrape(url: str) -> Optional[Dict[str, Any]]:
    """Run the AI-guided adaptive scraping pipeline and return normalized output.

    Execution Order:
    URL → Fetch HTML → DOM Compression → AI Analysis → Strategy Engine → Adaptive Scraping → Structured Parser → Export

    Adaptive Strategy Decisions:
    - Playwright Forcing: If strategy.requires_playwright is True and initial fetch was fast HTTP requests,
      re-fetches content using Playwright to capture dynamic JavaScript elements.
    - Trafilatura Skipping: If strategy.use_trafilatura is False, skips Trafilatura body text extraction
      to prevent unwanted editorial filtering on structured catalog or table pages.
    - Parser Prioritization: Passes strategy flags to parse_html to preserve complete heading hierarchies,
      hyperlink sets, or data tables according to page requirements.

    Args:
        url: Target URL to scrape.

    Returns:
        A dictionary containing normalized scrape results, ai_analysis, and strategy, or None if fetch fails.
    """
    # Stage 1: Fetch HTML
    print("Fetching HTML...")
    html = fetcher.fetch_html(url)
    if html is None:
        print("Error: Failed to fetch HTML.")
        return None

    # Stage 2: DOM Compression
    print("Running DOM compression...")
    dom_summary: Optional[Dict[str, Any]] = None
    try:
        compressor = DOMCompressor()
        dom_summary = compressor.compress(html)
    except Exception as exc:
        print(f"Warning: DOM compression failed: {exc}")

    # Stage 3: AI Analysis
    print("Running AI analysis...")
    analysis_obj: Optional[AIAnalysis] = None
    ai_analysis_dict: Optional[Dict[str, Any]] = None
    try:
        analyzer = AIAnalyzer()
        analysis_obj = analyzer.analyze_page(html, url)
        ai_analysis_dict = analysis_obj.to_dict()
    except Exception as exc:
        print(f"Warning: AI analysis failed: {exc}")

    # Stage 4: Strategy Engine Determination
    print("Evaluating scraping strategy...")
    strategy_obj: Optional[Strategy] = None
    strategy_dict: Optional[Dict[str, Any]] = None

    if analysis_obj or ai_analysis_dict:
        try:
            engine = StrategyEngine()
            strategy_obj = engine.determine_strategy(
                analysis=analysis_obj or ai_analysis_dict,
                dom_summary=dom_summary
            )
            strategy_dict = strategy_obj.to_dict()
        except Exception as exc:
            print(f"Warning: Strategy engine evaluation failed: {exc}")

    # Stage 5: Strategy Logging
    if strategy_obj:
        website_type = (ai_analysis_dict or {}).get("website_type", "Unknown")
        mode = strategy_obj.scraping_mode
        playwright_str = str(strategy_obj.requires_playwright)
        tables_str = "High Priority" if strategy_obj.prioritize_tables else "Standard"
        trafilatura_str = "Enabled" if strategy_obj.use_trafilatura else "Disabled"

        print("\n[Strategy]")
        print(f"Website Type : {website_type}")
        print(f"Mode         : {mode}")
        print(f"Playwright   : {playwright_str}")
        print(f"Tables       : {tables_str}")
        print(f"Trafilatura  : {trafilatura_str}\n")
    else:
        print("\n[Strategy]\nNo AI Strategy available. Operating in fallback mode.\n")

    # Stage 6: Adaptive Scraping
    # Decision 6a: Force Playwright if required by strategy
    if strategy_obj and strategy_obj.requires_playwright:
        current_method = getattr(fetcher, "LAST_FETCH_METHOD", "")
        if current_method != "Playwright":
            print("[Adaptive Scraping] Strategy requires Playwright. Forcing Playwright rendering...")
            pw_html = fetcher.fetch_with_playwright(url)
            if pw_html:
                html = pw_html
                fetcher.LAST_FETCH_METHOD = "Playwright"

    # Decision 6b: Execute or skip Trafilatura extraction
    extracted: Optional[Dict[str, str]] = None
    use_trafilatura = strategy_obj.use_trafilatura if strategy_obj else True

    if use_trafilatura:
        print("[Adaptive Scraping] Running Trafilatura main content extractor...")
        try:
            extracted = extract_content(html)
        except Exception as exc:
            print(f"Warning: Content extraction failed: {exc}")
    else:
        print("[Adaptive Scraping] Trafilatura disabled by strategy. Skipping content extractor.")

    # Stage 7: Structured Parser Execution
    print("Running structured parser...")
    parsed: Dict[str, Any] = {}
    try:
        parsed = parse_html(html, strategy=strategy_dict) or {}
    except Exception as exc:
        print(f"Warning: Parser failed: {exc}")
        parsed = {}

    # Stage 8: Result Merging & Export Preparation
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

    if strategy_dict:
        result["strategy"] = strategy_dict

    print("Pipeline execution complete.")
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
    if "strategy" in result:
        print(f"Scraping Strategy: {result['strategy'].get('scraping_mode', 'N/A')}")
    elif "ai_analysis" in result:
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