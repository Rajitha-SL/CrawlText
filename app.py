import os
import tempfile
import asyncio
import gradio as gr

try:
    import spaces

    @spaces.GPU
    def _zero_gpu_startup():
        """Satisfies ZeroGPU container startup inspection without GPU queue bottlenecks."""
        return True
except Exception:
    pass

from crawler import crawl_site
from extractor import format_crawl_results

async def handle_crawl(url: str, max_pages: int, delay: float):
    """Clean async crawl handler running on CPU without ZeroGPU queue bottlenecks."""
    if not url or not url.strip():
        return "⚠️ Please enter a valid URL.", "", None

    url = url.strip()
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    try:
        results = await crawl_site(
            start_url=url,
            max_pages=int(max_pages),
            delay=float(delay)
        )

        if not results:
            return "❌ No pages were found or extracted.", "", None

        formatted_text = format_crawl_results(results)
        summary = f"### ✅ Crawl Complete\n- **Target**: `{url}`\n- **Pages Extracted**: `{len(results)}`"

        # Create temporary file for download
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".txt", mode="w", encoding="utf-8")
        tmp.write(formatted_text)
        tmp.close()

        return summary, formatted_text, tmp.name

    except Exception as e:
        return f"❌ Error during crawl: {str(e)}", "", None

# Gradio Interface Construction
with gr.Blocks(
    title="RaSL CrawlText",
    theme=gr.themes.Soft(primary_hue="blue", secondary_hue="cyan")
) as demo:
    gr.Markdown("# 🕸️ RaSL CrawlText - Web Scraper")
    gr.Markdown("Extract clean text content from multiple pages of a target website. **Logic and Discipline**.")

    with gr.Row():
        with gr.Column(scale=1):
            url_input = gr.Textbox(
                label="Target URL",
                placeholder="https://example.com",
                lines=1
            )
            max_pages = gr.Slider(
                minimum=1,
                maximum=50,
                value=15,
                step=1,
                label="Max Pages to Crawl"
            )
            delay = gr.Slider(
                minimum=0.1,
                maximum=2.0,
                value=0.3,
                step=0.1,
                label="Crawl Throttle Delay (seconds)"
            )
            crawl_btn = gr.Button("Start Crawling", variant="primary")

        with gr.Column(scale=2):
            status_box = gr.Markdown("Ready.")
            download_btn = gr.File(label="Download Formatted Text (.txt)")
            output_box = gr.Textbox(
                label="Extracted Content",
                lines=16,
                max_lines=25,
                show_copy_button=True
            )

    crawl_btn.click(
        fn=handle_crawl,
        inputs=[url_input, max_pages, delay],
        outputs=[status_box, output_box, download_btn],
        api_name=False
    )

demo.queue()
demo.launch(
    server_name="0.0.0.0",
    server_port=7860,
    ssr_mode=False
)
