import pytest
import json
import os
from fastapi.testclient import TestClient
from unittest.mock import MagicMock
from backend.app import app
from backend.exceptions import ConnectionFailedError, AIAnalysisError

client = TestClient(app)

def test_root_endpoint():
    """Verify root endpoint returns success message."""
    response = client.get("/")
    assert response.status_code == 200
    assert "ScrapeX API is running" in response.json()["message"]


def test_scrape_endpoint_success(mocker):
    """Verify scrape endpoint successfully processes valid URL."""
    mock_result = {
        "url": "http://example.com",
        "title": "Example Domain",
        "clean_text": "Sample text",
        "headings": ["Heading 1"],
        "paragraphs": ["Sample text"],
        "links": [],
        "tables": []
    }
    mocker.patch("backend.app.scrape", return_value=mock_result)

    response = client.post("/scrape", json={"url": "http://example.com"})
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Example Domain"
    assert data["clean_text"] == "Sample text"


def test_scrape_endpoint_malformed_url():
    """Verify scrape endpoint rejects empty URL and unsupported schemes with HTTP 400."""
    # 1. Empty URL
    response = client.post("/scrape", json={"url": ""})
    assert response.status_code == 400
    assert "Validation Error" in response.json()["detail"]
    assert "empty or blank" in response.json()["detail"]

    # 2. Unsupported scheme (ftp)
    response = client.post("/scrape", json={"url": "ftp://example.com"})
    assert response.status_code == 400
    assert "Validation Error" in response.json()["detail"]
    assert "ftp" in response.json()["detail"] or "protocols" in response.json()["detail"]


def test_scrape_endpoint_connection_failed(mocker):
    """Verify scrape endpoint returns HTTP 502 on network/connection failure."""
    mocker.patch("backend.app.scrape", side_effect=ConnectionFailedError("Failed to connect to the target server."))
    
    response = client.post("/scrape", json={"url": "http://thisdomaindoesnotexist12345.com"})
    assert response.status_code == 502
    assert "Scraping failed: Failed to connect" in response.json()["detail"]


def test_analyze_endpoint_success(mocker):
    """Verify analyze endpoint parses structure successfully."""
    mocker.patch("backend.app.fetch_html", return_value="<html><body>Mock HTML</body></html>")
    
    mock_analysis = MagicMock()
    mock_analysis.to_dict.return_value = {
        "website_type": "Blog",
        "framework": "WordPress",
        "content_confidence": 0.9,
        "recommended_strategy": "blog"
    }
    mocker.patch("backend.app.AIAnalyzer.analyze_page", return_value=mock_analysis)

    response = client.post("/analyze", json={"url": "http://example.com"})
    assert response.status_code == 200
    assert response.json()["website_type"] == "Blog"
    assert response.json()["framework"] == "WordPress"


def test_analyze_endpoint_ai_unavailable(mocker):
    """Verify analyze endpoint returns HTTP 502 when Groq AI model is offline/unavailable."""
    mocker.patch("backend.app.fetch_html", return_value="<html><body>Mock HTML</body></html>")
    mocker.patch("backend.app.AIAnalyzer.analyze_page", side_effect=AIAnalysisError("AI service unavailable"))

    response = client.post("/analyze", json={"url": "http://example.com"})
    assert response.status_code == 502
    assert "Analysis failed: AI service unavailable" in response.json()["detail"]


def mock_export_csv(data, links_filename, tables_filename):
    """Mock exporter helper to create empty files on disk to prevent FileResponse failures."""
    with open(links_filename, "w", encoding="utf-8") as f:
        f.write("text,href\n")
    with open(tables_filename, "w", encoding="utf-8") as f:
        f.write("table_index\n")


def test_download_csv_success(mocker):
    """Verify CSV export endpoint generates and returns a CSV file response."""
    mock_result = {
        "url": "http://example.com",
        "title": "Example Title",
        "links": [{"text": "First Link", "href": "http://example.com/first"}],
        "tables": []
    }
    mocker.patch("backend.app.scrape", return_value=mock_result)
    mocker.patch("backend.app.export_to_csv", side_effect=mock_export_csv)

    response = client.post("/download/csv", json={"url": "http://example.com"})
    assert response.status_code == 200
    assert response.headers["content-type"] == "text/csv; charset=utf-8"
    assert "attachment" in response.headers["content-disposition"]
    # Clean up temporary test files immediately if background task hasn't finished
    body = response.read()
    assert len(body) > 0


def mock_export_pdf(data, pdf_filename):
    """Mock exporter helper to write dummy PDF header."""
    with open(pdf_filename, "w") as f:
        f.write("%PDF-1.4 Mock PDF Data")


def test_download_pdf_success(mocker):
    """Verify PDF export endpoint generates and returns a PDF file response."""
    mock_result = {
        "url": "http://example.com",
        "title": "Example Title",
        "clean_text": "Sample text",
        "links": [],
        "tables": []
    }
    mocker.patch("backend.app.scrape", return_value=mock_result)
    mocker.patch("backend.app.export_to_pdf", side_effect=mock_export_pdf)

    response = client.post("/download/pdf", json={"url": "http://example.com"})
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert "attachment" in response.headers["content-disposition"]
    body = response.read()
    assert len(body) > 0
