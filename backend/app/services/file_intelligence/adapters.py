"""
HSBot General Chat — Universal File Adapter Registry (FileAdapterRegistryV2)
Adapters: PDF, DOCX, XLSX, CSV, PPTX, TXT, MD, JSON, JSONL, XML, YAML, CODE, IMAGE, AUDIO, VIDEO, ARCHIVE
"""
import os
import re
import csv
import json
import base64
import zipfile
import tarfile
import tempfile
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from typing import Optional, Any
from pathlib import Path

from app.services.file_intelligence.models import (
    FileProcessingState,
    FileCapabilities,
    FileChunk,
    FileChunkMetadata,
    ProcessedFileRepresentation,
    PARSER_VERSION,
    FILE_LIMITS,
)
from app.services.file_intelligence.security import (
    CODE_EXTENSIONS,
    detect_file_type_and_validate,
    validate_archive_safety,
    compute_sha256_file,
)
from app.services.file_intelligence.chunker import StructureAwareChunker, estimate_tokens
from app.services.file_intelligence.spreadsheet_calc import _col_index_to_letter, _to_number


class BaseFileAdapterV2:
    adapter_name: str = "BaseAdapterV2"
    supported_formats: list[str] = []

    def get_capabilities(self) -> FileCapabilities:
        return FileCapabilities()

    def process(
        self,
        file_path: str,
        file_id: str,
        user_id: str,
        filename: str,
        detection: dict[str, Any],
        conversation_id: Optional[str] = None,
        message_id: Optional[str] = None,
        inner_path: Optional[str] = None,
    ) -> ProcessedFileRepresentation:
        raise NotImplementedError


class PDFAdapterV2(BaseFileAdapterV2):
    adapter_name = "PDFAdapterV2"
    supported_formats = ["pdf"]

    def get_capabilities(self) -> FileCapabilities:
        return FileCapabilities(
            canExtractText=True,
            canExtractTables=True,
            canExtractImages=True,
            canPreview=True,
            canSearch=True,
            canChunk=True,
            canInspectStructure=True,
        )

    def process(
        self,
        file_path: str,
        file_id: str,
        user_id: str,
        filename: str,
        detection: dict[str, Any],
        conversation_id: Optional[str] = None,
        message_id: Optional[str] = None,
        inner_path: Optional[str] = None,
    ) -> ProcessedFileRepresentation:
        from PyPDF2 import PdfReader

        reader = PdfReader(file_path)
        if reader.is_encrypted:
            try:
                reader.decrypt("")
            except Exception:
                raise ValueError("PDF is password-protected and encrypted.")

        pages_data: list[dict[str, Any]] = []
        full_text_parts: list[str] = []
        all_headings: list[dict[str, Any]] = []
        total_images = 0
        extracted_tables: list[dict[str, Any]] = []

        for idx, page in enumerate(reader.pages, start=1):
            raw_text = (page.extract_text() or "").strip()
            page_headings: list[str] = []
            page_tables: list[list[str]] = []

            for line in raw_text.splitlines():
                s = line.strip()
                if not s:
                    continue
                if len(s) <= 85 and (
                    re.match(r"^(?:Chapter|Section|Part|Appendix)\s+\w+", s, re.I)
                    or re.match(r"^\d+(?:\.\d+)*\s+[A-Z][A-Za-z0-9\s\-:,]{2,70}$", s)
                    or (s.isupper() and len(s) >= 4 and any(c.isalpha() for c in s))
                ):
                    page_headings.append(s)
                    all_headings.append({"page": idx, "heading": s})

                # Heuristic tabular row detection in PDF text
                if "\t" in s or re.search(r"\S+\s{3,}\S+\s{3,}\S+", s):
                    cols = [c.strip() for c in re.split(r"\t+|\s{3,}", s) if c.strip()]
                    if len(cols) >= 2:
                        page_tables.append(cols)

            img_count = 0
            try:
                if hasattr(page, "images"):
                    img_count = len(page.images)
            except Exception:
                img_count = 0
            total_images += img_count

            if len(page_tables) >= 2:
                extracted_tables.append({"page": idx, "rows": page_tables[:30]})

            pages_data.append({
                "page": idx,
                "text": raw_text,
                "char_count": len(raw_text),
                "headings": page_headings,
                "image_count": img_count,
                "has_table": len(page_tables) >= 2,
            })
            if raw_text:
                full_text_parts.append(f"--- [Page {idx}] ---\n{raw_text}")

        full_text = "\n\n".join(full_text_parts)
        chunks = StructureAwareChunker.chunk_pdf_pages(file_id, filename, pages_data)

        status = FileProcessingState.READY
        warnings: list[str] = []
        error_msg: Optional[str] = None
        if not full_text.strip():
            if len(reader.pages) > 0:
                status = FileProcessingState.PARTIAL
                warnings.append("PDF contains pages with no extractable text layer (scanned/image-only PDF).")
            else:
                status = FileProcessingState.FAILED
                error_msg = "PDF contains 0 pages or no readable content."

        return ProcessedFileRepresentation(
            fileId=file_id,
            userId=user_id,
            conversationId=conversation_id,
            messageId=message_id,
            filename=filename,
            mimeType="application/pdf",
            detectedFormat="pdf",
            extension="pdf",
            size=detection["size"],
            contentHash=compute_sha256_file(file_path),
            parserName=self.adapter_name,
            status=status,
            processingStage="Ready" if status == FileProcessingState.READY else status.value,
            error=error_msg,
            warnings=warnings,
            capabilities=self.get_capabilities(),
            fullText=full_text,
            textPreview=full_text[:1200],
            totalTokensEstimate=estimate_tokens(full_text),
            structureSummary={
                "page_count": len(reader.pages),
                "non_empty_pages": sum(1 for p in pages_data if p["text"]),
                "headings_count": len(all_headings),
                "tables_detected": len(extracted_tables),
                "images_detected": total_images,
                "headings": all_headings[:40],
            },
            structuredData={
                "pages": pages_data,
                "tables": extracted_tables[:20],
                "headings": all_headings,
            },
            chunks=chunks,
            preview={
                "type": "pdf",
                "page_count": len(reader.pages),
                "headings": all_headings[:20],
                "pages_preview": [
                    {
                        "page": p["page"],
                        "snippet": p["text"][:400],
                        "headings": p["headings"],
                    }
                    for p in pages_data[:15]
                ],
            },
            securityScan=detection["security_scan"],
            createdAt=datetime.now(timezone.utc).isoformat(),
        )


