"""REST API endpoints for Web Search and Deep Research (section 59)."""

import uuid
from typing import Dict, Optional
from fastapi import APIRouter, HTTPException

from app.web.models import ResearchRequest, SearchMode, SearchRequest, SearchResultBundle
from app.web.research import ResearchService
from app.web.search import WebSearchService

web_router = APIRouter(prefix="/api", tags=["web-research"])

_web_search_svc = WebSearchService()
_research_svc = ResearchService()

_stored_results: Dict[str, SearchResultBundle] = {}


@web_router.post("/search", response_model=SearchResultBundle)
async def execute_search(req: SearchRequest):
    bundle = await _web_search_svc.search(
        query=req.query,
        mode=req.mode,
        max_sources=req.max_sources,
        with_images=req.with_images,
        with_videos=req.with_videos,
        chat_history=req.chat_history,
        location=req.region,
    )
    req_id = str(uuid.uuid4())
    _stored_results[req_id] = bundle
    return bundle


@web_router.post("/research", response_model=SearchResultBundle)
async def execute_research(req: ResearchRequest):
    bundle = await _research_svc.conduct_research(
        query=req.query,
        depth=req.depth,
        max_sources=12,
        chat_history=req.chat_history,
    )
    req_id = str(uuid.uuid4())
    _stored_results[req_id] = bundle
    return bundle


@web_router.get("/search/{request_id}", response_model=SearchResultBundle)
async def get_search_result(request_id: str):
    res = _stored_results.get(request_id)
    if not res:
        raise HTTPException(status_code=404, detail="Search result not found")
    return res


@web_router.get("/research/{request_id}", response_model=SearchResultBundle)
async def get_research_result(request_id: str):
    res = _stored_results.get(request_id)
    if not res:
        raise HTTPException(status_code=404, detail="Research result not found")
    return res


@web_router.get("/research/{request_id}/sources")
async def get_research_sources(request_id: str):
    res = _stored_results.get(request_id)
    if not res:
        raise HTTPException(status_code=404, detail="Research result not found")
    return {"sources": res.sources, "total": len(res.sources)}
