"""AI Page Analyzer module for architectural analysis of web pages in ScrapeX using Groq API."""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union

import requests

try:
    from backend.config import ConfigurationError, get_groq_api_key
except ImportError:
    from config import ConfigurationError, get_groq_api_key


class AIAnalysisError(Exception):
    """Custom exception raised for errors during AI analysis or external API communication."""
    pass


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
    Analyzes web page structure, technology stack, and content layout using Groq LLM API.
    
    This class serves as the interface between raw HTML scraping results and intelligence-driven
    extraction planning, enabling optimized selector detection and rendering choices.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "llama-3.3-70b-versatile",
        timeout: int = 15
    ) -> None:
        """
        Initialize the AIAnalyzer instance.
        
        Args:
            api_key (Optional[str]): API key for the Groq provider. If None, loaded dynamically from config.
            model (str): Groq LLM model identifier. Defaults to 'llama-3.3-70b-versatile'.
            timeout (int): HTTP request timeout in seconds. Defaults to 15 seconds.
        """
        self.api_key = api_key
        self.model = model
        self.timeout = timeout

    def build_prompt(self, html: str, url: str) -> str:
        """
        Construct a structured prompt for the LLM analyzing page architecture.
        
        Args:
            html (str): The raw or sanitized HTML content of the target web page.
            url (str): The destination URL of the web page.
            
        Returns:
            str: Formatted prompt containing structural instructions and schema expectations.
        """
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

    def send_prompt(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """
        Send a prompt to the Groq API and return the raw JSON string response.
        
        Implements timeout, retry logic (retries once on failure), strict JSON output format,
        and graceful error handling.
        
        Args:
            prompt (str): The user prompt or analysis content to send.
            system_prompt (Optional[str]): System instructions for the model.
            
        Returns:
            str: Raw JSON string response from the LLM.
            
        Raises:
            AIAnalysisError: If the API call fails after retries or returns invalid data.
            ConfigurationError: If the Groq API key is missing.
        """
        api_key = self.api_key or get_groq_api_key()

        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        if system_prompt is None:
            system_prompt = "You are a web architecture analyzer for ScrapeX. You must output valid JSON only."

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.1
        }

        last_exception: Optional[Exception] = None

        # Retry once on failure (up to 2 total attempts)
        for attempt in range(2):
            try:
                response = requests.post(url, headers=headers, json=payload, timeout=self.timeout)
                if response.status_code != 200:
                    raise AIAnalysisError(
                        f"Groq API error (status code {response.status_code}): {response.text}"
                    )
                
                response_data = response.json()
                choices = response_data.get("choices", [])
                if not choices:
                    raise AIAnalysisError("Groq API returned an empty completion choice list.")
                
                content = choices[0].get("message", {}).get("content", "")
                if not content:
                    raise AIAnalysisError("Groq API returned empty message content.")
                
                return content

            except (requests.RequestException, AIAnalysisError, json.JSONDecodeError) as err:
                last_exception = err
                logging.warning(
                    f"Groq API request attempt {attempt + 1} failed: {err}. "
                    f"{'Retrying once...' if attempt == 0 else 'No more retries.'}"
                )
                if attempt == 0:
                    time.sleep(1.0)  # Short backoff before retry

        raise AIAnalysisError(f"Groq API communication failed after retry: {last_exception}") from last_exception

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
        Execute full architectural analysis on a target web page using Groq AI.
        
        Args:
            html (str): Raw or processed HTML content of the web page.
            url (str): Target page URL.
            
        Returns:
            AIAnalysis: Structured analysis results for the web page.
        """
        prompt = self.build_prompt(html, url)
        
        try:
            response_text = self.send_prompt(prompt)
            return self.parse_response(response_text)
        except (AIAnalysisError, ConfigurationError, ValueError) as err:
            logging.error(f"AI analysis failed for {url}: {err}")
            return AIAnalysis(
                website_type="Unknown",
                framework="Unknown",
                main_content_selector="body",
                table_confidence=0.0,
                content_confidence=0.0,
                requires_javascript=False,
                scrape_strategy="Standard HTML extraction (Fallback)",
                warnings=[f"AI Analysis error: {str(err)}"],
                summary=f"Fallback analysis generated due to AI processing failure: {err}"
            )