class DOCXAdapterV2(BaseFileAdapterV2):
    adapter_name = "DOCXAdapterV2"
    supported_formats = ["docx"]

    def get_capabilities(self) -> FileCapabilities:
        return FileCapabilities(
            canExtractText=True,
            canExtractTables=True,
            canPreview=True,
            canSearch=True,
            canChunk=True,
            canInspectStructure=True,
        )

    def process(
        self,
        file_path: str,
        file_id: str,
        user_id: str,
        filename: str,
        detection: dict[str, Any],
        conversation_id: Optional[str] = None,
        message_id: Optional[str] = None,
        inner_path: Optional[str] = None,
    ) -> ProcessedFileRepresentation:
        from docx import Document

        doc = Document(file_path)
        sections: list[dict[str, Any]] = []
        current_heading = "Introduction"
        current_lines: list[str] = []
        all_headings: list[str] = []
        tables_data: list[dict[str, Any]] = []
        list_items_count = 0

        for para in doc.paragraphs:
            txt = (para.text or "").strip()
            if not txt:
                continue
            style_name = (para.style.name if para.style else "") or ""
            if style_name.lower().startswith("heading") or style_name.lower() == "title":
                if current_lines:
                    sections.append({
                        "heading": current_heading,
                        "content": "\n".join(current_lines),
                    })
                    current_lines = []
                current_heading = txt
                all_headings.append(txt)
            elif "list" in style_name.lower() or txt.startswith(("•", "-", "*")):
                list_items_count += 1
                current_lines.append(f"• {txt.lstrip('•-* ')}")
            else:
                current_lines.append(txt)

        if current_lines:
            sections.append({
                "heading": current_heading,
                "content": "\n".join(current_lines),
            })

        # Extract tables
        for t_idx, table in enumerate(doc.tables, start=1):
            t_rows: list[list[str]] = []
            for row in table.rows:
                t_rows.append([cell.text.strip().replace("\n", " ") for cell in row.cells])
            if t_rows:
                tables_data.append({
                    "table_index": t_idx,
                    "headers": t_rows[0],
                    "rows": t_rows[1:],
                })
                md_lines = [f"Table {t_idx}:"]
                md_lines.append(" | ".join(t_rows[0]))
                md_lines.append(" | ".join(["---"] * len(t_rows[0])))
                for r in t_rows[1:]:
                    md_lines.append(" | ".join(r))
                sections.append({
                    "heading": f"Table {t_idx}",
                    "content": "\n".join(md_lines),
                })

        full_text = "\n\n".join(f"## {s['heading']}\n{s['content']}" for s in sections)
        chunks = StructureAwareChunker.chunk_docx_sections(file_id, filename, sections)

        status = FileProcessingState.READY if full_text.strip() else FileProcessingState.PARTIAL
        return ProcessedFileRepresentation(
            fileId=file_id,
            userId=user_id,
            conversationId=conversation_id,
            messageId=message_id,
            filename=filename,
            mimeType=detection["mime_type"],
            detectedFormat="docx",
            extension="docx",
            size=detection["size"],
            contentHash=compute_sha256_file(file_path),
            parserName=self.adapter_name,
            status=status,
            processingStage="Ready",
            capabilities=self.get_capabilities(),
            fullText=full_text,
            textPreview=full_text[:1200],
            totalTokensEstimate=estimate_tokens(full_text),
            structureSummary={
                "sections_count": len(sections),
                "headings": all_headings,
                "tables_count": len(tables_data),
                "list_items_count": list_items_count,
                "docx_sections_count": len(doc.sections),
            },
            structuredData={
                "sections": sections,
                "tables": tables_data,
                "headings": all_headings,
            },
            chunks=chunks,
            preview={
                "type": "docx",
                "headings": all_headings,
                "sections": [
                    {
                        "section_number": i + 1,
                        "heading": s["heading"],
                        "preview_text": s["content"][:350],
                        "has_table": s["heading"].startswith("Table "),
                    }
                    for i, s in enumerate(sections[:20])
                ],
                "tables": tables_data[:5],
            },
            securityScan=detection["security_scan"],
            createdAt=datetime.now(timezone.utc).isoformat(),
        )


