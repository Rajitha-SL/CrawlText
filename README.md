---
title: RaSL CrawlText
emoji: 🕸️
colorFrom: blue
colorTo: indigo
sdk: gradio
sdk_version: 5.20.0
app_file: app.py
pinned: false
space_hardware: cpu-basic
---

# CrawlText: Full-Site Text Extraction & Web Crawler Engine

**CrawlText** is a high-performance, asynchronous web crawler and text extraction engine. Given a target domain's root URL, it recursively traverses all internal links, strips out non-content boilerplate (headers, footers, navigations, sidebars, cookie popups, scripts), and outputs clean, structured text.

## Key Features & Interfaces

- **Standalone SaaS Frontend (`frontend/`)**: Modern dark glassmorphic web app deployable directly to **Vercel** or **GitHub Pages**. Programmatically connects to Hugging Face Space backend `RASL143/RaSL-CrawlText` via `@gradio/client`.
- **FastAPI Async Backend**: High-performance REST & Server-Sent Events (SSE) streaming engine.
- **Gradio Interface (`app.py`)**: Native Gradio application pre-configured for Hugging Face Spaces.
- **Enterprise SSRF Protection**: Built-in security middleware blocking internal subnets, loopbacks, and cloud metadata.

## Quick Start & Local Execution

```bash
pip install -r requirements.txt

# Option A: Run FastAPI Server (http://localhost:8000)
python main.py

# Option B: Run Gradio App (http://127.0.0.1:7860)
python app.py
```

## Deploying Frontend on Vercel

1. Import your GitHub repository **`Rajitha-SL/CrawlText`** into [Vercel](https://vercel.com).
2. Vercel will automatically detect `vercel.json` and set the output directory to `frontend/`.
3. Click **Deploy**. Your standalone SaaS web application is live!
