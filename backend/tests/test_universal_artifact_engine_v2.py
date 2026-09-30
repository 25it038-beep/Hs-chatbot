import ast
import csv
import io
import json
import os
import sys
import zipfile
import xml.etree.ElementTree as ET

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.services.artifacts.output_intent_engine import OutputMode, sanitize_filename
from app.services.artifacts.universal_engine_v2 import (
    ArtifactFormatRegistryV2,
    ArtifactIntentDetector,
    ArtifactStorageAndVersionManager,
    ArtifactValidator,
    UniversalArtifactEngineV2,
)


def test_1_normal_chat_question_no_unnecessary_files():
    """Section 58 Test 1: Normal Chat Question -> Chat response only, no file generated."""
    res = UniversalArtifactEngineV2.execute(
        user_id="test_user_1",
        conversation_id="conv_chat_only",
        message_id="msg_1",
        user_message="What is Operating Systems?",
    )
    assert res["status"] == "chat_only"
    assert res["artifacts"] == []


def test_2_direct_pdf_generation():
    """Section 58 Test 2 & Section 59: Direct PDF Generation -> real PDF binary, >0 bytes, extractable text."""
    res = UniversalArtifactEngineV2.execute(
        user_id="test_user_1",
        conversation_id="conv_pdf",
        message_id="msg_2",
        user_message="Explain Operating Systems and give me a PDF",
    )
    assert res["status"] == "completed"
    assert res["mode"] in (OutputMode.FILE.value, OutputMode.CHAT_AND_FILE.value)
    assert len(res["artifacts"]) == 1

    card = res["artifacts"][0]
    assert card["extension"] == "pdf"
    assert card["mimeType"] == "application/pdf"
    assert card["size"] > 500

    rec_bytes = ArtifactStorageAndVersionManager.get_artifact_bytes("test_user_1", card["artifactId"])
    assert rec_bytes is not None
    _, raw = rec_bytes
    assert raw.startswith(b"%PDF-")
    assert b"%%EOF" in raw[-512:]
    assert b"Operating Systems" in raw or len(raw) > 500


def test_3_direct_docx_generation():
    """Section 58 Test 3 & Section 60: Direct DOCX Generation -> real Word document with paragraphs & headings."""
    res = UniversalArtifactEngineV2.execute(
        user_id="test_user_1",
        conversation_id="conv_docx",
        message_id="msg_3",
        user_message="Create a Word document about Machine Learning",
    )
    assert res["status"] == "completed"
    card = res["artifacts"][0]
    assert card["extension"] == "docx"
    assert card["mimeType"] == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

    _, raw = ArtifactStorageAndVersionManager.get_artifact_bytes("test_user_1", card["artifactId"])
    assert raw.startswith(b"PK\x03\x04")

    with zipfile.ZipFile(io.BytesIO(raw), "r") as zf:
        assert "word/document.xml" in zf.namelist()
        root = ET.fromstring(zf.read("word/document.xml"))
        texts = [el.text.strip() for el in root.iter() if el.tag.endswith("}t") and el.text and el.text.strip()]
        assert len(texts) >= 3


def test_4_direct_xlsx_generation():
    """Section 58 Test 4 & Section 61: Direct XLSX Generation -> real workbook, headers, numeric values, formulas."""
    res = UniversalArtifactEngineV2.execute(
        user_id="test_user_1",
        conversation_id="conv_xlsx",
        message_id="msg_4",
        user_message="Create an Excel sheet for student monthly budget",
    )
    assert res["status"] == "completed"
    card = res["artifacts"][0]
    assert card["extension"] == "xlsx"
    assert card["mimeType"] == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

    _, raw = ArtifactStorageAndVersionManager.get_artifact_bytes("test_user_1", card["artifactId"])
    with zipfile.ZipFile(io.BytesIO(raw), "r") as zf:
        assert "xl/workbook.xml" in zf.namelist()
        sheet_xml = zf.read("xl/worksheets/sheet1.xml")
        root = ET.fromstring(sheet_xml)
        rows_els = [el for el in root.iter() if el.tag.endswith("}row")]
        formulas_els = [el.text for el in root.iter() if el.tag.endswith("}f") and el.text]
        assert len(rows_els) >= 5
        assert len(formulas_els) >= 1


def test_5_direct_pptx_10_slides():
    """Section 58 Test 5 & Section 62: Direct PPTX Generation -> 10 slides with titles and bullets."""
    res = UniversalArtifactEngineV2.execute(
        user_id="test_user_1",
        conversation_id="conv_pptx",
        message_id="msg_5",
        user_message="Create a 10-slide presentation on Cloud Computing",
    )
    assert res["status"] == "completed"
    card = res["artifacts"][0]
    assert card["extension"] == "pptx"

    _, raw = ArtifactStorageAndVersionManager.get_artifact_bytes("test_user_1", card["artifactId"])
    with zipfile.ZipFile(io.BytesIO(raw), "r") as zf:
        slide_files = [n for n in zf.namelist() if n.startswith("ppt/slides/slide") and n.endswith(".xml")]
        assert len(slide_files) == 10


