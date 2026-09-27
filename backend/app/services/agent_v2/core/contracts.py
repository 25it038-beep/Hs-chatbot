import time
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Dict, List, Optional, Any, Union

class AgentRole(str, Enum):
    # 1. EXECUTIVE LAYER
    PRODUCT_DIRECTOR = "PRODUCT_DIRECTOR"
    CEO_PRODUCT_DIRECTOR = "CEO_PRODUCT_DIRECTOR"  # Alias
    PRODUCT_STRATEGIST = "PRODUCT_STRATEGIST"
    REQUIREMENTS_DIRECTOR = "REQUIREMENTS_DIRECTOR"

    # 2. DISCOVERY LAYER
    PRODUCT_ANALYST = "PRODUCT_ANALYST"
    REQUIREMENTS_ANALYST = "REQUIREMENTS_ANALYST"  # Alias
    RESEARCH_AGENT = "RESEARCH_AGENT"
    RESEARCH_TECHNICAL_ANALYST = "RESEARCH_TECHNICAL_ANALYST"  # Alias
    DOMAIN_ANALYST = "DOMAIN_ANALYST"
    REQUIREMENT_VALIDATOR = "REQUIREMENT_VALIDATOR"

    # 3. PLANNING LAYER
    MASTER_PLANNER = "MASTER_PLANNER"
    SOLUTION_ARCHITECT = "SOLUTION_ARCHITECT"
    TECHNICAL_ARCHITECT = "TECHNICAL_ARCHITECT"
    DATA_ARCHITECT = "DATA_ARCHITECT"
    AI_ARCHITECT = "AI_ARCHITECT"

    # 4. DESIGN LAYER
    UX_RESEARCHER = "UX_RESEARCHER"
    UX_ARCHITECT = "UX_ARCHITECT"
    UI_UX_DESIGNER = "UI_UX_DESIGNER"
    DESIGN_SYSTEM_ENGINEER = "DESIGN_SYSTEM_ENGINEER"
    VISUAL_DESIGN_REVIEWER = "VISUAL_DESIGN_REVIEWER"
    VISUAL_SCREENSHOT_ANALYST = "VISUAL_SCREENSHOT_ANALYST"  # Alias

    # 5. ENGINEERING LAYER
    FRONTEND_ARCHITECT = "FRONTEND_ARCHITECT"
    FRONTEND_ENGINEER = "FRONTEND_ENGINEER"
    BACKEND_ARCHITECT = "BACKEND_ARCHITECT"
    BACKEND_ENGINEER = "BACKEND_ENGINEER"
    DATABASE_ENGINEER = "DATABASE_ENGINEER"
    AI_ENGINEER = "AI_ENGINEER"
    INTEGRATION_ENGINEER = "INTEGRATION_ENGINEER"
    INFRASTRUCTURE_ENGINEER = "INFRASTRUCTURE_ENGINEER"

    # 6. SPECIALIZED ENGINEERING
    GAME_ENGINEER = "GAME_ENGINEER"
    SIMULATION_ENGINEER = "SIMULATION_ENGINEER"
    GRAPHICS_3D_ENGINEER = "GRAPHICS_3D_ENGINEER"
    MEDIA_ENGINEER = "MEDIA_ENGINEER"
    IOT_HARDWARE_ENGINEER = "IOT_HARDWARE_ENGINEER"
    DATA_ENGINEER = "DATA_ENGINEER"

    # 7. QUALITY LAYER
    TEST_ENGINEER = "TEST_ENGINEER"
    DEBUG_ENGINEER = "DEBUG_ENGINEER"
    FAST_REPAIR_AGENT = "FAST_REPAIR_AGENT"  # Alias
    BROWSER_QA_ENGINEER = "BROWSER_QA_ENGINEER"
    BROWSER_GUI_AGENT = "BROWSER_GUI_AGENT"  # Alias
    VISUAL_QA_ENGINEER = "VISUAL_QA_ENGINEER"
    SECURITY_ENGINEER = "SECURITY_ENGINEER"
    PERFORMANCE_ENGINEER = "PERFORMANCE_ENGINEER"
    CODE_REVIEWER = "CODE_REVIEWER"
    ARCHITECTURE_REVIEWER = "ARCHITECTURE_REVIEWER"

    # 8. FINAL LAYER
    PRODUCT_CRITIC = "PRODUCT_CRITIC"
    AGENT_CRITIC = "AGENT_CRITIC"  # Alias
    RELEASE_ENGINEER = "RELEASE_ENGINEER"
    INDEPENDENT_FINAL_VERIFIER = "INDEPENDENT_FINAL_VERIFIER"
    FINAL_VERIFICATION_ENGINEER = "FINAL_VERIFICATION_ENGINEER"  # Alias
    INDEPENDENT_VERIFIER = "INDEPENDENT_VERIFIER"  # Alias

class AgentState(str, Enum):
    IDLE = "IDLE"
    READY = "READY"
    RUNNING = "RUNNING"
    WAITING = "WAITING"
    BLOCKED = "BLOCKED"
    FAILED = "FAILED"
    COMPLETED = "COMPLETED"
    VERIFIED = "VERIFIED"

