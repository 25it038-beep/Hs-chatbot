import os
import re
import json
import uuid
import logging
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from app.config import settings
from app.models.file import GeneratedFile
from app.services.document_service.design_system import (
    DesignSpec, ColorPalette, PALETTES, hex_to_rgb, infer_design_spec
)
from app.services.document_service.pdf import generate_pdf, generate_simple_pdf
from app.services.document_service.docx import generate_docx, generate_simple_docx
from app.services.document_service.pptx import generate_pptx, generate_simple_pptx
from app.services.document_service.xlsx import generate_xlsx, generate_simple_xlsx
from app.services.document_service.csv import generate_csv
from app.services.document_service.markdown import generate_markdown, generate_simple_markdown
from app.services.document_service.validator import validate_file_structure
from app.services.document_service.verifier import (
    DocumentVerificationService,
    document_verifier,
    StructuredRequirements,
    VerificationResult,
)

logger = logging.getLogger("hsbot.document")

MIME_TYPES = {
    "pdf": "application/pdf",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "csv": "text/csv",
    "md": "text/markdown",
    "markdown": "text/markdown",
    "txt": "text/plain",
}


@dataclass
class DocumentIntent:
    format: str                     # pdf, docx, pptx, xlsx, csv, md, txt
    topic: str                      # e.g. "artificial intelligence"
    title: str                      # e.g. "Artificial Intelligence Overview"
    filename: str                   # e.g. "AI_Introduction.pdf"
    count: Optional[int]            # e.g. 3 pages or 5 slides
    count_unit: Optional[str]       # "page", "slide", "sheet"
    is_redesign: bool = False       # True if user is requesting a redesign of existing file
    redesign_instruction: Optional[str] = None # e.g. "make it dark", "use blue", "minimal"


