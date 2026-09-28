import os
import csv
import logging
from typing import Dict, List, Optional, Any
from app.services.chat_context.contracts import (
    FileCapability,
    FileProcessingState,
    DocumentChunk,
    FileAnalysisResult
)
from app.services.chat_context.file_adapters.base import BaseFileAdapter

logger = logging.getLogger("hsbot.chat_context.spreadsheet")


class SpreadsheetAdapter(BaseFileAdapter):
    capability = FileCapability.SPREADSHEET
    supported_extensions = [".xlsx", ".xls", ".csv", ".tsv", ".ods"]
    supported_mimes = [
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/vnd.ms-excel",
        "text/csv",
        "text/tab-separated-values",
        "application/vnd.oasis.opendocument.spreadsheet"
    ]

    def _estimate_tokens(self, text: str) -> int:
        return max(1, len(text) // 4)

    def _compute_column_stats(self, headers: List[str], rows: List[List[str]]) -> Dict[str, str]:
        stats = {}
        for col_idx, header in enumerate(headers):
            numeric_vals = []
            for r in rows:
                if col_idx < len(r):
                    val_str = r[col_idx].strip().replace(",", "").replace("$", "")
                    try:
                        numeric_vals.append(float(val_str))
                    except ValueError:
                        pass
            if len(numeric_vals) >= max(3, len(rows) // 2) and numeric_vals:
                tot = sum(numeric_vals)
                avg = tot / len(numeric_vals)
                stats[header] = f"Total={tot:,.2f}, Avg={avg:,.2f} (n={len(numeric_vals)})"
        return stats

    async def extract(self, file_path: str, filename: str, file_id: str) -> FileAnalysisResult:
        if not os.path.exists(file_path):
            return FileAnalysisResult(
                file_id=file_id,
                filename=filename,
                capability=self.capability,
                state=FileProcessingState.FAILED,
                error=f"File not found: {file_path}"
            )

        ext = os.path.splitext(filename)[1].lower()
        chunks: List[DocumentChunk] = []
        citations: List[str] = []
        sheet_summaries: List[str] = []
        metadata: Dict[str, Any] = {"filename": filename, "format": ext.lstrip(".").upper()}

        if ext in [".csv", ".tsv"]:
            delimiter = "\t" if ext == ".tsv" else ","
            try:
                all_rows = []
                with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                    reader = csv.reader(f, delimiter=delimiter)
                    for r in reader:
                        if any(cell.strip() for cell in r):
                            all_rows.append(r)

                if not all_rows:
                    return FileAnalysisResult(
                        file_id=file_id,
                        filename=filename,
                        capability=self.capability,
                        state=FileProcessingState.READY,
                        summary=f"Empty {ext.upper()} file.",
                        chunks=[],
                        total_tokens=0
                    )

                headers = all_rows[0]
                data_rows = all_rows[1:]
                row_count = len(data_rows)
                col_count = len(headers)
                metadata["columns"] = headers
                metadata["row_count"] = row_count

                # Compute quick numeric summary
                numeric_stats = self._compute_column_stats(headers, data_rows)

                summary_str = (
                    f"{ext.upper()} Dataset: '{filename}' ({row_count} rows, {col_count} columns).\n"
                    f"Headers: {', '.join(headers[:15])}\n"
                )
                if numeric_stats:
                    summary_str += "Summary Statistics:\n" + "\n".join(f"- {k}: {v}" for k, v in list(numeric_stats.items())[:6])

                # Batch rows into chunks of 50 rows
                batch_size = 50
                for start_idx in range(0, max(1, row_count), batch_size):
                    end_idx = min(start_idx + batch_size, row_count)
                    batch = data_rows[start_idx:end_idx]
                    table_md = [" | ".join(headers)]
                    table_md.append(" | ".join(["---"] * col_count))
                    for r in batch:
                        padded_row = r + [""] * (col_count - len(r))
                        table_md.append(" | ".join(padded_row[:col_count]))

                    batch_content = f"### {filename} (Rows {start_idx + 1} to {end_idx}):\n" + "\n".join(table_md)
                    loc = f"rows {start_idx + 1}-{end_idx}"
                    chunks.append(DocumentChunk(
                        chunk_id=f"{file_id}-r{start_idx + 1}-{end_idx}",
                        file_id=file_id,
                        source=filename,
                        location=loc,
                        section=f"Rows {start_idx + 1}-{end_idx}",
                        sheet=filename,
                        content=batch_content,
                        token_count=self._estimate_tokens(batch_content),
                        metadata={"start_row": start_idx + 1, "end_row": end_idx, "headers": headers}
                    ))
                    citations.append(f"{loc} of {filename}")

                sheet_summaries.append(summary_str)

            except Exception as e:
                return FileAnalysisResult(
                    file_id=file_id,
                    filename=filename,
                    capability=self.capability,
                    state=FileProcessingState.FAILED,
                    error=f"Error parsing CSV/TSV: {e}"
                )
        else:
            # Excel XLSX / XLS / ODS
            try:
                import openpyxl
                wb = openpyxl.load_workbook(file_path, data_only=True, read_only=True)
                sheet_names = wb.sheetnames
                metadata["sheets"] = sheet_names

                for s_name in sheet_names:
                    sheet = wb[s_name]
                    rows_data = []
                    for row in sheet.iter_rows(values_only=True):
                        if any(c is not None and str(c).strip() for c in row):
                            rows_data.append([str(c) if c is not None else "" for c in row])

                    if not rows_data:
                        continue

                    headers = rows_data[0]
                    data_rows = rows_data[1:]
                    row_count = len(data_rows)
                    col_count = len(headers)

                    numeric_stats = self._compute_column_stats(headers, data_rows)

                    summary_str = f"Sheet '{s_name}' ({row_count} rows, {col_count} columns). Headers: {', '.join(headers[:12])}"
                    if numeric_stats:
                        summary_str += " | " + "; ".join(f"{k}: {v}" for k, v in list(numeric_stats.items())[:3])
                    sheet_summaries.append(summary_str)

                    # Batch rows
                    batch_size = 50
                    for start_idx in range(0, max(1, row_count), batch_size):
                        end_idx = min(start_idx + batch_size, row_count)
                        batch = data_rows[start_idx:end_idx]
                        table_md = [" | ".join(headers)]
                        table_md.append(" | ".join(["---"] * col_count))
                        for r in batch:
                            padded_row = r + [""] * (col_count - len(r))
                            table_md.append(" | ".join(padded_row[:col_count]))

                        batch_content = f"### Sheet: {s_name} (Rows {start_idx + 1} to {end_idx}):\n" + "\n".join(table_md)
                        loc = f"sheet '{s_name}', rows {start_idx + 1}-{end_idx}"
                        chunks.append(DocumentChunk(
                            chunk_id=f"{file_id}_{s_name[:6]}-r{start_idx + 1}-{end_idx}",
                            file_id=file_id,
                            source=filename,
                            location=loc,
                            section=f"Sheet '{s_name}', Rows {start_idx + 1}-{end_idx}",
                            sheet=s_name,
                            content=batch_content,
                            token_count=self._estimate_tokens(batch_content),
                            metadata={"sheet": s_name, "start_row": start_idx + 1, "end_row": end_idx}
                        ))
                        citations.append(f"{loc} of {filename}")

                wb.close()

            except Exception as e:
                logger.error(f"Error reading Excel file: {e}")
                return FileAnalysisResult(
                    file_id=file_id,
                    filename=filename,
                    capability=self.capability,
                    state=FileProcessingState.FAILED,
                    error=f"Error reading spreadsheet: {str(e)}"
                )

        total_tokens = sum(c.token_count for c in chunks)
        summary = f"Spreadsheet: '{filename}' ({len(sheet_summaries)} sheet/table sections, ~{total_tokens} tokens).\n" + "\n".join(sheet_summaries[:4])

        return FileAnalysisResult(
            file_id=file_id,
            filename=filename,
            capability=self.capability,
            state=FileProcessingState.READY,
            summary=summary,
            chunks=chunks,
            total_tokens=total_tokens,
            metadata=metadata,
            citations=citations
        )
