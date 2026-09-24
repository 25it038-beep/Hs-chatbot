"""Adaptive Clarification Quiz Generator for HSBot General Chat.
Generates focused, minimal questions and options based on user prompt and detected intent.
"""

import uuid
import re
from typing import Optional, List, Dict
from app.services.intent.models import ClarificationQuiz, IntentCategory


class QuizGenerator:
    """Generates adaptive clarification quizzes when user intent is ambiguous."""

    @staticmethod
    def generate_quiz(
        intent: IntentCategory,
        query: str,
        context_hints: Optional[Dict[str, str]] = None,
    ) -> ClarificationQuiz:
        q_clean = query.strip()
        hints = context_hints or {}
        topic = hints.get("topic") or QuizGenerator._extract_topic(q_clean)

        # 1. Ambiguous public official / leader / entity
        if hints.get("sub_type") == "entity_overview" or (
            re.search(r"\b(tell\s+me\s+about|about|who\s+is|info\s+on)\s+(?:the\s+)?(cm|chief\s+minister|president|prime\s+minister|pm|governor|ceo|leader|minister|modi|stalin|biden|trump)\b", q_clean, re.I)
            and not re.search(r"\b(who\s+is\s+the\s+(?:current\s+|new\s+|present\s+)?(?:cm|chief\s+minister|president|prime\s+minister))\b", q_clean, re.I)
        ):
            target = topic or "this topic"
            return ClarificationQuiz(
                id=str(uuid.uuid4()),
                question=f"What would you like to know about {target}?",
                options=[
                    "Current office holder",
                    "Biography & background",
                    "Current government & administration",
                    "Key policies & decisions",
                    "Political history",
                ],
                quiz_type="scope",
                allow_custom=True,
                intent=intent,
                context=target,
            )

        # 2. Recommendation
        if intent == IntentCategory.RECOMMENDATION or re.search(r"\b(suggest|recommend|which\s+(?:one\s+)?should\s+i\s+buy|best\s+(?:phone|laptop|car|tv|camera))\b", q_clean, re.I):
            target = topic or "your request"
            return ClarificationQuiz(
                id=str(uuid.uuid4()),
                question=f"What matters most for this {target} recommendation?",
                options=[
                    "Top performance & speed",
                    "Camera & display quality",
                    "Battery life & reliability",
                    "Budget-friendly / Best value",
                    "Balanced all-rounder",
                ],
                quiz_type="criteria",
                allow_custom=True,
                intent=intent,
                context=target,
            )

        # 3. Comparison
        if intent == IntentCategory.COMPARISON or re.search(r"\b(compare|versus|vs)\b", q_clean, re.I):
            return ClarificationQuiz(
                id=str(uuid.uuid4()),
                question="What aspects would you like to focus on in the comparison?",
                options=[
                    "Key features & specifications",
                    "Price & value for money",
                    "Performance & benchmarks",
                    "Pros & cons summary",
                    "Final recommendation",
                ],
                quiz_type="criteria",
                allow_custom=True,
                intent=intent,
            )

        # 4. Presentation request
        if intent == IntentCategory.PRESENTATION_REQUEST or re.search(r"\b(presentation|slides|powerpoint|pptx|deck)\b", q_clean, re.I):
            return ClarificationQuiz(
                id=str(uuid.uuid4()),
                question="What size and target audience for the presentation?",
                options=[
                    "5 slides (Executive pitch)",
                    "10 slides (Standard overview)",
                    "15 slides (Comprehensive deep-dive)",
                    "Technical / Academic audience",
                    "Business / Client audience",
                ],
                quiz_type="scope",
                allow_custom=True,
                intent=intent,
            )

        # 5. Document request
        if intent in (IntentCategory.DOCUMENT_REQUEST, IntentCategory.FILE_GENERATION) or re.search(r"\b(document|report|doc|write\s+a\s+report)\b", q_clean, re.I):
            return ClarificationQuiz(
                id=str(uuid.uuid4()),
                question="What format and style would you prefer for the document?",
                options=[
                    "PDF Document (Professional)",
                    "DOCX Word Document",
                    "Both PDF & Word",
                    "Academic / Research style",
                    "Executive Summary",
                ],
                quiz_type="output_format",
                allow_custom=True,
                intent=intent,
            )

        # 6. File conversion
        if intent == IntentCategory.FILE_CONVERSION or re.search(r"\b(convert\s+this|change\s+format)\b", q_clean, re.I):
            return ClarificationQuiz(
                id=str(uuid.uuid4()),
                question="What target format should I convert it to?",
                options=[
                    "PDF Document",
                    "DOCX (Word)",
                    "PPTX (Presentation)",
                    "XLSX (Spreadsheet)",
                    "Markdown / Plain Text",
                ],
                quiz_type="output_format",
                allow_custom=True,
                intent=intent,
            )

        # 7. Game Development request
        if intent == IntentCategory.GAME_DEVELOPMENT or re.search(r"\b(game|play\s+game|make\s+a\s+game|create\s+a\s+game)\b", q_clean, re.I):
            from app.services.game.detector import GameDetector
            from app.services.game.models import GameGenre
            genre = GameDetector.extract_genre(q_clean)
            if genre == GameGenre.FOOTBALL:
                return ClarificationQuiz(
                    id=str(uuid.uuid4()),
                    question="What style of football gameplay would you prefer?",
                    options=[
                        "Top-down 2D match (Single Player vs AI)",
                        "Penalty shootout tournament",
                        "2D side-view arcade match",
                        "Target shooting practice challenge",
                    ],
                    quiz_type="scope",
                    allow_custom=True,
                    intent=intent,
                )
            elif genre == GameGenre.RACING:
                return ClarificationQuiz(
                    id=str(uuid.uuid4()),
                    question="What type of racing experience do you want?",
                    options=[
                        "Top-down circuit race with AI competitors",
                        "Endless highway overtake & drift",
                        "Time-trial lap challenge",
                    ],
                    quiz_type="scope",
                    allow_custom=True,
                    intent=intent,
                )
            else:
                return ClarificationQuiz(
                    id=str(uuid.uuid4()),
                    question="What genre and style of game would you like to build?",
                    options=[
                        "Arcade Football (Player vs AI)",
                        "Top-Down 2D Racing Game",
                        "Platformer Adventure",
                        "Space Arcade Shooter",
                        "Retro Brick Breaker / Snake",
                    ],
                    quiz_type="scope",
                    allow_custom=True,
                    intent=intent,
                )


        # 7. Default generic intent clarification
        return ClarificationQuiz(
            id=str(uuid.uuid4()),
            question="I can help with this. What are you looking for?",
            options=[
                "Get the current factual answer",
                "Detailed explanation",
                "Compare options & alternatives",
                "Conduct deep web research",
                "Generate a document / file",
                "Provide step-by-step guidance",
            ],
            quiz_type="intent",
            allow_custom=True,
            intent=intent,
        )

    @staticmethod
    def _extract_topic(query: str) -> str:
        # Strip common prefix filler
        cleaned = re.sub(
            r"^(?:please\s+|can\s+you\s+|tell\s+me\s+about\s+|info\s+on\s+|about\s+|suggest\s+me\s+a\s+|recommend\s+a\s+|compare\s+)",
            "",
            query,
            flags=re.I,
        ).strip()
        cleaned = re.sub(r"[?!.,]+$", "", cleaned).strip()
        return cleaned[:50] if cleaned else "this topic"
