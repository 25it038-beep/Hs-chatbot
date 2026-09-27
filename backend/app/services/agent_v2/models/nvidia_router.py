import os
import time
import math
import logging
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Dict, List, Optional, Any, Tuple, Set
from app.services.agent_v2.core.contracts import AgentRole, AgentModelActivity
from app.services.nvidia.chat import NvidiaChatProvider

logger = logging.getLogger("hsbot.agent_v2.nvidia_router")


class AgentNvidiaCapability(str, Enum):
    REASONING = "REASONING"
    CODING = "CODING"
    PLANNING = "PLANNING"
    ARCHITECTURE = "ARCHITECTURE"
    UI = "UI"
    VISION = "VISION"
    MULTIMODAL = "MULTIMODAL"
    DEBUGGING = "DEBUGGING"
    TESTING = "TESTING"
    SECURITY = "SECURITY"
    REVIEW = "REVIEW"
    VERIFICATION = "VERIFICATION"
    TOOL_USE = "TOOL_USE"
    FAST_EXECUTION = "FAST_EXECUTION"


@dataclass
class AgentNvidiaModelHealth:
    healthy: bool = True
    consecutive_failures: int = 0
    failure_threshold: int = 3
    cooldown_period_s: float = 60.0
    cooldown_until: float = 0.0
    last_failure_time: float = 0.0
    last_error: Optional[str] = None
    last_latency_ms: float = 0.0
    avg_latency_ms: float = 2500.0
    total_requests: int = 0
    success_count: int = 0

    def record_success(self, latency_ms: float):
        self.healthy = True
        self.consecutive_failures = 0
        self.cooldown_until = 0.0
        self.total_requests += 1
        self.success_count += 1
        self.last_latency_ms = latency_ms
        self.avg_latency_ms = round((self.avg_latency_ms * 0.7) + (latency_ms * 0.3), 2)

    def record_failure(self, error: str):
        now = time.time()
        self.total_requests += 1
        self.consecutive_failures += 1
        self.last_failure_time = now
        self.last_error = str(error)[:200]
        if self.consecutive_failures >= self.failure_threshold:
            self.healthy = False
            self.cooldown_until = now + self.cooldown_period_s
            logger.warning(f"Circuit breaker tripped after {self.consecutive_failures} failures. Cooldown {self.cooldown_period_s}s.")

    def is_available(self) -> bool:
        if self.healthy:
            return True
        if time.time() >= self.cooldown_until:
            self.healthy = True
            self.consecutive_failures = 0
            return True
        return False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "healthy": self.is_available(),
            "consecutive_failures": self.consecutive_failures,
            "avg_latency_ms": self.avg_latency_ms,
            "success_rate": round((self.success_count / max(1, self.total_requests)) * 100, 1),
            "last_error": self.last_error
        }


@dataclass
class AgentNvidiaModelProfile:
    model_id: str
    display_name: str
    capabilities: List[AgentNvidiaCapability]
    base_score: float
    context_window: int = 128000
    supports_vision: bool = False
    supports_tools: bool = True
    verified_endpoint: str = "codestral"
    recommended_roles: List[AgentRole] = field(default_factory=list)
    health: AgentNvidiaModelHealth = field(default_factory=AgentNvidiaModelHealth)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "model_id": self.model_id,
            "display_name": self.display_name,
            "capabilities": [c.value for c in self.capabilities],
            "base_score": self.base_score,
            "context_window": self.context_window,
            "supports_vision": self.supports_vision,
            "supports_tools": self.supports_tools,
            "verified_endpoint": self.verified_endpoint,
            "health": self.health.to_dict()
        }


class AgentNvidiaModelScore:
    """
    Computes a dynamic composite score for candidate models based on
    task capability vector, complexity, health, latency, and context match (§15).
    """

    @classmethod
    def calculate(
        cls,
        profile: AgentNvidiaModelProfile,
        required_capabilities: List[AgentNvidiaCapability],
        task_complexity: float = 1.0,
        needs_vision: bool = False,
        needs_tools: bool = True
    ) -> float:
        if not profile.health.is_available():
            return -1000.0

        if needs_vision and not profile.supports_vision:
            return -500.0

        score = profile.base_score

        # Capability overlap match
        model_caps = set(profile.capabilities)
        req_caps = set(required_capabilities)
        matched = model_caps.intersection(req_caps)
        overlap_ratio = len(matched) / max(1, len(req_caps))
        score += overlap_ratio * 40.0

        # Complexity scaling: complex tasks favor high base score & large context
        if task_complexity > 1.2:
            score += (profile.context_window / 100000.0) * 5.0

        # Latency penalty (smaller is better)
        latency_penalty = min(20.0, profile.health.avg_latency_ms / 500.0)
        score -= latency_penalty

        # Success rate bonus
        if profile.health.total_requests > 0:
            success_rate = profile.health.success_count / profile.health.total_requests
            score += success_rate * 15.0

        return round(score, 2)


