"""Custom exceptions module for ScrapeX.

Defines a clean exception hierarchy for network issues, content issues,
configuration issues, and exporter issues, mapping each to appropriate HTTP status codes.
"""

from __future__ import annotations
from typing import Optional

class ScrapeXError(Exception):
    """Base exception class for all ScrapeX errors.
    
    Attributes:
        detail (str): User-friendly error message description.
        status_code (int): Corresponding HTTP status code for API responses.
    """
    def __init__(self, detail: str, status_code: int = 500) -> None:
        super().__init__(detail)
        self.detail = detail
        self.status_code = status_code


class FetchError(ScrapeXError):
    """Base exception for all fetching-related failures."""
    pass


class URLValidationError(FetchError):
    """Raised when URL is malformed or lacks correct scheme (http/https)."""
    def __init__(self, detail: str = "Invalid URL format. URL must start with http:// or https://.") -> None:
        super().__init__(detail, status_code=400)


class ConnectionTimeoutError(FetchError):
    """Raised when network request to the target server times out."""
    def __init__(self, detail: str = "Request timed out. The target server took too long to respond.") -> None:
        super().__init__(detail, status_code=504)


class ConnectionFailedError(FetchError):
    """Raised when connection cannot be established (DNS resolution fails, port closed, refused)."""
    def __init__(self, detail: str = "Failed to connect to the target server. Please verify the URL or domain.") -> None:
        super().__init__(detail, status_code=502)


class HTTPClientError(FetchError):
    """Raised for 4xx HTTP client errors returned by the target website."""
    def __init__(self, status_code: int, detail: Optional[str] = None) -> None:
        if not detail:
            if status_code == 403:
                detail = "Access denied. The target website blocked the request (HTTP 403 Forbidden)."
            elif status_code == 404:
                detail = "Page not found. The target website returned a 404 error."
            else:
                detail = f"The target website returned client error HTTP {status_code}."
        # We return a 502 Bad Gateway to our API callers since the target site is the failing upstream.
        super().__init__(detail, status_code=502)


class HTTPServerError(FetchError):
    """Raised for 5xx HTTP server errors returned by the target website."""
    def __init__(self, status_code: int, detail: Optional[str] = None) -> None:
        if not detail:
            detail = f"The target website returned a server error (HTTP {status_code})."
        # We return a 502 Bad Gateway to our API callers since the target site is the failing upstream.
        super().__init__(detail, status_code=502)


class EmptyOrNonHTMLContentError(FetchError):
    """Raised when the fetched URL returns empty content or a document that is not HTML."""
    def __init__(self, detail: str = "The target URL did not return a valid HTML document. Only HTML pages can be scraped.") -> None:
        super().__init__(detail, status_code=422)


class AIAnalysisError(ScrapeXError):
    """Custom exception raised for errors during AI analysis or external API communication (e.g. Groq API errors)."""
    def __init__(self, detail: str, status_code: int = 502) -> None:
        super().__init__(detail, status_code=status_code)


class ConfigurationError(ScrapeXError):
    """Custom exception raised when a required configuration or API key is missing or empty."""
    def __init__(self, detail: str) -> None:
        super().__init__(detail, status_code=500)


class ExportError(ScrapeXError):
    """Base exception for all export-related failures."""
    pass


class CSVExportError(ExportError):
    """Raised when structured data cannot be written to CSV format."""
    def __init__(self, detail: str = "Failed to export data to CSV.") -> None:
        super().__init__(detail, status_code=500)


class PDFExportError(ExportError):
    """Raised when structured data cannot be rendered as a PDF report."""
    def __init__(self, detail: str = "Failed to export data to PDF.") -> None:
        super().__init__(detail, status_code=500)
