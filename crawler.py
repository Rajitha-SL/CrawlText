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


def normalize_url(url: str, base_url: str, preserve_trailing_slash: bool = False) -> Optional[str]:
    """
    Normalizes a link relative to base_url.
    Strips anchor fragments (#) and tracking query parameters.
    Preserve trailing slashes for redirect targets to avoid canonicalization loops.
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
    if not preserve_trailing_slash and path != "/" and path.endswith("/"):
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
        self.concurrency = 1  # Deliberate bounded sequential crawling for public beta
        self.event_callback = event_callback
        self.cancel_event = cancel_event or asyncio.Event()

        parsed = urlparse(root_url)
        self.root_domain = parsed.netloc.removeprefix('www.')

        self.visited_urls: Set[str] = set()
        self.discovered_urls: Set[str] = set()
        self.skipped_count: int = 0
        self.crawled_count: int = 0
        self.failure_reasons: list[str] = []
        self.resolved_urls: dict[str, str] = {}

        self.semaphore = asyncio.Semaphore(self.concurrency)

    async def _emit(self, event_type: str, data: Dict[str, Any]):
        """Helper to send SSE callbacks to listener."""
        if self.event_callback:
            try:
                await self.event_callback(event_type, data)
            except Exception:
                pass

    def _record_failure(self, message: str) -> None:
        """Collect concise, user-safe reasons without exposing response bodies or secrets."""
        if len(self.failure_reasons) < 5 and message not in self.failure_reasons:
            self.failure_reasons.append(message)

    async def fetch_page(self, client: httpx.AsyncClient, url: str, redirect_count: int = 0, redirect_seen: Optional[Set[str]] = None) -> Optional[str]:
        """Fetches a page content safely checking SSRF and payload size limits."""
        # Redirects are followed manually, validating each hop before any request.
        # Restrict destinations to the original domain and cap the chain.
        redirect_seen = redirect_seen or set()
        if url in redirect_seen or redirect_count > 5:
            self._record_failure("The website has a redirect loop or too many redirects.")
            self.skipped_count += 1
            return None
        redirect_seen.add(url)
        # 1. SSRF Check
        is_safe, reason = is_ssrf_safe(url)
        if not is_safe:
            await self._emit("log", {"level": "WARN", "message": f"Skipped SSRF unsafe URL '{url}': {reason}"})
            self._record_failure("The URL was blocked by the crawler's network safety checks.")
            self.skipped_count += 1
            return None

        # 2. Fetch headers first to verify Content-Type & Size
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) CrawlText-Bot/1.0",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
            }
            
            # HTTPX redirects stay disabled. Resolve and validate every Location manually.
            async with client.stream('GET', url, headers=headers, follow_redirects=False, timeout=12.0) as response:
                if response.is_redirect:
                    location = response.headers.get("location")
                    if not location:
                        self._record_failure(f"The website returned HTTP {response.status_code} without a redirect destination.")
                        self.skipped_count += 1
                        return None
                    target = normalize_url(location, url, preserve_trailing_slash=True)
                    if not target or not is_same_domain(target, self.root_domain):
                        self._record_failure("The website redirected outside the requested domain or to an unsupported URL.")
                        self.skipped_count += 1
                        return None
                    # Security and redirect-loop checks run again inside fetch_page.
                    await self._emit('log', {'level':'INFO', 'message':f'Following HTTP {response.status_code} redirect to {target}'})
                    html = await self.fetch_page(client, target, redirect_count + 1, redirect_seen)
                    if html is not None:
                        self.resolved_urls[url] = self.resolved_urls.get(target, target)
                    return html
                if response.status_code != 200:
                    code = response.status_code
                    if code in (401, 403):
                        self._record_failure(f"The website denied crawler access (HTTP {code}).")
                    elif code == 429:
                        self._record_failure("The website rate-limited the crawler (HTTP 429).")
                    else:
                        self._record_failure(f"The website returned HTTP {code}.")
                    await self._emit('log', {'level':'WARN', 'message':f'HTTP {response.status_code} for {url}'})
                    self.skipped_count += 1
                    return None
                content_type = response.headers.get('Content-Type', '').lower()
                if 'text/html' not in content_type and 'application/xhtml+xml' not in content_type:
                    self._record_failure("The response was not an HTML page (unsupported content type).")
                    self.skipped_count += 1
                    return None
                content_length = response.headers.get('Content-Length')
                if content_length and int(content_length) > 2 * 1024 * 1024:
                    self._record_failure("The page exceeded the 2 MB size limit.")
                    self.skipped_count += 1
                    return None
                chunks = []
                size = 0
                async for chunk in response.aiter_bytes():
                    size += len(chunk)
                    if size > 2 * 1024 * 1024:
                        self._record_failure("The page exceeded the 2 MB size limit.")
                        self.skipped_count += 1
                        await self._emit('log', {'level':'WARN','message':'Page exceeded 2 MB limit'})
                        return None
                    chunks.append(chunk)
                self.resolved_urls[url] = url
                return b''.join(chunks).decode(response.encoding or 'utf-8', errors='replace')

        except httpx.TimeoutException:
            self._record_failure("The website did not respond within 12 seconds (timeout).")
            await self._emit("log", {"level": "ERROR", "message": f"Timeout fetching {url}"})
            self.skipped_count += 1
            return None
        except httpx.ConnectError:
            self._record_failure("Could not establish a connection to the website.")
            self.skipped_count += 1
            return None
        except httpx.HTTPError:
            self._record_failure("The website connection failed while fetching the page.")
            self.skipped_count += 1
            return None
        except Exception:
            self._record_failure("An unexpected error occurred while fetching the page.")
            await self._emit("log", {"level": "ERROR", "message": f"Error fetching {url}"})
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

        async with httpx.AsyncClient(verify=True, trust_env=False, timeout=12.0) as client:
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

                # Use the final validated URL for source attribution and relative links.
                effective_url = self.resolved_urls.get(current_url, current_url)
                # Content Extraction
                extracted_data = clean_and_extract_content(html_content, effective_url)
                if not extracted_data.get("success"):
                    self._record_failure("The page loaded, but no readable body text was found. It may require JavaScript rendering.")
                    self.skipped_count += 1
                    continue
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
                    new_links = self.discover_links(html_content, effective_url)
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
            "failure_reasons": self.failure_reasons,
            "combined_output": "".join(combined_output_chunks)
        }

        await self._emit("done", final_summary)
        return final_summary


async def crawl_site(start_url: str, max_pages: int = 10, delay: float = 0.3, include_diagnostics: bool = False):
    """Helper function to run AsyncCrawler and return extracted pages list."""
    crawler = AsyncCrawler(
        root_url=start_url,
        max_pages=max_pages,
        max_depth=4,
        crawl_delay_ms=int(delay * 1000)
    )
    results = await crawler.crawl()
    return results if include_diagnostics else results.get("extracted_pages", [])

