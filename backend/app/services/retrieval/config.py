"""Retrieval pipeline configuration — every knob is env-overridable."""

import os


def _int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default


def _float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default


class RetrievalConfig:
    # ── Concurrency control (section 17) ──
    MAX_SEARCH_CONCURRENCY: int = _int("MAX_SEARCH_CONCURRENCY", 4)
    MAX_FETCH_CONCURRENCY: int = _int("MAX_FETCH_CONCURRENCY", 8)
    MAX_IMAGE_CONCURRENCY: int = _int("MAX_IMAGE_CONCURRENCY", 4)
    MAX_NEWS_CONCURRENCY: int = _int("MAX_NEWS_CONCURRENCY", 3)
    MAX_TAVILY_CONCURRENCY: int = _int("RETRIEVAL_MAX_TAVILY_CONCURRENCY", 2)

    # ── Tavily (primary provider, sections 2, 20) ──
    # Primary key is the default; the fallback key is rotated in automatically
    # when the primary is rejected (401/403) or exhausted (429).
    TAVILY_API_KEY: str = os.getenv(
        "TAVILY_API_KEY", "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"
    )
    TAVILY_FALLBACK_API_KEY: str = os.getenv(
        "TAVILY_FALLBACK_API_KEY", "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"
    )
    TAVILY_TIMEOUT_S: float = _float("RETRIEVAL_TAVILY_TIMEOUT_S", 5.0)
    TAVILY_MAX_RESULTS: int = _int("RETRIEVAL_TAVILY_MAX_RESULTS", 10)
    TAVILY_DEPTH: str = os.getenv("RETRIEVAL_TAVILY_DEPTH", "basic")
    TAVILY_IMAGE_ENABLED: bool = os.getenv("RETRIEVAL_TAVILY_IMAGE_ENABLED", "1") != "0"
    TAVILY_IMAGE_MAX: int = _int("RETRIEVAL_TAVILY_IMAGE_MAX", 8)
    TAVILY_VIDEO_ENABLED: bool = os.getenv("RETRIEVAL_TAVILY_VIDEO_ENABLED", "1") != "0"
    TAVILY_VIDEO_MAX: int = _int("RETRIEVAL_TAVILY_VIDEO_MAX", 15)
    TAVILY_EXTRACT_ENABLED: bool = os.getenv("RETRIEVAL_TAVILY_EXTRACT_ENABLED", "1") != "0"
    TAVILY_EXTRACT_MAX: int = _int("RETRIEVAL_TAVILY_EXTRACT_MAX", 3)
    TAVILY_EXTRACT_TIMEOUT_S: float = _float("RETRIEVAL_TAVILY_EXTRACT_TIMEOUT_S", 8.0)

    # ── Candidate / selection limits (section 4) ──
    CANDIDATES_PER_PROVIDER: int = _int("RETRIEVAL_CANDIDATES", 25)
    TOP_RESULTS_MAX: int = _int("RETRIEVAL_TOP_MAX", 10)
    TOP_RESULTS_SIMPLE: int = _int("RETRIEVAL_TOP_SIMPLE", 3)
    TOP_RESULTS_MEDIUM: int = _int("RETRIEVAL_TOP_MEDIUM", 6)

    # ── Timeouts (section 6) ──
    SEARCH_TIMEOUT_S: float = _float("RETRIEVAL_SEARCH_TIMEOUT_S", 4.5)
    FETCH_TIMEOUT_S: float = _float("RETRIEVAL_FETCH_TIMEOUT_S", 5.0)
    CONNECT_TIMEOUT_S: float = _float("RETRIEVAL_CONNECT_TIMEOUT_S", 3.0)
    GLOBAL_TIMEOUT_S: float = _float("RETRIEVAL_GLOBAL_TIMEOUT_S", 8.0)

    # ── Fetch safety (sections 6, 21) ──
    MAX_PAGE_BYTES: int = _int("RETRIEVAL_MAX_PAGE_BYTES", 600_000)
    MAX_REDIRECTS: int = 5
    FETCH_RETRIES: int = _int("RETRIEVAL_FETCH_RETRIES", 1)
    MAX_CONTEXT_CHARS: int = _int("RETRIEVAL_MAX_CONTEXT_CHARS", 8_000)
    PASSAGE_CHARS: int = 1_200
    PASSAGE_OVERLAP: int = 150

    # ── Caching (sections 7, 8) ──
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    CACHE_ENABLED: bool = os.getenv("RETRIEVAL_CACHE_ENABLED", "1") != "0"
    TTL_NEWS_S: int = _int("RETRIEVAL_TTL_NEWS_S", 15 * 60)
    TTL_CURRENT_S: int = _int("RETRIEVAL_TTL_CURRENT_S", 30 * 60)
    TTL_GENERAL_S: int = _int("RETRIEVAL_TTL_GENERAL_S", 24 * 3600)
    TTL_DOCS_S: int = _int("RETRIEVAL_TTL_DOCS_S", 7 * 24 * 3600)

    # ── Image relevance (section 11) ──
    IMAGE_MIN_KEYWORD_HITS: int = _int("RETRIEVAL_IMAGE_MIN_KEYWORD_HITS", 2)
    MAX_IMAGES: int = _int("RETRIEVAL_MAX_IMAGES", 6)

    # ── Video retrieval (section 26) ──
    MAX_VIDEOS: int = _int("RETRIEVAL_MAX_VIDEOS", 4)
    VIDEO_CANDIDATES: int = _int("RETRIEVAL_VIDEO_CANDIDATES", 20)

    # ── Selenium dynamic-page fallback (section 27) ──
    # Only used when fast HTTP fetch + Tavily extract both fail, or when the
    # HTTP body is too thin to be useful (JS-rendered page).
    SELENIUM_ENABLED: bool = os.getenv("SELENIUM_ENABLED", "1") != "0"
    SELENIUM_PAGE_LOAD_TIMEOUT_S: float = _float("SELENIUM_PAGE_LOAD_TIMEOUT_S", 8.0)
    SELENIUM_SCRIPT_TIMEOUT_S: float = _float("SELENIUM_SCRIPT_TIMEOUT_S", 5.0)
    SELENIUM_TOTAL_TIMEOUT_S: float = _float("SELENIUM_TOTAL_TIMEOUT_S", 10.0)
    # First browser start includes the chromedriver download (Selenium
    # Manager); that must not count against a single page's budget.
    SELENIUM_STARTUP_TIMEOUT_S: float = _float("SELENIUM_STARTUP_TIMEOUT_S", 30.0)
    SELENIUM_MAX_WORKERS: int = _int("SELENIUM_MAX_WORKERS", 2)
    SELENIUM_MAX_PAGES_PER_BROWSER: int = _int("SELENIUM_MAX_PAGES_PER_BROWSER", 5)
    SELENIUM_MAX_FALLBACKS: int = _int("SELENIUM_MAX_FALLBACKS", 3)
    SELENIUM_MIN_CONTENT_CHARS: int = _int("SELENIUM_MIN_CONTENT_CHARS", 200)
    SELENIUM_MIN_HTML_CHARS: int = _int("SELENIUM_MIN_HTML_CHARS", 1_500)
    SELENIUM_HEADLESS: bool = os.getenv("SELENIUM_HEADLESS", "1") != "0"
    SELENIUM_BLOCK_IMAGES: bool = os.getenv("SELENIUM_BLOCK_IMAGES", "1") != "0"
    # Explicit wait target: Selenium waits for one of these selectors (or
    # document.readyState == complete) instead of arbitrary sleeps.
    SELENIUM_CONTENT_SELECTOR: str = os.getenv("SELENIUM_CONTENT_SELECTOR", "article, main, [role=main], p, h1")
    SELENIUM_WAIT_SETTLE_S: float = _float("SELENIUM_WAIT_SETTLE_S", 1.0)

    # ── User agent ──
    USER_AGENT: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0 Safari/537.36 HSBot/1.0"
    )


retrieval_config = RetrievalConfig()
