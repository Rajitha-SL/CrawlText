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
const statusSpinner = document.getElementById("statusSpinner");

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

// Provide editable numeric fields alongside both sliders without changing the
// established controls or backend request contract.
function addTypedCrawlerSetting(slider, display, options) {
    const input = document.createElement("input");
    input.type = "number";
    input.min = String(options.min);
    input.max = String(options.max);
    input.step = String(options.step);
    input.value = slider.value;
    input.id = options.id;
    input.setAttribute("aria-label", options.label);
    input.title = options.label + " (" + options.min + "–" + options.max + ")";
    input.className = "w-20 sm:w-24 rounded-md border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-900 px-2 py-1 text-sm font-mono text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-500";
    input.style.cssText += "width:90px;max-width:100%;min-height:36px;";
    const row = document.createElement("div");
    row.className = "flex items-center gap-3 mt-2";
    const sliderParent = slider.parentElement;
    sliderParent.insertBefore(row, slider);
    slider.classList.add("flex-1");
    slider.classList.remove("w-full");
    row.appendChild(slider);
    row.appendChild(input);
    const normalize = (value) => {
        const parsed = Number(value);
        const safe = Number.isFinite(parsed) ? parsed : Number(slider.value);
        const bounded = Math.min(options.max, Math.max(options.min, safe));
        return options.decimals === 0 ? String(Math.round(bounded)) : bounded.toFixed(options.decimals);
    };
    slider.addEventListener("input", () => { input.value = slider.value; });
    input.addEventListener("input", () => {
        // Allow partial values such as "0." while the user is typing.
        // Only synchronize a complete, in-range value; clamp on change.
        const raw = input.value.trim();
        if(raw === "" || raw.endsWith(".") || !Number.isFinite(Number(raw))) return;
        const number = Number(raw);
        if(number < options.min || number > options.max) return;
        slider.value = normalize(raw);
        // Update the readout without overwriting the user's in-progress typing.
        display.innerText = options.decimals === 0
            ? slider.value + " pages"
            : Number(slider.value).toFixed(1) + " seconds";
        slider.setAttribute("aria-valuenow", slider.value);
    });
    input.addEventListener("change", () => {
        const val = normalize(input.value);
        input.value = val;
        slider.value = val;
        slider.dispatchEvent(new Event("input", { bubbles: true }));
    });
    return input;
}
addTypedCrawlerSetting(maxPagesInput, maxPagesDisplay, {
    id: "maxPagesTyped", label: "Type maximum pages", min: 1, max: 100, step: 1, decimals: 0
});
addTypedCrawlerSetting(crawlDelayInput, delayDisplay, {
    id: "crawlDelayTyped", label: "Type throttle delay in seconds", min: 0.1, max: 2, step: 0.1, decimals: 1
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
    let msg = err?.message || "Failed to communicate with Hugging Face Space backend.";

    const errStr = String(err).toLowerCase();

    if (errStr.includes("no readable pages extracted")) {
        title = "No Readable Pages Extracted";
        msg = String(err?.message || "").replace(/^❌\\s*/, "").replace(/\\*\\*/g, "").replace(/\\n/g, " ").trim();
    } else if (errStr.includes("403") || errStr.includes("forbidden") || errStr.includes("cloudflare")) {
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
    const maxPages = Math.min(100, Math.max(1,parseInt(maxPagesInput.value, 10) || 25));
    const delay = parseFloat(crawlDelayInput.value);

    // Immediate Execution State Feedback (Pulsing Disabled Button)
    btnStart.disabled = true;
    btnStart.classList.add("opacity-60", "cursor-not-allowed", "animate-pulse");
    btnIcon.className = "fa-solid fa-spinner animate-spin text-xs";
    btnText.innerText = "Crawling...";
    
    statusPanel.classList.remove("hidden");
    if(statusSpinner) statusSpinner.classList.remove("hidden");
    progressBar.style.width = "0%";
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
            statusMessage.innerText = "No readable pages extracted.";
            progressBar.style.width = "100%";
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
        if(statusSpinner) statusSpinner.classList.add("hidden");

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
        // Align the results toolbar below the fixed/sticky site header.
        // Scrolling directly to the panel without an offset hides export buttons.
        requestAnimationFrame(() => {
            const header = document.querySelector("header");
            const headerHeight = header ? header.getBoundingClientRect().height : 110;
            const panelTop = window.scrollY + resultsPanel.getBoundingClientRect().top;
            window.scrollTo({
                top: Math.max(0, panelTop - headerHeight - 16),
                behavior: "smooth"
            });
        });

    } catch (err) {
        console.error("Crawl error:", err);
        showGranularError(err, url);
    } finally {
        if(statusSpinner) statusSpinner.classList.add("hidden");
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
    if(statusSpinner) statusSpinner.classList.add("hidden");
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

// Optional BYOK AI flow. Keys are never written to localStorage/sessionStorage.
const aiProvider = document.getElementById("aiProvider");
const aiKey = document.getElementById("aiKey");
const aiOperation = document.getElementById("aiOperation");
const aiConfirm = document.getElementById("aiConfirm");
const btnRunAI = document.getElementById("btnRunAI");
const aiStatus = document.getElementById("aiStatus");
const aiResult = document.getElementById("aiResult");
const aiResultWrap = document.getElementById("aiResultWrap");
const aiDownload = document.getElementById("aiDownload");
function syncAiButton(){if(btnRunAI)btnRunAI.disabled=!(aiKey.value.trim()&&aiConfirm.checked&&currentFormattedText.trim());}
function clearAi(){if(aiKey)aiKey.value="";if(aiConfirm)aiConfirm.checked=false;if(aiResult)aiResult.value="";if(aiResultWrap)aiResultWrap.classList.add("hidden");if(aiStatus)aiStatus.textContent="";syncAiButton();}
if(aiKey&&btnRunAI){
 aiKey.addEventListener("input",syncAiButton);aiConfirm.addEventListener("change",syncAiButton);
 aiProvider.addEventListener("change",()=>{aiKey.value="";aiConfirm.checked=false;syncAiButton()});
 btnRunAI.addEventListener("click",async()=>{
  if(!currentFormattedText.trim()||!aiKey.value.trim()||!aiConfirm.checked)return;
  const text=currentFormattedText.slice(0,60000),key=aiKey.value;
  aiKey.value="";aiConfirm.checked=false;btnRunAI.disabled=true;aiResultWrap.classList.add("hidden");
  aiStatus.textContent="Contacting your selected provider. Your key is not saved by CrawlText.";
  try{
   const client=await getClient();
   const response=await client.predict("/process_with_ai",[aiProvider.value,key,aiOperation.value,text]);
   const result=(response.data||response)[0];
   if(typeof result!=="string")throw new Error("Unexpected provider response");
   aiResult.value=result;aiResultWrap.classList.remove("hidden");aiStatus.textContent="AI operation finished.";
  }catch(err){aiStatus.textContent="AI processing failed. Check your provider credentials, quota and backend availability.";}
  finally{syncAiButton();}
 });
 aiDownload.addEventListener("click",()=>{
  if(!aiResult.value)return;
  const blob=new Blob([aiResult.value],{type:"text/plain;charset=utf-8"});
  const url=URL.createObjectURL(blob);const a=document.createElement("a");a.href=url;a.download="CrawlText_AI_output.txt";a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
 });
 // Never cache the API key; clear it whenever the user begins a new crawl.
 crawlForm.addEventListener("submit",clearAi);
 if(btnReset)btnReset.addEventListener("click",clearAi);
 window.addEventListener("pagehide",()=>{aiKey.value="";});
}

/* Client-side Word (.docx) and PDF exports; no additional backend or paid tokens. */
async function createExport(format){
  if(!currentFormattedText.trim())return;
  const text=currentFormattedText;
  const name="CrawlText_"+currentTargetDomain.replace(/[^a-zA-Z0-9-]/g,"-");
  if(format==="docx"){
    if(!window.docx?.Document||!window.docx?.Packer)throw new Error("Word exporter unavailable");
    const paragraphs=text.split(/\r?\n/).map(line=>new window.docx.Paragraph({text:line||" ",spacing:{after:90}}));
    const doc=new window.docx.Document({sections:[{properties:{},children:paragraphs}]});
    const blob=await window.docx.Packer.toBlob(doc);
    saveExportBlob(blob,name+".docx");
  }else if(format==="pdf"){
    // Render each PDF sheet independently with canvas to avoid html2pdf's
    // off-page positioning, right-edge clipping and mid-line page slicing.
    // Browser canvas fonts preserve Japanese and other multilingual scripts.
    if(!window.jspdf?.jsPDF) throw new Error("PDF exporter unavailable");
    const pdf = new window.jspdf.jsPDF({unit:"mm",format:"a4",compress:true});
    const sheetWidth = 210, sheetHeight = 297, margin = 15;
    const canvasWidth = 1200;
    const pxPerMm = canvasWidth / sheetWidth;
    const canvasHeight = Math.round(sheetHeight * pxPerMm);
    const left = Math.round(margin * pxPerMm);
    const right = canvasWidth - left;
    const top = Math.round(19 * pxPerMm);
    const bottom = canvasHeight - Math.round(16 * pxPerMm);
    const fontSize = 20, lineHeight = 32;
    const sourceCount = (text.match(/^PAGE:\s/gm) || []).length;
    let canvas, ctx, y, pageNumber = 0;
    function newSheet() {
        canvas = document.createElement("canvas");
        canvas.width = canvasWidth;
        canvas.height = canvasHeight;
        ctx = canvas.getContext("2d");
        ctx.fillStyle = "#ffffff";
        ctx.fillRect(0,0,canvasWidth,canvasHeight);
        ctx.textBaseline = "top";
        ctx.fillStyle = "#111827";
        ctx.font = "bold 27px Arial, 'Yu Gothic', Meiryo, sans-serif";
        ctx.fillText("CrawlText — Extracted Web Pages",left,top);
        ctx.font = "17px Arial, 'Yu Gothic', Meiryo, sans-serif";
        ctx.fillStyle = "#475569";
        ctx.fillText("Source web pages: " + sourceCount + " | Target: " + currentTargetDomain,left,top+38);
        ctx.font = fontSize + "px Arial, 'Yu Gothic', Meiryo, sans-serif";
        ctx.fillStyle = "#111827";
        y = top + 96;
        pageNumber++;
    }
    function finishSheet() {
        ctx.fillStyle = "#64748b";
        ctx.font = "16px Arial, sans-serif";
        ctx.textAlign = "right";
        ctx.fillText("PDF sheet " + pageNumber,right,canvasHeight-42);
        ctx.textAlign = "left";
        pdf.addImage(canvas.toDataURL("image/png"),"PNG",0,0,sheetWidth,sheetHeight,undefined,"FAST");
    }
    function drawLine(line) {
        // Do not allocate a fresh sheet for a blank separator at a page boundary.
        if (y + lineHeight > bottom) {
            if (!line) return;
            finishSheet();
            pdf.addPage();
            newSheet();
        }
        if (line) ctx.fillText(line,left,y);
        y += lineHeight;
    }
    function wrapLine(original) {
        if (!original.trim()) { drawLine(""); return; }
        let line = "";
        // A space-aware version of the previously working character wrapper.
        // Each token is measured before insertion; only oversized tokens
        // (long URLs or scripts without spaces) are split by code point.
        const tokens = original.match(/\S+\s*|\s+/g) || [original];
        for (const token of tokens) {
            if (ctx.measureText(line + token).width <= right - left) {
                line += token;
                continue;
            }
            if (line.trim()) {
                drawLine(line.trimEnd());
                line = "";
            }
            const word = token.trimStart();
            if (ctx.measureText(word).width <= right - left) {
                line = word;
                continue;
            }
            for (const character of Array.from(word)) {
                if (line && ctx.measureText(line + character).width > right - left) {
                    drawLine(line.trimEnd());
                    line = "";
                }
                line += character;
            }
        }
        if (line.trim()) drawLine(line.trimEnd());
    }
    // Do not render the trailing blank lines from the extracted text.
    for (const original of text.trimEnd().split(/\r?\n/)) {
        wrapLine(original);
    }
    finishSheet();
    pdf.save(name+".pdf");
  }
}
function saveExportBlob(blob,name){const url=URL.createObjectURL(blob);const a=document.createElement("a");a.href=url;a.download=name;document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),3000)}
for(const fmt of ["docx","pdf"]){
  const btn=document.getElementById(fmt==="docx"?"btnWord":"btnPdf");
  if(btn)btn.addEventListener("click",async()=>{if(!currentFormattedText.trim())return;btn.disabled=true;const label=btn.textContent;btn.textContent="Preparing…";try{await createExport(fmt)}catch(err){console.error("CrawlText "+fmt.toUpperCase()+" export error:",err);showGranularError(new Error(fmt.toUpperCase()+" export failed: "+(err?.message||"Unknown error")+". Try again or use TXT."),urlInput.value)}finally{btn.disabled=false;btn.textContent=label}});
}
