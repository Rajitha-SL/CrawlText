import asyncio
import os
import tempfile
import time
import gradio as gr

from security import is_ssrf_safe
from crawler import AsyncCrawler

async def run_crawl_gradio(url: str, max_pages: int, crawl_delay_s: float):
    """
    Async handler function for Gradio interface.
    Executes crawler, formats results, and creates a temporary downloadable .txt file.
    """
    if not url or not isinstance(url, str) or not (url.startswith("http://") or url.startswith("https://")):
        return (
            "### ❌ Error\nPlease enter a valid URL starting with `http://` or `https://`.",
            "",
            None
        )

    # SSRF Protection Check
    is_safe, error_reason = is_ssrf_safe(url)
    if not is_safe:
        return (
            f"### 🛡️ SSRF Security Blocked\n**Reason:** {error_reason}",
            "",
            None
        )

    start_time = time.time()
    crawl_delay_ms = int(crawl_delay_s * 1000)

    crawler = AsyncCrawler(
        root_url=url,
        max_pages=int(max_pages),
        max_depth=4,
        crawl_delay_ms=crawl_delay_ms
    )

    try:
        results = await crawler.crawl()
    except Exception as e:
        return (
            f"### ❌ Execution Error\n`{str(e)}`",
            "",
            None
        )

    elapsed_s = round(time.time() - start_time, 2)
    combined_output = results.get("combined_output", "")
    pages_crawled = results.get("pages_crawled", 0)
    pages_discovered = results.get("pages_discovered", 0)
    pages_skipped = results.get("pages_skipped", 0)
    domain = results.get("target_domain", "")

    summary_md = f"""### 📊 Crawl Job Completed Successfully
- **Target Domain:** `{domain}`
- **Pages Crawled:** `{pages_crawled}` / `{max_pages}`
- **Discovered Links:** `{pages_discovered}`
- **Skipped / Failed:** `{pages_skipped}`
- **Elapsed Time:** `{elapsed_s}s`
"""

    if not combined_output.strip():
        combined_output = "[No readable text content was extracted from this domain]"

    # Create temporary file for download component
    temp_dir = tempfile.gettempdir()
    file_name = f"crawltext_{domain.replace('.', '_')}_{int(time.time())}.txt"
    file_path = os.path.join(temp_dir, file_name)

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(combined_output)

    return summary_md, combined_output, file_path


# Build Gradio Blocks UI
with gr.Blocks(
    title="CrawlText - Web Text Extraction Engine",
    theme=gr.themes.Soft(primary_hue="blue", secondary_hue="cyan")
) as demo:
    gr.Markdown(
        """
        # 🕷️ CrawlText - Full-Site Text Extraction & Crawler Engine
        Extract clean main body text from entire web domains, stripping headers, footers, sidebars, scripts, and cookie banners.
        """
    )

    with gr.Row():
        with gr.Column(scale=2):
            url_input = gr.Textbox(
                label="Target Root URL",
                placeholder="https://example.com",
                lines=1
            )
            with gr.Row():
                max_pages_slider = gr.Slider(
                    minimum=5,
                    maximum=100,
                    value=25,
                    step=5,
                    label="Max Pages Limit"
                )
                crawl_delay_slider = gr.Slider(
                    minimum=0.1,
                    maximum=1.0,
                    value=0.3,
                    step=0.05,
                    label="Crawl Throttle Delay (Seconds)"
                )
            btn_start = gr.Button("🚀 Start Crawling", variant="primary")

        with gr.Column(scale=1):
            status_output = gr.Markdown("### ℹ️ Status\nEnter a target URL and click **Start Crawling**.")
            file_download = gr.File(label="📥 Download Extracted Text (.txt)")

    output_text = gr.Textbox(
        label="Extracted Formatted Content",
        lines=18,
        max_lines=35,
        interactive=False,
        show_copy_button=True
    )

    btn_start.click(
        fn=run_crawl_gradio,
        inputs=[url_input, max_pages_slider, crawl_delay_slider],
        outputs=[status_output, output_text, file_download]
    )

if __name__ == "__main__":
    demo.queue().launch()
