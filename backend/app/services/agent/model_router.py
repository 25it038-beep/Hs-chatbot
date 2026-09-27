import asyncio
import time
import logging
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Dict, List, Optional, Any, Tuple
from app.services.nvidia.chat import NvidiaChatProvider

logger = logging.getLogger("hsbot.agent.model_router")

class AgentModelCapability(str, Enum):
    UNDERSTANDING = "UNDERSTANDING"
    REQUIREMENT_ANALYSIS = "REQUIREMENT_ANALYSIS"
    REASONING = "REASONING"
    ARCHITECTURE = "ARCHITECTURE"
    CODING = "CODING"
    UI = "UI"
    VISION = "VISION"
    DEBUGGING = "DEBUGGING"
    TESTING = "TESTING"
    REVIEW = "REVIEW"
    VERIFICATION = "VERIFICATION"

@dataclass
class AgentModelProfile:
    model_id: str
    display_name: str
    capabilities: List[AgentModelCapability]
    priority: int = 50
    provider: str = "nvidia"
    max_tokens: int = 8192
    default_temperature: float = 0.2
    supports_streaming: bool = True
    supports_json: bool = True
    supports_vision: bool = False
    healthy: bool = True
    failure_count: int = 0
    consecutive_failures: int = 0
    last_failure_time: float = 0.0
    cooldown_until: float = 0.0
    avg_latency_ms: float = 0.0
    total_requests: int = 0
    successful_requests: int = 0
    last_error: Optional[str] = None

    def is_available(self, current_time: Optional[float] = None) -> bool:
        now = current_time or time.time()
        if not self.healthy:
            if now >= self.cooldown_until:
                # Half-open state: cooldown has elapsed, allowed a trial request
                return True
            return False
        return True

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["capabilities"] = [c.value if isinstance(c, Enum) else str(c) for c in self.capabilities]
        d["is_available"] = self.is_available()
        return d