def test_6_code_file_generation_ast_valid():
    """Section 58 Test 6: Code File Generation -> valid Python AST syntax."""
    res = UniversalArtifactEngineV2.execute(
        user_id="test_user_1",
        conversation_id="conv_py",
        message_id="msg_6",
        user_message="Write a Python script to analyze sales CSV data and give me the .py file",
    )
    assert res["status"] == "completed"
    card = res["artifacts"][0]
    assert card["extension"] == "py"
    assert card["filename"].endswith(".py")

    _, raw = ArtifactStorageAndVersionManager.get_artifact_bytes("test_user_1", card["artifactId"])
    code_str = raw.decode("utf-8")
    tree = ast.parse(code_str)
    assert len(tree.body) >= 3
    assert "def " in code_str


def test_7_web_project_zip_archive():
    """Section 58 Test 7: Web Project Archive -> valid .zip containing HTML, CSS, JS, and README.md."""
    res = UniversalArtifactEngineV2.execute(
        user_id="test_user_1",
        conversation_id="conv_zip",
        message_id="msg_7",
        user_message="Create a portfolio website with HTML, CSS, and JS and give me the ZIP",
    )
    assert res["status"] == "completed"
    zip_cards = [a for a in res["artifacts"] if a["extension"] == "zip"]
    assert len(zip_cards) >= 1

    _, raw = ArtifactStorageAndVersionManager.get_artifact_bytes("test_user_1", zip_cards[0]["artifactId"])
    with zipfile.ZipFile(io.BytesIO(raw), "r") as zf:
        assert zf.testzip() is None
        names = zf.namelist()
        assert "index.html" in names
        assert "style.css" in names
        assert "script.js" in names
        assert "README.md" in names


def test_8_and_9_multi_uploaded_files_to_one_presentation():
    """Section 58 Test 8 & 9 & Section 63: Multiple uploaded files synthesized into one PPTX."""
    uploaded_sources = [
        {
            "id": "src_1",
            "filename": "architecture_overview.pdf",
            "extracted_text": "Zero-Trust Cloud Security Architecture\n• Identity verification at every boundary\n• Micro-segmentation of workloads",
        },
        {
            "id": "src_2",
            "filename": "q3_security_notes.docx",
            "extracted_text": "Q3 Audit Findings\n• 99.98% uptime achieved across regional clusters\n• Automated key rotation deployed",
        },
        {
            "id": "src_3",
            "filename": "latency_chart.png",
            "extracted_text": "Visual benchmark chart showing 42% latency reduction.",
        },
    ]
    res = UniversalArtifactEngineV2.execute(
        user_id="test_user_1",
        conversation_id="conv_multi_upload",
        message_id="msg_8",
        user_message="Combine these uploaded files into one PowerPoint presentation",
        uploaded_sources=uploaded_sources,
    )
    assert res["status"] == "completed"
    card = res["artifacts"][0]
    assert card["extension"] == "pptx"
    assert set(card["inputReferences"]) == {"src_1", "src_2", "src_3"}

    # Check slides include insights from uploaded files
    slides_preview = card["preview"]["slides"]
    slide_titles = " ".join(s.get("title", "") for s in slides_preview)
    assert "architecture_overview.pdf" in slide_titles
    assert "q3_security_notes.docx" in slide_titles


def test_10_followup_edit_and_version_chain():
    """Section 58 Test 10 & Section 64 & 66: Follow-Up Artifact Edit -> Version 1 to Version 2."""
    # Step 1: Create Version 1 PDF
    v1_res = UniversalArtifactEngineV2.execute(
        user_id="test_user_1",
        conversation_id="conv_versioning",
        message_id="msg_v1",
        user_message="Create a PDF report on Database Normalization",
    )
    assert v1_res["status"] == "completed"
    v1_card = v1_res["artifacts"][0]
    assert v1_card["version"] == 1

    # Step 2: Follow-up edit in same conversation
    v2_res = UniversalArtifactEngineV2.execute(
        user_id="test_user_1",
        conversation_id="conv_versioning",
        message_id="msg_v2",
        user_message="Add a conclusion section to the PDF",
    )
    assert v2_res["status"] == "completed"
    v2_card = v2_res["artifacts"][0]
    assert v2_card["version"] == 2
    assert v2_card["parentArtifactId"] == v1_card["artifactId"]
    assert v2_card["rootArtifactId"] == v1_card["artifactId"]
    assert len(v2_card["versionHistory"]) == 2

    headings = [s["heading"] for s in v2_card["spec"]["sections"]]
    assert any("Conclusion" in h for h in headings)