class XLSXAdapterV2(BaseFileAdapterV2):
    adapter_name = "XLSXAdapterV2"
    supported_formats = ["xlsx", "xls"]

    def get_capabilities(self) -> FileCapabilities:
        return FileCapabilities(
            canExtractText=True,
            canExtractTables=True,
            canPreview=True,
            canSearch=True,
            canChunk=True,
            canInspectStructure=True,
        )

    def process(
        self,
        file_path: str,
        file_id: str,
        user_id: str,
        filename: str,
        detection: dict[str, Any],
        conversation_id: Optional[str] = None,
        message_id: Optional[str] = None,
        inner_path: Optional[str] = None,
    ) -> ProcessedFileRepresentation:
        import openpyxl

        wb_val = openpyxl.load_workbook(file_path, data_only=True)
        try:
            wb_formula = openpyxl.load_workbook(file_path, data_only=False)
        except Exception:
            wb_formula = None

        sheets_data: list[dict[str, Any]] = []
        full_text_parts: list[str] = []

        for sheet_name in wb_val.sheetnames:
            ws_val = wb_val[sheet_name]
            ws_form = wb_formula[sheet_name] if wb_formula and sheet_name in wb_formula.sheetnames else None

            raw_rows: list[list[Any]] = []
            formulas_found: list[dict[str, str]] = []

            max_r = min(ws_val.max_row or 0, 5000)
            max_c = min(ws_val.max_column or 0, 100)

            for r_idx in range(1, max_r + 1):
                row_vals = []
                has_any = False
                for c_idx in range(1, max_c + 1):
                    cell_v = ws_val.cell(row=r_idx, column=c_idx).value
                    if ws_form is not None:
                        cell_f = ws_form.cell(row=r_idx, column=c_idx).value
                        if isinstance(cell_f, str) and cell_f.startswith("="):
                            coord = f"{_col_index_to_letter(c_idx - 1)}{r_idx}"
                            formulas_found.append({
                                "cell": coord,
                                "formula": cell_f,
                                "evaluated": str(cell_v) if cell_v is not None else "",
                            })
                            # If data_only=True had None (un-cached formula), evaluate simple SUM/AVERAGE
                            if cell_v is None:
                                cell_v = f"{cell_f}"
                    if cell_v is not None and str(cell_v).strip() != "":
                        has_any = True
                    row_vals.append(cell_v)
                if has_any:
                    raw_rows.append(row_vals)

            if not raw_rows:
                continue

            col_count = max(len(r) for r in raw_rows)
            col_letters = [_col_index_to_letter(i) for i in range(col_count)]
            headers = [
                str(raw_rows[0][i]).strip() if i < len(raw_rows[0]) and raw_rows[0][i] is not None else f"Column_{col_letters[i]}"
                for i in range(col_count)
            ]
            data_rows = raw_rows[1:]

            # Infer column types & precompute column totals/stats
            col_stats: list[dict[str, Any]] = []
            for c_idx in range(col_count):
                col_let = col_letters[c_idx]
                hdr = headers[c_idx]
                nums: list[float] = []
                non_empty = 0
                for r in data_rows:
                    if c_idx < len(r) and r[c_idx] is not None and str(r[c_idx]).strip() != "":
                        non_empty += 1
                        num = _to_number(r[c_idx])
                        if num is not None:
                            nums.append(num)
                dtype = "numeric" if (nums and len(nums) >= max(1, non_empty // 2)) else "text"
                stat_entry: dict[str, Any] = {
                    "column": col_let,
                    "header": hdr,
                    "data_type": dtype,
                    "non_empty_count": non_empty,
                }
                if nums:
                    stat_entry.update({
                        "sum": round(sum(nums), 4),
                        "avg": round(sum(nums) / len(nums), 4),
                        "min": min(nums),
                        "max": max(nums),
                        "numeric_count": len(nums),
                    })
                col_stats.append(stat_entry)

            summary_lines = [
                f"=== Sheet: {sheet_name} (Rows: {len(data_rows)}, Columns: {col_count}) ===",
                "Columns: " + ", ".join(f"{col_letters[i]}='{headers[i]}'" for i in range(col_count)),
            ]
            for st in col_stats:
                if "sum" in st:
                    summary_lines.append(
                        f"  • Column {st['column']} ({st['header']}): SUM={st['sum']:g} ({st['sum']:,.2f}), "
                        f"AVG={st['avg']:g}, MIN={st['min']:g}, MAX={st['max']:g}, COUNT={st['numeric_count']}"
                    )
            if formulas_found:
                summary_lines.append(
                    "Formulas: " + ", ".join(f"{f['cell']}: {f['formula']} => {f['evaluated']}" for f in formulas_found[:20])
                )
            summary_text = "\n".join(summary_lines)

            serialized_rows = [
                [str(cell) if cell is not None else "" for cell in r]
                for r in data_rows
            ]

            sheets_data.append({
                "sheet_name": sheet_name,
                "headers": headers,
                "column_letters": col_letters,
                "rows": serialized_rows,
                "row_count": len(serialized_rows),
                "column_stats": col_stats,
                "formulas": formulas_found[:50],
                "summary_text": summary_text,
            })

            # Build readable sheet representation
            sheet_txt_lines = [summary_text, ""]
            for idx_r, r in enumerate(serialized_rows[:200], start=2):
                cells_str = " | ".join(
                    f"{col_letters[c]}({headers[c]})={r[c]}"
                    for c in range(min(len(r), col_count))
                    if r[c] != ""
                )
                if cells_str:
                    sheet_txt_lines.append(f"Row {idx_r}: {cells_str}")
            full_text_parts.append("\n".join(sheet_txt_lines))

        full_text = "\n\n".join(full_text_parts)
        chunks = StructureAwareChunker.chunk_spreadsheet_sheets(file_id, filename, "xlsx", sheets_data)

        return ProcessedFileRepresentation(
            fileId=file_id,
            userId=user_id,
            conversationId=conversation_id,
            messageId=message_id,
            filename=filename,
            mimeType=detection["mime_type"],
            detectedFormat="xlsx",
            extension=detection["extension"],
            size=detection["size"],
            contentHash=compute_sha256_file(file_path),
            parserName=self.adapter_name,
            status=FileProcessingState.READY if sheets_data else FileProcessingState.PARTIAL,
            processingStage="Ready",
            capabilities=self.get_capabilities(),
            fullText=full_text,
            textPreview=full_text[:1200],
            totalTokensEstimate=estimate_tokens(full_text),
            structureSummary={
                "sheet_names": [s["sheet_name"] for s in sheets_data],
                "sheets_count": len(sheets_data),
                "total_rows": sum(s["row_count"] for s in sheets_data),
            },
            structuredData={
                "sheets": sheets_data,
            },
            chunks=chunks,
            preview={
                "type": "xlsx",
                "sheets": [
                    {
                        "sheet_name": s["sheet_name"],
                        "headers": s["headers"],
                        "sample_rows": s["rows"][:15],
                        "row_count": s["row_count"],
                        "column_stats": s["column_stats"],
                    }
                    for s in sheets_data
                ],
            },
            securityScan=detection["security_scan"],
            createdAt=datetime.now(timezone.utc).isoformat(),
        )


class CSVAdapterV2(BaseFileAdapterV2):
    adapter_name = "CSVAdapterV2"
    supported_formats = ["csv", "tsv"]

    def get_capabilities(self) -> FileCapabilities:
        return FileCapabilities(
            canExtractText=True,
            canExtractTables=True,
            canPreview=True,
            canSearch=True,
            canChunk=True,
            canInspectStructure=True,
        )

    def process(
        self,
        file_path: str,
        file_id: str,
        user_id: str,
        filename: str,
        detection: dict[str, Any],
        conversation_id: Optional[str] = None,
        message_id: Optional[str] = None,
        inner_path: Optional[str] = None,
    ) -> ProcessedFileRepresentation:
        delimiter = "\t" if filename.lower().endswith(".tsv") else ","
        raw_rows: list[list[str]] = []
        with open(file_path, "r", encoding="utf-8", errors="replace", newline="") as f:
            reader = csv.reader(f, delimiter=delimiter)
            for idx, row in enumerate(reader):
                if idx >= 10000:
                    break
                if any(c.strip() for c in row):
                    raw_rows.append([c.strip() for c in row])

        if not raw_rows:
            raise ValueError("CSV file is empty or contains no valid rows.")

        col_count = max(len(r) for r in raw_rows)
        col_letters = [_col_index_to_letter(i) for i in range(col_count)]
        headers = [
            raw_rows[0][i] if i < len(raw_rows[0]) and raw_rows[0][i] else f"Column_{col_letters[i]}"
            for i in range(col_count)
        ]
        data_rows = raw_rows[1:]

        col_stats: list[dict[str, Any]] = []
        for c_idx in range(col_count):
            col_let = col_letters[c_idx]
            hdr = headers[c_idx]
            nums: list[float] = []
            non_empty = 0
            for r in data_rows:
                if c_idx < len(r) and r[c_idx] != "":
                    non_empty += 1
                    num = _to_number(r[c_idx])
                    if num is not None:
                        nums.append(num)
            dtype = "numeric" if (nums and len(nums) >= max(1, non_empty // 2)) else "text"
            stat_entry: dict[str, Any] = {
                "column": col_let,
                "header": hdr,
                "data_type": dtype,
                "non_empty_count": non_empty,
            }
            if nums:
                stat_entry.update({
                    "sum": round(sum(nums), 4),
                    "avg": round(sum(nums) / len(nums), 4),
                    "min": min(nums),
                    "max": max(nums),
                    "numeric_count": len(nums),
                })
            col_stats.append(stat_entry)

        summary_lines = [
            f"=== CSV Table: {filename} (Rows: {len(data_rows)}, Columns: {col_count}) ===",
            "Columns: " + ", ".join(f"{col_letters[i]}='{headers[i]}'" for i in range(col_count)),
        ]
        for st in col_stats:
            if "sum" in st:
                summary_lines.append(
                    f"  • Column {st['column']} ({st['header']}): SUM={st['sum']:g} ({st['sum']:,.2f}), "
                    f"AVG={st['avg']:g}, MIN={st['min']:g}, MAX={st['max']:g}, COUNT={st['numeric_count']}"
                )
        summary_text = "\n".join(summary_lines)

        sheet_obj = {
            "sheet_name": "CSV_Data",
            "headers": headers,
            "column_letters": col_letters,
            "rows": data_rows,
            "row_count": len(data_rows),
            "column_stats": col_stats,
            "formulas": [],
            "summary_text": summary_text,
        }
        sheets_data = [sheet_obj]
        chunks = StructureAwareChunker.chunk_spreadsheet_sheets(file_id, filename, "csv", sheets_data)
        full_text = "\n\n".join(c.text for c in chunks)

        return ProcessedFileRepresentation(
            fileId=file_id,
            userId=user_id,
            conversationId=conversation_id,
            messageId=message_id,
            filename=filename,
            mimeType=detection["mime_type"],
            detectedFormat="csv",
            extension=detection["extension"],
            size=detection["size"],
            contentHash=compute_sha256_file(file_path),
            parserName=self.adapter_name,
            status=FileProcessingState.READY,
            processingStage="Ready",
            capabilities=self.get_capabilities(),
            fullText=full_text,
            textPreview=full_text[:1200],
            totalTokensEstimate=estimate_tokens(full_text),
            structureSummary={
                "row_count": len(data_rows),
                "column_count": col_count,
                "headers": headers,
            },
            structuredData={
                "sheets": sheets_data,
            },
            chunks=chunks,
            preview={
                "type": "csv",
                "sheets": [
                    {
                        "sheet_name": "CSV_Data",
                        "headers": headers,
                        "sample_rows": data_rows[:15],
                        "row_count": len(data_rows),
                        "column_stats": col_stats,
                    }
                ],
            },
            securityScan=detection["security_scan"],
            createdAt=datetime.now(timezone.utc).isoformat(),
        )


class PPTXAdapterV2(BaseFileAdapterV2):
    adapter_name = "PPTXAdapterV2"
    supported_formats = ["pptx"]

    def get_capabilities(self) -> FileCapabilities:
        return FileCapabilities(
            canExtractText=True,
            canExtractTables=True,
            canExtractImages=True,
            canPreview=True,
            canSearch=True,
            canChunk=True,
            canInspectStructure=True,
        )

    def process(
        self,
        file_path: str,
        file_id: str,
        user_id: str,
        filename: str,
        detection: dict[str, Any],
        conversation_id: Optional[str] = None,
        message_id: Optional[str] = None,
        inner_path: Optional[str] = None,
    ) -> ProcessedFileRepresentation:
        from pptx import Presentation

        prs = Presentation(file_path)
        slides_data: list[dict[str, Any]] = []
        full_text_parts: list[str] = []

        for idx, slide in enumerate(prs.slides, start=1):
            title = ""
            if slide.shapes.title and slide.shapes.title.text:
                title = slide.shapes.title.text.strip()

            body_points: list[str] = []
            slide_tables: list[list[list[str]]] = []
            image_count = 0

            for shape in slide.shapes:
                if shape == slide.shapes.title:
                    continue
                if getattr(shape, "has_table", False):
                    t_rows = []
                    for r in shape.table.rows:
                        t_rows.append([c.text.strip().replace("\n", " ") for c in r.cells])
                    if t_rows:
                        slide_tables.append(t_rows)
                elif hasattr(shape, "text") and shape.text and shape.text.strip():
                    for line in shape.text.strip().splitlines():
                        if line.strip():
                            body_points.append(line.strip())
                elif getattr(shape, "shape_type", None) == 13:  # PICTURE
                    image_count += 1

            notes_text = ""
            try:
                if slide.has_notes_slide and slide.notes_slide.notes_text_frame:
                    notes_text = (slide.notes_slide.notes_text_frame.text or "").strip()
            except Exception:
                notes_text = ""

            if not title and body_points:
                title = body_points[0][:80]

            slide_lines = [f"[Slide {idx}: {title or f'Slide {idx}'}]"]
            for pt in body_points:
                slide_lines.append(f"  • {pt}")
            for t_i, tbl in enumerate(slide_tables, start=1):
                slide_lines.append(f"  [Table {t_i}]:")
                for r in tbl:
                    slide_lines.append("    | " + " | ".join(r) + " |")
            if notes_text:
                slide_lines.append(f"  [Speaker Notes]: {notes_text}")

            slide_block = "\n".join(slide_lines)
            slides_data.append({
                "slide": idx,
                "title": title or f"Slide {idx}",
                "body": body_points,
                "tables": slide_tables,
                "notes": notes_text,
                "image_count": image_count,
                "text": slide_block,
            })
            full_text_parts.append(slide_block)

        full_text = "\n\n".join(full_text_parts)
        chunks = StructureAwareChunker.chunk_pptx_slides(file_id, filename, slides_data)

        return ProcessedFileRepresentation(
            fileId=file_id,
            userId=user_id,
            conversationId=conversation_id,
            messageId=message_id,
            filename=filename,
            mimeType=detection["mime_type"],
            detectedFormat="pptx",
            extension="pptx",
            size=detection["size"],
            contentHash=compute_sha256_file(file_path),
            parserName=self.adapter_name,
            status=FileProcessingState.READY if slides_data else FileProcessingState.PARTIAL,
            processingStage="Ready",
            capabilities=self.get_capabilities(),
            fullText=full_text,
            textPreview=full_text[:1200],
            totalTokensEstimate=estimate_tokens(full_text),
            structureSummary={
                "slide_count": len(slides_data),
                "slide_titles": [s["title"] for s in slides_data],
            },
            structuredData={
                "slides": slides_data,
            },
            chunks=chunks,
            preview={
                "type": "pptx",
                "slides": [
                    {
                        "slide_number": s["slide"],
                        "title": s["title"],
                        "layout": "Standard",
                        "preview_points": s["body"][:6],
                        "notes": s["notes"][:200] if s["notes"] else None,
                    }
                    for s in slides_data
                ],
            },
            securityScan=detection["security_scan"],
            createdAt=datetime.now(timezone.utc).isoformat(),
        )


class CodeAdapterV2(BaseFileAdapterV2):
    adapter_name = "CodeAdapterV2"
    supported_formats = ["code"]

    def get_capabilities(self) -> FileCapabilities:
        return FileCapabilities(
            canExtractText=True,
            canPreview=True,
            canSearch=True,
            canChunk=True,
            canInspectStructure=True,
        )

    @staticmethod
    def extract_code_symbols(code_text: str) -> dict[str, list[str]]:
        functions = re.findall(
            r"(?:^\s*(?:async\s+)?def\s+([A-Za-z_][A-Za-z0-9_]*)|^\s*(?:export\s+)?(?:async\s+)?function\s+([A-Za-z_][A-Za-z0-9_]*)|^\s*(?:pub\s+)?fn\s+([A-Za-z_][A-Za-z0-9_]*))",
            code_text,
            re.MULTILINE,
        )
        fn_list = [next(g for g in tup if g) for tup in functions if any(tup)]

        classes = re.findall(
            r"^\s*(?:export\s+)?(?:class|interface|struct|enum)\s+([A-Za-z_][A-Za-z0-9_]*)",
            code_text,
            re.MULTILINE,
        )
        imports = re.findall(
            r"^(?:import\s+.+|from\s+\S+\s+import\s+.+|#include\s+.+|use\s+.+;)",
            code_text,
            re.MULTILINE,
        )
        return {
            "functions": list(dict.fromkeys(fn_list))[:100],
            "classes": list(dict.fromkeys(classes))[:100],
            "imports": [i.strip() for i in imports[:50]],
        }

    def process(
        self,
        file_path: str,
        file_id: str,
        user_id: str,
        filename: str,
        detection: dict[str, Any],
        conversation_id: Optional[str] = None,
        message_id: Optional[str] = None,
        inner_path: Optional[str] = None,
    ) -> ProcessedFileRepresentation:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            code_text = f.read()

        ext = "." + detection["extension"].lower() if detection.get("extension") else os.path.splitext(filename)[1].lower()
        language = CODE_EXTENSIONS.get(ext, ext.lstrip(".") or "text")
        symbols = self.extract_code_symbols(code_text)
        lines = code_text.splitlines()
        chunks = StructureAwareChunker.chunk_code_file(
            file_id=file_id,
            filename=filename,
            code_text=code_text,
            language=language,
            inner_path=inner_path,
        )

        numbered_preview = "\n".join(f"{i+1}: {line}" for i, line in enumerate(lines[:120]))

        return ProcessedFileRepresentation(
            fileId=file_id,
            userId=user_id,
            conversationId=conversation_id,
            messageId=message_id,
            filename=filename,
            mimeType=detection["mime_type"],
            detectedFormat="code",
            extension=detection["extension"],
            size=detection["size"],
            contentHash=compute_sha256_file(file_path),
            parserName=self.adapter_name,
            status=FileProcessingState.READY,
            processingStage="Ready",
            capabilities=self.get_capabilities(),
            fullText=code_text,
            textPreview=numbered_preview[:1500],
            totalTokensEstimate=estimate_tokens(code_text),
            structureSummary={
                "language": language,
                "line_count": len(lines),
                "functions": symbols["functions"],
                "classes": symbols["classes"],
                "imports_count": len(symbols["imports"]),
            },
            structuredData={
                "language": language,
                "line_count": len(lines),
                "symbols": symbols,
                "inner_path": inner_path or filename,
            },
            chunks=chunks,
            preview={
                "type": "code",
                "language": language,
                "line_count": len(lines),
                "symbols": symbols,
                "snippet": numbered_preview,
            },
            securityScan=detection["security_scan"],
            createdAt=datetime.now(timezone.utc).isoformat(),
        )


class StructuredDataAdapterV2(BaseFileAdapterV2):
    adapter_name = "StructuredDataAdapterV2"
    supported_formats = ["json", "jsonl", "xml", "yaml"]

    def get_capabilities(self) -> FileCapabilities:
        return FileCapabilities(
            canExtractText=True,
            canPreview=True,
            canSearch=True,
            canChunk=True,
            canInspectStructure=True,
        )

    def process(
        self,
        file_path: str,
        file_id: str,
        user_id: str,
        filename: str,
        detection: dict[str, Any],
        conversation_id: Optional[str] = None,
        message_id: Optional[str] = None,
        inner_path: Optional[str] = None,
    ) -> ProcessedFileRepresentation:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            raw_text = f.read()

        fmt = detection["detected_format"]
        structure_info: dict[str, Any] = {"format": fmt}

        if fmt == "json":
            parsed = json.loads(raw_text)
            if isinstance(parsed, dict):
                structure_info["root_type"] = "object"
                structure_info["keys"] = list(parsed.keys())[:100]
            elif isinstance(parsed, list):
                structure_info["root_type"] = "array"
                structure_info["length"] = len(parsed)
            formatted_text = json.dumps(parsed, indent=2, ensure_ascii=False)
        elif fmt == "jsonl":
            records = []
            for idx, line in enumerate(raw_text.splitlines(), start=1):
                if line.strip():
                    records.append(json.loads(line))
            structure_info["record_count"] = len(records)
            formatted_text = raw_text
        elif fmt == "xml":
            root = ET.fromstring(raw_text)
            structure_info["root_tag"] = root.tag
            structure_info["child_tags"] = list({child.tag for child in root})[:50]
            formatted_text = raw_text
        else:
            # YAML
            formatted_text = raw_text
            top_keys = re.findall(r"^([A-Za-z0-9_\-]+)\s*:", raw_text, re.MULTILINE)
            structure_info["keys"] = list(dict.fromkeys(top_keys))[:100]

        chunks = StructureAwareChunker.chunk_text_or_markdown(
            file_id=file_id,
            filename=filename,
            text=formatted_text,
            source_type=fmt,
            inner_path=inner_path,
        )

        return ProcessedFileRepresentation(
            fileId=file_id,
            userId=user_id,
            conversationId=conversation_id,
            messageId=message_id,
            filename=filename,
            mimeType=detection["mime_type"],
            detectedFormat=fmt,
            extension=detection["extension"],
            size=detection["size"],
            contentHash=compute_sha256_file(file_path),
            parserName=self.adapter_name,
            status=FileProcessingState.READY,
            processingStage="Ready",
            capabilities=self.get_capabilities(),
            fullText=formatted_text,
            textPreview=formatted_text[:1200],
            totalTokensEstimate=estimate_tokens(formatted_text),
            structureSummary=structure_info,
            structuredData=structure_info,
            chunks=chunks,
            preview={
                "type": fmt,
                "structure": structure_info,
                "snippet": formatted_text[:1500],
            },
            securityScan=detection["security_scan"],
            createdAt=datetime.now(timezone.utc).isoformat(),
        )


class TextMarkdownAdapterV2(BaseFileAdapterV2):
    adapter_name = "TextMarkdownAdapterV2"
    supported_formats = ["txt", "md"]

    def get_capabilities(self) -> FileCapabilities:
        return FileCapabilities(
            canExtractText=True,
            canPreview=True,
            canSearch=True,
            canChunk=True,
            canInspectStructure=True,
        )

    def process(
        self,
        file_path: str,
        file_id: str,
        user_id: str,
        filename: str,
        detection: dict[str, Any],
        conversation_id: Optional[str] = None,
        message_id: Optional[str] = None,
        inner_path: Optional[str] = None,
    ) -> ProcessedFileRepresentation:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            text = f.read()

        fmt = detection["detected_format"]
        headings = re.findall(r"^(#{1,6})\s+(.+)$", text, re.MULTILINE)
        heading_list = [h[1].strip() for h in headings]
        lines = text.splitlines()

        chunks = StructureAwareChunker.chunk_text_or_markdown(
            file_id=file_id,
            filename=filename,
            text=text,
            source_type=fmt,
            inner_path=inner_path,
        )

        return ProcessedFileRepresentation(
            fileId=file_id,
            userId=user_id,
            conversationId=conversation_id,
            messageId=message_id,
            filename=filename,
            mimeType=detection["mime_type"],
            detectedFormat=fmt,
            extension=detection["extension"],
            size=detection["size"],
            contentHash=compute_sha256_file(file_path),
            parserName=self.adapter_name,
            status=FileProcessingState.READY if text.strip() else FileProcessingState.PARTIAL,
            processingStage="Ready",
            capabilities=self.get_capabilities(),
            fullText=text,
            textPreview=text[:1200],
            totalTokensEstimate=estimate_tokens(text),
            structureSummary={
                "line_count": len(lines),
                "word_count": len(text.split()),
                "headings": heading_list[:50],
            },
            structuredData={
                "headings": heading_list,
                "line_count": len(lines),
            },
            chunks=chunks,
            preview={
                "type": fmt,
                "headings": heading_list[:25],
                "line_count": len(lines),
                "snippet": text[:1500],
            },
            securityScan=detection["security_scan"],
            createdAt=datetime.now(timezone.utc).isoformat(),
        )


class ImageAdapterV2(BaseFileAdapterV2):
    adapter_name = "ImageAdapterV2"
    supported_formats = ["image"]

    def get_capabilities(self) -> FileCapabilities:
        return FileCapabilities(
            canExtractText=True,
            canExtractImages=True,
            canPreview=True,
            canSearch=True,
            canChunk=True,
            canAnalyzeVisually=True,
            canInspectStructure=True,
        )

    def process(
        self,
        file_path: str,
        file_id: str,
        user_id: str,
        filename: str,
        detection: dict[str, Any],
        conversation_id: Optional[str] = None,
        message_id: Optional[str] = None,
        inner_path: Optional[str] = None,
    ) -> ProcessedFileRepresentation:
        from PIL import Image
        import io

        with Image.open(file_path) as img:
            img.verify()

        with Image.open(file_path) as img:
            width, height = img.size
            img_format = (img.format or "PNG").upper()
            mode = img.mode

            # Generate a compact base64 data URI (resized if needed) for visual model input & thumbnail preview
            thumb = img.copy()
            if thumb.mode not in ("RGB", "RGBA"):
                thumb = thumb.convert("RGB")
            thumb.thumbnail((1024, 1024))
            buf = io.BytesIO()
            save_fmt = "PNG" if img_format == "PNG" else "JPEG"
            if save_fmt == "JPEG" and thumb.mode == "RGBA":
                thumb = thumb.convert("RGB")
            thumb.save(buf, format=save_fmt, quality=85)
            b64_data = base64.b64encode(buf.getvalue()).decode("utf-8")
            mime = "image/png" if save_fmt == "PNG" else "image/jpeg"
            data_uri = f"data:{mime};base64,{b64_data}"

            # Optional OCR via pytesseract if installed
            ocr_text = ""
            try:
                import pytesseract
                ocr_text = (pytesseract.image_to_string(img) or "").strip()
            except Exception:
                ocr_text = ""

        desc_lines = [
            f"[Image Attachment: {filename}]",
            f"Format: {img_format} | Dimensions: {width}x{height}px | Color Mode: {mode}",
        ]
        if ocr_text:
            desc_lines.append(f"OCR Extracted Text from Image:\n{ocr_text}")

        full_text = "\n".join(desc_lines)
        cid = f"{file_id}_img_0"
        chunk = FileChunk(
            chunkId=cid,
            fileId=file_id,
            filename=filename,
            text=full_text,
            tokenEstimate=estimate_tokens(full_text) + 256,
            metadata=FileChunkMetadata(
                chunkId=cid,
                fileId=file_id,
                filename=filename,
                sourceType="image",
                section=f"{width}x{height} {img_format}",
                position=0,
            ),
        )

        return ProcessedFileRepresentation(
            fileId=file_id,
            userId=user_id,
            conversationId=conversation_id,
            messageId=message_id,
            filename=filename,
            mimeType=detection["mime_type"],
            detectedFormat="image",
            extension=detection["extension"],
            size=detection["size"],
            contentHash=compute_sha256_file(file_path),
            parserName=self.adapter_name,
            status=FileProcessingState.READY,
            processingStage="Ready",
            capabilities=self.get_capabilities(),
            fullText=full_text,
            textPreview=full_text[:600],
            totalTokensEstimate=estimate_tokens(full_text) + 256,
            structureSummary={
                "width": width,
                "height": height,
                "format": img_format,
                "mode": mode,
                "has_ocr_text": bool(ocr_text),
            },
            structuredData={
                "width": width,
                "height": height,
                "format": img_format,
                "mode": mode,
                "ocr_text": ocr_text,
                "data_uri": data_uri,
            },
            chunks=[chunk],
            preview={
                "type": "image",
                "width": width,
                "height": height,
                "format": img_format,
                "thumbnail_data_uri": data_uri,
                "ocr_text": ocr_text,
            },
            securityScan=detection["security_scan"],
            createdAt=datetime.now(timezone.utc).isoformat(),
        )


class AudioVideoAdapterV2(BaseFileAdapterV2):
    adapter_name = "AudioVideoAdapterV2"
    supported_formats = ["audio", "video"]

    def get_capabilities(self) -> FileCapabilities:
        return FileCapabilities(
            canExtractText=False,
            canPreview=True,
            canTranscribe=False,
            canInspectStructure=True,
        )

    def process(
        self,
        file_path: str,
        file_id: str,
        user_id: str,
        filename: str,
        detection: dict[str, Any],
        conversation_id: Optional[str] = None,
        message_id: Optional[str] = None,
        inner_path: Optional[str] = None,
    ) -> ProcessedFileRepresentation:
        fmt = detection["detected_format"]
        note = (
            f"Media file '{filename}' ({fmt.upper()}, {detection['size']} bytes) was uploaded and validated. "
            f"Automated audio/video transcription was not executed on this file; only container metadata is available."
        )
        cid = f"{file_id}_{fmt}_meta"
        chunk = FileChunk(
            chunkId=cid,
            fileId=file_id,
            filename=filename,
            text=note,
            tokenEstimate=estimate_tokens(note),
            metadata=FileChunkMetadata(
                chunkId=cid,
                fileId=file_id,
                filename=filename,
                sourceType=fmt,
                section="Container Metadata",
                position=0,
            ),
        )
        return ProcessedFileRepresentation(
            fileId=file_id,
            userId=user_id,
            conversationId=conversation_id,
            messageId=message_id,
            filename=filename,
            mimeType=detection["mime_type"],
            detectedFormat=fmt,
            extension=detection["extension"],
            size=detection["size"],
            contentHash=compute_sha256_file(file_path),
            parserName=self.adapter_name,
            status=FileProcessingState.PARTIAL,
            processingStage="Metadata Extracted (No Transcript)",
            warnings=[f"No transcript was extracted for {fmt} file '{filename}'. Only metadata is available."],
            capabilities=self.get_capabilities(),
            fullText=note,
            textPreview=note,
            totalTokensEstimate=estimate_tokens(note),
            structureSummary={
                "media_type": fmt,
                "size_bytes": detection["size"],
                "transcribed": False,
            },
            structuredData={
                "media_type": fmt,
                "transcribed": False,
            },
            chunks=[chunk],
            preview={
                "type": fmt,
                "size": detection["size"],
                "transcribed": False,
                "note": note,
            },
            securityScan=detection["security_scan"],
            createdAt=datetime.now(timezone.utc).isoformat(),
        )


class ArchiveAdapterV2(BaseFileAdapterV2):
    adapter_name = "ArchiveAdapterV2"
    supported_formats = ["archive"]

    def get_capabilities(self) -> FileCapabilities:
        return FileCapabilities(
            canExtractText=True,
            canExtractTables=True,
            canPreview=True,
            canSearch=True,
            canChunk=True,
            canInspectStructure=True,
        )

    def process(
        self,
        file_path: str,
        file_id: str,
        user_id: str,
        filename: str,
        detection: dict[str, Any],
        conversation_id: Optional[str] = None,
        message_id: Optional[str] = None,
        inner_path: Optional[str] = None,
    ) -> ProcessedFileRepresentation:
        is_safe, err_reason, archive_tree = validate_archive_safety(file_path)
        if not is_safe:
            raise ValueError(err_reason or "Archive failed security validation.")

        all_chunks: list[FileChunk] = []
        full_text_parts: list[str] = []
        extracted_files_summary: list[dict[str, Any]] = []

        # Create archive tree overview chunk first
        tree_lines = [f"=== Archive Inventory: {filename} ({len(archive_tree)} files) ==="]
        for item in archive_tree[:200]:
            tree_lines.append(f"  • {item['path']} ({item['type']}, {item['size']} bytes)")
        tree_text = "\n".join(tree_lines)
        full_text_parts.append(tree_text)

        tree_chunk = FileChunk(
            chunkId=f"{file_id}_archive_tree",
            fileId=file_id,
            filename=filename,
            text=tree_text,
            tokenEstimate=estimate_tokens(tree_text),
            metadata=FileChunkMetadata(
                chunkId=f"{file_id}_archive_tree",
                fileId=file_id,
                filename=filename,
                sourceType="archive",
                section="Archive Directory Tree",
                position=0,
            ),
        )
        all_chunks.append(tree_chunk)

        # Safely extract supported files into a controlled temporary directory and parse them
        with tempfile.TemporaryDirectory(prefix="hsbot_arch_") as tmpdir:
            if zipfile.is_zipfile(file_path):
                with zipfile.ZipFile(file_path, "r") as zf:
                    for info in zf.infolist()[: FILE_LIMITS.MAX_ARCHIVE_FILES]:
                        if info.is_dir() or info.file_size > 10 * 1024 * 1024:
                            continue
                        rel_path = info.filename.replace("\\", "/").lstrip("/")
                        if ".." in rel_path.split("/"):
                            continue
                        # Skip noisy build/vendor folders
                        if any(part in (".git", "node_modules", "__pycache__", ".venv", "venv", "dist", "build") for part in rel_path.split("/")):
                            continue
                        target_p = Path(tmpdir) / rel_path
                        target_p.parent.mkdir(parents=True, exist_ok=True)
                        with zf.open(info, "r") as src, open(target_p, "wb") as dst:
                            dst.write(src.read())
                        self._parse_inner_file(
                            str(target_p),
                            rel_path,
                            file_id,
                            user_id,
                            filename,
                            all_chunks,
                            full_text_parts,
                            extracted_files_summary,
                        )
            elif tarfile.is_tarfile(file_path):
                with tarfile.open(file_path, "r:*") as tf:
                    for member in tf.getmembers()[: FILE_LIMITS.MAX_ARCHIVE_FILES]:
                        if not member.isfile() or member.size > 10 * 1024 * 1024:
                            continue
                        rel_path = member.name.replace("\\", "/").lstrip("/")
                        if ".." in rel_path.split("/"):
                            continue
                        if any(part in (".git", "node_modules", "__pycache__", ".venv", "venv", "dist", "build") for part in rel_path.split("/")):
                            continue
                        target_p = Path(tmpdir) / rel_path
                        target_p.parent.mkdir(parents=True, exist_ok=True)
                        f_obj = tf.extractfile(member)
                        if f_obj:
                            with open(target_p, "wb") as dst:
                                dst.write(f_obj.read())
                            self._parse_inner_file(
                                str(target_p),
                                rel_path,
                                file_id,
                                user_id,
                                filename,
                                all_chunks,
                                full_text_parts,
                                extracted_files_summary,
                            )

        # Re-index chunk positions sequentially
        for i, ch in enumerate(all_chunks):
            ch.metadata.position = i

        full_text = "\n\n".join(full_text_parts)
        return ProcessedFileRepresentation(
            fileId=file_id,
            userId=user_id,
            conversationId=conversation_id,
            messageId=message_id,
            filename=filename,
            mimeType=detection["mime_type"],
            detectedFormat="archive",
            extension=detection["extension"],
            size=detection["size"],
            contentHash=compute_sha256_file(file_path),
            parserName=self.adapter_name,
            status=FileProcessingState.READY,
            processingStage="Ready",
            capabilities=self.get_capabilities(),
            fullText=full_text,
            textPreview=tree_text[:1500],
            totalTokensEstimate=estimate_tokens(full_text),
            structureSummary={
                "total_files_in_archive": len(archive_tree),
                "parsed_files_count": len(extracted_files_summary),
                "archive_tree": archive_tree[:150],
                "parsed_files": extracted_files_summary[:100],
            },
            structuredData={
                "archive_tree": archive_tree,
                "parsed_files": extracted_files_summary,
            },
            chunks=all_chunks,
            preview={
                "type": "archive",
                "total_files": len(archive_tree),
                "parsed_files_count": len(extracted_files_summary),
                "archive_tree": archive_tree[:100],
                "parsed_files": extracted_files_summary[:50],
            },
            securityScan=detection["security_scan"],
            createdAt=datetime.now(timezone.utc).isoformat(),
        )

    def _parse_inner_file(
        self,
        inner_abs_path: str,
        rel_path: str,
        archive_file_id: str,
        user_id: str,
        archive_filename: str,
        all_chunks: list[FileChunk],
        full_text_parts: list[str],
        extracted_files_summary: list[dict[str, Any]],
    ) -> None:
        inner_det = detect_file_type_and_validate(inner_abs_path, rel_path)
        fmt = inner_det["detected_format"]
        if fmt in ("unsupported", "archive", "image", "audio", "video") or inner_det["is_corrupt"]:
            return
        adapter = FileAdapterRegistryV2.get_adapter(fmt)
        if not adapter or isinstance(adapter, UnsupportedAdapterV2):
            return
        try:
            rep = adapter.process(
                file_path=inner_abs_path,
                file_id=archive_file_id,
                user_id=user_id,
                filename=archive_filename,
                detection=inner_det,
                inner_path=rel_path,
            )
            for ch in rep.chunks:
                ch.metadata.innerPath = rel_path
                all_chunks.append(ch)
            if rep.fullText:
                full_text_parts.append(f"=== Archive File: {rel_path} ===\n{rep.fullText}")
            extracted_files_summary.append({
                "path": rel_path,
                "format": fmt,
                "size": inner_det["size"],
                "chunks": len(rep.chunks),
                "summary": rep.structureSummary,
            })
        except Exception:
            pass


class UnsupportedAdapterV2(BaseFileAdapterV2):
    adapter_name = "UnsupportedAdapterV2"
    supported_formats = ["unsupported"]

    def get_capabilities(self) -> FileCapabilities:
        return FileCapabilities()

    def process(
        self,
        file_path: str,
        file_id: str,
        user_id: str,
        filename: str,
        detection: dict[str, Any],
        conversation_id: Optional[str] = None,
        message_id: Optional[str] = None,
        inner_path: Optional[str] = None,
    ) -> ProcessedFileRepresentation:
        ext = detection.get("extension") or os.path.splitext(filename)[1].lstrip(".") or "unknown"
        reason = f"No compatible parser is available for '.{ext}' ({detection.get('mime_type', 'unknown')})."
        return ProcessedFileRepresentation(
            fileId=file_id,
            userId=user_id,
            conversationId=conversation_id,
            messageId=message_id,
            filename=filename,
            mimeType=detection["mime_type"],
            detectedFormat="unsupported",
            extension=ext,
            size=detection["size"],
            contentHash=compute_sha256_file(file_path),
            parserName=self.adapter_name,
            status=FileProcessingState.UNSUPPORTED,
            processingStage="Unsupported",
            error=reason,
            capabilities=self.get_capabilities(),
            fullText="",
            textPreview="",
            totalTokensEstimate=0,
            structureSummary={"unsupported": True, "reason": reason},
            structuredData={},
            chunks=[],
            preview={"type": "unsupported", "reason": reason},
            securityScan=detection["security_scan"],
            createdAt=datetime.now(timezone.utc).isoformat(),
        )


class FileAdapterRegistryV2:
    """Central extensible registry mapping detected file formats to V2 adapters."""

    _adapters: dict[str, BaseFileAdapterV2] = {}

    @classmethod
    def register(cls, adapter: BaseFileAdapterV2) -> None:
        for fmt in adapter.supported_formats:
            cls._adapters[fmt.lower()] = adapter

    @classmethod
    def get_adapter(cls, detected_format: str) -> BaseFileAdapterV2:
        if not cls._adapters:
            cls._init_defaults()
        return cls._adapters.get(detected_format.lower(), UnsupportedAdapterV2())

    @classmethod
    def _init_defaults(cls) -> None:
        for adapter in [
            PDFAdapterV2(),
            DOCXAdapterV2(),
            XLSXAdapterV2(),
            CSVAdapterV2(),
            PPTXAdapterV2(),
            CodeAdapterV2(),
            StructuredDataAdapterV2(),
            TextMarkdownAdapterV2(),
            ImageAdapterV2(),
            AudioVideoAdapterV2(),
            ArchiveAdapterV2(),
            UnsupportedAdapterV2(),
        ]:
            cls.register(adapter)

    @classmethod
    def process_file(
        cls,
        file_path: str,
        file_id: str,
        user_id: str,
        original_filename: str,
        client_mime: Optional[str] = None,
        conversation_id: Optional[str] = None,
        message_id: Optional[str] = None,
    ) -> ProcessedFileRepresentation:
        detection = detect_file_type_and_validate(file_path, original_filename, client_mime)
        safe_name = detection["filename"]

        # Check if file was detected as corrupt during header/container inspection
        if detection.get("is_corrupt"):
            reason = detection.get("corrupt_reason") or f"{safe_name} could not be parsed (corrupted or malformed file)."
            return ProcessedFileRepresentation(
                fileId=file_id,
                userId=user_id,
                conversationId=conversation_id,
                messageId=message_id,
                filename=safe_name,
                mimeType=detection["mime_type"],
                detectedFormat=detection["detected_format"],
                extension=detection["extension"],
                size=detection["size"],
                contentHash=compute_sha256_file(file_path),
                parserName="SecurityAndHeaderValidatorV2",
                status=FileProcessingState.FAILED,
                processingStage="Failed",
                error=reason,
                capabilities=FileCapabilities(),
                fullText="",
                textPreview="",
                totalTokensEstimate=0,
                structureSummary={"error": reason},
                structuredData={},
                chunks=[],
                preview={"type": "error", "error": reason},
                securityScan=detection["security_scan"],
                createdAt=datetime.now(timezone.utc).isoformat(),
            )

        adapter = cls.get_adapter(detection["detected_format"])
        try:
            return adapter.process(
                file_path=file_path,
                file_id=file_id,
                user_id=user_id,
                filename=safe_name,
                detection=detection,
                conversation_id=conversation_id,
                message_id=message_id,
            )
        except Exception as e:
            reason = f"{detection['detected_format'].upper()} could not be parsed: {str(e)}"
            return ProcessedFileRepresentation(
                fileId=file_id,
                userId=user_id,
                conversationId=conversation_id,
                messageId=message_id,
                filename=safe_name,
                mimeType=detection["mime_type"],
                detectedFormat=detection["detected_format"],
                extension=detection["extension"],
                size=detection["size"],
                contentHash=compute_sha256_file(file_path),
                parserName=adapter.adapter_name,
                status=FileProcessingState.FAILED,
                processingStage="Failed",
                error=reason,
                capabilities=FileCapabilities(),
                fullText="",
                textPreview="",
                totalTokensEstimate=0,
                structureSummary={"error": reason},
                structuredData={},
                chunks=[],
                preview={"type": "error", "error": reason},
                securityScan=detection["security_scan"],
                createdAt=datetime.now(timezone.utc).isoformat(),
            )
