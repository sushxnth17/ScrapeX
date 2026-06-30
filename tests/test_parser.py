import pytest
from backend.parser import parse_html

def test_parse_html_structure():
    """Verify parse_html successfully extracts structural headings, paragraphs, and links."""
    html = """
    <html>
      <head><title>ScrapeX Parser Page</title></head>
      <body>
        <h1>Main Heading</h1>
        <h2>Sub Heading</h2>
        <p>This is paragraph block one which has a length that is longer than fifty characters to pass parsing checks.</p>
        <p>This is paragraph block two which also has a length that is longer than fifty characters to satisfy the minimum requirements.</p>
        <a href="https://example.com/first">First Link</a>
        <a href="/relative-path">Relative Link</a>
      </body>
    </html>
    """
    
    parsed = parse_html(html)
    
    assert parsed["title"] == "ScrapeX Parser Page"
    
    # Assert headings (are flat strings in parsed output)
    headings = parsed["headings"]
    assert len(headings) == 2
    assert headings[0] == "Main Heading"
    assert headings[1] == "Sub Heading"
    
    # Assert paragraphs
    paragraphs = parsed["paragraphs"]
    assert len(paragraphs) == 2
    assert "paragraph block one" in paragraphs[0]
    assert "paragraph block two" in paragraphs[1]
    
    # Assert links
    links = parsed["links"]
    assert len(links) == 2
    assert links[0]["text"] == "First Link"
    assert links[0]["href"] == "https://example.com/first"
    assert links[1]["text"] == "Relative Link"
    assert links[1]["href"] == "/relative-path"


def test_parse_html_tables():
    """Verify parse_html extracts and structured tabular elements correctly."""
    html = """
    <html>
      <body>
        <table class="wikitable">
          <thead>
            <tr><th>Header 1</th><th>Header 2</th></tr>
          </thead>
          <tbody>
            <tr><td>Cell 1a</td><td>Cell 1b</td></tr>
            <tr><td>Cell 2a</td><td>Cell 2b</td></tr>
          </tbody>
        </table>
      </body>
    </html>
    """
    
    parsed = parse_html(html)
    tables = parsed["tables"]
    
    assert len(tables) == 1
    table = tables[0]
    assert len(table) == 3 # includes header row + 2 data rows
    assert table[0] == ["Header 1", "Header 2"]
    assert table[1] == ["Cell 1a", "Cell 1b"]
    assert table[2] == ["Cell 2a", "Cell 2b"]
