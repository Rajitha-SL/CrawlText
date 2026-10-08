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
