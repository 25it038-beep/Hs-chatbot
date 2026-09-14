import os
import shutil
import pytest
import pytest_asyncio
from app.services.document_service import (
    DocumentService, document_service,
    generate_pdf, generate_docx, generate_pptx, generate_xlsx, generate_csv,
    generate_markdown, validate_file_structure,
)
from app.services.document_service.validator import (
    validate_pdf, validate_docx, validate_pptx, validate_xlsx, validate_csv,
)
from app.models.file import GeneratedFile
from app.database import async_session, engine, Base


TEST_DIR = "./data/test_output"


@pytest.fixture(scope="module", autouse=True)
def setup_test_dir():
    os.makedirs(TEST_DIR, exist_ok=True)
    yield
    if os.path.exists(TEST_DIR):
        shutil.rmtree(TEST_DIR, ignore_errors=True)


class TestDocumentIntentDetection:
    def test_pdf_intent(self):
        intent = DocumentService.detect_intent("Create a PDF about artificial intelligence")
        assert intent is not None
        assert intent.format == "pdf"
        assert "artificial intelligence" in intent.topic.lower()
        assert intent.filename.endswith(".pdf")

    def test_pdf_with_page_count(self):
        intent = DocumentService.detect_intent("Create a 3-page PDF explaining artificial intelligence.")
        assert intent is not None
        assert intent.format == "pdf"
        assert intent.count == 3
        assert intent.count_unit == "page"

    def test_pptx_with_slide_count(self):
        intent = DocumentService.detect_intent("Create a 5-slide PowerPoint about my project")
        assert intent is not None
        assert intent.format == "pptx"
        assert intent.count == 5
        assert intent.count_unit == "slide"
        assert intent.filename.endswith(".pptx")

    def test_xlsx_expense_tracker(self):
        intent = DocumentService.detect_intent("Create an Excel expense tracker")
        assert intent is not None
        assert intent.format == "xlsx"
        assert intent.filename.endswith(".xlsx")

    def test_docx_word_document(self):
        intent = DocumentService.detect_intent("Create a Word document about quantum computing")
        assert intent is not None
        assert intent.format == "docx"
        assert intent.filename.endswith(".docx")

    def test_docx_make_docx(self):
        intent = DocumentService.detect_intent("Make a DOCX report for quarterly earnings")
        assert intent is not None
        assert intent.format == "docx"

    def test_csv_creation(self):
        intent = DocumentService.detect_intent("Create CSV with employee records")
        assert intent is not None
        assert intent.format == "csv"
        assert intent.filename.endswith(".csv")

    def test_markdown_creation(self):
        intent = DocumentService.detect_intent("Generate a markdown guide for Python")
        assert intent is not None
        assert intent.format == "md"
        assert intent.filename.endswith(".md")

    def test_negative_questions_do_not_trigger(self):
        assert DocumentService.detect_intent("What is a PDF?") is None
        assert DocumentService.detect_intent("How does PowerPoint work?") is None
        assert DocumentService.detect_intent("Explain what is an Excel spreadsheet") is None
        assert DocumentService.detect_intent("Why is CSV format used?") is None
        assert DocumentService.detect_intent("What is artificial intelligence?") is None


