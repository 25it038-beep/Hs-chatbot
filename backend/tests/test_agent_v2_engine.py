import pytest
import inspect
import tempfile
from pathlib import Path

from app.services.agent_v2.core.contracts import (
    AgentRole,
    AgentState,
    OrchestratorStage,
    ModelHandoffContract,
    ProductSpecification,
    ProductDNA,
    VerificationStatus,
    CheckpointType,
    ToolPermissionLevel
)
from app.services.agent_v2.understanding.sufficiency import RequirementSufficiencyEngine
from app.services.agent_v2.dna.dna_engine import ProductDNAEngine, CapabilityGraph
from app.services.agent_v2.planning.planner import ImplementationPlanner
from app.services.agent_v2.workspace.workspace_v2 import AgentWorkspaceV2, WorkspaceSecurityError
from app.services.agent_v2.execution.tool_orchestrator import AgentToolOrchestrator
from app.services.agent_v2.specialists.specialists import (
    SolutionArchitect,
    UIUXDesigner,
    FrontendEngineer,
    TestEngineer,
    SecurityEngineer,
    IndependentFinalVerifier
)
from app.services.agent_v2.qa.qa_engine import NoveltyTestEngine, AgentCritic
from app.services.agent_v2.orchestrator import AgentOrchestratorV2
from app.services.agent.terminal import TerminalAgent


def test_requirement_sufficiency_engine():
    # 1. Ambiguous prompt triggers adaptive question
    is_suff, classified, q = RequirementSufficiencyEngine.evaluate("Build a social networking application")
    assert is_suff is False
    assert q is not None
    assert q.question_id == "Q-SOCIAL-TYPE"
    assert len(q.options) >= 3

    # 2. Specific prompt is sufficient
    is_suff_fb, classified_fb, q_fb = RequirementSufficiencyEngine.evaluate("Create an interactive football penalty arena game")
    assert is_suff_fb is True
    assert q_fb is None

    # 3. Product specification generation
    spec = RequirementSufficiencyEngine.generate_product_specification(
        "Build a modern football game with penalty shootout",
        {"Q-GAME-GENRE": "2D Canvas Sports Arena"}
    )
    assert spec.domain == "game"
    assert "GoalKeeper" in spec.entities or "Ball" in spec.entities
    assert len(spec.core_workflow) >= 3


def test_product_dna_and_capabilities():
    spec = RequirementSufficiencyEngine.generate_product_specification("Create a hospital patient triage system")
    caps = CapabilityGraph.extract_capabilities(spec)
    assert "database" in caps

    dna, tech_stack = ProductDNAEngine.build_dna(spec, "Create a hospital patient triage system")
    assert dna.identity == spec.product_name
    assert "clinical" in dna.visual_identity.get("visual_direction", "").lower()
    assert tech_stack.is_locked is True


def test_implementation_planner_and_validation():
    spec = RequirementSufficiencyEngine.generate_product_specification("Build an archaeology artifact reconstruction studio")
    dna, tech_stack = ProductDNAEngine.build_dna(spec, "Build an archaeology artifact reconstruction studio")

    plan = ImplementationPlanner.generate_plan(spec, dna, tech_stack)
    assert len(plan.phases) == 12
    assert len(plan.tasks) >= 6

    # Validate plan
    is_valid, errors = ImplementationPlanner.validate_plan(plan)
    assert is_valid is True
    assert len(errors) == 0


def test_workspace_v2_and_checkpoints():
    with tempfile.TemporaryDirectory() as temp_dir:
        ws = AgentWorkspaceV2(Path(temp_dir))

        # 1. Safe write
        w_res = ws.write_file("src/app.js", "const x = 1;\n", task_id="T1")
        assert w_res["success"] is True
        assert w_res["is_new"] is True

        # 2. Edit with diff
        e_res = ws.write_file("src/app.js", "const x = 2;\n", task_id="T2")
        assert e_res["success"] is True
        assert "-const x = 1;" in e_res["diff"]
        assert "+const x = 2;" in e_res["diff"]

        # 3. Path traversal protection
        with pytest.raises(WorkspaceSecurityError):
            ws.write_file("../../secret.txt", "hacked")

        # 4. Checkpoint & Rollback
        cp_id = ws.create_checkpoint("initial_checkpoint", CheckpointType.REQUIREMENTS_COMPLETE)
        ws.write_file("src/extra.js", "delete me later")
        assert "src/extra.js" in ws.list_files()

        # Restore
        ws.restore_checkpoint(cp_id)
        assert "src/extra.js" not in ws.list_files()
        assert "src/app.js" in ws.list_files()


