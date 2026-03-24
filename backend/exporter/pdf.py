"""Utilities for generating PDF reports from scraped web data."""

from typing import Any, Dict
from xml.sax.saxutils import escape

from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer


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

	try:
		doc.build(story)
		print("PDF report generated")
	except Exception as error:
		print(f"Failed to generate PDF report: {error}")