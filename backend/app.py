"""FastAPI app exposing ScrapeX scraping pipeline."""

from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, HttpUrl
import uvicorn

try:
	# Works when running from project root: uvicorn backend.app:app
	from backend.main import scrape
except ImportError:
	# Works when running from backend folder: uvicorn app:app or uvicorn api:app
	from main import scrape


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

	return result


if __name__ == "__main__":
	uvicorn.run("app:app", host="127.0.0.1", port=8000)