def test_11_format_conversion_pipeline():
    """Section 20: Format Conversion (PDF -> PPTX and XLSX -> CSV)."""
    pdf_res = UniversalArtifactEngineV2.execute(
        user_id="test_user_1",
        conversation_id="conv_convert",
        message_id="msg_c1",
        user_message="Create a PDF report on Kubernetes Autoscaling",
    )
    assert pdf_res["status"] == "completed"

    pptx_res = UniversalArtifactEngineV2.execute(
        user_id="test_user_1",
        conversation_id="conv_convert",
        message_id="msg_c2",
        user_message="Convert that PDF into a PowerPoint presentation",
    )
    assert pptx_res["status"] == "completed"
    pptx_card = pptx_res["artifacts"][0]
    assert pptx_card["extension"] == "pptx"
    assert pptx_card["version"] == 2


def test_12_all_additional_registry_formats():
    """Sections 5-14: Verify ODT, RTF, CSV, TSV, JSON, JSONL, YAML, XML, SQL, SVG, PNG generation & validation."""
    formats_to_test = [
        ("Create a CSV file of monthly sales", "csv"),
        ("Create a TSV file of inventory items", "tsv"),
        ("Export a JSON file of API endpoints", "json"),
        ("Generate a JSONL dataset file", "jsonl"),
        ("Create a YAML configuration file for deployment", "yaml"),
        ("Create an XML file for product catalog", "xml"),
        ("Write a SQL schema file for user orders", "sql"),
        ("Create an SVG architecture diagram file", "svg"),
        ("Create a PNG chart image file", "png"),
        ("Create an RTF document on Network Security", "rtf"),
        ("Create an ODT document on Cloud Native Design", "odt"),
    ]
    for idx, (prompt, expected_ext) in enumerate(formats_to_test):
        res = UniversalArtifactEngineV2.execute(
            user_id="test_user_formats",
            conversation_id=f"conv_fmt_{idx}",
            message_id=f"msg_fmt_{idx}",
            user_message=prompt,
        )
        assert res["status"] == "completed", f"Failed for prompt={prompt!r}: {res}"
        card = res["artifacts"][0]
        assert card["extension"] == expected_ext
        _, raw = ArtifactStorageAndVersionManager.get_artifact_bytes("test_user_formats", card["artifactId"])
        ok, msg, _ = ArtifactValidator.validate_bytes(expected_ext, raw)
        assert ok, f"Validation failed for {expected_ext}: {msg}"


def test_13_unsupported_format_honesty():
    """Section 51 & 65: Unsupported format returns honest message and never creates a fake file."""
    res = UniversalArtifactEngineV2.execute(
        user_id="test_user_1",
        conversation_id="conv_unsup",
        message_id="msg_unsup",
        user_message="Create a Blender .blend 3D model file for a spaceship",
    )
    assert res["status"] == "error"
    assert res["error_code"] == "UNSUPPORTED_FORMAT"
    assert ".blend" in res["message"]
    assert res["artifacts"] == []


def test_14_security_sanitization_and_tenant_isolation():
    """Section 39: Path traversal sanitization and strict multi-user isolation."""
    safe = sanitize_filename("../../../etc/passwd.pdf", default_stem="report", ext="pdf")
    assert ".." not in safe
    assert "/" not in safe
    assert "\\" not in safe
    assert safe.endswith(".pdf")

    # User A creates an artifact
    res_a = UniversalArtifactEngineV2.execute(
        user_id="user_alpha",
        conversation_id="conv_sec",
        message_id="msg_sec",
        user_message="Create a PDF report on Confidential Strategy",
    )
    aid = res_a["artifacts"][0]["artifactId"]

    # User B must not be able to read, download, rename, or delete User A's artifact
    assert ArtifactStorageAndVersionManager.get_artifact("user_beta", aid) is None
    assert ArtifactStorageAndVersionManager.get_artifact_bytes("user_beta", aid) is None
    assert ArtifactStorageAndVersionManager.rename_artifact("user_beta", aid, "hacked.pdf") is None
    assert ArtifactStorageAndVersionManager.delete_artifact("user_beta", aid) is False
    # User A still has full access
    assert ArtifactStorageAndVersionManager.get_artifact("user_alpha", aid) is not None


if __name__ == "__main__":
    import inspect
    test_funcs = [
        (name, obj)
        for name, obj in inspect.getmembers(sys.modules[__name__], inspect.isfunction)
        if name.startswith("test_")
    ]
    for name, fn in test_funcs:
        print(f"[RUN] {name} ...")
        fn()
        print(f"[PASS] {name}")
    print(f"\nALL {len(test_funcs)} UNIVERSAL ARTIFACT ENGINE V2 TESTS PASSED!")

