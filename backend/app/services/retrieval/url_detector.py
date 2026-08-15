import re
from typing import list, dict, Optional

URL_PATTERN = re.compile(r'(https?://[^\s<>"]+|www\.[^\s<>"]+)', re.I)

def detect_urls(text: str) -> list[str]:
    if not text:
        return []
    urls = []
    for match in URL_PATTERN.finditer(text):
        url = match.group(0)
        # Strip trailing punctuation commonly added at the end of a URL in a sentence
        url = re.sub(r'[.,;:!?\)\"\'\u201d\u201c]+$', '', url)
        # If it starts with www., prepend https://
        if url.lower().startswith("www."):
            url = "https://" + url
        if url not in urls:
            urls.append(url)
    return urls

def extract_url_query(text: str) -> dict:
    urls = detect_urls(text)
    if not urls:
        return {"url": None, "urls": [], "query": text}
    
    first_url = urls[0]
    
    # Remove all detected URLs from the query text
    query_clean = text
    for u in urls:
        query_clean = query_clean.replace(u, "")
        # Also handle if it was originally 'www.' without protocol in the text
        if u.startswith("https://") and "www." in u:
            raw_www = u[8:]  # strip 'https://'
            query_clean = query_clean.replace(raw_www, "")
            
    # Clean up punctuation around the removed URL (colons, dashes, etc.)
    query_clean = re.sub(r'\s*[:,\-\–\—]?\s*', ' ', query_clean).strip()
    query_clean = re.sub(r'\s+', ' ', query_clean).strip()
    
    return {
        "url": first_url,
        "urls": urls,
        "query": query_clean or "Summarize this website"
    }
