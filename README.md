---
title: RaSL CrawlText
emoji: 🕸️
colorFrom: blue
colorTo: indigo
sdk: gradio
sdk_version: 5.20.0
app_file: app.py
pinned: false
---

# CrawlText: Full-Site Text Extraction & Web Crawler Engine

**CrawlText** is a high-performance, asynchronous web crawler and text extraction engine. Given a target domain's root URL, it recursively traverses all internal links, strips out non-content boilerplate (headers, footers, navigations, sidebars, cookie popups, scripts), and outputs clean, structured text.

## Key Features & Interfaces

- **FastAPI Async Backend**: High-performance REST & Server-Sent Events (SSE) streaming engine.
- **Tailwind CSS Web Dashboard**: Single-page dark mode interface serving interactive real-time logs and text preview.
- **Gradio Interface**: Native Gradio application (`app.py`) pre-configured for Hugging Face Spaces.
- **Enterprise SSRF Protection**: Built-in security middleware blocking internal subnets, loopbacks, and cloud metadata.

## Quick Start

```bash
pip install -r requirements.txt

# Option A: Run FastAPI Server (http://localhost:8000)
python main.py

# Option B: Run Gradio App (http://127.0.0.1:7860)
python app.py
```