class TestDocumentGenerators:
    def test_generate_and_validate_pdf(self):
        pdf_path = os.path.join(TEST_DIR, "AI_Report.pdf")
        sections = [
            {
                "heading": "Introduction to Artificial Intelligence",
                "content": "Artificial Intelligence represents a paradigm shift in computing.\n\nKey areas include machine learning and neural networks.",
                "items": ["Supervised Learning", "Unsupervised Learning", "Reinforcement Learning"],
                "table": [["Branch", "Focus"], ["NLP", "Language Processing"], ["CV", "Computer Vision"]],
                "page_break": True,
            },
            {
                "heading": "Modern Architecture & LLMs",
                "content": "Transformer architectures utilize attention mechanisms.",
            }
        ]
        out = generate_pdf(
            title="Artificial Intelligence Report",
            sections=sections,
            output_path=pdf_path,
            author="HSBot",
        )
        assert os.path.exists(out)
        assert os.path.getsize(out) > 500
        assert validate_pdf(out) is True

    def test_generate_and_validate_docx(self):
        docx_path = os.path.join(TEST_DIR, "Quantum_Computing.docx")
        sections = [
            {
                "heading": "Quantum Supremacy",
                "content": "Qubits allow simultaneous superposition of states.",
                "items": ["Superposition", "Entanglement", "Interference"],
                "table": [["Architecture", "Qubits"], ["Superconducting", "1000+"], ["Trapped Ion", "64"]],
            }
        ]
        out = generate_docx(
            title="Quantum Computing Analysis",
            sections=sections,
            output_path=docx_path,
            author="HSBot",
        )
        assert os.path.exists(out)
        assert os.path.getsize(out) > 500
        assert validate_docx(out) is True

    def test_generate_and_validate_pptx(self):
        pptx_path = os.path.join(TEST_DIR, "Project_Presentation.pptx")
        slides = [
            {"title": "Project Scope", "content": ["Goal 1: File Generation", "Goal 2: RAG Pipeline"]},
            {"title": "Architecture", "content": ["FastAPI backend", "React frontend", "Automated Agents"]},
            {"title": "Validation & Quality", "content": ["Magic byte checking", "Structured parsing"]},
            {"title": "Deployment", "content": ["Render hosting", "Local desktop integration"]},
            {"title": "Conclusion", "content": ["Production ready system"]},
        ]
        out = generate_pptx(
            title="Project Presentation",
            slides=slides,
            output_path=pptx_path,
            subtitle="Automated AI Briefing",
        )
        assert os.path.exists(out)
        assert os.path.getsize(out) > 1000
        assert validate_pptx(out) is True

        from pptx import Presentation
        prs = Presentation(out)
        # Title slide + 5 content slides = 6 slides
        assert len(prs.slides) == 6

    def test_generate_and_validate_xlsx(self):
        xlsx_path = os.path.join(TEST_DIR, "Expense_Tracker.xlsx")
        sheets = {
            "Expenses": [
                ["ID", "Date", "Category", "Amount ($)", "Status"],
                ["TX1", "2026-03-01", "Hardware", 250.00, "Paid"],
                ["TX2", "2026-03-02", "Cloud Hosting", 120.50, "Approved"],
            ]
        }
        out = generate_xlsx(
            title="Expense Tracker",
            sheets_data=sheets,
            output_path=xlsx_path,
        )
        assert os.path.exists(out)
        assert os.path.getsize(out) > 500
        assert validate_xlsx(out) is True

    def test_generate_and_validate_csv(self):
        csv_path = os.path.join(TEST_DIR, "dataset.csv")
        rows = [
            ["ID", "Name", "Score"],
            ["1", "Alice", "95"],
            ["2", "Bob", "88"],
        ]
        out = generate_csv(data=rows, output_path=csv_path)
        assert os.path.exists(out)
        assert validate_csv(out) is True


@pytest.mark.asyncio
class TestDocumentServicePipeline:
    async def test_full_pipeline_with_database(self):
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async with async_session() as session:
            intent = DocumentService.detect_intent("Create a PDF about artificial intelligence")
            assert intent is not None

            content = document_service._generate_fallback_content(intent)
            result = await document_service.generate_file(
                fmt=intent.format,
                filename=intent.filename,
                title=intent.title,
                content=content,
                conversation_id="test-conv-123",
                user_id="test-user-456",
                db=session,
            )

            assert "id" in result
            assert result["filename"] == intent.filename
            assert result["download_url"] == f"/api/files/{result['id']}/download"
            assert os.path.exists(result["path"])
            assert result["file_size"] > 0

            # Verify in DB
            from sqlalchemy import select
            db_res = await session.execute(select(GeneratedFile).where(GeneratedFile.id == result["id"]))
            record = db_res.scalar_one_or_none()
            assert record is not None
            assert record.filename == intent.filename
            assert record.storage_path == result["path"]
            assert record.mime_type == "application/pdf"