@pytest.mark.asyncio
async def test_tool_orchestrator_permissions():
    with tempfile.TemporaryDirectory() as temp_dir:
        term = TerminalAgent(Path(temp_dir))
        orchestrator = AgentToolOrchestrator(term)

        # 1. READ_ONLY
        assert orchestrator.classify_tool_action("echo 'hello'") == ToolPermissionLevel.READ_ONLY

        # 2. DESTRUCTIVE blocked
        res = await orchestrator.execute_command("rm -rf /")
        assert res["success"] is False
        assert res.get("blocked") is True


@pytest.mark.asyncio
async def test_virtual_company_specialists():
    spec = RequirementSufficiencyEngine.generate_product_specification("Create a football penalty game")

    contract = ModelHandoffContract(
        project_id="test-proj",
        task_id="T1",
        from_role=AgentRole.CEO_PRODUCT_DIRECTOR,
        to_role=AgentRole.SOLUTION_ARCHITECT,
        product_specification=spec.to_dict()
    )

    # 1. Solution Architect
    architect = SolutionArchitect()
    contract = await architect.execute(contract)
    assert contract.architecture is not None

    # 2. UI/UX Designer
    designer = UIUXDesigner()
    contract = await designer.execute(contract)
    assert "palette" in contract.previous_results["ui_design"]

    # 3. Frontend Engineer
    frontend = FrontendEngineer()
    contract = await frontend.execute(contract)
    files = contract.previous_results["generated_files"]
    assert "index.html" in files
    assert "script.js" in files

    # 4. Test Engineer
    test_eng = TestEngineer()
    contract = await test_eng.execute(contract)
    assert "tests/test_app.js" in contract.previous_results["generated_files"]

    # 5. Security Engineer
    sec_eng = SecurityEngineer()
    contract = await sec_eng.execute(contract)
    assert contract.previous_results["security_audit"]["status"] == "PASS"

    # 6. Independent Final Verifier
    verifier = IndependentFinalVerifier()
    contract = await verifier.execute(contract)
    matrix = contract.previous_results["verification_matrix"]
    assert len(matrix) >= 2
    assert all(m["status"] == "PASS" for m in matrix)


def test_novelty_and_critic():
    # 1. Novelty Test passes for genuine game
    genuine_game_files = {
        "index.html": "<canvas id='pitch'></canvas><button id='kickBtn'>Kick</button>",
        "script.js": "requestAnimationFrame(gameLoop); kickBtn.addEventListener('click', shoot);"
    }
    passed, msg = NoveltyTestEngine.evaluate_novelty("game", genuine_game_files, "football game")
    assert passed is True

    # 2. Novelty Test fails if game has SaaS dashboard metrics
    bad_game_files = {
        "index.html": "<div>Total Users: 500</div><div>Total Revenue: $10,000</div>",
        "script.js": "console.log('dashboard');"
    }
    passed_bad, msg_bad = NoveltyTestEngine.evaluate_novelty("game", bad_game_files, "football game")
    assert passed_bad is False

    # 3. Agent Critic
    critique = AgentCritic.critique("football game", genuine_game_files, "game")
    assert critique["critique_passed"] is False  # Missing viewport meta
    genuine_game_files["index.html"] += "<meta name='viewport' content='width=device-width'>"
    critique_ok = AgentCritic.critique("football game", genuine_game_files, "game")
    assert critique_ok["critique_passed"] is True


@pytest.mark.asyncio
async def test_agent_orchestrator_v2_lifecycle():
    with tempfile.TemporaryDirectory() as temp_dir:
        orch = AgentOrchestratorV2(workspace_id="test-orch-ws", base_dir=temp_dir)
        events = []

        async for chunk in orch.run_lifecycle(
            user_request="Build an interactive ancient archaeology reconstruction application",
            chat_id="test-chat",
            user_id="test-user"
        ):
            events.append(chunk)

        event_types = {e.get("type") for e in events}
        assert "stage_update" in event_types
        assert "requirement_snapshot" in event_types
        assert "tech_decision" in event_types
        assert "plan_created" in event_types
        assert "file_written" in event_types
        assert "visual_qa" in event_types
        assert "novelty_audit" in event_types
        assert "requirement_matrix" in event_types
        assert "final_summary" in event_types
        assert orch.state == AgentState.COMPLETED


def test_general_chat_remains_frozen():
    """Verify General Chat router has zero references to agent_v2 (§1)."""
    import app.services.chat as chat_module
    chat_src = inspect.getsource(chat_module)
    assert "agent_v2" not in chat_src
    assert "AgentOrchestratorV2" not in chat_src
    assert "AgentRole" not in chat_src


