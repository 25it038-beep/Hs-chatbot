import pytest
from pathlib import Path
from app.services.agent.tech_stack import (
    TargetPlatform,
    ProgrammingLanguage,
    FrameworkType,
    TechStackSnapshot,
    TechnologyDecisionEngine,
    AdaptiveQuizEngine,
    EnvironmentDetector
)
from app.services.agent.qa_engine import (
    VisualQAInspector,
    UserFlowVerifier,
    RequirementTraceabilityEngine,
    HardQualityGate,
    ProjectMemoryManager
)
from app.services.agent.orchestrator import AgentOrchestrator


def test_technology_decision_engine_platforms_and_languages():
    # 1. Rust CLI / System Tool
    rust_stack = TechnologyDecisionEngine.select_and_lock_stack(
        prompt="Create a high performance CLI tool in Rust for file encryption",
        domain_str="developer_tools",
        product_type_str="developer_tool"
    )
    assert rust_stack.primary_language == ProgrammingLanguage.RUST
    assert rust_stack.package_manager == "cargo"
    assert rust_stack.is_locked is True

    # 2. Go API / Backend
    go_stack = TechnologyDecisionEngine.select_and_lock_stack(
        prompt="Build a distributed microservice in Golang with high concurrency",
        domain_str="python_backend",
        product_type_str="python_backend"
    )
    assert go_stack.primary_language == ProgrammingLanguage.GO
    assert go_stack.package_manager == "go mod"
    assert go_stack.is_locked is True

    # 3. Python FastAPI
    py_stack = TechnologyDecisionEngine.select_and_lock_stack(
        prompt="Create a FastAPI REST API with SQLite database backend",
        domain_str="python_backend",
        product_type_str="python_backend"
    )
    assert py_stack.primary_language == ProgrammingLanguage.PYTHON
    assert py_stack.framework == FrameworkType.FASTAPI
    assert py_stack.package_manager == "pip"

    # 4. Canvas Web Game
    game_stack = TechnologyDecisionEngine.select_and_lock_stack(
        prompt="Build a 2D football shootout arcade game",
        domain_str="game",
        product_type_str="game"
    )
    assert game_stack.platform == TargetPlatform.WEB_BROWSER
    assert game_stack.primary_language == ProgrammingLanguage.JAVASCRIPT
    assert game_stack.framework == FrameworkType.CANVAS_2D_WEBGL

    # 5. Mobile Cross-Platform
    mobile_stack = TechnologyDecisionEngine.select_and_lock_stack(
        prompt="Create a mobile app in Flutter for personal fitness workout tracking",
        domain_str="universal_dynamic",
        product_type_str="universal_app"
    )
    assert mobile_stack.platform == TargetPlatform.MOBILE_CROSS_PLATFORM
    assert mobile_stack.primary_language == ProgrammingLanguage.DART
    assert mobile_stack.framework == FrameworkType.FLUTTER


def test_environment_detector_non_blocking():
    toolchains = EnvironmentDetector.get_installed_toolchains()
    assert isinstance(toolchains, dict)
    assert "python" in toolchains or "python3" in toolchains
    assert "node" in toolchains


def test_adaptive_quiz_engine():
    # E-commerce ambiguity
    quiz_shop = AdaptiveQuizEngine.evaluate_and_generate_quiz("Build a shopping app to buy things")
    assert len(quiz_shop) >= 1
    assert any("shopping experience" in q.question.lower() for q in quiz_shop)
    assert len(quiz_shop[0].options) >= 2
    assert quiz_shop[0].default_option != ""

    # Platform ambiguity
    quiz_app = AdaptiveQuizEngine.evaluate_and_generate_quiz("Create an app for managing books")
    assert any("platform" in q.question.lower() for q in quiz_app)


