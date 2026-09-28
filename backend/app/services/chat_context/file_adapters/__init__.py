from app.services.chat_context.file_adapters.base import BaseFileAdapter
from app.services.chat_context.file_adapters.registry import file_adapter_registry, FileAdapterRegistry
from app.services.chat_context.file_adapters.caching import file_processing_cache, FileProcessingCache
from app.services.chat_context.file_adapters.pdf_adapter import PDFAdapter
from app.services.chat_context.file_adapters.docx_adapter import DOCXAdapter
from app.services.chat_context.file_adapters.spreadsheet_adapter import SpreadsheetAdapter
from app.services.chat_context.file_adapters.presentation_adapter import PresentationAdapter
from app.services.chat_context.file_adapters.code_adapter import CodeAdapter
from app.services.chat_context.file_adapters.text_adapter import TextAdapter
from app.services.chat_context.file_adapters.image_adapter import ImageAdapter
from app.services.chat_context.file_adapters.archive_adapter import ArchiveAdapter
from app.services.chat_context.file_adapters.media_adapter import MediaAdapter
from app.services.chat_context.file_adapters.fallback_adapter import FallbackAdapter

__all__ = [
    "BaseFileAdapter",
    "FileAdapterRegistry",
    "file_adapter_registry",
    "FileProcessingCache",
    "file_processing_cache",
    "PDFAdapter",
    "DOCXAdapter",
    "SpreadsheetAdapter",
    "PresentationAdapter",
    "CodeAdapter",
    "TextAdapter",
    "ImageAdapter",
    "ArchiveAdapter",
    "MediaAdapter",
    "FallbackAdapter",
]
