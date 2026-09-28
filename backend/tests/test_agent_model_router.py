import pytest
import time
import inspect
from app.services.agent.model_router import (
    AgentModelCapability,
    AgentModelProfile,
    AgentModelRegistry,
    AgentModelRouter
)
from app.services.agent.mode_classifier import (
    ChatMode,
    AgentModeClassifier
)

def test_agent_model_registry_initialization():
    registry = AgentModelRegistry()
    status = registry.get_status()
    assert status["total_models"] >= 5
    assert status["healthy_models"] >= 5

    # Check primary profiles exist
    codestral = registry.get_profile("codestral")
    assert codestral is not None
    assert AgentModelCapability.CODING in codestral.capabilities
    assert AgentModelCapability.DEBUGGING in codestral.capabilities
    assert codestral.priority == 95

    llama70b = registry.get_profile("llama-3.1-70b")
    assert llama70b is not None
    assert AgentModelCapability.REASONING in llama70b.capabilities
    assert AgentModelCapability.ARCHITECTURE in llama70b.capabilities

    llama11b = registry.get_profile("llama-3.2-11b")
    assert llama11b is not None
    assert AgentModelCapability.VISION in llama11b.capabilities
    assert llama11b.supports_vision is True


def test_agent_model_circuit_breaker():
    registry = AgentModelRegistry()
    profile = registry.get_profile("codestral")
    assert profile.healthy is True

    # 1 failure: still healthy
    registry.record_failure("codestral", "Network timeout")
    assert profile.consecutive_failures == 1
    assert profile.healthy is True
    assert profile.is_available() is True

    # 2 failures: still healthy
    registry.record_failure("codestral", "Rate limit 429")
    assert profile.consecutive_failures == 2
    assert profile.healthy is True

    # 3 failures: trips circuit breaker
    registry.record_failure("codestral", "Service unavailable 503")
    assert profile.consecutive_failures == 3
    assert profile.healthy is False
    assert profile.is_available() is False
    assert profile.cooldown_until > time.time()

    # Success records reset
    registry.record_success("codestral", latency_ms=120.5)
    assert profile.healthy is True
    assert profile.consecutive_failures == 0
    assert profile.is_available() is True
    assert profile.avg_latency_ms == 120.5

    # Manual reset health
    registry.record_failure("codestral", "Crash 1")
    registry.record_failure("codestral", "Crash 2")
    registry.record_failure("codestral", "Crash 3")
    assert profile.healthy is False
    registry.reset_health("codestral")
    assert profile.healthy is True
    assert profile.is_available() is True


def test_agent_model_router_capability_selection():
    registry = AgentModelRegistry()
    router = AgentModelRouter(registry)

    # 1. CODING routes to highest-priority coding model (Nemotron-3 Ultra 550B, Kimi K3, or Codestral)
    best_coding = router.route(AgentModelCapability.CODING)
    assert best_coding.model_id in ["nvidia/nemotron-3-ultra-550b-a55b", "moonshotai/kimi-k3", "codestral"]

    # 2. REASONING routes to highest-priority reasoning model (Nemotron-3 Ultra or Llama 3.1 70B)
    best_reasoning = router.route(AgentModelCapability.REASONING)
    assert best_reasoning.model_id in ["nvidia/nemotron-3-ultra-550b-a55b", "llama-3.1-70b"]

    # 3. VISION routes to multimodal model (Kimi K3 or Llama 3.2 11B)
    best_vision = router.route(AgentModelCapability.VISION)
    assert best_vision.model_id in ["moonshotai/kimi-k3", "llama-3.2-11b"]

    # 4. Preferred model overrides if capable and healthy
    pref_coding = router.route(AgentModelCapability.CODING, preferred_model="codestral")
    assert pref_coding.model_id == "codestral"


def test_agent_model_router_fallback_when_unhealthy():
    registry = AgentModelRegistry()
    router = AgentModelRouter(registry)

    # Trip primary coding model circuit breaker
    top_model = router.route(AgentModelCapability.CODING).model_id
    for _ in range(3):
        registry.record_failure(top_model, "Simulated error")
    assert registry.get_profile(top_model).is_available() is False

    # CODING capability should now gracefully fallback to next available model
    fallback_coding = router.route(AgentModelCapability.CODING)
    assert fallback_coding.model_id != top_model
    assert AgentModelCapability.CODING in fallback_coding.capabilities


@pytest.mark.asyncio
async def test_agent_model_router_execution_with_fallback():
    registry = AgentModelRegistry()

    class FakeProvider:
        def __init__(self):
            self.calls = []

        async def generate(self, messages, model, **kwargs):
            self.calls.append(model)
            if model == "codestral":
                raise ConnectionError("Simulated codestral network drop")
            # Fallback model succeeds
            class FakeResp:
                content = "export default function App() { return <div>Success</div> }"
            return FakeResp()

    fake_provider = FakeProvider()
    router = AgentModelRouter(registry, provider=fake_provider)

    content, used_model = await router.execute_task(
        capability=AgentModelCapability.CODING,
        messages=[{"role": "user", "content": "Create test component"}],
        preferred_model="codestral",
        timeout_seconds=5.0
    )

    # Should have attempted preferred codestral, failed, and succeeded with fallback
    assert "codestral" in fake_provider.calls
    assert used_model != "codestral"
    assert "Success" in content

    # Registry should have tracked codestral failure and fallback success
    assert registry.get_profile("codestral").failure_count >= 1
    assert registry.get_profile(used_model).successful_requests >= 1


def test_agent_mode_classifier_general_chat():
    classifier = AgentModeClassifier()

    general_prompts = [
        "What is the capital of France?",
        "Who won the 2022 FIFA World Cup?",
        "Explain how binary search trees operate in O(log n) time.",
        "How do I reverse an array in JavaScript?",
        "What's the weather in Tokyo right now?",
        "Play Tamil songs on YouTube",
        "Can you explain the difference between let, const, and var?",
        "Hello, how are you today?",
        "Explain how to build a good software architecture"
    ]

    for p in general_prompts:
        res = classifier.classify(p)
        assert res.mode == ChatMode.GENERAL_CHAT, f"Failed for prompt: {p}, got: {res.mode} ({res.reason})"
        assert res.confidence >= 0.7


def test_agent_mode_classifier_agent_mode():
    classifier = AgentModeClassifier()

    agent_prompts = [
        "Build a modern football game with penalty shootouts and sound effects",
        "Create an e-commerce website with product catalog, cart, and checkout",
        "Develop a hospital patient management system with admission triage",
        "Create a real estate portal with mortgage calculator and tour booking",
        "Build a React canvas drawing whiteboard web app",
        "Develop a food delivery platform with restaurants and live tracking",
        "Build a personal finance budget tracker with monthly charts",
        "Create a multi-file portfolio website for a senior software engineer",
        "Fix all failing tests in my repository and package the zip archive"
    ]

    for p in agent_prompts:
        res = classifier.classify(p)
        assert res.mode == ChatMode.AGENT, f"Failed for prompt: {p}, got: {res.mode} ({res.reason})"
        assert res.confidence >= 0.8


def test_general_chat_router_isolation():
    """Verify that General Chat router (chat.py) does not import or depend on agent model router."""
    import app.services.chat as chat_module
    chat_src = inspect.getsource(chat_module)
    assert "AgentModelRouter" not in chat_src
    assert "AgentModelRegistry" not in chat_src
    assert "model_router" not in chat_src