def test_visual_qa_inspector():
    sample_files = {
        "index.html": """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Aura Modern Storefront</title>
</head>
<body class="bg-slate-950 text-white">
  <header class="p-4 flex justify-between items-center">
    <h1>Aura Storefront</h1>
    <button class="bg-emerald-500 px-4 py-2 rounded-xl" aria-label="Cart">Cart (0)</button>
  </header>
  <main class="grid grid-cols-1 md:grid-cols-3 gap-4 p-6">
    <div class="product-card">Product Item</div>
  </main>
</body>
</html>""",
        "styles.css": "body { margin: 0; }"
    }

    report = VisualQAInspector.inspect(sample_files, "Aura Modern Storefront", "ecommerce")
    assert report.viewport_responsive is True
    assert report.semantic_hierarchy_valid is True
    assert report.first_impression_score > 0.8
    assert report.overflow_risk_detected is False
    assert report.accessibility_checks_passed is True


def test_user_flow_verifier():
    # E-Commerce
    ecom_files = {
        "index.html": "<div id='productsGrid'></div><div id='cartModal'></div>",
        "script.js": "let products = []; let cart = []; function checkout() {}"
    }
    report = UserFlowVerifier.verify_flow(ecom_files, "ecommerce", ["Browse catalog", "Add to cart", "Checkout"])
    assert report.flow_status == "VERIFIED"
    assert report.state_transitions_verified is True
    assert len(report.steps_verified) >= 3

    # Game
    game_files = {
        "index.html": "<canvas id='gameCanvas'></canvas>",
        "script.js": "function gameLoop() { requestAnimationFrame(gameLoop); } window.addEventListener('keydown', () => {}); let score = 0;"
    }
    game_report = UserFlowVerifier.verify_flow(game_files, "game", ["Aim shot", "Score goal"])
    assert game_report.flow_status == "VERIFIED"
    assert game_report.state_transitions_verified is True


def test_requirement_traceability_and_hard_quality_gate(tmp_path):
    workflows = [
        "Search catalog with responsive filtering",
        "Add selected items into interactive cart",
        "Submit simulated payment checkout"
    ]
    files = {
        "index.html": "<!DOCTYPE html><meta name=\"viewport\" content=\"width=device-width\" />",
        "styles.css": "body { color: white; }",
        "script.js": "localStorage.setItem('cart', '[]');",
        "tests/test_app.js": "console.log('tests passed');"
    }

    matrix = RequirementTraceabilityEngine.generate_matrix(workflows, workflows, files, "ecommerce")
    assert len(matrix) == 3
    assert matrix[0].status == "VERIFIED"
    assert "REQ-001" == matrix[0].requirement_id

    # Test Gate Pass
    passed, blockers = HardQualityGate.evaluate(
        prompt_understood=True,
        tech_locked=True,
        files_created=4,
        flow_verified=True,
        tests_passed=True
    )
    assert passed is True
    assert len(blockers) == 0

    # Test Gate Fail (blocking errors or unverified)
    failed, fail_blockers = HardQualityGate.evaluate(
        prompt_understood=True,
        tech_locked=False,
        files_created=1,
        flow_verified=False,
        tests_passed=False
    )
    assert failed is False
    assert len(fail_blockers) >= 3

    # Project Memory Persistence
    mem_file = ProjectMemoryManager.save_project_memory(
        workspace_dir=tmp_path,
        project_id="test-proj-101",
        tech_stack={"primary_language": "typescript"},
        snapshot={"product_name": "Test Store"},
        matrix=[m.to_dict() for m in matrix]
    )
    assert mem_file.exists()
    assert "Test Store" in mem_file.read_text(encoding="utf-8")


@pytest.mark.asyncio
async def test_orchestrator_generate_plan_with_tech_stack():
    orchestrator = AgentOrchestrator(workspace_id="test-plan-ws")
    plan = await orchestrator.generate_plan("Build an online course learning platform in TypeScript")

    task_ids = list(plan.tasks.keys())
    assert "TASK-1" in task_ids
    assert "TASK-2" in task_ids
    assert "TASK-3" in task_ids
    assert "TASK-4" in task_ids
    assert "TASK-5" in task_ids
    assert "TASK-QA" in task_ids
    assert "TASK-MATRIX" in task_ids
    assert "TASK-ZIP" in task_ids
    assert "TASK-FINAL" in task_ids

    # Verify task 3 contains product and technology specifics
    task3_desc = plan.tasks["TASK-3"].description
    assert "TYPESCRIPT" in task3_desc or "Synthesize" in plan.tasks["TASK-3"].title
