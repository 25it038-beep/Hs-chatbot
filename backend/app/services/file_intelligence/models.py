"""
HSBot General Chat — File Intelligence Models, State Machine & Contracts (V2)
"""
from enum import Enum
from typing import Optional, Any
from pydantic import BaseModel, Field


PARSER_VERSION = "2.0.0"


class FileProcessingState(str, Enum):
    UPLOADING = "UPLOADING"
    UPLOADED = "UPLOADED"
    VALIDATING = "VALIDATING"
    PARSING = "PARSING"
    EXTRACTING_STRUCTURE = "EXTRACTING_STRUCTURE"
    CHUNKING = "CHUNKING"
    INDEXING = "INDEXING"
    READY = "READY"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"
    UNSUPPORTED = "UNSUPPORTED"


class FileLimitsConfig(BaseModel):
    MAX_FILE_SIZE: int = 50 * 1024 * 1024  # 50MB
    MAX_TOTAL_UPLOAD_SIZE: int = 100 * 1024 * 1024  # 100MB
    MAX_FILES_PER_MESSAGE: int = 10
    MAX_FILES_PER_CONVERSATION: int = 50
    MAX_ARCHIVE_FILES: int = 200
    MAX_ARCHIVE_EXTRACTED_SIZE: int = 100 * 1024 * 1024  # 100MB
    MAX_PROCESSING_TIME_SECONDS: int = 45
    MAX_CHUNKS_PER_FILE: int = 500


FILE_LIMITS = FileLimitsConfig()


class FileCapabilities(BaseModel):
    canExtractText: bool = False
    canExtractTables: bool = False
    canExtractImages: bool = False
    canPreview: bool = False
    canSearch: bool = False
    canChunk: bool = False
    canAnalyzeVisually: bool = False
    canTranscribe: bool = False
    canInspectStructure: bool = False


class FileChunkMetadata(BaseModel):
    chunkId: str
    fileId: str
    filename: str
    sourceType: str = "txt"
    page: Optional[int] = None
    section: Optional[str] = None
    slide: Optional[int] = None
    sheet: Optional[str] = None
    rowStart: Optional[int] = None
    rowEnd: Optional[int] = None
    cellRange: Optional[str] = None
    lineStart: Optional[int] = None
    lineEnd: Optional[int] = None
    innerPath: Optional[str] = None
    position: int = 0

    def format_citation(self) -> str:
        parts = [self.innerPath or self.filename]
        if self.page is not None:
            parts.append(f"page {self.page}")
        if self.slide is not None:
            parts.append(f"slide {self.slide}")
        if self.sheet:
            parts.append(f"sheet '{self.sheet}'")
        if self.cellRange:
            parts.append(f"cells {self.cellRange}")
        elif self.rowStart is not None and self.rowEnd is not None:
            parts.append(f"rows {self.rowStart}–{self.rowEnd}")
        if self.lineStart is not None and self.lineEnd is not None:
            parts.append(f"lines {self.lineStart}–{self.lineEnd}")
        if self.section and self.section not in parts:
            parts.append(f"section '{self.section}'")
        return " — ".join(parts)

    def to_compact_dict(self) -> dict[str, Any]:
        return {k: v for k, v in self.model_dump().items() if v is not None}


class FileChunk(BaseModel):
    chunkId: str
    fileId: str
    filename: str
    text: str
    tokenEstimate: int = 0
    metadata: FileChunkMetadata


class ProcessedFileRepresentation(BaseModel):
    fileId: str
    userId: str
    conversationId: Optional[str] = None
    messageId: Optional[str] = None
    filename: str
    mimeType: str = "application/octet-stream"
    detectedFormat: str = "txt"
    extension: str = "txt"
    size: int = 0
    contentHash: str = ""
    parserVersion: str = PARSER_VERSION
    parserName: str = "BaseAdapterV2"
    status: FileProcessingState = FileProcessingState.READY
    processingStage: str = "Ready"
    error: Optional[str] = None
    warnings: list[str] = Field(default_factory=list)
    capabilities: FileCapabilities = Field(default_factory=FileCapabilities)
    fullText: str = ""
    textPreview: str = ""
    totalTokensEstimate: int = 0
    structureSummary: dict[str, Any] = Field(default_factory=dict)
    structuredData: dict[str, Any] = Field(default_factory=dict)
    chunks: list[FileChunk] = Field(default_factory=list)
    preview: dict[str, Any] = Field(default_factory=dict)
    securityScan: dict[str, Any] = Field(default_factory=dict)
    createdAt: str = ""


class FileProvenanceRecord(BaseModel):
    modelRequestId: str
    fileId: str
    filename: str
    chunkIds: list[str] = Field(default_factory=list)
    sourceLocations: list[str] = Field(default_factory=list)
    contentBytesDelivered: int = 0
    tokensDelivered: int = 0
    wasRequiredContext: bool = False
