import os
import pytest
from app.services.document_service.verifier import (
    DocumentVerificationService,
    StructuredRequirements,
    FileInspectionReport,
    Requirement,
)
from app.services.document_service.service import DocumentService, document_service
from app.services.document_service.pptx import generate_pptx
from app.services.document_service.pdf import generate_pdf
from app.services.document_service.docx import generate_docx
from app.services.document_service.xlsx import generate_xlsx
from app.services.document_service.design_system import infer_design_spec


class TestDocumentRequirementExtraction:
    def test_extract_quantity_slides(self):
        prompt = "Create a 5-slide presentation on Machine Learning Security"
        reqs = DocumentVerificationService.extract_requirements(
            user_prompt=prompt,
            fmt="pptx",
            topic="Machine Learning Security",
            count=5,
        )
        qty_req = next((r for r in reqs.requirements if r.category == "quantity"), None)
        assert qty_req is not None
        assert qty_req.expected_value == 5
        assert qty_req.mandatory is True

    def test_extract_visual_elements_kpis_and_workflow(self):
        prompt = "Build an executive PDF report on Cloud Architecture with KPI metrics and a process roadmap"
        reqs = DocumentVerificationService.extract_requirements(
            user_prompt=prompt,
            fmt="pdf",
            topic="Cloud Architecture",
        )
        ids = [r.id for r in reqs.requirements]
        assert "req_kpi" in ids
        assert "req_process_workflow" in ids
        assert "req_cover_or_intro" in ids

    def test_extract_table_and_chart(self):
        prompt = "Create a presentation comparing competitors with a comparison table and growth chart"
        reqs = DocumentVerificationService.extract_requirements(
            user_prompt=prompt,
            fmt="pptx",
            topic="Competitor Analysis",
        )
        ids = [r.id for r in reqs.requirements]
        assert "req_table" in ids
        assert "req_chart" in ids


