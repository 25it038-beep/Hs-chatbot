import os
import json
import pytest
import asyncio
from app.services.universal_artifacts.contracts import (
    OutputIntent,
    ArtifactCategory,
    ArtifactSpec,
)
from app.services.universal_artifacts.registry import ArtifactFormatRegistryV2
from app.services.universal_artifacts.intent_engine import ResponseOutputIntentEngine
from app.services.universal_artifacts.engine import UniversalArtifactEngineV2
from app.services.universal_artifacts.validator import ArtifactValidator
from app.services.universal_artifacts.converters import ArtifactConverter
from app.services.universal_artifacts.version_manager import ArtifactVersionManager
from app.services.universal_artifacts.synthesizer import UniversalArtifactSynthesizer


@pytest.fixture(autouse=True)
def set_env(monkeypatch):
    monkeypatch.setenv("STORAGE_DIR", "./tests_storage")
    monkeypatch.setenv("JWT_SECRET", "test_secret_key_1234567890_test_key_must_be_32")


def test_registry_supported_formats():
    assert ArtifactFormatRegistryV2.is_supported("pdf")
    assert ArtifactFormatRegistryV2.is_supported("docx")
    assert ArtifactFormatRegistryV2.is_supported("pptx")
    assert ArtifactFormatRegistryV2.is_supported("xlsx")
    assert ArtifactFormatRegistryV2.is_supported("csv")
    assert ArtifactFormatRegistryV2.is_supported("json")
    assert ArtifactFormatRegistryV2.is_supported("yaml")
    assert ArtifactFormatRegistryV2.is_supported("xml")
    assert ArtifactFormatRegistryV2.is_supported("sql")
    assert ArtifactFormatRegistryV2.is_supported("py")
    assert ArtifactFormatRegistryV2.is_supported("zip")
    assert ArtifactFormatRegistryV2.is_supported("svg")

    assert ArtifactFormatRegistryV2.get_category("pdf") == ArtifactCategory.DOCUMENT
    assert ArtifactFormatRegistryV2.get_category("xlsx") == ArtifactCategory.SPREADSHEET
    assert ArtifactFormatRegistryV2.get_category("pptx") == ArtifactCategory.PRESENTATION
    assert ArtifactFormatRegistryV2.get_category("json") == ArtifactCategory.DATA
    assert ArtifactFormatRegistryV2.get_category("py") == ArtifactCategory.CODE
    assert ArtifactFormatRegistryV2.get_category("zip") == ArtifactCategory.ARCHIVE
    assert ArtifactFormatRegistryV2.get_category("svg") == ArtifactCategory.WEB


def test_intent_engine_detection():
    engine = ResponseOutputIntentEngine()

    # 1. Pure chat (returns None)
    spec1 = engine.detect_intent("What is the capital of France?")
    assert spec1 is None

    # 2. File output
    spec2 = engine.detect_intent("Create an excel spreadsheet for quarterly budget")
    assert spec2.output_intent in (OutputIntent.FILE, OutputIntent.CHAT_AND_FILE)
    assert spec2.format == "xlsx"
    assert spec2.category == ArtifactCategory.SPREADSHEET

    spec3 = engine.detect_intent("Generate a pdf report about artificial intelligence")
    assert spec3.output_intent in (OutputIntent.FILE, OutputIntent.CHAT_AND_FILE)
    assert spec3.format == "pdf"
    assert spec3.category == ArtifactCategory.DOCUMENT

    spec4 = engine.detect_intent("Write a python script to parse CSV files and export to test.py")
    assert spec4.output_intent in (OutputIntent.FILE, OutputIntent.CHAT_AND_FILE)
    assert spec4.format == "py"
    assert spec4.category == ArtifactCategory.CODE

    # 3. Dual intent (chat and file)
    spec5 = engine.detect_intent("Explain quicksort in detail and provide the python script as a file")
    assert spec5.output_intent == OutputIntent.CHAT_AND_FILE
    assert spec5.format == "py"

    # 4. Conversion
    spec6 = engine.detect_intent("Convert that to PDF")
    assert spec6.is_format_conversion is True
    assert spec6.format == "pdf"

    # 5. Conversational edit
    spec7 = engine.detect_intent("Change the title to Q3 Financial Report")
    assert spec7.is_conversational_edit is True


def test_version_manager_computation():
    next_ver, next_name = ArtifactVersionManager.compute_next_version("report.pdf")
    assert next_ver == 2
    assert next_name == "report_v2.pdf"

    next_ver3, next_name3 = ArtifactVersionManager.compute_next_version("report_v2.pdf")
    assert next_ver3 == 3
    assert next_name3 == "report_v3.pdf"


@pytest.mark.asyncio
async def test_pdf_generation_and_validation(tmp_path):
    spec = ArtifactSpec(
        output_intent=OutputIntent.FILE,
        category=ArtifactCategory.DOCUMENT,
        format="pdf",
        filename="test_report.pdf",
        title="Test Executive Summary",
    )
    content = {
        "title": "Test Executive Summary",
        "sections": [
            {
                "heading": "Introduction",
                "paragraphs": ["This is a test paragraph for universal PDF generation."],
                "kpis": [{"metric": "99.9%", "label": "Reliability"}],
            }
        ],
    }

    meta = await UniversalArtifactEngineV2.generate_artifact(
        spec=spec,
        content=content,
        user_id="test_user",
        conversation_id="test_chat",
        db=None,
    )

    assert os.path.exists(meta.storage_path)
    assert meta.file_size > 0
    assert len(meta.sha256_hash) == 64
    assert meta.verification.get("is_valid") is True


