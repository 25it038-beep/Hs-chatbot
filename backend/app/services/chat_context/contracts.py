from enum import Enum
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any


class FileCapability(str, Enum):
    TEXT = "TEXT"
    DOCUMENT = "DOCUMENT"
    PDF = "PDF"
    WORD_DOCUMENT = "WORD_DOCUMENT"
    SPREADSHEET = "SPREADSHEET"
    PRESENTATION = "PRESENTATION"
    IMAGE = "IMAGE"
    AUDIO = "AUDIO"
    VIDEO = "VIDEO"
    CODE = "CODE"
    DATA = "DATA"
    ARCHIVE = "ARCHIVE"
    STRUCTURED_DATA = "STRUCTURED_DATA"
    MARKUP = "MARKUP"
    DATABASE = "DATABASE"
    BINARY = "BINARY"
    OTHER = "OTHER"


class FileProcessingState(str, Enum):
    UPLOADING = "UPLOADING"
    PROCESSING = "PROCESSING"
    ANALYZING = "ANALYZING"
    READY = "READY"
    PARTIALLY_SUPPORTED = "PARTIALLY_SUPPORTED"
    FAILED = "FAILED"


class ChatRequestPhase(str, Enum):
    QUEUED = "QUEUED"
    PREPARING_CONTEXT = "PREPARING_CONTEXT"
    READING_FILES = "READING_FILES"
    CALLING_MODEL = "CALLING_MODEL"
    STREAMING = "STREAMING"
    TOOL_CALLING = "TOOL_CALLING"
    WAITING_TOOL = "WAITING_TOOL"
    FINALIZING = "FINALIZING"
    COMPLETED = "COMPLETED"
    RETRYING = "RETRYING"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class ContextPriority(int, Enum):
    CURRENT_REQUEST = 1
    EXPLICIT_FILES = 2
    RELEVANT_MESSAGES = 3
    RELEVANT_DOCS = 4
    TOOL_RESULTS = 5
    RECENT_CHAT = 6
    OLDER_HISTORY = 7


@dataclass
class DocumentChunk:
    chunk_id: str
    file_id: str
    source: str
    location: str
    section: str = ""
    page: Optional[int] = None
    sheet: Optional[str] = None
    slide: Optional[int] = None
    start_line: Optional[int] = None
    end_line: Optional[int] = None
    content: str = ""
    token_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class FileAnalysisResult:
    file_id: str
    filename: str
    capability: FileCapability
    state: FileProcessingState
    summary: str = ""
    chunks: List[DocumentChunk] = field(default_factory=list)
    total_tokens: int = 0
    total_pages: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    citations: List[str] = field(default_factory=list)
    error: Optional[str] = None
    is_partially_supported: bool = False

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["capability"] = self.capability.value
        d["state"] = self.state.value
        d["chunks"] = [c.to_dict() for c in self.chunks]
        return d


@dataclass
class ContextBudget:
    model_id: str
    max_context: int
    safety_margin: float
    usable_budget: int
    system_tokens: int = 0
    user_tokens: int = 0
    file_tokens: int = 0
    history_tokens: int = 0
    tool_tokens: int = 0
    output_budget: int = 4096
    remaining_tokens: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ConversationContextSummary:
    active_topic: str = ""
    user_requirements: List[str] = field(default_factory=list)
    decisions: List[str] = field(default_factory=list)
    active_files: List[Dict[str, Any]] = field(default_factory=list)
    open_questions: List[str] = field(default_factory=list)
    summary_text: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class RequestObservability:
    request_id: str
    model: str
    started_at: float
    phase: ChatRequestPhase = ChatRequestPhase.QUEUED
    first_token_at: Optional[float] = None
    completed_at: Optional[float] = None
    retry_count: int = 0
    context_size: int = 0
    input_sources: List[str] = field(default_factory=list)
    file_count: int = 0
    retrieved_chunks_count: int = 0
    status: str = "IN_PROGRESS"
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["phase"] = self.phase.value
        return d
