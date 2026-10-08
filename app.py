import os
import tempfile
import asyncio
import gradio as gr
import httpx
from urllib.parse import urlparse

try:
    import spaces

    @spaces.GPU
    def _zero_gpu_startup():
        """Satisfies ZeroGPU container startup inspection without GPU queue bottlenecks."""
        return True
except Exception:
    pass

from crawler import crawl_site
from security import is_ssrf_safe
from extractor import format_crawl_results

async def handle_crawl(url: str, max_pages: int, delay: float):
    """Clean async crawl handler running on CPU without ZeroGPU queue bottlenecks."""
    if not url or not url.strip():
        return "⚠️ Please enter a valid URL.", "", None

    url = url.strip()
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    safe, reason = is_ssrf_safe(url)
    if not safe:
        return f"⚠️ URL rejected: {reason}", "", None

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

# Stateless bring-your-own-key processing. No application-level credential persistence.
# Note: infrastructure providers may have their own request logging/retention policies.
AI_ENDPOINTS = {
    "Google Gemini": "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
    "OpenAI": "https://api.openai.com/v1/chat/completions",
    "Anthropic Claude": "https://api.anthropic.com/v1/messages",
    "OpenRouter": "https://openrouter.ai/api/v1/chat/completions",
}
DEFAULT_MODELS = {
    "Google Gemini": "gemini-2.5-flash",
    "OpenAI": "gpt-4.1-mini",
    "Anthropic Claude": "claude-haiku-4-5",
    "OpenRouter": "openrouter/free",
}
TASKS = {
    "Clean and structure": "Clean formatting and organize the provided text without inventing facts. Preserve source meaning.",
    "Summarize": "Summarize the provided text faithfully, clearly distinguish uncertainty, and do not invent details.",
    "Convert to Markdown": "Reformat the provided text into readable Markdown without fabricating content.",
}
async def process_with_ai(provider: str, api_key: str, operation: str, text: str):
    if provider not in AI_ENDPOINTS or operation not in TASKS:
        return "Unsupported provider or operation."
    if not api_key or not api_key.strip():
        return "Enter your own API key for this operation. CrawlText does not provide paid AI credits."
    if not text or not text.strip():
        return "There is no extracted text to process."
    if len(text.encode("utf-8")) > 60000:
        return "Input is too large for a single AI request (60 KB limit). Select a smaller excerpt."
    prompt = TASKS[operation] + "\n\nSource text:\n" + text
    model = DEFAULT_MODELS[provider]
    headers = {"Content-Type": "application/json"}
    if provider == "Google Gemini":
        headers["x-goog-api-key"] = api_key
        endpoint = AI_ENDPOINTS[provider].format(model=model)
        payload = {"contents":[{"parts":[{"text":prompt}]}],"generationConfig":{"maxOutputTokens":1800}}
    elif provider == "Anthropic Claude":
        endpoint = AI_ENDPOINTS[provider]
        headers.update({"x-api-key":api_key,"anthropic-version":"2023-06-01"})
        payload = {"model":model,"max_tokens":1800,"messages":[{"role":"user","content":prompt}]}
    else:
        endpoint = AI_ENDPOINTS[provider]
        headers["Authorization"] = "Bearer " + api_key
        payload = {"model":model,"max_tokens":1800,"messages":[{"role":"user","content":prompt}]}
    try:
        async with httpx.AsyncClient(timeout=35, follow_redirects=False, trust_env=False) as client:
            response = await client.post(endpoint, headers=headers, json=payload)
        if response.status_code == 401 or response.status_code == 403:
            return "Provider rejected the API key or access permissions. Verify your provider account."
        if response.status_code == 429:
            return "Provider rate limit or quota reached. No automatic retry was made."
        if response.status_code >= 400:
            return f"Provider request failed (HTTP {response.status_code}). Verify model access and billing limits."
        data=response.json()
        if provider == "Google Gemini":
            parts=data.get("candidates",[{}])[0].get("content",{}).get("parts",[])
            result="".join(part.get("text","") for part in parts)
        elif provider == "Anthropic Claude":
            result="".join(part.get("text","") for part in data.get("content",[]))
        else:
            result=data.get("choices",[{}])[0].get("message",{}).get("content","")
        return result or "Provider returned no text."
    except (httpx.HTTPError, ValueError, KeyError, IndexError):
        return "The AI request could not be completed. Confirm provider availability and model access."

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
                maximum=100,
                value=25,
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

    ai_provider = gr.Dropdown(choices=list(AI_ENDPOINTS), value="Google Gemini", label="AI Provider (optional)")
    ai_key = gr.Textbox(label="Your API key — entered per request, not saved by CrawlText", type="password", placeholder="Paste your API key only when needed")
    ai_task = gr.Dropdown(choices=list(TASKS), value="Clean and structure", label="AI operation")
    ai_submit = gr.Button("Run AI with my own key")
    ai_output = gr.Textbox(label="AI processed text", lines=12, show_copy_button=True)
    gr.Markdown("CrawlText does not supply paid AI tokens. Provider charges, usage limits and data policies belong to your account. The key is sent through the hosting backend for this operation and is not deliberately written to application storage. Infrastructure/provider retention policies may apply.")
    async def run_ai_and_clear(provider, api_key, operation, source_text):
        result = await process_with_ai(provider, api_key, operation, source_text)
        return result, ""
    ai_submit.click(fn=run_ai_and_clear, inputs=[ai_provider, ai_key, ai_task, output_box], outputs=[ai_output, ai_key], api_name="process_with_ai", concurrency_limit=2)

    crawl_btn.click(
        fn=handle_crawl,
        inputs=[url_input, max_pages, delay],
        outputs=[status_box, output_box, download_btn],
        api_name="handle_crawl", concurrency_limit=2
    )

demo.queue()
demo.launch(ssr_mode=False)
