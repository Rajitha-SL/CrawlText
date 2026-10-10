from crawler import normalize_url, is_same_domain
from extractor import clean_and_extract_content
from security import is_ssrf_safe

def test_normalize_strips_fragments_and_trackers():
    value = normalize_url("https://example.com/a/?utm_source=x&q=2#section", "https://example.com")
    assert value == "https://example.com/a?q=2"

def test_external_domain_rejected():
    assert not is_same_domain("https://evil-example.com", "example.com")
    assert is_same_domain("https://docs.example.com", "example.com")

def test_private_and_local_addresses():
    for url in ("http://127.0.0.1", "http://10.0.0.1", "http://169.254.169.254", "file:///etc/passwd", "http://[::1]"):
        assert not is_ssrf_safe(url)[0]

def test_basic_extraction():
    html = "<html><head><title>Example</title></head><body><main><h1>A substantial article heading</h1><p>This paragraph contains actual material to be extracted from this test page.</p></main></body></html>"
    result = clean_and_extract_content(html, "https://example.com")
    assert result["success"]
    assert "paragraph" in result["text"].lower()

def test_safe_same_domain_redirect(monkeypatch):
    import asyncio
    import crawler

    class Response:
        def __init__(self, code, location=None):
            self.status_code = code
            self.headers = {"Content-Type": "text/html"}
            if location:
                self.headers["location"] = location
            self.encoding = "utf-8"
            self.is_redirect = code in (301, 302, 303, 307, 308)

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def aiter_bytes(self):
            yield b"<html><body><p>Redirected page content</p></body></html>"

    class Client:
        def __init__(self):
            self.urls = []

        def stream(self, method, url, **kwargs):
            self.urls.append(url)
            if url == "https://whop.com/home":
                return Response(308, "https://www.whop.com/home/")
            return Response(200)

    monkeypatch.setattr(crawler, "is_ssrf_safe", lambda url: (True, ""))
    worker = crawler.AsyncCrawler("https://whop.com/home")
    client = Client()
    result = asyncio.run(worker.fetch_page(client, "https://whop.com/home"))
    assert "Redirected page content" in result
    assert client.urls == ["https://whop.com/home", "https://www.whop.com/home/"]
    assert worker.resolved_urls["https://whop.com/home"] == "https://www.whop.com/home/"


def test_external_redirect_is_blocked(monkeypatch):
    import asyncio
    import crawler

    class Response:
        status_code = 308
        headers = {"location": "https://other-domain.example/private"}
        is_redirect = True

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

    class Client:
        def stream(self, *args, **kwargs):
            return Response()

    monkeypatch.setattr(crawler, "is_ssrf_safe", lambda url: (True, ""))
    worker = crawler.AsyncCrawler("https://whop.com/home")
    result = asyncio.run(worker.fetch_page(Client(), "https://whop.com/home"))
    assert result is None
    assert any("outside the requested domain" in reason for reason in worker.failure_reasons)


def test_redirect_preserves_canonical_trailing_slash(monkeypatch):
    import asyncio
    import crawler

    class Response:
        def __init__(self, status, location=None):
            self.status_code = status
            self.headers = {"Content-Type": "text/html"}
            if location:
                self.headers["location"] = location
            self.encoding = "utf-8"
            self.is_redirect = status in (301, 302, 303, 307, 308)

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def aiter_bytes(self):
            yield b"<html><body>canonical content</body></html>"

    class Client:
        def __init__(self):
            self.urls = []

        def stream(self, method, url, **kwargs):
            self.urls.append(url)
            if url == "https://whop.com/checkout/home":
                return Response(308, "/checkout/home/")
            return Response(200)

    monkeypatch.setattr(crawler, "is_ssrf_safe", lambda url: (True, ""))
    worker = crawler.AsyncCrawler("https://whop.com/checkout/home")
    client = Client()
    result = asyncio.run(worker.fetch_page(client, "https://whop.com/checkout/home"))
    assert "canonical content" in result
    assert client.urls == ["https://whop.com/checkout/home", "https://whop.com/checkout/home/"]
    assert worker.resolved_urls["https://whop.com/checkout/home"] == "https://whop.com/checkout/home/"


def test_clean_text_blocks_preserves_meaningful_numbers_and_removes_counters():
    from extractor import clean_text_blocks

    testimonial = "A genuine detailed customer testimonial describing the actual experience and the service received over several weeks."
    source = (
        "Annual plan costs $120 per year.\n\n"
        + "$01234567890123456789012345678901234567890123456789\n\n"
        + testimonial + "\n\n" + testimonial
    )
    result = clean_text_blocks(source)
    assert "$120" in result
    assert "0123456789012345" not in result
    assert result.count(testimonial) == 1


def test_shared_text_blocks_only_remove_exact_long_repeats():
    from extractor import clean_text_blocks

    seen = set()
    shared = "Our platform supports subscriptions and recurring payments with flexible settlement and reporting options for businesses."
    first = clean_text_blocks(shared + "\n\nUnique first-page content.", seen)
    second = clean_text_blocks(shared + "\n\nUnique second-page content.", seen)
    assert shared in first
    assert shared not in second
    assert "Unique second-page content." in second


def test_canonical_page_key_preserves_queries_and_distinct_subdomains():
    from crawler import canonical_page_key

    assert canonical_page_key("https://www.whop.com/home/") == canonical_page_key("https://whop.com/home")
    assert canonical_page_key("https://whop.com/home?tab=one") != canonical_page_key("https://whop.com/home?tab=two")
    assert canonical_page_key("https://docs.whop.com/home") != canonical_page_key("https://whop.com/home")


def test_crawl_skips_duplicate_resolved_pages(monkeypatch):
    import asyncio
    import crawler

    class FakeClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

    calls = []

    async def fake_fetch(self, client, url, *args, **kwargs):
        calls.append(url)
        self.resolved_urls[url] = "https://www.whop.com/home/" if url.endswith("/home") else url
        return "<html><head><title>Whop Home</title></head><body><main><p>A substantial unique paragraph about the product and services available to customers.</p></main></body></html>"

    def fake_links(self, html, url):
        return {"https://www.whop.com/home", "https://whop.com/home"}

    monkeypatch.setattr(crawler, "is_ssrf_safe", lambda url: (True, ""))
    monkeypatch.setattr(crawler.httpx, "AsyncClient", lambda **kwargs: FakeClient())
    monkeypatch.setattr(crawler.AsyncCrawler, "fetch_page", fake_fetch)
    monkeypatch.setattr(crawler.AsyncCrawler, "discover_links", fake_links)

    worker = crawler.AsyncCrawler("https://whop.com/home", max_pages=5, crawl_delay_ms=0)
    result = asyncio.run(worker.crawl())
    assert len(result["extracted_pages"]) == 1
    assert result["combined_output"].count("PAGE: Whop Home") == 1
