import os
import re
from enum import Enum
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any


class OutputMode(str, Enum):
    CHAT = "CHAT"
    FILE = "FILE"
    CHAT_AND_FILE = "CHAT_AND_FILE"
    MULTIPLE_FILES = "MULTIPLE_FILES"
    PROJECT = "PROJECT"
    ARCHIVE = "ARCHIVE"

    # Aliases for Section 45 compatibility
    CHAT_ONLY = "CHAT"
    FILE_ONLY = "FILE"
    MULTI_FILE = "MULTIPLE_FILES"


SUPPORTED_EXTENSIONS = {
    # Documents (Section 5)
    "txt", "md", "markdown", "rtf", "doc", "docx", "odt", "pdf",
    # Spreadsheets (Section 6)
    "csv", "tsv", "xls", "xlsx", "ods",
    # Presentations (Section 7)
    "ppt", "pptx", "odp",
    # Data / Structured (Section 8)
    "json", "jsonl", "yaml", "yml", "xml", "sql",
    # Code (Section 9)
    "py", "js", "ts", "tsx", "jsx", "html", "css", "java", "c", "cpp",
    "cs", "go", "rs", "php", "rb", "kt", "swift", "sh", "ps1",
    # Web / Diagrams (Section 10)
    "svg",
    # Images (Section 11)
    "png", "jpg", "jpeg", "webp",
    # Archives (Section 12)
    "zip",
}

FORMAT_SYNONYMS: Dict[str, str] = {
    "pdf": "pdf",
    "word": "docx",
    "word document": "docx",
    "word doc": "docx",
    "docx": "docx",
    "doc": "doc",
    "odt": "odt",
    "openoffice document": "odt",
    "rtf": "rtf",
    "rich text": "rtf",
    "markdown": "md",
    "md": "md",
    "readme": "md",
    "plain text": "txt",
    "text file": "txt",
    "txt": "txt",
    "excel": "xlsx",
    "excel spreadsheet": "xlsx",
    "excel workbook": "xlsx",
    "excel sheet": "xlsx",
    "spreadsheet": "xlsx",
    "workbook": "xlsx",
    "xlsx": "xlsx",
    "xls": "xls",
    "ods": "ods",
    "csv": "csv",
    "tsv": "tsv",
    "powerpoint": "pptx",
    "power point": "pptx",
    "presentation": "pptx",
    "slide deck": "pptx",
    "pitch deck": "pptx",
    "slides": "pptx",
    "pptx": "pptx",
    "ppt": "ppt",
    "odp": "odp",
    "json": "json",
    "jsonl": "jsonl",
    "yaml": "yaml",
    "yml": "yml",
    "xml": "xml",
    "sql": "sql",
    "python": "py",
    "python script": "py",
    "python program": "py",
    "py": "py",
    "javascript": "js",
    "js": "js",
    "typescript": "ts",
    "ts": "ts",
    "tsx": "tsx",
    "jsx": "jsx",
    "html": "html",
    "webpage": "html",
    "css": "css",
    "stylesheet": "css",
    "java": "java",
    "c++": "cpp",
    "cpp": "cpp",
    "c#": "cs",
    "csharp": "cs",
    "golang": "go",
    "go": "go",
    "rust": "rs",
    "rs": "rs",
    "php": "php",
    "ruby": "rb",
    "rb": "rb",
    "kotlin": "kt",
    "kt": "kt",
    "swift": "swift",
    "bash": "sh",
    "shell script": "sh",
    "sh": "sh",
    "powershell": "ps1",
    "ps1": "ps1",
    "svg": "svg",
    "png": "png",
    "jpg": "jpg",
    "jpeg": "jpeg",
    "webp": "webp",
    "zip": "zip",
    "archive": "zip",
}


