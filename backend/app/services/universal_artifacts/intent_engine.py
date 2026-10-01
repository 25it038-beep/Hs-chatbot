import re
import os
from typing import Optional, List, Dict, Any, Tuple
from app.services.universal_artifacts.contracts import (
    OutputIntent,
    ArtifactCategory,
    ArtifactSpec,
)
from app.services.universal_artifacts.registry import ArtifactFormatRegistryV2


class ResponseOutputIntentEngine:
    """
    Universal Response Output Intent Engine (§1, §4, §45, §46, §47).
    Determines whether a user's prompt requests:
    - CHAT
    - FILE
    - CHAT_AND_FILE
    - MULTIPLE_FILES
    - PROJECT / ARCHIVE
    Infers requested file formats, extracts parameters (counts, units, custom filenames),
    and flags conversational edits or ambiguities.
    """

    # Verbs indicating file generation or transformation
    GEN_VERBS = r"(?:create|make|generate|build|write|produce|prepare|export|save|convert|turn(?:\s+this)?\s+into|download|put(?:\s+this)?\s+in(?:to)?)"

    # Format Regex Patterns
    FORMAT_PATTERNS = [
        # Explicit Code Files (high priority before generic words)
        (rf"\b(?:{GEN_VERBS})?\b.*?\b(?:python\s+script|python\s+program|\.py\s+file|save\s+as\s+python|as\s+a\s+\.py|export\s+to\s+[a-zA-Z0-9_\-]+\.py)\b", "py", None),
        (rf"\b(?:{GEN_VERBS})?\b.*?\b(?:javascript\s+file|\.js\s+file|node\s+script|export\s+to\s+[a-zA-Z0-9_\-]+\.js)\b", "js", None),
        (rf"\b(?:{GEN_VERBS})?\b.*?\b(?:typescript\s+file|\.ts\s+file|export\s+to\s+[a-zA-Z0-9_\-]+\.ts)\b", "ts", None),
        (rf"\b(?:{GEN_VERBS})?\b.*?\b(?:html\s+file|html\s+page|\.html\s+file)\b", "html", None),
        (rf"\b(?:{GEN_VERBS})?\b.*?\b(?:css\s+file|stylesheet|\.css\s+file)\b", "css", None),
        (rf"\b(?:{GEN_VERBS})?\b.*?\b(?:bash\s+script|shell\s+script|\.sh\s+file)\b", "sh", None),
        (rf"\b(?:{GEN_VERBS})?\b.*?\b(?:powershell\s+script|\.ps1\s+file)\b", "ps1", None),

        # Presentations
        (rf"\b(?:{GEN_VERBS})?\b.*?\b(\d+)?\s*(?:-| )*(?:slide|slides)?\s*(?:powerpoint|pptx?|presentation|slide\s+deck|pitch\s+deck|slides)\b", "pptx", "slide"),
        
        # Spreadsheets
        (rf"\b(?:{GEN_VERBS})?\b.*?\b(?:excel|xlsx?|spreadsheet|workbook|sheet)\b", "xlsx", "sheet"),
        (rf"\b(?:{GEN_VERBS})\b.*?\b(?:csv|comma\s+separated)\b|\b(?:csv\s+file|csv\s+sheet|as\s+csv|\.csv\b)\b", "csv", "row"),
        (rf"\b(?:{GEN_VERBS})\b.*?\b(?:tsv|tab\s+separated)\b|\b(?:tsv\s+file|as\s+tsv|\.tsv\b)\b", "tsv", "row"),

        # Documents
        (rf"\b(?:{GEN_VERBS})?\b.*?\b(\d+)?\s*(?:-| )*(?:page|pages)?\s*(?:pdf|pdf\s+report|report\s+pdf|pdf\s+document|pdf\s+notes)\b", "pdf", "page"),
        (rf"\b(?:{GEN_VERBS})?\b.*?\b(?:word\s+doc(?:ument)?|docx?|word\s+file)\b", "docx", "page"),
        (rf"\b(?:{GEN_VERBS})?\b.*?\b(?:markdown|md\s+file)\b", "md", None),
        (rf"\b(?:{GEN_VERBS})?\b.*?\b(?:text\s+file|txt\s+file|plain\s+text\s+file)\b", "txt", None),
        (rf"\b(?:{GEN_VERBS})?\b.*?\b(?:rtf|rich\s+text)\b", "rtf", None),

        # Structured Data
        (rf"\b(?:{GEN_VERBS})?\b.*?\b(?:json\s+file|jsonl?\b|json\s+data|as\s+json)\b", "json", None),
        (rf"\b(?:{GEN_VERBS})?\b.*?\b(?:yaml\s+file|yml\s+file|as\s+yaml)\b", "yaml", None),
        (rf"\b(?:{GEN_VERBS})?\b.*?\b(?:xml\s+file|as\s+xml)\b", "xml", None),
        (rf"\b(?:{GEN_VERBS})?\b.*?\b(?:sql\s+script|sql\s+file|sql\s+dump|database\s+schema\s+file)\b", "sql", None),

        # Media & Vector
        (rf"\b(?:{GEN_VERBS})?\b.*?\b(?:svg\s+file|svg\s+vector|svg\s+image|as\s+svg)\b", "svg", None),
        (rf"\b(?:{GEN_VERBS})?\b.*?\b(?:png\s+image|png\s+file)\b", "png", None),

        # Archives & Projects
        (rf"\b(?:{GEN_VERBS})?\b.*?\b(?:zip\s+file|zip\s+archive|as\s+a\s+zip|\.zip)\b", "zip", "file"),
        (rf"\b(?:{GEN_VERBS})\b.*?\b(?:complete\s+project|entire\s+project|project\s+files|website\s+bundle)\b", "zip", "file"),
    ]

    # Explicit Dual Request Signals: CHAT_AND_FILE (§1, §45)
    DUAL_INTENT_SIGNALS = [
        r"\b(?:give\s+me|show\s+me|explain|tell\s+me|write)\b.*?\b(?:and\s+(?:create|make|save|export|turn|generate|give\s+me|provide|attach|include|deliver|send))\b",
        r"\b(?:answer\s+and\s+(?:create|make|export|give|save|provide|attach))\b",
        r"\b(?:explain\s+.*?\s+and\s+(?:make|create|save|export|give\s+me|provide|attach|include))\b",
        r"\b(?:in\s+the\s+chat\s+and\s+(?:as|in)\s+a\s+file)\b",
        r"\b(?:both\s+in\s+chat\s+and\s+(?:as|in)\s+a\s+file)\b",
    ]

    # Conversational Edit Signals (§19, §20, §43)
    CONVERSATIONAL_EDIT_SIGNALS = [
        r"\b(?:change|update|modify|edit|adjust)\s+the\s+(?:title|header|content|slides?|document|pdf|presentation|file|spreadsheet)\b",
        r"\b(?:add|insert)\s+(?:a\s+)?(?:cover\s+page|slide|page|table|column|row|section|chart)\b",
        r"\b(?:convert|export|turn)\s+this\s+(?:in)?to\s+(?:pdf|excel|word|powerpoint|csv|json)\b",
        r"\b(?:make\s+the\s+slides\s+more\s+professional|make\s+it\s+dark|use\s+a\s+table)\b",
    ]

    @classmethod
    def detect_intent(
        cls,
        message: str = "",
        uploaded_files: Optional[List[str]] = None,
        has_previous_artifact: bool = False,
        previous_artifact_meta: Optional[Dict[str, Any]] = None,
        prompt: Optional[str] = None,
        conversation_history: Optional[List[Any]] = None,
        **kwargs,
    ) -> Optional[ArtifactSpec]:
        """Analyzes a message to determine if a real artifact should be synthesized (§1)."""
        msg = (message or prompt or "").strip()
        lower = msg.lower()

        # 1. Negative Checks: Pure informational queries
        neg_patterns = [
            r'^(what|how|why|when|where|who)\s+(is|are|was|were|do|does|can)\s+(a|an|the)?\s*(pdf|word|docx?|powerpoint|pptx?|excel|xlsx?|csv|spreadsheet|presentation|json|yaml|zip|svg)\b',
            r'\bexplain\s+(what\s+is\s+a\s+|how\s+to\s+use\s+)?(pdf|word|powerpoint|excel|csv|json|yaml|zip)\b',
            r'\btell\s+me\s+about\s+(pdf|word|powerpoint|excel|csv|json|yaml)\b',
            r'\bdifference\s+between\b.*(pdf|word|excel|csv)',
        ]
        for np in neg_patterns:
            if re.search(np, lower):
                return None

        # 2. Conversational Edit Check (§19, §20)
        is_edit = False
        edit_instruction = None
        for ep in cls.CONVERSATIONAL_EDIT_SIGNALS:
            m_edit = re.search(ep, lower)
            if m_edit:
                is_edit = True
                edit_instruction = msg
                break

        # Check conversion intent (e.g. "convert this to Excel", "convert that to PDF", "make it a PDF")
        convert_match = re.search(r"\b(?:convert|export|turn|transform)\s+(?:this|that|it)?\s*(?:in)?to\s+(\w+)\b", lower)
        target_conv_fmt = None
        if convert_match:
            cand = convert_match.group(1).lower()
            if cand in ["excel", "spreadsheet", "xlsx", "xls"]: target_conv_fmt = "xlsx"
            elif cand in ["word", "doc", "docx"]: target_conv_fmt = "docx"
            elif cand in ["powerpoint", "slides", "presentation", "pptx", "ppt"]: target_conv_fmt = "pptx"
            elif cand in ["pdf"]: target_conv_fmt = "pdf"
            elif cand in ["csv"]: target_conv_fmt = "csv"
            elif cand in ["json"]: target_conv_fmt = "json"

        # 3. Detect Output Format and Parameters
        detected_fmt = target_conv_fmt
        detected_unit = None
        count_val = None

        if not detected_fmt:
            for pattern, fmt_key, unit in cls.FORMAT_PATTERNS:
                m = re.search(pattern, lower)
                if m:
                    detected_fmt = fmt_key
                    detected_unit = unit
                    # Extract count if present in groups
                    try:
                        for g in m.groups():
                            if g and g.isdigit():
                                count_val = int(g)
                                break
                    except Exception:
                        pass
                    break

        # 4. Check for user-uploaded file transform requests (§22, §48)
        # e.g., "turn this into a 10-slide presentation"
        if uploaded_files and len(uploaded_files) > 0 and not detected_fmt:
            if any(w in lower for w in ["slide", "presentation", "deck", "pitch"]):
                detected_fmt = "pptx"
                detected_unit = "slide"
            elif any(w in lower for w in ["report", "document", "pdf", "summary"]):
                detected_fmt = "pdf"
                detected_unit = "page"
            elif any(w in lower for w in ["sheet", "table", "excel", "spreadsheet"]):
                detected_fmt = "xlsx"
                detected_unit = "sheet"

        # 5. Check for ambiguous file request (§46)
        # e.g., "Make this into a file" / "Save this to a file"
        is_ambiguous = False
        suggested = ["pdf", "docx", "xlsx", "pptx", "txt"]
        if not detected_fmt and re.search(r"\b(?:make|save|export|turn)\s+this\s+(?:in)?to\s+(?:a\s+)?file\b", lower):
            is_ambiguous = True
            detected_fmt = "pdf"  # sensible default while indicating ambiguity

        # If no format and not edit/file request, return None -> CHAT ONLY
        if not detected_fmt and not is_edit:
            # Check if user asked to "create a script" or "create a website"
            if re.search(r"\b(?:create|make|build)\s+(?:a\s+)?(?:python\s+script|website|web\s+page)\b", lower):
                detected_fmt = "zip" if "website" in lower else "py"
            else:
                return None

        detected_fmt = detected_fmt or (previous_artifact_meta.get("format") if previous_artifact_meta else "pdf")
        category = ArtifactFormatRegistryV2.get_category(detected_fmt)

        # 6. Determine Output Intent Mode (CHAT, FILE, CHAT_AND_FILE, MULTIPLE_FILES, PROJECT, ARCHIVE)
        is_dual = any(re.search(ds, lower) for ds in cls.DUAL_INTENT_SIGNALS)
        
        if detected_fmt == "zip" or "project" in lower:
            output_intent = OutputIntent.PROJECT if "project" in lower else OutputIntent.ARCHIVE
        elif is_dual:
            output_intent = OutputIntent.CHAT_AND_FILE
        else:
            output_intent = OutputIntent.FILE

        # 7. Extract Custom Filename if user specified (§29)
        # e.g., "Save it as final_report.pdf" or "filename: sales_data.xlsx"
        filename_match = re.search(r'(?:save\s+(?:it\s+)?as|name\s+it|filename:?)\s+([a-zA-Z0-9_\-\.]+)', msg, re.IGNORECASE)
        custom_name = None
        if filename_match:
            candidate_name = filename_match.group(1).strip()
            # Strip invalid path chars
            candidate_name = re.sub(r'[^a-zA-Z0-9_\-\.]', '', candidate_name)
            if candidate_name:
                if not candidate_name.endswith(f".{detected_fmt}"):
                    candidate_name = f"{candidate_name.rsplit('.', 1)[0]}.{detected_fmt}"
                custom_name = candidate_name

        # Derive Topic & Title
        topic = re.sub(r'^(?:create|make|generate|build|write|save|export|turn|produce)\s+(?:a\s+|an\s+|the\s+)?', '', msg, flags=re.IGNORECASE).strip()
        topic = re.sub(r'\b(?:in|as|to|into)\s+(?:a\s+|an\s+)?(?:pdf|word|excel|powerpoint|pptx?|xlsx?|docx?|csv|json|py|zip|file)\b', '', topic, flags=re.IGNORECASE).strip()
        topic = re.sub(r'^[,\.\s\-:]+', '', topic).strip()
        if not topic or len(topic) < 3:
            topic = "Generated Deliverable"

        title = topic[:60].strip().title()
        if not custom_name:
            clean_base = re.sub(r'[^a-zA-Z0-9_]', '_', title.lower()).strip('_')
            clean_base = re.sub(r'_+', '_', clean_base)[:35] or "document"
            version_suffix = "_v2" if is_edit else ""
            custom_name = f"{clean_base}{version_suffix}.{detected_fmt}"

        parent_id = None
        if is_edit and previous_artifact_meta:
            parent_id = previous_artifact_meta.get("id")

        return ArtifactSpec(
            format=detected_fmt,
            output_intent=output_intent,
            title=title,
            filename=custom_name,
            category=category,
            topic=topic,
            user_prompt=msg,
            count=count_val,
            count_unit=detected_unit,
            is_conversational_edit=is_edit,
            is_format_conversion=bool(target_conv_fmt),
            parent_artifact_id=parent_id,
            edit_instruction=edit_instruction,
            source_files=uploaded_files or [],
            requires_chat_response=(output_intent == OutputIntent.CHAT_AND_FILE),
            is_ambiguous=is_ambiguous,
            suggested_formats=suggested if is_ambiguous else [],
        )


output_intent_engine = ResponseOutputIntentEngine()
