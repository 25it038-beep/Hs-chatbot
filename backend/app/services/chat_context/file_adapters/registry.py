import os
import logging
from typing import Dict, List, Optional
from app.services.chat_context.contracts import FileAnalysisResult
from app.services.chat_context.file_adapters.base import BaseFileAdapter
from app.services.chat_context.file_adapters.caching import file_processing_cache
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

logger = logging.getLogger("hsbot.chat_context.registry")


class FileAdapterRegistry:
    """
    Central registry routing files to specialized adapters with caching and fallback guarantees.
    """

    def __init__(self):
        # Order matters: specific rich formats first, code and text next, fallback last
        self._adapters: List[BaseFileAdapter] = [
            PDFAdapter(),
            DOCXAdapter(),
            SpreadsheetAdapter(),
            PresentationAdapter(),
            CodeAdapter(),
            TextAdapter(),
            ImageAdapter(),
            ArchiveAdapter(),
            MediaAdapter(),
        ]
        self._fallback_adapter = FallbackAdapter()

    def get_adapter(self, filename: str, mime_type: Optional[str] = None) -> BaseFileAdapter:
        for adapter in self._adapters:
            if adapter.can_handle(filename, mime_type):
                return adapter
        return self._fallback_adapter

    async def process_file(
        self,
        file_path: str,
        filename: str,
        file_id: str,
        mime_type: Optional[str] = None,
        use_cache: bool = True
    ) -> FileAnalysisResult:
        """
        Parses and extracts structured document chunks. Checks cache first.
        """
        if use_cache:
            cached = file_processing_cache.get(file_path, filename)
            if cached is not None:
                logger.debug(f"Retrieved cached extraction for file {filename} ({file_id})")
                return cached

        adapter = self.get_adapter(filename, mime_type)
        logger.info(f"Extracting file '{filename}' with adapter {adapter.__class__.__name__}")
        result = await adapter.extract(file_path, filename, file_id)

        if use_cache and result.state.value != "FAILED":
            file_processing_cache.put(file_path, result)

        return result


file_adapter_registry = FileAdapterRegistry()
