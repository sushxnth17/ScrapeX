"""FastAPI app exposing ScrapeX scraping pipeline."""

from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, HttpUrl
import uvicorn

try:
	# Works when running as a package: uvicorn backend.app:app
	from .main import scrape
except ImportError:
	# Works when running from backend folder: uvicorn app:app or uvicorn api:app
	from main import scrape

try:
	from .exporter.csv_export import export_to_csv
	from .exporter.pdf import export_to_pdf
except ImportError:
	from exporter.csv_export import export_to_csv
	from exporter.pdf import export_to_pdf


class ScrapeRequest(BaseModel):
	"""Payload for scrape endpoint."""

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
	}


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


@app.post("/download/csv")
def download_csv(payload: ScrapeRequest):
	"""Download scraped links as a CSV file."""
	url_str = str(payload.url)
	try:
		result = scrape_cache.get(url_str) or scrape(url_str)
	except Exception as exc:
		raise HTTPException(status_code=500, detail=f"Scraping failed: {exc}") from exc

	if not result:
		raise HTTPException(status_code=502, detail="Scraping failed: Unable to fetch or process URL.")

	scrape_cache[url_str] = result
	export_to_csv(result)
	return FileResponse("links.csv", media_type="text/csv", filename="data.csv")


@app.post("/download/tables-csv")
def download_tables_csv(payload: ScrapeRequest):
	"""Download scraped tables as a CSV file."""
	url_str = str(payload.url)
	try:
		result = scrape_cache.get(url_str) or scrape(url_str)
	except Exception as exc:
		raise HTTPException(status_code=500, detail=f"Scraping failed: {exc}") from exc

	if not result:
		raise HTTPException(status_code=502, detail="Scraping failed: Unable to fetch or process URL.")

	scrape_cache[url_str] = result
	export_to_csv(result)
	return FileResponse("tables.csv", media_type="text/csv", filename="tables.csv")


@app.post("/download/pdf")
def download_pdf(payload: ScrapeRequest):
	"""Download scraped data as a PDF report."""
	url_str = str(payload.url)
	try:
		result = scrape_cache.get(url_str) or scrape(url_str)
	except Exception as exc:
		raise HTTPException(status_code=500, detail=f"Scraping failed: {exc}") from exc

	if not result:
		raise HTTPException(status_code=502, detail="Scraping failed: Unable to fetch or process URL.")

	scrape_cache[url_str] = result
	export_to_pdf(result)
	return FileResponse("report.pdf", media_type="application/pdf", filename="data.pdf")


if __name__ == "__main__":
	uvicorn.run("app:app", host="127.0.0.1", port=8000)
