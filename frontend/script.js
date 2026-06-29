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

	const updateProgressBar = (fillEl, valEl, value) => {
		if (valEl) valEl.textContent = `${value}%`;
		if (fillEl) {
			fillEl.style.width = `${value}%`;
			fillEl.classList.remove("conf-green", "conf-yellow", "conf-red");
			if (value >= 90) {
				fillEl.classList.add("conf-green");
			} else if (value >= 70) {
				fillEl.classList.add("conf-yellow");
			} else {
				fillEl.classList.add("conf-red");
			}
		}
	};

	const contentConf = Math.round((aiData.content_confidence || 0) * 100);
	updateProgressBar(document.getElementById("ai-content-fill"), document.getElementById("ai-content-confidence"), contentConf);

	const tableConf = Math.round((aiData.table_confidence || 0) * 100);
	updateProgressBar(document.getElementById("ai-table-fill"), document.getElementById("ai-table-confidence"), tableConf);

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
		const iconInfo = `<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-info"><circle cx="12" cy="12" r="10"/><path d="M12 16v-4"/><path d="M12 8h.01"/></svg>`;
		const iconWarn = `<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-alert-triangle"><path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"/><line x1="12" x2="12" y1="9" y2="13"/><line x1="12" x2="12.01" y1="17" y2="17"/></svg>`;
		const iconLock = `<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-lock"><rect width="18" height="11" x="3" y="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg>`;
		const iconCheck = `<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-check"><polyline points="20 6 9 17 4 12"/></svg>`;

		if (warnings.length > 0) {
			warnings.forEach(warn => {
				const card = document.createElement("div");
				const lower = warn.toLowerCase();
				let type = "warning";
				let icon = iconWarn;

				if (lower.includes("appears to use") || lower.includes("react") || lower.includes("vue") || lower.includes("angular") || lower.includes("framework")) {
					type = "info";
					icon = iconInfo;
				} else if (lower.includes("login") || lower.includes("paywall") || lower.includes("captcha") || lower.includes("error") || lower.includes("failed")) {
					type = "danger";
					icon = iconLock;
				}

				card.className = `warning-card ${type}`;
				card.innerHTML = `<span class="warning-icon">${icon}</span><span class="warning-text">${escapeHtml(warn)}</span>`;
				warningsContainer.appendChild(card);
			});
		} else {
			const successCard = document.createElement("div");
			successCard.className = "warning-card success";
			successCard.innerHTML = `<span class="warning-icon">${iconCheck}</span><span class="warning-text">No scraping obstacles or anti-scraping protections detected.</span>`;
			warningsContainer.appendChild(successCard);
		}
	}

	// Populate Website Compatibility Report
	const compatBadge = document.getElementById("ai-compat-badge");
	if (compatBadge) {
		compatBadge.textContent = "Evaluated";
		compatBadge.classList.add("active");
	}

	const overallScore = aiData.overall_score !== undefined ? aiData.overall_score : 85;
	const scoreEl = document.getElementById("compat-score");
	if (scoreEl) scoreEl.textContent = overallScore;
	const scoreFill = document.getElementById("compat-score-fill");
	if (scoreFill) {
		scoreFill.style.width = `${overallScore}%`;
		scoreFill.classList.remove("conf-green", "conf-yellow", "conf-red");
		if (overallScore >= 90) scoreFill.classList.add("conf-green");
		else if (overallScore >= 70) scoreFill.classList.add("conf-yellow");
		else scoreFill.classList.add("conf-red");
	}

	const gradeEl = document.getElementById("compat-grade");
	if (gradeEl) {
		const grade = (aiData.compatibility_grade || "A").toUpperCase();
		gradeEl.textContent = grade;
		gradeEl.className = `compat-grade-badge grade-${grade}`;
	}

	const renderingEl = document.getElementById("compat-rendering");
	if (renderingEl) renderingEl.textContent = aiData.rendering_type || "Mostly Static";

	const jsCompEl = document.getElementById("compat-js-complexity");
	if (jsCompEl) jsCompEl.textContent = aiData.javascript_complexity || "Low";

	const iconCheck = `<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-check"><polyline points="20 6 9 17 4 12"/></svg>`;
	const iconWarn = `<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-alert-triangle"><path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"/><line x1="12" x2="12" y1="9" y2="13"/><line x1="12" x2="12.01" y1="17" y2="17"/></svg>`;
	const iconInfo = `<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-info"><circle cx="12" cy="12" r="10"/><path d="M12 16v-4"/><path d="M12 8h.01"/></svg>`;

	const strengthsContainer = document.getElementById("compat-strengths");
	if (strengthsContainer) {
		strengthsContainer.innerHTML = "";
		const strengths = aiData.strengths || [];
		if (strengths.length > 0) {
			strengths.forEach(item => {
				const card = document.createElement("div");
				card.className = "compat-card strength";
				card.innerHTML = `<span class="compat-card-icon">${iconCheck}</span><span class="compat-card-text">${escapeHtml(item)}</span>`;
				strengthsContainer.appendChild(card);
			});
		} else {
			strengthsContainer.innerHTML = `<div class="compat-card strength"><span class="compat-card-icon">${iconCheck}</span><span class="compat-card-text">Standard web page content layout.</span></div>`;
		}
	}

	const limitationsContainer = document.getElementById("compat-limitations");
	if (limitationsContainer) {
		limitationsContainer.innerHTML = "";
		const limitations = aiData.limitations || [];
		if (limitations.length > 0) {
			limitations.forEach(item => {
				const card = document.createElement("div");
				card.className = "compat-card limitation";
				card.innerHTML = `<span class="compat-card-icon">${iconWarn}</span><span class="compat-card-text">${escapeHtml(item)}</span>`;
				limitationsContainer.appendChild(card);
			});
		} else {
			limitationsContainer.innerHTML = `<div class="compat-card limitation info"><span class="compat-card-icon">${iconInfo}</span><span class="compat-card-text">No critical extraction limitations identified.</span></div>`;
		}
	}

	const recBox = document.getElementById("compat-recommendation");
	if (recBox) {
		recBox.textContent = aiData.recommendation || "Proceed with recommended scraping strategy for optimal data retrieval.";
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

	const iconInfo = `<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-info"><circle cx="12" cy="12" r="10"/><path d="M12 16v-4"/><path d="M12 8h.01"/></svg>`;

	if (!pipelineSteps || !Array.isArray(pipelineSteps) || pipelineSteps.length === 0) {
		const fallbackEl = document.createElement("div");
		fallbackEl.className = "pipeline-fallback";
		fallbackEl.innerHTML = `
			<span class="pipeline-fallback-icon">${iconInfo}</span>
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
					<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-check">
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

	const spinnerSvg = `<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-loader-2 spinner-icon"><path d="M21 12a9 9 0 1 1-6.219-8.56"/></svg>`;

	loadingMsg.innerHTML = `${spinnerSvg} <span>Analyzing &amp; Scraping...</span>`;
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
					loadingMsg.innerHTML = `${spinnerSvg} <span>AI Analysis complete. Scraping data...</span>`;
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
				noHeadings.innerHTML = `<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-heading"><path d="M6 12h12"/><path d="M6 20V4"/><path d="M18 20V4"/></svg> <span>No headings found on this page.</span>`;
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
				titleDiv.style.color = "var(--color-ai)";
				titleDiv.style.fontFamily = "var(--font-sans)";
				titleDiv.style.fontWeight = "700";
				
				tablesContainer.appendChild(titleDiv);
				tablesContainer.appendChild(wrapper);
			});
		} else {
			const noTables = document.createElement("p");
			noTables.className = "no-tables-msg";
			noTables.innerHTML = `<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-table"><path d="M12 3v18"/><path d="M3 12h18"/><rect width="18" height="18" x="3" y="3" rx="2"/></svg> <span>No tables found on this page.</span>`;
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
			noLinks.innerHTML = `<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-link"><path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/></svg> <span>No links found on this page.</span>`;
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
