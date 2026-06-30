import pytest
from backend.extractor import extract_content, extract_with_trafilatura, extract_basic

def test_extract_with_trafilatura_success(mocker):
    """Verify trafilatura extractor correctly parses valid HTML content."""
    # Mock text must be > 200 characters to pass MIN_TEXT_LENGTH check
    long_text = "This is a clean, readable main article text that contains useful information and is repeated multiple times to ensure it satisfies the minimum character length required by the extractor module configuration." * 2
    mocker.patch("trafilatura.extract", return_value=long_text)
    html = "<html><body><article><p>Some HTML paragraphs</p></article></body></html>"
    
    result = extract_content(html)
    assert result is not None
    assert result["title"] == "Untitled"
    assert "clean, readable" in result["text"]


def test_extract_fallback_to_basic_on_trafilatura_fail(mocker):
    """Verify that if trafilatura fails (returns None), the pipeline falls back to BeautifulSoup basic extractor."""
    mocker.patch("trafilatura.extract", return_value=None)
    
    # Simple HTML snippet containing multiple >50 character paragraphs to satisfy BeautifulSoup basic parsing constraints
    html = """
    <html>
      <head><title>ScrapeX Test Title</title></head>
      <body>
        <p>This is paragraph block one which has a length that is longer than fifty characters to pass parsing checks.</p>
        <p>This is paragraph block two which also has a length that is longer than fifty characters to satisfy the minimum requirements.</p>
        <p>This is paragraph block three which also has a length that is longer than fifty characters to satisfy the minimum requirements.</p>
      </body>
    </html>
    """
    
    result = extract_content(html)
    assert result is not None
    assert result["title"] == "ScrapeX Test Title"
    assert "paragraph block one" in result["text"]


def test_extract_content_both_fail(mocker):
    """Verify extract_content returns None when both extractors fail to find valid content."""
    mocker.patch("trafilatura.extract", return_value=None)
    
    # HTML with no valid long paragraphs (less than minimum length)
    html = "<html><body><p>Short</p></body></html>"
    result = extract_content(html)
    assert result is None
