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

    # 2. Requirements Analyst
    AgentRole.REQUIREMENTS_ANALYST: RoleModelConfig(
        role=AgentRole.REQUIREMENTS_ANALYST,
        role_name="Requirements Analyst",
        model="nvidia/nemotron-3-ultra-550b-a55b",
        responsibility="Find missing/ambiguous requirements and decide what must be asked",
        capability=AgentModelCapability.REQUIREMENT_ANALYSIS,
        fallback_model="llama-3.1-70b"
    ),
    AgentRole.PRODUCT_ANALYST: RoleModelConfig(
        role=AgentRole.PRODUCT_ANALYST,
        role_name="Requirements Analyst",
        model="nvidia/nemotron-3-ultra-550b-a55b",
        responsibility="Find missing/ambiguous requirements and decide what must be asked",
        capability=AgentModelCapability.REQUIREMENT_ANALYSIS,
        fallback_model="llama-3.1-70b"
    ),

    # 3. Research / Technical Analyst
    AgentRole.RESEARCH_TECHNICAL_ANALYST: RoleModelConfig(
        role=AgentRole.RESEARCH_TECHNICAL_ANALYST,
        role_name="Research / Technical Analyst",
        model="nvidia/nemotron-3-super-120b-a12b",
        responsibility="Research technical options and constraints",
        capability=AgentModelCapability.UNDERSTANDING,
        fallback_model="llama-3.1-70b"
    ),

    # 4. Master Planner
    AgentRole.MASTER_PLANNER: RoleModelConfig(
        role=AgentRole.MASTER_PLANNER,
        role_name="Master Planner",
        model="nvidia/nemotron-3-ultra-550b-a55b",
        responsibility="Produce the complete implementation plan and task decomposition",
        capability=AgentModelCapability.ARCHITECTURE,
        fallback_model="llama-3.1-70b"
    ),

    # 5. Solution Architect
    AgentRole.SOLUTION_ARCHITECT: RoleModelConfig(
        role=AgentRole.SOLUTION_ARCHITECT,
        role_name="Solution Architect",
        model="nvidia/nemotron-3-ultra-550b-a55b",
        responsibility="Architecture, services, APIs, data flow, system boundaries",
        capability=AgentModelCapability.ARCHITECTURE,
        fallback_model="llama-3.1-70b"
    ),

    # 6. UX Researcher
    AgentRole.UX_RESEARCHER: RoleModelConfig(
        role=AgentRole.UX_RESEARCHER,
        role_name="UX Researcher",
        model="nvidia/nemotron-3-super-120b-a12b",
        responsibility="User journeys, information architecture, interaction design",
        capability=AgentModelCapability.UNDERSTANDING,
        fallback_model="llama-3.2-11b"
    ),

    # 7. UI/UX Designer
    AgentRole.UI_UX_DESIGNER: RoleModelConfig(
        role=AgentRole.UI_UX_DESIGNER,
        role_name="UI/UX Designer",
        model="moonshotai/kimi-k3",
        responsibility="Product-specific UI/UX, screens, visual structures, design-to-code reasoning",
        capability=AgentModelCapability.UI,
        fallback_model="llama-3.2-11b"
    ),

    # 8. Visual / Screenshot Analyst
    AgentRole.VISUAL_SCREENSHOT_ANALYST: RoleModelConfig(
        role=AgentRole.VISUAL_SCREENSHOT_ANALYST,
        role_name="Visual / Screenshot Analyst",
        model="meta/muse-glimmer-30b",
        responsibility="Analyze screenshots, existing UI, visual defects, visual references",
        capability=AgentModelCapability.VISION,
        fallback_model="llama-3.2-11b"
    ),

    # 9. Frontend Architect
    AgentRole.FRONTEND_ARCHITECT: RoleModelConfig(
        role=AgentRole.FRONTEND_ARCHITECT,
        role_name="Frontend Architect",
        model="moonshotai/kimi-k3",
        responsibility="Frontend architecture, state, component strategy",
        capability=AgentModelCapability.CODING,
        fallback_model="codestral"
    ),

    # 10. Frontend Engineer
    AgentRole.FRONTEND_ENGINEER: RoleModelConfig(
        role=AgentRole.FRONTEND_ENGINEER,
        role_name="Frontend Engineer",
        model="moonshotai/kimi-k3",
        responsibility="Long-horizon frontend implementation and repository-level coding",
        capability=AgentModelCapability.CODING,
        fallback_model="codestral"
    ),

    # 11. Backend Architect
    AgentRole.BACKEND_ARCHITECT: RoleModelConfig(
        role=AgentRole.BACKEND_ARCHITECT,
        role_name="Backend Architect",
        model="nvidia/nemotron-3-super-120b-a12b",
        responsibility="Services, APIs, business logic, backend architecture",
        capability=AgentModelCapability.ARCHITECTURE,
        fallback_model="llama-3.1-70b"
    ),

    # 12. Backend Engineer
    AgentRole.BACKEND_ENGINEER: RoleModelConfig(
        role=AgentRole.BACKEND_ENGINEER,
        role_name="Backend Engineer",
        model="moonshotai/kimi-k3",
        responsibility="Backend implementation and integration",
        capability=AgentModelCapability.CODING,
        fallback_model="codestral"
    ),

    # 13. Database Engineer
    AgentRole.DATABASE_ENGINEER: RoleModelConfig(
        role=AgentRole.DATABASE_ENGINEER,
        role_name="Database Engineer",
        model="nvidia/nemotron-3-super-120b-a12b",
        responsibility="Schema, migrations, indexes, persistence",
        capability=AgentModelCapability.CODING,
        fallback_model="codestral"
    ),

    # 14. AI Engineer
    AgentRole.AI_ENGINEER: RoleModelConfig(
        role=AgentRole.AI_ENGINEER,
        role_name="AI Engineer",
        model="nvidia/nemotron-3-ultra-550b-a55b",
        responsibility="AI architecture, agent flows, RAG/tool strategy",
        capability=AgentModelCapability.REASONING,
        fallback_model="llama-3.1-70b"
    ),

    # 15. Integration Engineer
    AgentRole.INTEGRATION_ENGINEER: RoleModelConfig(
        role=AgentRole.INTEGRATION_ENGINEER,
        role_name="Integration Engineer",
        model="nvidia/nemotron-3.5-lightning-30b-a3b",
        responsibility="API integrations, repetitive tool/integration work",
        capability=AgentModelCapability.CODING,
        fallback_model="codestral"
    ),

    # 16. Game Engineer
    AgentRole.GAME_ENGINEER: RoleModelConfig(
        role=AgentRole.GAME_ENGINEER,
        role_name="Game Engineer",
        model="moonshotai/kimi-k3",
        responsibility="Game code, gameplay systems, engine logic",
        capability=AgentModelCapability.CODING,
        fallback_model="codestral"
    ),

    # 17. 3D / Graphics Engineer
    AgentRole.GRAPHICS_3D_ENGINEER: RoleModelConfig(
        role=AgentRole.GRAPHICS_3D_ENGINEER,
        role_name="3D / Graphics Engineer",
        model="moonshotai/kimi-k3",
        responsibility="Three.js/WebGL/graphics-heavy implementation",
        capability=AgentModelCapability.CODING,
        fallback_model="codestral"
    ),

    # 18. Debug Engineer
    AgentRole.DEBUG_ENGINEER: RoleModelConfig(
        role=AgentRole.DEBUG_ENGINEER,
        role_name="Debug Engineer",
        model="nvidia/nemotron-3-super-120b-a12b",
        responsibility="Diagnose errors, trace failures, repair code",
        capability=AgentModelCapability.DEBUGGING,
        fallback_model="codestral"
    ),

    # 19. Fast Repair Agent
    AgentRole.FAST_REPAIR_AGENT: RoleModelConfig(
        role=AgentRole.FAST_REPAIR_AGENT,
        role_name="Fast Repair Agent",
        model="nvidia/nemotron-3.5-lightning-30b-a3b",
        responsibility="Small fixes, repetitive corrections, quick retries",
        capability=AgentModelCapability.DEBUGGING,
        fallback_model="codestral"
    ),

    # 20. Test Engineer
    AgentRole.TEST_ENGINEER: RoleModelConfig(
        role=AgentRole.TEST_ENGINEER,
        role_name="Test Engineer",
        model="nvidia/nemotron-3-super-120b-a12b",
        responsibility="Unit/integration/E2E test generation and analysis",
        capability=AgentModelCapability.TESTING,
        fallback_model="codestral"
    ),

    # 21. Browser / GUI Agent
    AgentRole.BROWSER_GUI_AGENT: RoleModelConfig(
        role=AgentRole.BROWSER_GUI_AGENT,
        role_name="Browser / GUI Agent",
        model="nvidia/nemotron-3-nano-omni-30b-a3b-reasoning",
        responsibility="Screenshot/GUI understanding and browser-oriented multimodal work",
        capability=AgentModelCapability.VISION,
        fallback_model="llama-3.2-11b"
    ),

    # 22. Visual QA Engineer
    AgentRole.VISUAL_QA_ENGINEER: RoleModelConfig(
        role=AgentRole.VISUAL_QA_ENGINEER,
        role_name="Visual QA Engineer",
        model="meta/muse-glimmer-30b",
        responsibility="Inspect rendered interfaces and identify visual problems",
        capability=AgentModelCapability.VISION,
        fallback_model="llama-3.2-11b"
    ),

    # 23. Security Engineer
    AgentRole.SECURITY_ENGINEER: RoleModelConfig(
        role=AgentRole.SECURITY_ENGINEER,
        role_name="Security Engineer",
        model="nvidia/nemotron-3-ultra-550b-a55b",
        responsibility="Deep security and architecture review",
        capability=AgentModelCapability.REASONING,
        fallback_model="llama-3.1-70b"
    ),

    # 24. Performance Engineer
    AgentRole.PERFORMANCE_ENGINEER: RoleModelConfig(
        role=AgentRole.PERFORMANCE_ENGINEER,
        role_name="Performance Engineer",
        model="nvidia/nemotron-3-super-120b-a12b",
        responsibility="Performance analysis and optimization",
        capability=AgentModelCapability.REASONING,
        fallback_model="llama-3.1-70b"
    ),

    # 25. Code Reviewer
    AgentRole.CODE_REVIEWER: RoleModelConfig(
        role=AgentRole.CODE_REVIEWER,
        role_name="Code Reviewer",
        model="nvidia/nemotron-3-ultra-550b-a55b",
        responsibility="Independent architecture/code review",
        capability=AgentModelCapability.REVIEW,
        fallback_model="llama-3.1-70b"
    ),

    # 26. Product Critic
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

    # 27. Final Verification Engineer
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