class AgentModelRegistry:
    """
    Registry for Agent Mode AI models.
    Strictly isolated to Agent Mode and NVIDIA NIM infrastructure.
    Maintains model profiles, capability mappings, and health/circuit-breaker states.
    """
    CIRCUIT_BREAKER_THRESHOLD = 3  # consecutive failures before tripping
    COOLDOWN_PERIOD_S = 60.0       # cooldown duration after trip

    def __init__(self):
        self._profiles: Dict[str, AgentModelProfile] = {}
        self._init_default_nvidia_models()

    def _init_default_nvidia_models(self):
        # 1. Codestral: Specialized coding, testing, and debugging champion
        self.register(AgentModelProfile(
            model_id="codestral",
            display_name="Mistral Codestral 22B",
            capabilities=[
                AgentModelCapability.CODING,
                AgentModelCapability.DEBUGGING,
                AgentModelCapability.TESTING,
                AgentModelCapability.REVIEW,
            ],
            priority=100,
            default_temperature=0.15,
            max_tokens=8192
        ))

        # 2. Llama 3.1 70B: Elite reasoning, architecture design, and verification
        self.register(AgentModelProfile(
            model_id="llama-3.1-70b",
            display_name="Meta Llama 3.1 70B Instruct",
            capabilities=[
                AgentModelCapability.REASONING,
                AgentModelCapability.ARCHITECTURE,
                AgentModelCapability.REVIEW,
                AgentModelCapability.VERIFICATION,
                AgentModelCapability.CODING,
                AgentModelCapability.DEBUGGING,
            ],
            priority=90,
            default_temperature=0.2,
            max_tokens=8192
        ))

        # 3. Llama 3.2 11B Vision: Fast understanding, UI design, and visual inspection
        self.register(AgentModelProfile(
            model_id="llama-3.2-11b",
            display_name="Meta Llama 3.2 11B Vision Instruct",
            capabilities=[
                AgentModelCapability.UNDERSTANDING,
                AgentModelCapability.REQUIREMENT_ANALYSIS,
                AgentModelCapability.UI,
                AgentModelCapability.VISION,
                AgentModelCapability.CODING,
                AgentModelCapability.REASONING,
            ],
            priority=80,
            supports_vision=True,
            default_temperature=0.2,
            max_tokens=8192
        ))

        # 4. GLM 5.2: Multi-turn reasoning & coding backup
        self.register(AgentModelProfile(
            model_id="glm-5.2",
            display_name="Zhipu GLM 5.2",
            capabilities=[
                AgentModelCapability.REASONING,
                AgentModelCapability.CODING,
                AgentModelCapability.ARCHITECTURE,
            ],
            priority=70,
            default_temperature=0.2,
            max_tokens=8192
        ))

        # 5. Mistral Large: General fallback
        self.register(AgentModelProfile(
            model_id="mistral-large",
            display_name="Mistral Large 2",
            capabilities=[
                AgentModelCapability.REASONING,
                AgentModelCapability.CODING,
                AgentModelCapability.REVIEW,
            ],
            priority=60,
            default_temperature=0.2,
            max_tokens=8192
        ))

    def register(self, profile: AgentModelProfile):
        self._profiles[profile.model_id] = profile

    def get_profile(self, model_id: str) -> Optional[AgentModelProfile]:
        return self._profiles.get(model_id)

    def list_profiles(self) -> List[AgentModelProfile]:
        return list(self._profiles.values())

    def get_models_for_capability(
        self,
        capability: AgentModelCapability,
        only_healthy: bool = True
    ) -> List[AgentModelProfile]:
        now = time.time()
        matches = [
            p for p in self._profiles.values()
            if capability in p.capabilities and (not only_healthy or p.is_available(now))
        ]
        # Sort descending by priority
        matches.sort(key=lambda p: p.priority, reverse=True)
        return matches

    def record_success(self, model_id: str, latency_ms: float):
        profile = self._profiles.get(model_id)
        if not profile:
            return
        profile.healthy = True
        profile.consecutive_failures = 0
        profile.cooldown_until = 0.0
        profile.last_error = None
        profile.total_requests += 1
        profile.successful_requests += 1
        # Rolling average latency
        if profile.avg_latency_ms == 0.0:
            profile.avg_latency_ms = latency_ms
        else:
            profile.avg_latency_ms = round((profile.avg_latency_ms * 0.8) + (latency_ms * 0.2), 2)

    def record_failure(self, model_id: str, error_msg: str):
        profile = self._profiles.get(model_id)
        if not profile:
            return
        now = time.time()
        profile.total_requests += 1
        profile.failure_count += 1
        profile.consecutive_failures += 1
        profile.last_failure_time = now
        profile.last_error = str(error_msg)[:300]

        if profile.consecutive_failures >= self.CIRCUIT_BREAKER_THRESHOLD:
            profile.healthy = False
            profile.cooldown_until = now + self.COOLDOWN_PERIOD_S
            logger.warning(
                f"Circuit breaker tripped for Agent model '{model_id}' "
                f"after {profile.consecutive_failures} failures. Cooldown for {self.COOLDOWN_PERIOD_S}s."
            )

    def reset_health(self, model_id: str):
        profile = self._profiles.get(model_id)
        if profile:
            profile.healthy = True
            profile.consecutive_failures = 0
            profile.cooldown_until = 0.0
            profile.last_error = None

    def get_status(self) -> Dict[str, Any]:
        return {
            "total_models": len(self._profiles),
            "healthy_models": sum(1 for p in self._profiles.values() if p.healthy),
            "models": {m_id: p.to_dict() for m_id, p in self._profiles.items()}
        }


