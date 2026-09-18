import os
import shutil
import tempfile
import pytest
from pathlib import Path
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.services.workspace.workspace import WorkspaceManager, WorkspaceSecurityError
from app.services.agent.terminal import TerminalAgent, redact_secrets
from app.services.artifacts.engine import UniversalArtifactEngine, ArtifactSecretScanner, SecretLeakDetectedError
from app.utils.security import create_access_token

@pytest.mark.asyncio
async def test_workspace_manager_security_and_operations():
    with tempfile.TemporaryDirectory() as temp_dir:
        ws = WorkspaceManager(workspace_id="test-ws", base_dir=temp_dir)

        # 1. Create and write file
        w_res = ws.write_file("src/main.py", "print('hello world')\nline2\nline3\n")
        assert w_res["success"] is True

        # 2. Read file
        r_res = ws.read_file("src/main.py")
        assert r_res["success"] is True
        assert "hello world" in r_res["content"]
        assert r_res["total_lines"] == 3

        # 3. Sliced read
        slice_res = ws.read_file("src/main.py", start_line=2, end_line=3)
        assert slice_res["success"] is True
        assert "line2" in slice_res["content"]

        # 4. Surgical edit with unified diff
        e_res = ws.edit_file("src/main.py", "print('hello world')", "print('hello universe')")
        assert e_res["success"] is True
        assert "-print('hello world')" in e_res["diff"]
        assert "+print('hello universe')" in e_res["diff"]

        # 5. Search code
        s_res = ws.search_code("universe")
        assert s_res["success"] is True
        assert len(s_res["matches"]) >= 1

        # 6. Path traversal security checks
        with pytest.raises(WorkspaceSecurityError):
            ws.read_file("../../secret.txt")

        with pytest.raises(WorkspaceSecurityError):
            ws.write_file("../outside.txt", "hacked")

@pytest.mark.asyncio
async def test_terminal_agent_security_and_redaction():
    with tempfile.TemporaryDirectory() as temp_dir:
        term = TerminalAgent(Path(temp_dir))

        # 1. Allowed echo command
        res = await term.execute("echo 'test execution'")
        assert res["success"] is True
        assert "test execution" in res["stdout"]

        # 2. Blocked dangerous command
        res_blocked = await term.execute("rm -rf /")
        assert res_blocked["success"] is False
        assert res_blocked.get("blocked") is True

        # 3. Disallowed binary
        res_disallowed = await term.execute("unauthorized_binary --flag")
        assert res_disallowed["success"] is False
        assert res_disallowed.get("blocked") is True

        # 4. Secret redaction verification
        sample_output = "Connected with key nvapi-abc123XYZ4567890123456789 and sk-12345678901234567890123456"
        redacted = redact_secrets(sample_output)
        assert "nvapi-" not in redacted
        assert "sk-" not in redacted
        assert "[REDACTED_SECRET]" in redacted

@pytest.mark.asyncio
async def test_universal_artifact_engine_and_secret_scanner():
    with tempfile.TemporaryDirectory() as temp_dir:
        art_engine = UniversalArtifactEngine(artifact_storage_dir=temp_dir)
        ws_path = Path(temp_dir) / "project_files"
        ws_path.mkdir()
        (ws_path / "index.js").write_text("console.log('App ready');")
        (ws_path / "README.md").write_text("# Project Docs\nClean project.")

        # 1. Clean ZIP packaging
        zip_res = art_engine.create_zip_project(
            workspace_dir=ws_path,
            zip_filename="test_archive.zip"
        )
        assert zip_res["success"] is True
        assert zip_res["artifact"]["validation_status"] == "passed"
        assert Path(zip_res["artifact"]["storage_path"]).exists()

        # 2. Leaked secret inside project file blocks delivery
        (ws_path / "config.env").write_text("NVIDIA_API_KEY=nvapi-secretkey1234567890123456789")
        with pytest.raises(SecretLeakDetectedError):
            art_engine.create_zip_project(
                workspace_dir=ws_path,
                zip_filename="leaked_archive.zip"
            )

