import os
import json
import tempfile
import pytest
from pathlib import Path

from app.services.artifacts.adapters import (
    adapter_registry, PDFAdapter, DOCXAdapter, PPTXAdapter,
    XLSXAdapter, CSVAdapter, HTMLAdapter, SVGAdapter, ZIPAdapter
)
from app.services.artifacts.registry import PersistentArtifactRegistry
from app.services.artifacts.editor import ArtifactEditorService
from app.services.artifacts.preview import ArtifactPreviewService
from app.services.artifacts.engine import (
    UniversalArtifactEngine, ArtifactSecretScanner, SecretLeakDetectedError
)
from app.services.artifacts.tools import execute_artifact_tool, ARTIFACT_TOOL_DEFINITIONS
from app.services.document_service.service import DocumentService

# ==============================================================================
# TEST-PDF: Create PDF -> open -> parse -> validate (Section 51)
# ==============================================================================
@pytest.mark.asyncio
async def test_pdf_create_parse_validate():
    with tempfile.TemporaryDirectory() as temp_dir:
        dest_pdf = Path(temp_dir) / "test_report.pdf"
        adapter = PDFAdapter()
        res = adapter.generate(dest_pdf, "Test Security Report", "Executive Summary of AI Security")
        assert res.passed is True
        assert dest_pdf.exists()

        valid, errs = adapter.validate(dest_pdf)
        assert valid is True
        assert len(errs) == 0

        # Check magic bytes
        with open(dest_pdf, "rb") as f:
            header = f.read(5)
            assert header.startswith(b"%PDF-")

# ==============================================================================
# TEST-DOCX: Create DOCX -> reopen -> validate (Section 51)
# ==============================================================================
@pytest.mark.asyncio
async def test_docx_create_reopen_validate():
    with tempfile.TemporaryDirectory() as temp_dir:
        dest_docx = Path(temp_dir) / "test_doc.docx"
        adapter = DOCXAdapter()
        res = adapter.generate(dest_docx, "Technical Architecture", "Complete architectural breakdown.")
        assert res.passed is True
        assert dest_docx.exists()

        valid, errs = adapter.validate(dest_docx)
        assert valid is True
        assert len(errs) == 0

        import docx
        doc = docx.Document(str(dest_docx))
        assert len(doc.paragraphs) > 0

# ==============================================================================
# TEST-PPTX: Create PPTX -> reopen -> validate -> render (Section 51)
# ==============================================================================
@pytest.mark.asyncio
async def test_pptx_create_reopen_validate_render():
    with tempfile.TemporaryDirectory() as temp_dir:
        dest_pptx = Path(temp_dir) / "presentation.pptx"
        adapter = PPTXAdapter()
        content = {
            "title": "Autonomous AI Presentation",
            "slides": [
                {"title": "Introduction", "bullets": ["Overview of agent", "Key capabilities"]},
                {"title": "Architecture", "bullets": ["FastAPI backend", "Tauri desktop shell"]}
            ]
        }
        res = adapter.generate(dest_pptx, "Autonomous AI Presentation", content)
        assert res.passed is True
        assert dest_pptx.exists()

        valid, errs = adapter.validate(dest_pptx)
        assert valid is True

        import pptx
        prs = pptx.Presentation(str(dest_pptx))
        assert len(prs.slides) == 2

        prev = adapter.render_preview(dest_pptx)
        assert prev["type"] == "pptx_preview"
        assert prev["total_slides"] == 2
        assert prev["slides"][0]["title"] == "Introduction"

