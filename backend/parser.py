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


def is_data_table(table) -> bool:
	"""Determine if a <table> tag represents actual structured data rather than layout/navigation.

	Heuristics:
	1. Explicitly whitelist Wikipedia infoboxes and standard wikitable data tables.
	2. Reject layout roles: presentation, none, navigation.
	3. Reject if fewer than 2 rows (<tr>).
	4. Reject if all rows have only 1 cell (often lists or layout spacers).
	5. Reject based on ID or class keywords (nav, sidebar, menu, ad, footer, header, banner, social, etc.).
	6. Reject based on parent tag names or parent class/ID keywords.
	7. Reject if total clean text content is extremely short (e.g. < 20 characters).
	8. Reject if more than 50% of the cells are empty.
	9. Reject if the table consists mostly of links (link density > 0.75), indicating a navigation list or menu.
	"""
	# Check if it's a whitelisted class
	table_classes = [c.lower() for c in table.get("class", []) if isinstance(c, str)]
	is_infobox = any("infobox" in cls or "wikitable" in cls or "data" in cls for cls in table_classes)
	
	# If it's a Wikipedia infobox or standard data table, bypass most layout checks but still check rows
	rows = table.find_all("tr")
	if len(rows) < 2:
		return False
		
	# Extract all cells (direct td/th of rows to avoid counting cells from deeply nested tables recursively)
	all_cells = []
	for r in rows:
		row_cells = r.find_all(["th", "td"], recursive=False)
		all_cells.extend(row_cells)

	if not all_cells:
		return False

	# If all rows have only 1 cell, it is not a structured table
	row_lengths = []
	for r in rows:
		row_cells = r.find_all(["th", "td"], recursive=False)
		if row_cells:
			row_lengths.append(len(row_cells))
	if row_lengths and all(l == 1 for l in row_lengths):
		return False

	# If it's a whitelisted infobox, we can accept it directly here
	if is_infobox:
		return True

	# Reject layout roles
	table_role = (table.get("role") or "").lower()
	if table_role in ["presentation", "none", "navigation"]:
		return False

	# ID and Class keywords check
	table_id = (table.get("id") or "").lower()
	ignored_keywords = {
		"nav", "navigation", "navbox", "sidebar", "menu", "vertical-navbox",
		"navbox-inner", "metadata", "maintenance", "mbox", "ambox", "imbox",
		"tmbox", "fmbox", "ombox", "cmbox", "warning", "error", "alert",
		"caution", "info", "toc", "footer", "header", "banner", "ad", "ads",
		"social", "share", "login", "signup"
	}
	
	for kw in ignored_keywords:
		if table_id == kw or table_id.startswith(kw + "-") or table_id.endswith("-" + kw) or kw in table_id:
			return False
		for cls in table_classes:
			if cls == kw or cls.startswith(kw + "-") or cls.endswith("-" + kw) or kw in cls:
				return False

	# Check parent elements for layout/nav elements
	for parent in table.parents:
		if parent.name in ["nav", "header", "footer", "aside"]:
			return False
		parent_role = (parent.get("role") or "").lower()
		if parent_role in ["navigation", "banner", "contentinfo"]:
			return False
		parent_classes = [c.lower() for c in parent.get("class", []) if isinstance(c, str)]
		parent_id = (parent.get("id") or "").lower()
		for kw in ignored_keywords:
			if parent_id == kw or parent_id.startswith(kw + "-") or parent_id.endswith("-" + kw) or kw in parent_id:
				return False
			for cls in parent_classes:
				if cls == kw or cls.startswith(kw + "-") or cls.endswith("-" + kw) or kw in cls:
					return False
		if parent.name == "body":
			break

	# Text content analysis
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
			# Find links inside this cell
			for a in cell.find_all("a", href=True):
				link_text = " ".join(a.get_text().split()).strip()
				link_text_len += len(link_text)

	# 1. Total text check (reject if extremely small text content)
	if total_text_len < 20:
		return False

	# 2. Empty cell ratio check (reject if > 50% empty cells)
	if empty_cells / len(all_cells) > 0.5:
		return False

	# 3. Link density check (reject if link text is > 75% of total text)
	if total_text_len > 0 and (link_text_len / total_text_len) > 0.75:
		return False

	return True


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
