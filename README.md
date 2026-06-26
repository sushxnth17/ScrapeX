#  ScrapeX

> **Transform websites into structured, exportable insights.**

ScrapeX is a full-stack intelligent web scraping platform that analyzes websites, extracts meaningful information, and converts it into structured reports. It combines traditional scraping techniques with a modular architecture to provide clean, organized, and exportable data.

---

##  Features

###  Intelligent Fetching
- Hybrid scraping engine
- Fast `requests`-based scraping
- Automatic Playwright fallback for JavaScript-heavy websites
- Robust request handling

###  Content Extraction
- Clean article extraction using Trafilatura
- BeautifulSoup fallback parser
- Noise reduction for cleaner content
- Structured text normalization

###  Structured Data Parsing
- Headings extraction
- Paragraph extraction
- Hyperlink extraction
- Smart HTML table detection
- Layout table filtering

###  Export Options
- Professional PDF reports
- CSV export for extracted links
- CSV export for extracted tables
- Safe concurrent downloads using unique file generation

###  Modern User Interface
- Responsive Neomorphic UI
- Tab-based results interface
- Interactive table previews
- Download progress indicators
- Improved validation messages

---

#  Tech Stack

### Backend
- FastAPI
- BeautifulSoup4
- Trafilatura
- Requests
- Playwright
- ReportLab
- Pandas

### Frontend
- HTML5
- CSS3
- JavaScript (ES6)

---

# ⚙️ Project Workflow

```text
             User URL
                 │
                 ▼
      Requests / Playwright
                 │
                 ▼
        Content Extraction
 (Trafilatura + BeautifulSoup)
                 │
                 ▼
      Structured Data Parsing
      ├── Headings
      ├── Paragraphs
      ├── Links
      └── Tables
                 │
                 ▼
        Frontend Preview
                 │
                 ▼
        PDF / CSV Export
```

---

# ✅ Current Capabilities

- Universal scraping pipeline
- JavaScript rendering support
- Structured content extraction
- Smart table filtering
- Interactive frontend
- PDF report generation
- CSV exports
- Responsive Neomorphic interface
- Download progress handling
- Improved validation feedback

---

# 📁 Project Structure

```text
ScrapeX
│
├── backend
│   ├── app.py
│   ├── fetcher.py
│   ├── extractor.py
│   ├── parser.py
│   ├── main.py
│   └── exporter
│       ├── csv_export.py
│       └── pdf.py
│
├── frontend
│   ├── index.html
│   ├── style.css
│   └── script.js
│
├── requirements.txt
└── README.md
```

---

# 🚀 Getting Started

## Clone the repository

```bash
git clone https://github.com/<your-username>/ScrapeX.git
cd ScrapeX
```

## Create a virtual environment

```bash
python -m venv venv
```

Activate it:

### Windows

```bash
venv\Scripts\activate
```

### Linux / macOS

```bash
source venv/bin/activate
```

## Install dependencies

```bash
pip install -r requirements.txt
```

## Install Playwright browser

```bash
playwright install
```

## Run the backend

```bash
uvicorn backend.app:app --reload
```

## Open the frontend

Open:

```
frontend/index.html
```

in your browser.

---

# 🛣️ Roadmap

- AI-assisted website analysis
- Website confidence scoring
- AI-powered extraction strategy selection
- Excel (.xlsx) export
- Batch URL scraping
- CSS selector extraction mode
- AI-generated page summaries
- SSRF protection
- Smart caching
- Website compatibility checker

---

# 🤝 Contributing

Contributions, feature requests, and suggestions are welcome.

If you'd like to improve ScrapeX, feel free to fork the repository and submit a pull request.


---


If you found this project useful, consider giving it a **⭐ Star** on GitHub.

It helps the project grow and motivates future development.
