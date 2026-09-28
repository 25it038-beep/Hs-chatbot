import os
import tempfile
import zipfile
import pytest
from app.services.chat_context import (
    GeneralChatContextEngineV2,
    general_chat_context_engine,
    file_adapter_registry,
    chunk_ranker,
    StreamWatchdog,
    compute_context_budget,
    estimate_tokens,
    FileCapability,
    FileProcessingState,
    conversation_context_store,
)
from app.services.chat_context.file_adapters import (
    TextAdapter,
    CodeAdapter,
    SpreadsheetAdapter,
    ArchiveAdapter,
    MediaAdapter,
    FallbackAdapter,
)


@pytest.mark.asyncio
async def test_budget_computation():
    budget = compute_context_budget(model_id="llama-3.1-70b", output_budget=4096, safety_margin=0.15)
    assert budget.max_context == 131072
    assert budget.safety_margin == 0.15
    safe_max = int(131072 * 0.85)
    assert budget.usable_budget == safe_max - 4096
    assert budget.remaining_tokens == budget.usable_budget


@pytest.mark.asyncio
async def test_text_adapter_markdown_sections():
    with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False, encoding="utf-8") as f:
        f.write("# Introduction\nThis is the intro section.\n\n# Architecture\nDetails of the architecture.\n")
        temp_path = f.name

    try:
        adapter = TextAdapter()
        res = await adapter.extract(temp_path, "docs.md", "file_md_1")
        assert res.state == FileProcessingState.READY
        assert res.capability == FileCapability.TEXT
        assert len(res.chunks) == 2
        assert "Introduction" in res.chunks[0].section
        assert "Architecture" in res.chunks[1].section
        assert any("docs.md" in c for c in res.citations)
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


@pytest.mark.asyncio
async def test_code_adapter_line_ranges():
    code_content = (
        "def calculate_total(a, b):\n"
        "    return a + b\n\n"
        "class OrderService:\n"
        "    def process(self):\n"
        "        pass\n"
    )
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8") as f:
        f.write(code_content)
        temp_path = f.name

    try:
        adapter = CodeAdapter()
        res = await adapter.extract(temp_path, "service.py", "file_py_1")
        assert res.state == FileProcessingState.READY
        assert res.capability == FileCapability.CODE
        assert len(res.chunks) >= 1
        first_chunk = res.chunks[0]
        assert "Lines 1-" in first_chunk.location
        assert "calculate_total" in res.metadata.get("definitions", [])
        assert "OrderService" in res.metadata.get("definitions", [])
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


@pytest.mark.asyncio
async def test_spreadsheet_adapter_csv_stats():
    csv_content = (
        "Item,Price,Quantity\n"
        "Widget,10.50,4\n"
        "Gadget,25.00,2\n"
        "Doohickey,5.00,10\n"
    )
    with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False, encoding="utf-8") as f:
        f.write(csv_content)
        temp_path = f.name

    try:
        adapter = SpreadsheetAdapter()
        res = await adapter.extract(temp_path, "sales.csv", "file_csv_1")
        assert res.state == FileProcessingState.READY
        assert res.capability == FileCapability.SPREADSHEET
        assert len(res.chunks) >= 1
        assert "sales.csv" in res.summary
        assert "Price" in res.metadata.get("columns", [])
        assert any("rows 1-3 of sales.csv" in cit.lower() for cit in res.citations)
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


@pytest.mark.asyncio
async def test_archive_adapter_inspection():
    with tempfile.NamedTemporaryFile("wb", suffix=".zip", delete=False) as f:
        temp_zip = f.name

    try:
        with zipfile.ZipFile(temp_zip, "w") as zf:
            zf.writestr("README.md", "# Project Archive\nWelcome to the archive.")
            zf.writestr("src/main.py", "print('hello world')")

        adapter = ArchiveAdapter()
        res = await adapter.extract(temp_zip, "project.zip", "file_zip_1")
        assert res.state == FileProcessingState.READY
        assert res.capability == FileCapability.ARCHIVE
        assert len(res.chunks) >= 1
        assert "project.zip" in res.summary
        assert any("README.md" in c.content for c in res.chunks)
    finally:
        if os.path.exists(temp_zip):
            os.remove(temp_zip)


@pytest.mark.asyncio
async def test_media_adapter_partial_support():
    with tempfile.NamedTemporaryFile("wb", suffix=".mp4", delete=False) as f:
        f.write(b"\x00\x00\x00\x1cftypisom\x00\x00\x02\x00isomiso2mp41")
        temp_mp4 = f.name

    try:
        adapter = MediaAdapter()
        res = await adapter.extract(temp_mp4, "demo.mp4", "file_mp4_1")
        assert res.state == FileProcessingState.PARTIALLY_SUPPORTED
        assert res.is_partially_supported is True
        assert res.capability == FileCapability.VIDEO
        assert "Partially Supported" in res.chunks[0].content
    finally:
        if os.path.exists(temp_mp4):
            os.remove(temp_mp4)