@pytest.mark.asyncio
async def test_agent_api_endpoints():
    transport = ASGITransport(app=app)
    token = create_access_token({"sub": "test-agent-user"})
    headers = {"Authorization": f"Bearer {token}"}

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Agent state
        state_resp = await client.get("/api/agent/state", headers=headers)
        assert state_resp.status_code == 200
        data = state_resp.json()
        assert "status" in data
        assert "autonomy_mode" in data

        # 2. Plan task
        plan_resp = await client.post("/api/agent/plan", json={"prompt": "Build API tests and zip project"}, headers=headers)
        assert plan_resp.status_code == 200
        pdata = plan_resp.json()
        assert pdata["success"] is True
        assert len(pdata["plan"]["tasks"]) >= 4

        # 3. Workspace file write & read
        w_resp = await client.post(
            "/api/agent/workspace/file",
            json={"path": "api/test.txt", "content": "agent workspace file test"},
            headers=headers
        )
        assert w_resp.status_code == 200

        r_resp = await client.get(
            "/api/agent/workspace/file?path=api/test.txt",
            headers=headers
        )
        assert r_resp.status_code == 200
        assert "agent workspace file test" in r_resp.json()["content"]

        # 4. Workspace tree
        tree_resp = await client.get("/api/agent/workspace/tree", headers=headers)
        assert tree_resp.status_code == 200
        assert "tree" in tree_resp.json()

        # 5. List artifacts
        art_resp = await client.get("/api/agent/artifacts", headers=headers)
        assert art_resp.status_code == 200
        assert "artifacts" in art_resp.json()


@pytest.mark.asyncio
async def test_modular_adapters_and_editing():
    from app.services.artifacts.adapters import PPTXAdapter, XLSXAdapter, CSVAdapter
    from app.services.artifacts.registry import PersistentArtifactRegistry
    from app.services.artifacts.editor import ArtifactEditorService
    from app.services.artifacts.preview import ArtifactPreviewService

    with tempfile.TemporaryDirectory() as temp_dir:
        reg = PersistentArtifactRegistry(storage_dir=temp_dir)
        editor = ArtifactEditorService(registry=reg)
        preview_svc = ArtifactPreviewService(registry=reg)

        # 1. Test PPTX generation and preview
        pptx_adapter = PPTXAdapter()
        content = {
            "title": "Quarterly Business Review",
            "slides": [
                {"title": "Overview", "bullets": ["Revenue up 25%", "User growth +40%"]},
                {"title": "Technical Architecture", "bullets": ["FastAPI microservices", "Qdrant vector search"]}
            ]
        }
        dest_pptx = Path(temp_dir) / "presentation.pptx"
        val = pptx_adapter.generate(content, dest_pptx)
        assert val.passed is True
        assert dest_pptx.exists()

        # Register in registry
        art_meta = reg.register_artifact(
            filename="presentation.pptx",
            file_path=dest_pptx,
            artifact_type="presentation",
            mime_type="application/vnd.openxmlformats-officedocument.presentationml.presentation"
        )
        assert art_meta.version == 1

        # Check preview
        prev = preview_svc.get_preview(art_meta.artifact_id)
        assert prev["type"] == "pptx_preview"
        assert prev["total_slides"] == 2
        assert prev["slides"][0]["title"] == "Overview"

        # 2. Test targeted incremental edit on PPTX (e.g. modify slide 2)
        success, updated_art, msg = await editor.edit_artifact(
            artifact_id=art_meta.artifact_id,
            instruction="Update slide 2 bullets with Autonomous Agent Platform",
            target="slide 2"
        )
        assert success is True
        assert updated_art.version == 2
        assert len(updated_art.versions) == 2

        # 3. Test version restore
        restored_art = reg.restore_version(art_meta.artifact_id, 1)
        assert restored_art is not None
        assert restored_art.version == 3
        assert "Restored from version 1" in restored_art.versions[-1].change_description

        # 4. Test XLSX generation and preview
        xlsx_adapter = XLSXAdapter()
        xlsx_content = {
            "sheets": [
                {"name": "Summary", "data": [["Metric", "Value"], ["ARR", "$5.2M"], ["Retention", "94%"]]},
                {"name": "Details", "data": [["ID", "Name"], [1, "Enterprise"], [2, "Growth"]]}
            ]
        }
        dest_xlsx = Path(temp_dir) / "financials.xlsx"
        val_xlsx = xlsx_adapter.generate(xlsx_content, dest_xlsx)
        assert val_xlsx.passed is True
        assert dest_xlsx.exists()

        art_xlsx = reg.register_artifact(
            filename="financials.xlsx",
            file_path=dest_xlsx,
            artifact_type="spreadsheet",
            mime_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        prev_xlsx = preview_svc.get_preview(art_xlsx.artifact_id)
        assert prev_xlsx["type"] == "xlsx_preview"
        assert len(prev_xlsx["sheets"]) == 2
        assert prev_xlsx["sheets"][0]["sheet_name"] == "Summary"

