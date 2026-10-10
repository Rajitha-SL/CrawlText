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
    assert client.urls == ["https://whop.com/home", "https://www.whop.com/home"]
    assert worker.resolved_urls["https://whop.com/home"] == "https://www.whop.com/home"


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