def test_role_model_registry_and_responsibilities():
    """Verify all 27 specialized company roles, assigned models, and responsibilities."""
    from app.services.agent_v2.models.role_router import AgentRoleRouter, ROLE_MODEL_REGISTRY

    manifest = AgentRoleRouter.get_role_manifest()
    assert len(manifest) >= 27

    # Verify specific roles and assigned models
    assert AgentRoleRouter.get_model_for_role(AgentRole.PRODUCT_DIRECTOR) == "nvidia/nemotron-3-ultra-550b-a55b"
    assert AgentRoleRouter.get_model_for_role(AgentRole.REQUIREMENTS_ANALYST) == "nvidia/nemotron-3-ultra-550b-a55b"
    assert AgentRoleRouter.get_model_for_role(AgentRole.RESEARCH_TECHNICAL_ANALYST) == "nvidia/nemotron-3-super-120b-a12b"
    assert AgentRoleRouter.get_model_for_role(AgentRole.MASTER_PLANNER) == "nvidia/nemotron-3-ultra-550b-a55b"
    assert AgentRoleRouter.get_model_for_role(AgentRole.SOLUTION_ARCHITECT) == "nvidia/nemotron-3-ultra-550b-a55b"
    assert AgentRoleRouter.get_model_for_role(AgentRole.UX_RESEARCHER) == "nvidia/nemotron-3-super-120b-a12b"
    assert AgentRoleRouter.get_model_for_role(AgentRole.UI_UX_DESIGNER) == "moonshotai/kimi-k3"
    assert AgentRoleRouter.get_model_for_role(AgentRole.VISUAL_SCREENSHOT_ANALYST) == "meta/muse-glimmer-30b"
    assert AgentRoleRouter.get_model_for_role(AgentRole.FRONTEND_ARCHITECT) == "moonshotai/kimi-k3"
    assert AgentRoleRouter.get_model_for_role(AgentRole.FRONTEND_ENGINEER) == "moonshotai/kimi-k3"
    assert AgentRoleRouter.get_model_for_role(AgentRole.BACKEND_ARCHITECT) == "nvidia/nemotron-3-super-120b-a12b"
    assert AgentRoleRouter.get_model_for_role(AgentRole.BACKEND_ENGINEER) == "moonshotai/kimi-k3"
    assert AgentRoleRouter.get_model_for_role(AgentRole.DATABASE_ENGINEER) == "nvidia/nemotron-3-super-120b-a12b"
    assert AgentRoleRouter.get_model_for_role(AgentRole.AI_ENGINEER) == "nvidia/nemotron-3-ultra-550b-a55b"
    assert AgentRoleRouter.get_model_for_role(AgentRole.INTEGRATION_ENGINEER) == "nvidia/nemotron-3.5-lightning-30b-a3b"
    assert AgentRoleRouter.get_model_for_role(AgentRole.GAME_ENGINEER) == "moonshotai/kimi-k3"
    assert AgentRoleRouter.get_model_for_role(AgentRole.GRAPHICS_3D_ENGINEER) == "moonshotai/kimi-k3"
    assert AgentRoleRouter.get_model_for_role(AgentRole.DEBUG_ENGINEER) == "nvidia/nemotron-3-super-120b-a12b"
    assert AgentRoleRouter.get_model_for_role(AgentRole.FAST_REPAIR_AGENT) == "nvidia/nemotron-3.5-lightning-30b-a3b"
    assert AgentRoleRouter.get_model_for_role(AgentRole.TEST_ENGINEER) == "nvidia/nemotron-3-super-120b-a12b"
    assert AgentRoleRouter.get_model_for_role(AgentRole.BROWSER_GUI_AGENT) == "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning"
    assert AgentRoleRouter.get_model_for_role(AgentRole.VISUAL_QA_ENGINEER) == "meta/muse-glimmer-30b"
    assert AgentRoleRouter.get_model_for_role(AgentRole.SECURITY_ENGINEER) == "nvidia/nemotron-3-ultra-550b-a55b"
    assert AgentRoleRouter.get_model_for_role(AgentRole.PERFORMANCE_ENGINEER) == "nvidia/nemotron-3-super-120b-a12b"
    assert AgentRoleRouter.get_model_for_role(AgentRole.CODE_REVIEWER) == "nvidia/nemotron-3-ultra-550b-a55b"
    assert AgentRoleRouter.get_model_for_role(AgentRole.PRODUCT_CRITIC) == "nvidia/nemotron-3-super-120b-a12b"
    assert AgentRoleRouter.get_model_for_role(AgentRole.FINAL_VERIFICATION_ENGINEER) == "nvidia/nemotron-3-ultra-550b-a55b"

    # Verify responsibilities
    pd_cfg = AgentRoleRouter.get_role_config(AgentRole.PRODUCT_DIRECTOR)
    assert "Understand the user's product idea" in pd_cfg.responsibility
    tc_cfg = AgentRoleRouter.get_role_config(AgentRole.PRODUCT_CRITIC)
    assert "Check whether the product actually matches" in tc_cfg.responsibility

