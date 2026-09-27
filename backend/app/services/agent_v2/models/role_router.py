import time
import logging
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any, Tuple
from app.services.agent_v2.core.contracts import AgentRole
from app.services.agent.model_router import (
    AgentModelCapability,
    AgentModelProfile,
    AgentModelRegistry,
    AgentModelRouter,
    agent_model_registry
)
from app.services.nvidia.chat import NvidiaChatProvider

logger = logging.getLogger("hsbot.agent_v2.models")


@dataclass
class AgentNvidiaModelHealth:
    model_id: str
    is_healthy: bool = True
    consecutive_errors: int = 0
    average_latency_ms: float = 1200.0
    last_verified: float = field(default_factory=time.time)
    circuit_breaker_active: bool = False
    cooldown_until: float = 0.0

    def record_success(self, latency_ms: float):
        self.is_healthy = True
        self.consecutive_errors = 0
        self.average_latency_ms = 0.8 * self.average_latency_ms + 0.2 * latency_ms
        self.circuit_breaker_active = False

    def record_failure(self):
        self.consecutive_errors += 1
        if self.consecutive_errors >= 3:
            self.circuit_breaker_active = True
            self.is_healthy = False
            self.cooldown_until = time.time() + 60.0


@dataclass
class AgentNvidiaModelScore:
    model_id: str
    reasoning: float = 0.8
    coding: float = 0.8
    planning: float = 0.8
    agentic_ability: float = 0.8
    tool_use: float = 0.8
    context_tokens: int = 128000
    has_vision: bool = False
    has_multimodal: bool = False
    reliability: float = 0.95
    latency_score: float = 0.85

    def calculate_score(self, task_type: str = "coding", needs_vision: bool = False) -> float:
        if needs_vision and not self.has_vision:
            return 0.0
        if task_type == "architecture" or task_type == "planning":
            return (
                0.35 * self.reasoning +
                0.25 * self.planning +
                0.15 * self.agentic_ability +
                0.10 * self.tool_use +
                0.10 * self.reliability +
                0.05 * self.latency_score
            )
        elif task_type == "coding":
            return (
                0.35 * self.coding +
                0.20 * self.reasoning +
                0.15 * self.agentic_ability +
                0.15 * self.tool_use +
                0.10 * self.reliability +
                0.05 * self.latency_score
            )
        elif task_type == "vision":
            return (
                0.40 * (1.0 if self.has_vision else 0.0) +
                0.25 * self.reasoning +
                0.15 * self.agentic_ability +
                0.10 * self.reliability +
                0.10 * self.latency_score
            )
        else:
            return (
                0.25 * self.reasoning +
                0.25 * self.coding +
                0.15 * self.agentic_ability +
                0.10 * self.tool_use +
                0.15 * self.reliability +
                0.10 * self.latency_score
            )