class TestRealFileInspectionAndVerification:
    def test_inspect_and_verify_real_pptx(self, tmp_path):
        out_pptx = str(tmp_path / "test_presentation.pptx")
        slides_data = [
            {
                "title": "Executive Overview",
                "layout": "cards",
                "cards": [
                    {"title": "Vision", "points": ["Pillar 1", "Pillar 2"]},
                    {"title": "Strategy", "points": ["Action 1", "Action 2"]},
                ]
            },
            {
                "title": "Pipeline Architecture",
                "layout": "process",
                "steps": [
                    {"title": "Data Ingestion", "description": "Streaming sources"},
                    {"title": "Processing", "description": "Real-time transforms"},
                ]
            },
            {
                "title": "Performance Metrics",
                "layout": "kpis",
                "kpis": [
                    {"metric": "99.9%", "label": "Availability"},
                    {"metric": "10x", "label": "Acceleration"},
                ]
            }
        ]

        design_spec = infer_design_spec(topic="AI Systems", doc_format="pptx")
        generate_pptx("AI Systems", slides_data, out_pptx, design_spec=design_spec)

        # 1. Physical inspection
        report = DocumentVerificationService.inspect_file(out_pptx, "pptx")
        assert report.exists is True
        # Title slide + 3 content slides = 4 slides
        assert report.page_or_slide_count == 4
        assert report.diagram_elements_count > 0  # right arrows in process layout
        assert report.kpis_count >= 2
        assert len(report.text_overflow_warnings) == 0

        # 2. Verification
        reqs = DocumentVerificationService.extract_requirements(
            user_prompt="Create a 4-slide presentation on AI Systems with process workflow and KPIs",
            fmt="pptx",
            topic="AI Systems",
            count=4,
        )
        v_res = DocumentVerificationService.verify(reqs, report)
        assert v_res.passed is True
        assert v_res.overall_score >= 85
        assert len(v_res.verified_checklist) > 0

    def test_inspect_and_verify_real_pdf(self, tmp_path):
        out_pdf = str(tmp_path / "test_report.pdf")
        sections = [
            {
                "heading": "Executive Summary",
                "content": "Comprehensive overview of system throughput and reliability metrics.",
                "callout": "Key insight: latency reduced by 75% across enterprise workloads.",
                "kpis": [{"metric": "99.99%", "label": "Uptime"}],
            },
            {
                "heading": "Architectural Analysis",
                "content": "Detailed exploration of containerized microservices and edge gateways.",
                "table": [["Service", "Latency", "Status"], ["Gateway", "5ms", "Active"], ["Auth", "12ms", "Active"]],
            }
        ]

        design_spec = infer_design_spec(topic="Infrastructure", doc_format="pdf")
        generate_pdf("Infrastructure Report", sections, out_pdf, design_spec=design_spec)

        report = DocumentVerificationService.inspect_file(out_pdf, "pdf")
        assert report.exists is True
        assert report.page_or_slide_count >= 2
        assert "Infrastructure Report" in report.extracted_text
        assert "Executive Summary" in report.extracted_text

        reqs = DocumentVerificationService.extract_requirements(
            user_prompt="Create a PDF report on Infrastructure with KPIs and comparison table",
            fmt="pdf",
            topic="Infrastructure",
        )
        v_res = DocumentVerificationService.verify(reqs, report)
        assert v_res.passed is True
        assert v_res.overall_score >= 80

    def test_inspect_and_verify_real_docx(self, tmp_path):
        out_docx = str(tmp_path / "test_doc.docx")
        sections = [
            {
                "heading": "Market Dynamics",
                "content": "An in-depth analysis of emerging artificial intelligence applications and governance models.",
                "kpis": [{"metric": "$4.5B", "label": "TAM"}],
            }
        ]
        design_spec = infer_design_spec(topic="Market Dynamics", doc_format="docx")
        generate_docx("Market Dynamics", sections, out_docx, design_spec=design_spec)

        report = DocumentVerificationService.inspect_file(out_docx, "docx")
        assert report.exists is True
        assert report.tables_count >= 1
        assert "Market Dynamics" in report.extracted_text

    def test_inspect_and_verify_real_xlsx(self, tmp_path):
        out_xlsx = str(tmp_path / "test_sheet.xlsx")
        data = {
            "Budget": [
                ["Category", "Allocated", "Spent", "Remaining"],
                ["Cloud Compute", 120000, 95000, 25000],
                ["Licenses", 45000, 30000, 15000],
            ]
        }
        kpis = [{"metric": "$165K", "label": "Total Budget"}]
        design_spec = infer_design_spec(topic="Financial Model", doc_format="xlsx")
        generate_xlsx("Budget Model", data, out_xlsx, design_spec=design_spec, kpis=kpis)

        report = DocumentVerificationService.inspect_file(out_xlsx, "xlsx")
        assert report.exists is True
        assert report.sheets_count == 1
        assert "Budget" in report.sheet_names
        assert report.kpis_count >= 1


class TestAutoRepairLoop:
    def test_auto_repair_inserts_missing_slides_and_kpis(self):
        reqs = DocumentVerificationService.extract_requirements(
            user_prompt="Create a 5-slide deck on Autonomous Systems with KPI metrics",
            fmt="pptx",
            topic="Autonomous Systems",
            count=5,
        )
        initial_slides = [
            {"title": "Slide 1", "layout": "cards", "cards": [{"title": "Card 1", "points": ["P1"]}]},
            {"title": "Slide 2", "layout": "cards", "cards": [{"title": "Card 2", "points": ["P2"]}]},
        ]
        issues = ["Insufficient count: generated 2, expected 5.", "Requested KPI metrics / statistics are missing."]

        repaired = DocumentVerificationService.auto_repair_content(
            content=initial_slides,
            fmt="pptx",
            requirements=reqs,
            issues=issues,
        )

        assert len(repaired) >= 5
        assert any(s.get("layout") == "kpis" for s in repaired)

    def test_auto_repair_splits_overcrowded_slides(self):
        reqs = DocumentVerificationService.extract_requirements(
            user_prompt="Slide deck",
            fmt="pptx",
            topic="General",
        )
        overcrowded = [
            {
                "title": "Overcrowded Slide",
                "layout": "cards",
                "cards": [
                    {"title": f"Card {i}", "points": [f"Point {i}"]} for i in range(6)
                ]
            }
        ]
        repaired = DocumentVerificationService.auto_repair_content(
            content=overcrowded,
            fmt="pptx",
            requirements=reqs,
            issues=["Slide has high text density"],
        )
        # Should be split into Part 1 and Part 2
        assert len(repaired) == 2
        assert "Part 1" in repaired[0]["title"]
        assert "Part 2" in repaired[1]["title"]
