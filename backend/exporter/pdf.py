from typing import Any, Dict
from xml.sax.saxutils import escape

from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle, LongTable
from reportlab.lib import colors


def export_to_pdf(data: Dict[str, Any], filename: str = "report.pdf") -> None:
	"""Generate a clean PDF report from scraped website data.

	Args:
		data: Scraped data dictionary containing values such as title, url,
			clean_text, and headings.
		filename: Output PDF filename.
	"""
	styles = getSampleStyleSheet()
	doc = SimpleDocTemplate(filename)
	story = []

	title = str(data.get("title") or "No Title")
	url = str(data.get("url") or "")
	clean_text = str(data.get("clean_text") or "No content available")

	raw_headings = data.get("headings")
	if isinstance(raw_headings, list):
		headings = [str(item) for item in raw_headings if item]
	else:
		headings = []

	raw_tables = data.get("tables")
	if isinstance(raw_tables, list):
		tables = [item for item in raw_tables if isinstance(item, list) and item]
	else:
		tables = []

	# Title section
	story.append(Paragraph(escape(title), styles["Title"]))
	story.append(Spacer(1, 12))

	# URL section
	if url:
		story.append(Paragraph(f"<b>URL:</b> {escape(url)}", styles["Normal"]))
	else:
		story.append(Paragraph("<b>URL:</b> Not provided", styles["Normal"]))
	story.append(Spacer(1, 12))

	# Content preview section
	preview = clean_text[:1000].replace("\n", "<br/>")
	story.append(Paragraph("<b>Content Preview:</b>", styles["Heading2"]))
	story.append(Spacer(1, 6))
	story.append(Paragraph(escape(preview).replace("&lt;br/&gt;", "<br/>"), styles["BodyText"]))
	story.append(Spacer(1, 12))

	# Headings section
	story.append(Paragraph("<b>Headings:</b>", styles["Heading2"]))
	story.append(Spacer(1, 6))
	if headings:
		for heading in headings[:20]:
			story.append(Paragraph(escape(heading), styles["BodyText"], bulletText="•"))
	else:
		story.append(Paragraph("No headings available", styles["BodyText"]))
	story.append(Spacer(1, 12))

	# Tables section
	if tables:
		story.append(Paragraph("<b>Extracted Tables:</b>", styles["Heading2"]))
		story.append(Spacer(1, 6))

		cell_style = ParagraphStyle(
			'TableCellStyle',
			parent=styles['Normal'],
			fontSize=8,
			leading=10
		)
		header_style = ParagraphStyle(
			'TableHeaderStyle',
			parent=styles['Normal'],
			fontSize=8,
			leading=10,
			textColor=colors.whitesmoke,
			fontName='Helvetica-Bold'
		)

		for idx, table_data in enumerate(tables[:5], start=1):
			story.append(Paragraph(f"<b>Table {idx}:</b>", styles["Heading3"]))
			story.append(Spacer(1, 4))

			formatted_rows = []
			for r_idx, row in enumerate(table_data):
				if not isinstance(row, list):
					continue
				formatted_row = []
				for cell in row:
					text_str = str(cell or "").strip()
					if len(text_str) > 200:
						text_str = text_str[:197] + "..."
					cell_text = escape(text_str)
					style = header_style if r_idx == 0 else cell_style
					formatted_row.append(Paragraph(cell_text, style))
				if formatted_row:
					formatted_rows.append(formatted_row)

			if not formatted_rows:
				continue

			try:
				# 1. Pad rows to raw_max_cols first so we can analyze columns
				raw_max_cols = max(len(row) for row in formatted_rows)
				padded_rows = []
				for row in formatted_rows:
					padded_row = list(row)
					while len(padded_row) < raw_max_cols:
						padded_row.append(Paragraph("", cell_style))
					padded_rows.append(padded_row)

				# 2. Find columns that are not completely empty across all rows
				active_col_indices = []
				for col_idx in range(raw_max_cols):
					col_has_content = False
					for row in padded_rows:
						cell_text = row[col_idx].text.strip()
						if cell_text:
							col_has_content = True
							break
					if col_has_content:
						active_col_indices.append(col_idx)

				# 3. Limit to at most 8 active columns to ensure readability in portrait PDF
				active_col_indices = active_col_indices[:8]

				if not active_col_indices:
					continue

				# 4. Reconstruct rows keeping only active columns
				final_rows = []
				for row in padded_rows:
					final_row = [row[idx] for idx in active_col_indices]
					final_rows.append(final_row)

				max_cols = len(active_col_indices)
				col_width = 460.0 / max_cols if max_cols > 0 else 100.0
				t = LongTable(final_rows, colWidths=[col_width] * max_cols, repeatRows=1)
				t.setStyle(TableStyle([
					('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#0f9d8b")),
					('ALIGN', (0, 0), (-1, -1), 'LEFT'),
					('VALIGN', (0, 0), (-1, -1), 'TOP'),
					('BOTTOMPADDING', (0, 0), (-1, -1), 4),
					('TOPPADDING', (0, 0), (-1, -1), 4),
					('LEFTPADDING', (0, 0), (-1, -1), 4),
					('RIGHTPADDING', (0, 0), (-1, -1), 4),
					('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#eadcc8")),
					('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#fffdf7")]),
				]))
				story.append(t)
			except Exception as table_err:
				print(f"Warning: Failed to render table {idx}: {table_err}")
				story.append(Paragraph("Failed to render table layout.", styles["BodyText"]))

			story.append(Spacer(1, 12))

	try:
		doc.build(story)
		print("PDF report generated")
	except Exception as error:
		print(f"Failed to generate PDF report: {error}")
		raise error