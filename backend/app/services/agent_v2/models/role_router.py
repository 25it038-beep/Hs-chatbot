import time
import logging
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

# Explicit mapping of Agent Roles to Primary Capabilities (§4, §5)
ROLE_CAPABILITY_MAP: Dict[AgentRole, AgentModelCapability] = {
    AgentRole.CEO_PRODUCT_DIRECTOR: AgentModelCapability.REASONING,
    AgentRole.PRODUCT_ANALYST: AgentModelCapability.REQUIREMENT_ANALYSIS,
    AgentRole.SOLUTION_ARCHITECT: AgentModelCapability.ARCHITECTURE,
    AgentRole.UX_RESEARCHER: AgentModelCapability.UNDERSTANDING,
    AgentRole.UI_UX_DESIGNER: AgentModelCapability.UI,
    AgentRole.FRONTEND_ENGINEER: AgentModelCapability.CODING,
    AgentRole.BACKEND_ENGINEER: AgentModelCapability.CODING,
    AgentRole.DATABASE_ENGINEER: AgentModelCapability.CODING,
    AgentRole.AI_ENGINEER: AgentModelCapability.REASONING,
    AgentRole.INTEGRATION_ENGINEER: AgentModelCapability.CODING,
    AgentRole.GAME_ENGINEER: AgentModelCapability.CODING,
    AgentRole.GRAPHICS_3D_ENGINEER: AgentModelCapability.CODING,
    AgentRole.SECURITY_ENGINEER: AgentModelCapability.REASONING,
    AgentRole.TEST_ENGINEER: AgentModelCapability.TESTING,
    AgentRole.VISUAL_QA_ENGINEER: AgentModelCapability.VISION,
    AgentRole.DEBUG_ENGINEER: AgentModelCapability.DEBUGGING,
    AgentRole.CODE_REVIEWER: AgentModelCapability.REVIEW,
    AgentRole.INDEPENDENT_VERIFIER: AgentModelCapability.VERIFICATION,
    AgentRole.AGENT_CRITIC: AgentModelCapability.REASONING
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

    def route_role(self, role: AgentRole, preferred_model: Optional[str] = None) -> AgentModelProfile:
        capability = ROLE_CAPABILITY_MAP.get(role, AgentModelCapability.REASONING)
        return self.router.route(capability, preferred_model=preferred_model)

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
        capability = ROLE_CAPABILITY_MAP.get(role, AgentModelCapability.REASONING)
        return await self.router.execute_task(
            capability=capability,
            messages=messages,
            system_prompt=system_prompt,
            preferred_model=preferred_model,
            temperature=temperature,
            max_tokens=max_tokens,
            json_mode=json_mode,
            timeout_seconds=timeout_seconds
        )


# Global singleton role router
agent_role_router = AgentRoleRouter()
