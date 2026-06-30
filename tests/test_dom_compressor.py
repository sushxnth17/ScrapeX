import pytest
from backend.ai import DOMCompressor

def test_dom_compressor_basic():
    """Verify DOMCompressor extracts page title and structural tokens."""
    html = """
    <html>
      <head><title>ScrapeX Target</title></head>
      <body>
        <div>
          <h1>Topic Title</h1>
          <p>Important intro text here which is long enough to satisfy checks.</p>
          <p>Another paragraph block for testing purposes.</p>
        </div>
      </body>
    </html>
    """
    
    compressor = DOMCompressor()
    summary = compressor.compress(html)
    
    assert summary is not None
    assert summary["page_title"] == "ScrapeX Target"
    assert len(summary["first_3_paragraphs"]) > 0
    assert "Important intro text" in summary["first_3_paragraphs"][0]


def test_dom_compressor_tables():
    """Verify DOMCompressor counts table elements correctly."""
    html = """
    <html>
      <body>
        <table>
          <tr><td>Data A</td><td>Data B</td></tr>
        </table>
      </body>
    </html>
    """
    
    compressor = DOMCompressor()
    summary = compressor.compress(html)
    
    assert summary is not None
    assert summary["number_of_tables"] == 1
