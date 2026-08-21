import asyncio
import re
from typing import Set, Dict, Any, Callable, Awaitable, Optional
from urllib.parse import urlparse, urljoin, parse_qs, urlencode, urlunparse
import httpx
from bs4 import BeautifulSoup

from security import is_ssrf_safe
from extractor import clean_and_extract_content, format_page_output

# Marketing & Tracking parameters to strip
TRACKING_PARAMS = {
    "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
    "fbclid", "gclid", "msclkid", "ref", "source", "mc_eid", "_ga"
}

# Non-HTML file extensions to ignore
NON_HTML_EXTENSIONS = (
    ".pdf", ".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg", ".ico",
    ".zip", ".tar", ".gz", ".rar", ".7z", ".mp3", ".mp4", ".avi", ".mov",
    ".docx", ".xlsx", ".pptx", ".csv", ".css", ".js", ".json", ".xml",
    ".exe", ".dmg", ".apk", ".iso", ".woff", ".woff2", ".ttf", ".eot"
)


def normalize_url(url: str, base_url: str) -> Optional[str]:
    """
    Normalizes a link relative to base_url.
    Strips anchor fragments (#) and tracking query parameters.
    Returns None if URL scheme is not http/https or contains binary extensions.
    """
    if not url or not isinstance(url, str):
        return None

    url = url.strip()

    # Skip mailto:, tel:, javascript:
    if url.startswith(("mailto:", "tel:", "javascript:", "data:", "blob:")):
        return None

    # Resolve relative URL
    absolute_url = urljoin(base_url, url)

    try:
        parsed = urlparse(absolute_url)
    except Exception:
        return None

    if parsed.scheme not in ("http", "https"):
        return None

    # Check file extension
    path_lower = parsed.path.lower()
    if any(path_lower.endswith(ext) for ext in NON_HTML_EXTENSIONS):
        return None

    # Clean query parameters
    query_params = parse_qs(parsed.query, keep_blank_values=False)
    filtered_params = {
        k: v for k, v in query_params.items()
        if k.lower() not in TRACKING_PARAMS
    }
    new_query = urlencode(filtered_params, doseq=True)

    # Strip trailing slash from path for consistency unless path is empty/root
    path = parsed.path
    if path != "/" and path.endswith("/"):
        path = path.rstrip("/")

    # Reconstruct normalized URL (dropping fragment)
    normalized = urlunparse((
        parsed.scheme,
        parsed.netloc.lower(),
        path or "/",
        parsed.params,
        new_query,
        ""  # Drop anchor fragment
    ))

    return normalized


def is_same_domain(target_url: str, root_domain: str) -> bool:
    """Checks if target_url belongs to the same domain/subdomain as root_domain."""
    try:
        target_netloc = urlparse(target_url).netloc.lower().split(":")[0]
        root_netloc = root_domain.lower().split(":")[0]
        
        # Direct match or exact subdomain match
        return target_netloc == root_netloc or target_netloc.endswith("." + root_netloc)
    except Exception:
        return False


