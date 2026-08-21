import { Client } from "https://cdn.jsdelivr.net/npm/@gradio/client/dist/index.min.js";

// DOM Element References
const crawlForm = document.getElementById("crawlForm");
const urlInput = document.getElementById("urlInput");
const maxPagesInput = document.getElementById("maxPages");
const maxPagesDisplay = document.getElementById("maxPagesDisplay");
const crawlDelayInput = document.getElementById("crawlDelay");
const delayDisplay = document.getElementById("delayDisplay");

const toggleAdvBtn = document.getElementById("toggleAdvBtn");
const advDrawer = document.getElementById("advDrawer");
const advChevron = document.getElementById("advChevron");

const btnStart = document.getElementById("btnStart");
const btnIcon = document.getElementById("btnIcon");
const btnText = document.getElementById("btnText");

const statusPanel = document.getElementById("statusPanel");
const statusMessage = document.getElementById("statusMessage");
const statusTimer = document.getElementById("statusTimer");
const progressBar = document.getElementById("progressBar");

const errorAlert = document.getElementById("errorAlert");
const errorTitle = document.getElementById("errorTitle");
const errorMessage = document.getElementById("errorMessage");

const metricsGrid = document.getElementById("metricsGrid");
const statDomain = document.getElementById("statDomain");
const statPages = document.getElementById("statPages");
const statChars = document.getElementById("statChars");
const statStatus = document.getElementById("statStatus");

const resultsPanel = document.getElementById("resultsPanel");
const outputTextarea = document.getElementById("outputTextarea");
const btnCopy = document.getElementById("btnCopy");
const copyBtnText = document.getElementById("copyBtnText");
const btnDownload = document.getElementById("btnDownload");
const btnReset = document.getElementById("btnReset");

const themeToggleBtn = document.getElementById("themeToggleBtn");
const themeToggleIcon = document.getElementById("themeToggleIcon");

let timerInterval = null;
let startTime = 0;
let gradioClient = null;
let currentFormattedText = "";
let currentTargetDomain = "extracted";

// Theme Toggle Logic with Professional Clean SVG Icons
const SUN_SVG = `<svg id="themeToggleIcon" class="w-4 h-4 text-amber-500 dark:text-amber-400 group-hover:rotate-45 transition-transform duration-300" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="5"></circle><line x1="12" y1="1" x2="12" y2="3"></line><line x1="12" y1="21" x2="12" y2="23"></line><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"></line><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"></line><line x1="1" y1="12" x2="3" y2="12"></line><line x1="21" y1="12" x2="23" y2="12"></line><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"></line><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"></line></svg>`;
const MOON_SVG = `<svg id="themeToggleIcon" class="w-4 h-4 text-indigo-500 dark:text-indigo-400 group-hover:rotate-12 transition-transform duration-300" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"></path></svg>`;

function updateThemeIcon(isLight) {
    if (!themeToggleBtn) return;
    if (isLight) {
        themeToggleBtn.innerHTML = MOON_SVG;
        themeToggleBtn.title = "Switch to Dark Mode";
    } else {
        themeToggleBtn.innerHTML = SUN_SVG;
        themeToggleBtn.title = "Switch to Light Mode";
    }
}

// Initial Theme Check (localStorage with system preference fallback)
const getInitialTheme = () => {
    const saved = localStorage.getItem("theme");
    if (saved) return saved;
    return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
};

const currentTheme = getInitialTheme();
if (currentTheme === "light") {
    document.documentElement.classList.remove("dark");
    document.documentElement.classList.add("light");
    updateThemeIcon(true);
} else {
    document.documentElement.classList.add("dark");
    document.documentElement.classList.remove("light");
    updateThemeIcon(false);
}

if (themeToggleBtn) {
    themeToggleBtn.addEventListener("click", () => {
        const isDark = document.documentElement.classList.contains("dark");
        if (isDark) {
            document.documentElement.classList.remove("dark");
            document.documentElement.classList.add("light");
            localStorage.setItem("theme", "light");
            updateThemeIcon(true);
        } else {
            document.documentElement.classList.remove("light");
            document.documentElement.classList.add("dark");
            localStorage.setItem("theme", "dark");
            updateThemeIcon(false);
        }
    });
}

// Advanced Controls Drawer Toggle
toggleAdvBtn.addEventListener("click", () => {
    advDrawer.classList.toggle("hidden");
    advChevron.classList.toggle("rotate-180");
});

// Slider Input Value & ARIA Feedback
maxPagesInput.addEventListener("input", (e) => {
    const val = e.target.value;
    maxPagesDisplay.innerText = `${val} pages`;
    maxPagesInput.setAttribute("aria-valuenow", val);
});

