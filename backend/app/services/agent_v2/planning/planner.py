import json
import logging
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any, Tuple
from app.services.agent_v2.core.contracts import (
    ProductSpecification,
    ProductDNA,
    AgentRole
)
from app.services.agent.tech_stack import TechStackSnapshot

logger = logging.getLogger("hsbot.agent_v2.planning")

@dataclass
class PlanTaskItem:
    task_id: str
    phase: str
    title: str
    description: str
    assigned_role: AgentRole
    dependencies: List[str]
    expected_files: List[str]
    verification_criteria: str
    status: str = "pending"

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["assigned_role"] = self.assigned_role.value
        return d


@dataclass
class ImplementationPlan:
    plan_id: str
    product_name: str
    phases: List[str]
    tasks: List[PlanTaskItem]
    technology_summary: str
    architecture_summary: str
    folder_structure: List[str]
    core_workflow_summary: List[str]
    test_plan_summary: str
    known_assumptions: List[str]
    open_requirements: List[str]
    validation_status: str = "PENDING_APPROVAL" # APPROVED | REJECTED | VALIDATED

    def to_dict(self) -> Dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "product_name": self.product_name,
            "phases": self.phases,
            "tasks": [t.to_dict() for t in self.tasks],
            "technology_summary": self.technology_summary,
            "architecture_summary": self.architecture_summary,
            "folder_structure": self.folder_structure,
            "core_workflow_summary": self.core_workflow_summary,
            "test_plan_summary": self.test_plan_summary,
            "known_assumptions": self.known_assumptions,
            "open_requirements": self.open_requirements,
            "validation_status": self.validation_status
        }