class AgentModelRouter:
    """
    Intelligent Model Router for Agent Mode tasks.
    Routes tasks to the most suitable NVIDIA NIM model according to required capability,
    respecting circuit breakers and falling back gracefully without impacting General Chat.
    """

    def __init__(self, registry: Optional[AgentModelRegistry] = None, provider: Optional[NvidiaChatProvider] = None):
        self.registry = registry or AgentModelRegistry()
        self.provider = provider or NvidiaChatProvider()

    def route(
        self,
        capability: AgentModelCapability,
        preferred_model: Optional[str] = None
    ) -> AgentModelProfile:
        """
        Determines the optimal model profile for a given capability.
        Prefers the requested model if available and capable.
        Otherwise falls back through prioritized healthy candidates.
        """
        now = time.time()

        # 1. Check preferred model if requested
        if preferred_model:
            prof = self.registry.get_profile(preferred_model)
            if prof and prof.is_available(now) and capability in prof.capabilities:
                return prof

        # 2. Get healthy models supporting capability
        candidates = self.registry.get_models_for_capability(capability, only_healthy=True)
        if candidates:
            return candidates[0]

        # 3. If no healthy models matched, check any model for this capability
        all_capability_models = self.registry.get_models_for_capability(capability, only_healthy=False)
        if all_capability_models:
            # Pick the one with the earliest cooldown expiration
            all_capability_models.sort(key=lambda p: p.cooldown_until)
            chosen = all_capability_models[0]
            logger.info(f"All models for capability '{capability.value}' in cooldown; using earliest '{chosen.model_id}'")
            return chosen

        # 4. Ultimate fallback: default to llama-3.2-11b or codestral
        default_prof = self.registry.get_profile("llama-3.2-11b") or self.registry.get_profile("codestral")
        if default_prof:
            return default_prof

        # 5. Last resort fallback profile
        return AgentModelProfile(
            model_id="llama-3.2-11b",
            display_name="Fallback Model",
            capabilities=list(AgentModelCapability),
            priority=1
        )

    async def execute_task(
        self,
        capability: AgentModelCapability,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        preferred_model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        json_mode: bool = False,
        timeout_seconds: float = 60.0
    ) -> Tuple[Optional[str], str]:
        """
        Executes an agent task using capability routing with automatic fallback.
        Returns: (output_content, used_model_id)
        """
        tried_models = set()
        # Candidate chain: routed model first, followed by other capable models
        primary_profile = self.route(capability, preferred_model=preferred_model)
        chain = [primary_profile]
        other_candidates = self.registry.get_models_for_capability(capability, only_healthy=True)
        for c in other_candidates:
            if c.model_id != primary_profile.model_id:
                chain.append(c)

        for profile in chain:
            if profile.model_id in tried_models:
                continue
            tried_models.add(profile.model_id)

            t0 = time.time()
            try:
                temp = temperature if temperature is not None else profile.default_temperature
                tokens = max_tokens or profile.max_tokens

                resp = await asyncio.wait_for(
                    self.provider.generate(
                        messages=messages,
                        system_prompt=system_prompt,
                        model=profile.model_id,
                        temperature=temp,
                        max_tokens=tokens,
                        json_mode=json_mode
                    ),
                    timeout=timeout_seconds
                )
                latency = round((time.time() - t0) * 1000, 2)

                if resp and resp.content and len(resp.content.strip()) > 0:
                    self.registry.record_success(profile.model_id, latency)
                    logger.info(f"Agent model '{profile.model_id}' succeeded for {capability.value} in {latency}ms")
                    return resp.content.strip(), profile.model_id

                # Empty response treated as error
                self.registry.record_failure(profile.model_id, "Empty response from provider")
            except Exception as e:
                latency = round((time.time() - t0) * 1000, 2)
                self.registry.record_failure(profile.model_id, str(e))
                logger.warning(
                    f"Agent model '{profile.model_id}' failed for {capability.value} "
                    f"after {latency}ms: {e}. Trying fallback..."
                )

        return None, "none"


# Global singleton router for Agent Mode
agent_model_registry = AgentModelRegistry()
agent_model_router = AgentModelRouter(agent_model_registry)
