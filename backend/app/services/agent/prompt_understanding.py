import re
import time
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field, asdict

# Message types from Section 3
MESSAGE_TYPES = [
    "QUESTION", "INFORMATION_REQUEST", "CODE_REQUEST", "DEBUG_REQUEST",
    "FEATURE_REQUEST", "PROJECT_REQUEST", "MODIFICATION_REQUEST", "REFACTOR_REQUEST",
    "FILE_REQUEST", "DOCUMENT_REQUEST", "PRESENTATION_REQUEST", "SPREADSHEET_REQUEST",
    "RESEARCH_REQUEST", "AUTOMATION_REQUEST", "AGENT_TASK", "VOICE_COMMAND",
    "FOLLOW_UP", "CORRECTION", "APPROVAL", "REJECTION", "CANCELLATION",
    "CONTINUATION", "EXPORT_REQUEST", "CONVERSION_REQUEST", "REVIEW_REQUEST"
]

@dataclass
class RequirementItem:
    id: str
    text: str
    category: str # "feature" | "auth" | "design" | "db" | "performance" | "testing" | "delivery" | "other"
    importance: str # "MANDATORY" | "IMPORTANT" | "OPTIONAL" | "PREFERENCE" | "CONSTRAINT" | "EXCLUSION"
    source: str # "EXPLICIT" | "INFERRED" | "DISCOVERED" | "DEFAULT"
    verified: bool = False
    evidence: Optional[str] = None

@dataclass
class NegativeRequirement:
    action: str
    scope: str
    reason: str
    strictly_forbidden: bool = True

@dataclass
class AmbiguityItem:
    phrase: str
    category: str
    impact: str # "LOW" | "MEDIUM" | "HIGH"
    can_infer: bool
    safe_default: str
    requires_question: bool
    targeted_question: Optional[str] = None
    options: List[str] = field(default_factory=list)

@dataclass
class ConflictItem:
    conflict_type: str # "DIRECT" | "TECHNICAL" | "ARCHITECTURAL" | "SCOPE" | "FILE" | "VERSION"
    prior_instruction: str
    current_instruction: str
    recommended_resolution: str
    resolution_options: List[str] = field(default_factory=list)

@dataclass
class AcceptanceCriteriaItem:
    id: str
    description: str
    target_verification: str

@dataclass
class AdaptiveQuestion:
    id: str
    question: str
    context_reason: str
    options: List[str]
    allow_custom: bool = True
    selected_option: Optional[str] = None
    answered: bool = False

@dataclass
class UnderstandingModel:
    raw_prompt: str
    normalized_prompt: str
    message_types: List[str]
    primary_goal: str
    desired_outcome: str
    action_type: str
    target_scope: str # "file" | "project" | "workspace"
    target_file: Optional[str] = None
    quality_intent: List[str] = field(default_factory=list)
    user_knowledge_level: str = "GENERAL"
    
    explicit_requirements: List[RequirementItem] = field(default_factory=list)
    implicit_requirements: List[RequirementItem] = field(default_factory=list)
    negative_requirements: List[NegativeRequirement] = field(default_factory=list) # FORBIDDEN_ACTIONS
    
    constraints: Dict[str, Any] = field(default_factory=dict)
    preferences: List[str] = field(default_factory=list)
    
    references_resolved: Dict[str, str] = field(default_factory=dict)
    reference_confidence: str = "HIGH" # "HIGH" | "MEDIUM" | "LOW"
    
    ambiguities: List[AmbiguityItem] = field(default_factory=list)
    conflicts: List[ConflictItem] = field(default_factory=list)
    missing_info: List[str] = field(default_factory=list)
    
    adaptive_quiz: List[AdaptiveQuestion] = field(default_factory=list)
    acceptance_criteria: List[AcceptanceCriteriaItem] = field(default_factory=list)
    
    summary_text: str = ""
    decision: str = "PLAN" # "ANSWER" | "ASK" | "PLAN" | "EXECUTE"
    confidence_score: float = 0.95 # 0.0 - 1.0
    quality_gate_passed: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

