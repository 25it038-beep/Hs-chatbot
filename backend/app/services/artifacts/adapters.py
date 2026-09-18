import io
import os
import re
import json
import zipfile
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from abc import ABC, abstractmethod

from app.services.artifacts.models import ArtifactCategory
from app.services.document_service.service import MIME_TYPES
from app.services.document_service.pdf import generate_pdf, generate_simple_pdf
from app.services.document_service.docx import generate_docx, generate_simple_docx
from app.services.document_service.pptx import generate_pptx, generate_simple_pptx
from app.services.document_service.xlsx import generate_xlsx, generate_simple_xlsx
from app.services.document_service.csv import generate_csv
from app.services.document_service.markdown import generate_markdown, generate_simple_markdown

class FileTypeAdapter(ABC):
    """Abstract base class for all file type adapters in the Artifact Engine."""
    extension: str = ""
    mime_type: str = "application/octet-stream"
    category: ArtifactCategory = ArtifactCategory.OTHER

    can_create: bool = True
    can_edit: bool = True
    can_validate: bool = True
    can_render: bool = True
    can_convert: bool = False

    @abstractmethod
    async def generate(self, target_path: Path, title: str, content: Any, options: Optional[Dict[str, Any]] = None) -> bool:
        pass

    @abstractmethod
    def validate(self, file_path: Path) -> Tuple[bool, List[str]]:
        pass

    @abstractmethod
    def render_preview(self, file_path: Path) -> Dict[str, Any]:
        pass

    def edit(self, file_path: Path, instruction: str, target: Optional[str] = None) -> bool:
        return False

    def convert(self, source_path: Path, target_extension: str, output_path: Path) -> bool:
        return False

