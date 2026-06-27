"""Parse HTML content into structured JSON-like Python data."""

from __future__ import annotations

import re
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


def is_data_table(table) -> bool:
	"""Determine if a <table> tag represents actual structured data rather than layout/navigation.

	Heuristics:
	1. Whitelist common data table class names (infobox, wikitable, ws-table-all, data-table, etc.).
	2. Reject layout roles: presentation, none, navigation.
	3. Reject if fewer than 2 rows (<tr>).
	4. Reject if all rows have only 1 cell.
	5. Check exact keyword tokens on table ID/class.
	6. Traversal stops at <main> or <article> parent tags.
	"""
	# Extract table classes
	table_classes = [c.lower() for c in table.get("class", []) if isinstance(c, str)]
	is_whitelisted = any(
		kw in cls for cls in table_classes for kw in ["infobox", "wikitable", "data", "table-all", "grid"]
	)

	rows = table.find_all("tr")
	if len(rows) < 2:
		return False

	# Extract direct row cells
	all_cells = []
	for r in rows:
		row_cells = r.find_all(["th", "td"], recursive=False)
		all_cells.extend(row_cells)

	if not all_cells:
		return False

	# Check row cell counts
	row_lengths = []
	for r in rows:
		row_cells = r.find_all(["th", "td"], recursive=False)
		if row_cells:
			row_lengths.append(len(row_cells))
	if row_lengths and all(l == 1 for l in row_lengths):
		return False

	if is_whitelisted:
		return True

	# Reject explicit layout roles
	table_role = (table.get("role") or "").lower()
	if table_role in ["presentation", "none", "navigation"]:
		return False

	ignored_keywords = {
		"nav", "navigation", "navbox", "sidebar", "menu", "vertical-navbox",
		"navbox-inner", "metadata", "maintenance", "mbox", "ambox", "imbox",
		"tmbox", "fmbox", "ombox", "cmbox", "warning", "error", "alert",
		"caution", "info", "toc", "footer", "header", "banner", "ad", "ads",
		"social", "share", "login", "signup"
	}

	def extract_tokens(text: str) -> set[str]:
		return set(re.split(r"[^a-z0-9]+", text.lower())) if text else set()

	table_id = table.get("id") or ""
	table_tokens = extract_tokens(table_id)
	for cls in table_classes:
		table_tokens.update(extract_tokens(cls))

	if table_tokens.intersection(ignored_keywords):
		return False

	# Parent checks (Stop at <main> or <article>)
	for parent in table.parents:
		if parent.name in ["main", "article"]:
			break
		if parent.name in ["nav", "header", "footer", "aside"]:
			return False
		parent_role = (parent.get("role") or "").lower()
		if parent_role in ["navigation", "banner", "contentinfo"]:
			return False

		parent_id = parent.get("id") or ""
		parent_classes = [c for c in parent.get("class", []) if isinstance(c, str)]
		parent_tokens = extract_tokens(parent_id)
		for p_cls in parent_classes:
			parent_tokens.update(extract_tokens(p_cls))

		if parent_tokens.intersection(ignored_keywords):
			return False

		if parent.name == "body":
			break

	# Text content and link density checks
	cell_texts = []
	empty_cells = 0
	total_text_len = 0
	link_text_len = 0

	for cell in all_cells:
		text = " ".join(cell.get_text().split()).strip()
		cell_texts.append(text)
		if not text:
			empty_cells += 1
		else:
			total_text_len += len(text)
			for a in cell.find_all("a", href=True):
				link_text = " ".join(a.get_text().split()).strip()
				link_text_len += len(link_text)

	if total_text_len < 15:
		return False

	if empty_cells / len(all_cells) > 0.6:
		return False

	if total_text_len > 0 and (link_text_len / total_text_len) > 0.8:
		return False

	return True


def parse_html(html: str) -> Dict[str, object]:
	"""Parse raw HTML into a structured dictionary.

	Args:
		html: Raw HTML string to parse.

	Returns:
		A dictionary containing title, headings, paragraphs, links, and tables.
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
		if not is_data_table(table):
			continue

		rows = []
		for tr in table.find_all("tr"):
			cells = [_clean_text(cell.get_text()) for cell in tr.find_all(["th", "td"])]
			cells = [cell for cell in cells if cell]
			if cells:
				rows.append(cells)

		if not rows:
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
