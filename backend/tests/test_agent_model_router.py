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
    assert codestral.priority == 100

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

    # 1. CODING should route to codestral (highest priority: 100)
    best_coding = router.route(AgentModelCapability.CODING)
    assert best_coding.model_id == "codestral"

    # 2. REASONING should route to llama-3.1-70b (priority: 90)
    best_reasoning = router.route(AgentModelCapability.REASONING)
    assert best_reasoning.model_id == "llama-3.1-70b"

    # 3. VISION should route to llama-3.2-11b
    best_vision = router.route(AgentModelCapability.VISION)
    assert best_vision.model_id == "llama-3.2-11b"

    # 4. Preferred model overrides if capable and healthy
    pref_coding = router.route(AgentModelCapability.CODING, preferred_model="llama-3.1-70b")
    assert pref_coding.model_id == "llama-3.1-70b"


def test_agent_model_router_fallback_when_unhealthy():
    registry = AgentModelRegistry()
    router = AgentModelRouter(registry)

    # Trip codestral circuit breaker
    for _ in range(3):
        registry.record_failure("codestral", "Simulated error")
    assert registry.get_profile("codestral").is_available() is False

    # CODING capability should now gracefully fallback to llama-3.1-70b
    fallback_coding = router.route(AgentModelCapability.CODING)
    assert fallback_coding.model_id == "llama-3.1-70b"

    # Trip llama-3.1-70b too
    for _ in range(3):
        registry.record_failure("llama-3.1-70b", "Simulated error")

    # Next fallback should be llama-3.2-11b or glm-5.2
    next_fallback = router.route(AgentModelCapability.CODING)
    assert next_fallback.model_id in ["llama-3.2-11b", "glm-5.2"]


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
        timeout_seconds=5.0
    )

    # Should have attempted codestral, failed, and succeeded with fallback (llama-3.1-70b)
    assert "codestral" in fake_provider.calls
    assert "llama-3.1-70b" in fake_provider.calls
    assert used_model == "llama-3.1-70b"
    assert "Success" in content

    # Registry should have tracked codestral failure and llama-3.1-70b success
    assert registry.get_profile("codestral").failure_count >= 1
    assert registry.get_profile("llama-3.1-70b").successful_requests >= 1


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
