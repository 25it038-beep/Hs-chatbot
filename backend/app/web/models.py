"""Data models and schemas for the Perplexity-Level Search and Research Engine."""

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class SearchMode(str, Enum):
    FAST = "fast"
    PRO = "pro"
    DEEP = "deep"
    NONE = "none"


class SourceType(str, Enum):
    OFFICIAL = "official"
    GOVERNMENT = "government"
    ACADEMIC = "academic"
    PRIMARY = "primary"
    NEWS = "news"
    TECHNICAL = "technical"
    COMPANY = "company"
    COMMUNITY = "community"
    BLOG = "blog"
    FORUM = "forum"
    AGGREGATOR = "aggregator"
    WEB = "web"


class SearchRequest(BaseModel):
    query: str
    mode: Optional[SearchMode] = None  # None = auto-detect
    freshness: Optional[str] = None    # "current", "recent", "all"
    region: Optional[str] = None
    source_focus: Optional[List[str]] = None
    max_sources: int = 8
    with_images: bool = False
    with_videos: bool = False
    chat_history: Optional[List[Dict[str, str]]] = None


class ResearchRequest(BaseModel):
    query: str
    depth: str = "comprehensive"       # "standard", "comprehensive", "exhaustive"
    source_preferences: Optional[List[str]] = None
    date_range: Optional[Dict[str, str]] = None
    output_format: str = "report"      # "answer", "report", "pdf", "docx", "pptx"
    region: Optional[str] = None
    max_iterations: int = 3
    chat_history: Optional[List[Dict[str, str]]] = None


class SourceMetadata(BaseModel):
    source_id: int
    title: str
    url: str
    domain: str
    source_type: SourceType = SourceType.WEB
    authority_score: float = 0.0
    published_date: Optional[str] = None
    snippet: str = ""
    relevance_score: float = 0.0


class EvidenceItem(BaseModel):
    evidence_id: str
    source_id: int
    text: str
    relevance: float = 0.0
    extracted_at: Optional[str] = None


class ClaimVerification(BaseModel):
    claim_id: str
    claim_text: str
    source_ids: List[int] = Field(default_factory=list)
    status: str = "VERIFIED"  # "VERIFIED", "CONTRADICTED", "PARTIAL", "UNVERIFIED"
    contradiction_notes: Optional[str] = None


class ResearchSubtask(BaseModel):
    subtask_id: str
    question: str
    search_queries: List[str] = Field(default_factory=list)
    completed: bool = False
    evidence_found: int = 0


class ResearchPlan(BaseModel):
    topic: str
    objectives: List[str] = Field(default_factory=list)
    subtasks: List[ResearchSubtask] = Field(default_factory=list)
    total_sources_consulted: int = 0
    gaps_identified: List[str] = Field(default_factory=list)


class SearchResultBundle(BaseModel):
    mode: SearchMode
    original_query: str
    resolved_query: str
    direct_answer: Optional[str] = None
    structured_context: str = ""
    sources: List[SourceMetadata] = Field(default_factory=list)
    evidence: List[EvidenceItem] = Field(default_factory=list)
    claims: List[ClaimVerification] = Field(default_factory=list)
    conflicts: List[str] = Field(default_factory=list)
    images_md: str = ""
    videos_md: str = ""
    sources_md: str = ""
    duration_ms: float = 0.0
    research_plan: Optional[ResearchPlan] = None
