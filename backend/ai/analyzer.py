"""AI Page Analyzer module for architectural analysis of web pages in ScrapeX."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union


@dataclass
class AIAnalysis:
    """
    Structured container holding analytical insights derived from web page content.
    
    Attributes:
        website_type (str): Categorization of the website (e.g., 'E-commerce', 'Blog', 'Documentation', 'News').
        framework (str): Detected web technology stack or framework (e.g., 'React', 'Next.js', 'WordPress', 'Unknown').
        main_content_selector (str): Recommended CSS selector for extracting main body content.
        table_confidence (float): Confidence score (0.0 to 1.0) regarding table data extraction accuracy.
        content_confidence (float): Confidence score (0.0 to 1.0) regarding textual content extraction accuracy.
        requires_javascript (bool): Flag indicating if dynamic JavaScript rendering (e.g., Playwright) is necessary.
        scrape_strategy (str): Recommended strategy for optimal scraping performance and quality.
        warnings (List[str]): Potential challenges or anti-scraping measures identified on the page.
        summary (str): Brief overview summary of the page architecture and structural layout.
    """
    website_type: str
    framework: str
    main_content_selector: str
    table_confidence: float
    content_confidence: float
    requires_javascript: bool
    scrape_strategy: str
    warnings: List[str] = field(default_factory=list)
    summary: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert the dataclass instance into a JSON-serializable dictionary."""
        return {
            "website_type": self.website_type,
            "framework": self.framework,
            "main_content_selector": self.main_content_selector,
            "table_confidence": self.table_confidence,
            "content_confidence": self.content_confidence,
            "requires_javascript": self.requires_javascript,
            "scrape_strategy": self.scrape_strategy,
            "warnings": self.warnings,
            "summary": self.summary,
        }


class AIAnalyzer:
    """
    Analyzes web page structure, technology stack, and content layout using AI LLM models.
    
    This class serves as the interface between raw HTML scraping results and intelligence-driven
    extraction planning, enabling optimized selector detection and rendering choices.
    """

    def __init__(self, api_key: Optional[str] = None) -> None:
        """
        Initialize the AIAnalyzer instance.
        
        Args:
            api_key (Optional[str]): API key for the LLM provider. If None, it will be lazily loaded 
                                     from backend.config when performing API calls.
        """
        self.api_key = api_key

    def build_prompt(self, html: str, url: str) -> str:
        """
        Construct a structured prompt for the LLM analyzing page architecture.
        
        Args:
            html (str): The raw or sanitized HTML content of the target web page.
            url (str): The destination URL of the web page.
            
        Returns:
            str: Formatted prompt containing structural instructions and schema expectations.
        """
        # Truncate HTML body if necessary to prevent context window bloat during initial analysis
        truncated_html = html[:8000] if len(html) > 8000 else html

        prompt = f"""
You are an expert web scraper and web architecture analyzer for ScrapeX.
Analyze the following web page content and metadata, then provide architectural insights in strict JSON format.

Target URL: {url}

HTML Snippet:
```html
{truncated_html}
```

Please respond strictly with a valid JSON object matching this schema:
{{
    "website_type": "<Type of website, e.g., News, E-commerce, Documentation, Blog>",
    "framework": "<Detected frontend technology/framework, e.g., React, Next.js, WordPress, Static>",
    "main_content_selector": "<Optimal CSS selector targeting primary content>",
    "table_confidence": <Float between 0.0 and 1.0 indicating confidence in structured tabular data presence>,
    "content_confidence": <Float between 0.0 and 1.0 indicating confidence in main text extraction>,
    "requires_javascript": <Boolean true/false if Client-Side Rendering/JS execution is essential>,
    "scrape_strategy": "<Brief recommended scraping approach>",
    "warnings": ["<List of potential scraping challenges or obstacles if any>"],
    "summary": "<Short overview of page structure>"
}}
"""
        return prompt.strip()

    def parse_response(self, response: Union[str, Dict[str, Any]]) -> AIAnalysis:
        """
        Parse raw LLM response (JSON string or pre-parsed dictionary) into an AIAnalysis dataclass.
        
        Args:
            response (Union[str, Dict[str, Any]]): The raw text or dictionary response returned by the AI provider.
            
        Returns:
            AIAnalysis: A validated and structured analysis object.
            
        Raises:
            ValueError: If the response cannot be parsed or lacks required fields.
        """
        if isinstance(response, str):
            clean_response = response.strip()
            # Handle potential markdown code block wrappers from LLM output
            if clean_response.startswith("```json"):
                clean_response = clean_response[7:]
            if clean_response.startswith("```"):
                clean_response = clean_response[3:]
            if clean_response.endswith("```"):
                clean_response = clean_response[:-3]
            clean_response = clean_response.strip()

            try:
                data = json.loads(clean_response)
            except json.JSONDecodeError as err:
                raise ValueError(f"Failed to parse AI response as valid JSON: {err}") from err
        elif isinstance(response, dict):
            data = response
        else:
            raise ValueError(f"Unsupported response type for parsing: {type(response)}")

        return AIAnalysis(
            website_type=str(data.get("website_type", "Unknown")),
            framework=str(data.get("framework", "Unknown")),
            main_content_selector=str(data.get("main_content_selector", "body")),
            table_confidence=float(data.get("table_confidence", 0.0)),
            content_confidence=float(data.get("content_confidence", 0.0)),
            requires_javascript=bool(data.get("requires_javascript", False)),
            scrape_strategy=str(data.get("scrape_strategy", "Standard HTML parsing")),
            warnings=list(data.get("warnings", [])),
            summary=str(data.get("summary", "")),
        )

    def analyze_page(self, html: str, url: str) -> AIAnalysis:
        """
        Execute full architectural analysis on a target web page.
        
        Note:
            This method is currently built as a structural architecture foundation.
            Groq API calling will be integrated in subsequent phases.
        
        Args:
            html (str): Raw or processed HTML content of the web page.
            url (str): Target page URL.
            
        Returns:
            AIAnalysis: Structured analysis results for the web page.
        """
        prompt = self.build_prompt(html, url)
        
        # Placeholder / mock architectural response until Groq client integration
        mock_response = {
            "website_type": "Static / Generic",
            "framework": "Standard HTML/CSS",
            "main_content_selector": "article, main, body",
            "table_confidence": 0.8,
            "content_confidence": 0.9,
            "requires_javascript": False,
            "scrape_strategy": "Direct HTTP request and DOM selector parsing",
            "warnings": [],
            "summary": f"Architectural analysis preview for {url}. Ready for Groq integration.",
        }
        
        return self.parse_response(mock_response)