@pytest.mark.asyncio
async def test_xlsx_generation_and_validation(tmp_path):
    spec = ArtifactSpec(
        output_intent=OutputIntent.FILE,
        category=ArtifactCategory.SPREADSHEET,
        format="xlsx",
        filename="financials.xlsx",
        title="Quarterly Financials",
    )
    content = {
        "title": "Quarterly Financials",
        "headers": ["Department", "Q1", "Q2", "Growth"],
        "rows": [["Engineering", 120000, 135000, "12.5%"], ["Marketing", 45000, 52000, "15.5%"]],
    }

    meta = await UniversalArtifactEngineV2.generate_artifact(
        spec=spec,
        content=content,
        user_id="test_user",
        conversation_id="test_chat",
        db=None,
    )

    assert os.path.exists(meta.storage_path)
    assert meta.file_size > 0
    assert meta.verification.get("is_valid") is True


@pytest.mark.asyncio
async def test_pptx_generation_and_validation(tmp_path):
    spec = ArtifactSpec(
        output_intent=OutputIntent.FILE,
        category=ArtifactCategory.PRESENTATION,
        format="pptx",
        filename="pitch.pptx",
        title="Product Pitch Deck",
    )
    content = {
        "title": "Product Pitch Deck",
        "slides": [
            {"title": "Overview", "bullets": ["First key insight", "Second key insight"]},
            {"title": "Financial Projections", "bullets": ["ARR target reached", "Strong gross margin"]},
        ],
    }

    meta = await UniversalArtifactEngineV2.generate_artifact(
        spec=spec,
        content=content,
        user_id="test_user",
        conversation_id="test_chat",
        db=None,
    )

    assert os.path.exists(meta.storage_path)
    assert meta.file_size > 0
    assert meta.verification.get("is_valid") is True


@pytest.mark.asyncio
async def test_code_py_generation_and_validation(tmp_path):
    spec = ArtifactSpec(
        output_intent=OutputIntent.FILE,
        category=ArtifactCategory.CODE,
        format="py",
        filename="calc.py",
        title="Calculation Tool",
    )
    code_text = "def add(a: int, b: int) -> int:\n    return a + b\n\nif __name__ == '__main__':\n    print(add(2, 3))\n"

    meta = await UniversalArtifactEngineV2.generate_artifact(
        spec=spec,
        content=code_text,
        user_id="test_user",
        conversation_id="test_chat",
        db=None,
    )

    assert os.path.exists(meta.storage_path)
    assert meta.file_size > 0
    assert meta.verification.get("is_valid") is True


@pytest.mark.asyncio
async def test_zip_archive_generation_and_validation(tmp_path):
    spec = ArtifactSpec(
        output_intent=OutputIntent.ARCHIVE,
        category=ArtifactCategory.ARCHIVE,
        format="zip",
        filename="bundle.zip",
        title="Project Bundle",
    )
    files_map = {
        "README.md": "# Universal Project\nComplete deliverables.\n",
        "src/main.py": "print('Universal Delivery')\n",
        "requirements.txt": "fastapi>=0.100.0\n",
    }

    meta = await UniversalArtifactEngineV2.generate_artifact(
        spec=spec,
        content=files_map,
        user_id="test_user",
        conversation_id="test_chat",
        db=None,
    )

    assert os.path.exists(meta.storage_path)
    assert meta.file_size > 0
    assert meta.verification.get("is_valid") is True


@pytest.mark.asyncio
async def test_data_formats_generation_and_validation(tmp_path):
    # JSON
    spec_json = ArtifactSpec(
        output_intent=OutputIntent.FILE,
        category=ArtifactCategory.DATA,
        format="json",
        filename="data.json",
        title="Data Export",
    )
    meta_json = await UniversalArtifactEngineV2.generate_artifact(
        spec=spec_json,
        content={"records": [{"id": 1, "value": "A"}, {"id": 2, "value": "B"}]},
        user_id="test_user",
        conversation_id="test_chat",
        db=None,
    )
    assert meta_json.verification.get("is_valid") is True

    # YAML
    spec_yaml = ArtifactSpec(
        output_intent=OutputIntent.FILE,
        category=ArtifactCategory.DATA,
        format="yaml",
        filename="config.yaml",
        title="Config",
    )
    meta_yaml = await UniversalArtifactEngineV2.generate_artifact(
        spec=spec_yaml,
        content={"app": {"port": 8000, "debug": False}},
        user_id="test_user",
        conversation_id="test_chat",
        db=None,
    )
    assert meta_yaml.verification.get("is_valid") is True


def test_artifact_converters(tmp_path):
    # 1. XLSX -> CSV
    xlsx_path = os.path.join(tmp_path, "sample.xlsx")
    csv_path = os.path.join(tmp_path, "sample.csv")

    from app.services.universal_artifacts.generators.spreadsheet_gen import generate_universal_xlsx
    generate_universal_xlsx("Sample", {"headers": ["ID", "Name"], "rows": [["1", "Alice"], ["2", "Bob"]]}, xlsx_path)

    ok, msg = ArtifactConverter.convert(xlsx_path, "xlsx", "csv", csv_path)
    assert ok is True
    assert os.path.exists(csv_path)

    # 2. CSV -> XLSX
    xlsx_out = os.path.join(tmp_path, "converted.xlsx")
    ok2, msg2 = ArtifactConverter.convert(csv_path, "csv", "xlsx", xlsx_out)
    assert ok2 is True
    assert os.path.exists(xlsx_out)