# ==========================================
# 1. PDF Adapter
# ==========================================
class PDFAdapter(FileTypeAdapter):
    extension = "pdf"
    mime_type = "application/pdf"
    category = ArtifactCategory.DOCUMENT
    can_convert = True

    async def generate(self, target_path: Path, title: str, content: Any, options: Optional[Dict[str, Any]] = None) -> bool:
        from app.services.document_service.design_system import infer_design_spec
        spec = infer_design_spec(topic=title, doc_format="pdf")
        target_path.parent.mkdir(parents=True, exist_ok=True)

        if isinstance(content, dict):
            return generate_pdf(content, str(target_path), spec)
        elif isinstance(content, str):
            return generate_simple_pdf(title, content, str(target_path), spec)
        else:
            return generate_simple_pdf(title, str(content), str(target_path), spec)

    def validate(self, file_path: Path) -> Tuple[bool, List[str]]:
        errors = []
        if not file_path.exists() or file_path.stat().st_size < 100:
            return False, ["PDF file is empty or missing"]
        with open(file_path, "rb") as f:
            header = f.read(5)
            if not header.startswith(b"%PDF-"):
                errors.append("Invalid PDF magic bytes")
        return len(errors) == 0, errors

    def render_preview(self, file_path: Path) -> Dict[str, Any]:
        size_kb = round(file_path.stat().st_size / 1024, 1)
        return {
            "type": "pdf_preview",
            "filename": file_path.name,
            "size_kb": size_kb,
            "pages_estimated": max(1, int(size_kb // 8)),
            "supports_direct_view": True
        }

# ==========================================
# 2. DOCX Adapter
# ==========================================
class DOCXAdapter(FileTypeAdapter):
    extension = "docx"
    mime_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    category = ArtifactCategory.DOCUMENT
    can_convert = True

    async def generate(self, target_path: Path, title: str, content: Any, options: Optional[Dict[str, Any]] = None) -> bool:
        from app.services.document_service.design_system import infer_design_spec
        spec = infer_design_spec(topic=title, doc_format="docx")
        target_path.parent.mkdir(parents=True, exist_ok=True)

        if isinstance(content, dict):
            return generate_docx(content, str(target_path), spec)
        else:
            return generate_simple_docx(title, str(content), str(target_path), spec)

    def validate(self, file_path: Path) -> Tuple[bool, List[str]]:
        errors = []
        if not file_path.exists() or file_path.stat().st_size < 500:
            return False, ["DOCX file missing or too small"]
        try:
            import docx
            doc = docx.Document(str(file_path))
            if len(doc.paragraphs) == 0 and len(doc.tables) == 0:
                errors.append("DOCX has no paragraphs or tables")
        except Exception as e:
            errors.append(f"DOCX corrupt: {e}")
        return len(errors) == 0, errors

    def render_preview(self, file_path: Path) -> Dict[str, Any]:
        try:
            import docx
            doc = docx.Document(str(file_path))
            headings = [p.text for p in doc.paragraphs if p.style.name.startswith("Heading") and p.text.strip()]
            first_paragraphs = [p.text for p in doc.paragraphs if p.text.strip()][:5]
            return {
                "type": "docx_preview",
                "headings": headings[:10],
                "paragraphs_count": len(doc.paragraphs),
                "tables_count": len(doc.tables),
                "sample_text": "\n\n".join(first_paragraphs)
            }
        except Exception:
            return {"type": "docx_preview", "headings": [], "paragraphs_count": 0}

# ==========================================
# 3. PPTX Adapter (with targeted slide editing)
# ==========================================
class PPTXAdapter(FileTypeAdapter):
    extension = "pptx"
    mime_type = "application/vnd.openxmlformats-officedocument.presentationml.presentation"
    category = ArtifactCategory.PRESENTATION

    async def generate(self, target_path: Path, title: str, content: Any, options: Optional[Dict[str, Any]] = None) -> bool:
        from app.services.document_service.design_system import infer_design_spec
        spec = infer_design_spec(topic=title, doc_format="pptx")
        target_path.parent.mkdir(parents=True, exist_ok=True)

        if isinstance(content, dict):
            return generate_pptx(content, str(target_path), spec)
        else:
            return generate_simple_pptx(title, str(content), str(target_path), spec)

    def validate(self, file_path: Path) -> Tuple[bool, List[str]]:
        errors = []
        if not file_path.exists():
            return False, ["PPTX file missing"]
        try:
            import pptx
            prs = pptx.Presentation(str(file_path))
            if len(prs.slides) == 0:
                errors.append("Presentation contains 0 slides")
        except Exception as e:
            errors.append(f"PPTX corrupt: {e}")
        return len(errors) == 0, errors

    def render_preview(self, file_path: Path) -> Dict[str, Any]:
        try:
            import pptx
            prs = pptx.Presentation(str(file_path))
            slides_data = []
            for idx, slide in enumerate(prs.slides, start=1):
                title_text = f"Slide {idx}"
                bullets = []
                for shape in slide.shapes:
                    if shape.has_text_frame:
                        text = shape.text_frame.text.strip()
                        if text:
                            lines = [l.strip() for l in text.splitlines() if l.strip()]
                            if lines:
                                if title_text == f"Slide {idx}":
                                    title_text = lines[0]
                                bullets.extend(lines[1:])
                slides_data.append({
                    "slide_number": idx,
                    "title": title_text,
                    "bullets": bullets[:4]
                })
            return {
                "type": "pptx_preview",
                "total_slides": len(prs.slides),
                "slides": slides_data
            }
        except Exception:
            return {"type": "pptx_preview", "total_slides": 0, "slides": []}

    def edit(self, file_path: Path, instruction: str, target: Optional[str] = None) -> bool:
        """Incremental targeted editing of a specific slide in PPTX."""
        try:
            import pptx
            prs = pptx.Presentation(str(file_path))
            slide_idx = 0
            # Check if a slide number is specified (e.g. "slide 4")
            m = re.search(r"slide\s+(\d+)", instruction.lower()) or (re.search(r"slide\s+(\d+)", target.lower()) if target else None)
            if m:
                slide_num = int(m.group(1))
                if 1 <= slide_num <= len(prs.slides):
                    slide_idx = slide_num - 1

            target_slide = prs.slides[slide_idx]
            # Add updated card or note shape
            for shape in target_slide.shapes:
                if shape.has_text_frame:
                    shape.text_frame.text += f"\n• Updated: {instruction}"
                    break
            prs.save(str(file_path))
            return True
        except Exception:
            return False

# ==========================================
# 4. XLSX Adapter (with multi-sheet & formulas)
# ==========================================
class XLSXAdapter(FileTypeAdapter):
    extension = "xlsx"
    mime_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    category = ArtifactCategory.SPREADSHEET

    async def generate(self, target_path: Path, title: str, content: Any, options: Optional[Dict[str, Any]] = None) -> bool:
        from app.services.document_service.design_system import infer_design_spec
        spec = infer_design_spec(topic=title, doc_format="xlsx")
        target_path.parent.mkdir(parents=True, exist_ok=True)

        if isinstance(content, dict):
            return generate_xlsx(content, str(target_path), spec)
        else:
            return generate_simple_xlsx(title, str(content), str(target_path), spec)

    def validate(self, file_path: Path) -> Tuple[bool, List[str]]:
        errors = []
        if not file_path.exists():
            return False, ["XLSX file missing"]
        try:
            import openpyxl
            wb = openpyxl.load_workbook(str(file_path), data_only=False)
            if len(wb.sheetnames) == 0:
                errors.append("Workbook has 0 worksheets")
        except Exception as e:
            errors.append(f"XLSX corrupt: {e}")
        return len(errors) == 0, errors

    def render_preview(self, file_path: Path) -> Dict[str, Any]:
        try:
            import openpyxl
            wb = openpyxl.load_workbook(str(file_path), data_only=True)
            sheets_preview = []
            for sheetname in wb.sheetnames:
                ws = wb[sheetname]
                rows_data = []
                for r_idx, row in enumerate(ws.iter_rows(values_only=True), start=1):
                    if r_idx > 8:
                        break
                    filtered_row = [str(cell) if cell is not None else "" for cell in row[:6]]
                    if any(filtered_row):
                        rows_data.append(filtered_row)
                sheets_preview.append({
                    "sheet_name": sheetname,
                    "rows": rows_data
                })
            return {
                "type": "xlsx_preview",
                "sheet_names": wb.sheetnames,
                "sheets": sheets_preview
            }
        except Exception:
            return {"type": "xlsx_preview", "sheet_names": [], "sheets": []}

# ==========================================
# 5. CSV Adapter
# ==========================================
class CSVAdapter(FileTypeAdapter):
    extension = "csv"
    mime_type = "text/csv"
    category = ArtifactCategory.DATA

    async def generate(self, target_path: Path, title: str, content: Any, options: Optional[Dict[str, Any]] = None) -> bool:
        target_path.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(content, dict):
            return generate_csv(content, str(target_path))
        elif isinstance(content, str):
            target_path.write_text(content, encoding="utf-8")
            return True
        return False

    def validate(self, file_path: Path) -> Tuple[bool, List[str]]:
        errors = []
        if not file_path.exists() or file_path.stat().st_size == 0:
            return False, ["CSV file empty or missing"]
        return True, []

    def render_preview(self, file_path: Path) -> Dict[str, Any]:
        lines = file_path.read_text(encoding="utf-8", errors="ignore").splitlines()[:10]
        rows = [l.split(",") for l in lines]
        return {
            "type": "csv_preview",
            "headers": rows[0] if rows else [],
            "rows": rows[1:] if len(rows) > 1 else []
        }

# ==========================================
# 6. HTML & Web Adapter
# ==========================================
class HTMLAdapter(FileTypeAdapter):
    extension = "html"
    mime_type = "text/html"
    category = ArtifactCategory.WEB

    async def generate(self, target_path: Path, title: str, content: Any, options: Optional[Dict[str, Any]] = None) -> bool:
        target_path.parent.mkdir(parents=True, exist_ok=True)
        html_str = str(content)
        if not html_str.strip().startswith("<!DOCTYPE") and not html_str.strip().startswith("<html"):
            html_str = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{title}</title>
  <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-slate-50 text-slate-900 p-8">
  <div class="max-w-4xl mx-auto bg-white p-8 rounded-2xl shadow-sm border border-slate-200">
    <h1 class="text-3xl font-bold mb-4">{title}</h1>
    {html_str}
  </div>
</body>
</html>"""
        target_path.write_text(html_str, encoding="utf-8")
        return True

    def validate(self, file_path: Path) -> Tuple[bool, List[str]]:
        if not file_path.exists():
            return False, ["HTML file missing"]
        text = file_path.read_text(encoding="utf-8", errors="ignore")
        if "<body" not in text and "<div" not in text:
            return False, ["HTML has no body or div tags"]
        return True, []

    def render_preview(self, file_path: Path) -> Dict[str, Any]:
        text = file_path.read_text(encoding="utf-8", errors="ignore")
        return {
            "type": "html_preview",
            "html_snippet": text[:5000],
            "supports_live_preview": True
        }

# ==========================================
# 7. SVG Adapter
# ==========================================
class SVGAdapter(FileTypeAdapter):
    extension = "svg"
    mime_type = "image/svg+xml"
    category = ArtifactCategory.DIAGRAM

    async def generate(self, target_path: Path, title: str, content: Any, options: Optional[Dict[str, Any]] = None) -> bool:
        target_path.parent.mkdir(parents=True, exist_ok=True)
        svg_str = str(content).strip()
        if not svg_str.startswith("<svg"):
            svg_str = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 500" width="800" height="500"><text x="40" y="60" font-size="24" fill="#0f172a">{title}</text>{svg_str}</svg>'
        target_path.write_text(svg_str, encoding="utf-8")
        return True

    def validate(self, file_path: Path) -> Tuple[bool, List[str]]:
        if not file_path.exists():
            return False, ["SVG missing"]
        text = file_path.read_text(encoding="utf-8", errors="ignore")
        if "<svg" not in text or "</svg>" not in text:
            return False, ["Invalid SVG structure"]
        return True, []

    def render_preview(self, file_path: Path) -> Dict[str, Any]:
        svg_content = file_path.read_text(encoding="utf-8", errors="ignore")
        return {
            "type": "svg_preview",
            "svg_content": svg_content
        }

# ==========================================
# 8. Markdown Adapter
# ==========================================
class MarkdownAdapter(FileTypeAdapter):
    extension = "md"
    mime_type = "text/markdown"
    category = ArtifactCategory.DOCUMENT

    async def generate(self, target_path: Path, title: str, content: Any, options: Optional[Dict[str, Any]] = None) -> bool:
        target_path.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(content, dict):
            return generate_markdown(content, str(target_path))
        else:
            return generate_simple_markdown(title, str(content), str(target_path))

    def validate(self, file_path: Path) -> Tuple[bool, List[str]]:
        if not file_path.exists() or file_path.stat().st_size == 0:
            return False, ["Markdown file missing or empty"]
        return True, []

    def render_preview(self, file_path: Path) -> Dict[str, Any]:
        text = file_path.read_text(encoding="utf-8", errors="ignore")
        return {
            "type": "markdown_preview",
            "markdown": text[:8000]
        }

# ==========================================
# 9. Code Adapter (.py, .ts, .tsx, .js, .sql)
# ==========================================
class CodeAdapter(FileTypeAdapter):
    category = ArtifactCategory.CODE

    def __init__(self, extension: str, mime: str = "text/plain"):
        self.extension = extension
        self.mime_type = mime

    async def generate(self, target_path: Path, title: str, content: Any, options: Optional[Dict[str, Any]] = None) -> bool:
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_text(str(content), encoding="utf-8")
        return True

    def validate(self, file_path: Path) -> Tuple[bool, List[str]]:
        if not file_path.exists() or file_path.stat().st_size == 0:
            return False, ["Code file missing or empty"]
        if file_path.suffix == ".py":
            import ast
            try:
                ast.parse(file_path.read_text(encoding="utf-8"))
            except SyntaxError as e:
                return False, [f"Python syntax error: {e}"]
        return True, []

    def render_preview(self, file_path: Path) -> Dict[str, Any]:
        text = file_path.read_text(encoding="utf-8", errors="ignore")
        return {
            "type": "code_preview",
            "language": self.extension,
            "code": text[:10000],
            "total_lines": len(text.splitlines())
        }

# ==========================================
# 10. ZIP Adapter
# ==========================================
class ZIPAdapter(FileTypeAdapter):
    extension = "zip"
    mime_type = "application/zip"
    category = ArtifactCategory.ARCHIVE

    async def generate(self, target_path: Path, title: str, content: Any, options: Optional[Dict[str, Any]] = None) -> bool:
        # Content can be directory path or dict of files
        target_path.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(target_path, "w", zipfile.ZIP_DEFLATED) as zf:
            if isinstance(content, (str, Path)) and Path(content).is_dir():
                src_dir = Path(content)
                for root, _, files in os.walk(src_dir):
                    for f in files:
                        p = Path(root) / f
                        zf.write(p, p.relative_to(src_dir))
            elif isinstance(content, dict):
                for filename, file_content in content.items():
                    zf.writestr(filename, str(file_content))
            return True

    def validate(self, file_path: Path) -> Tuple[bool, List[str]]:
        if not file_path.exists():
            return False, ["ZIP missing"]
        try:
            with zipfile.ZipFile(file_path, "r") as zf:
                bad_file = zf.testzip()
                if bad_file:
                    return False, [f"Corrupt ZIP member: {bad_file}"]
        except Exception as e:
            return False, [f"Corrupt ZIP: {e}"]
        return True, []

    def render_preview(self, file_path: Path) -> Dict[str, Any]:
        try:
            with zipfile.ZipFile(file_path, "r") as zf:
                members = [{"name": info.filename, "size": info.file_size} for info in zf.infolist()[:25]]
                return {
                    "type": "zip_preview",
                    "total_files": len(zf.infolist()),
                    "files": members
                }
        except Exception:
            return {"type": "zip_preview", "total_files": 0, "files": []}

# ==========================================
# Adapter Registry
# ==========================================
class AdapterRegistry:
    def __init__(self):
        self._adapters: Dict[str, FileTypeAdapter] = {
            "pdf": PDFAdapter(),
            "docx": DOCXAdapter(),
            "pptx": PPTXAdapter(),
            "xlsx": XLSXAdapter(),
            "csv": CSVAdapter(),
            "html": HTMLAdapter(),
            "svg": SVGAdapter(),
            "md": MarkdownAdapter(),
            "zip": ZIPAdapter(),
            "py": CodeAdapter("py", "text/x-python"),
            "ts": CodeAdapter("ts", "application/typescript"),
            "tsx": CodeAdapter("tsx", "application/typescript"),
            "js": CodeAdapter("js", "application/javascript"),
            "jsx": CodeAdapter("jsx", "application/javascript"),
            "json": CodeAdapter("json", "application/json"),
            "sql": CodeAdapter("sql", "application/sql"),
            "txt": CodeAdapter("txt", "text/plain"),
        }

    def get(self, extension: str) -> Optional[FileTypeAdapter]:
        ext = extension.lower().lstrip(".")
        return self._adapters.get(ext)

adapter_registry = AdapterRegistry()