class AgentNvidiaCapabilityRegistry:
    """Registry of NVIDIA hosted model profiles, context sizes, and modalities."""
    CAPABILITY_PROFILES: Dict[str, AgentNvidiaModelScore] = {
        "nvidia/nemotron-3-ultra-550b-a55b": AgentNvidiaModelScore(
            model_id="nvidia/nemotron-3-ultra-550b-a55b",
            reasoning=0.98,
            coding=0.96,
            planning=0.99,
            agentic_ability=0.98,
            tool_use=0.97,
            context_tokens=1000000,
            has_vision=False,
            has_multimodal=False,
            reliability=0.96,
            latency_score=0.75
        ),
        "nvidia/nemotron-3.5-lightning-30b-a3b": AgentNvidiaModelScore(
            model_id="nvidia/nemotron-3.5-lightning-30b-a3b",
            reasoning=0.88,
            coding=0.87,
            planning=0.85,
            agentic_ability=0.92,
            tool_use=0.90,
            context_tokens=128000,
            has_vision=False,
            has_multimodal=False,
            reliability=0.98,
            latency_score=0.95
        ),
        "moonshotai/kimi-k3": AgentNvidiaModelScore(
            model_id="moonshotai/kimi-k3",
            reasoning=0.94,
            coding=0.97,
            planning=0.91,
            agentic_ability=0.95,
            tool_use=0.94,
            context_tokens=256000,
            has_vision=True,
            has_multimodal=True,
            reliability=0.94,
            latency_score=0.85
        ),
        "meta/muse-glimmer-30b": AgentNvidiaModelScore(
            model_id="meta/muse-glimmer-30b",
            reasoning=0.86,
            coding=0.80,
            planning=0.82,
            agentic_ability=0.88,
            tool_use=0.85,
            context_tokens=64000,
            has_vision=True,
            has_multimodal=True,
            reliability=0.92,
            latency_score=0.90
        ),
        "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning": AgentNvidiaModelScore(
            model_id="nvidia/nemotron-3-nano-omni-30b-a3b-reasoning",
            reasoning=0.87,
            coding=0.82,
            planning=0.84,
            agentic_ability=0.90,
            tool_use=0.88,
            context_tokens=64000,
            has_vision=True,
            has_multimodal=True,
            reliability=0.93,
            latency_score=0.92
        ),
        "nvidia/nemotron-3-super-120b-a12b": AgentNvidiaModelScore(
            model_id="nvidia/nemotron-3-super-120b-a12b",
            reasoning=0.93,
            coding=0.91,
            planning=0.92,
            agentic_ability=0.93,
            tool_use=0.92,
            context_tokens=128000,
            has_vision=False,
            has_multimodal=False,
            reliability=0.95,
            latency_score=0.82
        ),
        "llama-3.1-70b": AgentNvidiaModelScore(
            model_id="llama-3.1-70b",
            reasoning=0.92,
            coding=0.91,
            planning=0.90,
            agentic_ability=0.91,
            tool_use=0.90,
            context_tokens=128000,
            has_vision=False,
            has_multimodal=False,
            reliability=0.95,
            latency_score=0.88
        ),
        "codestral": AgentNvidiaModelScore(
            model_id="codestral",
            reasoning=0.89,
            coding=0.94,
            planning=0.84,
            agentic_ability=0.89,
            tool_use=0.92,
            context_tokens=32000,
            has_vision=False,
            has_multimodal=False,
            reliability=0.93,
            latency_score=0.86
        ),
        "llama-3.2-11b": AgentNvidiaModelScore(
            model_id="llama-3.2-11b",
            reasoning=0.84,
            coding=0.82,
            planning=0.80,
            agentic_ability=0.83,
            tool_use=0.82,
            context_tokens=128000,
            has_vision=True,
            has_multimodal=True,
            reliability=0.96,
            latency_score=0.97
        )
    }

    @classmethod
    def get_profile(cls, model_id: str) -> Optional[AgentNvidiaModelScore]:
        return cls.CAPABILITY_PROFILES.get(model_id)


class AgentNvidiaModelRegistry:
    """Manages active health, scores, and runtime availability for NVIDIA Agent models."""
    def __init__(self):
        self._health: Dict[str, AgentNvidiaModelHealth] = {
            m: AgentNvidiaModelHealth(model_id=m)
            for m in AgentNvidiaCapabilityRegistry.CAPABILITY_PROFILES.keys()
        }

    def get_health(self, model_id: str) -> AgentNvidiaModelHealth:
        if model_id not in self._health:
            self._health[model_id] = AgentNvidiaModelHealth(model_id=model_id)
        return self._health[model_id]

    def reset_health(self, model_id: str):
        self._health[model_id] = AgentNvidiaModelHealth(model_id=model_id)


class AgentNvidiaModelRouter:
    """
    Selects primary model, fallback model, and last-resort compatible model
    using the multi-vector scoring algorithm (§13, §14, §15, §40, §48).
    """
    def __init__(self, registry: Optional[AgentNvidiaModelRegistry] = None):
        self.registry = registry or AgentNvidiaModelRegistry()

    def select_model(
        self,
        task_type: str,
        needs_vision: bool = False,
        preferred_model: Optional[str] = None
    ) -> Tuple[str, str, Optional[str]]:
        """
        Returns (primary_model, fallback_model, last_resort_model)
        """
        candidates = list(AgentNvidiaCapabilityRegistry.CAPABILITY_PROFILES.values())

        # If vision is required, filter to models supporting vision
        if needs_vision:
            candidates = [c for c in candidates if c.has_vision]

        # Filter out circuit-broken models if alternates exist
        healthy_candidates = [
            c for c in candidates
            if not self.registry.get_health(c.model_id).circuit_breaker_active
        ]
        pool = healthy_candidates if healthy_candidates else candidates

        # Score all pool models
        scored = sorted(
            pool,
            key=lambda c: (
                1.0 if c.model_id == preferred_model else 0.0,
                c.calculate_score(task_type, needs_vision)
            ),
            reverse=True
        )

        primary = scored[0].model_id if scored else "llama-3.1-70b"
        fallback = scored[1].model_id if len(scored) > 1 else "llama-3.1-70b"
        last_resort = scored[2].model_id if len(scored) > 2 else "llama-3.2-11b"

        return primary, fallback, last_resort