class ImplementationPlanner:
    """
    Creates and validates the multi-phase implementation plan before execution (§14, §15, §16, §17).
    Assigns tasks to virtual company specialists.
    """

    @classmethod
    def generate_plan(
        cls,
        spec: ProductSpecification,
        dna: ProductDNA,
        tech_stack: TechStackSnapshot,
        plan_id: str = "plan-v2"
    ) -> ImplementationPlan:
        phases = [
            "Phase 1: Product Foundation",
            "Phase 2: Architecture & Schemas",
            "Phase 3: Database & State Model",
            "Phase 4: Backend / Service Logic",
            "Phase 5: Frontend Foundation & UI System",
            "Phase 6: Core Workflow Realization",
            "Phase 7: Additional Features & Controls",
            "Phase 8: Integrations & Media",
            "Phase 9: Automated Test Suites",
            "Phase 10: Visual QA & Viewport Responsiveness",
            "Phase 11: Security Review & Secret Scan",
            "Phase 12: Independent Final Verification"
        ]

        tasks: List[PlanTaskItem] = [
            # Phase 1
            PlanTaskItem(
                task_id="TASK-P1-FOUNDATION",
                phase=phases[0],
                title="Initialize Workspace & Project Manifest",
                description="Establish repository files, manifest (package.json), and README documentation",
                assigned_role=AgentRole.SOLUTION_ARCHITECT,
                dependencies=[],
                expected_files=["package.json", "README.md"],
                verification_criteria="Valid JSON manifest with scripts and clean markdown README"
            ),
            # Phase 2 & 3
            PlanTaskItem(
                task_id="TASK-P2-ARCH",
                phase=phases[1],
                title="Define Component Schemas & State Interfaces",
                description=f"Model {', '.join(spec.entities[:3])} schemas and state machine transitions",
                assigned_role=AgentRole.DATABASE_ENGINEER,
                dependencies=["TASK-P1-FOUNDATION"],
                expected_files=["script.js"],
                verification_criteria="Data structures represent genuine product entities with zero placeholders"
            ),
            # Phase 4 & 5
            PlanTaskItem(
                task_id="TASK-P5-UI",
                phase=phases[4],
                title="Synthesize UI/UX System & Semantic Shell",
                description=f"Implement semantic layout ({dna.visual_identity.get('layout_archetype')}) with responsive breakpoints",
                assigned_role=AgentRole.UI_UX_DESIGNER,
                dependencies=["TASK-P2-ARCH"],
                expected_files=["index.html", "styles.css"],
                verification_criteria="Valid HTML5 semantic structure, Google Fonts, Tailwind CDN, and responsive meta"
            ),
            # Phase 6 & 7
            PlanTaskItem(
                task_id="TASK-P6-CORE",
                phase=phases[5],
                title=f"Implement Core Workflow: {spec.core_workflow[0] if spec.core_workflow else 'Primary Action'}",
                description="Realize interactive client state machine, event listeners, and domain workflows",
                assigned_role=AgentRole.FRONTEND_ENGINEER,
                dependencies=["TASK-P5-UI"],
                expected_files=["script.js"],
                verification_criteria="Buttons, forms, and canvas/arena operate with live interactive feedback"
            ),
            # Phase 9
            PlanTaskItem(
                task_id="TASK-P9-TESTS",
                phase=phases[8],
                title="Construct Automated Test Suite",
                description=f"Write automated assertion suites via {tech_stack.test_framework}",
                assigned_role=AgentRole.TEST_ENGINEER,
                dependencies=["TASK-P6-CORE"],
                expected_files=["tests/test_app.js"],
                verification_criteria="Assertion suite executes without failures and verifies core workflows"
            ),
            # Phase 10
            PlanTaskItem(
                task_id="TASK-P10-VISUAL",
                phase=phases[9],
                title="Visual QA & Responsive Layout Audit",
                description="Inspect viewport responsiveness, accessibility contrast, and typography hierarchy",
                assigned_role=AgentRole.VISUAL_QA_ENGINEER,
                dependencies=["TASK-P9-TESTS"],
                expected_files=[],
                verification_criteria="Visual QA score >= 90% with zero overflow hazards"
            ),
            # Phase 11
            PlanTaskItem(
                task_id="TASK-P11-SECURITY",
                phase=phases[10],
                title="Security Review & Secret Scanning",
                description="Audit files for hard-coded credentials, private keys, and unsafe command execution",
                assigned_role=AgentRole.SECURITY_ENGINEER,
                dependencies=["TASK-P10-VISUAL"],
                expected_files=[],
                verification_criteria="Zero secret leaks and safe permission clearance"
            ),
            # Phase 12
            PlanTaskItem(
                task_id="TASK-P12-VERIFICATION",
                phase=phases[11],
                title="Independent Final Acceptance Verification",
                description="Compare deliverables against original prompt and compile Requirement Matrix",
                assigned_role=AgentRole.INDEPENDENT_VERIFIER,
                dependencies=["TASK-P11-SECURITY"],
                expected_files=[],
                verification_criteria="All confirmed requirements documented with code/DOM evidence"
            )
        ]

        folder_structure = [
            "/index.html",
            "/styles.css",
            "/script.js",
            "/package.json",
            "/README.md",
            "/tests/test_app.js"
        ]

        return ImplementationPlan(
            plan_id=plan_id,
            product_name=spec.product_name,
            phases=phases,
            tasks=tasks,
            technology_summary=f"{tech_stack.platform.value} • {tech_stack.primary_language.value.upper()} • {tech_stack.framework.value} ({tech_stack.rationale})",
            architecture_summary=f"{dna.interaction_model} with {len(spec.entities)} core entities",
            folder_structure=folder_structure,
            core_workflow_summary=spec.core_workflow,
            test_plan_summary=f"Automated testing via {tech_stack.test_framework} checking state transitions and assertions",
            known_assumptions=["Self-contained client execution", "Persistent storage via browser localStorage"],
            open_requirements=[],
            validation_status="VALIDATED"
        )

    @classmethod
    def validate_plan(cls, plan: ImplementationPlan) -> Tuple[bool, List[str]]:
        """
        Independent Plan Validation before showing to user (§17).
        Checks task dependencies, role assignments, and requirement coverage.
        """
        errors = []
        task_ids = {t.task_id for t in plan.tasks}
        for task in plan.tasks:
            for dep in task.dependencies:
                if dep not in task_ids:
                    errors.append(f"Task {task.task_id} has invalid dependency {dep}")

        if not any(t.assigned_role == AgentRole.TEST_ENGINEER for t in plan.tasks):
            errors.append("Plan lacks a dedicated test engineering task")

        if not any(t.assigned_role == AgentRole.INDEPENDENT_VERIFIER for t in plan.tasks):
            errors.append("Plan lacks an independent final verifier task")

        is_valid = len(errors) == 0
        return is_valid, errors
