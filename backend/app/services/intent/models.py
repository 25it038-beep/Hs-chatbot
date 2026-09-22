"""Data models and schemas for General Chat Intent Classification, Adaptive Clarification Quiz,
Requirement Verification, and User Satisfaction Loop.
"""

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class IntentCategory(str, Enum):
    FACTUAL = "factual"
    CURRENT_FACTUAL = "current_factual"
    NEWS = "news"
    RESEARCH = "research"
    EXPLANATION = "explanation"
    TUTORIAL = "tutorial"
    COMPARISON = "comparison"
    RECOMMENDATION = "recommendation"
    CALCULATION = "calculation"
    TROUBLESHOOTING = "troubleshooting"
    CODE = "code"
    PROJECT = "project"
    FILE_GENERATION = "file_generation"
    FILE_EDITING = "file_editing"
    FILE_CONVERSION = "file_conversion"
    IMAGE_REQUEST = "image_request"
    DOCUMENT_REQUEST = "document_request"
    PRESENTATION_REQUEST = "presentation_request"
    SPREADSHEET_REQUEST = "spreadsheet_request"
    SUMMARIZATION = "summarization"
    TRANSLATION = "translation"
    REWRITING = "rewriting"
    PLANNING = "planning"
    BRAINSTORMING = "brainstorming"
    WEATHER = "weather"
    TIME = "time"
    LOCATION = "location"
    FOLLOW_UP = "follow_up"
    ACTION_REQUEST = "action_request"
    OTHER = "other"


class IntentConfidence(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ClarificationQuiz(BaseModel):
    id: str
    question: str
    options: List[str] = Field(default_factory=list)
    quiz_type: str = "intent"  # "intent", "criteria", "output_format", "scope", "audience"
    allow_custom: bool = True
    intent: Optional[IntentCategory] = None
    context: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()


class ChatRequirementSnapshot(BaseModel):
    goal: str
    intent: IntentCategory
    secondary_intents: List[IntentCategory] = Field(default_factory=list)
    confidence: IntentConfidence = IntentConfidence.HIGH
    freshness: str = "none"  # "current", "recent", "all", "none"
    output_format: str = "answer"  # "answer", "report", "pdf", "docx", "pptx", "xlsx", "code", "project"
    criteria: List[str] = Field(default_factory=list)
    constraints: Dict[str, Any] = Field(default_factory=dict)
    source_requirements: List[str] = Field(default_factory=list)
    verification_requirements: List[str] = Field(default_factory=list)
    answered_questions: List[Dict[str, str]] = Field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()


class VerificationResult(BaseModel):
    request_understood: bool = True
    intent: str = "factual"
    requirements_complete: bool = True
    tool_execution_complete: bool = True
    answer_verified: bool = True
    sources_verified: bool = True
    citation_verified: bool = True
    satisfaction_check: bool = False
    verification_notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()


class IntentClassificationResult(BaseModel):
    primary_intent: IntentCategory
    secondary_intents: List[IntentCategory] = Field(default_factory=list)
    confidence: IntentConfidence
    needs_quiz: bool = False
    quiz: Optional[ClarificationQuiz] = None
    requires_web: bool = False
    requires_current_data: bool = False
    requires_live_tool: Optional[str] = None  # "time", "weather", "location"
    target_workflow: str = "normal_chat"  # "web_search", "deep_research", "live_tool", "document", "code", "explanation", "image"
    snapshot: Optional[ChatRequirementSnapshot] = None
