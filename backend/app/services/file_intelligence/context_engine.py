"""
HSBot General Chat — File Context Engine & Provenance Tracker (GeneralChatFileContextEngineV2)
Combines current prompt, conversation history, active files, retrieved chunks, spreadsheet calculations,
and visual analysis within the selected model's context budget.
"""
import uuid
import base64
import logging
from typing import Optional, Any
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.file_intelligence.models import (
    ProcessedFileRepresentation,
    FileProcessingState,
    FileProvenanceRecord,
)
from app.services.file_intelligence.retrieval import FileRetrievalEngineV2
from app.services.file_intelligence.spreadsheet_calc import SpreadsheetCalculator
from app.services.file_intelligence.chunker import estimate_tokens

_logger = logging.getLogger("hsbot.file_context_v2")

# Recent provenance log for instrumentation & verification (Section 37 & 59)
_PROVENANCE_LOG: list[FileProvenanceRecord] = []


def get_recent_provenance(limit: int = 50) -> list[dict[str, Any]]:
    return [p.model_dump() for p in _PROVENANCE_LOG[-limit:]]


class GeneralChatFileContextEngineV2:
    """
    Constructs bounded, source-cited, multi-file context for General Chat LLM calls.
    Never exposes raw server paths. Never fakes file analysis when a file failed or is unsupported.
    """

    MODEL_CONTEXT_BUDGETS: dict[str, int] = {
        "llama-3.2-11b": 32000,
        "llama-3.1-70b": 64000,
        "llama-3.3-70b": 64000,
        "mistral-large": 64000,
        "codestral": 64000,
        "glm-5.2": 64000,
        "glm-coder": 64000,
        "DeepSeek-V3.2": 64000,
    }
    DEFAULT_CONTEXT_LIMIT = 32000
    RESERVED_OUTPUT_TOKENS = 4096

    @classmethod
    def get_file_evidence_budget(
        cls,
        model: Optional[str],
        system_prompt: str,
        conversation_messages: list[dict[str, Any]],
        user_prompt: str,
        max_output_tokens: int = RESERVED_OUTPUT_TOKENS,
    ) -> int:
        max_ctx = cls.MODEL_CONTEXT_BUDGETS.get(model or "", cls.DEFAULT_CONTEXT_LIMIT)
        used = (
            estimate_tokens(system_prompt)
            + estimate_tokens(user_prompt)
            + sum(estimate_tokens(m.get("content", "")) for m in conversation_messages[-10:])
            + max_output_tokens
        )
        available = max_ctx - used
        # Always guarantee at least 3,000 tokens for file evidence, capped at 20,000 tokens for fast inference
        return max(3000, min(available, 20000))

    @classmethod
    async def build_file_context_for_chat(
        cls,
        db: AsyncSession,
        user_id: Optional[str],
        message: str,
        explicit_file_ids: Optional[list[str]] = None,
        conversation_id: Optional[str] = None,
        message_id: Optional[str] = None,
        model: Optional[str] = None,
        system_prompt: str = "",
        conversation_messages: Optional[list[dict[str, Any]]] = None,
    ) -> dict[str, Any]:
        """
        Resolves active files, executes structure-aware retrieval + spreadsheet arithmetic + vision analysis,
        enforces the Model Context Contract (Section 36), and records provenance instrumentation (Section 37 & 59).
        """
        if not user_id:
            return {
                "has_files": False,
                "context_block": "",
                "cleaned_prompt": message,
                "files_used": [],
                "provenance": [],
                "attachments_meta": [],
                "all_failed_or_unsupported": False,
                "failure_summary": None,
            }

        resolved_files, required_ids, cleaned_prompt = await FileRetrievalEngineV2.resolve_active_files(
            db=db,
            user_id=str(user_id),
            message=message,
            explicit_file_ids=explicit_file_ids,
            conversation_id=conversation_id,
            message_id=message_id,
        )

        if not resolved_files:
            return {
                "has_files": False,
                "context_block": "",
                "cleaned_prompt": message,
                "files_used": [],
                "provenance": [],
                "attachments_meta": [],
                "all_failed_or_unsupported": False,
                "failure_summary": None,
            }

        model_request_id = f"req_{uuid.uuid4().hex[:12]}"
        evidence_budget_tokens = cls.get_file_evidence_budget(
            model=model,
            system_prompt=system_prompt,
            conversation_messages=conversation_messages or [],
            user_prompt=cleaned_prompt,
        )

        usable_files = [
            f for f in resolved_files
            if f.status in (FileProcessingState.READY, FileProcessingState.PARTIAL)
        ]
        failed_or_unsupported = [
            f for f in resolved_files
            if f.status in (FileProcessingState.FAILED, FileProcessingState.UNSUPPORTED)
        ]

        # Build attachment metadata for message persistence (Section 47)
        attachments_meta = [
            {
                "id": f.fileId,
                "fileId": f.fileId,
                "name": f.filename,
                "filename": f.filename,
                "type": f.mimeType,
                "mimeType": f.mimeType,
                "size": f.size,
                "status": f.status.value,
                "detectedFormat": f.detectedFormat,
                "error": f.error,
                "download_url": f"/api/files/{f.fileId}/download",
            }
            for f in resolved_files
        ]

        # If ALL requested files failed or are unsupported, report honestly and prevent hallucination (Section 40, 41, 66)
        if not usable_files and failed_or_unsupported:
            err_lines = []
            for f in failed_or_unsupported:
                state_lbl = "Unsupported" if f.status == FileProcessingState.UNSUPPORTED else "Failed"
                err_lines.append(
                    f"• **{f.filename}** — Status: **{state_lbl}** | Reason: {f.error or 'No compatible parser or file is corrupted.'}"
                )
            failure_summary = (
                "The attached file(s) could not be processed, so I cannot analyze their contents:\n\n"
                + "\n".join(err_lines)
            )
            return {
                "has_files": True,
                "context_block": "",
                "cleaned_prompt": cleaned_prompt,
                "files_used": [],
                "provenance": [],
                "attachments_meta": attachments_meta,
                "all_failed_or_unsupported": True,
                "failure_summary": failure_summary,
            }

        # Allocate token budget across usable files (Required files get priority share)
        num_usable = max(1, len(usable_files))
        per_file_token_budget = max(1200, evidence_budget_tokens // num_usable)

        context_sections: list[str] = []
        provenance_records: list[FileProvenanceRecord] = []

        # Multi-file inventory header (Section 34)
        if len(resolved_files) > 1:
            inv_lines = [f"=== ACTIVE CONVERSATION FILE INVENTORY ({len(resolved_files)} files) ==="]
            for idx, f in enumerate(resolved_files, start=1):
                req_tag = " [REQUIRED CONTEXT]" if f.fileId in required_ids else ""
                if f.status in (FileProcessingState.FAILED, FileProcessingState.UNSUPPORTED):
                    inv_lines.append(
                        f"{idx}. {f.filename} (fileId={f.fileId}, format={f.detectedFormat.upper()}) — "
                        f"STATUS: {f.status.value} ({f.error})"
                    )
                else:
                    inv_lines.append(
                        f"{idx}. {f.filename} (fileId={f.fileId}, format={f.detectedFormat.upper()}, "
                        f"size={f.size} bytes, chunks={len(f.chunks)}){req_tag} — STATUS: {f.status.value}"
                    )
            context_sections.append("\n".join(inv_lines))

        # Report any partial failure among multiple files (Section 39)
        if failed_or_unsupported and usable_files:
            unavail_lines = [
                "=== UNAVAILABLE / FAILED ATTACHMENTS (DO NOT PRETEND TO HAVE READ THESE) ==="
            ]
            for f in failed_or_unsupported:
                unavail_lines.append(
                    f"FILE: {f.filename} | STATUS: {f.status.value} | REASON: {f.error or 'Unavailable'}"
                )
            context_sections.append("\n".join(unavail_lines))

        # Process each usable file
        for rep in usable_files:
            is_req = rep.fileId in required_ids
            file_lines: list[str] = []

            # 1. If image file, run live vision analysis on the actual image bytes if needed (Section 17)
            vision_description = None
            if rep.detectedFormat == "image":
                data_uri = rep.structuredData.get("data_uri")
                if data_uri and "," in data_uri:
                    try:
                        from app.services.nvidia.vision import NvidiaVisionProvider
                        b64_part = data_uri.split(",", 1)[1]
                        img_bytes = base64.b64decode(b64_part)
                        v_prompt = (
                            f"The user attached image '{rep.filename}' and asked: '{cleaned_prompt}'. "
                            "Examine the image carefully. Describe all relevant visual details, charts, numbers, text, objects, and layout."
                        )
                        v_resp = await NvidiaVisionProvider().analyze(
                            image_data=img_bytes,
                            prompt=v_prompt,
                            mime_type=rep.mimeType or "image/png",
                        )
                        if v_resp and v_resp.content:
                            vision_description = v_resp.content
                    except Exception as e:
                        _logger.warning("Vision analysis fallback to metadata/OCR for %s: %s", rep.filename, e)

            # 2. If spreadsheet (XLSX / CSV), run deterministic SpreadsheetCalculator (Section 14 & 56)
            calc_block = None
            if rep.detectedFormat in ("xlsx", "csv"):
                sheets = rep.structuredData.get("sheets") or []
                calc_block = SpreadsheetCalculator.analyze_and_calculate(
                    rep.filename, sheets, cleaned_prompt
                )

            # 3. Exact occurrence search if user asked to find occurrences/functions
            exact_search_block = FileRetrievalEngineV2.find_exact_occurrences(rep, cleaned_prompt)

            # 4. Retrieve top relevant structure-aware chunks
            top_k = 14 if len(usable_files) == 1 else max(4, 16 // len(usable_files))
            selected_chunks = FileRetrievalEngineV2.search_within_file(rep, cleaned_prompt, top_k=top_k)

            # Enforce per-file token budget
            kept_chunks: list[dict[str, Any]] = []
            tokens_used = 0
            for ch in selected_chunks:
                ch_tok = ch.get("tokenEstimate") or estimate_tokens(ch.get("text", ""))
                if kept_chunks and (tokens_used + ch_tok > per_file_token_budget):
                    break
                kept_chunks.append(ch)
                tokens_used += ch_tok

            source_locations = [ch["citation"] for ch in kept_chunks if ch.get("citation")]
            chunk_ids = [ch["chunkId"] for ch in kept_chunks]

            # Build Model Context Contract block (Section 36)
            file_lines.append("====================================================================")
            file_lines.append(f"FILE: {rep.filename}" + (" [REQUIRED CONTEXT]" if is_req else ""))
            file_lines.append(f"TYPE: {rep.detectedFormat.upper()} ({rep.mimeType})")
            file_lines.append(f"SOURCE: fileId={rep.fileId}")
            file_lines.append(f"STATUS: {rep.status.value}")
            if rep.warnings:
                file_lines.append(f"WARNINGS: {'; '.join(rep.warnings)}")
            if rep.structureSummary:
                file_lines.append(f"STRUCTURE SUMMARY: {rep.structureSummary}")
            if source_locations:
                file_lines.append(f"RELEVANT LOCATIONS: {'; '.join(dict.fromkeys(source_locations[:10]))}")
            file_lines.append("--------------------------------------------------------------------")

            if vision_description:
                file_lines.append(f"[VISUAL ANALYSIS OF {rep.filename}]:\n{vision_description}\n")

            if calc_block:
                file_lines.append(f"{calc_block}\n")

            if exact_search_block:
                file_lines.append(f"{exact_search_block}\n")

            if kept_chunks:
                file_lines.append("RELEVANT CONTENT:")
                for ch in kept_chunks:
                    file_lines.append(f"--- Source Citation: {ch['citation']} (chunkId={ch['chunkId']}) ---")
                    file_lines.append(ch["text"])
            elif rep.fullText:
                snippet = rep.fullText[: per_file_token_budget * 4]
                file_lines.append(f"RELEVANT CONTENT:\n{snippet}")

            file_block_str = "\n".join(file_lines)
            context_sections.append(file_block_str)

            prov = FileProvenanceRecord(
                modelRequestId=model_request_id,
                fileId=rep.fileId,
                filename=rep.filename,
                chunkIds=chunk_ids,
                sourceLocations=list(dict.fromkeys(source_locations)),
                contentBytesDelivered=len(file_block_str.encode("utf-8")),
                tokensDelivered=estimate_tokens(file_block_str),
                wasRequiredContext=is_req,
            )
            provenance_records.append(prov)
            _PROVENANCE_LOG.append(prov)
            if len(_PROVENANCE_LOG) > 200:
                del _PROVENANCE_LOG[:50]

            _logger.info(
                "[FILE_CONTEXT_V2] req=%s fileId=%s filename=%s chunks=%d bytes=%d tokens=%d",
                model_request_id,
                rep.fileId,
                rep.filename,
                len(chunk_ids),
                prov.contentBytesDelivered,
                prov.tokensDelivered,
            )

        instructions_header = (
            "=== UPLOADED FILE INTELLIGENCE & GROUNDING CONTRACT ===\n"
            "You have been provided with real, verified, structure-extracted content from the user's uploaded file(s) below.\n"
            "CRITICAL RULES:\n"
            "1. Ground your answer strictly in the RELEVANT CONTENT, STRUCTURE SUMMARY, and VERIFIED SPREADSHEET CALCULATIONS below.\n"
            "2. Cite exact source locations whenever available (e.g., `report.pdf — page 24`, `data.xlsx — Sheet2, cells D2:D4`, `backend/auth.py — lines 45–82`). Do NOT fabricate page numbers, sheet names, or line numbers.\n"
            "3. When multiple files are provided, address and synthesize across all relevant files.\n"
            "4. If a file has STATUS: FAILED, UNSUPPORTED, or PARTIAL (e.g., audio/video without transcript), state that honestly and never pretend to have read unavailable content.\n"
        )

        final_context = instructions_header + "\n\n" + "\n\n".join(context_sections)

        return {
            "has_files": True,
            "model_request_id": model_request_id,
            "context_block": final_context,
            "cleaned_prompt": cleaned_prompt,
            "files_used": [
                {
                    "fileId": r.fileId,
                    "filename": r.filename,
                    "format": r.detectedFormat,
                    "status": r.status.value,
                }
                for r in usable_files
            ],
            "provenance": [p.model_dump() for p in provenance_records],
            "attachments_meta": attachments_meta,
            "all_failed_or_unsupported": False,
            "failure_summary": None,
        }