crawlDelayInput.addEventListener("input", (e) => {
    const val = parseFloat(e.target.value).toFixed(1);
    delayDisplay.innerText = `${val} seconds`;
    crawlDelayInput.setAttribute("aria-valuenow", val);
});

// Aggressive Input Sanitization
function sanitizeUrl(rawUrl) {
    if (!rawUrl || typeof rawUrl !== "string") return "";

    // 1. Strip zero-width & invisible whitespace characters
    let url = rawUrl.trim().replace(/[​-‍﻿]/g, "");

    // 2. Strip trailing slashes
    url = url.replace(/\/+$/, "");

    // 3. Auto-prefix https:// if protocol omitted
    if (!url.startsWith("http://") && !url.startsWith("https://")) {
        url = "https://" + url;
    }
    return url;
}

// Helper: Start Timer
function startTimer() {
    startTime = Date.now();
    statusTimer.innerText = "00:00";
    clearInterval(timerInterval);
    timerInterval = setInterval(() => {
        const elapsedSec = Math.floor((Date.now() - startTime) / 1000);
        const m = String(Math.floor(elapsedSec / 60)).padStart(2, "0");
        const s = String(elapsedSec % 60).padStart(2, "0");
        statusTimer.innerText = `${m}:${s}`;
    }, 1000);
}

// Helper: Stop Timer
function stopTimer() {
    clearInterval(timerInterval);
}

// Granular Error Handler
function showGranularError(err, url) {
    let title = "Extraction Failed";
    let msg = err.message || "Failed to communicate with Hugging Face Space backend.";

    const errStr = String(err).toLowerCase();

    if (errStr.includes("403") || errStr.includes("forbidden") || errStr.includes("cloudflare")) {
        title = "🛡️ Target Security Blocked";
        msg = `The target site (${url}) blocked automated extraction (Cloudflare / WAF protection).`;
    } else if (errStr.includes("404") || errStr.includes("not found")) {
        title = "🔍 Page Not Found (404)";
        msg = `The target URL (${url}) returned a 404 Not Found error.`;
    } else if (errStr.includes("ssrf") || errStr.includes("private") || errStr.includes("loopback")) {
        title = "🛡️ SSRF Security Blocked";
        msg = "Internal subnets, localhost, and cloud metadata IPs are blocked for security.";
    } else if (errStr.includes("timeout") || errStr.includes("timed out")) {
        title = "⏱️ Connection Timed Out";
        msg = "The target server took too long to respond.";
    }

    errorTitle.innerText = title;
    errorMessage.innerText = msg;
    errorAlert.classList.remove("hidden");
    errorAlert.scrollIntoView({ behavior: "smooth", block: "center" });
}

// Helper: Dismiss Error Alert
window.dismissError = function() {
    errorAlert.classList.add("hidden");
};

// Connect to Hugging Face Client
async function getClient() {
    if (!gradioClient) {
        statusMessage.innerText = "Connecting to Hugging Face Space (RASL143/RaSL-CrawlText)...";
        gradioClient = await Client.connect("RASL143/RaSL-CrawlText");
    }
    return gradioClient;
}

// Restore Transient Session Cache on Page Load
function restoreSessionCache() {
    try {
        const cached = sessionStorage.getItem("crawltext_session");
        if (cached) {
            const data = JSON.parse(cached);
            if (data.formattedText && data.formattedText.trim()) {
                currentFormattedText = data.formattedText;
                currentTargetDomain = data.domain || "extracted";
                urlInput.value = data.url || "";
                outputTextarea.value = data.formattedText;

                statDomain.innerText = data.domain || "-";
                statPages.innerText = data.pages || 1;
                statChars.innerText = data.size || "0 KB";
                statStatus.innerText = "Restored";

                metricsGrid.classList.remove("hidden");
                resultsPanel.classList.remove("hidden");
            }
        }
    } catch (e) {
        console.warn("Could not restore session cache:", e);
    }
}

restoreSessionCache();

