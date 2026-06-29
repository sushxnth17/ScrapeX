"""DOM Compression module for ScrapeX.

This module provides deterministic HTML compression and extraction capabilities
to reduce payload sizes sent to AI models while preserving structural, technology,
and metadata signals required for downstream web scraping and analysis.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional, Set

from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class DOMCompressor:
    """
    Extracts structural metadata, framework hints, tag statistics, and key content signals from raw HTML.
    
    Attributes:
        parser (str): The BeautifulSoup parser backend used for DOM traversal.
    """

    def __init__(self, parser: str = "lxml") -> None:
        """
        Initialize the DOMCompressor.

        Args:
            parser (str): BeautifulSoup parser backend ('lxml' or 'html.parser'). Defaults to 'lxml'.
        """
        self.parser = parser

    def compress(self, html: str) -> Dict[str, Any]:
        """
        Extract structural signals and content metadata from an HTML string into a structured dictionary.

        Args:
            html (str): Raw HTML content of the target web page.

        Returns:
            Dict[str, Any]: Structured dictionary containing extracted signals:
                - page_title (str): Content of <title> or fallback meta title tags.
                - meta_description (str): Content of description meta tag.
                - canonical_url (str): Target of canonical link tag.
                - heading_hierarchy (List[Dict[str, str]]): Ordered list of H1-H6 elements with level and text.
                - number_of_tables (int): Count of <table> elements.
                - number_of_forms (int): Count of <form> elements.
                - number_of_links (int): Count of <a> elements.
                - number_of_images (int): Count of <img> elements.
                - number_of_scripts (int): Count of <script> elements.
                - presence_of_structural_tags (Dict[str, bool]): Presence flags for article, main, nav, aside, footer.
                - framework_hints (List[str]): Alphabetically sorted list of detected frontend frameworks/technologies.
                - first_3_paragraphs (List[str]): Text of the first three non-empty <p> tags.
                - total_html_size (int): Total character length of input HTML.
                - visible_text_length (int): Character length of clean visible text extracted from DOM.
        """
        if not html:
            html = ""

        total_html_size = len(html)

        try:
            soup = BeautifulSoup(html, self.parser)
        except Exception as err:
            logger.warning(f"Failed to parse HTML with parser '{self.parser}', falling back to 'html.parser': {err}")
            soup = BeautifulSoup(html, "html.parser")

        page_title = self._extract_page_title(soup)
        meta_description = self._extract_meta_description(soup)
        canonical_url = self._extract_canonical_url(soup)
        heading_hierarchy = self._extract_heading_hierarchy(soup)
        
        counts = self._extract_counts(soup)
        structural_tags = self._extract_structural_tags(soup)
        framework_hints = self._extract_framework_hints(soup, html)
        first_3_paragraphs = self._extract_first_paragraphs(soup, limit=3)
        visible_text_length = self._calculate_visible_text_length(soup)

        return {
            "page_title": page_title,
            "meta_description": meta_description,
            "canonical_url": canonical_url,
            "heading_hierarchy": heading_hierarchy,
            "number_of_tables": counts["tables"],
            "number_of_forms": counts["forms"],
            "number_of_links": counts["links"],
            "number_of_images": counts["images"],
            "number_of_scripts": counts["scripts"],
            "presence_of_structural_tags": structural_tags,
            "framework_hints": framework_hints,
            "first_3_paragraphs": first_3_paragraphs,
            "total_html_size": total_html_size,
            "visible_text_length": visible_text_length,
        }

    def _clean_text(self, text: str) -> str:
        """
        Normalize whitespace and trim surrounding spaces.

        Args:
            text (str): Input string.

        Returns:
            str: Normalized single-spaced string.
        """
        if not text:
            return ""
        return " ".join(text.split()).strip()

    def _extract_page_title(self, soup: BeautifulSoup) -> str:
        """Extract page title from <title> tag or open-graph metadata fallback."""
        title_tag = soup.find("title")
        if title_tag and title_tag.get_text():
            cleaned = self._clean_text(title_tag.get_text())
            if cleaned:
                return cleaned

        og_title = soup.find("meta", property=re.compile(r"^og:title$", re.I))
        if og_title and og_title.get("content"):
            cleaned = self._clean_text(og_title["content"])
            if cleaned:
                return cleaned

        return ""

    def _extract_meta_description(self, soup: BeautifulSoup) -> str:
        """Extract meta description from standard or open-graph meta tags."""
        meta_desc = soup.find("meta", attrs={"name": re.compile(r"^description$", re.I)})
        if meta_desc and meta_desc.get("content"):
            cleaned = self._clean_text(meta_desc["content"])
            if cleaned:
                return cleaned

        og_desc = soup.find("meta", property=re.compile(r"^og:description$", re.I))
        if og_desc and og_desc.get("content"):
            cleaned = self._clean_text(og_desc["content"])
            if cleaned:
                return cleaned

        return ""

    def _extract_canonical_url(self, soup: BeautifulSoup) -> str:
        """Extract canonical URL from link tag or open-graph metadata."""
        canonical_link = soup.find("link", rel=lambda r: r and "canonical" in (r if isinstance(r, list) else r.split()))
        if canonical_link and canonical_link.get("href"):
            return canonical_link["href"].strip()

        og_url = soup.find("meta", property=re.compile(r"^og:url$", re.I))
        if og_url and og_url.get("content"):
            return og_url["content"].strip()

        return ""


    def _extract_heading_hierarchy(self, soup: BeautifulSoup) -> List[Dict[str, str]]:
        """Extract ordered sequence of headings H1 through H6."""
        headings: List[Dict[str, str]] = []
        for tag in soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6"]):
            cleaned = self._clean_text(tag.get_text())
            if cleaned:
                headings.append({
                    "level": tag.name.lower(),
                    "text": cleaned
                })
        return headings

    def _extract_counts(self, soup: BeautifulSoup) -> Dict[str, int]:
        """Calculate counts of major structural elements."""
        return {
            "tables": len(soup.find_all("table")),
            "forms": len(soup.find_all("form")),
            "links": len(soup.find_all("a")),
            "images": len(soup.find_all("img")),
            "scripts": len(soup.find_all("script")),
        }

    def _extract_structural_tags(self, soup: BeautifulSoup) -> Dict[str, bool]:
        """Determine presence of semantic HTML5 structural components."""
        target_tags = ["article", "main", "nav", "aside", "footer"]
        return {tag: bool(soup.find(tag)) for tag in target_tags}

    def _extract_first_paragraphs(self, soup: BeautifulSoup, limit: int = 3) -> List[str]:
        """Extract text of the first N non-empty paragraph (<p>) elements."""
        paragraphs: List[str] = []
        for p in soup.find_all("p"):
            cleaned = self._clean_text(p.get_text())
            if cleaned:
                paragraphs.append(cleaned)
                if len(paragraphs) == limit:
                    break
        return paragraphs

    def _extract_framework_hints(self, soup: BeautifulSoup, raw_html: str) -> List[str]:
        """
        Detect web technology and frontend framework indicators deterministically.

        Returns:
            List[str]: Alphabetically sorted list of detected technologies.
        """
        hints: Set[str] = set()

        # Check meta generator tags
        generator_meta = soup.find("meta", attrs={"name": re.compile(r"^generator$", re.I)})
        if generator_meta and generator_meta.get("content"):
            gen_content = generator_meta["content"].lower()
            if "wordpress" in gen_content:
                hints.add("WordPress")
            if "gatsby" in gen_content:
                hints.add("Gatsby")
            if "next.js" in gen_content or "nextjs" in gen_content:
                hints.add("Next.js")
            if "nuxt" in gen_content:
                hints.add("Nuxt.js")
            if "shopify" in gen_content:
                hints.add("Shopify")
            if "drupal" in gen_content:
                hints.add("Drupal")
            if "joomla" in gen_content:
                hints.add("Joomla")

        # DOM Attributes & IDs
        if soup.find(id="__NEXT_DATA__") or soup.find(attrs={"data-reactroot": True}) or soup.find(attrs={"data-reactid": True}):
            hints.add("Next.js" if soup.find(id="__NEXT_DATA__") else "React")
        
        if soup.find(id="__NUXT__"):
            hints.add("Nuxt.js")
            hints.add("Vue.js")

        if soup.find(id="___gatsby"):
            hints.add("Gatsby")
            hints.add("React")

        # Vue indicators
        for tag in soup.find_all(True):
            if isinstance(tag.attrs, dict):
                if any(attr.startswith("data-v-") or attr in ["v-bind", "v-model", "v-if", "v-for"] for attr in tag.attrs.keys()):
                    hints.add("Vue.js")
                    break

        # Angular indicators
        def _is_angular_attrs(attrs: Any) -> bool:
            if isinstance(attrs, dict):
                return any(k.startswith("ng-") or k.startswith("data-ng-") for k in attrs.keys())
            return False

        if soup.find(attrs=_is_angular_attrs):
            hints.add("Angular")


        # Script sources & Stylesheet links
        for script in soup.find_all("script", src=True):
            src = script["src"].lower()
            if "_next/" in src:
                hints.add("Next.js")
                hints.add("React")
            elif "react" in src:
                hints.add("React")
            if "_nuxt/" in src:
                hints.add("Nuxt.js")
                hints.add("Vue.js")
            elif "vue" in src:
                hints.add("Vue.js")
            if "angular" in src:
                hints.add("Angular")
            if "jquery" in src:
                hints.add("jQuery")
            if "bootstrap" in src:
                hints.add("Bootstrap")
            if "wp-content" in src or "wp-includes" in src:
                hints.add("WordPress")
            if "shopify" in src or "cdn.shopify.com" in src:
                hints.add("Shopify")

        for link in soup.find_all("link", href=True):
            href = link["href"].lower()
            if "bootstrap" in href:
                hints.add("Bootstrap")
            if "tailwind" in href:
                hints.add("Tailwind CSS")
            if "wp-content" in href or "wp-includes" in href:
                hints.add("WordPress")

        # Raw HTML strings checks for inline indicators
        if "tailwindcss" in raw_html.lower() or 'class="tw-' in raw_html.lower():
            hints.add("Tailwind CSS")
        if "Shopify.theme" in raw_html:
            hints.add("Shopify")

        return sorted(list(hints))

    def _calculate_visible_text_length(self, soup: BeautifulSoup) -> int:
        """
        Calculate character length of clean visible text by ignoring script, style, and metadata tags.
        """
        # Create a shallow copy or work with filtered tag texts without mutating original soup if possible
        # BeautifulSoup decompose mutates the tree, so we build a fresh temporary parser instance
        temp_soup = BeautifulSoup(str(soup), self.parser)
        
        ignored_tags = ["script", "style", "noscript", "header", "footer", "nav", "svg", "style", "template", "iframe"]
        for element in temp_soup(ignored_tags):
            element.decompose()

        clean_text = self._clean_text(temp_soup.get_text())
        return len(clean_text)
