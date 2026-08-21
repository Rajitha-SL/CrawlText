import re
from typing import Dict, Any, Optional
from bs4 import BeautifulSoup
import trafilatura

# Class / ID keywords for boilerplate & popups to strip
NOISE_PATTERNS = re.compile(
    r"(cookie|consent|popup|modal|banner|advertisement|banner|sidebar|navigation|nav-menu|header|footer|disclaimer|social-share|newsletter|subscribe)",
    re.IGNORECASE,
)

ELEMENTS_TO_REMOVE = [
    "header", "footer", "nav", "aside", "script", "style", "noscript",
    "svg", "iframe", "form", "dialog", "button", "template", "style"
]

def extract_page_title(soup: BeautifulSoup, fallback_url: str) -> str:
    """Extracts the cleanest title for a page from <title>, <h1>, or og:title."""
    # Try og:title
    og_title = soup.find("meta", property="og:title")
    if og_title and og_title.get("content"):
        title_str = og_title["content"].strip()
        if title_str:
            return title_str

    # Try <title> tag
    if soup.title and soup.title.string:
        title_str = soup.title.string.strip()
        if title_str:
            return title_str

    # Try first <h1> tag
    h1 = soup.find("h1")
    if h1:
        h1_str = h1.get_text(strip=True)
        if h1_str:
            return h1_str

    # Fallback to URL path
    return fallback_url


def fallback_bs4_extract(html: str, url: str) -> str:
    """
    Secondary fallback parser using BeautifulSoup4.
    Strips navigation, header, footer, popups, and non-textual elements.
    """
    soup = BeautifulSoup(html, "lxml")

    # Remove unwanted tag types
    for element_name in ELEMENTS_TO_REMOVE:
        for tag in soup.find_all(element_name):
            tag.decompose()

    # Remove noise elements matching class or id regex
    for tag in soup.find_all(True):
        classes = " ".join(tag.get("class", [])) if isinstance(tag.get("class"), list) else tag.get("class", "")
        tag_id = tag.get("id", "") or ""
        if NOISE_PATTERNS.search(classes) or NOISE_PATTERNS.search(tag_id):
            tag.decompose()

    # Look for main content container
    main_container = soup.find("main") or soup.find("article") or soup.find(id=re.compile(r"content|main", re.I)) or soup.find("body")
    if not main_container:
        main_container = soup

    # Gather paragraphs, headings, list items
    content_blocks = []
    for elem in main_container.find_all(["p", "h1", "h2", "h3", "h4", "h5", "h6", "li", "blockquote", "dt", "dd"]):
        text = elem.get_text(separator=" ", strip=True)
        if len(text) > 15: # Ignore very short text snippets
            content_blocks.append(text)

    if not content_blocks:
        # Final fallback to raw text lines
        raw_text = main_container.get_text(separator="\n", strip=True)
        lines = [line.strip() for line in raw_text.splitlines() if len(line.strip()) > 20]
        return "\n\n".join(lines)

    # Deduplicate consecutive identical blocks
    clean_blocks = []
    prev = None
    for block in content_blocks:
        if block != prev:
            clean_blocks.append(block)
            prev = block

    return "\n\n".join(clean_blocks)


def clean_and_extract_content(html: str, url: str) -> Dict[str, Any]:
    """
    Main extraction function combining Trafilatura and BeautifulSoup4.
    """
    if not html or not html.strip():
        return {
            "url": url,
            "title": "Empty Page",
            "text": "",
            "word_count": 0,
            "char_count": 0,
            "success": False,
            "error": "HTML content is empty."
        }

    soup = BeautifulSoup(html, "lxml")
    title = extract_page_title(soup, url)

    # 1. Primary Extraction with Trafilatura
    extracted_text = trafilatura.extract(
        html,
        url=url,
        include_comments=False,
        include_tables=True,
        include_links=False,
        no_fallback=False
    )

    # 2. Fallback to BeautifulSoup if Trafilatura yields poor results (< 50 chars)
    if not extracted_text or len(extracted_text.strip()) < 50:
        extracted_text = fallback_bs4_extract(html, url)

    # Clean up whitespace & line breaks
    if extracted_text:
        # Normalize multiple newlines
        extracted_text = re.sub(r"\n{3,}", "\n\n", extracted_text).strip()

    word_count = len(extracted_text.split()) if extracted_text else 0
    char_count = len(extracted_text) if extracted_text else 0

    return {
        "url": url,
        "title": title,
        "text": extracted_text or "[No readable body text found]",
        "word_count": word_count,
        "char_count": char_count,
        "success": bool(extracted_text and len(extracted_text.strip()) > 0),
        "error": None
    }


def format_page_output(title: str, url: str, body_text: str) -> str:
    """Formats a single page's output according to the required specification."""
    divider = "=" * 50
    return f"{divider}\nPAGE: {title}\nURL: {url}\n{divider}\n\n{body_text}\n\n"


def format_crawl_results(results: list) -> str:
    """Formats list of page result dictionaries into a unified formatted output string."""
    chunks = []
    for item in results:
        chunks.append(format_page_output(item.get("title", ""), item.get("url", ""), item.get("text", "")))
    return "".join(chunks)