class AsyncCrawler:
    """
    Production-grade async web crawler with politeness delay, SSRF defense,
    and real-time event callbacks.
    """

    def __init__(
        self,
        root_url: str,
        max_pages: int = 50,
        max_depth: int = 3,
        crawl_delay_ms: int = 300,
        concurrency: int = 3,
        event_callback: Optional[Callable[[str, Dict[str, Any]], Awaitable[None]]] = None,
        cancel_event: Optional[asyncio.Event] = None
    ):
        self.root_url = root_url
        self.max_pages = min(max(max_pages, 1), 100)
        self.max_depth = min(max(max_depth, 1), 5)
        self.crawl_delay = crawl_delay_ms / 1000.0
        self.concurrency = max(1, min(concurrency, 5))
        self.event_callback = event_callback
        self.cancel_event = cancel_event or asyncio.Event()

        parsed = urlparse(root_url)
        self.root_domain = parsed.netloc

        self.visited_urls: Set[str] = set()
        self.discovered_urls: Set[str] = set()
        self.skipped_count: int = 0
        self.crawled_count: int = 0

        self.semaphore = asyncio.Semaphore(self.concurrency)

    async def _emit(self, event_type: str, data: Dict[str, Any]):
        """Helper to send SSE callbacks to listener."""
        if self.event_callback:
            try:
                await self.event_callback(event_type, data)
            except Exception:
                pass

    async def fetch_page(self, client: httpx.AsyncClient, url: str) -> Optional[str]:
        """Fetches a page content safely checking SSRF and payload size limits."""
        # 1. SSRF Check
        is_safe, reason = is_ssrf_safe(url)
        if not is_safe:
            await self._emit("log", {"level": "WARN", "message": f"Skipped SSRF unsafe URL '{url}': {reason}"})
            self.skipped_count += 1
            return None

        # 2. Fetch headers first to verify Content-Type & Size
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) CrawlText-Bot/1.0",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
            }
            
            response = await client.get(url, headers=headers, follow_redirects=True, timeout=12.0)

            if response.status_code != 200:
                await self._emit("log", {"level": "WARN", "message": f"HTTP {response.status_code} for {url}"})
                self.skipped_count += 1
                return None

            content_type = response.headers.get("Content-Type", "").lower()
            if "text/html" not in content_type and "application/xhtml+xml" not in content_type:
                await self._emit("log", {"level": "INFO", "message": f"Skipped non-HTML Content-Type '{content_type}' at {url}"})
                self.skipped_count += 1
                return None

            # Skip large payloads > 5MB
            content_length = response.headers.get("Content-Length")
            if content_length and int(content_length) > 5 * 1024 * 1024:
                await self._emit("log", {"level": "WARN", "message": f"Skipped payload > 5MB at {url}"})
                self.skipped_count += 1
                return None

            return response.text

        except httpx.TimeoutException:
            await self._emit("log", {"level": "ERROR", "message": f"Timeout fetching {url}"})
            self.skipped_count += 1
            return None
        except Exception as e:
            await self._emit("log", {"level": "ERROR", "message": f"Error fetching {url}: {str(e)}"})
            self.skipped_count += 1
            return None

    def discover_links(self, html: str, current_url: str) -> Set[str]:
        """Parses HTML DOM for internal anchors."""
        internal_links = set()
        try:
            soup = BeautifulSoup(html, "lxml")
            for a_tag in soup.find_all("a", href=True):
                href = a_tag["href"]
                norm_link = normalize_url(href, current_url)
                if norm_link and is_same_domain(norm_link, self.root_domain):
                    internal_links.add(norm_link)
        except Exception:
            pass
        return internal_links

    async def crawl(self) -> Dict[str, Any]:
        """Executes the full crawl loop emitting real-time events."""
        normalized_root = normalize_url(self.root_url, self.root_url)
        if not normalized_root:
            raise ValueError(f"Invalid root URL provided: {self.root_url}")

        is_safe, reason = is_ssrf_safe(normalized_root)
        if not is_safe:
            raise ValueError(f"Root URL rejected by SSRF defense: {reason}")

        await self._emit("log", {"level": "INFO", "message": f"Starting crawl targeting root: {normalized_root}"})

        queue: list[tuple[str, int]] = [(normalized_root, 1)] # (url, depth)
        self.discovered_urls.add(normalized_root)
        extracted_pages = []
        combined_output_chunks = []

        async with httpx.AsyncClient(verify=True) as client:
            while queue and self.crawled_count < self.max_pages:
                if self.cancel_event.is_set():
                    await self._emit("log", {"level": "WARN", "message": "Crawl aborted by user request."})
                    break

                current_url, depth = queue.pop(0)

                if current_url in self.visited_urls:
                    continue

                self.visited_urls.add(current_url)
                self.crawled_count += 1

                await self._emit("log", {"level": "CRAWL", "message": f"[{self.crawled_count}/{self.max_pages}] Crawling (Depth {depth}): {current_url}"})
                await self._emit("progress", {
                    "crawled": self.crawled_count,
                    "discovered": len(self.discovered_urls),
                    "skipped": self.skipped_count,
                    "current_url": current_url
                })

                async with self.semaphore:
                    html_content = await self.fetch_page(client, current_url)

                if not html_content:
                    continue

                # Content Extraction
                extracted_data = clean_and_extract_content(html_content, current_url)
                formatted_chunk = format_page_output(
                    extracted_data["title"],
                    extracted_data["url"],
                    extracted_data["text"]
                )

                extracted_pages.append(extracted_data)
                combined_output_chunks.append(formatted_chunk)

                await self._emit("page_result", {
                    "title": extracted_data["title"],
                    "url": extracted_data["url"],
                    "word_count": extracted_data["word_count"],
                    "formatted_text": formatted_chunk
                })

                # Discover new links if depth < max_depth
                if depth < self.max_depth and self.crawled_count + len(queue) < self.max_pages * 2:
                    new_links = self.discover_links(html_content, current_url)
                    for link in new_links:
                        if link not in self.visited_urls and link not in self.discovered_urls:
                            self.discovered_urls.add(link)
                            queue.append((link, depth + 1))

                    await self._emit("progress", {
                        "crawled": self.crawled_count,
                        "discovered": len(self.discovered_urls),
                        "skipped": self.skipped_count,
                        "current_url": current_url
                    })

                # Polite delay between requests
                if self.crawl_delay > 0:
                    await asyncio.sleep(self.crawl_delay)

        final_summary = {
            "root_url": self.root_url,
            "target_domain": self.root_domain,
            "pages_crawled": self.crawled_count,
            "pages_discovered": len(self.discovered_urls),
            "pages_skipped": self.skipped_count,
            "extracted_pages": extracted_pages,
            "combined_output": "".join(combined_output_chunks)
        }

        await self._emit("done", final_summary)
        return final_summary