# ==============================================================================
# TEST-XLSX: Create XLSX -> reopen -> validate sheets/formulas (Section 51)
# ==============================================================================
@pytest.mark.asyncio
async def test_xlsx_create_sheets_formulas_validate():
    with tempfile.TemporaryDirectory() as temp_dir:
        dest_xlsx = Path(temp_dir) / "financials.xlsx"
        adapter = XLSXAdapter()
        content = {
            "sheets": [
                {"name": "Dashboard", "data": [["Metric", "Value"], ["Total Users", 15000], ["MRR", "$45,000"]]},
                {"name": "Expenses", "data": [["Category", "Amount"], ["Cloud", 1200], ["Bandwidth", 400]]}
            ]
        }
        res = adapter.generate(dest_xlsx, "Financial Model", content)
        assert res.passed is True
        assert dest_xlsx.exists()

        valid, errs = adapter.validate(dest_xlsx)
        assert valid is True

        import openpyxl
        wb = openpyxl.load_workbook(str(dest_xlsx))
        assert "Dashboard" in wb.sheetnames
        assert "Expenses" in wb.sheetnames

        prev = adapter.render_preview(dest_xlsx)
        assert prev["type"] == "xlsx_preview"
        assert len(prev["sheets"]) == 2

# ==============================================================================
# TEST-CSV: Create CSV -> reopen -> validate rows/columns (Section 51)
# ==============================================================================
@pytest.mark.asyncio
async def test_csv_create_reopen_validate():
    with tempfile.TemporaryDirectory() as temp_dir:
        dest_csv = Path(temp_dir) / "data.csv"
        adapter = CSVAdapter()
        content = [
            ["ID", "Name", "Status"],
            ["1", "Alice", "Active"],
            ["2", "Bob", "Pending"]
        ]
        res = adapter.generate(dest_csv, "User Data", content)
        assert res.passed is True
        assert dest_csv.exists()

        valid, errs = adapter.validate(dest_csv)
        assert valid is True

        lines = dest_csv.read_text(encoding="utf-8").splitlines()
        assert len(lines) == 3
        assert "Alice" in lines[1]

# ==============================================================================
# TEST-HTML & SVG: Validate render and sandbox safety (Section 51)
# ==============================================================================
@pytest.mark.asyncio
async def test_html_and_svg_validation():
    with tempfile.TemporaryDirectory() as temp_dir:
        # HTML
        dest_html = Path(temp_dir) / "index.html"
        html_adapter = HTMLAdapter()
        h_res = html_adapter.generate(dest_html, "Dashboard", "<div id='root'><h1>Dashboard</h1></div>")
        assert h_res.passed is True
        assert dest_html.exists()
        h_valid, _ = html_adapter.validate(dest_html)
        assert h_valid is True

        # SVG
        dest_svg = Path(temp_dir) / "diagram.svg"
        svg_adapter = SVGAdapter()
        s_res = svg_adapter.generate(dest_svg, "Architecture Diagram", "<circle cx='50' cy='50' r='40' fill='blue'/>")
        assert s_res.passed is True
        assert dest_svg.exists()
        s_valid, _ = svg_adapter.validate(dest_svg)
        assert s_valid is True

# ==============================================================================
# TEST-ZIP: Create ZIP -> reopen -> integrity check (Section 51 & 32)
# ==============================================================================
@pytest.mark.asyncio
async def test_zip_create_integrity_check():
    with tempfile.TemporaryDirectory() as temp_dir:
        dest_zip = Path(temp_dir) / "bundle.zip"
        adapter = ZIPAdapter()
        content = {
            "index.html": "<!DOCTYPE html><html><body>Test</body></html>",
            "styles.css": "body { margin: 0; }",
            "README.md": "# Project Title"
        }
        res = adapter.generate(dest_zip, "Project Bundle", content)
        assert res.passed is True
        assert dest_zip.exists()

        valid, errs = adapter.validate(dest_zip)
        assert valid is True
        assert len(errs) == 0

        # Preview
        prev = adapter.render_preview(dest_zip)
        assert prev["type"] == "zip_preview"
        assert prev["total_files"] == 3

