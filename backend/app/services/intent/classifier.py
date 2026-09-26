"""General Chat Intent Classifier for HSBot.
Classifies user requests across 30+ intent categories, calibrates confidence,
strictly enforces the Minimum-Question Principle, and triggers Adaptive Clarification Quizzes
only when necessary.
"""

import re
from typing import List, Optional, Dict, Any
from app.services.intent.models import (
    IntentCategory,
    IntentConfidence,
    IntentClassificationResult,
    ChatRequirementSnapshot,
)
from app.services.intent.quiz_generator import QuizGenerator


# ── Explicit Clear Entity / Leadership Question Regex ──
_EXPLICIT_OFFICE_HOLDER_Q = re.compile(
    r"^(?:who\s+(?:is|are|was|were)|name\s+(?:the|of))\s+(?:the\s+)?(?:current\s+|new\s+|present\s+)?(?:cm|chief\s+minister|president|prime\s+minister|pm|governor|mayor|ceo|chairman|leader|head)\b|"
    r"\bwho\s+is\s+(?:the\s+)?(?:current\s+|present\s+)?(?:cm|chief\s+minister|president|prime\s+minister|pm|governor|mayor|ceo)\s+(?:of|in)\s+[\w\s]+[?!.]*$",
    re.I,
)

# ── Ambiguous Open-Ended Topic Expressions ──
_AMBIGUOUS_ENTITY_OPENING = re.compile(
    r"^(?:tell\s+me\s+about|about|give\s+(?:me\s+)?info\s+(?:on|about))\s+(?:the\s+)?(?:cm|chief\s+minister|president|prime\s+minister|pm|governor|ceo|minister)\b|"
    r"^(?:tell\s+me\s+about|about|give\s+(?:me\s+)?info\s+(?:on|about))\s+([a-zA-Z\s]{2,25})[?!.]*$",
    re.I,
)

# ── Ambiguous Recommendations ──
_AMBIGUOUS_RECOMMENDATION = re.compile(
    r"^(?:suggest|recommend)\s+(?:me\s+)?(?:a|an|some)\s+(?:phone|laptop|car|tv|camera|headphones|tablet|monitor|watch|bike|course|book|movie|pc|gpu|cpu)[?!.]*$|"
    r"^which\s+(?:phone|laptop|car|tv|camera|headphones|tablet|gpu|cpu)\s+should\s+i\s+buy[?!.]*$",
    re.I,
)

# ── Ambiguous Comparisons ──
_AMBIGUOUS_COMPARISON = re.compile(
    r"^compare\s+these(?:\s+phones|\s+laptops|\s+options|\s+items)?[?!.]*$|"
    r"^compare\s+[a-zA-Z0-9\s]{2,20}\s+(?:and|vs|versus)\s+[a-zA-Z0-9\s]{2,20}[?!.]*$",
    re.I,
)

# ── Ambiguous Document Requests ──
_AMBIGUOUS_DOC_REQUEST = re.compile(
    r"^(?:create|make|write|generate)\s+(?:a\s+|an\s+)?(?:project\s+report|report|document|summary\s+report|business\s+proposal)[?!.]*$",
    re.I,
)

# ── Ambiguous Presentation Requests ──
_AMBIGUOUS_PPTX_REQUEST = re.compile(
    r"^(?:make|create|generate|prepare)\s+(?:a\s+|an\s+)?(?:presentation|slides|powerpoint|slide\s+deck)(?:\s+about\s+[\w\s]+)?[?!.]*$",
    re.I,
)

# ── Ambiguous Conversion Requests ──
_AMBIGUOUS_CONVERT_REQUEST = re.compile(
    r"^(?:convert\s+this|change\s+the\s+format|convert\s+file|convert\s+it)[?!.]*$",
    re.I,
)


