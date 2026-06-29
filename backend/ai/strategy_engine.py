"""AI Strategy Engine module for ScrapeX.

This module provides a decision layer between AI web analysis and the scraping pipeline.
It maps website classifications and structural signals into optimized scraping strategies
without performing any scraping operations directly.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Union

try:
    from backend.ai.analyzer import AIAnalysis
except ImportError:
    from .analyzer import AIAnalysis

logger = logging.getLogger(__name__)


@dataclass
class Strategy:
    """
    Structured representation of an execution strategy for scraping a web page.

    Attributes:
        scraping_mode (str): High-level category classification determining extraction approach.
                             Options: 'article', 'product_catalog', 'documentation', 'forum', 'wiki',
                             'blog', 'news', 'ecommerce', 'table_heavy', 'generic'.
        extraction_priority (List[str]): Ordered list of DOM targets to prioritize during extraction.
        use_trafilatura (bool): Flag indicating whether Trafilatura text extraction should be enabled.
        use_parser (bool): Flag indicating whether BeautifulSoup structured DOM parsing should be enabled.
        prioritize_tables (bool): Flag indicating special handling/extraction for tabular data.
        prioritize_links (bool): Flag indicating special extraction for structural/navigation links.
        prioritize_headings (bool): Flag indicating structural heading hierarchy extraction.
        requires_playwright (bool): Flag indicating dynamic headless browser rendering is required.
    """
    scraping_mode: str
    extraction_priority: List[str]
    use_trafilatura: bool
    use_parser: bool
    prioritize_tables: bool
    prioritize_links: bool
    prioritize_headings: bool
    requires_playwright: bool

    def to_dict(self) -> Dict[str, Any]:
        """Convert the strategy instance into a JSON-serializable dictionary."""
        return {
            "scraping_mode": self.scraping_mode,
            "extraction_priority": self.extraction_priority,
            "use_trafilatura": self.use_trafilatura,
            "use_parser": self.use_parser,
            "prioritize_tables": self.prioritize_tables,
            "prioritize_links": self.prioritize_links,
            "prioritize_headings": self.prioritize_headings,
            "requires_playwright": self.requires_playwright,
        }


class StrategyEngine:
    """
    Decision engine that determines scraping strategies based on AI analytical insights and DOM metadata.

    This class evaluates site types, confidence scores, and framework indicators to generate modular
    execution plans for downstream extraction components without executing scraping tasks directly.
    """

    # Modular strategy definition registry for supported scraping modes
    STRATEGY_DEFINITIONS: Dict[str, Dict[str, Any]] = {
        "article": {
            "description": "Optimized for single-topic narrative articles, research papers, and long-form editorial content.",
            "extraction_priority": ["main_text", "headings", "metadata"],
            "use_trafilatura": True,
            "use_parser": True,
            "prioritize_tables": False,
            "prioritize_links": False,
            "prioritize_headings": True,
        },
        "product_catalog": {
            "description": "Designed for product listing pages, category indexes, and multi-card search results grids.",
            "extraction_priority": ["links", "product_cards", "images", "prices"],
            "use_trafilatura": False,
            "use_parser": True,
            "prioritize_tables": False,
            "prioritize_links": True,
            "prioritize_headings": False,
        },
        "documentation": {
            "description": "Tailored for technical documentation, API references, and manuals with code snippets and hierarchy.",
            "extraction_priority": ["headings", "code_blocks", "sidebar_links", "main_text"],
            "use_trafilatura": True,
            "use_parser": True,
            "prioritize_tables": False,
            "prioritize_links": True,
            "prioritize_headings": True,
        },
        "forum": {
            "description": "Optimized for community message boards, QA threads, and threaded social discussion posts.",
            "extraction_priority": ["posts", "replies", "user_metadata", "links"],
            "use_trafilatura": False,
            "use_parser": True,
            "prioritize_tables": False,
            "prioritize_links": True,
            "prioritize_headings": False,
        },
        "wiki": {
            "description": "Designed for open knowledge bases featuring dense cross-links, infobox tables, and structural sections.",
            "extraction_priority": ["tables", "headings", "links", "main_text"],
            "use_trafilatura": True,
            "use_parser": True,
            "prioritize_tables": True,
            "prioritize_links": True,
            "prioritize_headings": True,
        },
        "blog": {
            "description": "Tailored for blog posts combining author metadata, editorial content, and recommended posts.",
            "extraction_priority": ["main_text", "headings", "author_meta", "links"],
            "use_trafilatura": True,
            "use_parser": True,
            "prioritize_tables": False,
            "prioritize_links": False,
            "prioritize_headings": True,
        },
        "news": {
            "description": "Optimized for time-sensitive press releases, news reports, and journal publications emphasizing dates and headlines.",
            "extraction_priority": ["headline", "main_text", "timestamp", "links"],
            "use_trafilatura": True,
            "use_parser": True,
            "prioritize_tables": False,
            "prioritize_links": False,
            "prioritize_headings": True,
        },
        "ecommerce": {
            "description": "Designed for individual product detail pages focusing on pricing, stock availability, and specs.",
            "extraction_priority": ["price_and_specs", "tables", "images", "description"],
            "use_trafilatura": False,
            "use_parser": True,
            "prioritize_tables": True,
            "prioritize_links": False,
            "prioritize_headings": False,
        },
        "table_heavy": {
            "description": "Specially tuned for data-dense pages dominated by HTML tables such as financial reports or sports statistics.",
            "extraction_priority": ["tables", "structured_data", "headers"],
            "use_trafilatura": False,
            "use_parser": True,
            "prioritize_tables": True,
            "prioritize_links": False,
            "prioritize_headings": False,
        },
        "generic": {
            "description": "Fallback strategy for general websites or unidentified page layouts requiring balanced extraction.",
            "extraction_priority": ["main_text", "tables", "links", "headings"],
            "use_trafilatura": True,
            "use_parser": True,
            "prioritize_tables": False,
            "prioritize_links": False,
            "prioritize_headings": False,
        },
    }

    def __init__(self) -> None:
        """Initialize the StrategyEngine."""
        self._custom_rules: List[Callable[[Dict[str, Any], Optional[Dict[str, Any]]], Optional[str]]] = []

    def register_rule(self, rule_fn: Callable[[Dict[str, Any], Optional[Dict[str, Any]]], Optional[str]]) -> None:
        """
        Register a custom rule function for modular strategy evaluation.

        Args:
            rule_fn: A callable receiving analysis dict and dom summary dict, returning a strategy mode string or None.
        """
        self._custom_rules.append(rule_fn)

    def determine_strategy(
        self,
        analysis: Union[AIAnalysis, Dict[str, Any]],
        dom_summary: Optional[Dict[str, Any]] = None
    ) -> Strategy:
        """
        Evaluate AI analysis findings and DOM compression signals to produce a structured Scraping Strategy.

        Args:
            analysis (Union[AIAnalysis, Dict[str, Any]]): Analytical results from AIAnalyzer.
            dom_summary (Optional[Dict[str, Any]]): Compressed DOM metadata from DOMCompressor.

        Returns:
            Strategy: Object containing configuration flags and extraction priorities.
        """
        analysis_dict = analysis.to_dict() if isinstance(analysis, AIAnalysis) else dict(analysis)
        dom_dict = dom_summary or {}

        # 1. Determine Playwright requirement
        requires_playwright = self._evaluate_playwright_requirement(analysis_dict, dom_dict)

        # 2. Determine scraping mode
        scraping_mode = self._determine_scraping_mode(analysis_dict, dom_dict)

        # 3. Fetch base strategy configuration from registry
        base_config = self.STRATEGY_DEFINITIONS.get(scraping_mode, self.STRATEGY_DEFINITIONS["generic"])

        return Strategy(
            scraping_mode=scraping_mode,
            extraction_priority=list(base_config["extraction_priority"]),
            use_trafilatura=base_config["use_trafilatura"],
            use_parser=base_config["use_parser"],
            prioritize_tables=base_config["prioritize_tables"],
            prioritize_links=base_config["prioritize_links"],
            prioritize_headings=base_config["prioritize_headings"],
            requires_playwright=requires_playwright,
        )

    def _evaluate_playwright_requirement(self, analysis: Dict[str, Any], dom_summary: Dict[str, Any]) -> bool:
        """Evaluate whether headless browser rendering via Playwright is required."""
        if analysis.get("requires_javascript", False):
            return True

        framework = str(analysis.get("framework", "")).lower()
        if framework in ["react", "next.js", "vue.js", "nuxt.js", "angular", "svelte"]:
            return True

        framework_hints = [f.lower() for f in dom_summary.get("framework_hints", [])]
        if any(f in framework_hints for f in ["react", "next.js", "vue.js", "nuxt.js", "angular", "svelte"]):
            return True

        return False

    def _determine_scraping_mode(self, analysis: Dict[str, Any], dom_summary: Dict[str, Any]) -> str:
        """Map analytical indicators and structural DOM signals to one of the 10 supported strategy modes."""
        # Check custom registered rules first
        for rule in self._custom_rules:
            try:
                custom_mode = rule(analysis, dom_summary)
                if custom_mode and custom_mode in self.STRATEGY_DEFINITIONS:
                    return custom_mode
            except Exception as err:
                logger.warning(f"Error executing custom strategy rule: {err}")

        website_type = str(analysis.get("website_type", "")).lower().strip()
        recommended_strat = str(analysis.get("recommended_strategy", "")).lower().strip()
        
        # Check table heaviness signals
        table_confidence = float(analysis.get("table_confidence", 0.0))
        num_tables = dom_summary.get("number_of_tables", 0)
        if (num_tables >= 3 or table_confidence >= 0.8) and website_type not in ["e-commerce", "ecommerce", "store", "shop"]:
            if "table" in recommended_strat or num_tables >= 4:
                return "table_heavy"

        # Direct mapping checks against website_type and recommended_strategy
        combined_text = f"{website_type} {recommended_strat}"

        if any(kw in combined_text for kw in ["product catalog", "catalog", "product list"]):
            return "product_catalog"
        if any(kw in combined_text for kw in ["e-commerce", "ecommerce", "store", "shop"]):
            return "ecommerce"
        if any(kw in combined_text for kw in ["wiki", "wikipedia", "knowledgebase", "knowledge base"]):
            return "wiki"
        if any(kw in combined_text for kw in ["forum", "discussion", "qa", "q&a", "community"]):
            return "forum"
        if any(kw in combined_text for kw in ["documentation", "docs", "api reference"]):
            return "documentation"
        if any(kw in combined_text for kw in ["news", "press", "journal"]):
            return "news"
        if any(kw in combined_text for kw in ["blog"]):
            return "blog"
        if any(kw in combined_text for kw in ["article", "editorial", "paper"]):
            return "article"
        if any(kw in combined_text for kw in ["table", "financial"]):
            return "table_heavy"

        return "generic"
