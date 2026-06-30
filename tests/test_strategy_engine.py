import pytest
from backend.ai import StrategyEngine, AIAnalysis

def test_strategy_engine_static_wiki():
    """Verify strategy engine recommends fast static extraction for Wikipedia pages."""
    analysis = AIAnalysis(
        website_type="Wiki",
        framework="MediaWiki",
        content_confidence=0.9,
        table_confidence=0.1,
        requires_javascript=False,
        recommended_strategy="wiki",
        warnings=[],
        summary="Static wiki page content"
    )
    
    engine = StrategyEngine()
    strategy = engine.determine_strategy(analysis=analysis, dom_summary=None)
    
    assert strategy is not None
    assert strategy.scraping_mode == "wiki"
    assert strategy.requires_playwright is False
    assert strategy.use_trafilatura is True


def test_strategy_engine_js_heavy_ecommerce():
    """Verify strategy engine forces Playwright for javascript-heavy e-commerce pages."""
    analysis = AIAnalysis(
        website_type="E-commerce",
        framework="React",
        content_confidence=0.8,
        table_confidence=0.9,
        requires_javascript=True,
        recommended_strategy="ecommerce",
        warnings=[],
        summary="JS SPA listing"
    )
    
    engine = StrategyEngine()
    strategy = engine.determine_strategy(analysis=analysis, dom_summary=None)
    
    assert strategy is not None
    assert strategy.scraping_mode == "ecommerce"
    assert strategy.requires_playwright is True
    assert strategy.prioritize_tables is True
