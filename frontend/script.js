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
const linksContainer = document.getElementById("extracted-links-container");

// Helper to format error messages
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

// Populate AI Analysis Card
function populateAIAnalysis(aiData) {
	const statusBadge = document.getElementById("ai-status-badge");
	if (statusBadge) {
		statusBadge.textContent = "Analyzed";
		statusBadge.classList.add("active");
	}

	if (!aiData) return;

	document.getElementById("ai-website-type").textContent = aiData.website_type || "Unknown";
	document.getElementById("ai-framework").textContent = aiData.framework || "Unknown";

	const contentConf = Math.round((aiData.content_confidence || 0) * 100);
	document.getElementById("ai-content-confidence").textContent = `${contentConf}%`;
	const contentFill = document.getElementById("ai-content-fill");
	if (contentFill) contentFill.style.width = `${contentConf}%`;

	const tableConf = Math.round((aiData.table_confidence || 0) * 100);
	document.getElementById("ai-table-confidence").textContent = `${tableConf}%`;
	const tableFill = document.getElementById("ai-table-fill");
	if (tableFill) tableFill.style.width = `${tableConf}%`;

	const reqJsEl = document.getElementById("ai-requires-js");
	if (reqJsEl) {
		if (aiData.requires_javascript) {
			reqJsEl.textContent = "Yes";
			reqJsEl.className = "ai-value-badge js-yes";
		} else {
			reqJsEl.textContent = "No";
			reqJsEl.className = "ai-value-badge js-no";
		}
	}

	document.getElementById("ai-strategy").textContent =
		aiData.recommended_strategy || aiData.scrape_strategy || "Standard HTML extraction";
	document.getElementById("ai-summary").textContent =
		aiData.summary || "No architectural summary provided.";

	const warningsContainer = document.getElementById("ai-warnings");
	if (warningsContainer) {
		warningsContainer.innerHTML = "";
		const warnings = aiData.warnings || [];
		if (warnings.length > 0) {
			warnings.forEach(warn => {
				const card = document.createElement("div");
				const lower = warn.toLowerCase();
				let type = "warning";
				let icon = "⚠️";

				if (lower.includes("appears to use") || lower.includes("react") || lower.includes("vue") || lower.includes("angular") || lower.includes("framework")) {
					type = "info";
					icon = "ℹ️";
				} else if (lower.includes("login") || lower.includes("paywall") || lower.includes("captcha") || lower.includes("error") || lower.includes("failed")) {
					type = "danger";
					icon = "🔒";
				}

				card.className = `warning-card ${type}`;
				card.innerHTML = `<span class="warning-icon">${icon}</span><span class="warning-text">${warn}</span>`;
				warningsContainer.appendChild(card);
			});
		} else {
			const successCard = document.createElement("div");
			successCard.className = "warning-card success";
			successCard.innerHTML = `<span class="warning-icon">✓</span><span class="warning-text">No scraping obstacles or anti-scraping protections detected.</span>`;
			warningsContainer.appendChild(successCard);
		}
	}
}

