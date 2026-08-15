import re
from urllib.parse import urlparse

from .config import browser_config

_MARKDOWN_LINK_RE = re.compile(r"\[(.+?)\]\((https?://[^)]+)\)")


def _strip_markdown(text: str) -> str:
    text = text.strip()
    if not text:
        return text
    text = _MARKDOWN_LINK_RE.sub(r"\2", text)
    text = text.strip(" \t\n\r\"'`[]()")
    return text


def _known_service_url(candidate: str) -> str | None:
    text = candidate.strip().lower()
    if not text:
        return None
    if text in browser_config.WEBSITES:
        return browser_config.WEBSITES[text]
    for service in sorted(browser_config.WEBSITES, key=len, reverse=True):
        pattern = rf"(?<![a-z0-9]){re.escape(service.lower())}(?![a-z0-9])"
        if re.search(pattern, text):
            return browser_config.WEBSITES[service]
    return None


def _is_local_host(host: str) -> bool:
    if host in {"localhost", "127.0.0.1"}:
        return True
    return (
        host.startswith("127.")
        or host.startswith("10.")
        or host.startswith("192.168.")
        or host.startswith("172.")
        or host.startswith("169.254.")
        or host.endswith(".internal")
    )


def normalize_browser_url(raw: str | None, *, default_service: str | None = None) -> str | None:
    """Normalize user-entered URLs to safe http/https URLs with validation."""
    if raw is None:
        raw = ""
    candidate = _strip_markdown(str(raw))
    if not candidate:
        if default_service:
            svc = default_service.lower()
            url = browser_config.WEBSITES.get(svc)
            if url:
                return url
        return None

    service_url = _known_service_url(candidate)
    if service_url:
        return service_url

    # Direct URL or markdown link already resolved.
    if candidate.lower().startswith(("http://", "https://")):
        url = candidate
    elif candidate.lower().startswith("//"):
        url = "https:" + candidate
    elif re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*://", candidate):
        return None
    else:
        if " " in candidate.strip():
            return None
        if candidate.lower().startswith("www."):
            url = f"https://{candidate}"
        elif re.fullmatch(r"[a-z0-9.-]+", candidate):
            url = f"https://{candidate}"
        else:
            return None

    parsed = urlparse(url)
    if parsed.scheme.lower() not in {"http", "https"}:
        return None
    host = (parsed.hostname or "").lower()
    if not host:
        return None
    if _is_local_host(host) and not browser_config.BROWSER_TRUSTED_LOCAL:
        return None
    if host.endswith("."):
        host = host.rstrip(".")
    if not host or host.startswith("."):
        return None
    if not re.fullmatch(r"[a-z0-9.-]+", host):
        return None
    normalized = parsed._replace(netloc=host, scheme=parsed.scheme.lower(), path=parsed.path or "/").geturl()
    return normalized.rstrip("/") if normalized.endswith("/") and len(normalized) > 8 else normalized


def validate_browser_url(raw: str | None) -> bool:
    return normalize_browser_url(raw) is not None