// Main Execution Handler
crawlForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    dismissError();

    const url = sanitizeUrl(urlInput.value);

    if (!url) {
        showGranularError(new Error("Please enter a valid target URL."), "");
        return;
    }

    urlInput.value = url;
    const maxPages = parseInt(maxPagesInput.value, 10);
    const delay = parseFloat(crawlDelayInput.value);

    // Immediate Execution State Feedback (Pulsing Disabled Button)
    btnStart.disabled = true;
    btnStart.classList.add("opacity-60", "cursor-not-allowed", "animate-pulse");
    btnIcon.className = "fa-solid fa-spinner animate-spin text-xs";
    btnText.innerText = "Crawling...";
    
    statusPanel.classList.remove("hidden");
    metricsGrid.classList.add("hidden");
    resultsPanel.classList.add("hidden");
    startTimer();

    try {
        statusMessage.innerText = "Connecting to Hugging Face Space backend...";
        progressBar.style.width = "20%";

        const client = await getClient();

        statusMessage.innerText = `Crawling domain (Max ${maxPages} pages, ${delay}s throttle)...`;
        progressBar.style.width = "50%";

        // Call Gradio endpoint
        let response;
        try {
            response = await client.predict("/handle_crawl", [url, maxPages, delay]);
        } catch (err) {
            response = await client.predict(0, [url, maxPages, delay]);
        }

        progressBar.style.width = "90%";
        statusMessage.innerText = "Formatting extracted body copy...";

        // Destructure response tuple [summaryMarkdown, formattedText, fileData]
        const data = response.data || response;
        const summaryMarkdown = data[0] || "";
        const formattedText = data[1] || "";

        if (!formattedText || formattedText.startsWith("❌") || formattedText.startsWith("⚠️")) {
            showGranularError(new Error(summaryMarkdown || formattedText || "No content extracted."), url);
            return;
        }

        currentFormattedText = formattedText;
        outputTextarea.value = formattedText;

        // Extract Metric Info
        let domainName = "extracted";
        try {
            domainName = new URL(url).hostname;
        } catch (err) {
            domainName = url;
        }
        currentTargetDomain = domainName;

        const pageMatches = (formattedText.match(/PAGE:/g) || []).length;
        const sizeKB = (new Blob([formattedText]).size / 1024).toFixed(1) + " KB";

        statDomain.innerText = domainName;
        statPages.innerText = pageMatches || 1;
        statChars.innerText = sizeKB;
        statStatus.innerText = "Completed";

        progressBar.style.width = "100%";
        statusMessage.innerText = "Extraction complete!";

        // Save Transient State to sessionStorage
        try {
            sessionStorage.setItem("crawltext_session", JSON.stringify({
                url: url,
                domain: domainName,
                pages: pageMatches || 1,
                size: sizeKB,
                formattedText: formattedText
            }));
        } catch (e) {
            console.warn("Failed to write to sessionStorage:", e);
        }

        // Reveal Metrics & Output Panels
        metricsGrid.classList.remove("hidden");
        resultsPanel.classList.remove("hidden");
        resultsPanel.scrollIntoView({ behavior: "smooth" });

    } catch (err) {
        console.error("Crawl error:", err);
        showGranularError(err, url);
    } finally {
        stopTimer();
        btnStart.disabled = false;
        btnStart.classList.remove("opacity-60", "cursor-not-allowed", "animate-pulse");
        btnIcon.className = "fa-solid fa-bolt text-xs";
        btnText.innerText = "Start Crawl";
    }
});

// Post-Crawl Reset / New Crawl Action
btnReset.addEventListener("click", () => {
    currentFormattedText = "";
    currentTargetDomain = "extracted";
    outputTextarea.value = "";
    urlInput.value = "";

    sessionStorage.removeItem("crawltext_session");

    metricsGrid.classList.add("hidden");
    resultsPanel.classList.add("hidden");
    statusPanel.classList.add("hidden");
    dismissError();

    urlInput.focus();
});

// Copy to Clipboard Action
btnCopy.addEventListener("click", () => {
    if (!currentFormattedText) return;
    navigator.clipboard.writeText(currentFormattedText).then(() => {
        copyBtnText.innerText = "Copied!";
        btnCopy.classList.add("bg-emerald-600/30", "border-emerald-500/50", "text-emerald-300");

        setTimeout(() => {
            copyBtnText.innerText = "Copy Raw Text";
            btnCopy.classList.remove("bg-emerald-600/30", "border-emerald-500/50", "text-emerald-300");
        }, 2000);
    });
});

// Dynamic File Naming Download Action (e.g. CrawlText_example-com.txt)
btnDownload.addEventListener("click", () => {
    if (!currentFormattedText) return;

    const safeDomain = currentTargetDomain.replace(/[^a-zA-Z0-9-]/g, "-");
    const fileName = `CrawlText_${safeDomain}.txt`;

    const blob = new Blob([currentFormattedText], { type: "text/plain;charset=utf-8" });
    const blobUrl = URL.createObjectURL(blob);

    const a = document.createElement("a");
    a.href = blobUrl;
    a.download = fileName;
    document.body.appendChild(a);
    a.click();

    document.body.removeChild(a);
    URL.revokeObjectURL(blobUrl);
});