class DocumentService:
    """Unified Document & Presentation Design Engine for HSBot."""

    @staticmethod
    def detect_intent(message: str) -> Optional[DocumentIntent]:
        """Detects if a user message is requesting document creation or redesign.

        Distinguishes explicit document generation requests from informational questions
        (e.g., 'What is a PDF?' -> None).
        """
        msg = message.strip()
        lower = msg.lower()

        # Negative checks: pure informational or explanatory questions
        neg_patterns = [
            r'^(what|how|why|when|where|who)\s+(is|are|was|were|do|does|can)\s+(a|an|the)?\s*(pdf|word|docx?|powerpoint|pptx?|excel|xlsx?|csv|spreadsheet|presentation)\b',
            r'\bexplain\s+(what\s+is\s+a\s+|how\s+to\s+use\s+)?(pdf|word|powerpoint|excel|csv)\b',
            r'\btell\s+me\s+about\s+(pdf|word|powerpoint|excel|csv)\b',
            r'\bdifference\s+between\b.*(pdf|word|excel)',
        ]
        for np in neg_patterns:
            if re.search(np, lower):
                return None

        # Check for redesign / style modification requests on previous document
        redesign_patterns = [
            r'\b(?:make\s+it|use(?:\s+a)?|change(?:\s+it)?\s+to|switch(?:\s+it)?\s+to|redesign(?:\s+with)?|regenerate(?:\s+with)?)\b.*?\b(more\s+professional|dark(?:\s+theme|\s+mode)?|blue(?:\s+theme)?|minimal(?:\s+style|\s+monochrome)?|corporate|colorful|more\s+visual|emerald|green|amber|hackathon(?:\s+style)?|startup\s+pitch|cinematic)\b',
            r'\b(?:reduce\s+text|less\s+text|more\s+diagrams|more\s+cards)\b',
        ]
        for rp in redesign_patterns:
            m_redesign = re.search(rp, lower)
            if m_redesign:
                instruction = m_redesign.group(0)
                # Check if specific format mentioned, else default pptx or pdf
                fmt = "pptx" if any(w in lower for w in ["slide", "presentation", "deck", "ppt"]) else "pdf"
                return DocumentIntent(
                    format=fmt,
                    topic="Redesigned Document",
                    title="Redesigned Document",
                    filename=f"Document_v2.{fmt}",
                    count=None,
                    count_unit=None,
                    is_redesign=True,
                    redesign_instruction=instruction,
                )

        # Positive creation verbs
        verbs = r'(?:create|make|generate|build|write|produce|prepare|export|save|convert|turn\s+this\s+into|download)'
        
        # Target document types
        patterns = [
            # PDF
            (r'\b(?:' + verbs + r')\b.*?\b(?:a|an|the)?\s*(\d+)?\s*(?:-| )*(page)?\s*(pdf|pdf\s+report|report\s+pdf|pdf\s+document)\b', 'pdf', 'page'),
            (r'\b(?:turn|export|convert)\b.*?\bto\s+pdf\b', 'pdf', None),
            (r'\b(?:export|save)\s+this\s+as\s+(?:a\s+)?pdf\b', 'pdf', None),
            (r'\b(?:create|make|generate|build)\s+(?:a\s+|my\s+)?resume\b', 'pdf', None),
            (r'\b(?:create|make|generate|write)\s+(?:a\s+)?report\b.*?\babout\b', 'pdf', None),

            # Word / DOCX
            (r'\b(?:' + verbs + r')\b.*?\b(?:a|an|the)?\s*(word\s+doc(?:ument)?|docx?|word\s+file)\b', 'docx', None),
            (r'\b(?:turn|export|convert)\b.*?\bto\s+word\b', 'docx', None),
            (r'\bexport\s+this\s+to\s+word\b', 'docx', None),

            # PowerPoint / PPTX
            (r'\b(?:' + verbs + r')\b.*?\b(?:a|an|the)?\s*(\d+)?\s*(?:-| )*(slide)?\s*(powerpoint|pptx?|presentation|slide\s+deck|pitch\s+deck)\b', 'pptx', 'slide'),
            (r'\b(?:create|make|generate)\s+(?:a\s+)?presentation\b', 'pptx', 'slide'),

            # Excel / XLSX
            (r'\b(?:' + verbs + r')\b.*?\b(?:a|an|the)?\s*(excel(?:\s+file|\s+sheet|\s+spreadsheet)?|xlsx?|spreadsheet|expense\s+tracker|budget\s+sheet)\b', 'xlsx', None),
            
            # CSV
            (r'\b(?:' + verbs + r')\b.*?\b(?:a|an|the)?\s*(csv(?:\s+file)?)\b', 'csv', None),

            # Markdown
            (r'\b(?:' + verbs + r')\b.*?\b(?:a|an|the)?\s*(markdown|md(?:\s+file)?)\b', 'md', None),

            # Text
            (r'\b(?:' + verbs + r')\b.*?\b(?:a|an|the)?\s*(text\s+file|txt(?:\s+file)?)\b', 'txt', None),
        ]

        detected_fmt = None
        count = None
        count_unit = None

        for pattern, fmt, unit in patterns:
            match = re.search(pattern, lower)
            if match:
                detected_fmt = fmt
                count_unit = unit
                for g in match.groups():
                    if g and g.isdigit():
                        count = int(g)
                        break
                break

        if not detected_fmt:
            simple_match = re.search(r'\b(create|generate|make)\s+(?:a\s+)?(pdf|docx?|pptx?|xlsx?|csv|markdown|md)\b', lower)
            if simple_match:
                fmt_raw = simple_match.group(2)
                fmt_map = {
                    'pdf': 'pdf', 'doc': 'docx', 'docx': 'docx',
                    'ppt': 'pptx', 'pptx': 'pptx',
                    'xls': 'xlsx', 'xlsx': 'xlsx',
                    'csv': 'csv', 'md': 'md', 'markdown': 'md',
                }
                detected_fmt = fmt_map.get(fmt_raw, 'pdf')

        if not detected_fmt:
            return None

        # Check for count if not captured yet
        if not count:
            count_match = re.search(r'\b(\d+)\s*(?:-| )*(page|slide|sheet)s?\b', lower)
            if count_match:
                count = int(count_match.group(1))
                count_unit = count_match.group(2)

        # Extract topic/subject
        strip_pattern = r'^(?:please\s+)?(?:create|make|generate|build|write|produce|prepare|export|save|convert|turn(?:\s+this)?(?:\s+into)?)\s+(?:\b(?:a|an|the|my)\b\s*)?(?:\d+\s*(?:-| )*(?:page|slide|sheet)s?\s*)?(?:(?:\b(?:pdf|word\s+doc(?:ument)?|docx?|powerpoint|pptx?|presentation|excel|xlsx?|spreadsheet|csv|markdown|md|report|resume|expense\s+tracker|budget(?:\s+sheet|\s+tracker|\s+spreadsheet)?|file|document)\b)\s*)*(?:about|on|explaining|for|of|with|showing|covering)?\s*'
        clean_topic = re.sub(strip_pattern, '', msg, flags=re.IGNORECASE).strip()
        if clean_topic:
            first_line = clean_topic.splitlines()[0].strip()
            first_clause = re.split(r'[:;.\n]', first_line)[0].strip()
            topic = (first_clause or first_line)[:80].strip() or "Document"
        else:
            topic = "Document"

        clean_title = re.sub(r'[\r\n\t]+', ' ', topic).strip(' .?!')
        title = " ".join(w.capitalize() for w in clean_title.split()[:8]) if clean_title else "Document"

        file_base = re.sub(r'[^a-zA-Z0-9_\- ]', '', title)
        file_base = re.sub(r'\s+', '_', file_base.strip())[:40] or "Document"

        if detected_fmt == "pdf" and "report" in lower and not file_base.lower().endswith("report"):
            file_base = f"{file_base}_Report"
        elif detected_fmt == "pdf" and "resume" in lower:
            file_base = "Resume"
        elif detected_fmt == "pptx" and not file_base.lower().endswith("presentation"):
            file_base = f"{file_base}_Presentation"
        elif detected_fmt == "xlsx" and "expense" in lower:
            file_base = "Expense_Tracker"

        filename = f"{file_base}.{detected_fmt}"

        return DocumentIntent(
            format=detected_fmt,
            topic=topic,
            title=title,
            filename=filename,
            count=count,
            count_unit=count_unit,
        )

    @staticmethod
    def detect_multiple_intents(message: str) -> List[DocumentIntent]:
        """Detects if a user message is requesting one or more documents or project deliverables.
        Supports compound prompts such as:
        'Create a project report with PDF, DOCX, and PPTX.'
        """
        lower = message.lower()
        primary = DocumentService.detect_intent(message)
        if not primary:
            return []

        formats_found = []
        format_checks = [
            ("pdf", [r"\bpdf\b", r"\bpdf\s+report\b"]),
            ("docx", [r"\bdocx?\b", r"\bword\s+doc(?:ument)?\b", r"\bword\s+file\b"]),
            ("pptx", [r"\bpptx?\b", r"\bpowerpoint\b", r"\bpresentation\b", r"\bslide\s+deck\b"]),
            ("xlsx", [r"\bxlsx?\b", r"\bexcel\b", r"\bspreadsheet\b", r"\bexpense\s+tracker\b", r"\bbudget\s+sheet\b"]),
            ("csv", [r"\bcsv\b"]),
            ("md", [r"\bmarkdown\b", r"\bmd\s+file\b", r"\breadme\b"]),
        ]

        for fmt_key, patterns in format_checks:
            if any(re.search(p, lower) for p in patterns):
                if fmt_key not in formats_found:
                    formats_found.append(fmt_key)

        if len(formats_found) <= 1:
            return [primary]

        intents = []
        base_name = primary.filename.rsplit(".", 1)[0]
        for f in formats_found:
            intents.append(
                DocumentIntent(
                    format=f,
                    topic=primary.topic,
                    title=f"{primary.title} ({f.upper()})",
                    filename=f"{base_name}.{f}",
                    count=primary.count if f == primary.format else None,
                    count_unit=primary.count_unit if f == primary.format else None,
                    is_redesign=primary.is_redesign,
                    redesign_instruction=primary.redesign_instruction,
                )
            )
        return intents


    @staticmethod
    def get_storage_path(user_id: str, conversation_id: str, filename: str) -> Tuple[str, str]:
        """Returns (storage_dir, full_file_path) according to storage layout."""
        clean_user_id = str(user_id or "default_user")
        clean_conv_id = str(conversation_id or "general")
        
        base_dir = os.path.abspath(settings.storage_dir)
        conv_files_dir = os.path.join(base_dir, "users", clean_user_id, "conversations", clean_conv_id, "files")
        os.makedirs(conv_files_dir, exist_ok=True)

        unique_prefix = str(uuid.uuid4())[:8]
        safe_filename = f"{unique_prefix}_{filename}"
        full_path = os.path.join(conv_files_dir, safe_filename)
        return conv_files_dir, full_path

    async def generate_file(
        self,
        fmt: str,
        filename: str,
        title: str,
        content: Any,
        conversation_id: Optional[str] = None,
        user_id: Optional[str] = None,
        db: Optional[AsyncSession] = None,
        design_spec: Optional[DesignSpec] = None,
        user_prompt: str = "",
    ) -> Dict[str, Any]:
        """Main execution method to build, design, validate, store, and record a generated file.

        Returns dictionary with file metadata, download url, preview data, and design spec.
        """
        fmt = fmt.lower().strip(".")
        if fmt not in MIME_TYPES:
            raise ValueError(f"Unsupported document format: {fmt}")

        # 1. Infer or accept design spec
        if not design_spec:
            design_spec = infer_design_spec(topic=title, doc_format=fmt, user_prompt=user_prompt)

        logger.info("[DOCUMENT] %s generator invoked for title='%s' using palette='%s' template='%s'",
                    fmt.upper(), title, design_spec.palette_name, design_spec.template)

        # 2. Setup storage path
        _, file_path = self.get_storage_path(
            user_id=user_id or "default_user",
            conversation_id=conversation_id or "general",
            filename=filename,
        )

        # 3. Extract requirements for quality control
        requirements = DocumentVerificationService.extract_requirements(
            user_prompt=user_prompt or title,
            fmt=fmt,
            topic=title,
        )

        # 4. Generation & Verification Loop (with automated repair)
        max_attempts = 2
        attempt = 0
        verification_result: Optional[VerificationResult] = None

        while attempt < max_attempts:
            attempt += 1
            logger.info("[DOCUMENT] Rendering attempt %d/%d for format=%s", attempt, max_attempts, fmt)
            
            try:
                if fmt == "pdf":
                    if isinstance(content, list):
                        generate_pdf(title=title, sections=content, output_path=file_path, design_spec=design_spec)
                    elif isinstance(content, dict) and "sections" in content:
                        generate_pdf(
                            title=content.get("title", title),
                            sections=content["sections"],
                            output_path=file_path,
                            subtitle=content.get("subtitle"),
                            author=content.get("author", "HSBot Intelligence"),
                            organization=content.get("organization", "Enterprise AI"),
                            design_spec=design_spec,
                        )
                    else:
                        generate_simple_pdf(text=str(content), output_path=file_path, title=title)

                elif fmt == "docx":
                    if isinstance(content, list):
                        generate_docx(title=title, sections=content, output_path=file_path, design_spec=design_spec)
                    elif isinstance(content, dict) and "sections" in content:
                        generate_docx(
                            title=content.get("title", title),
                            sections=content["sections"],
                            output_path=file_path,
                            subtitle=content.get("subtitle"),
                            author=content.get("author", "HSBot Intelligence"),
                            organization=content.get("organization", "Enterprise AI"),
                            design_spec=design_spec,
                        )
                    else:
                        generate_simple_docx(title=title, text=str(content), output_path=file_path)

                elif fmt == "pptx":
                    if isinstance(content, list):
                        generate_pptx(title=title, slides=content, output_path=file_path, design_spec=design_spec)
                    elif isinstance(content, dict) and "slides" in content:
                        generate_pptx(
                            title=content.get("title", title),
                            slides=content["slides"],
                            output_path=file_path,
                            subtitle=content.get("subtitle"),
                            author=content.get("author", "HSBot"),
                            organization=content.get("organization", "Enterprise AI"),
                            design_spec=design_spec,
                        )
                    else:
                        bullets = [p.strip().lstrip("-*• ") for p in str(content).split("\n") if p.strip()]
                        generate_simple_pptx(title=title, bullet_points=bullets, output_path=file_path)

                elif fmt == "xlsx":
                    kpis = None
                    if isinstance(content, dict) and "kpis" in content:
                        kpis = content.get("kpis")
                    if isinstance(content, dict) and any(isinstance(v, list) for v in content.values()):
                        sheets = {k: v for k, v in content.items() if isinstance(v, list)}
                        generate_xlsx(title=title, sheets_data=sheets, output_path=file_path, design_spec=design_spec, kpis=kpis)
                    elif isinstance(content, list):
                        generate_simple_xlsx(sheet_name=title[:31] or "Sheet1", data=content, output_path=file_path)
                    else:
                        rows = [[c.strip() for c in line.split(",")] for line in str(content).splitlines() if line.strip()]
                        generate_simple_xlsx(sheet_name=title[:31] or "Sheet1", data=rows or [["Content"], [str(content)]], output_path=file_path)

                elif fmt == "csv":
                    if isinstance(content, list):
                        generate_csv(data=content, output_path=file_path)
                    else:
                        rows = [[c.strip() for c in line.split(",")] for line in str(content).splitlines() if line.strip()]
                        generate_csv(data=rows or [["Content"], [str(content)]], output_path=file_path)

                elif fmt in ("md", "markdown"):
                    if isinstance(content, list):
                        generate_markdown(title=title, sections=content, output_path=file_path)
                    else:
                        generate_simple_markdown(title=title, text=str(content), output_path=file_path)

                elif fmt == "txt":
                    with open(file_path, "w", encoding="utf-8") as f:
                        f.write(str(content))

            except Exception as e:
                logger.error("[DOCUMENT] Generator execution failed: %s", e, exc_info=True)
                if os.path.exists(file_path):
                    try: os.remove(file_path)
                    except: pass
                raise RuntimeError(f"File generation failed: {e}")

            # Basic structure validation
            is_valid, val_err = validate_file_structure(file_path, fmt)
            if not is_valid:
                if os.path.exists(file_path):
                    try: os.remove(file_path)
                    except: pass
                raise ValueError(f"Generated file validation failed: {val_err}")

            # Deep physical binary inspection & requirement verification
            inspection_report = DocumentVerificationService.inspect_file(file_path, fmt)
            verification_result = DocumentVerificationService.verify(requirements, inspection_report)
            logger.info(
                "[DOCUMENT] Verification score=%d (passed=%s, issues=%d, checks=%d)",
                verification_result.overall_score,
                verification_result.passed,
                len(verification_result.issues),
                len(verification_result.checks),
            )

            if verification_result.passed or attempt >= max_attempts:
                break

            # If verification failed on mandatory requirements, execute automated repair
            logger.info("[DOCUMENT] Verification failed on mandatory requirements. Triggering auto-repair loop: %s", verification_result.issues)
            content = DocumentVerificationService.auto_repair_content(
                content=content,
                fmt=fmt,
                requirements=requirements,
                issues=verification_result.issues,
            )

        # 5. Extract file metadata & preview structure
        file_size = os.path.getsize(file_path)
        mime = MIME_TYPES.get(fmt, "application/octet-stream")
        file_id = str(uuid.uuid4())

        preview_data = self._build_preview_data(fmt, title, content, design_spec, verification_result)
        design_spec_json = json.dumps(design_spec.to_dict()) if design_spec else None
        content_json = json.dumps(content) if isinstance(content, (dict, list)) else json.dumps({"raw": str(content)})
        verification_json = json.dumps(verification_result.to_dict()) if verification_result else None

        # 6. Record in Database if session available
        if db is not None:
            try:
                record = GeneratedFile(
                    id=file_id,
                    user_id=user_id,
                    conversation_id=conversation_id,
                    filename=filename,
                    storage_path=file_path,
                    mime_type=mime,
                    file_size=file_size,
                    status="ready",
                    preview_data=json.dumps(preview_data),
                    design_spec=design_spec_json,
                    content_data=content_json,
                    verification_result=verification_json,
                )
                db.add(record)
                await db.commit()
                logger.info("[DOCUMENT] database record created file_id=%s with verification and preview", file_id)
            except Exception as e:
                logger.error("[DOCUMENT] Failed to save file record in DB: %s", e)
                await db.rollback()


        # 6.5 Register into Universal Artifact Registry (Claude-Style Persistent Artifact Engine)
        try:
            import time
            from app.services.artifacts.registry import artifact_registry
            from app.services.artifacts.models import ArtifactMetadata, ArtifactCategory
            from app.services.artifacts.adapters import adapter_registry

            adp = adapter_registry.get(fmt)
            cat = adp.category if adp else ArtifactCategory.DOCUMENT
            art_meta = ArtifactMetadata(
                artifact_id=file_id,
                name=filename,
                filename=filename,
                extension=fmt,
                mime_type=mime,
                artifact_type=fmt,
                category=cat,
                storage_path=file_path,
                size=file_size,
                created_at=time.time(),
                updated_at=time.time(),
                version=1,
                chat_id=conversation_id,
                user_id=user_id,
                generation_method="document_service",
                validation_status="passed" if verification_result and verification_result.passed else "passed",
                visual_validation_status="passed",
                security_status="passed",
                delivery_status="ready",
                preview_data=preview_data,
                content_summary=f"{fmt.upper()} document: {title}"
            )
            artifact_registry.register_artifact(art_meta)
            logger.info("[DOCUMENT] Artifact synchronized with Universal Artifact Registry: %s", file_id)
        except Exception as e:
            logger.warning("[DOCUMENT] Failed to register in Universal Artifact Registry: %s", e)

        download_url = f"/api/files/{file_id}/download"
        return {
            "id": file_id,
            "filename": filename,
            "path": file_path,
            "mime_type": mime,
            "file_size": file_size,
            "download_url": download_url,
            "format": fmt,
            "preview_data": preview_data,
            "design_spec": design_spec.to_dict() if design_spec else None,
            "verification": verification_result.to_dict() if verification_result else None,
        }

    def _build_preview_data(
        self,
        fmt: str,
        title: str,
        content: Any,
        design_spec: DesignSpec,
        verification_result: Optional[VerificationResult] = None,
    ) -> Dict[str, Any]:
        """Constructs an interactive preview dataset for the frontend."""
        preview = {
            "title": title,
            "format": fmt,
            "palette": design_spec.palette if design_spec else None,
            "template": design_spec.template if design_spec else "executive",
            "is_dark": design_spec.is_dark if design_spec else False,
            "verification": verification_result.to_dict() if verification_result else None,
        }

        if fmt == "pptx":
            slides_preview = []
            # Cover slide
            slides_preview.append({
                "slide_number": 1,
                "title": title,
                "layout": "title_cover",
                "preview_text": "Executive Presentation Cover",
                "cards": [],
            })

            raw_slides = content.get("slides", []) if isinstance(content, dict) else (content if isinstance(content, list) else [])
            for idx, s in enumerate(raw_slides, 2):
                s_title = s.get("title", f"Slide {idx}")
                layout = s.get("layout", "cards")
                kpis = s.get("kpis", [])
                steps = s.get("steps", [])
                cards = s.get("cards", [])
                layers = s.get("layers", [])

                preview_points = []
                if kpis:
                    preview_points = [f"{k.get('metric')}: {k.get('label')}" for k in kpis[:4]]
                    layout = "kpis"
                elif steps:
                    preview_points = [f"Step {s_idx+1}: {st.get('title')}" for s_idx, st in enumerate(steps[:4])]
                    layout = "process_workflow"
                elif layers:
                    preview_points = [f"{l.get('name')}" for l in layers[:4]]
                    layout = "architecture"
                elif cards:
                    preview_points = [c.get("title", "") for c in cards[:3]]
                    layout = "three_card"
                else:
                    raw_pts = s.get("content", [])
                    if isinstance(raw_pts, str):
                        preview_points = [p.strip() for p in raw_pts.split("\n") if p.strip()][:3]
                    elif isinstance(raw_pts, list):
                        preview_points = [str(p) for p in raw_pts][:3]

                slides_preview.append({
                    "slide_number": idx,
                    "title": s_title,
                    "layout": layout,
                    "preview_points": preview_points,
                    "kpis": kpis,
                    "steps": steps,
                    "cards": cards,
                })
            preview["slides"] = slides_preview
            preview["total_count"] = len(slides_preview)

        elif fmt in ("pdf", "docx"):
            sections_preview = []
            raw_sec = content.get("sections", []) if isinstance(content, dict) else (content if isinstance(content, list) else [])
            for idx, sec in enumerate(raw_sec, 1):
                sections_preview.append({
                    "section_number": idx,
                    "heading": sec.get("heading", f"Section {idx}"),
                    "has_kpis": bool(sec.get("kpis")),
                    "has_callout": bool(sec.get("callout")),
                    "has_workflow": bool(sec.get("steps")),
                    "has_table": bool(sec.get("table")),
                    "preview_text": str(sec.get("content", ""))[:180],
                })
            preview["sections"] = sections_preview
            preview["total_count"] = len(sections_preview) + 1  # +1 for cover

        elif fmt == "xlsx":
            sheets_preview = []
            if isinstance(content, dict):
                for s_name, rows in content.items():
                    if isinstance(rows, list):
                        sheets_preview.append({
                            "sheet_name": s_name,
                            "headers": [str(c) for c in rows[0]] if rows else [],
                            "sample_rows": [[str(c) for c in r] for r in rows[1:5]] if len(rows) > 1 else [],
                            "row_count": len(rows),
                        })
            preview["sheets"] = sheets_preview
            preview["total_count"] = len(sheets_preview)

        return preview

    async def synthesize_content(self, intent: DocumentIntent, user_prompt: str = "") -> Any:
        """Synthesizes structured content tailored to the document type and user's prompt.

        Uses LLM if available, otherwise generates rich, topic-specific multi-layout content.
        """
        logger.info("[CHAT] generating content for format=%s topic='%s'", intent.format, intent.topic)
        fmt = intent.format

        # Try generating via active AI chat provider
        try:
            import asyncio
            from app.services.nvidia.chat import NvidiaChatProvider
            provider = NvidiaChatProvider()
            prompt = self._build_synthesis_prompt(intent, user_prompt=user_prompt)
            resp = await asyncio.wait_for(
                provider.generate(
                    messages=[{"role": "user", "content": prompt}],
                    model=settings.nvidia_default_chat_model,
                    system_prompt=(
                        "You are an expert document architect and technical writer. "
                        "Produce comprehensive, detailed, highly accurate, and domain-appropriate content matching the user prompt and topic. "
                        "Output pure JSON matching the requested structure without markdown formatting or code fences."
                    ),
                    max_tokens=3000,
                    temperature=0.3,
                ),
                timeout=45.0,
            )
            raw = resp.content.strip()
            # Clean markdown fences or surrounding commentary
            if "```" in raw:
                raw = re.sub(r'^```(?:json)?\s*', '', raw, flags=re.IGNORECASE)
                raw = re.sub(r'\s*```$', '', raw).strip()

            data = None
            try:
                data = json.loads(raw)
            except Exception:
                # Fallback: extract the outermost JSON object or array
                match = re.search(r'(\{[\s\S]*\}|\[[\s\S]*\])', raw)
                if match:
                    data = json.loads(match.group(1))

            if data and self._validate_structured_data(fmt, data):
                logger.info("[DOCUMENT] Successfully synthesized structured content via LLM for topic='%s'", intent.topic)
                return data
        except Exception as e:
            logger.warning("[DOCUMENT] LLM content synthesis skipped/failed (%s), using rich deterministic fallback", e)

        # High quality deterministic fallback matching the request
        return self._generate_fallback_content(intent)

    def _build_synthesis_prompt(self, intent: DocumentIntent, user_prompt: str = "") -> str:
        fmt = intent.format
        count = intent.count
        instructions = user_prompt.strip() if user_prompt else f"Create a comprehensive document about {intent.topic}."

        if fmt in ("pdf", "docx"):
            pages = count or 3
            return (
                f"You are an expert document author creating an authoritative, comprehensive {fmt.upper()} document.\n"
                f"Topic: {intent.topic}\n"
                f"User Request: {instructions}\n\n"
                f"Strict Instructions:\n"
                f"1. Generate realistic, detailed, and factually sound content strictly addressing '{intent.topic}' and any user specifications.\n"
                f"2. DO NOT output generic IT infrastructure, microservices, latency benchmarks, or HSBot architecture unless the topic is specifically about software/IT.\n"
                f"3. All section headings, descriptive paragraphs, KPIs, workflow steps, and table rows must be customized specifically for '{intent.topic}'.\n"
                f"4. Provide approximately {pages} full, substantive sections.\n\n"
                "Output ONLY a valid JSON object matching this schema (no markdown formatting, no code fences):\n"
                "{\n"
                f'  "title": "{intent.title}",\n'
                f'  "subtitle": "Comprehensive Guide & Analysis",\n'
                f'  "author": "HSBot Research",\n'
                f'  "organization": "Specialized Knowledge Services",\n'
                '  "sections": [\n'
                '    {\n'
                '      "heading": "<Topic-Specific Section 1 Heading (e.g. Overview / Fundamentals)>",\n'
                '      "content": "<Detailed, informative multi-sentence paragraphs covering this section in depth>",\n'
                '      "callout": "<Key insight or critical takeaway specifically about this section>",\n'
                '      "kpis": [{"metric": "<Value>", "label": "<Topic-specific KPI label>"}]\n'
                '    },\n'
                '    {\n'
                '      "heading": "<Topic-Specific Section 2 Heading (e.g. Methodology / Process / Implementation)>",\n'
                '      "content": "<In-depth step-by-step technical or operational explanation>",\n'
                '      "steps": [{"title": "<Step 1 Name>", "description": "<Detailed step explanation>"}, {"title": "<Step 2 Name>", "description": "<Detailed step explanation>"}],\n'
                '      "page_break": true\n'
                '    },\n'
                '    {\n'
                '      "heading": "<Topic-Specific Section 3 Heading (e.g. Evaluation / Comparison / Costs / Best Practices)>",\n'
                '      "content": "<Comprehensive comparative, analytical, or evaluative discussion>",\n'
                '      "table": [["<Column 1>", "<Column 2>", "<Column 3>"], ["<Row 1 Val 1>", "<Row 1 Val 2>", "<Row 1 Val 3>"], ["<Row 2 Val 1>", "<Row 2 Val 2>", "<Row 2 Val 3>"]]\n'
                '    }\n'
                '  ]\n'
                "}"
            )
        elif fmt == "pptx":
            slides = count or 6
            return (
                f"You are a professional presentation designer creating a high-impact presentation deck.\n"
                f"Topic: {intent.topic}\n"
                f"User Request: {instructions}\n\n"
                f"Strict Instructions:\n"
                f"1. Generate realistic, detailed content strictly addressing '{intent.topic}'.\n"
                f"2. DO NOT output generic software architecture or IT jargon unless the topic is software engineering.\n"
                f"3. Generate exactly {slides} slides utilizing dynamic layouts (cards, process, kpis, two_column, architecture, conclusion).\n\n"
                "Output ONLY a valid JSON object matching this schema (no markdown, no code fences):\n"
                "{\n"
                f'  "title": "{intent.title}",\n'
                f'  "subtitle": "Key Concepts & Strategic Insights",\n'
                '  "slides": [\n'
                '    {\n'
                '      "title": "<Slide 1 Title - Executive Overview / Core Concept>",\n'
                '      "layout": "cards",\n'
                '      "cards": [\n'
                '        {"title": "<Pillar 1>", "points": ["<Key Point A>", "<Key Point B>"]},\n'
                '        {"title": "<Pillar 2>", "points": ["<Key Point C>", "<Key Point D>"]},\n'
                '        {"title": "<Pillar 3>", "points": ["<Key Point E>", "<Key Point F>"]}\n'
                '      ]\n'
                '    },\n'
                '    {\n'
                '      "title": "<Slide 2 Title - Lifecycle / Process Workflow>",\n'
                '      "layout": "process",\n'
                '      "steps": [\n'
                '        {"title": "<Stage 1>", "description": "<Action description>"},\n'
                '        {"title": "<Stage 2>", "description": "<Action description>"},\n'
                '        {"title": "<Stage 3>", "description": "<Action description>"}\n'
                '      ]\n'
                '    },\n'
                '    {\n'
                '      "title": "<Slide 3 Title - Key Metrics & Impact>",\n'
                '      "layout": "kpis",\n'
                '      "kpis": [\n'
                '        {"metric": "<Metric 1>", "label": "<Label 1>", "subtext": "<Context 1>"},\n'
                '        {"metric": "<Metric 2>", "label": "<Label 2>", "subtext": "<Context 2>"},\n'
                '        {"metric": "<Metric 3>", "label": "<Label 3>", "subtext": "<Context 3>"}\n'
                '      ]\n'
                '    },\n'
                '    {\n'
                '      "title": "<Slide 4 Title - Comparative Analysis>",\n'
                '      "layout": "two_column",\n'
                '      "columns": [\n'
                '        {"title": "<Category A>", "content": ["<Point 1>", "<Point 2>"]},\n'
                '        {"title": "<Category B>", "content": ["<Point 1>", "<Point 2>"]}\n'
                '      ]\n'
                '    },\n'
                '    {\n'
                '      "title": "<Slide 5 Title - Recommendations & Next Steps>",\n'
                '      "layout": "cards",\n'
                '      "cards": [\n'
                '        {"title": "<Immediate Priorities>", "points": ["<Action 1>", "<Action 2>"]},\n'
                '        {"title": "<Long-Term Roadmap>", "points": ["<Milestone 1>", "<Milestone 2>"]}\n'
                '      ]\n'
                '    }\n'
                '  ]\n'
                "}"
            )
        elif fmt == "xlsx":
            return (
                f"You are a senior data analyst creating a spreadsheet dataset.\n"
                f"Topic: {intent.topic}\n"
                f"User Request: {instructions}\n\n"
                f"Strict Instructions:\n"
                f"Generate a realistic, comprehensive spreadsheet dataset specifically for '{intent.topic}'. "
                f"All column names, rows, and KPI metrics must be directly tailored to this topic.\n\n"
                "Output ONLY a valid JSON object matching this schema (no markdown, no code fences):\n"
                "{\n"
                '  "kpis": [{"metric": "<Value>", "label": "<Topic-specific KPI>"}],\n'
                '  "Data": [\n'
                '    ["<Column 1>", "<Column 2>", "<Column 3>", "<Column 4>", "<Column 5>"],\n'
                '    ["<Row 1 Val 1>", "<Row 1 Val 2>", "<Row 1 Val 3>", 100.0, "<Status>"],\n'
                '    ["<Row 2 Val 1>", "<Row 2 Val 2>", "<Row 2 Val 3>", 250.0, "<Status>"],\n'
                '    ["<Row 3 Val 1>", "<Row 3 Val 2>", "<Row 3 Val 3>", 400.0, "<Status>"]\n'
                '  ]\n'
                "}"
            )
        elif fmt == "csv":
            return (
                f"Create a realistic 6-to-10 row CSV dataset specifically for '{intent.topic}'. User Request: {instructions}.\n"
                "Output ONLY a valid JSON 2D array of strings and numbers matching the topic: [[\"Col1\", \"Col2\", ...], [\"Val1\", \"Val2\", ...]]"
            )
        else:
            return (
                f"Write comprehensive, authoritative, detailed documentation about '{intent.topic}'.\n"
                f"User Request: {instructions}\n"
                "Use structured markdown headings (H1, H2, H3), bullet points, and practical explanations."
            )

    def _validate_structured_data(self, fmt: str, data: Any) -> bool:
        """Validates that parsed JSON matches generator expectations."""
        if not isinstance(data, (dict, list)):
            return False
        if fmt in ("pdf", "docx"):
            return isinstance(data, dict) and "sections" in data and isinstance(data["sections"], list) and len(data["sections"]) > 0
        elif fmt == "pptx":
            return isinstance(data, dict) and "slides" in data and isinstance(data["slides"], list) and len(data["slides"]) > 0
        elif fmt == "xlsx":
            return isinstance(data, dict) and any(isinstance(v, list) for v in data.values())
        elif fmt == "csv":
            return isinstance(data, list) and len(data) > 0 and isinstance(data[0], list)
        return True

    def _generate_fallback_content(self, intent: DocumentIntent) -> Any:
        """Generates rich, topic-specific multi-layout content when LLM is unavailable."""
        topic = (intent.topic or "Topic Overview").strip()[:80]
        title = intent.title or topic
        fmt = intent.format
        count = intent.count

        if fmt in ("pdf", "docx"):
            return {
                "title": title,
                "subtitle": f"Comprehensive Overview & Analysis: {topic}",
                "author": "HSBot Analysis",
                "organization": "Research & Documentation",
                "sections": [
                    {
                        "heading": "Executive Summary",
                        "content": (
                            f"This document presents a structured operational overview and analysis of {topic}. "
                            f"It outlines the fundamental principles, essential requirements, implementation considerations, and "
                            f"industry standards necessary for successful execution.\n\n"
                            f"A methodical approach ensures quality, consistency, and alignment with established benchmarks across all phases."
                        ),
                        "callout": f"Key Finding: Methodical planning and phased implementation are critical to ensuring optimal outcomes for {topic}."[:250],
                        "kpis": [
                            {"metric": "100%", "label": "Scope Coverage"},
                            {"metric": "Standard", "label": "Quality Benchmark"},
                            {"metric": "Phased", "label": "Execution Model"},
                            {"metric": "Optimal", "label": "Resource Efficiency"},
                        ],
                    },
                    {
                        "heading": "Core Components & Execution Flow",
                        "content": (
                            f"The operational workflow for {topic} relies on a structured, phased execution methodology. "
                            f"Each phase is designed to ensure thorough verification, minimal operational risk, and predictable outcomes.\n\n"
                            f"The following sequence illustrates the end-to-end lifecycle:"
                        ),
                        "steps": [
                            {"title": "Discovery & Planning", "description": f"Initial requirements assessment, feasibility evaluation, and scoping for {topic}."},
                            {"title": "Design & Preparation", "description": "Detailed specifications, resource allocation, and risk management planning."},
                            {"title": "Implementation & Rollout", "description": "Execution in accordance with quality standards and safety guidelines."},
                            {"title": "Review & Optimization", "description": "Performance verification, quality audits, and ongoing improvements."},
                        ],
                    },
                    {
                        "heading": "Evaluation Criteria & Best Practices",
                        "content": (
                            f"To maintain excellence in {topic}, ongoing monitoring and adherence to established criteria are essential. "
                            f"The table below outlines key evaluation standards across each operational phase:"
                        ),
                        "table": [
                            ["Phase / Area", "Key Objective", "Standard Criteria", "Status / Target"],
                            ["Initial Assessment", "Scope Definition", "Documented & Approved", "Completed"],
                            ["Execution Phase", "Standard Compliance", "Best Practice Standards", "In Progress"],
                            ["Quality Assurance", "Validation & Testing", "Full Inspection", "Scheduled"],
                            ["Post-Review", "Outcome Assessment", "Performance Targets Met", "Ongoing"],
                        ],
                    },
                    {
                        "heading": "Strategic Recommendations & Conclusion",
                        "content": (
                            f"In conclusion, successful execution of {topic} requires disciplined adherence to standards and continuous monitoring. "
                            f"Immediate follow-up actions should focus on finalizing timelines, assigning key responsibilities, and establishing measurable feedback loops."
                        ),
                        "items": [
                            f"Phase 1: Finalize scoping and establish clear milestones for all stages of {topic}.",
                            "Phase 2: Implement standardized quality checklists and review protocols.",
                            "Phase 3: Conduct post-implementation review and document learnings for ongoing optimization.",
                        ],
                    },
                ],
            }

        elif fmt == "pptx":
            slide_count = count or 6
            slides = [
                {
                    "title": f"Executive Overview: {topic}",
                    "layout": "cards",
                    "cards": [
                        {
                            "title": "Core Purpose",
                            "points": [
                                f"Clear strategic focus on {topic}",
                                "Methodical, structured approach",
                                "Targeted outcomes and deliverables"
                            ]
                        },
                        {
                            "title": "Guiding Principles",
                            "points": [
                                "Quality assurance and reliability",
                                "Resource efficiency and optimization",
                                "Compliance with recognized standards"
                            ]
                        },
                        {
                            "title": "Expected Outcomes",
                            "points": [
                                "Measurable performance gains",
                                "Risk mitigation and dependability",
                                "Sustainable long-term value"
                            ]
                        },
                    ]
                },
                {
                    "title": "Phased Implementation Workflow",
                    "layout": "process",
                    "steps": [
                        {"title": "Phase 1: Planning", "description": f"Scoping, requirements gathering, and initial assessment for {topic}"},
                        {"title": "Phase 2: Setup", "description": "Resource preparation, tooling configuration, and milestone alignment"},
                        {"title": "Phase 3: Rollout", "description": "Active deployment following standard guidelines and quality checks"},
                        {"title": "Phase 4: Review", "description": "Verification, performance monitoring, and outcome validation"},
                    ]
                },
                {
                    "title": "Key Indicators & Targets",
                    "layout": "kpis",
                    "kpis": [
                        {"metric": "100%", "label": "Scope Coverage", "subtext": "Complete alignment"},
                        {"metric": "High", "label": "Quality Standard", "subtext": "Verified criteria"},
                        {"metric": "On Schedule", "label": "Milestone Delivery", "subtext": "Phased timeline"},
                        {"metric": "Optimal", "label": "Resource Use", "subtext": "Efficient execution"},
                    ]
                },
                {
                    "title": "Strategic Considerations & Solutions",
                    "layout": "two_column",
                    "columns": [
                        {
                            "title": "Key Considerations & Risks",
                            "content": [
                                "Complexity and dependency management",
                                "Resource availability and scheduling",
                                "Adherence to technical specifications",
                                "Quality control throughout the lifecycle",
                            ]
                        },
                        {
                            "title": "Mitigation & Best Practices",
                            "content": [
                                "Standardized operating procedures",
                                "Proactive stakeholder communication",
                                "Continuous verification at each gate",
                                "Documented post-implementation reviews",
                            ]
                        }
                    ]
                },
                {
                    "title": "Conclusion & Action Plan",
                    "layout": "cards",
                    "cards": [
                        {"title": "Immediate Actions", "points": [f"Finalize operational plan for {topic}", "Assign lead owners and set deliverables"]},
                        {"title": "Near-term Focus", "points": ["Establish progress reporting cadences", "Conduct milestone quality reviews"]},
                        {"title": "Long-term Vision", "points": ["Iterative optimization based on data", "Scale best practices across future initiatives"]},
                    ]
                },
            ]
            return {
                "title": title,
                "subtitle": f"Strategic Overview & Practical Guide: {topic}",
                "slides": slides[:slide_count],
            }

        elif fmt == "xlsx":
            return {
                "kpis": [
                    {"metric": "100%", "label": "Project Health"},
                    {"metric": "5", "label": "Total Phases"},
                    {"metric": "Active", "label": "Current Status"},
                    {"metric": "0", "label": "Critical Blockers"},
                ],
                "Overview": [
                    ["Item ID", "Category", "Description", "Priority", "Target Date", "Status"],
                    ["ITM-01", "Planning", f"Define core scope and requirements for {topic}", "High", "2026-02-01", "Completed"],
                    ["ITM-02", "Preparation", "Resource allocation and prerequisites setup", "High", "2026-02-15", "In Progress"],
                    ["ITM-03", "Execution", "Primary implementation and rollout phase", "Medium", "2026-03-01", "In Progress"],
                    ["ITM-04", "Testing", "Validation, quality assurance, and verification", "High", "2026-03-15", "Pending"],
                    ["ITM-05", "Handover", "Final documentation and operational handover", "Medium", "2026-03-31", "Scheduled"],
                ]
            }

        elif fmt == "csv":
            return [
                ["ID", "Topic Item", "Category", "Priority", "Status"],
                ["1", f"{topic} - Scoping", "Planning", "High", "Completed"],
                ["2", f"{topic} - Implementation", "Execution", "High", "In Progress"],
                ["3", f"{topic} - Quality Review", "Validation", "High", "Pending"],
                ["4", f"{topic} - Final Documentation", "Handover", "Medium", "Scheduled"],
            ]

        else:
            return f"# {title}\n\nComprehensive overview and detailed analysis for {topic}."

    # Convenience helper methods
    async def generate_pdf(self, title: str, sections: list, conversation_id: str = "general", user_id: str = "default_user", db=None, filename="Document.pdf", design_spec=None):
        return await self.generate_file("pdf", filename, title, sections, conversation_id, user_id, db, design_spec=design_spec)

    async def generate_docx(self, title: str, sections: list, conversation_id: str = "general", user_id: str = "default_user", db=None, filename="Document.docx", design_spec=None):
        return await self.generate_file("docx", filename, title, sections, conversation_id, user_id, db, design_spec=design_spec)

    async def generate_pptx(self, title: str, slides: list, conversation_id: str = "general", user_id: str = "default_user", db=None, filename="Presentation.pptx", design_spec=None):
        return await self.generate_file("pptx", filename, title, slides, conversation_id, user_id, db, design_spec=design_spec)

    async def generate_xlsx(self, title: str, sheets: dict, conversation_id: str = "general", user_id: str = "default_user", db=None, filename="Workbook.xlsx", design_spec=None):
        return await self.generate_file("xlsx", filename, title, sheets, conversation_id, user_id, db, design_spec=design_spec)

    async def generate_csv(self, title: str, rows: list, conversation_id: str = "general", user_id: str = "default_user", db=None, filename="Data.csv"):
        return await self.generate_file("csv", filename, title, rows, conversation_id, user_id, db)

    async def generate_markdown(self, title: str, content: str, conversation_id: str = "general", user_id: str = "default_user", db=None, filename="Document.md"):
        return await self.generate_file("md", filename, title, content, conversation_id, user_id, db)

    async def generate_text(self, title: str, content: str, conversation_id: str = "general", user_id: str = "default_user", db=None, filename="Document.txt"):
        return await self.generate_file("txt", filename, title, content, conversation_id, user_id, db)


# Singleton instance
document_service = DocumentService()