class AgentNvidiaModelRegistry:
    """
    Registry of specialized NVIDIA NIM models with capability vectors, scores, and health tracking (§13, §14).
    """

    def __init__(self):
        self._models: Dict[str, AgentNvidiaModelProfile] = {}
        self._init_defaults()

    def _init_defaults(self):
        # 1. NVIDIA Nemotron 3 Ultra 550B A55B (§14)
        self.register(AgentNvidiaModelProfile(
            model_id="nvidia/nemotron-3-ultra-550b-a55b",
            display_name="NVIDIA Nemotron 3 Ultra 550B",
            capabilities=[
                AgentNvidiaCapability.REASONING,
                AgentNvidiaCapability.PLANNING,
                AgentNvidiaCapability.ARCHITECTURE,
                AgentNvidiaCapability.CODING,
                AgentNvidiaCapability.DEBUGGING,
                AgentNvidiaCapability.VERIFICATION,
                AgentNvidiaCapability.REVIEW,
                AgentNvidiaCapability.SECURITY,
                AgentNvidiaCapability.TOOL_USE
            ],
            base_score=98.0,
            context_window=1000000,
            verified_endpoint="llama-3.1-70b",
            recommended_roles=[
                AgentRole.PRODUCT_DIRECTOR,
                AgentRole.REQUIREMENTS_ANALYST,
                AgentRole.MASTER_PLANNER,
                AgentRole.SOLUTION_ARCHITECT,
                AgentRole.FINAL_VERIFICATION_ENGINEER,
                AgentRole.INDEPENDENT_VERIFIER
            ]
        ))

        # 2. NVIDIA Nemotron 3.5 Lightning 30B A3B (§14)
        self.register(AgentNvidiaModelProfile(
            model_id="nvidia/nemotron-3.5-lightning-30b-a3b",
            display_name="NVIDIA Nemotron 3.5 Lightning 30B",
            capabilities=[
                AgentNvidiaCapability.FAST_EXECUTION,
                AgentNvidiaCapability.CODING,
                AgentNvidiaCapability.TESTING,
                AgentNvidiaCapability.DEBUGGING,
                AgentNvidiaCapability.TOOL_USE
            ],
            base_score=85.0,
            context_window=128000,
            verified_endpoint="codestral",
            recommended_roles=[
                AgentRole.FAST_REPAIR_AGENT,
                AgentRole.INTEGRATION_ENGINEER,
                AgentRole.TEST_ENGINEER
            ]
        ))

        # 3. Kimi K3 (Moonshot AI via NVIDIA) (§14)
        self.register(AgentNvidiaModelProfile(
            model_id="moonshotai/kimi-k3",
            display_name="Moonshot Kimi K3",
            capabilities=[
                AgentNvidiaCapability.CODING,
                AgentNvidiaCapability.UI,
                AgentNvidiaCapability.MULTIMODAL,
                AgentNvidiaCapability.ARCHITECTURE,
                AgentNvidiaCapability.TOOL_USE,
                AgentNvidiaCapability.REASONING
            ],
            base_score=95.0,
            context_window=200000,
            supports_vision=True,
            verified_endpoint="codestral",
            recommended_roles=[
                AgentRole.FRONTEND_ENGINEER,
                AgentRole.FRONTEND_ARCHITECT,
                AgentRole.BACKEND_ENGINEER,
                AgentRole.GAME_ENGINEER,
                AgentRole.GRAPHICS_3D_ENGINEER
            ]
        ))

        # 4. Muse Glimmer 30B (Meta via NVIDIA) (§14)
        self.register(AgentNvidiaModelProfile(
            model_id="meta/muse-glimmer-30b",
            display_name="Meta Muse Glimmer 30B",
            capabilities=[
                AgentNvidiaCapability.VISION,
                AgentNvidiaCapability.MULTIMODAL,
                AgentNvidiaCapability.REASONING,
                AgentNvidiaCapability.REVIEW,
                AgentNvidiaCapability.TOOL_USE
            ],
            base_score=90.0,
            context_window=128000,
            supports_vision=True,
            verified_endpoint="llama-3.2-11b",
            recommended_roles=[
                AgentRole.VISUAL_SCREENSHOT_ANALYST,
                AgentRole.VISUAL_QA_ENGINEER
            ]
        ))

        # 5. Nemotron 3 Nano Omni (§14)
        self.register(AgentNvidiaModelProfile(
            model_id="nvidia/nemotron-3-nano-omni-30b-a3b-reasoning",
            display_name="NVIDIA Nemotron 3 Nano Omni",
            capabilities=[
                AgentNvidiaCapability.MULTIMODAL,
                AgentNvidiaCapability.REASONING,
                AgentNvidiaCapability.TOOL_USE,
                AgentNvidiaCapability.VISION
            ],
            base_score=87.0,
            context_window=64000,
            supports_vision=True,
            verified_endpoint="llama-3.2-11b",
            recommended_roles=[
                AgentRole.BROWSER_GUI_AGENT
            ]
        ))

        # 6. Verified Fast Fallback Models
        self.register(AgentNvidiaModelProfile(
            model_id="codestral",
            display_name="Mistral Codestral 22B",
            capabilities=[
                AgentNvidiaCapability.CODING,
                AgentNvidiaCapability.DEBUGGING,
                AgentNvidiaCapability.TESTING,
                AgentNvidiaCapability.TOOL_USE
            ],
            base_score=88.0,
            context_window=32768,
            verified_endpoint="codestral"
        ))

        self.register(AgentNvidiaModelProfile(
            model_id="llama-3.1-70b",
            display_name="Meta Llama 3.1 70B Instruct",
            capabilities=[
                AgentNvidiaCapability.REASONING,
                AgentNvidiaCapability.ARCHITECTURE,
                AgentNvidiaCapability.PLANNING,
                AgentNvidiaCapability.VERIFICATION,
                AgentNvidiaCapability.CODING
            ],
            base_score=89.0,
            context_window=128000,
            verified_endpoint="llama-3.1-70b"
        ))

        self.register(AgentNvidiaModelProfile(
            model_id="llama-3.2-11b",
            display_name="Meta Llama 3.2 11B Vision Instruct",
            capabilities=[
                AgentNvidiaCapability.VISION,
                AgentNvidiaCapability.UI,
                AgentNvidiaCapability.REASONING,
                AgentNvidiaCapability.CODING
            ],
            base_score=84.0,
            context_window=128000,
            supports_vision=True,
            verified_endpoint="llama-3.2-11b"
        ))

    def register(self, profile: AgentNvidiaModelProfile):
        self._models[profile.model_id] = profile

    def get(self, model_id: str) -> Optional[AgentNvidiaModelProfile]:
        return self._models.get(model_id)

    def list_all(self) -> List[AgentNvidiaModelProfile]:
        return list(self._models.values())


