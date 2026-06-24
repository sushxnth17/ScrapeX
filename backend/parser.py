"""Parse HTML content into structured JSON-like Python data."""

from __future__ import annotations

from typing import Dict, List

from bs4 import BeautifulSoup

try:
	from .fetcher import fetch_html
except ImportError:
	from fetcher import fetch_html


def _clean_text(value: str) -> str:
	"""Normalize whitespace and trim text content."""
	return " ".join(value.split()).strip()


def _dedupe_preserve_order(items: List[str]) -> List[str]:
	"""Return unique string items while preserving insertion order."""
	seen = set()
	unique_items: List[str] = []
	for item in items:
		if not item or item in seen:
			continue
		seen.add(item)
		unique_items.append(item)
	return unique_items


def parse_html(html: str) -> Dict[str, object]:
	"""Parse raw HTML into a structured dictionary.

	Args:
		html: Raw HTML string to parse.

	Returns:
		A dictionary containing:
		- title: page title text
		- headings: list of h1/h2/h3 texts
		- paragraphs: list of meaningful paragraph texts (>50 chars)
		- links: list of {"text": ..., "href": ...}
		- tables: list of tables where each table is a list of rows and each row is
		  a list of cell texts
	"""
	result: Dict[str, object] = {
		"title": "",
		"headings": [],
		"paragraphs": [],
		"links": [],
		"tables": [],
	}

	if not html or not isinstance(html, str):
		return result

	try:
		soup = BeautifulSoup(html, "lxml")
	except Exception:
		# BeautifulSoup with lxml is resilient, but return safe defaults on failure.
		return result

	title_tag = soup.find("title")
	if title_tag:
		result["title"] = _clean_text(title_tag.get_text())

	headings = [
		_clean_text(tag.get_text())
		for tag in soup.find_all(["h1", "h2", "h3"])
		if _clean_text(tag.get_text())
	]
	result["headings"] = _dedupe_preserve_order(headings)

	paragraphs = []
	for tag in soup.find_all("p"):
		text = _clean_text(tag.get_text())
		if len(text) > 50:
			paragraphs.append(text)
	result["paragraphs"] = _dedupe_preserve_order(paragraphs)

	links = []
	seen_links = set()
	for tag in soup.find_all("a", href=True):
		href = _clean_text(tag.get("href", ""))
		text = _clean_text(tag.get_text())
		if not href:
			continue

		key = (text, href)
		if key in seen_links:
			continue
		seen_links.add(key)

		links.append({"text": text, "href": href})
	result["links"] = links

	tables = []
	seen_tables = set()
	for table in soup.find_all("table"):
		# 1. Filter out layout, navigation, maintenance, or warning tables by role, classes, or ancestors
		table_classes = set(c.lower() for c in table.get("class", []) if isinstance(c, str))
		table_role = (table.get("role") or "").lower()
		table_id = (table.get("id") or "").lower()

		if table_role in ["presentation", "none", "navigation"]:
			continue

		ignored_keywords = {
			"nav", "navigation", "navbox", "sidebar", "menu", "vertical-navbox",
			"navbox-inner", "metadata", "maintenance", "mbox", "ambox", "imbox",
			"tmbox", "fmbox", "ombox", "cmbox", "warning", "error", "alert",
			"caution", "info", "toc"
		}

		is_ignored = False
		# Check table ID for ignored keywords
		for kw in ignored_keywords:
			if table_id == kw or table_id.startswith(kw + "-") or table_id.endswith("-" + kw):
				is_ignored = True
				break

		# Check table classes for ignored keywords (excluding infoboxes)
		if not is_ignored:
			for cls in table_classes:
				if "infobox" in cls:
					continue
				for kw in ignored_keywords:
					if cls == kw or cls.startswith(kw + "-") or cls.endswith("-" + kw):
						is_ignored = True
						break
				if is_ignored:
					break

		# Check if the table is nested inside any ignored tags, roles, or class structures
		if not is_ignored:
			for parent in table.parents:
				if parent.name in ["nav", "header", "footer"]:
					is_ignored = True
					break
				parent_role = (parent.get("role") or "").lower()
				if parent_role == "navigation":
					is_ignored = True
					break
				parent_classes = set(c.lower() for c in parent.get("class", []) if isinstance(c, str))
				for cls in parent_classes:
					if "infobox" in cls:
						continue
					for kw in ignored_keywords:
						if cls == kw or cls.startswith(kw + "-") or cls.endswith("-" + kw):
							is_ignored = True
							break
					if is_ignored:
						break
				if is_ignored or parent.name == "body":
					break

		if is_ignored:
			continue

		rows = []
		for tr in table.find_all("tr"):
			cells = [_clean_text(cell.get_text()) for cell in tr.find_all(["th", "td"])]
			cells = [cell for cell in cells if cell]
			if cells:
				rows.append(cells)

		# 2. Ignore tables with fewer than 2 rows
		if len(rows) < 2:
			continue

		# 3. Ignore tables where every row contains only a single cell (often lists or layout elements)
		if all(len(row) == 1 for row in rows):
			continue

		table_key = tuple(tuple(row) for row in rows)
		if table_key in seen_tables:
			continue
		seen_tables.add(table_key)
		tables.append(rows)

	result["tables"] = tables
	return result


if __name__ == "__main__":
	try:
		url = input("Enter URL to parse: ").strip()
		if not url:
			print("Error: URL cannot be empty")
		else:
			html_content = fetch_html(url)
			if not html_content:
				print("Error: Failed to fetch HTML")
			else:
				parsed = parse_html(html_content)
				print("\nParsed Summary")
				print(f"Title: {parsed['title'] or 'N/A'}")
				print(f"Headings: {len(parsed['headings'])}")
				print(f"Paragraphs: {len(parsed['paragraphs'])}")
				print(f"Links: {len(parsed['links'])}")
				print(f"Tables: {len(parsed['tables'])}")
	except KeyboardInterrupt:
		print("\nOperation cancelled by user")