@pytest.mark.asyncio
async def test_fallback_adapter_binary_honesty():
    with tempfile.NamedTemporaryFile("wb", suffix=".bin", delete=False) as f:
        f.write(b"\x7f\x45\x4c\x46\x02\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00")
        temp_bin = f.name

    try:
        adapter = FallbackAdapter()
        res = await adapter.extract(temp_bin, "compiled.bin", "file_bin_1")
        assert res.state == FileProcessingState.PARTIALLY_SUPPORTED
        assert res.is_partially_supported is True
        assert "compiled.bin" in res.summary
        assert "binary or proprietary" in res.chunks[0].content.lower()
    finally:
        if os.path.exists(temp_bin):
            os.remove(temp_bin)


def test_lexical_chunk_ranker_boosts():
    from app.services.chat_context.contracts import DocumentChunk

    chunk1 = DocumentChunk(
        chunk_id="c1",
        file_id="f1",
        source="annual_report.pdf",
        location="Page 1 of annual_report.pdf",
        page=1,
        content="General overview of corporate governance."
    )
    chunk2 = DocumentChunk(
        chunk_id="c2",
        file_id="f1",
        source="annual_report.pdf",
        location="Page 4 of annual_report.pdf",
        page=4,
        content="Fiscal revenue grew 35% in Q4 with record net income."
    )

    query = "What was the revenue on page 4 of annual_report.pdf?"
    selected = chunk_ranker.select_top_chunks([chunk1, chunk2], query=query, token_budget=1000)
    assert len(selected) > 0
    # chunk2 should score highest because of page 4, filename, and keyword match
    scored = chunk_ranker.score_chunks([chunk1, chunk2], query=query)
    assert scored[0][0].chunk_id == "c2"


def test_conversation_context_store_compaction():
    messages = [
        {"role": "user", "content": "I require a PostgreSQL 16 database with Redis caching and distributed worker queues."},
        {"role": "assistant", "content": "Agreed, we will configure PostgreSQL 16, Redis 7, and Celery workers."},
        {"role": "user", "content": "Please make sure to enable mutual TLS and enforce SSL encryption on all connections."},
        {"role": "assistant", "content": "Mutual TLS and SSL encryption have been enabled across all endpoints."},
        {"role": "user", "content": "What port is PostgreSQL running on and what is the maximum connection limit?"},
        {"role": "assistant", "content": "PostgreSQL is running on port 5432 with max_connections set to 200."},
        {"role": "user", "content": "We need automated backups to S3 every 6 hours with 30 day retention policy."},
        {"role": "assistant", "content": "Automated S3 snapshot cron has been scheduled every 6 hours with a 30-day lifecycle retention policy."},
        {"role": "user", "content": "Can you check the current health status and verify if all services are responsive?"}
    ]

    # Compact with tight budget (e.g. 50 tokens)
    compacted = conversation_context_store.compact_history(messages, history_budget=50, preserve_recent_turns=1)
    assert len(compacted) < len(messages)
    # Verify that memory summary is present
    has_summary = any("[CONVERSATION MEMORY SUMMARY]" in m["content"] for m in compacted)
    assert has_summary


def test_stream_watchdog():
    watchdog = StreamWatchdog(request_id="req_test_1", ttft_timeout_s=1.0, inactivity_timeout_s=1.0)
    watchdog.record_chunk("Hello")
    watchdog.record_chunk(" world!")
    assert watchdog.get_partial_content() == "Hello world!"
    metrics = watchdog.get_metrics()
    assert metrics["chunks_received"] == 2
    assert metrics["total_chars"] == 12
    watchdog.complete()
    assert watchdog.is_completed is True


@pytest.mark.asyncio
async def test_end_to_end_context_engine():
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8") as f:
        f.write("Server specification: 8 CPUs, 32GB RAM, Ubuntu 24.04.")
        temp_file = f.name

    try:
        attached = [{
            "file_id": "file_123",
            "filename": "server_specs.txt",
            "file_path": temp_file,
            "mime_type": "text/plain"
        }]

        messages, meta = await general_chat_context_engine.prepare_context(
            model_id="llama-3.1-70b",
            user_message="What are the RAM specifications in server_specs.txt?",
            conversation_history=[
                {"role": "user", "content": "Hi there."},
                {"role": "assistant", "content": "Hello! How can I assist you today?"}
            ],
            attached_files=attached
        )

        assert len(messages) >= 3
        # System prompt present
        assert messages[0]["role"] == "system"
        # User message has attached file context
        user_msg = messages[-1]
        assert user_msg["role"] == "user"
        assert "server_specs.txt" in user_msg["content"]
        assert "32GB RAM" in user_msg["content"]

        # Observability and citations present
        assert meta["chunks_included"] >= 1
        assert len(meta["citations"]) >= 1
        assert meta["budget"]["usable_budget"] > 0
    finally:
        if os.path.exists(temp_file):
            os.remove(temp_file)
