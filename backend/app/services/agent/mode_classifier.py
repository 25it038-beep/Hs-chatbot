import re
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import List, Optional, Dict, Any

class ChatMode(str, Enum):
    GENERAL_CHAT = "GENERAL_CHAT"
    AGENT = "AGENT"

@dataclass
class ModeClassificationResult:
    mode: ChatMode
    confidence: float
    reason: str
    detected_features: List[str] = field(default_factory=list)
    suggested_action: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "mode": self.mode.value if isinstance(self.mode, Enum) else self.mode,
            "confidence": round(self.confidence, 2),
            "reason": self.reason,
            "detected_features": self.detected_features,
            "suggested_action": self.suggested_action
        }


class AgentModeClassifier:
    """
    Intelligent Intent & Mode Router (§4, §5, §77).
    Determines whether a user request belongs in General Chat (fast informational conversation,
    QA, retrieval, weather, YouTube search) or Agent Mode (autonomous multi-file software engineering,
    app realization, game creation, testing, packaging).
    """

    # Direct agent action triggers
    AGENT_ACTION_VERBS = [
        r"\bbuild\b", r"\bcreate\b", r"\bgenerate\b", r"\bdevelop\b",
        r"\bcode\b", r"\bmake\b", r"\bimplement\b", r"\bscaffold\b",
        r"\bprogram\b", r"\barchitect\b", r"\bdesign and build\b",
        r"\bwrite an? (?:app|application|game|program|website|tool|script|cli)\b",
        r"\bfix\b", r"\bpackage\b", r"\bdeploy\b", r"\bdebug\b",
        r"\brefactor\b", r"\btest\b", r"\bcompile\b"
    ]

    # Application / Product targets
    AGENT_TARGET_NOUNS = [
        r"\bapp\b", r"\bapplication\b", r"\bwebsite\b", r"\bgame\b",
        r"\bweb app\b", r"\bwebapp\b", r"\blanding page\b", r"\bportfolio\b",
        r"\bstore\b", r"\be-?commerce\b", r"\bdashboard\b", r"\bportal\b",
        r"\btool\b", r"\bcli\b", r"\bbackend\b", r"\bfull-?stack\b",
        r"\bmicroservice\b", r"\brepository\b", r"\bcodebase\b",
        r"\bproject\b", r"\bwhiteboard\b", r"\bkanban\b", r"\btracker\b",
        r"\bplatform\b", r"\bsystem\b", r"\binterface\b", r"\bui\b",
        r"\btests?\b", r"\bbugs?\b", r"\bzip (?:file|archive)?\b"
    ]

    # Domain-specific targets that strongly indicate software generation
    AGENT_DOMAINS = [
        r"football (?:game|match|arena|sim)",
        r"soccer (?:game|match|sim)",
        r"(?:arcade|racing|snake|tetris|pong|flappy|platformer|rpg) game",
        r"hospital (?:management|system|portal)",
        r"healthcare (?:platform|app|system)",
        r"food delivery (?:app|platform)",
        r"real estate (?:marketplace|listing|portal)",
        r"recipe (?:studio|planner|app)",
        r"chat (?:app|messenger|workspace)",
        r"audio (?:synth|synthesizer|workstation|studio)",
        r"markdown (?:editor|workspace|notepad)",
        r"expense (?:tracker|manager|finance)",
        r"budget (?:tracker|planner)",
        r"calculator (?:app|tool)"
    ]

    # Conversational / informational indicators (GENERAL_CHAT cues)
    CHAT_INFORMATIONAL_PATTERNS = [
        r"^what (?:is|are|was|were)\b",
        r"^who (?:is|was|are|were)\b",
        r"^when (?:did|was|is|will)\b",
        r"^where (?:is|are|was|were)\b",
        r"^why (?:is|are|does|do|did)\b",
        r"^how (?:does|do|did|can|would|is|are)\b",
        r"^explain\b",
        r"^tell me (?:about|a story|a joke)\b",
        r"^can you explain\b",
        r"^difference between\b",
        r"^what's the (?:weather|time|date|difference|meaning)\b",
        r"^search (?:for|the web|google)\b",
        r"^play (?:.*) on youtube\b",
        r"^summarize (?:this|the following|an article)\b",
        r"^translate (?:this|the following)\b",
        r"^(?:hi|hello|hey|good morning|good evening|good afternoon|howdy)\b"
    ]

    @classmethod
    def classify(cls, prompt: str) -> ModeClassificationResult:
        """
        Classifies a user prompt into GENERAL_CHAT or AGENT mode.
        Returns ModeClassificationResult with mode, confidence, and diagnostic reason.
        """
        if not prompt or not prompt.strip():
            return ModeClassificationResult(
                mode=ChatMode.GENERAL_CHAT,
                confidence=1.0,
                reason="Empty prompt defaults to General Chat.",
                suggested_action=None
            )

        text = prompt.strip().lower()
        detected_features = []

        # 1. Check strong agent domain targets (e.g. "football game", "hospital management")
        has_domain_target = False
        for dom_pat in cls.AGENT_DOMAINS:
            if re.search(dom_pat, text):
                detected_features.append(f"domain_target:{dom_pat}")
                has_domain_target = True

        # 2. Check agent action verbs
        action_count = 0
        for verb_pat in cls.AGENT_ACTION_VERBS:
            if re.search(verb_pat, text):
                detected_features.append(f"action_verb:{verb_pat}")
                action_count += 1

        # 3. Check agent target nouns
        target_count = 0
        for noun_pat in cls.AGENT_TARGET_NOUNS:
            if re.search(noun_pat, text):
                detected_features.append(f"target_noun:{noun_pat}")
                target_count += 1

        # 4. Check explicit engineering flags / deliverables
        has_engineering_deliverable = any(
            re.search(pat, text)
            for pat in [
                r"\bmulti-?file\b", r"\bzip (?:file|archive|download)\b",
                r"\brun tests\b", r"\bunit tests\b", r"\bpackage\.json\b",
                r"\btask graph\b", r"\brepository\b", r"\bfrontend and backend\b",
                r"\bhtml(?:5)?, css(?:3)?, and (?:javascript|js)\b"
            ]
        )
        if has_engineering_deliverable:
            detected_features.append("engineering_deliverable")

        # 5. Check conversational / informational patterns
        is_informational = any(re.search(pat, text) for pat in cls.CHAT_INFORMATIONAL_PATTERNS)
        if is_informational:
            detected_features.append("informational_cue")

        # 6. Evaluation Logic
        # Case A: Strong domain target present (e.g., "football game", "hospital management")
        if has_domain_target:
            confidence = 0.95 if action_count > 0 else 0.85
            return ModeClassificationResult(
                mode=ChatMode.AGENT,
                confidence=confidence,
                reason=f"Detected high-fidelity application domain target: {detected_features[0]}.",
                detected_features=detected_features,
                suggested_action="Launch Universal Agent Realization Pipeline"
            )

        # Case B: Action Verb + Target Noun (e.g. "build a react app", "create an e-commerce website")
        if action_count > 0 and (target_count > 0 or has_engineering_deliverable):
            # Guard against "Explain how to build an app"
            if is_informational and any(text.startswith(prefix) for prefix in ["explain how to build", "how do i build", "what does it take to create"]):
                return ModeClassificationResult(
                    mode=ChatMode.GENERAL_CHAT,
                    confidence=0.88,
                    reason="User is asking for an architectural or educational explanation, not direct code synthesis.",
                    detected_features=detected_features,
                    suggested_action="Answer in General Chat with explanatory guide"
                )

            confidence = 0.95
            return ModeClassificationResult(
                mode=ChatMode.AGENT,
                confidence=confidence,
                reason="User is requesting autonomous software creation with action verb and software target.",
                detected_features=detected_features,
                suggested_action="Activate Agent Mode Orchestrator"
            )

        # Case C: Standalone application noun if explicit (e.g., "portfolio website", "calculator app")
        if target_count >= 2 and not is_informational:
            return ModeClassificationResult(
                mode=ChatMode.AGENT,
                confidence=0.80,
                reason="Detected multiple software product targets without informational questioning.",
                detected_features=detected_features,
                suggested_action="Suggest Agent Mode"
            )

        # Case D: Default to General Chat
        confidence = 0.95 if is_informational else 0.80
        reason = (
            "Classified as conversational or informational query."
            if is_informational else
            "No software creation imperatives detected; routing to fast General Chat."
        )
        return ModeClassificationResult(
            mode=ChatMode.GENERAL_CHAT,
            confidence=confidence,
            reason=reason,
            detected_features=detected_features,
            suggested_action="Handle in General Chat"
        )


# Global singleton classifier
agent_mode_classifier = AgentModeClassifier()
