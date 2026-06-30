import pytest
from unittest.mock import MagicMock
from backend.exceptions import (
    URLValidationError,
    ConnectionFailedError,
    ConnectionTimeoutError,
    EmptyOrNonHTMLContentError,
)
from backend.fetcher import fetch_html, fetch_with_requests, fetch_with_playwright

# Playwright mock structure
class MockPage:
    def __init__(self, html_content="<html><body><h1>Playwright Mock</h1></body></html>", content_type="text/html"):
        self.html_content = html_content
        self.headers = {"content-type": content_type}

    def goto(self, url, timeout=0, wait_until=""):
        class MockResponse:
            def __init__(self, headers):
                self.headers = headers
        return MockResponse(self.headers)

    def wait_for_timeout(self, ms):
        pass

    def evaluate(self, js):
        pass

    def content(self):
        return self.html_content

    def reload(self, timeout=0, wait_until=""):
        pass

class MockContext:
    def __init__(self, page):
        self._page = page

    def new_page(self):
        return self._page

class MockBrowser:
    def __init__(self, context):
        self._context = context

    def new_context(self, **kwargs):
        return self._context

class MockPlaywright:
    def __init__(self, browser):
        self.chromium = self
        self._browser = browser

    def launch(self, **kwargs):
        return self._browser

class MockSyncPlaywright:
    def __init__(self, page):
        self._playwright = MockPlaywright(MockBrowser(MockContext(page)))

    def __enter__(self):
        return self._playwright

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass


def test_fetch_html_validation():
    """Verify url input checks in fetch_html raise proper URLValidationError."""
    with pytest.raises(URLValidationError, match="empty or blank"):
        fetch_html("   ")

    with pytest.raises(URLValidationError, match="Missing scheme"):
        fetch_html("google.com")

    with pytest.raises(URLValidationError, match="Unsupported protocol"):
        fetch_html("ftp://google.com")

    with pytest.raises(URLValidationError, match="Missing domain/host"):
        fetch_html("http:///path")


def test_fetch_with_requests_success(mocker):
    """Verify requests fetcher returns HTML on HTTP 200."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    # Must be > 500 characters to pass MIN_HTML_LENGTH check
    mock_resp.text = "<html><body><h1>Hello Requests</h1>" + "<p>Filler paragraph text to make the HTML string longer.</p>" * 20 + "</body></html>"
    mock_resp.apparent_encoding = "utf-8"
    mock_resp.headers = {"Content-Type": "text/html; charset=utf-8"}
    
    mocker.patch("requests.get", return_value=mock_resp)
    
    html = fetch_with_requests("http://example.com")
    assert "Hello Requests" in html


def test_fetch_with_requests_non_html(mocker):
    """Verify requests fetcher raises EmptyOrNonHTMLContentError for JSON responses."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = '{"status": "ok"}'
    mock_resp.apparent_encoding = "utf-8"
    mock_resp.headers = {"Content-Type": "application/json"}
    
    mocker.patch("requests.get", return_value=mock_resp)
    
    with pytest.raises(EmptyOrNonHTMLContentError, match="non-HTML Content-Type"):
        fetch_with_requests("http://example.com")


def test_fetch_with_playwright_success(mocker):
    """Verify Playwright fallback succeeds when configured correctly."""
    # Must be > 500 characters to pass MIN_HTML_LENGTH check
    long_html = "<html><body><h1>Hello Playwright</h1>" + "<p>Filler paragraph text to make the HTML string longer.</p>" * 20 + "</body></html>"
    mock_page = MockPage(html_content=long_html)
    mocker.patch("backend.fetcher.sync_playwright", return_value=MockSyncPlaywright(mock_page))

    html = fetch_with_playwright("http://example.com")
    assert "Hello Playwright" in html


def test_fetch_with_playwright_non_html(mocker):
    """Verify Playwright checks headers and fails on non-HTML responses."""
    mock_page = MockPage(html_content='{"err": "api"}', content_type="application/json")
    mocker.patch("backend.fetcher.sync_playwright", return_value=MockSyncPlaywright(mock_page))

    with pytest.raises(EmptyOrNonHTMLContentError, match="non-HTML Content-Type"):
        fetch_with_playwright("http://example.com")