class OrchestratorStage(str, Enum):
    DISCOVERY = "DISCOVERY"
    REQUIREMENTS = "REQUIREMENTS"
    PLANNING = "PLANNING"
    APPROVAL = "APPROVAL"
    ARCHITECTURE = "ARCHITECTURE"
    DESIGN = "DESIGN"
    IMPLEMENTATION = "IMPLEMENTATION"
    INTEGRATION = "INTEGRATION"
    TESTING = "TESTING"
    QA = "QA"
    REPAIR = "REPAIR"
    VERIFICATION = "VERIFICATION"
    DELIVERY = "DELIVERY"

class RequirementClass(str, Enum):
    KNOWN = "KNOWN"
    INFERRED = "INFERRED"
    MISSING = "MISSING"
    AMBIGUOUS = "AMBIGUOUS"
    CONFLICTING = "CONFLICTING"
    OPTIONAL = "OPTIONAL"

class VerificationStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    PARTIAL = "PARTIAL"
    BLOCKED = "BLOCKED"

class CheckpointType(str, Enum):
    REQUIREMENTS_COMPLETE = "REQUIREMENTS_COMPLETE"
    PLAN_VERIFIED = "PLAN_VERIFIED"
    ARCHITECTURE_COMPLETE = "ARCHITECTURE_COMPLETE"
    CORE_WORKFLOW_COMPLETE = "CORE_WORKFLOW_COMPLETE"
    FEATURE_COMPLETE = "FEATURE_COMPLETE"
    QA_COMPLETE = "QA_COMPLETE"
    FINAL_VERIFIED = "FINAL_VERIFIED"

class ToolPermissionLevel(str, Enum):
    READ_ONLY = "READ_ONLY"
    SAFE_WRITE = "SAFE_WRITE"
    DESTRUCTIVE = "DESTRUCTIVE"
    EXTERNAL_ACTION = "EXTERNAL_ACTION"


@dataclass
class AgentModelActivity:
    timestamp: float
    model: str
    role: str
    task: str
    status: str
    duration: float = 0.0
    tool_calls: List[str] = field(default_factory=list)
    files_changed: List[str] = field(default_factory=list)
    result: str = ""
    verification_status: str = "PENDING"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class GenerationProvenance:
    project_id: str
    task_id: str
    model: str
    prompt_version: str
    input_context_hash: str
    output_hash: str
    files_created: List[str] = field(default_factory=list)
    files_modified: List[str] = field(default_factory=list)
    tools_used: List[str] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class AdaptiveQuestion:
    question_id: str
    prompt: str
    options: List[str]
    custom_allowed: bool = True
    recommended_default: Optional[str] = None
    can_skip: bool = False
    impact_level: str = "HIGH"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ProductSpecification:
    product_name: str
    product_purpose: str
    target_users: List[str]
    problem: str
    domain: str
    platform: str
    core_workflow: List[str]
    features: List[str]
    entities: List[str]
    user_actions: List[str]
    inputs: List[str]
    outputs: List[str]
    business_rules: List[str]
    constraints: Dict[str, Any] = field(default_factory=dict)
    integrations: List[str] = field(default_factory=list)
    ai_requirements: List[str] = field(default_factory=list)
    security_requirements: List[str] = field(default_factory=list)
    performance_requirements: List[str] = field(default_factory=list)
    data_requirements: List[str] = field(default_factory=list)
    deployment_requirements: List[str] = field(default_factory=list)
    testing_requirements: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ProductDNA:
    identity: str
    purpose: str
    audience: List[str]
    core_experience: str
    workflow: List[str]
    feature_model: Dict[str, Any]
    information_architecture: Dict[str, Any]
    navigation: List[str]
    interaction_model: str
    visual_identity: Dict[str, Any]
    technology: Dict[str, Any]
    architecture: Dict[str, Any]
    data_model: Dict[str, Any]
    integrations: List[str]
    testing_strategy: str
    deployment_strategy: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ModelHandoffContract:
    """
    Explicit, structured communication contract between virtual company specialists (§6).
    Eliminates vague hidden context and ensures exact boundary compliance.
    """
    project_id: str
    task_id: str
    from_role: AgentRole
    to_role: AgentRole
    product_specification: Optional[Dict[str, Any]] = None
    requirements: List[str] = field(default_factory=list)
    acceptance_criteria: List[str] = field(default_factory=list)
    technology_decision: Optional[Dict[str, Any]] = None
    architecture: Optional[Dict[str, Any]] = None
    relevant_files: List[str] = field(default_factory=list)
    current_project_state: str = "READY"
    previous_results: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    constraints: Dict[str, Any] = field(default_factory=dict)
    expected_output: str = ""
    verification_criteria: str = ""
    evidence: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["from_role"] = self.from_role.value if isinstance(self.from_role, Enum) else self.from_role
        d["to_role"] = self.to_role.value if isinstance(self.to_role, Enum) else self.to_role
        return d


@dataclass
class VerificationMatrixItem:
    requirement_id: str
    requirement_text: str
    implementation_ref: str
    file_ref: str
    test_ref: str
    evidence: str
    status: VerificationStatus

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["status"] = self.status.value if isinstance(self.status, Enum) else self.status
        return d