@dataclass
class RoleModelConfig:
    role: AgentRole
    role_name: str
    model: str
    responsibility: str
    capability: AgentModelCapability
    fallback_model: str = "llama-3.1-70b"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "role": self.role.value,
            "role_name": self.role_name,
            "model": self.model,
            "responsibility": self.responsibility,
            "capability": self.capability.value,
            "fallback_model": self.fallback_model
        }


# Exact specification table for all Virtual Company roles, models, and responsibilities
ROLE_MODEL_REGISTRY: Dict[AgentRole, RoleModelConfig] = {
    # 1. Product Director
    AgentRole.PRODUCT_DIRECTOR: RoleModelConfig(
        role=AgentRole.PRODUCT_DIRECTOR,
        role_name="Product Director",
        model="nvidia/nemotron-3-ultra-550b-a55b",
        responsibility="Understand the user's product idea, scope, difficult product decisions",
        capability=AgentModelCapability.REASONING,
        fallback_model="llama-3.1-70b"
    ),
    AgentRole.CEO_PRODUCT_DIRECTOR: RoleModelConfig(
        role=AgentRole.CEO_PRODUCT_DIRECTOR,
        role_name="Product Director",
        model="nvidia/nemotron-3-ultra-550b-a55b",
        responsibility="Understand the user's product idea, scope, difficult product decisions",
        capability=AgentModelCapability.REASONING,
        fallback_model="llama-3.1-70b"
    ),
    AgentRole.PRODUCT_STRATEGIST: RoleModelConfig(
        role=AgentRole.PRODUCT_STRATEGIST,
        role_name="Product Strategist",
        model="nvidia/nemotron-3-ultra-550b-a55b",
        responsibility="Market differentiation, competitive edge, and feature prioritization",
        capability=AgentModelCapability.REASONING,
        fallback_model="llama-3.1-70b"
    ),
    AgentRole.REQUIREMENTS_DIRECTOR: RoleModelConfig(
        role=AgentRole.REQUIREMENTS_DIRECTOR,
        role_name="Requirements Director",
        model="nvidia/nemotron-3-ultra-550b-a55b",
        responsibility="Requirement completeness verification and acceptance governance",
        capability=AgentModelCapability.REQUIREMENT_ANALYSIS,
        fallback_model="llama-3.1-70b"
    ),

    # 2. Discovery Layer
    AgentRole.PRODUCT_ANALYST: RoleModelConfig(
        role=AgentRole.PRODUCT_ANALYST,
        role_name="Requirements Analyst",
        model="nvidia/nemotron-3-ultra-550b-a55b",
        responsibility="Find missing/ambiguous requirements and decide what must be asked",
        capability=AgentModelCapability.REQUIREMENT_ANALYSIS,
        fallback_model="llama-3.1-70b"
    ),
    AgentRole.REQUIREMENTS_ANALYST: RoleModelConfig(
        role=AgentRole.REQUIREMENTS_ANALYST,
        role_name="Requirements Analyst",
        model="nvidia/nemotron-3-ultra-550b-a55b",
        responsibility="Find missing/ambiguous requirements and decide what must be asked",
        capability=AgentModelCapability.REQUIREMENT_ANALYSIS,
        fallback_model="llama-3.1-70b"
    ),
    AgentRole.RESEARCH_AGENT: RoleModelConfig(
        role=AgentRole.RESEARCH_AGENT,
        role_name="Research Agent",
        model="nvidia/nemotron-3-super-120b-a12b",
        responsibility="Research external libraries, documentation, APIs, and domain constraints",
        capability=AgentModelCapability.UNDERSTANDING,
        fallback_model="llama-3.1-70b"
    ),
    AgentRole.RESEARCH_TECHNICAL_ANALYST: RoleModelConfig(
        role=AgentRole.RESEARCH_TECHNICAL_ANALYST,
        role_name="Research / Technical Analyst",
        model="nvidia/nemotron-3-super-120b-a12b",
        responsibility="Research technical options and constraints",
        capability=AgentModelCapability.UNDERSTANDING,
        fallback_model="llama-3.1-70b"
    ),
    AgentRole.DOMAIN_ANALYST: RoleModelConfig(
        role=AgentRole.DOMAIN_ANALYST,
        role_name="Domain Analyst",
        model="nvidia/nemotron-3-super-120b-a12b",
        responsibility="Extract industry norms, regulatory constraints, and domain standards",
        capability=AgentModelCapability.UNDERSTANDING,
        fallback_model="llama-3.1-70b"
    ),
    AgentRole.REQUIREMENT_VALIDATOR: RoleModelConfig(
        role=AgentRole.REQUIREMENT_VALIDATOR,
        role_name="Requirement Validator",
        model="nvidia/nemotron-3-ultra-550b-a55b",
        responsibility="Verify requirement consistency, eliminate conflicts and ambiguous scope",
        capability=AgentModelCapability.REQUIREMENT_ANALYSIS,
        fallback_model="llama-3.1-70b"
    ),

    # 3. Planning Layer
    AgentRole.MASTER_PLANNER: RoleModelConfig(
        role=AgentRole.MASTER_PLANNER,
        role_name="Master Planner",
        model="nvidia/nemotron-3-ultra-550b-a55b",
        responsibility="Produce the complete implementation plan and task decomposition",
        capability=AgentModelCapability.ARCHITECTURE,
        fallback_model="llama-3.1-70b"
    ),
    AgentRole.SOLUTION_ARCHITECT: RoleModelConfig(
        role=AgentRole.SOLUTION_ARCHITECT,
        role_name="Solution Architect",
        model="nvidia/nemotron-3-ultra-550b-a55b",
        responsibility="Architecture, services, APIs, data flow, system boundaries",
        capability=AgentModelCapability.ARCHITECTURE,
        fallback_model="llama-3.1-70b"
    ),
    AgentRole.TECHNICAL_ARCHITECT: RoleModelConfig(
        role=AgentRole.TECHNICAL_ARCHITECT,
        role_name="Technical Architect",
        model="nvidia/nemotron-3-ultra-550b-a55b",
        responsibility="Low-level software patterns, concurrency, protocol, and runtime choices",
        capability=AgentModelCapability.ARCHITECTURE,
        fallback_model="llama-3.1-70b"
    ),
    AgentRole.DATA_ARCHITECT: RoleModelConfig(
        role=AgentRole.DATA_ARCHITECT,
        role_name="Data Architect",
        model="nvidia/nemotron-3-super-120b-a12b",
        responsibility="Data modeling, state persistence, schema migrations, and consistency",
        capability=AgentModelCapability.ARCHITECTURE,
        fallback_model="codestral"
    ),
    AgentRole.AI_ARCHITECT: RoleModelConfig(
        role=AgentRole.AI_ARCHITECT,
        role_name="AI Architect",
        model="nvidia/nemotron-3-ultra-550b-a55b",
        responsibility="AI models, agent loops, prompt topology, and embedding strategies",
        capability=AgentModelCapability.REASONING,
        fallback_model="llama-3.1-70b"
    ),

    # 4. Design Layer
    AgentRole.UX_RESEARCHER: RoleModelConfig(
        role=AgentRole.UX_RESEARCHER,
        role_name="UX Researcher",
        model="nvidia/nemotron-3-super-120b-a12b",
        responsibility="User journeys, information architecture, interaction design",
        capability=AgentModelCapability.UNDERSTANDING,
        fallback_model="llama-3.2-11b"
    ),
    AgentRole.UX_ARCHITECT: RoleModelConfig(
        role=AgentRole.UX_ARCHITECT,
        role_name="UX Architect",
        model="nvidia/nemotron-3-super-120b-a12b",
        responsibility="Information hierarchy, screen flows, state transitions, and usability",
        capability=AgentModelCapability.UNDERSTANDING,
        fallback_model="llama-3.2-11b"
    ),
    AgentRole.UI_UX_DESIGNER: RoleModelConfig(
        role=AgentRole.UI_UX_DESIGNER,
        role_name="UI/UX Designer",
        model="moonshotai/kimi-k3",
        responsibility="Product-specific UI/UX, screens, visual structures, design-to-code reasoning",
        capability=AgentModelCapability.UI,
        fallback_model="llama-3.2-11b"
    ),
    AgentRole.DESIGN_SYSTEM_ENGINEER: RoleModelConfig(
        role=AgentRole.DESIGN_SYSTEM_ENGINEER,
        role_name="Design System Engineer",
        model="moonshotai/kimi-k3",
        responsibility="Component primitives, typography, theme tokens, and color system",
        capability=AgentModelCapability.UI,
        fallback_model="llama-3.2-11b"
    ),
    AgentRole.VISUAL_DESIGN_REVIEWER: RoleModelConfig(
        role=AgentRole.VISUAL_DESIGN_REVIEWER,
        role_name="Visual Design Reviewer",
        model="meta/muse-glimmer-30b",
        responsibility="Inspect visual hierarchy, alignment, contrast, and typography execution",
        capability=AgentModelCapability.VISION,
        fallback_model="llama-3.2-11b"
    ),
    AgentRole.VISUAL_SCREENSHOT_ANALYST: RoleModelConfig(
        role=AgentRole.VISUAL_SCREENSHOT_ANALYST,
        role_name="Visual / Screenshot Analyst",
        model="meta/muse-glimmer-30b",
        responsibility="Analyze screenshots, existing UI, visual defects, visual references",
        capability=AgentModelCapability.VISION,
        fallback_model="llama-3.2-11b"
    ),

    # 5. Engineering Layer
    AgentRole.FRONTEND_ARCHITECT: RoleModelConfig(
        role=AgentRole.FRONTEND_ARCHITECT,
        role_name="Frontend Architect",
        model="moonshotai/kimi-k3",
        responsibility="Frontend architecture, state, component strategy",
        capability=AgentModelCapability.CODING,
        fallback_model="codestral"
    ),
    AgentRole.FRONTEND_ENGINEER: RoleModelConfig(
        role=AgentRole.FRONTEND_ENGINEER,
        role_name="Frontend Engineer",
        model="moonshotai/kimi-k3",
        responsibility="Long-horizon frontend implementation and repository-level coding",
        capability=AgentModelCapability.CODING,
        fallback_model="codestral"
    ),
    AgentRole.BACKEND_ARCHITECT: RoleModelConfig(
        role=AgentRole.BACKEND_ARCHITECT,
        role_name="Backend Architect",
        model="nvidia/nemotron-3-super-120b-a12b",
        responsibility="Services, APIs, business logic, backend architecture",
        capability=AgentModelCapability.ARCHITECTURE,
        fallback_model="llama-3.1-70b"
    ),
    AgentRole.BACKEND_ENGINEER: RoleModelConfig(
        role=AgentRole.BACKEND_ENGINEER,
        role_name="Backend Engineer",
        model="moonshotai/kimi-k3",
        responsibility="Backend implementation and integration",
        capability=AgentModelCapability.CODING,
        fallback_model="codestral"
    ),
    AgentRole.DATABASE_ENGINEER: RoleModelConfig(
        role=AgentRole.DATABASE_ENGINEER,
        role_name="Database Engineer",
        model="nvidia/nemotron-3-super-120b-a12b",
        responsibility="Schema, migrations, indexes, persistence",
        capability=AgentModelCapability.CODING,
        fallback_model="codestral"
    ),
    AgentRole.AI_ENGINEER: RoleModelConfig(
        role=AgentRole.AI_ENGINEER,
        role_name="AI Engineer",
        model="nvidia/nemotron-3-ultra-550b-a55b",
        responsibility="AI architecture, agent flows, RAG/tool strategy",
        capability=AgentModelCapability.REASONING,
        fallback_model="llama-3.1-70b"
    ),
    AgentRole.INTEGRATION_ENGINEER: RoleModelConfig(
        role=AgentRole.INTEGRATION_ENGINEER,
        role_name="Integration Engineer",
        model="nvidia/nemotron-3.5-lightning-30b-a3b",
        responsibility="API integrations, repetitive tool/integration work",
        capability=AgentModelCapability.CODING,
        fallback_model="codestral"
    ),
    AgentRole.INFRASTRUCTURE_ENGINEER: RoleModelConfig(
        role=AgentRole.INFRASTRUCTURE_ENGINEER,
        role_name="Infrastructure Engineer",
        model="nvidia/nemotron-3-super-120b-a12b",
        responsibility="Build configuration, scripts, bundling, and deployment setup",
        capability=AgentModelCapability.CODING,
        fallback_model="codestral"
    ),

    # 6. Specialized Engineering
    AgentRole.GAME_ENGINEER: RoleModelConfig(
        role=AgentRole.GAME_ENGINEER,
        role_name="Game Engineer",
        model="moonshotai/kimi-k3",
        responsibility="Game code, gameplay systems, engine logic",
        capability=AgentModelCapability.CODING,
        fallback_model="codestral"
    ),
    AgentRole.SIMULATION_ENGINEER: RoleModelConfig(
        role=AgentRole.SIMULATION_ENGINEER,
        role_name="Simulation Engineer",
        model="moonshotai/kimi-k3",
        responsibility="Agent-based models, physical simulations, time-stepped calculations",
        capability=AgentModelCapability.CODING,
        fallback_model="codestral"
    ),
    AgentRole.GRAPHICS_3D_ENGINEER: RoleModelConfig(
        role=AgentRole.GRAPHICS_3D_ENGINEER,
        role_name="3D / Graphics Engineer",
        model="moonshotai/kimi-k3",
        responsibility="Three.js/WebGL/graphics-heavy implementation",
        capability=AgentModelCapability.CODING,
        fallback_model="codestral"
    ),
    AgentRole.MEDIA_ENGINEER: RoleModelConfig(
        role=AgentRole.MEDIA_ENGINEER,
        role_name="Media Engineer",
        model="moonshotai/kimi-k3",
        responsibility="Audio, video, waveform processing, and media pipelines",
        capability=AgentModelCapability.CODING,
        fallback_model="codestral"
    ),
    AgentRole.IOT_HARDWARE_ENGINEER: RoleModelConfig(
        role=AgentRole.IOT_HARDWARE_ENGINEER,
        role_name="IoT / Hardware Engineer",
        model="nvidia/nemotron-3-super-120b-a12b",
        responsibility="Sensor telemetry, serial/websocket protocols, and device status",
        capability=AgentModelCapability.CODING,
        fallback_model="codestral"
    ),
    AgentRole.DATA_ENGINEER: RoleModelConfig(
        role=AgentRole.DATA_ENGINEER,
        role_name="Data Engineer",
        model="nvidia/nemotron-3-super-120b-a12b",
        responsibility="Data pipelines, transformations, ETL, and export utilities",
        capability=AgentModelCapability.CODING,
        fallback_model="codestral"
    ),

    # 7. Quality Layer
    AgentRole.TEST_ENGINEER: RoleModelConfig(
        role=AgentRole.TEST_ENGINEER,
        role_name="Test Engineer",
        model="nvidia/nemotron-3-super-120b-a12b",
        responsibility="Unit/integration/E2E test generation and analysis",
        capability=AgentModelCapability.TESTING,
        fallback_model="codestral"
    ),
    AgentRole.DEBUG_ENGINEER: RoleModelConfig(
        role=AgentRole.DEBUG_ENGINEER,
        role_name="Debug Engineer",
        model="nvidia/nemotron-3-super-120b-a12b",
        responsibility="Diagnose errors, trace failures, repair code",
        capability=AgentModelCapability.DEBUGGING,
        fallback_model="codestral"
    ),
    AgentRole.FAST_REPAIR_AGENT: RoleModelConfig(
        role=AgentRole.FAST_REPAIR_AGENT,
        role_name="Fast Repair Agent",
        model="nvidia/nemotron-3.5-lightning-30b-a3b",
        responsibility="Small fixes, repetitive corrections, quick retries",
        capability=AgentModelCapability.DEBUGGING,
        fallback_model="codestral"
    ),
    AgentRole.BROWSER_QA_ENGINEER: RoleModelConfig(
        role=AgentRole.BROWSER_QA_ENGINEER,
        role_name="Browser QA Engineer",
        model="nvidia/nemotron-3-nano-omni-30b-a3b-reasoning",
        responsibility="Browser interaction testing, form workflows, navigation QA",
        capability=AgentModelCapability.VISION,
        fallback_model="llama-3.2-11b"
    ),
    AgentRole.BROWSER_GUI_AGENT: RoleModelConfig(
        role=AgentRole.BROWSER_GUI_AGENT,
        role_name="Browser / GUI Agent",
        model="nvidia/nemotron-3-nano-omni-30b-a3b-reasoning",
        responsibility="Screenshot/GUI understanding and browser-oriented multimodal work",
        capability=AgentModelCapability.VISION,
        fallback_model="llama-3.2-11b"
    ),
    AgentRole.VISUAL_QA_ENGINEER: RoleModelConfig(
        role=AgentRole.VISUAL_QA_ENGINEER,
        role_name="Visual QA Engineer",
        model="meta/muse-glimmer-30b",
        responsibility="Inspect rendered interfaces and identify visual problems",
        capability=AgentModelCapability.VISION,
        fallback_model="llama-3.2-11b"
    ),
    AgentRole.SECURITY_ENGINEER: RoleModelConfig(
        role=AgentRole.SECURITY_ENGINEER,
        role_name="Security Engineer",
        model="nvidia/nemotron-3-ultra-550b-a55b",
        responsibility="Deep security and architecture review",
        capability=AgentModelCapability.REASONING,
        fallback_model="llama-3.1-70b"
    ),
    AgentRole.PERFORMANCE_ENGINEER: RoleModelConfig(
        role=AgentRole.PERFORMANCE_ENGINEER,
        role_name="Performance Engineer",
        model="nvidia/nemotron-3-super-120b-a12b",
        responsibility="Performance analysis and optimization",
        capability=AgentModelCapability.REASONING,
        fallback_model="llama-3.1-70b"
    ),
    AgentRole.CODE_REVIEWER: RoleModelConfig(
        role=AgentRole.CODE_REVIEWER,
        role_name="Code Reviewer",
        model="nvidia/nemotron-3-ultra-550b-a55b",
        responsibility="Independent architecture/code review",
        capability=AgentModelCapability.REVIEW,
        fallback_model="llama-3.1-70b"
    ),
    AgentRole.ARCHITECTURE_REVIEWER: RoleModelConfig(
        role=AgentRole.ARCHITECTURE_REVIEWER,
        role_name="Architecture Reviewer",
        model="nvidia/nemotron-3-ultra-550b-a55b",
        responsibility="Validate architecture boundaries, modularity, and technical feasibility",
        capability=AgentModelCapability.REVIEW,
        fallback_model="llama-3.1-70b"
    ),

    # 8. Final Layer
    AgentRole.PRODUCT_CRITIC: RoleModelConfig(
        role=AgentRole.PRODUCT_CRITIC,
        role_name="Product Critic",
        model="nvidia/nemotron-3-super-120b-a12b",
        responsibility="Check whether the product actually matches the requested idea",
        capability=AgentModelCapability.REASONING,
        fallback_model="llama-3.1-70b"
    ),
    AgentRole.AGENT_CRITIC: RoleModelConfig(
        role=AgentRole.AGENT_CRITIC,
        role_name="Product Critic",
        model="nvidia/nemotron-3-super-120b-a12b",
        responsibility="Check whether the product actually matches the requested idea",
        capability=AgentModelCapability.REASONING,
        fallback_model="llama-3.1-70b"
    ),
    AgentRole.RELEASE_ENGINEER: RoleModelConfig(
        role=AgentRole.RELEASE_ENGINEER,
        role_name="Release Engineer",
        model="nvidia/nemotron-3-ultra-550b-a55b",
        responsibility="Packaging, artifact creation, distribution verification, and manifest finalization",
        capability=AgentModelCapability.VERIFICATION,
        fallback_model="llama-3.1-70b"
    ),
    AgentRole.INDEPENDENT_FINAL_VERIFIER: RoleModelConfig(
        role=AgentRole.INDEPENDENT_FINAL_VERIFIER,
        role_name="Final Verification Engineer",
        model="nvidia/nemotron-3-ultra-550b-a55b",
        responsibility="Independent final acceptance against requirements",
        capability=AgentModelCapability.VERIFICATION,
        fallback_model="llama-3.1-70b"
    ),
    AgentRole.FINAL_VERIFICATION_ENGINEER: RoleModelConfig(
        role=AgentRole.FINAL_VERIFICATION_ENGINEER,
        role_name="Final Verification Engineer",
        model="nvidia/nemotron-3-ultra-550b-a55b",
        responsibility="Independent final acceptance against requirements",
        capability=AgentModelCapability.VERIFICATION,
        fallback_model="llama-3.1-70b"
    ),
    AgentRole.INDEPENDENT_VERIFIER: RoleModelConfig(
        role=AgentRole.INDEPENDENT_VERIFIER,
        role_name="Final Verification Engineer",
        model="nvidia/nemotron-3-ultra-550b-a55b",
        responsibility="Independent final acceptance against requirements",
        capability=AgentModelCapability.VERIFICATION,
        fallback_model="llama-3.1-70b"
    ),
}