class PromptUnderstandingEngine:
    """
    Advanced User Prompt Understanding Engine implementing the 48-section
    HSBot Prompt Understanding Pipeline.
    Runs BEFORE requirement discovery, planning, tool calling, or execution.
    """

    def __init__(self, workspace_context: Optional[Dict[str, Any]] = None):
        self.workspace_context = workspace_context or {}

    def normalize_prompt(self, prompt: str) -> str:
        """Section 27 & 28: Cleans up ASR/voice/speech errors and normalizes syntax while preserving semantics."""
        cleaned = prompt.strip()
        # Voice transcript normalization
        cleaned = re.sub(r'\bp\s*d\s*f\b', 'PDF', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'\bd\s*o\s*c\s*x?\b', 'DOCX', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'\bp\s*p\s*t\s*x?\b', 'PPTX', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'\bx\s*l\s*s\s*x?\b', 'XLSX', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'\bgenrate\b', 'generate', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'\bcreae\b', 'create', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'\bappliaction\b', 'application', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'\bapplicaton\b', 'application', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'\bwebiste\b', 'website', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'\bcalcultor\b', 'calculator', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'\bdasboard\b', 'dashboard', cleaned, flags=re.IGNORECASE)
        return cleaned

    def classify_message_types(self, text: str) -> List[str]:
        """Section 3: Classifies message into one or more categories."""
        lower = text.lower()
        types: List[str] = []

        # Questions
        if any(lower.startswith(w) for w in ["what", "how", "why", "when", "where", "who", "which", "can you explain", "explain", "is it"]):
            types.append("QUESTION")
            types.append("INFORMATION_REQUEST")

        # Code / Debug / Feature / Project
        if any(w in lower for w in ["error", "bug", "broken", "fix", "fail", "traceback", "exception", "crash"]):
            types.append("DEBUG_REQUEST")
        if any(w in lower for w in ["refactor", "clean up", "restructure", "organize code"]):
            types.append("REFACTOR_REQUEST")
        if any(w in lower for w in ["add", "implement", "support", "feature", "integrate", "extend"]):
            types.append("FEATURE_REQUEST")
        if any(w in lower for w in [
            "build an app", "create an app", "new project", "make an app", "full stack",
            "college management", "system", "create a game", "build a game", "create application",
            "make application", "build application", "web application", "create a dashboard",
            "build a store", "create a tool", "create a site", "build a site", "make a site",
            "create a calculator", "build a calculator", "create a canvas", "draw app"
        ]) or (
            any(v in lower for v in ["create", "build", "make", "generate", "develop"]) and
            any(n in lower for n in ["app", "application", "game", "dashboard", "store", "website", "project", "kanban", "calculator", "tool", "workspace"])
        ):
            types.append("PROJECT_REQUEST")
        elif any(w in lower for w in ["change", "update", "modify", "tweak", "adjust", "edit"]):
            types.append("MODIFICATION_REQUEST")
        else:
            types.append("CODE_REQUEST")

        # Document / Presentation / Spreadsheet / File
        if "pdf" in lower:
            types.append("DOCUMENT_REQUEST")
        if any(w in lower for w in ["pptx", "presentation", "slide", "slides"]):
            types.append("PRESENTATION_REQUEST")
        if any(w in lower for w in ["xlsx", "spreadsheet", "excel", "sheet"]):
            types.append("SPREADSHEET_REQUEST")
        if any(w in lower for w in ["zip", "package", "export", "download"]):
            types.append("EXPORT_REQUEST")

        # Automation
        if any(w in lower for w in ["automate", "cron", "schedule", "bot", "crawl", "scrape"]):
            types.append("AUTOMATION_REQUEST")

        # Conversational control
        if any(w in lower for w in ["actually", "i meant", "correction", "scratch that"]):
            types.append("CORRECTION")
        if lower in ["yes", "proceed", "that's correct", "looks good", "ok", "sure", "approve"]:
            types.append("APPROVAL")
        if lower in ["no", "cancel", "stop", "abort", "reject"]:
            types.append("REJECTION")

        return types if types else ["AGENT_TASK"]

    def extract_goal_and_outcome(self, text: str, message_types: List[str]) -> Tuple[str, str, str]:
        """Sections 4 & 5: Distinguishes ACTION from GOAL and defines the DESIRED OUTCOME."""
        lower = text.lower()
        
        # Determine action
        if "DEBUG_REQUEST" in message_types:
            action = "debug_and_repair"
        elif "MODIFICATION_REQUEST" in message_types:
            action = "modify_existing"
        elif "PROJECT_REQUEST" in message_types:
            action = "synthesize_project"
        elif "DOCUMENT_REQUEST" in message_types or "PRESENTATION_REQUEST" in message_types:
            action = "generate_document"
        elif "QUESTION" in message_types:
            action = "explain_and_answer"
        else:
            action = "engineer_solution"

        # Extract Goal (What should be functional or achieved)
        if "college" in lower and "event" in lower:
            primary_goal = "College Event Management Application with registration, user authentication, and interactive schedules"
        elif "dashboard" in lower:
            primary_goal = "Interactive Data Dashboard with filtering, navigation, and metrics"
        elif "login" in lower or "auth" in lower:
            primary_goal = "Secure Authentication and Session Access Flow"
        elif "pdf" in lower:
            primary_goal = "Formal Structured PDF Document Artifact"
        elif "presentation" in lower or "slide" in lower:
            primary_goal = "High-Quality Presentation Deck with structured slides and visual layout"
        elif "DEBUG_REQUEST" in message_types:
            primary_goal = f"Diagnose and resolve code defects in {text[:40]}"
        else:
            primary_goal = f"Deliver verified solution for: {text[:60]}"

        # Extract Desired Outcome
        if "DOCUMENT_REQUEST" in message_types:
            desired_outcome = "PDF"
        elif "PRESENTATION_REQUEST" in message_types:
            desired_outcome = "PPTX"
        elif "SPREADSHEET_REQUEST" in message_types:
            desired_outcome = "XLSX"
        elif "EXPORT_REQUEST" in message_types or "zip" in lower:
            desired_outcome = "ZIP"
        elif "QUESTION" in message_types:
            desired_outcome = "explanation"
        elif "PROJECT_REQUEST" in message_types:
            desired_outcome = "complete application"
        else:
            desired_outcome = "working code"

        return action, primary_goal, desired_outcome

    def extract_negative_requirements(self, text: str) -> List[NegativeRequirement]:
        """Section 11: Detects explicit 'DO NOT' / 'NEVER' / 'DONT' rules and maps to FORBIDDEN_ACTIONS."""
        forbidden: List[NegativeRequirement] = []
        lower = text.lower()

        # Backend protection
        if re.search(r'\b(don\'t|dont|do not|never|without)\s+(modify|touch|change|alter|break|rewrite)\s+(the\s+)?backend\b', lower):
            forbidden.append(NegativeRequirement(
                action="MODIFY_BACKEND",
                scope="backend/",
                reason="Explicit user constraint: do not modify existing backend code or endpoints."
            ))

        # Firebase protection
        if re.search(r'\b(don\'t|dont|do not|never|no)\s+(use|add|include)?\s*firebase\b', lower):
            forbidden.append(NegativeRequirement(
                action="USE_FIREBASE",
                scope="all",
                reason="Explicit user constraint: do not introduce Firebase SDK or dependencies."
            ))

        # UI/Design preservation
        if re.search(r'\b(don\'t|dont|do not|preserve|keep)\s+(redesign|change|alter)\s+(the\s+)?(current\s+)?ui\b', lower) or "preserve design" in lower or "same design" in lower:
            forbidden.append(NegativeRequirement(
                action="OVERRIDE_CURRENT_DESIGN",
                scope="design_system",
                reason="Explicit user constraint: keep current design language intact."
            ))

        # File deletion protection
        if re.search(r'\b(don\'t|dont|do not|never)\s+(delete|remove|erase)\s+(any|existing)?\s*files\b', lower):
            forbidden.append(NegativeRequirement(
                action="DELETE_FILES",
                scope="workspace",
                reason="Explicit user constraint: preserve existing workspace files without deletion."
            ))

        # General "don't break anything"
        if re.search(r'\b(don\'t|dont|do not)\s+break\s+(anything|existing)\b', lower):
            forbidden.append(NegativeRequirement(
                action="BREAK_EXISTING_FEATURES",
                scope="all",
                reason="Explicit user instruction: ensure backwards compatibility and passing invariants."
            ))

        return forbidden

    def extract_explicit_and_implicit_requirements(self, text: str) -> Tuple[List[RequirementItem], List[RequirementItem]]:
        """Sections 6 & 7: Extracts explicit requirements and infers implicit prerequisites."""
        lower = text.lower()
        explicit: List[RequirementItem] = []
        implicit: List[RequirementItem] = []
        req_counter = 1

        # 1. Authentication
        if any(w in lower for w in ["login", "signin", "sign in", "auth", "authentication"]):
            explicit.append(RequirementItem(
                id=f"REQ-{req_counter:03d}",
                text="User Authentication (login / session management)",
                category="auth",
                importance="MANDATORY",
                source="EXPLICIT"
            ))
            req_counter += 1
            # Implicit prerequisites
            implicit.append(RequirementItem(
                id=f"REQ-{req_counter:03d}",
                text="Credential validation, form validation, and session persistence",
                category="auth",
                importance="IMPORTANT",
                source="INFERRED"
            ))
            req_counter += 1
            implicit.append(RequirementItem(
                id=f"REQ-{req_counter:03d}",
                text="Sign out / logout capability and protected route handling",
                category="auth",
                importance="IMPORTANT",
                source="INFERRED"
            ))
            req_counter += 1

        # 2. Registration / Sign up
        if any(w in lower for w in ["registration", "register", "signup", "sign up"]):
            explicit.append(RequirementItem(
                id=f"REQ-{req_counter:03d}",
                text="User Registration flow with field validation",
                category="auth",
                importance="MANDATORY",
                source="EXPLICIT"
            ))
            req_counter += 1

        # 3. College / Event Management
        if "college" in lower or "event" in lower:
            explicit.append(RequirementItem(
                id=f"REQ-{req_counter:03d}",
                text="Event Management Catalog (creation, browsing, and details)",
                category="feature",
                importance="MANDATORY",
                source="EXPLICIT"
            ))
            req_counter += 1
            implicit.append(RequirementItem(
                id=f"REQ-{req_counter:03d}",
                text="Event status tracking (upcoming, ongoing, completed)",
                category="feature",
                importance="IMPORTANT",
                source="INFERRED"
            ))
            req_counter += 1

        # 4. Search / Filtering
        if any(w in lower for w in ["search", "filter", "find"]):
            explicit.append(RequirementItem(
                id=f"REQ-{req_counter:03d}",
                text="Search and multi-criteria filtering capability",
                category="feature",
                importance="IMPORTANT",
                source="EXPLICIT"
            ))
            req_counter += 1

        # 5. UI Quality / Design
        if any(w in lower for w in ["premium ui", "clean ui", "best ui", "modern", "dark mode", "responsive"]):
            desc = "Premium responsive UI with coherent typography and styling"
            if "dark" in lower:
                desc += " with Dark Mode support"
            explicit.append(RequirementItem(
                id=f"REQ-{req_counter:03d}",
                text=desc,
                category="design",
                importance="IMPORTANT",
                source="EXPLICIT"
            ))
            req_counter += 1

        # 6. Database / Persistence
        if any(w in lower for w in ["postgres", "postgresql", "sql", "sqlite", "database", "db"]):
            db_name = "PostgreSQL" if "postgres" in lower else "Database"
            explicit.append(RequirementItem(
                id=f"REQ-{req_counter:03d}",
                text=f"{db_name} persistence and schema models",
                category="db",
                importance="MANDATORY",
                source="EXPLICIT"
            ))
            req_counter += 1

        # 7. Testing & Verification
        explicit.append(RequirementItem(
            id=f"REQ-{req_counter:03d}",
            text="Automated unit / integration tests and syntax validation",
            category="testing",
            importance="IMPORTANT",
            source="INFERRED"
        ))
        req_counter += 1

        # Fallback if no specific feature matched
        if len(explicit) == 0:
            explicit.append(RequirementItem(
                id=f"REQ-{req_counter:03d}",
                text=f"Implement requested capability: {text[:60]}",
                category="feature",
                importance="MANDATORY",
                source="EXPLICIT"
            ))

        return explicit, implicit

    def extract_constraints_and_preferences(self, text: str) -> Tuple[Dict[str, Any], List[str]]:
        """Sections 8, 10 & 12: Extracts constraints and user preferences."""
        lower = text.lower()
        constraints: Dict[str, Any] = {}
        preferences: List[str] = []

        # Backend constraint
        if "don't change the backend" in lower or "don't modify the backend" in lower or "use my existing project" in lower:
            constraints["backend"] = "PRESERVE_EXISTING"
        
        # UI preference
        if "premium" in lower:
            preferences.append("Aesthetic: Premium, refined high-contrast visual finish")
        if "clean" in lower:
            preferences.append("Layout: Clean, uncluttered typography and spacious margins")
        if "dark" in lower:
            preferences.append("Theme: Dark mode color system")
        if "responsive" in lower or "mobile" in lower:
            constraints["responsive"] = "MOBILE_AND_DESKTOP"

        # AI provider
        if "nvidia only" in lower:
            constraints["ai_provider"] = "NVIDIA_ONLY"

        return constraints, preferences

    def detect_ambiguities_and_conflicts(
        self,
        text: str,
        explicit_reqs: List[RequirementItem],
        negative_reqs: List[NegativeRequirement]
    ) -> Tuple[List[AmbiguityItem], List[ConflictItem]]:
        """Sections 16, 17 & 18: Identifies ambiguities and potential conflicts."""
        lower = text.lower()
        ambiguities: List[AmbiguityItem] = []
        conflicts: List[ConflictItem] = []

        # Target audience ambiguity for management systems
        if "college" in lower and ("event" in lower or "management" in lower):
            if not any(w in lower for w in ["student", "faculty", "admin", "teacher"]):
                ambiguities.append(AmbiguityItem(
                    phrase="college events management",
                    category="target_audience",
                    impact="MEDIUM",
                    can_infer=False,
                    safe_default="Both Students & Faculty",
                    requires_question=True,
                    targeted_question="Who are the primary users of the events system?",
                    options=["Students", "Faculty", "Both Students & Faculty"]
                ))

        # "Make it better" or "best"
        if "make it better" in lower or "make it fast" in lower:
            ambiguities.append(AmbiguityItem(
                phrase="make it better",
                category="quality_metric",
                impact="LOW",
                can_infer=True,
                safe_default="Improve page performance and interaction responsiveness",
                requires_question=False,
                targeted_question="What should be prioritized for improvement?",
                options=["Load Time", "Visual Design", "Code Architecture"]
            ))

        # Conflict detection: e.g. "don't modify backend" but also asking "add new database tables in postgres"
        has_no_backend = any(nr.action == "MODIFY_BACKEND" for nr in negative_reqs)
        has_new_backend_req = "backend" in lower and ("add" in lower or "create" in lower or "new api" in lower)
        if has_no_backend and has_new_backend_req:
            conflicts.append(ConflictItem(
                conflict_type="DIRECT",
                prior_instruction="Constraint: Do not modify backend",
                current_instruction="Request: Add backend API / tables",
                recommended_resolution="Preserve backend and provide mock/client-side storage, or confirm permission to add new API route",
                resolution_options=["Keep backend untouched (use client mock state)", "Permit extending backend with new endpoint"]
            ))

        return ambiguities, conflicts

    def generate_adaptive_quiz(
        self,
        ambiguities: List[AmbiguityItem],
        primary_goal: str,
        desired_outcome: str
    ) -> List[AdaptiveQuestion]:
        """Sections 35 & 36: Generates targeted questions ONLY for material unknowns, offering crisp chip options."""
        quiz: List[AdaptiveQuestion] = []
        q_count = 1

        for amb in ambiguities:
            if amb.requires_question and amb.targeted_question:
                quiz.append(AdaptiveQuestion(
                    id=f"QUIZ-Q{q_count}",
                    question=amb.targeted_question,
                    context_reason=f"Clarifying {amb.category} to configure authorization roles properly.",
                    options=amb.options,
                    allow_custom=True
                ))
                q_count += 1

        return quiz

    def build_acceptance_criteria(
        self,
        explicit_reqs: List[RequirementItem],
        negative_reqs: List[NegativeRequirement]
    ) -> List[AcceptanceCriteriaItem]:
        """Section 33: Builds concrete, verifiable acceptance criteria."""
        criteria: List[AcceptanceCriteriaItem] = []
        c_count = 1

        for req in explicit_reqs:
            criteria.append(AcceptanceCriteriaItem(
                id=f"AC-{c_count:02d}",
                description=f"Verify that {req.text} functions without errors",
                target_verification=f"Automated test or invariant inspection for {req.category}"
            ))
            c_count += 1

        for neg in negative_reqs:
            criteria.append(AcceptanceCriteriaItem(
                id=f"AC-{c_count:02d}",
                description=f"Ensure invariant respected: {neg.reason}",
                target_verification=f"Workspace diff verifies {neg.scope} is intact"
            ))
            c_count += 1

        return criteria

    def synthesize_summary_text(
        self,
        primary_goal: str,
        desired_outcome: str,
        explicit_reqs: List[RequirementItem],
        negative_reqs: List[NegativeRequirement],
        constraints: Dict[str, Any]
    ) -> str:
        """Section 38: Concise user-facing understanding check before execution."""
        parts = [f"I understand that you want to **{primary_goal}**."]
        
        req_bullets = [f"• {r.text}" for r in explicit_reqs[:4]]
        if req_bullets:
            parts.append("Key objectives:\n" + "\n".join(req_bullets))

        if negative_reqs:
            neg_bullets = [f"• Preserve: {n.reason}" for n in negative_reqs]
            parts.append("Invariants & Exclusions:\n" + "\n".join(neg_bullets))

        parts.append(f"Deliverable format: **{desired_outcome}**")
        return "\n\n".join(parts)

    def analyze(
        self,
        prompt: str,
        target_file: Optional[str] = None,
        scope: str = "workspace"
    ) -> UnderstandingModel:
        """
        Executes the full Section 1 Understanding Pipeline on the user prompt.
        """
        norm_prompt = self.normalize_prompt(prompt)
        msg_types = self.classify_message_types(norm_prompt)
        action_type, primary_goal, desired_outcome = self.extract_goal_and_outcome(norm_prompt, msg_types)
        
        negative_reqs = self.extract_negative_requirements(norm_prompt)
        explicit_reqs, implicit_reqs = self.extract_explicit_and_implicit_requirements(norm_prompt)
        constraints, preferences = self.extract_constraints_and_preferences(norm_prompt)
        
        ambiguities, conflicts = self.detect_ambiguities_and_conflicts(norm_prompt, explicit_reqs, negative_reqs)
        adaptive_quiz = self.generate_adaptive_quiz(ambiguities, primary_goal, desired_outcome)
        acceptance_criteria = self.build_acceptance_criteria(explicit_reqs, negative_reqs)
        
        summary = self.synthesize_summary_text(primary_goal, desired_outcome, explicit_reqs, negative_reqs, constraints)
        
        # Decide: ANSWER | ASK | PLAN | EXECUTE
        decision = "PLAN"
        if "QUESTION" in msg_types and len(explicit_reqs) <= 1 and not any(w in norm_prompt.lower() for w in ["build", "create", "make", "fix"]):
            decision = "ANSWER"
        elif len(adaptive_quiz) > 0 and not any(nr.action == "QUICK_START" for nr in negative_reqs):
            decision = "ASK" # Trigger Adaptive Quiz
        else:
            decision = "PLAN"

        # Check quality gate (Section 41)
        quality_gate = True
        if len(conflicts) > 0:
            quality_gate = False

        return UnderstandingModel(
            raw_prompt=prompt,
            normalized_prompt=norm_prompt,
            message_types=msg_types,
            primary_goal=primary_goal,
            desired_outcome=desired_outcome,
            action_type=action_type,
            target_scope=scope,
            target_file=target_file,
            explicit_requirements=explicit_reqs,
            implicit_requirements=implicit_reqs,
            negative_requirements=negative_reqs,
            constraints=constraints,
            preferences=preferences,
            ambiguities=ambiguities,
            conflicts=conflicts,
            adaptive_quiz=adaptive_quiz,
            acceptance_criteria=acceptance_criteria,
            summary_text=summary,
            decision=decision,
            confidence_score=0.96 if len(conflicts) == 0 else 0.70,
            quality_gate_passed=quality_gate
        )
