"""Export structured scrape results into CSV files."""

from __future__ import annotations

from typing import Any, Dict, List

import pandas as pd

try:
	from backend.exceptions import CSVExportError
except ImportError:
	from exceptions import CSVExportError



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


def export_to_csv(data: Dict[str, Any], links_filename: str = "links.csv", tables_filename: str = "tables.csv") -> None:
	"""Export links and tables from parsed scrape data into CSV files.

	Args:
		data: Parsed scrape output dictionary.
		links_filename: Destination filename for links.
		tables_filename: Destination filename for tables.
	"""
	try:
		payload = data if isinstance(data, dict) else {}

		links = _normalize_links(payload.get("links", []))
		links_df = pd.DataFrame(links, columns=["text", "href"])
		links_df.to_csv(links_filename, index=False)
		print(f"Links CSV saved to {links_filename}")

		table_rows = _flatten_tables(payload.get("tables", []))
		if table_rows:
			tables_df = pd.DataFrame(table_rows)
		else:
			tables_df = pd.DataFrame(columns=["table_index", "row_index", "col_1"])
		tables_df.to_csv(tables_filename, index=False)
		print(f"Tables CSV saved to {tables_filename}")
	except Exception as exc:
		raise CSVExportError(f"Failed to generate CSV export files: {exc}") from exc