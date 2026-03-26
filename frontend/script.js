const form = document.getElementById("scrape-form");
const loadingMsg = document.getElementById("loading-message");

// Result elements
const titleEl = document.getElementById("result-title");
const lengthEl = document.getElementById("stat-length");
const headingsEl = document.getElementById("stat-headings");
const paragraphsEl = document.getElementById("stat-paragraphs");
const linksEl = document.getElementById("stat-links");
const tablesEl = document.getElementById("stat-tables");
const previewEl = document.getElementById("content-preview");

// Download buttons
const csvBtn = document.getElementById("download-csv");
const pdfBtn = document.getElementById("download-pdf");

// Handle form submit
form.addEventListener("submit", async (e) => {
	e.preventDefault();

	const url = document.getElementById("url-input").value;

	if (!url) {
		alert("Please enter a URL");
		return;
	}

	loadingMsg.textContent = "Scraping...";

	try {
		const response = await fetch("http://127.0.0.1:8000/scrape", {
			method: "POST",
			headers: {
				"Content-Type": "application/json"
			},
			body: JSON.stringify({ url })
		});

		const data = await response.json();

		loadingMsg.textContent = "";

		if (data.error) {
			alert(data.error);
			return;
		}

		// Fill UI
		titleEl.textContent = data.title || "No title";
		lengthEl.textContent = data.content_length || 0;
		headingsEl.textContent = data.headings?.length || 0;
		paragraphsEl.textContent = data.paragraphs?.length || 0;
		linksEl.textContent = data.links?.length || 0;
		tablesEl.textContent = data.tables?.length || 0;

		previewEl.textContent = data.clean_text
			? data.clean_text.slice(0, 300) + "..."
			: "No preview available";

	} catch (error) {
		console.error(error);
		loadingMsg.textContent = "";
		alert("Error connecting to backend");
	}
});

// Download handlers
csvBtn.addEventListener("click", () => {
	window.open("http://127.0.0.1:8000/download/csv");
});

pdfBtn.addEventListener("click", () => {
	window.open("http://127.0.0.1:8000/download/pdf");
});