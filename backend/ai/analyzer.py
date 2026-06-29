"""AI Page Analyzer module for architectural analysis of web pages in ScrapeX using Groq API."""

from __future__ import annotations

import json
import logging
import re
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
        content_confidence (float): Confidence score (0.0 to 1.0) regarding textual content extraction accuracy.
        table_confidence (float): Confidence score (0.0 to 1.0) regarding table data extraction accuracy.
        requires_javascript (bool): Flag indicating if dynamic JavaScript rendering (e.g., Playwright) is necessary.
        recommended_strategy (str): Recommended strategy for optimal scraping performance and quality.
        warnings (List[str]): Potential challenges or anti-scraping measures identified on the page.
        summary (str): Brief overview summary of the page architecture and structural layout.
        main_content_selector (str): Optional/legacy CSS selector for extracting main body content.
        overall_score (int): Overall compatibility rating (0 to 100).
        compatibility_grade (str): Letter grade representing scraping ease ('A', 'B', 'C', 'D').
        rendering_type (str): Web page rendering paradigm (e.g., 'Mostly Static', 'Server-Side Rendered', 'Single Page Application').
        javascript_complexity (str): Level of client-side scripting interaction required ('Low', 'Medium', 'High', 'Critical').
        strengths (List[str]): Key architectural advantages for content extraction.
        limitations (List[str]): Potential scraping hurdles or anti-extraction constraints.
        recommendation (str): Actionable intelligence recommendation for extraction pipelines.
    """
    website_type: str
    framework: str
    content_confidence: float
    table_confidence: float
    requires_javascript: bool
    recommended_strategy: str
    warnings: List[str] = field(default_factory=list)
    summary: str = ""
    main_content_selector: str = "body"
    overall_score: int = 85
    compatibility_grade: str = "A"
    rendering_type: str = "Mostly Static"
    javascript_complexity: str = "Low"
    strengths: List[str] = field(default_factory=list)
    limitations: List[str] = field(default_factory=list)
    recommendation: str = "Optimal for automated extraction."

    @property
    def scrape_strategy(self) -> str:
        """Backward-compatible alias for recommended_strategy."""
        return self.recommended_strategy

    def to_dict(self) -> Dict[str, Any]:
        """Convert the dataclass instance into a JSON-serializable dictionary."""
        return {
            "website_type": self.website_type,
            "framework": self.framework,
            "content_confidence": self.content_confidence,
            "table_confidence": self.table_confidence,
            "requires_javascript": self.requires_javascript,
            "recommended_strategy": self.recommended_strategy,
            "warnings": self.warnings,
            "summary": self.summary,
            "main_content_selector": self.main_content_selector,
            "overall_score": self.overall_score,
            "compatibility_grade": self.compatibility_grade,
            "rendering_type": self.rendering_type,
            "javascript_complexity": self.javascript_complexity,
            "strengths": self.strengths,
            "limitations": self.limitations,
            "recommendation": self.recommendation,
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

    def build_prompt(self, html: str, url: str, title: str = "") -> str:
        """
        Construct a structured prompt for Groq to analyze web page architecture while minimizing hallucinations.
        
        Args:
            html (str): The raw or sanitized HTML content of the target web page.
            url (str): The destination URL of the web page.
            title (str): The HTML page title. If empty, extracted from HTML snippet.
            
        Returns:
            str: Formatted prompt instructing the LLM to output strict JSON according to schema.
        """
        if not title and html:
            match = re.search(r"<title[^>]*>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
            if match:
                title = match.group(1).strip()

        truncated_html = html[:8000] if len(html) > 8000 else html

        prompt = f"""Target URL: {url}
Page Title: {title if title else 'N/A'}

HTML Snapshot:
{truncated_html}

Instructions:
1. Analyze the provided page content and metadata objectively. Do NOT speculate or extrapolate facts not supported by the HTML or URL.
2. If the frontend framework or technology cannot be confirmed via meta tags, script source tags, or DOM indicators, set "framework" to "Unknown".
3. "content_confidence" and "table_confidence" must be numeric floating-point values between 0.0 and 1.0.
4. "requires_javascript" must be a boolean (true or false).
5. "overall_score" must be an integer between 0 and 100. "compatibility_grade" must be one of "A", "B", "C", "D".
6. Identify key architectural strengths, limitations, rendering_type, javascript_complexity, and recommendation for scraping pipelines.
7. Output strictly raw JSON matching the exact schema below. Do NOT use markdown code blocks (e.g., do not use ```json ... ```), and do NOT provide explanations or conversating text before or after the JSON object.

