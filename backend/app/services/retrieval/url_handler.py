import logging
import asyncio
from typing import Optional, Dict, Any
from app.services.retrieval.url_detector import extract_url_query
from app.services.retrieval.fetcher import page_fetcher
from app.services.retrieval.extractor import extract_text, extract_meta

logger = logging.getLogger("hsbot.retrieval.url_handler")

async def handle_url_fetching(message: str, status_cb = None) -> dict[str, Any]:
    """
    Detects, fetches and extracts webpage content for URLs in a user message.
    Returns:
        {
            "has_url": bool,
            "success": bool,
            "url": str or None,
            "query": str,
            "context": str or None,
            "error": str or None
        }
    """
    extracted = extract_url_query(message)
    url = extracted["url"]
    query = extracted["query"]
    
    if not url:
        return {
            "has_url": False,
            "success": False,
            "url": None,
            "query": message,
            "context": None,
            "error": None
        }
        
    logger.info(f"[URL] Detected URL: {url}")
    if status_cb:
        await status_cb(f"🔗 Detected URL: {url}")
        
    logger.info(f"[URL] Validating: {url}")
    if status_cb:
        await status_cb(f"🔎 Validating URL: {url}")
        
    # Start fetching
    logger.info(f"[URL] Fetch started: {url}")
    if status_cb:
        await status_cb(f"📥 Fetching webpage: {url}")
        
    try:
        # Use our robust PageFetcher which wraps HTTP, Tavily Extract, and Selenium
        results = await page_fetcher.fetch_many([url], budget_s=12.0)
        res = results[0]
        
        err = res.get("error")
        content = res.get("content")
        method = res.get("method", "http")
        final_url = res.get("final_url", url)
        
        if err:
            logger.error(f"[URL] Fetch failed: {err}")
            if status_cb:
                await status_cb(f"❌ Failed to fetch page: {err}")
            return {
                "has_url": True,
                "success": False,
                "url": url,
                "query": query,
                "context": None,
                "error": f"Failed to fetch webpage: {err}"
            }
            
        logger.info(f"[URL] Fetch completed successfully using {method}")
        meta = extract_meta(content, fallback_title="Webpage")
        title = meta.get("title", "Webpage")
        
        logger.info("[URL] HTML extraction started")
        clean_text = extract_text(content)
        char_count = len(clean_text)
        logger.info(f"[URL] Extracted characters: {char_count}")
        
        if status_cb:
            await status_cb(f"📄 Content extracted ({char_count} chars): {title}")
            
        context = f"[Webpage Content]\nURL: {final_url}\nTitle: {title}\nContent:\n{clean_text}"
        
        return {
            "has_url": True,
            "success": True,
            "url": url,
            "query": query,
            "context": context,
            "error": None
        }
    except Exception as e:
        logger.exception(f"[URL] Exception in URL fetching handler: {e}")
        if status_cb:
            await status_cb(f"❌ Fetching error: {str(e)}")
        return {
            "has_url": True,
            "success": False,
            "url": url,
            "query": query,
            "context": None,
            "error": f"Failed to fetch webpage due to internal error: {str(e)}"
        }
