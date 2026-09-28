import pytest
import time
from app.services.agent_v2.core.contracts import (
    AgentRole,
    ProductSpecification,
    ModelHandoffContract
)
from app.services.agent_v2.models.nvidia_router import (
    AgentNvidiaCapability,
    AgentNvidiaModelHealth,
    AgentNvidiaModelProfile,
    AgentNvidiaModelScore,
    AgentNvidiaModelRegistry,
    AgentNvidiaModelRouter
)
from app.services.agent_v2.verification.anti_template import TemplateContaminationDetector
from app.services.agent_v2.verification.uniqueness import ApplicationUniquenessValidator
from app.services.agent_v2.verification.provenance import GenerationProvenanceTracker


def test_anti_template_detector_catches_contamination():
    # 1. Counter boilerplate detection in non-counter app
    contaminated_files = {
        "index.html": "<div id='counterDisplay'>0</div><button id='incBtn'>Click to increment</button>",
        "script.js": "let count = 0; document.getElementById('incBtn').onclick = () => { count++; };"
    }
    report = TemplateContaminationDetector.detect_post_generation(
        files=contaminated_files,
        spec_dict={"product_name": "Football Simulator", "domain": "game"}
    )
    assert report.is_contaminated is True
    assert any("counter" in p.lower() for p in report.matched_patterns)

    # 2. Canned dashboard metrics in game
    saas_dashboard_in_game = {
        "index.html": "<div><h1>Football Manager</h1><span>Monthly Recurring Revenue</span><span>Active Subscriptions $49,000</span></div>",
        "script.js": "console.log('ready');"
    }
    report_saas = TemplateContaminationDetector.detect_post_generation(
        files=saas_dashboard_in_game,
        spec_dict={"product_name": "Pro Football 2026", "domain": "game"}
    )
    assert report_saas.is_contaminated is True

    # 3. Clean authentic game with canvas passes
    clean_game_files = {
        "index.html": "<main><canvas id='pitchCanvas' width='800' height='500'></canvas><div id='scoreBoard'>Ball in play - Player 1</div></main>",
        "script.js": "const canvas = document.getElementById('pitchCanvas'); const player = { x: 50 }; const ball = { x: 100 }; function gameLoop() { requestAnimationFrame(gameLoop); } gameLoop();"
    }
    clean_report = TemplateContaminationDetector.detect_post_generation(
        files=clean_game_files,
        spec_dict={"product_name": "2D Soccer Arena", "domain": "game", "entities": ["Ball", "Player"]}
    )
    assert clean_report.is_contaminated is False


def test_application_uniqueness_validator():
    proj_a_files = {
        "index.html": "<div class='table-container'><table><tr><th>Reservation ID</th><th>Guest</th></tr></table></div>",
        "script.js": "fetch('/api/reservations').then(r => r.json());"
    }
    report_a = ApplicationUniquenessValidator.validate_uniqueness(
        project_id="proj-restaurant",
        files=proj_a_files,
        domain="hospitality",
        entities=["Reservation", "Guest", "Table"],
        workflows=["Book Table", "Cancel", "View Availability"]
    )
    assert report_a.is_unique is True

    # Proj B is a completely different domain (game)
    proj_b_files = {
        "index.html": "<canvas id='gameCanvas'></canvas>",
        "script.js": "const ctx = canvas.getContext('2d'); requestAnimationFrame(loop);"
    }
    report_b = ApplicationUniquenessValidator.validate_uniqueness(
        project_id="proj-space-dodge",
        files=proj_b_files,
        domain="game",
        entities=["Spaceship", "Asteroid", "Score"],
        workflows=["Spawn Asteroid", "Player Move", "Game Over"]
    )
    assert report_b.is_unique is True
    assert report_b.similarity_score < 0.85


def test_generation_provenance_tracker():
    tracker = GenerationProvenanceTracker()
    rec = tracker.record_generation(
        project_id="proj-alpha",
        task_id="TASK-3",
        model="codestral",
        role="Frontend Engineer",
        input_context="Build a custom weather dashboard",
        output_content="<!DOCTYPE html><html><body><h1>Weather</h1></body></html>",
        files_created=["index.html", "script.js"],
        files_modified=[],
        tools_used=["filesystem", "code_generator"]
    )
    assert rec.is_genuine_ai is True
    assert rec.input_context_hash is not None
    assert rec.output_hash is not None

    summary = tracker.get_provenance_summary("proj-alpha")
    assert len(summary) == 1
    assert summary[0]["model"] == "codestral"

    verified, msg = tracker.verify_provenance("proj-alpha", {"index.html": "...", "script.js": "..."})
    assert verified is True


def test_nvidia_router_dynamic_scoring_and_selection():
    registry = AgentNvidiaModelRegistry()
    router = AgentNvidiaModelRouter(registry=registry)

    # 1. Routing for complex architecture
    primary, fallback, meta = router.route_task(
        role=AgentRole.SOLUTION_ARCHITECT,
        required_capabilities=[AgentNvidiaCapability.ARCHITECTURE, AgentNvidiaCapability.REASONING],
        task_complexity=1.5
    )
    assert primary.model_id in ["nvidia/nemotron-3-ultra-550b-a55b", "llama-3.1-70b"]
    assert fallback is not None
    assert meta["candidates_evaluated"] >= 5

    # 2. Routing for fast execution
    fast_primary, _, _ = router.route_task(
        role=AgentRole.FRONTEND_ENGINEER,
        required_capabilities=[AgentNvidiaCapability.FAST_EXECUTION],
        task_complexity=0.8
    )
    assert fast_primary.model_id in ["nvidia/nemotron-3.5-lightning-30b-a3b", "codestral"]

    # 3. Vision requirement gates non-vision models
    vision_primary, _, _ = router.route_task(
        role=AgentRole.VISUAL_QA_ENGINEER,
        required_capabilities=[AgentNvidiaCapability.VISION, AgentNvidiaCapability.UI],
        needs_vision=True
    )
    assert vision_primary.supports_vision is True


def test_nvidia_model_health_and_circuit_breaker():
    health = AgentNvidiaModelHealth(failure_threshold=3, cooldown_period_s=10.0)
    assert health.is_available() is True

    # Record 2 failures -> still available
    health.record_failure("HTTP 500")
    health.record_failure("Timeout")
    assert health.consecutive_failures == 2
    assert health.is_available() is True

    # 3rd failure trips circuit breaker
    health.record_failure("HTTP 503")
    assert health.consecutive_failures == 3
    assert health.healthy is False
    assert health.is_available() is False

    # Simulate success after cooldown
    health.cooldown_until = time.time() - 1
    assert health.is_available() is True
    health.record_success(latency_ms=320.0)
    assert health.healthy is True
    assert health.consecutive_failures == 0