class GeneralIntentClassifier:
    """Classifies user messages, derives confidence, and determines if a clarification quiz is needed."""

    @classmethod
    def classify(
        cls,
        message: str,
        context: Optional[List[Dict[str, str]]] = None,
    ) -> IntentClassificationResult:
        query = (message or "").strip()
        lower_q = query.lower()
        context = context or []

        # ── 0. Anti-Quiz-Loop & Follow-Up Check ──
        # If the user is answering a previous quiz or clarifying an earlier turn,
        # never loop back into a quiz.
        is_answering_quiz = cls._check_if_answering_quiz(context)
        is_user_correction = bool(re.match(r"^(?:no[,\s]|actually[,\s]|i\s+meant|not\s+that|instead)\b", lower_q, re.I))

        # ── 1. Clear Direct Intent Detectors (HIGH Confidence, NO Quiz) ──

        # A. YouTube Video Search & Playback
        from app.services.media.youtube import youtube_service
        if youtube_service.detect_video_intent(query):
            return cls._build_result(
                primary=IntentCategory.VIDEO_SEARCH,
                confidence=IntentConfidence.HIGH,
                needs_quiz=False,
                workflow="video_search",
                goal=f"Search and play YouTube videos for '{query}'",
                output_format="answer",
            )

        # B. Explicit leadership / office-holder factual lookup
        if _EXPLICIT_OFFICE_HOLDER_Q.search(query):
            return cls._build_result(
                primary=IntentCategory.CURRENT_FACTUAL,
                confidence=IntentConfidence.HIGH,
                needs_quiz=False,
                requires_web=True,
                requires_current_data=True,
                workflow="web_search",
                goal=f"Determine the current office holder for '{query}'",
                freshness="current",
                output_format="answer",
            )

        # B. Live Tools (Time, Weather, Location)
        if re.search(r"\b(what\s+(?:is\s+the\s+)?time|current\s+time|time\s+in\s+[\w\s]+|what\s+time\s+is\s+it)\b", lower_q):
            return cls._build_result(
                primary=IntentCategory.TIME,
                confidence=IntentConfidence.HIGH,
                needs_quiz=False,
                requires_live_tool="time",
                workflow="live_tool",
                goal="Current time lookup",
                output_format="answer",
            )

        if re.search(r"\b(weather|forecast|temperature\s+(?:in|today|tomorrow))\b", lower_q):
            return cls._build_result(
                primary=IntentCategory.WEATHER,
                confidence=IntentConfidence.HIGH,
                needs_quiz=False,
                requires_live_tool="weather",
                workflow="live_tool",
                goal="Weather information",
                output_format="answer",
            )

        # C. Direct Math / Calculation
        if re.match(r"^(?:calculate|compute|solve|evaluate)\s+[\d\s+\-*/%^().]+$|^\s*[\d\s.+\-*/%^()]{3,}\s*$", query):
            return cls._build_result(
                primary=IntentCategory.CALCULATION,
                confidence=IntentConfidence.HIGH,
                needs_quiz=False,
                workflow="calculation",
                goal="Mathematical calculation",
                output_format="answer",
            )

        # D. Direct Translation
        if re.search(r"\b(?:translate\b.*?\b(?:to|into)\b|translate\s+(?:this|the|sentence|text)?)\b", lower_q):
            return cls._build_result(
                primary=IntentCategory.TRANSLATION,
                confidence=IntentConfidence.HIGH,
                needs_quiz=False,
                workflow="translation",
                goal="Language translation",
                output_format="answer",
            )

        # E. Direct Rewriting / Summarization
        if re.search(r"\b(?:make\s+this\s+(?:email|paragraph|text|sentence)?\s*(?:more\s+)?(?:professional|polite|concise|formal|better)|paraphrase|proofread)\b", lower_q):
            return cls._build_result(
                primary=IntentCategory.REWRITING,
                confidence=IntentConfidence.HIGH,
                needs_quiz=False,
                workflow="rewriting",
                goal="Text transformation / polishing",
                output_format="answer",
            )

        if re.search(r"^(?:summarize|summarise|tl;?dr|give\s+me\s+the\s+summary)\b", lower_q):
            return cls._build_result(
                primary=IntentCategory.SUMMARIZATION,
                confidence=IntentConfidence.HIGH,
                needs_quiz=False,
                workflow="summarization",
                goal="Content summarization",
                output_format="answer",
            )

        # F. Direct Image Generation
        if re.match(r"^/(?:image|img|draw|generate-image)\b", lower_q) or re.search(
            r"\b(?:create|generate|make|draw|render|illustrate|paint)\s+(?:a\s+|an\s+|the\s+|me\s+)?(?:image|picture|photo|illustration|drawing|artwork|poster|wallpaper)\b",
            lower_q,
        ):
            return cls._build_result(
                primary=IntentCategory.IMAGE_REQUEST,
                confidence=IntentConfidence.HIGH,
                needs_quiz=False,
                workflow="image",
                goal="Generate image artifact",
                output_format="image",
            )

        # G. Document & Presentation Requests
        if not is_answering_quiz and not is_user_correction:
            if _AMBIGUOUS_PPTX_REQUEST.search(query):
                quiz = QuizGenerator.generate_quiz(IntentCategory.PRESENTATION_REQUEST, query)
                return cls._build_result(
                    primary=IntentCategory.PRESENTATION_REQUEST,
                    confidence=IntentConfidence.LOW,
                    needs_quiz=True,
                    quiz=quiz,
                    workflow="clarification",
                    goal="Clarify presentation size and audience",
                )
            if _AMBIGUOUS_DOC_REQUEST.search(query):
                quiz = QuizGenerator.generate_quiz(IntentCategory.DOCUMENT_REQUEST, query)
                return cls._build_result(
                    primary=IntentCategory.DOCUMENT_REQUEST,
                    confidence=IntentConfidence.LOW,
                    needs_quiz=True,
                    quiz=quiz,
                    workflow="clarification",
                    goal="Clarify document format and style",
                )

        # Explicit Document Creation with format specified
        pdf_match = re.search(r"\b(?:create|make|generate|build)\s+(?:a\s+|an\s+)?(?:pdf|word|docx|excel|spreadsheet|xlsx|powerpoint|pptx)\b", lower_q)
        if pdf_match:
            fmt = "pdf" if "pdf" in lower_q else "docx" if ("word" in lower_q or "docx" in lower_q) else "pptx" if ("pptx" in lower_q or "powerpoint" in lower_q) else "xlsx"
            return cls._build_result(
                primary=IntentCategory.DOCUMENT_REQUEST,
                confidence=IntentConfidence.HIGH,
                needs_quiz=False,
                workflow="document",
                goal=f"Generate {fmt.upper()} document",
                output_format=fmt,
            )

        # H. Game Development Request
        from app.services.game.detector import GameDetector
        if GameDetector.is_game_request(lower_q):
            needs_q, _ = GameDetector.needs_clarification_quiz(lower_q)
            if needs_q and not is_answering_quiz and not is_user_correction:
                quiz = QuizGenerator.generate_quiz(IntentCategory.GAME_DEVELOPMENT, query)
                return cls._build_result(
                    primary=IntentCategory.GAME_DEVELOPMENT,
                    secondary=[IntentCategory.PROJECT, IntentCategory.CODE],
                    confidence=IntentConfidence.LOW,
                    needs_quiz=True,
                    quiz=quiz,
                    workflow="clarification",
                    goal="Clarify game style and requirements",
                    output_format="project",
                )
            return cls._build_result(
                primary=IntentCategory.GAME_DEVELOPMENT,
                secondary=[IntentCategory.PROJECT, IntentCategory.CODE],
                confidence=IntentConfidence.HIGH,
                needs_quiz=False,
                workflow="game_development",
                goal="Develop complete playable HTML5 game project",
                output_format="project",
            )

        # I. Direct Software / Web Project Creation
        if re.search(r"\b(?:create|build|make|generate|develop|scaffold)\s+(?:a\s+|an\s+)?(?:website|site|landing\s+page|portfolio|web\s+app|dashboard|api|rest\s+api|fullstack|frontend|backend)\b", lower_q):
            return cls._build_result(
                primary=IntentCategory.PROJECT,
                secondary=[IntentCategory.CODE],
                confidence=IntentConfidence.HIGH,
                needs_quiz=False,
                workflow="code",
                goal="Build full software / website project",
                output_format="project",
            )

        # I. Direct Coding / Function / Bug Fix Request
        if re.search(r"\b(?:write\s+(?:a\s+)?(?:python|javascript|typescript|c\+\+|java|rust|go|sql)?\s*(?:function|script|code|method|query)|fix\s+(?:this\s+)?(?:code|bug|error)|debug\s+this)\b", lower_q):
            return cls._build_result(
                primary=IntentCategory.CODE,
                confidence=IntentConfidence.HIGH,
                needs_quiz=False,
                workflow="code",
                goal="Code generation or debugging",
                output_format="code",
            )

        # J. Direct Factual / Concept Explanation ("What is Python?", "How does React work?")
        if re.search(r"^(?:what\s+is|what\s+are|how\s+does|how\s+do|explain\s+how|explain)\s+[\w\s]{2,40}[?!.]*$", query, re.I):
            is_current = bool(re.search(r"\b(?:latest|current|recent|new|2026|today|price|version|status)\b", lower_q))
            return cls._build_result(
                primary=IntentCategory.CURRENT_FACTUAL if is_current else IntentCategory.EXPLANATION,
                confidence=IntentConfidence.HIGH,
                needs_quiz=False,
                requires_web=True,
                requires_current_data=is_current,
                workflow="web_search" if is_current else "explanation",
                goal=f"Explain '{query}' clearly and accurately",
                freshness="current" if is_current else "recent",
                output_format="answer",
            )

        # ── 2. Ambiguity Detectors (LOW Confidence -> Triggers Adaptive Quiz) ──
        # ONLY if user is not already in the middle of answering a quiz

        if not is_answering_quiz and not is_user_correction:
            # A. Ambiguous Public Official / Leader Overview ("Tell me about Tamil Nadu CM")
            if _AMBIGUOUS_ENTITY_OPENING.search(query):
                quiz = QuizGenerator.generate_quiz(IntentCategory.CURRENT_FACTUAL, query, {"sub_type": "entity_overview"})
                return cls._build_result(
                    primary=IntentCategory.RESEARCH,
                    secondary=[IntentCategory.CURRENT_FACTUAL],
                    confidence=IntentConfidence.LOW,
                    needs_quiz=True,
                    quiz=quiz,
                    workflow="clarification",
                    goal=f"Clarify scope for '{query}'",
                )

            # B. Ambiguous Product Recommendation ("Suggest me a phone", "Recommend a laptop")
            if _AMBIGUOUS_RECOMMENDATION.search(query):
                quiz = QuizGenerator.generate_quiz(IntentCategory.RECOMMENDATION, query)
                return cls._build_result(
                    primary=IntentCategory.RECOMMENDATION,
                    confidence=IntentConfidence.LOW,
                    needs_quiz=True,
                    quiz=quiz,
                    workflow="clarification",
                    goal="Clarify criteria for recommendation",
                )

            # C. Ambiguous Comparison ("Compare these phones", "Compare these")
            if _AMBIGUOUS_COMPARISON.search(query):
                quiz = QuizGenerator.generate_quiz(IntentCategory.COMPARISON, query)
                return cls._build_result(
                    primary=IntentCategory.COMPARISON,
                    confidence=IntentConfidence.LOW,
                    needs_quiz=True,
                    quiz=quiz,
                    workflow="clarification",
                    goal="Clarify comparison aspects",
                )

            # D. Ambiguous Document Generation ("Create a project report")
            if _AMBIGUOUS_DOC_REQUEST.search(query):
                quiz = QuizGenerator.generate_quiz(IntentCategory.DOCUMENT_REQUEST, query)
                return cls._build_result(
                    primary=IntentCategory.DOCUMENT_REQUEST,
                    confidence=IntentConfidence.LOW,
                    needs_quiz=True,
                    quiz=quiz,
                    workflow="clarification",
                    goal="Clarify document format and style",
                )

            # E. Ambiguous Presentation Request ("Make a presentation about my project")
            if _AMBIGUOUS_PPTX_REQUEST.search(query):
                quiz = QuizGenerator.generate_quiz(IntentCategory.PRESENTATION_REQUEST, query)
                return cls._build_result(
                    primary=IntentCategory.PRESENTATION_REQUEST,
                    confidence=IntentConfidence.LOW,
                    needs_quiz=True,
                    quiz=quiz,
                    workflow="clarification",
                    goal="Clarify presentation size and audience",
                )

            # F. Ambiguous File Conversion ("Convert this")
            if _AMBIGUOUS_CONVERT_REQUEST.search(query):
                quiz = QuizGenerator.generate_quiz(IntentCategory.FILE_CONVERSION, query)
                return cls._build_result(
                    primary=IntentCategory.FILE_CONVERSION,
                    confidence=IntentConfidence.LOW,
                    needs_quiz=True,
                    quiz=quiz,
                    workflow="clarification",
                    goal="Clarify target conversion format",
                )

        # ── 3. Multi-Intent Detection ──
        # Check for combined goals, e.g. "Who is the CM of Tamil Nadu and make a PDF about their government"
        secondary_intents = []
        has_doc = bool(re.search(r"\b(?:make|create|generate)\s+(?:a\s+|an\s+)?(?:pdf|document|report|presentation|slides)\b", lower_q))
        has_current_info = bool(re.search(r"\b(?:who\s+is|current|latest|news|status)\b", lower_q))
        if has_doc and has_current_info:
            primary = IntentCategory.CURRENT_FACTUAL
            secondary_intents = [IntentCategory.DOCUMENT_REQUEST, IntentCategory.RESEARCH]
            return cls._build_result(
                primary=primary,
                secondary=secondary_intents,
                confidence=IntentConfidence.HIGH,
                needs_quiz=False,
                requires_web=True,
                requires_current_data=True,
                workflow="document",
                goal="Research current factual information and generate requested document",
                freshness="current",
                output_format="pdf" if "pdf" in lower_q else "docx",
            )

        # ── 4. Fallback Default (Standard Chat / Web Research) ──
        # If recency or web cues exist, default to CURRENT_FACTUAL or RESEARCH
        from app.services.retrieval.router import is_non_search_intent
        needs_search = not is_non_search_intent(query)

        return cls._build_result(
            primary=IntentCategory.CURRENT_FACTUAL if needs_search else IntentCategory.FACTUAL,
            confidence=IntentConfidence.HIGH,
            needs_quiz=False,
            requires_web=needs_search,
            requires_current_data=needs_search,
            workflow="web_search" if needs_search else "normal_chat",
            goal=query,
            freshness="current" if needs_search else "none",
            output_format="answer",
        )

    @classmethod
    def _check_if_answering_quiz(cls, context: List[Dict[str, str]]) -> bool:
        """Inspect context to prevent repetitive quizzes (Anti-Quiz-Loop)."""
        if not context:
            return False
        # Look at the last assistant message
        for msg in reversed(context[-4:]):
            role = msg.get("role", "")
            content = msg.get("content", "")
            extra = msg.get("extra_data") or msg.get("metadata") or {}
            if role == "assistant" and (extra.get("quiz") or "What would you like" in content or "What matters most" in content or "What format" in content):
                return True
        return False

    @classmethod
    def _build_result(
        cls,
        primary: IntentCategory,
        confidence: IntentConfidence,
        needs_quiz: bool,
        secondary: Optional[List[IntentCategory]] = None,
        quiz: Optional[Any] = None,
        requires_web: bool = False,
        requires_current_data: bool = False,
        requires_live_tool: Optional[str] = None,
        workflow: str = "normal_chat",
        goal: str = "",
        freshness: str = "none",
        output_format: str = "answer",
    ) -> IntentClassificationResult:
        sec = secondary or []
        snapshot = ChatRequirementSnapshot(
            goal=goal or primary.value,
            intent=primary,
            secondary_intents=sec,
            confidence=confidence,
            freshness=freshness,
            output_format=output_format,
            source_requirements=["authoritative", "government", "primary"] if requires_current_data else ["web"],
            verification_requirements=["fact_check", "citations"] if requires_web else ["completeness"],
        )
        return IntentClassificationResult(
            primary_intent=primary,
            secondary_intents=sec,
            confidence=confidence,
            needs_quiz=needs_quiz,
            quiz=quiz,
            requires_web=requires_web,
            requires_current_data=requires_current_data,
            requires_live_tool=requires_live_tool,
            target_workflow=workflow,
            snapshot=snapshot,
        )
