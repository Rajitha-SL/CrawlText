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

let timerInterval = null;
let startTime = 0;
let gradioClient = null;
let currentFormattedText = "";

// Advanced Controls Drawer Toggle
toggleAdvBtn.addEventListener("click", () => {
    advDrawer.classList.toggle("hidden");
    advChevron.classList.toggle("rotate-180");
});

// Slider Input Value Feedback
maxPagesInput.addEventListener("input", (e) => {
    maxPagesDisplay.innerText = `${e.target.value} pages`;
});

crawlDelayInput.addEventListener("input", (e) => {
    delayDisplay.innerText = `${parseFloat(e.target.value).toFixed(1)} seconds`;
});

// Helper: Normalize URL format
function normalizeInputUrl(rawUrl) {
    let url = rawUrl.trim();
    if (!url) return "";
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

// Helper: Show Error Alert
function showError(title, msg) {
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

// Main Execution Handler
crawlForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    dismissError();

    const rawUrl = urlInput.value;
    const url = normalizeInputUrl(rawUrl);

    if (!url) {
        showError("Invalid URL", "Please enter a valid target URL.");
        return;
    }

    urlInput.value = url;
    const maxPages = parseInt(maxPagesInput.value, 10);
    const delay = parseFloat(crawlDelayInput.value);

    // Update UI State for Active Crawl
    btnStart.disabled = true;
    btnIcon.className = "fa-solid fa-spinner animate-spin text-xs";
    btnText.innerText = "Extracting...";
    
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
        const fileData = data[2] || null;

        if (!formattedText || formattedText.startsWith("❌") || formattedText.startsWith("⚠️")) {
            showError("Crawl Execution Alert", summaryMarkdown || formattedText || "No content extracted.");
            return;
        }

        currentFormattedText = formattedText;
        outputTextarea.value = formattedText;

        // Extract Metric Info
        let domainName = "-";
        try {
            domainName = new URL(url).hostname;
        } catch (err) {
            domainName = url;
        }

        // Count extracted pages by dividing header separators
        const pageMatches = (formattedText.match(/PAGE:/g) || []).length;
        const sizeKB = (new Blob([formattedText]).size / 1024).toFixed(1);

        statDomain.innerText = domainName;
        statPages.innerText = pageMatches || 1;
        statChars.innerText = `${sizeKB} KB`;
        statStatus.innerText = "Completed";

        progressBar.style.width = "100%";
        statusMessage.innerText = "Extraction complete!";

        // Reveal Metrics & Output Panels
        metricsGrid.classList.remove("hidden");
        resultsPanel.classList.remove("hidden");
        resultsPanel.scrollIntoView({ behavior: "smooth" });

    } catch (err) {
        console.error("Crawl error:", err);
        showError("Extraction Failed", err.message || "Failed to communicate with Hugging Face Space backend.");
    } finally {
        stopTimer();
        btnStart.disabled = false;
        btnIcon.className = "fa-solid fa-bolt text-xs";
        btnText.innerText = "Start Crawl";
    }
});

// Copy to Clipboard Action
btnCopy.addEventListener("click", () => {
    if (!currentFormattedText) return;
    navigator.clipboard.writeText(currentFormattedText).then(() => {
        copyBtnText.innerText = "Copied!";
        btnCopy.classList.remove("bg-slate-800");
        btnCopy.classList.add("bg-emerald-600/30", "border-emerald-500/50", "text-emerald-300");

        setTimeout(() => {
            copyBtnText.innerText = "Copy Raw Text";
            btnCopy.classList.add("bg-slate-800");
            btnCopy.classList.remove("bg-emerald-600/30", "border-emerald-500/50", "text-emerald-300");
        }, 2000);
    });
});

// Download .TXT File Action
btnDownload.addEventListener("click", () => {
    if (!currentFormattedText) return;

    const domainName = statDomain.innerText !== "-" ? statDomain.innerText.replace(/\./g, "_") : "extracted";
    const fileName = `crawltext_${domainName}_${Date.now()}.txt`;

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
