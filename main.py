import asyncio
import datetime
import json
from typing import Dict, Any, Optional
from fastapi import FastAPI, Query, HTTPException, BackgroundTasks, Request
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse

from security import is_ssrf_safe
from crawler import AsyncCrawler

app = FastAPI(
    title="CrawlText - Web Text Extraction & Crawler Tool",
    description="Extracts main body text from entire domains, stripping navigation, footers, headers, and popups.",
    version="1.0.0"
)

# Enable CORS for public consumption
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static directory for frontend UI
app.mount("/static", StaticFiles(directory="static"), name="static")

# Active crawl session cancellation events indexed by session ID or current runner
active_cancellation_events: Dict[str, asyncio.Event] = {}


@app.get("/", response_class=FileResponse)
async def serve_index():
    """Serves the main single-page application UI."""
    return FileResponse("static/index.html")


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "app": "CrawlText", "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()}


@app.get("/api/crawl/stream")
async def stream_crawl(
    request: Request,
    url: str = Query(..., description="Target root URL to crawl"),
    max_pages: int = Query(50, ge=1, le=100, description="Max pages limit"),
    max_depth: int = Query(3, ge=1, le=5, description="Max crawling depth"),
    crawl_delay: int = Query(300, ge=0, le=2000, description="Politeness delay in milliseconds")
):
    """
    Server-Sent Events (SSE) endpoint to stream real-time crawl logs, progress,
    and page extraction output.
    """
    # 1. SSRF Safety Check
    is_safe, error_reason = is_ssrf_safe(url)
    if not is_safe:
        async def ssrf_error_generator():
            yield {
                "event": "error",
                "data": json.dumps({"message": f"Security Error: {error_reason}"})
            }
        return EventSourceResponse(ssrf_error_generator())

    # Create session cancel event
    session_id = f"session_{datetime.datetime.now().timestamp()}"
    cancel_event = asyncio.Event()
    active_cancellation_events[session_id] = cancel_event

    async def event_generator():
        queue = asyncio.Queue()

        async def callback(event_type: str, data: Dict[str, Any]):
            await queue.put({"event": event_type, "data": json.dumps(data)})

        # Header summary header block
        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")
        init_log = {
            "event": "log",
            "data": json.dumps({
                "level": "INFO",
                "message": f"Initialized CrawlText Job | Target: {url} | Time: {now_str}"
            })
        }
        yield init_log

        crawler = AsyncCrawler(
            root_url=url,
            max_pages=max_pages,
            max_depth=max_depth,
            crawl_delay_ms=crawl_delay,
            event_callback=callback,
            cancel_event=cancel_event
        )

        # Run crawler task concurrently with SSE reading loop
        crawl_task = asyncio.create_task(crawler.crawl())

        try:
            while not crawl_task.done() or not queue.empty():
                if await request.is_disconnected():
                    cancel_event.set()
                    break

                try:
                    # Wait for next event with short timeout to check task state
                    msg = await asyncio.wait_for(queue.get(), timeout=0.2)
                    yield msg
                    queue.task_done()
                except asyncio.TimeoutError:
                    continue
        except Exception as e:
            yield {
                "event": "error",
                "data": json.dumps({"message": f"Internal Crawler Error: {str(e)}"})
            }
        finally:
            active_cancellation_events.pop(session_id, None)

    return EventSourceResponse(event_generator())


@app.post("/api/crawl/cancel")
async def cancel_all_crawls():
    """Cancels all currently active crawl jobs."""
    count = len(active_cancellation_events)
    for session_id, cancel_evt in active_cancellation_events.items():
        cancel_evt.set()
    return {"status": "ok", "cancelled_jobs": count}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
