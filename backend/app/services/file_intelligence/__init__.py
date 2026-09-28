"""
HSBot General Chat — File Intelligence Package (V2)
"""
from app.services.file_intelligence.models import (
    FileProcessingState,
    FileCapabilities,
    FileChunk,
    FileChunkMetadata,
    ProcessedFileRepresentation,
    FileProvenanceRecord,
    FILE_LIMITS,
    PARSER_VERSION,
)
from app.services.file_intelligence.adapters import FileAdapterRegistryV2
from app.services.file_intelligence.storage import FileStorageManagerV2
from app.services.file_intelligence.retrieval import FileRetrievalEngineV2
from app.services.file_intelligence.context_engine import (
    GeneralChatFileContextEngineV2,
    get_recent_provenance,
)
from app.services.file_intelligence.spreadsheet_calc import SpreadsheetCalculator

__all__ = [
    "FileProcessingState",
    "FileCapabilities",
    "FileChunk",
    "FileChunkMetadata",
    "ProcessedFileRepresentation",
    "FileProvenanceRecord",
    "FILE_LIMITS",
    "PARSER_VERSION",
    "FileAdapterRegistryV2",
    "FileStorageManagerV2",
    "FileRetrievalEngineV2",
    "GeneralChatFileContextEngineV2",
    "SpreadsheetCalculator",
    "get_recent_provenance",
]
