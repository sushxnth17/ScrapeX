import os
import tempfile
import pytest
from backend.exporter.csv_export import export_to_csv
from backend.exporter.pdf import export_to_pdf

@pytest.fixture
def sample_scrape_data():
    """Returns a dictionary containing mock scrape data."""
    return {
        "url": "https://example.com/test",
        "title": "Test Document Title",
        "clean_text": "Paragraph content example text.",
        "headings": [{"level": "h1", "text": "Test Heading"}],
        "paragraphs": ["Paragraph content example text."],
        "links": [{"text": "Target Link", "href": "https://example.com/target"}],
        "tables": [[["Col 1", "Col 2"], ["Row 1a", "Row 1b"]]],
    }


def test_export_to_csv(sample_scrape_data):
    """Verify export_to_csv creates CSV files with correct tabular headers."""
    with tempfile.TemporaryDirectory() as tmpdir:
        links_file = os.path.join(tmpdir, "links.csv")
        tables_file = os.path.join(tmpdir, "tables.csv")
        
        export_to_csv(sample_scrape_data, links_filename=links_file, tables_filename=tables_file)
        
        assert os.path.exists(links_file)
        assert os.path.exists(tables_file)
        
        # Check links CSV contents
        with open(links_file, "r", encoding="utf-8") as f:
            links_content = f.read()
            assert "href" in links_content
            assert "https://example.com/target" in links_content

        # Check tables CSV contents
        with open(tables_file, "r", encoding="utf-8") as f:
            tables_content = f.read()
            assert "table_index" in tables_content
            assert "Row 1a" in tables_content


def test_export_to_pdf(sample_scrape_data):
    """Verify export_to_pdf builds report documents cleanly."""
    with tempfile.TemporaryDirectory() as tmpdir:
        pdf_file = os.path.join(tmpdir, "report.pdf")
        
        export_to_pdf(sample_scrape_data, pdf_file)
        
        assert os.path.exists(pdf_file)
        assert os.path.getsize(pdf_file) > 0