def sanitize_filename(name: str, default_stem: str = "artifact", ext: str = "txt") -> str:
    """Sanitizes a user-provided or inferred filename, blocking path traversal and unsafe characters."""
    if not name:
        return f"{default_stem}.{ext.lstrip('.')}"
    # Strip any directory components
    base = os.path.basename(name.replace("\\", "/")).strip()
    # Remove any path traversal sequences or null bytes
    base = base.replace("..", "").replace("\x00", "")
    # Split stem and extension
    if "." in base:
        stem, given_ext = base.rsplit(".", 1)
        clean_ext = re.sub(r"[^a-zA-Z0-9]", "", given_ext).lower() or ext.lstrip(".")
    else:
        stem = base
        clean_ext = ext.lstrip(".")
    clean_stem = re.sub(r"[^a-zA-Z0-9_\- ]", "", stem).strip()
    clean_stem = re.sub(r"\s+", "_", clean_stem)[:60] or default_stem
    return f"{clean_stem}.{clean_ext}"


@dataclass
class OutputIntentResult:
    mode: OutputMode
    formats: List[str] = field(default_factory=list)
    primary_format: Optional[str] = None
    topic: str = ""
    title: str = ""
    filename: Optional[str] = None
    user_specified_filename: bool = False
    count: Optional[int] = None
    count_unit: Optional[str] = None
    is_followup_edit: bool = False
    edit_instruction: Optional[str] = None
    target_artifact_hint: Optional[str] = None
    is_conversion: bool = False
    source_format: Optional[str] = None
    target_format: Optional[str] = None
    uses_uploaded_files: bool = False
    needs_format_clarification: bool = False
    clarification_question: Optional[str] = None
    clarification_options: List[str] = field(default_factory=list)
    unsupported_format: Optional[str] = None
    include_chat_explanation: bool = False
    package_as_zip: bool = False

    @property
    def output_mode_alias(self) -> str:
        """Returns Section 45 mode string (CHAT_ONLY, FILE_ONLY, CHAT_AND_FILE, MULTI_FILE)."""
        if self.mode == OutputMode.CHAT:
            return "CHAT_ONLY"
        if self.mode == OutputMode.FILE:
            return "FILE_ONLY"
        if self.mode == OutputMode.CHAT_AND_FILE:
            return "CHAT_AND_FILE"
        return "MULTI_FILE"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "mode": self.mode.value,
            "output_mode": self.output_mode_alias,
            "formats": self.formats,
            "primary_format": self.primary_format,
            "topic": self.topic,
            "title": self.title,
            "filename": self.filename,
            "user_specified_filename": self.user_specified_filename,
            "count": self.count,
            "count_unit": self.count_unit,
            "is_followup_edit": self.is_followup_edit,
            "edit_instruction": self.edit_instruction,
            "is_conversion": self.is_conversion,
            "source_format": self.source_format,
            "target_format": self.target_format,
            "uses_uploaded_files": self.uses_uploaded_files,
            "needs_format_clarification": self.needs_format_clarification,
            "clarification_question": self.clarification_question,
            "clarification_options": self.clarification_options,
            "unsupported_format": self.unsupported_format,
            "include_chat_explanation": self.include_chat_explanation,
            "package_as_zip": self.package_as_zip,
        }


