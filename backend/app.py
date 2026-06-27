"""FastAPI app exposing ScrapeX scraping pipeline and AI analysis endpoints."""

from __future__ import annotations

import os
import uuid
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, HttpUrl
import uvicorn

try:
	# Works when running as a package: uvicorn backend.app:app
	from .main import scrape
	from .fetcher import fetch_html
	from .ai import AIAnalyzer
except ImportError:
	# Works when running from backend folder: uvicorn app:app or uvicorn api:app
	from main import scrape
	from fetcher import fetch_html
	from ai import AIAnalyzer

try:
	from .exporter.csv_export import export_to_csv
	from .exporter.pdf import export_to_pdf
except ImportError:
	from exporter.csv_export import export_to_csv
	from exporter.pdf import export_to_pdf


class ScrapeRequest(BaseModel):
	"""Payload for scrape endpoint."""

	url: HttpUrl


class AnalyzeRequest(BaseModel):
	"""Payload for analyze endpoint."""

	url: HttpUrl


app = FastAPI(title="ScrapeX API")

app.add_middleware(
	CORSMiddleware,
	allow_origins=["*"],
	allow_credentials=True,
	allow_methods=["*"],
	allow_headers=["*"],
)


scrape_cache: dict = {}


@app.get("/")
def root():
	"""Simple root route to confirm API is running."""
	return {
		"message": "ScrapeX API is running.",
		"docs": "/docs",
		"scrape_endpoint": "/scrape (POST)",
		"analyze_endpoint": "/analyze (POST)",
	}


@app.post("/analyze")
def analyze_endpoint(payload: AnalyzeRequest):
	"""Analyze web page structure without performing scraping."""
	url_str = str(payload.url)
	html = fetch_html(url_str)
	if not html:
		raise HTTPException(
			status_code=502, detail="Analysis failed: Unable to fetch target URL."
		)

	analyzer = AIAnalyzer()
	analysis = analyzer.analyze_page(html=html, url=url_str)
	return analysis.to_dict()


@app.post("/scrape")
def scrape_endpoint(payload: ScrapeRequest):
	"""Scrape a URL and return structured result."""
	try:
		result = scrape(str(payload.url))
	except Exception as exc:
		raise HTTPException(status_code=500, detail=f"Scraping failed: {exc}") from exc

	if result is None:
		raise HTTPException(status_code=502, detail="Scraping failed: Unable to fetch or process URL.")

	scrape_cache[str(payload.url)] = result
	return result


def remove_temp_file(filepath: str):
	"""Helper task to clean up temporary files after sending the response."""
	try:
		if os.path.exists(filepath):
			os.remove(filepath)
	except Exception as err:
		print(f"Warning: Failed to remove temporary file {filepath}: {err}")


@app.post("/download/csv")
def download_csv(payload: ScrapeRequest, background_tasks: BackgroundTasks):
	"""Download scraped links as a CSV file."""
	url_str = str(payload.url)
	try:
		result = scrape_cache.get(url_str) or scrape(url_str)
	except Exception as exc:
		raise HTTPException(status_code=500, detail=f"Scraping failed: {exc}") from exc

	if not result:
		raise HTTPException(status_code=502, detail="Scraping failed: Unable to fetch or process URL.")

	scrape_cache[url_str] = result
	
	links_fn = f"links_{uuid.uuid4().hex}.csv"
	tables_fn = f"tables_{uuid.uuid4().hex}.csv"
	try:
		export_to_csv(result, links_filename=links_fn, tables_filename=tables_fn)
	except Exception as exc:
		raise HTTPException(status_code=500, detail=f"CSV generation failed: {exc}") from exc

	background_tasks.add_task(remove_temp_file, links_fn)
	background_tasks.add_task(remove_temp_file, tables_fn)
	return FileResponse(links_fn, media_type="text/csv", filename="data.csv")


@app.post("/download/tables-csv")
def download_tables_csv(payload: ScrapeRequest, background_tasks: BackgroundTasks):
	"""Download scraped tables as a CSV file."""
	url_str = str(payload.url)
	try:
		result = scrape_cache.get(url_str) or scrape(url_str)
	except Exception as exc:
		raise HTTPException(status_code=500, detail=f"Scraping failed: {exc}") from exc

	if not result:
		raise HTTPException(status_code=502, detail="Scraping failed: Unable to fetch or process URL.")

	scrape_cache[url_str] = result
	
	links_fn = f"links_{uuid.uuid4().hex}.csv"
	tables_fn = f"tables_{uuid.uuid4().hex}.csv"
	try:
		export_to_csv(result, links_filename=links_fn, tables_filename=tables_fn)
	except Exception as exc:
		raise HTTPException(status_code=500, detail=f"CSV generation failed: {exc}") from exc

	background_tasks.add_task(remove_temp_file, links_fn)
	background_tasks.add_task(remove_temp_file, tables_fn)
	return FileResponse(tables_fn, media_type="text/csv", filename="tables.csv")


@app.post("/download/pdf")
def download_pdf(payload: ScrapeRequest, background_tasks: BackgroundTasks):
	"""Download scraped data as a PDF report."""
	url_str = str(payload.url)
	try:
		result = scrape_cache.get(url_str) or scrape(url_str)
	except Exception as exc:
		raise HTTPException(status_code=500, detail=f"Scraping failed: {exc}") from exc

	if not result:
		raise HTTPException(status_code=502, detail="Scraping failed: Unable to fetch or process URL.")

	scrape_cache[url_str] = result
	
	pdf_fn = f"report_{uuid.uuid4().hex}.pdf"
	try:
		export_to_pdf(result, pdf_fn)
	except Exception as exc:
		raise HTTPException(status_code=500, detail=f"PDF generation failed: {exc}") from exc

	background_tasks.add_task(remove_temp_file, pdf_fn)
	return FileResponse(pdf_fn, media_type="application/pdf", filename="data.pdf")


if __name__ == "__main__":
	uvicorn.run("app:app", host="127.0.0.1", port=8000)
