"""FastAPI app exposing ScrapeX scraping pipeline and AI analysis endpoints."""

from __future__ import annotations

import logging
import os
import uuid
from fastapi import FastAPI, HTTPException, BackgroundTasks, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, HttpUrl
import uvicorn

try:
	from .logging_config import configure_logging
except ImportError:
	from logging_config import configure_logging

configure_logging()
logger = logging.getLogger(__name__)

try:
	# Works when running as a package: uvicorn backend.app:app
	from .main import scrape
	from .fetcher import fetch_html
	from .ai import AIAnalyzer
	from .exceptions import ScrapeXError
except ImportError:
	# Works when running from backend folder: uvicorn app:app or uvicorn api:app
	from main import scrape
	from fetcher import fetch_html
	from ai import AIAnalyzer
	from exceptions import ScrapeXError

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


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
	errors = exc.errors()
	error_details = []
	for err in errors:
		loc = err.get("loc", [])
		field_name = loc[-1] if loc else "payload"
		err_type = err.get("type", "")
		msg = err.get("msg", "")
		
		if field_name == "url":
			if "missing" in err_type or "required" in msg.lower():
				error_details.append("The 'url' parameter is required.")
			elif "scheme" in err_type or "scheme" in msg.lower():
				error_details.append("Invalid URL: Only 'http' and 'https' protocols are supported. Protocols like ftp, file, or data are rejected.")
			elif "url" in err_type or "url" in msg.lower():
				# Check if empty
				input_val = err.get("input", "") or ""
				if not str(input_val).strip():
					error_details.append("Invalid URL: The URL cannot be empty or blank.")
				else:
					error_details.append(f"Invalid URL format: {msg}.")
			else:
				error_details.append(f"Invalid URL: {msg}.")
		elif field_name == "body":
			error_details.append("Malformed request: The request body is empty or not valid JSON.")
		else:
			error_details.append(f"Invalid value for '{field_name}': {msg}.")
			
	detail_msg = "; ".join(error_details) if error_details else "Malformed request payload."
	logger.warning(f"Request validation failed for client request: {detail_msg}")
	
	return JSONResponse(
		status_code=400,
		content={"detail": f"Validation Error: {detail_msg}"}
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
	try:
		html = fetch_html(url_str)
		if not html:
			raise HTTPException(
				status_code=502, detail="Analysis failed: Unable to fetch target URL."
			)

		analyzer = AIAnalyzer()
		analysis = analyzer.analyze_page(html=html, url=url_str)
		return analysis.to_dict()
	except ScrapeXError as exc:
		logger.error(f"Analysis failed for {url_str}: {exc.detail}", exc_info=True)
		raise HTTPException(status_code=exc.status_code, detail=f"Analysis failed: {exc.detail}") from exc
	except Exception as exc:
		logger.exception(f"Unexpected analysis failure for URL {url_str}")
		raise HTTPException(status_code=500, detail="Analysis failed: An unexpected internal server error occurred.") from exc


@app.post("/scrape")
def scrape_endpoint(payload: ScrapeRequest):
	"""Scrape a URL and return structured result."""
	url_str = str(payload.url)
	try:
		result = scrape(url_str)
	except ScrapeXError as exc:
		logger.error(f"Scraping failed for {url_str}: {exc.detail}", exc_info=True)
		raise HTTPException(status_code=exc.status_code, detail=f"Scraping failed: {exc.detail}") from exc
	except Exception as exc:
		logger.exception(f"Unexpected scraping failure for URL {url_str}")
		raise HTTPException(status_code=500, detail="Scraping failed: An unexpected internal server error occurred.") from exc

	if result is None:
		logger.error(f"Scraping returned None for {url_str}")
		raise HTTPException(status_code=502, detail="Scraping failed: Unable to fetch or process URL.")

	scrape_cache[url_str] = result
	return result


def remove_temp_file(filepath: str):
	"""Helper task to clean up temporary files after sending the response."""
	try:
		if os.path.exists(filepath):
			os.remove(filepath)
	except Exception as err:
		logger.warning(f"Failed to remove temporary file {filepath}: {err}", exc_info=True)


@app.post("/download/csv")
def download_csv(payload: ScrapeRequest, background_tasks: BackgroundTasks):
	"""Download scraped links as a CSV file."""
	url_str = str(payload.url)
	try:
		result = scrape_cache.get(url_str) or scrape(url_str)
	except ScrapeXError as exc:
		logger.error(f"CSV export failed to scrape {url_str}: {exc.detail}", exc_info=True)
		raise HTTPException(status_code=exc.status_code, detail=f"Scraping failed: {exc.detail}") from exc
	except Exception as exc:
		logger.exception(f"Unexpected scraping failure during CSV download for URL {url_str}")
		raise HTTPException(status_code=500, detail="Scraping failed: An unexpected internal server error occurred.") from exc

	if not result:
		logger.error(f"Scraping returned empty result during CSV download for {url_str}")
		raise HTTPException(status_code=502, detail="Scraping failed: Unable to fetch or process URL.")

	scrape_cache[url_str] = result
	
	links_fn = f"links_{uuid.uuid4().hex}.csv"
	tables_fn = f"tables_{uuid.uuid4().hex}.csv"
	try:
		export_to_csv(result, links_filename=links_fn, tables_filename=tables_fn)
	except ScrapeXError as exc:
		logger.error(f"CSV generation failed: {exc.detail}", exc_info=True)
		raise HTTPException(status_code=exc.status_code, detail=f"CSV generation failed: {exc.detail}") from exc
	except Exception as exc:
		logger.exception(f"Unexpected CSV generation failure for {url_str}")
		raise HTTPException(status_code=500, detail="CSV generation failed: An unexpected internal server error occurred.") from exc

	background_tasks.add_task(remove_temp_file, links_fn)
	background_tasks.add_task(remove_temp_file, tables_fn)
	return FileResponse(links_fn, media_type="text/csv", filename="data.csv")


@app.post("/download/tables-csv")
def download_tables_csv(payload: ScrapeRequest, background_tasks: BackgroundTasks):
	"""Download scraped tables as a CSV file."""
	url_str = str(payload.url)
	try:
		result = scrape_cache.get(url_str) or scrape(url_str)
	except ScrapeXError as exc:
		logger.error(f"Tables CSV export failed to scrape {url_str}: {exc.detail}", exc_info=True)
		raise HTTPException(status_code=exc.status_code, detail=f"Scraping failed: {exc.detail}") from exc
	except Exception as exc:
		logger.exception(f"Unexpected scraping failure during tables CSV download for URL {url_str}")
		raise HTTPException(status_code=500, detail="Scraping failed: An unexpected internal server error occurred.") from exc

	if not result:
		logger.error(f"Scraping returned empty result during tables CSV download for {url_str}")
		raise HTTPException(status_code=502, detail="Scraping failed: Unable to fetch or process URL.")

	scrape_cache[url_str] = result
	
	links_fn = f"links_{uuid.uuid4().hex}.csv"
	tables_fn = f"tables_{uuid.uuid4().hex}.csv"
	try:
		export_to_csv(result, links_filename=links_fn, tables_filename=tables_fn)
	except ScrapeXError as exc:
		logger.error(f"CSV generation failed: {exc.detail}", exc_info=True)
		raise HTTPException(status_code=exc.status_code, detail=f"CSV generation failed: {exc.detail}") from exc
	except Exception as exc:
		logger.exception(f"Unexpected CSV generation failure for {url_str}")
		raise HTTPException(status_code=500, detail="CSV generation failed: An unexpected internal server error occurred.") from exc

	background_tasks.add_task(remove_temp_file, links_fn)
	background_tasks.add_task(remove_temp_file, tables_fn)
	return FileResponse(tables_fn, media_type="text/csv", filename="tables.csv")


@app.post("/download/pdf")
def download_pdf(payload: ScrapeRequest, background_tasks: BackgroundTasks):
	"""Download scraped data as a PDF report."""
	url_str = str(payload.url)
	try:
		result = scrape_cache.get(url_str) or scrape(url_str)
	except ScrapeXError as exc:
		logger.error(f"PDF export failed to scrape {url_str}: {exc.detail}", exc_info=True)
		raise HTTPException(status_code=exc.status_code, detail=f"Scraping failed: {exc.detail}") from exc
	except Exception as exc:
		logger.exception(f"Unexpected scraping failure during PDF download for URL {url_str}")
		raise HTTPException(status_code=500, detail="Scraping failed: An unexpected internal server error occurred.") from exc

	if not result:
		logger.error(f"Scraping returned empty result during PDF download for {url_str}")
		raise HTTPException(status_code=502, detail="Scraping failed: Unable to fetch or process URL.")

	scrape_cache[url_str] = result
	
	pdf_fn = f"report_{uuid.uuid4().hex}.pdf"
	try:
		export_to_pdf(result, pdf_fn)
	except ScrapeXError as exc:
		logger.error(f"PDF generation failed: {exc.detail}", exc_info=True)
		raise HTTPException(status_code=exc.status_code, detail=f"PDF generation failed: {exc.detail}") from exc
	except Exception as exc:
		logger.exception(f"Unexpected PDF generation failure for {url_str}")
		raise HTTPException(status_code=500, detail="PDF generation failed: An unexpected internal server error occurred.") from exc

	background_tasks.add_task(remove_temp_file, pdf_fn)
	return FileResponse(pdf_fn, media_type="application/pdf", filename="data.pdf")


if __name__ == "__main__":
	uvicorn.run("app:app", host="127.0.0.1", port=8000)
