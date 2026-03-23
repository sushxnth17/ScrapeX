"""Export structured scrape results into CSV files."""

from __future__ import annotations

from typing import Any, Dict, List

import pandas as pd


def _normalize_links(raw_links: Any) -> List[Dict[str, str]]:
	"""Return a clean list of link dictionaries with text and href keys."""
	if not isinstance(raw_links, list):
		return []

	normalized: List[Dict[str, str]] = []
	for item in raw_links:
		if not isinstance(item, dict):
			continue

		text = str(item.get("text", "") or "").strip()
		href = str(item.get("href", "") or "").strip()
		if not href:
			continue

		normalized.append({"text": text, "href": href})

	return normalized


def _flatten_tables(raw_tables: Any) -> List[Dict[str, str]]:
	"""Flatten nested tables into one row per table row for CSV export."""
	if not isinstance(raw_tables, list):
		return []

	flat_rows: List[Dict[str, str]] = []
	for table_index, table in enumerate(raw_tables, start=1):
		if not isinstance(table, list):
			continue

		for row_index, row in enumerate(table, start=1):
			if not isinstance(row, list) or not row:
				continue

			row_data: Dict[str, str] = {
				"table_index": table_index,
				"row_index": row_index,
			}
			for cell_index, cell_value in enumerate(row, start=1):
				row_data[f"col_{cell_index}"] = str(cell_value or "").strip()

			flat_rows.append(row_data)

	return flat_rows


def export_to_csv(data: Dict[str, Any], base_filename: str = "output") -> None:
	"""Export links and tables from parsed scrape data into CSV files.

	Args:
		data: Parsed scrape output dictionary.
		base_filename: Reserved for future naming strategies.
	"""
	_ = base_filename

	payload = data if isinstance(data, dict) else {}

	links = _normalize_links(payload.get("links", []))
	if links:
		links_df = pd.DataFrame(links, columns=["text", "href"])
		links_df.to_csv("links.csv", index=False)
		print("Links CSV saved")

	table_rows = _flatten_tables(payload.get("tables", []))
	if table_rows:
		tables_df = pd.DataFrame(table_rows)
		tables_df.to_csv("tables.csv", index=False)
		print("Tables CSV saved")