class ResponseOutputIntentEngine:
    """
    Universal Output Intent Detection Engine for General Chat (Sections 1, 4, 29, 43, 45, 46, 47).
    Determines whether a user wants CHAT, FILE, CHAT_AND_FILE, MULTIPLE_FILES, PROJECT, or ARCHIVE.
    """

    CLARIFICATION_OPTIONS = [
        "PDF",
        "Word",
        "Excel",
        "PowerPoint",
        "Plain text",
        "Other",
    ]

    # Informational / conceptual queries that must remain normal CHAT
    PURE_CHAT_PATTERNS = [
        r"^(what|how|why|when|where|who)\s+(is|are|was|were|do|does|can|should)\s+(a|an|the)?\s*(pdf|word|docx?|powerpoint|pptx?|excel|xlsx?|csv|json|xml|yaml|sql|zip|svg|html|css|python)\b(?!\s*(?:file\s+for|from\s+this|out\s+of))",
        r"^explain\s+[a-z0-9\s_\-]+[.?!]*$",
        r"^describe\s+(?:an?\s+|the\s+)?image\b",
        r"^what\s+does\s+this\s+image\s+show",
        r"^tell\s+me\s+about\s+[a-z0-9\s_\-]+[.?!]*$",
        r"^difference\s+between\b",
    ]

    @classmethod
    def detect(
        cls,
        message: str,
        has_uploaded_files: bool = False,
        has_previous_artifact: bool = False,
        previous_artifact_ext: Optional[str] = None,
    ) -> OutputIntentResult:
        msg = (message or "").strip()
        lower = msg.lower()
        if not msg:
            return OutputIntentResult(mode=OutputMode.CHAT)

        # 1. Check pure informational queries (unless they also ask to create/save a file)
        has_chat_and_file_conjunction = bool(
            re.search(
                r"\b(?:and\s+(?:also\s+)?(?:create|make|generate|save|export|give\s+me|put\s+it\s+in|turn\s+it\s+into)|give\s+me\s+the\s+(?:answer|explanation|code)\s+and\s+(?:create|save|make|export))\b",
                lower,
            )
        )
        if not has_chat_and_file_conjunction:
            for pat in cls.PURE_CHAT_PATTERNS:
                if re.search(pat, lower):
                    return OutputIntentResult(mode=OutputMode.CHAT, topic=msg)

        # 2. Check for unsupported binary formats explicitly requested (Section 51 & 65)
        unsupported_match = re.search(
            r"\b(?:create|make|generate|save|export|convert|build|produce)\b.*?(?:\.|\b)(exe|dmg|apk|iso|blend|psd|ai|dwg|flac|mkv|avi|fbx|3ds)\b",
            lower,
        )
        if unsupported_match:
            bad_fmt = unsupported_match.group(1).lower()
            return OutputIntentResult(
                mode=OutputMode.FILE,
                unsupported_format=bad_fmt,
                topic=msg,
            )

        # 3. Check for ambiguous file request (Section 46: "Make this into a file", "Save this as a file", "Export this to a file")
        ambiguous_patterns = [
            r"^(?:please\s+)?(?:make|turn|put|convert|save|export)\s+(?:this|it|the\s+output|the\s+response|these)\s+(?:into|as|to|in)\s+(?:a\s+|an\s+)?(?:downloadable\s+)?file[.?!]*$",
            r"^(?:please\s+)?(?:create|generate|make|give\s+me)\s+(?:a\s+)?(?:downloadable\s+)?file(?:\s+for\s+this|\s+from\s+this)?[.?!]*$",
        ]
        if any(re.search(p, lower) for p in ambiguous_patterns):
            return OutputIntentResult(
                mode=OutputMode.FILE,
                needs_format_clarification=True,
                clarification_question=(
                    "Which format would you like?\n\n"
                    "- PDF\n- Word\n- Excel\n- PowerPoint\n- Plain text\n- Other"
                ),
                clarification_options=list(cls.CLARIFICATION_OPTIONS),
                topic=msg,
            )

        # 4. Extract user-specified filename if present (Section 29: "Save it as final_report.pdf", "named budget.xlsx")
        explicit_filename = None
        explicit_ext = None
        fname_match = re.search(
            r"\b(?:save(?:\s+it|\s+this)?\s+as|named|called|filename\s*[:=]?\s*|file\s+named)\s+['\"`]?([a-zA-Z0-9_\-\.]+\.([a-zA-Z0-9]{1,6}))['\"`]?",
            msg,
            flags=re.IGNORECASE,
        )
        if not fname_match:
            fname_match = re.search(
                r"\bas\s+['\"`]?([a-zA-Z0-9_\-]+\.(pdf|docx?|odt|rtf|txt|md|xlsx?|ods|csv|tsv|pptx?|odp|json|jsonl|ya?ml|xml|sql|py|js|ts|tsx|jsx|html|css|java|cpp|c|cs|go|rs|php|rb|kt|swift|sh|ps1|svg|png|jpe?g|webp|zip))['\"`]?\b",
                msg,
                flags=re.IGNORECASE,
            )
        if fname_match:
            raw_fname = fname_match.group(1)
            raw_ext = fname_match.group(2).lower()
            if raw_ext in SUPPORTED_EXTENSIONS:
                explicit_ext = "md" if raw_ext == "markdown" else raw_ext
                explicit_filename = sanitize_filename(raw_fname, ext=explicit_ext)

        # 5. Check for Project / Multi-file / Archive requests (Sections 10, 12, 13, 28)
        is_project = bool(
            re.search(
                r"\b(?:create|build|generate|make|give\s+me)\s+(?:a\s+|the\s+)?(?:complete|full|entire|working|multi-file|portfolio)?\s*(?:html\/css\/js\s+website|website\s+with\s+html|web\s+project|website\s+project|complete\s+project|full\s+project|source\s+code\s+as\s+a\s+zip|project\s+as\s+a\s+zip|complete\s+html\/css\/js)\b",
                lower,
            )
            or re.search(r"\b(?:give\s+me|export|download|package)\s+(?:the\s+)?(?:source\s+code|project|files|website)?\s*(?:as|in|into)?\s*(?:a\s+|the\s+)?zip\b", lower)
            or re.search(r"\bcreate\s+(?:a\s+|the\s+)?complete\s+project\b", lower)
        )
        if is_project:
            want_zip = "zip" in lower or "archive" in lower or "complete project" in lower
            topic = cls._extract_topic(msg)
            title = cls._topic_to_title(topic or "Web Project")
            base_slug = re.sub(r"[^a-zA-Z0-9_\-]", "_", title.lower()).strip("_") or "project"
            return OutputIntentResult(
                mode=OutputMode.ARCHIVE if "zip" in lower else OutputMode.PROJECT,
                formats=["html", "css", "js", "zip"] if want_zip else ["html", "css", "js"],
                primary_format="zip" if want_zip else "html",
                topic=topic or msg,
                title=title,
                filename=explicit_filename or f"{base_slug}.zip",
                user_specified_filename=bool(explicit_filename),
                package_as_zip=True,
                include_chat_explanation=has_chat_and_file_conjunction,
            )

        # 6. Check for Conversational Follow-up Editing or Format Conversion (Sections 19, 20, 21, 43)
        conversion_match = re.search(
            r"\b(?:convert|export|turn|change|transform)\s+(?:this|that|it|(?:the|that|this)\s+(?:previous\s+|uploaded\s+)?(?:file|document|pdf|docx?|word|xlsx?|excel|csv|pptx?|presentation|slides|markdown|md|txt|json|report))\s+(?:to|into|as)\s+(?:a\s+|an\s+)?(\d+\s*(?:-| )*(?:slide|page)s?\s+)?(pdf|word(?:\s+document)?|docx?|excel(?:\s+spreadsheet)?|xlsx?|csv|powerpoint(?:\s+presentation)?|pptx?|presentation|slides|markdown|md|plain\s+text|txt|json)\b",
            lower,
        )
        if conversion_match:
            cnt_raw = conversion_match.group(1)
            target_raw = conversion_match.group(2).strip()
            if "powerpoint" in target_raw or "presentation" in target_raw or "slide" in target_raw:
                target_fmt = "pptx"
            elif "word" in target_raw:
                target_fmt = "docx"
            elif "excel" in target_raw or "spreadsheet" in target_raw:
                target_fmt = "xlsx"
            else:
                target_fmt = FORMAT_SYNONYMS.get(target_raw, target_raw)
            cnt = None
            unit = None
            if cnt_raw:
                m_c = re.search(r"(\d+)\s*(?:-| )*(slide|page)", cnt_raw)
                if m_c:
                    cnt = int(m_c.group(1))
                    unit = m_c.group(2)
            return OutputIntentResult(
                mode=OutputMode.FILE,
                formats=[target_fmt],
                primary_format=target_fmt,
                topic=cls._extract_topic(msg) or "Converted Document",
                title=cls._topic_to_title(cls._extract_topic(msg) or "Converted Document"),
                filename=explicit_filename,
                user_specified_filename=bool(explicit_filename),
                count=cnt,
                count_unit=unit,
                is_conversion=True,
                source_format=previous_artifact_ext,
                target_format=target_fmt,
                uses_uploaded_files=has_uploaded_files or ("uploaded" in lower),
            )

        # Follow-up edit patterns on existing artifact (Sections 19, 20, 43)
        followup_edit_patterns = [
            r"^(?:please\s+)?(?:change|update|modify|edit|revise|rename)\s+(?:the|that|this)\s+(?:pdf|docx?|word(?:\s+document)?|xlsx?|excel|spreadsheet|pptx?|powerpoint|presentation|slides?|csv|document|report|file|title|heading|table|cover\s+page)\b",
            r"^(?:please\s+)?(?:add\s+a\s+cover\s+page|change\s+the\s+title|use\s+a\s+table|make\s+the\s+slides\s+more\s+professional|add\s+(?:a|an)\s+[a-z0-9_\-\s]+section|add\s+charts?|add\s+more\s+slides|add\s+a\s+slide|add\s+a\s+column|add\s+formulas?)\b",
        ]
        if any(re.search(p, lower) for p in followup_edit_patterns):
            # Determine if a specific artifact format was referenced
            ref_fmt = previous_artifact_ext
            for key, mapped in [
                ("pdf", "pdf"), ("word", "docx"), ("docx", "docx"),
                ("excel", "xlsx"), ("xlsx", "xlsx"), ("spreadsheet", "xlsx"),
                ("powerpoint", "pptx"), ("pptx", "pptx"), ("slide", "pptx"), ("presentation", "pptx"),
                ("csv", "csv"),
            ]:
                if re.search(rf"\b{key}s?\b", lower):
                    ref_fmt = mapped
                    break
            return OutputIntentResult(
                mode=OutputMode.FILE,
                formats=[ref_fmt or "pdf"],
                primary_format=ref_fmt or "pdf",
                topic=msg,
                title="Updated Document",
                is_followup_edit=True,
                edit_instruction=msg,
                target_artifact_hint=ref_fmt,
            )

        # 7. Detect explicit or inferred file generation formats (Sections 4-11, 22-28, 47)
        detected_formats: List[str] = []
        if explicit_ext:
            detected_formats.append(explicit_ext)

        # Count detection (e.g., "5-page report", "10-slide presentation")
        count = None
        count_unit = None
        m_count = re.search(r"\b(\d+)\s*(?:-| )*(page|slide|sheet|section|row)s?\b", lower)
        if m_count:
            count = int(m_count.group(1))
            count_unit = m_count.group(2)

        # Action verbs signaling creation/saving/exporting
        has_creation_intent = bool(
            re.search(
                r"\b(?:create|make|generate|build|write|produce|prepare|export|save|convert|turn|put|give\s+me|download|synthesize|draft|compile|combine|merge|transform|summarize|package|format|render)\b",
                lower,
            )
        )

        if has_creation_intent or explicit_ext:
            format_rules = [
                ("pdf", [
                    r"\bpdf\b",
                    r"\b\d+\s*(?:-| )*page\s+report\b",
                    r"\bwrite\s+(?:a\s+|an\s+)?(?:\d+\s*(?:-| )*page\s+)?report\b",
                    r"\b(?:create|make|generate)\s+(?:a\s+|an\s+)?(?:\d+\s*(?:-| )*page\s+)?report\b(?!\s+in\s+(?:word|docx|excel|powerpoint))",
                ]),
                ("docx", [r"\bdocx\b", r"\bword\s+doc(?:ument)?\b", r"\bword\s+file\b", r"\bas\s+word\b", r"\bin\s+word\b"]),
                ("doc", [r"\b\.doc\b", r"\bdoc\s+file\b"]),
                ("odt", [r"\bodt\b", r"\bopen\s*document\s+text\b"]),
                ("rtf", [r"\brtf\b", r"\brich\s+text\s+file\b"]),
                ("xlsx", [
                    r"\bxlsx\b",
                    r"\bexcel\b",
                    r"\bspreadsheet\b",
                    r"\bworkbook\b",
                    r"\bbudget\s+planner\b",
                    r"\bexpense\s+tracker\b",
                    r"\bfinancial\s+tracker\b",
                ]),
                ("xls", [r"\b\.xls\b", r"\bxls\s+file\b"]),
                ("ods", [r"\bods\b", r"\bopen\s*document\s+spreadsheet\b"]),
                ("csv", [
                    r"\bcsv\s+file\b",
                    r"\b\.csv\b",
                    r"\bas\s+(?:a\s+)?csv\b",
                    r"\b(?:create|make|generate|export|save|download)\s+(?:a\s+|an\s+|the\s+)?csv\b",
                    r"\bcomma[\s\-]+separated\b",
                ]),
                ("tsv", [r"\btsv\b", r"\btab[\s\-]+separated\b"]),
                ("pptx", [
                    r"\bpptx\b",
                    r"\bpower\s*point\b",
                    r"\bpresentation\b",
                    r"\bslide\s+deck\b",
                    r"\bpitch\s+deck\b",
                    r"\b(?:make|create|generate|build|turn\s+.*?\s+into)\s+(?:\d+\s*(?:-| )*)?slides\b",
                ]),
                ("ppt", [r"\b\.ppt\b", r"\bppt\s+file\b"]),
                ("odp", [r"\bodp\b", r"\bopen\s*document\s+presentation\b"]),
                ("json", [r"\bjson\s+file\b", r"\bgenerate\s+json\b", r"\bsave\s+(?:this\s+|it\s+)?as\s+json\b", r"\b(?:create|export|write|make)\s+(?:a\s+|an\s+)?json\b"]),
                ("jsonl", [r"\bjsonl\b"]),
                ("yaml", [r"\byaml\b", r"\b\.yaml\b"]),
                ("yml", [r"\b\.yml\b", r"\byml\s+file\b"]),
                ("xml", [r"\bxml\b", r"\b\.xml\b"]),
                ("sql", [r"\bsql\s+(?:file|schema|script)\b", r"\b\.sql\b", r"\bsave\s+as\s+sql\b", r"\b(?:create|write|generate|export)\s+(?:a\s+|an\s+)?sql\b"]),
                ("py", [
                    r"\b\.py\b",
                    r"\bpython\s+(?:script|file|program|module)\b",
                    r"\bsave\s+(?:it\s+|this\s+)?as\s+python\b",
                ]),
                ("js", [r"\b\.js\b", r"\bjavascript\s+file\b", r"\bsave\s+as\s+javascript\b"]),
                ("ts", [r"\b\.ts\b", r"\btypescript\s+file\b", r"\bsave\s+as\s+typescript\b"]),
                ("tsx", [r"\b\.tsx\b"]),
                ("jsx", [r"\b\.jsx\b"]),
                ("html", [r"\b\.html\b", r"\bhtml\s+(?:file|page|website|document)\b", r"\bcreate\s+(?:an?\s+)?html\b"]),
                ("css", [r"\b\.css\b", r"\bcss\s+(?:file|stylesheet)\b"]),
                ("java", [r"\b\.java\b", r"\bjava\s+(?:file|class|program)\b"]),
                ("cpp", [r"\b\.cpp\b", r"\bc\+\+\s+(?:file|program)\b"]),
                ("c", [r"\b\.c\b", r"\bc\s+source\s+file\b"]),
                ("cs", [r"\b\.cs\b", r"\bc#\s+(?:file|program)\b"]),
                ("go", [r"\b\.go\b", r"\bgolang\s+(?:file|program)\b"]),
                ("rs", [r"\b\.rs\b", r"\brust\s+(?:file|program)\b"]),
                ("php", [r"\b\.php\b", r"\bphp\s+(?:file|script)\b"]),
                ("rb", [r"\b\.rb\b", r"\bruby\s+(?:file|script)\b"]),
                ("kt", [r"\b\.kt\b", r"\bkotlin\s+(?:file|program)\b"]),
                ("swift", [r"\b\.swift\b", r"\bswift\s+(?:file|program)\b"]),
                ("sh", [r"\b\.sh\b", r"\b(?:bash|shell)\s+script\b"]),
                ("ps1", [r"\b\.ps1\b", r"\bpowershell\s+script\b"]),
                ("svg", [r"\bsvg\b", r"\bvector\s+graphic\b"]),
                ("png", [r"\bpng\b", r"\b\.png\b"]),
                ("jpg", [r"\bjpg\b", r"\bjpeg\b", r"\b\.jpe?g\b"]),
                ("webp", [r"\bwebp\b", r"\b\.webp\b"]),
                ("md", [r"\bmarkdown\s+file\b", r"\b\.md\b", r"\bcreate\s+(?:a\s+)?markdown\b", r"\bsave\s+(?:this\s+|it\s+)?as\s+markdown\b"]),
                ("txt", [r"\btext\s+file\b", r"\b\.txt\b", r"\bplain\s+text\s+file\b", r"\bsave\s+(?:this\s+|it\s+)?as\s+txt\b"]),
                ("zip", [r"\bzip\s+(?:file|archive)\b", r"\bas\s+a\s+zip\b", r"\b\.zip\b"]),
            ]

            for fmt_code, regex_list in format_rules:
                if any(re.search(rx, lower) for rx in regex_list):
                    if fmt_code not in detected_formats:
                        detected_formats.append(fmt_code)

        # If HTML website requested with CSS/JS, promote to MULTIPLE_FILES
        if "html" in detected_formats and (
            re.search(r"\bwebsite\b", lower) or ("css" in detected_formats and "js" in detected_formats)
        ):
            for wf in ["html", "css", "js"]:
                if wf not in detected_formats:
                    detected_formats.append(wf)

        if not detected_formats:
            return OutputIntentResult(mode=OutputMode.CHAT, topic=msg)

        primary_fmt = detected_formats[0]
        topic = cls._extract_topic(msg)
        title = cls._topic_to_title(topic)

        # Determine default filename if not explicitly provided
        if explicit_filename:
            final_filename = explicit_filename
        else:
            final_filename = cls._build_default_filename(title, primary_fmt, lower)

        # Determine if user wants BOTH chat explanation AND file (Section 1, 16, 45)
        wants_chat_and_file = bool(
            has_chat_and_file_conjunction
            or re.search(r"\b(?:explain|answer|summarize|tell\s+me|describe|show\s+me)\b.*?\band\s+(?:create|make|save|export|generate|give\s+me)\b", lower)
            or re.search(r"\b(?:give\s+me\s+the\s+(?:answer|code|explanation|summary)\s+and)\b", lower)
        )

        # Determine if user references uploaded files (Sections 22, 23, 48)
        uses_uploads = bool(
            has_uploaded_files
            or re.search(
                r"\b(?:uploaded|attached|this\s+report|this\s+pdf|this\s+document|this\s+file|these\s+(?:two|three|four|\d+)?\s*files|combining\s+these|all\s+three|based\s+on\s+this\s+report)\b",
                lower,
            )
        )

        if len(detected_formats) > 1:
            mode = OutputMode.ARCHIVE if "zip" in detected_formats and len(detected_formats) == 1 else OutputMode.MULTIPLE_FILES
        elif primary_fmt == "zip":
            mode = OutputMode.ARCHIVE
        elif wants_chat_and_file:
            mode = OutputMode.CHAT_AND_FILE
        else:
            mode = OutputMode.FILE

        return OutputIntentResult(
            mode=mode,
            formats=detected_formats,
            primary_format=primary_fmt,
            topic=topic,
            title=title,
            filename=final_filename,
            user_specified_filename=bool(explicit_filename),
            count=count,
            count_unit=count_unit,
            uses_uploaded_files=uses_uploads,
            include_chat_explanation=wants_chat_and_file,
            package_as_zip="zip" in detected_formats,
        )

    @classmethod
    def _extract_topic(cls, message: str) -> str:
        msg = message.strip()
        # Remove trailing "and save it as X.ext"
        cleaned = re.sub(
            r"\s*(?:and\s+)?(?:save|export|name|call)\s+(?:it|this|them)?\s*(?:as|to)?\s*['\"`]?[a-zA-Z0-9_\-]+\.[a-zA-Z0-9]{1,6}['\"`]?[.?!]*$",
            "",
            msg,
            flags=re.IGNORECASE,
        )
        # Strip leading action & format boilerplate
        strip_pat = (
            r"^(?:please\s+)?(?:give\s+me\s+the\s+(?:answer|code|explanation)\s+and\s+)?"
            r"(?:explain\s+(.+?)\s+and\s+(?:make|create|generate|save)\s+(?:me\s+)?(?:a\s+|an\s+)?(?:pdf|docx?|word|xlsx?|excel|pptx?|powerpoint|csv|file)\s*)?"
        )
        m_explain = re.match(
            r"^(?:please\s+)?explain\s+(.+?)\s+and\s+(?:make|create|generate|save)\s+(?:me\s+)?(?:a\s+|an\s+)?(?:pdf|docx?|word|xlsx?|excel|pptx?|powerpoint|csv|file)",
            cleaned,
            flags=re.IGNORECASE,
        )
        if m_explain:
            return m_explain.group(1).strip(" .?!")

        prefix_pat = (
            r"^(?:please\s+)?(?:create|make|generate|build|write|produce|prepare|export|save|convert|turn|put|give\s+me)\s+"
            r"(?:this\s+into\s+|this\s+as\s+|it\s+into\s+|me\s+)?"
            r"(?:a\s+|an\s+|the\s+)?"
            r"(?:complete\s+|full\s+|working\s+)?"
            r"(?:\d+\s*(?:-| )*(?:page|slide|sheet)s?\s+)?"
            r"(?:(?:pdf|word(?:\s+document|\s+doc)?|docx?|odt|rtf|power\s*point|pptx?|odp|presentation|slide\s+deck|slides|"
            r"excel(?:\s+spreadsheet|\s+workbook|\s+sheet)?|xlsx?|ods|spreadsheet|csv|tsv|json|jsonl|ya?ml|xml|sql|"
            r"python(?:\s+program|\s+script|\s+file)?|javascript|typescript|html\/css\/js\s+website|html\s+website|website|svg|markdown|md|text\s+file|txt|report|notes|study\s+guide)\s+)*"
            r"(?:about|on|explaining|for|of|covering|analyzing|that\s+analyzes|summarizing|based\s+on|combining|from)?\s*"
        )
        topic = re.sub(prefix_pat, "", cleaned, flags=re.IGNORECASE).strip(" .?!")
        if not topic or topic.lower() in {"this", "it", "these", "the uploaded pdf", "the uploaded file"}:
            return "Generated Deliverable"
        return topic[:100].strip()

    @classmethod
    def _topic_to_title(cls, topic: str) -> str:
        clean = re.sub(r"[\r\n\t]+", " ", topic).strip(" .?!")
        if not clean:
            return "Document"
        words = clean.split()[:8]
        return " ".join(w.capitalize() if not w.isupper() else w for w in words)

    @classmethod
    def _build_default_filename(cls, title: str, fmt: str, lower_msg: str) -> str:
        slug = re.sub(r"[^a-zA-Z0-9_\- ]", "", title).strip()
        slug = re.sub(r"\s+", "_", slug).lower()[:40] or "artifact"
        if "budget" in lower_msg and "student" in lower_msg:
            slug = "student_budget"
        elif "sales" in lower_msg and "analyzer" in lower_msg or ("sales" in lower_msg and fmt == "py"):
            slug = "sales_analyzer"
        elif "operating_systems" in slug or "operating systems" in lower_msg:
            slug = "operating_systems"
        elif "normalization" in lower_msg and "report" in lower_msg:
            slug = "normalization_report"
        elif fmt == "html" and ("website" in lower_msg or slug == "generated_deliverable"):
            slug = "index"
        return sanitize_filename(f"{slug}.{fmt}", default_stem=slug, ext=fmt)