// Helper to escape HTML text
function escapeHtml(str) {
	if (!str) return "";
	return String(str)
		.replace(/&/g, "&amp;")
		.replace(/</g, "&lt;")
		.replace(/>/g, "&gt;")
		.replace(/"/g, "&quot;")
		.replace(/'/g, "&#039;");
}

// Render AI Decision Pipeline visualization component
function renderDecisionPipeline(pipelineSteps) {
	const container = document.getElementById("ai-pipeline-container");
	if (!container) return;

	container.innerHTML = "";

	if (!pipelineSteps || !Array.isArray(pipelineSteps) || pipelineSteps.length === 0) {
		const fallbackEl = document.createElement("div");
		fallbackEl.className = "pipeline-fallback";
		fallbackEl.innerHTML = `
			<span class="pipeline-fallback-icon">ℹ️</span>
			<span class="pipeline-fallback-text">Using default scraping pipeline.</span>
		`;
		container.appendChild(fallbackEl);
		return;
	}

	const listEl = document.createElement("div");
	listEl.className = "pipeline-list";

	pipelineSteps.forEach((step, index) => {
		const stepEl = document.createElement("div");
		stepEl.className = `pipeline-step ${step.status || "success"}`;

		const isLast = index === pipelineSteps.length - 1;

		stepEl.innerHTML = `
			<div class="step-left">
				<div class="step-icon-box">
					<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round">
						<polyline points="20 6 9 17 4 12"></polyline>
					</svg>
				</div>
				${!isLast ? '<div class="step-connector"></div>' : ''}
			</div>
			<div class="step-content">
				<h4 class="step-title">${escapeHtml(step.title || "")}</h4>
				${step.description ? `<p class="step-description">${escapeHtml(step.description)}</p>` : ''}
			</div>
		`;

		listEl.appendChild(stepEl);
	});

	container.appendChild(listEl);
}

// Handle form submit
form.addEventListener("submit", async (e) => {
	e.preventDefault();

	const url = document.getElementById("url-input").value;

	if (!url) {
		alert("Please enter a URL");
		return;
	}

	loadingMsg.textContent = "Analyzing & Scraping...";
	const statusBadge = document.getElementById("ai-status-badge");
	if (statusBadge) {
		statusBadge.textContent = "Analyzing...";
		statusBadge.classList.remove("active");
	}
	renderDecisionPipeline(null);

	// Trigger AI Analysis in parallel with scraping
	const analyzePromise = fetch(`${API_BASE_URL}/analyze`, {
		method: "POST",
		headers: { "Content-Type": "application/json" },
		body: JSON.stringify({ url })
	})
		.then(res => res.ok ? res.json() : null)
		.then(aiData => {
			if (aiData) {
				populateAIAnalysis(aiData);
				if (loadingMsg.textContent.includes("Analyzing")) {
					loadingMsg.textContent = "AI Analysis complete. Scraping data...";
				}
			}
			return aiData;
		})
		.catch(err => {
			console.warn("AI Analysis request failed:", err);
			return null;
		});

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

		// Render AI Decision Pipeline visualization
		renderDecisionPipeline(data.pipeline_steps);

		// Fill scraping UI
		titleEl.textContent = data.title || "No title";
		lengthEl.textContent = data.content_length || 0;
		headingsEl.textContent = data.headings?.length || 0;
		paragraphsEl.textContent = data.paragraphs?.length || 0;
		linksEl.textContent = data.links?.length || 0;
		tablesEl.textContent = data.tables?.length || 0;

		previewEl.textContent = data.clean_text
			? data.clean_text.slice(0, 300) + "..."
			: "No preview available";


		// Render Extracted Headings
		const headingsContainer = document.getElementById("extracted-headings-container");
		if (headingsContainer) {
			headingsContainer.innerHTML = "";
			if (data.headings && data.headings.length > 0) {
				data.headings.forEach(heading => {
					const headingEl = document.createElement("div");
					headingEl.className = "heading-item";
					headingEl.textContent = heading;
					headingsContainer.appendChild(headingEl);
				});
			} else {
				const noHeadings = document.createElement("p");
				noHeadings.className = "no-headings-msg";
				noHeadings.textContent = "No headings found on this page.";
				headingsContainer.appendChild(noHeadings);
			}
		}

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

		// Render Extracted Links
		linksContainer.innerHTML = "";
		const uniqueLinksMap = new Map();
		
		if (data.links && data.links.length > 0) {
			for (const link of data.links) {
				const linkUrl = (link.href || "").trim();
				if (!linkUrl) continue;

				const text = (link.text || "").trim();
				if (!uniqueLinksMap.has(linkUrl)) {
					uniqueLinksMap.set(linkUrl, text);
				} else {
					const existingText = uniqueLinksMap.get(linkUrl);
					if (!existingText && text) {
						uniqueLinksMap.set(linkUrl, text);
					}
				}
			}
		}

		const uniqueLinks = Array.from(uniqueLinksMap.entries()).map(([href, text]) => ({ href, text }));

		if (uniqueLinks.length > 0) {
			if (uniqueLinks.length > 100) {
				const limitMsg = document.createElement("p");
				limitMsg.className = "links-limit-msg";
				limitMsg.textContent = "Showing first 100 links.";
				linksContainer.appendChild(limitMsg);
			}

			const displayLinks = uniqueLinks.slice(0, 100);
			displayLinks.forEach(link => {
				const linkEl = document.createElement("a");
				linkEl.className = "link-item";
				linkEl.href = link.href;
				linkEl.target = "_blank";
				linkEl.rel = "noopener noreferrer";

				const titleSpan = document.createElement("span");
				titleSpan.className = "link-title";
				titleSpan.textContent = link.text || link.href;
				linkEl.appendChild(titleSpan);

				if (link.text && link.text !== link.href) {
					const urlSpan = document.createElement("span");
					urlSpan.className = "link-url";
					urlSpan.textContent = link.href;
					linkEl.appendChild(urlSpan);
				}

				linksContainer.appendChild(linkEl);
			});
		} else {
			const noLinks = document.createElement("p");
			noLinks.className = "no-links-msg";
			noLinks.textContent = "No links found on this page.";
			linksContainer.appendChild(noLinks);
		}

		// Populate AI card asynchronously once received
		const aiResult = await analyzePromise;
		populateAIAnalysis(aiResult);

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

// Tab switching logic
const tabButtons = document.querySelectorAll(".tab-btn");
const tabPanels = document.querySelectorAll(".tab-panel");

tabButtons.forEach(btn => {
	btn.addEventListener("click", () => {
		tabButtons.forEach(b => {
			b.classList.remove("active");
			b.setAttribute("aria-selected", "false");
		});
		tabPanels.forEach(p => {
			p.classList.remove("active");
		});

		btn.classList.add("active");
		btn.setAttribute("aria-selected", "true");

		const panelId = btn.getAttribute("aria-controls");
		const panel = document.getElementById(panelId);
		if (panel) {
			panel.classList.add("active");
		}
	});
});
