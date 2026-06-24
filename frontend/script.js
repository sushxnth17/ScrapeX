const form = document.getElementById("scrape-form");
const loadingMsg = document.getElementById("loading-message");
const API_BASE_URL = "http://127.0.0.1:8000";

// Result elements
const titleEl = document.getElementById("result-title");
const lengthEl = document.getElementById("stat-length");
const headingsEl = document.getElementById("stat-headings");
const paragraphsEl = document.getElementById("stat-paragraphs");
const linksEl = document.getElementById("stat-links");
const tablesEl = document.getElementById("stat-tables");
const previewEl = document.getElementById("content-preview");
const tablesContainer = document.getElementById("extracted-tables-container");

// Helper to format error messages (handles Pydantic arrays and custom details)
function getErrorMessage(data, fallbackMsg) {
	if (data && data.detail) {
		if (Array.isArray(data.detail)) {
			return data.detail.map(err => err.msg || JSON.stringify(err)).join("\n");
		}
		if (typeof data.detail === "string") {
			return data.detail;
		}
		return JSON.stringify(data.detail);
	}
	return data?.error || fallbackMsg;
}

// Download buttons
const csvBtn = document.getElementById("download-csv");
const tablesBtn = document.getElementById("download-tables");
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
		const response = await fetch(`${API_BASE_URL}/scrape`, {
			method: "POST",
			headers: {
				"Content-Type": "application/json"
			},
			body: JSON.stringify({ url })
		});

		const data = await response.json().catch(() => ({}));

		loadingMsg.textContent = "";

		if (!response.ok) {
			alert(getErrorMessage(data, `Request failed with status ${response.status}`));
			return;
		}

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

		// Render Extracted Tables
		tablesContainer.innerHTML = "";
		if (data.tables && data.tables.length > 0) {
			data.tables.forEach((tableData, index) => {
				const wrapper = document.createElement("div");
				wrapper.className = "table-wrapper";

				const tableEl = document.createElement("table");
				tableEl.className = "scraped-table";

				tableData.forEach((row, rowIndex) => {
					const tr = document.createElement("tr");
					row.forEach(cell => {
						const cellEl = document.createElement(rowIndex === 0 ? "th" : "td");
						cellEl.textContent = cell;
						tr.appendChild(cellEl);
					});
					tableEl.appendChild(tr);
				});

				wrapper.appendChild(tableEl);
				
				const titleDiv = document.createElement("h4");
				titleDiv.textContent = `Table ${index + 1}:`;
				titleDiv.style.margin = "14px 0 6px 0";
				titleDiv.style.color = "var(--ink)";
				titleDiv.style.fontFamily = "'Syne', 'Segoe UI', sans-serif";
				
				tablesContainer.appendChild(titleDiv);
				tablesContainer.appendChild(wrapper);
			});
		} else {
			const noTables = document.createElement("p");
			noTables.className = "no-tables-msg";
			noTables.textContent = "No tables found on this page.";
			tablesContainer.appendChild(noTables);
		}

	} catch (error) {
		console.error(error);
		loadingMsg.textContent = "";
		alert(`Cannot connect to backend at ${API_BASE_URL}. Make sure the API server is running.`);
	}
});

async function downloadFile(endpoint, filename, buttonEl) {
	const url = document.getElementById("url-input").value;

	if (!url) {
		alert("Please enter a URL first");
		return;
	}

	const originalText = buttonEl.textContent;
	const isPdf = filename.toLowerCase().endsWith(".pdf");
	buttonEl.textContent = isPdf ? "Downloading PDF..." : "Downloading CSV...";
	buttonEl.disabled = true;

	try {
		const response = await fetch(`${API_BASE_URL}${endpoint}`, {
			method: "POST",
			headers: {
				"Content-Type": "application/json"
			},
			body: JSON.stringify({ url })
		});

		if (!response.ok) {
			const data = await response.json().catch(() => ({}));
			alert(getErrorMessage(data, `Download failed with status ${response.status}`));
			return;
		}

		const blob = await response.blob();
		const objectUrl = window.URL.createObjectURL(blob);
		const link = document.createElement("a");
		link.href = objectUrl;
		link.download = filename;
		document.body.appendChild(link);
		link.click();
		link.remove();
		window.URL.revokeObjectURL(objectUrl);
	} catch (error) {
		console.error(error);
		alert(`Cannot connect to backend at ${API_BASE_URL}. Make sure the API server is running.`);
	} finally {
		buttonEl.textContent = originalText;
		buttonEl.disabled = false;
	}
}

// Download handlers
csvBtn.addEventListener("click", () => {
	downloadFile("/download/csv", "data.csv", csvBtn);
});

tablesBtn.addEventListener("click", () => {
	downloadFile("/download/tables-csv", "tables.csv", tablesBtn);
});

pdfBtn.addEventListener("click", () => {
	downloadFile("/download/pdf", "data.pdf", pdfBtn);
});