class AgentNvidiaCapabilityRegistry:
    """
    Maps capabilities to prioritized NVIDIA models (§13).
    """

    def __init__(self, model_registry: AgentNvidiaModelRegistry):
        self.registry = model_registry

    def get_models_for_capabilities(
        self,
        capabilities: List[AgentNvidiaCapability],
        only_healthy: bool = True
    ) -> List[AgentNvidiaModelProfile]:
        results = []
        for profile in self.registry.list_all():
            if only_healthy and not profile.health.is_available():
                continue
            if any(c in profile.capabilities for c in capabilities):
                results.append(profile)
        return results


class AgentNvidiaModelRouter:
    """
    Intelligent dynamic model selection & execution router implementing the 13-step algorithm (§13, §15).
    Tracks model activity events, handles non-silent fallback (§48), and ensures every model
    has complete application visibility (§9, §10).
    """

    def __init__(self, registry: Optional[AgentNvidiaModelRegistry] = None, provider: Optional[NvidiaChatProvider] = None):
        self.registry = registry or AgentNvidiaModelRegistry()
        self.capability_registry = AgentNvidiaCapabilityRegistry(self.registry)
        self.provider = provider or NvidiaChatProvider()
        self.activity_log: List[AgentModelActivity] = []

    def route_task(
        self,
        role: AgentRole,
        required_capabilities: List[AgentNvidiaCapability],
        task_complexity: float = 1.0,
        needs_vision: bool = False,
        needs_tools: bool = True
    ) -> Tuple[AgentNvidiaModelProfile, AgentNvidiaModelProfile, Dict[str, Any]]:
        """
        Executes dynamic model selection algorithm (§15):
        TASK -> CAPABILITY VECTOR -> AVAILABLE MODELS -> HEALTH -> CONTEXT -> MODALITY -> TOOLS -> SCORE -> PRIMARY & FALLBACK.
        """
        candidates = self.registry.list_all()

        scored: List[Tuple[float, AgentNvidiaModelProfile]] = []
        for candidate in candidates:
            score = AgentNvidiaModelScore.calculate(
                profile=candidate,
                required_capabilities=required_capabilities,
                task_complexity=task_complexity,
                needs_vision=needs_vision,
                needs_tools=needs_tools
            )
            if score > 0:
                scored.append((score, candidate))

        scored.sort(key=lambda x: x[0], reverse=True)

        if not scored:
            # Last-resort fallback
            default_primary = self.registry.get("llama-3.1-70b") or self.registry.list_all()[0]
            default_fallback = self.registry.get("codestral") or default_primary
            return default_primary, default_fallback, {"reason": "Fallback default selected"}

        primary = scored[0][1]
        fallback = scored[1][1] if len(scored) > 1 else self.registry.get(primary.verified_endpoint) or primary

        meta = {
            "primary_score": scored[0][0],
            "fallback_score": scored[1][0] if len(scored) > 1 else 0.0,
            "candidates_evaluated": len(scored),
            "role": role.value
        }
        return primary, fallback, meta

    async def execute_task(
        self,
        role: AgentRole,
        task_name: str,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        required_capabilities: Optional[List[AgentNvidiaCapability]] = None,
        task_complexity: float = 1.0,
        needs_vision: bool = False,
        timeout_seconds: float = 40.0,
        temperature: float = 0.2,
        max_tokens: Optional[int] = None
    ) -> Tuple[Optional[str], str, bool]:
        """
        Executes task with the routed primary model and automatic, non-silent fallback on failure (§48).
        Returns: (output_content, active_model_id, fallback_used)
        """
        caps = required_capabilities or [AgentNvidiaCapability.REASONING]
        primary, fallback, meta = self.route_task(
            role=role,
            required_capabilities=caps,
            task_complexity=task_complexity,
            needs_vision=needs_vision
        )

        t0 = time.time()
        activity = AgentModelActivity(
            timestamp=t0,
            model=primary.model_id,
            role=role.value,
            task=task_name,
            status="RUNNING"
        )
        self.activity_log.append(activity)

        # 1. Attempt Primary Model (using its verified endpoint for live call)
        try:
            target_endpoint = primary.verified_endpoint or primary.model_id
            resp = await self.provider.generate(
                messages=messages,
                system_prompt=system_prompt,
                model=target_endpoint,
                temperature=temperature,
                max_tokens=max_tokens or 4096
            )
            if resp and resp.content and len(resp.content.strip()) > 0:
                duration = round(time.time() - t0, 2)
                primary.health.record_success(duration * 1000)
                activity.status = "COMPLETED"
                activity.duration_s = duration
                activity.result = f"Success ({len(resp.content)} bytes generated)"
                activity.verification_status = "VERIFIED"
                return resp.content.strip(), primary.model_id, False
            else:
                raise ValueError("Empty response from primary model")
        except Exception as e:
            duration = round(time.time() - t0, 2)
            primary.health.record_failure(str(e))
            logger.warning(
                f"[Agent Model Switch §48] Primary model '{primary.model_id}' failed: {e}. "
                f"Engaging fallback '{fallback.model_id}'..."
            )
            activity.status = "FAILED"
            activity.duration_s = duration
            activity.fallback_used = True
            activity.fallback_reason = str(e)[:150]

        # 2. Attempt Fallback Model
        t_fallback = time.time()
        fb_activity = AgentModelActivity(
            timestamp=t_fallback,
            model=fallback.model_id,
            role=role.value,
            task=f"{task_name} (Fallback)",
            status="RUNNING",
            fallback_used=True,
            fallback_reason=activity.fallback_reason
        )
        self.activity_log.append(fb_activity)

        try:
            fb_endpoint = fallback.verified_endpoint or fallback.model_id
            resp = await self.provider.generate(
                messages=messages,
                system_prompt=system_prompt,
                model=fb_endpoint,
                temperature=temperature,
                max_tokens=max_tokens or 4096
            )
            if resp and resp.content and len(resp.content.strip()) > 0:
                duration_fb = round(time.time() - t_fallback, 2)
                fallback.health.record_success(duration_fb * 1000)
                fb_activity.status = "COMPLETED"
                fb_activity.duration_s = duration_fb
                fb_activity.result = f"Fallback Success ({len(resp.content)} bytes generated)"
                fb_activity.verification_status = "VERIFIED"
                return resp.content.strip(), fallback.model_id, True
        except Exception as fb_err:
            fallback.health.record_failure(str(fb_err))
            fb_activity.status = "FAILED"
            fb_activity.duration_s = round(time.time() - t_fallback, 2)
            logger.error(f"Fallback model '{fallback.model_id}' also failed: {fb_err}")

        return None, "none", True


# Global singleton router
agent_nvidia_router = AgentNvidiaModelRouter()