# Derived mapping of Agent Roles to Primary Capabilities
ROLE_CAPABILITY_MAP: Dict[AgentRole, AgentModelCapability] = {
    role: cfg.capability for role, cfg in ROLE_MODEL_REGISTRY.items()
}


class AgentRoleRouter:
    """
    Coordinates role-specialized model routing across the Virtual Engineering Organization.
    Strictly isolates model execution to Agent Mode while leveraging verified NVIDIA NIM endpoints.
    """

    def __init__(self, registry: Optional[AgentModelRegistry] = None, provider: Optional[NvidiaChatProvider] = None):
        self.registry = registry or agent_model_registry
        self.provider = provider or NvidiaChatProvider()
        self.router = AgentModelRouter(self.registry, self.provider)

    @classmethod
    def get_role_config(cls, role: AgentRole) -> Optional[RoleModelConfig]:
        return ROLE_MODEL_REGISTRY.get(role)

    @classmethod
    def get_model_for_role(cls, role: AgentRole) -> str:
        cfg = ROLE_MODEL_REGISTRY.get(role)
        return cfg.model if cfg else "nvidia/nemotron-3-ultra-550b-a55b"

    @classmethod
    def get_role_manifest(cls) -> List[Dict[str, Any]]:
        seen_roles = set()
        manifest = []
        for role, cfg in ROLE_MODEL_REGISTRY.items():
            if cfg.role_name not in seen_roles:
                seen_roles.add(cfg.role_name)
                manifest.append(cfg.to_dict())
        return manifest

    def route_role(self, role: AgentRole, preferred_model: Optional[str] = None) -> AgentModelProfile:
        cfg = ROLE_MODEL_REGISTRY.get(role)
        capability = cfg.capability if cfg else AgentModelCapability.REASONING
        # Use explicit preferred model or role's configured model/fallback
        target_model = preferred_model or (cfg.fallback_model if cfg else None)
        return self.router.route(capability, preferred_model=target_model)

    async def execute_for_role(
        self,
        role: AgentRole,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        preferred_model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        json_mode: bool = False,
        timeout_seconds: float = 60.0
    ) -> Tuple[Optional[str], str]:
        """
        Executes an agent task specialized for the given company role with capability routing & fallback.
        """
        cfg = ROLE_MODEL_REGISTRY.get(role)
        capability = cfg.capability if cfg else AgentModelCapability.REASONING
        target_model = preferred_model or (cfg.fallback_model if cfg else None)
        return await self.router.execute_task(
            capability=capability,
            messages=messages,
            system_prompt=system_prompt,
            preferred_model=target_model,
            temperature=temperature,
            max_tokens=max_tokens,
            json_mode=json_mode,
            timeout_seconds=timeout_seconds
        )


# Global singleton role router
agent_role_router = AgentRoleRouter()