# ==============================================================================
# TEST-VERSION: Create v1 -> edit -> verify v2 -> restore v1 (Section 20 & 51)
# ==============================================================================
@pytest.mark.asyncio
async def test_artifact_version_and_restore():
    with tempfile.TemporaryDirectory() as temp_dir:
        reg = PersistentArtifactRegistry(storage_dir=temp_dir)
        editor = ArtifactEditorService(registry=reg)

        src_file = Path(temp_dir) / "notes.md"
        src_file.write_text("# Project Notes\nInitial version content.", encoding="utf-8")

        art = reg.register_artifact(
            filename="notes.md",
            file_path=src_file,
            artifact_type="md",
            mime_type="text/markdown"
        )
        assert art.version == 1

        # Edit to create v2
        success, updated_art, msg = await editor.edit_artifact(
            artifact_id=art.artifact_id,
            instruction="Add Section 2 for Deployment Instructions"
        )
        assert success is True
        assert updated_art.version == 2
        assert len(updated_art.versions) == 2

        # Restore v1
        restored_art = reg.restore_version(art.artifact_id, 1)
        assert restored_art is not None
        assert restored_art.version == 3
        assert "Restored from version 1" in restored_art.versions[-1].change_description

# ==============================================================================
# TEST-SECURITY: Insert simulated secret -> ensure delivery blocked (Section 27 & 51)
# ==============================================================================
@pytest.mark.asyncio
async def test_secret_scanner_blocks_delivery():
    scanner = ArtifactSecretScanner()

    # Clean text
    clean_leak = scanner.scan_text("This is public documentation and safe code.")
    assert clean_leak is None

    # Leaked NVIDIA Key
    leak_nvidia = scanner.scan_text("API key: nvapi-abcdef1234567890abcdef1234567890")
    assert leak_nvidia is not None
    assert "NVIDIA" in leak_nvidia

    # Leaked OpenAI Key
    leak_openai = scanner.scan_text("sk-proj-123456789012345678901234567890")
    assert leak_openai is not None

# ==============================================================================
# TEST-TOOLS: Execute 14 tools via execute_artifact_tool (Section 2 & 39)
# ==============================================================================
@pytest.mark.asyncio
async def test_artifact_tools_execution():
    assert len(ARTIFACT_TOOL_DEFINITIONS) == 14

    # Test create_file tool
    res_file = await execute_artifact_tool("create_file", {
        "path": "test_script.py",
        "content": "print('running via create_file tool')\n"
    })
    assert res_file.get("success") is True

    # Test create_artifact tool
    res_art = await execute_artifact_tool("create_artifact", {
        "artifact_type": "csv",
        "filename": "metrics.csv",
        "content": [["A", "B"], [1, 2]],
        "title": "Metrics Summary"
    })
    assert res_art.get("success") is True
    art_id = res_art["artifact"]["artifact_id"]

    # Test inspect_artifact tool
    res_inspect = await execute_artifact_tool("inspect_artifact", {"artifact_id": art_id})
    assert res_inspect.get("success") is True
    assert res_inspect["filename"] == "metrics.csv"

    # Test validate_artifact tool
    res_val = await execute_artifact_tool("validate_artifact", {"artifact_id": art_id})
    assert res_val.get("success") is True
    assert res_val.get("valid") is True

    # Test render_artifact tool
    res_render = await execute_artifact_tool("render_artifact", {"artifact_id": art_id})
    assert res_render.get("success") is True

    # Test download_artifact tool
    res_dl = await execute_artifact_tool("download_artifact", {"artifact_id": art_id})
    assert res_dl.get("success") is True
    assert "download_url" in res_dl

    # Test list_artifacts tool
    res_list = await execute_artifact_tool("list_artifacts", {})
    assert res_list.get("success") is True
    assert len(res_list["artifacts"]) >= 1

# ==============================================================================
# TEST-MULTI-INTENT: Compound prompt detection (Section 19 & 52)
# ==============================================================================
def test_detect_multiple_intents():
    prompt = "Create a project report with PDF, DOCX, and PPTX presentation about AI Security"
    intents = DocumentService.detect_multiple_intents(prompt)
    assert len(intents) == 3
    formats = {i.format for i in intents}
    assert formats == {"pdf", "docx", "pptx"}