Required Schema:
{{
  "website_type": "",
  "framework": "",
  "content_confidence": 0.0,
  "table_confidence": 0.0,
  "requires_javascript": false,
  "recommended_strategy": "",
  "warnings": [],
  "summary": "",
  "overall_score": 90,
  "compatibility_grade": "A",
  "rendering_type": "Mostly Static",
  "javascript_complexity": "Low",
  "strengths": [],
  "limitations": [],
  "recommendation": ""
}}"""
        return prompt.strip()

    def send_prompt(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """
        Send a prompt to the Groq API and return the raw JSON string response.
        
        Implements timeout, retry logic (retries once on failure), strict JSON output format,
        and graceful error handling.
        """
        api_key = self.api_key or get_groq_api_key()

        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        if system_prompt is None:
            system_prompt = (
                "You are an objective web architecture analyzer for ScrapeX. "
                "Your task is to analyze web page metadata and HTML to assess scraping strategy. "
                "You must strictly output valid JSON matching the exact schema requested without any markdown formatting, preambles, or explanations."
            )

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
                    time.sleep(1.0)

        raise AIAnalysisError(f"Groq API communication failed after retry: {last_exception}") from last_exception

    def parse_response(self, response: Union[str, Dict[str, Any]]) -> AIAnalysis:
        """
        Parse raw LLM response (JSON string or pre-parsed dictionary) into an AIAnalysis dataclass.
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

        rec_strat = str(data.get("recommended_strategy") or data.get("scrape_strategy") or "Standard HTML parsing")
        warnings_list = list(data.get("warnings", []))

        framework_str = str(data.get("framework", "Unknown"))
        if framework_str != "Unknown" and framework_str != "Standard HTML/CSS":
            if not any(framework_str.lower() in w.lower() or "appears to use" in w.lower() for w in warnings_list):
                warnings_list.append(f"This site appears to use {framework_str}.")

        content_conf = float(data.get("content_confidence", 0.0))
        if content_conf < 0.4 and not any("content extraction" in w.lower() or "confidence" in w.lower() for w in warnings_list):
            warnings_list.append("Content extraction confidence is low.")

        table_conf = float(data.get("table_confidence", 0.0))
        if table_conf < 0.2 and not any("table" in w.lower() for w in warnings_list):
            warnings_list.append("No semantic HTML tables detected.")

        # Validation and safe fallbacks for compatibility report metrics
        try:
            overall_score = int(data.get("overall_score", 0))
        except (ValueError, TypeError):
            overall_score = 0

        if overall_score <= 0:
            base = int((content_conf * 60) + (table_conf * 20))
            overall_score = base + 20 if not bool(data.get("requires_javascript")) else base + 10
            overall_score = max(35, min(98, overall_score))

        comp_grade = str(data.get("compatibility_grade", "")).upper().strip()
        if comp_grade not in ["A", "B", "C", "D"]:
            if overall_score >= 85:
                comp_grade = "A"
            elif overall_score >= 70:
                comp_grade = "B"
            elif overall_score >= 50:
                comp_grade = "C"
            else:
                comp_grade = "D"

        rendering_type = str(data.get("rendering_type") or ("Dynamic SPA" if data.get("requires_javascript") else "Mostly Static"))
        js_complexity = str(data.get("javascript_complexity") or ("High" if data.get("requires_javascript") else "Low"))

        strengths_list = [str(s) for s in data.get("strengths", []) if s]
        if not strengths_list:
            if content_conf > 0.7:
                strengths_list.append("Clean semantic HTML structure with high text readability.")
            if not data.get("requires_javascript"):
                strengths_list.append("Static page rendering accessible via high-speed HTTP requests.")
            if table_conf > 0.5:
                strengths_list.append("Structured data tables detected for extraction.")
            if not strengths_list:
                strengths_list.append("Standard web page structure.")

        limitations_list = [str(l) for l in data.get("limitations", []) if l]
        if not limitations_list:
            if data.get("requires_javascript"):
                limitations_list.append("Requires headless browser execution for client-side JS rendering.")
            if content_conf < 0.5:
                limitations_list.append("Mixed text and navigation layout may reduce extraction precision.")
            if not limitations_list:
                limitations_list.append("No critical scraping limitations identified.")

        recommendation_str = str(data.get("recommendation") or f"Execute '{rec_strat}' extraction for optimal performance.")

        return AIAnalysis(
            website_type=str(data.get("website_type", "Unknown")),
            framework=framework_str,
            content_confidence=content_conf,
            table_confidence=table_conf,
            requires_javascript=bool(data.get("requires_javascript", False)),
            recommended_strategy=rec_strat,
            warnings=warnings_list,
            summary=str(data.get("summary", "")),
            main_content_selector=str(data.get("main_content_selector", "body")),
            overall_score=overall_score,
            compatibility_grade=comp_grade,
            rendering_type=rendering_type,
            javascript_complexity=js_complexity,
            strengths=strengths_list,
            limitations=limitations_list,
            recommendation=recommendation_str,
        )

    def analyze_page(self, html: str, url: str, title: str = "") -> AIAnalysis:
        """
        Execute full architectural analysis on a target web page using Groq AI.
        """
        prompt = self.build_prompt(html, url, title)
        
        try:
            response_text = self.send_prompt(prompt)
            return self.parse_response(response_text)
        except (AIAnalysisError, ConfigurationError, ValueError) as err:
            logging.error(f"AI analysis failed for {url}: {err}")
            return AIAnalysis(
                website_type="Unknown",
                framework="Unknown",
                content_confidence=0.0,
                table_confidence=0.0,
                requires_javascript=False,
                recommended_strategy="Standard HTML extraction (Fallback)",
                warnings=[f"AI Analysis notice: {str(err)}"],
                summary=f"Fallback analysis generated due to AI processing failure: {err}",
                main_content_selector="body",
                overall_score=50,
                compatibility_grade="C",
                rendering_type="Unknown / Fallback",
                javascript_complexity="Medium",
                strengths=["Basic HTML fallback parser available."],
                limitations=["AI architectural analysis was unavailable."],
                recommendation="Proceed with standard HTML extraction."
            )
