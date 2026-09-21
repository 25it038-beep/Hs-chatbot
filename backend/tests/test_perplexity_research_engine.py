"""Comprehensive tests for the Perplexity-Level General Chat Search + Answer Engine."""

import pytest
from unittest.mock import AsyncMock, patch

from app.web.citation import build_research_context, format_source_badge, format_sources_markdown
from app.web.conflict import ConflictDetector
from app.web.deduplication import canonicalize_url, deduplicate_sources
from app.web.evidence import EvidenceEngine
from app.web.freshness import check_version_compatibility, evaluate_freshness, extract_version
from app.web.models import EvidenceItem, ResearchRequest, SearchMode, SearchRequest, SourceMetadata, SourceType
from app.web.query_planner import QueryPlanner, clean_subject, resolve_anaphora
from app.web.research import ResearchService
from app.web.search import WebSearchService
from app.web.search_router import determine_search_mode, extract_constraints
from app.web.source_ranker import SourceRanker, classify_source_type, score_source_authority
from app.web.verifier import ClaimVerifier


# ── 1. Search Mode Determination & Zero Unnecessary Searches ──


def test_mode_determination_none():
    non_search_queries = [
        "Write a poem about rain",
        "Hello, how are you today?",
        "Calculate 50 * 12",
        "Translate hello to Spanish",
        "make this email more professional",
    ]
    for q in non_search_queries:
        mode, _ = determine_search_mode(q)
        assert mode == SearchMode.NONE, f"Expected NONE for {q}"


def test_mode_determination_fast():
    fast_queries = [
        "What is the latest Python version?",
        "Current price of Bitcoin today",
        "What happened in tech news today?",
    ]
    for q in fast_queries:
        mode, _ = determine_search_mode(q)
        assert mode == SearchMode.FAST, f"Expected FAST for {q}"


def test_mode_determination_pro():
    pro_queries = [
        "Compare React 19 vs Vue 3.5 major features",
        "Best laptops under ₹80,000 for battery and gaming",
        "RTX 5080 vs RTX 4090 benchmark comparison",
    ]
    for q in pro_queries:
        mode, _ = determine_search_mode(q)
        assert mode == SearchMode.PRO, f"Expected PRO for {q}"


def test_mode_determination_deep():
    deep_queries = [
        "Research the current state of humanoid robotics in 2026, compare major companies and limitations",
        "Deep research into quantum computing fault tolerance",
        "Produce a comprehensive report on solid-state battery technology",
    ]
    for q in deep_queries:
        mode, _ = determine_search_mode(q)
        assert mode == SearchMode.DEEP, f"Expected DEEP for {q}"


# ── 2. Constraint Extraction ──


def test_extract_constraints():
    q = "What are the best laptops under ₹80,000 in India for battery, gaming and development?"
    c = extract_constraints(q)
    assert c["category"] == "laptop"
    assert c["region"] == "IN"
    assert "₹80,000" in c["budget"] or "80,000" in c["budget"]
    assert "battery" in c["criteria"]
    assert "gaming" in c["criteria"]
    assert "development" in c["criteria"]


# ── 3. Query Planning & Decomposition ──


def test_query_planner_anaphora_and_angles():
    planner = QueryPlanner()
    history = [{"role": "user", "content": "NVIDIA Blackwell B200 GPU"}]
    resolved = resolve_anaphora("How much does it cost?", history)
    assert "Blackwell" in resolved or "NVIDIA" in resolved

    queries = planner.plan_queries(
        "NVIDIA Blackwell",
        mode=SearchMode.PRO,
        constraints={"year": "2026"},
    )
    assert len(queries) >= 3
    assert any("official" in q.lower() or "github" in q.lower() for q in queries)
    assert any("2026" in q or "updates" in q.lower() for q in queries)


def test_deep_research_plan_creation():
    planner = QueryPlanner()
    plan = planner.create_research_plan("Humanoid Robotics", constraints={"year": "2026"})
    assert len(plan.subtasks) == 4
    assert len(plan.objectives) >= 3
    assert plan.topic == "Humanoid Robotics"

    # Test gap recovery query planning
    gap_queries = planner.plan_gap_queries(plan.subtasks[2], plan.topic)
    assert len(gap_queries) >= 1
    assert "Humanoid Robotics" in gap_queries[0]


# ── 4. Source Classification & Ranking ──


def test_source_classification():
    assert classify_source_type("https://csrc.nist.gov/publications") == SourceType.GOVERNMENT
    assert classify_source_type("https://arxiv.org/abs/2401.12345") == SourceType.ACADEMIC
    assert classify_source_type("https://docs.python.org/3/whatsnew") == SourceType.OFFICIAL
    assert classify_source_type("https://developer.nvidia.com/nim") == SourceType.OFFICIAL
    assert classify_source_type("https://reuters.com/technology/article") == SourceType.NEWS
    assert classify_source_type("https://reddit.com/r/MachineLearning") == SourceType.COMMUNITY


def test_source_ranking_and_diversity():
    ranker = SourceRanker()
    raw = [
        {"title": f"NVIDIA Official Docs {i}", "url": f"https://developer.nvidia.com/page{i}", "body": "Blackwell specs"}
        for i in range(5)
    ] + [
        {"title": "Reuters Report", "url": "https://reuters.com/tech/blackwell", "body": "NVIDIA Blackwell chips"},
        {"title": "MIT Technology Review", "url": "https://technologyreview.com/chips", "body": "AI hardware analysis"},
    ]
    ranked = ranker.rank_and_select(raw, query="NVIDIA Blackwell specs", max_sources=5, max_per_domain=2)
    assert len(ranked) == 4  # 2 from nvidia + 1 reuters + 1 mit
    nv_count = sum(1 for s in ranked if "developer.nvidia.com" in s.domain)
    assert nv_count == 2  # Capped at 2 per domain!


# ── 5. Conflict Detection & Claim Verification ──


def test_conflict_detection_pricing():
    detector = ConflictDetector()
    sources = [
        SourceMetadata(source_id=1, title="Store A", url="https://store-a.com", domain="store-a.com"),
        SourceMetadata(source_id=2, title="Store B", url="https://store-b.com", domain="store-b.com"),
    ]
    evidence = [
        EvidenceItem(evidence_id="e1", source_id=1, text="The laptop is available for ₹74,990 right now."),
        EvidenceItem(evidence_id="e2", source_id=2, text="Official retail pricing starts at ₹89,990."),
    ]
    conflicts = detector.detect_conflicts(evidence, sources)
    assert len(conflicts) >= 1
    assert "Pricing discrepancies" in conflicts[0]


def test_claim_verifier():
    verifier = ClaimVerifier()
    sources = [
        SourceMetadata(source_id=1, title="Docs", url="https://nvidia.com", domain="nvidia.com"),
        SourceMetadata(source_id=2, title="AnandTech", url="https://anandtech.com", domain="anandtech.com"),
    ]
    evidence = [
        EvidenceItem(evidence_id="e1", source_id=1, text="Blackwell B200 features 208 billion transistors."),
        EvidenceItem(evidence_id="e2", source_id=2, text="NVIDIA confirmed 208 billion transistors on the B200."),
    ]
    claims = ["B200 has 208 billion transistors"]
    verified = verifier.verify_claims(claims, evidence, sources)
    assert len(verified) == 1
    assert verified[0].status == "VERIFIED"
    assert len(verified[0].source_ids) == 2


# ── 6. Citations & Context Generation ──


def test_citation_context_builder():
    sources = [
        SourceMetadata(source_id=1, title="Python 3.14 Release Notes", url="https://docs.python.org/3.14", domain="docs.python.org", source_type=SourceType.OFFICIAL),
    ]
    evidence = [
        EvidenceItem(evidence_id="e1", source_id=1, text="Python 3.14 introduces improved JIT compiler performance."),
    ]
    context = build_research_context(sources, evidence, conflicts=[])
    assert "[1] Python 3.14 Release Notes" in context
    assert "docs.python.org" in context
    assert "DIRECT ANSWER FIRST" in context
    assert "INLINE CITATIONS" in context


# ── 7. End-to-End Pipeline Execution ──


@pytest.mark.asyncio
async def test_web_search_service_pipeline():
    svc = WebSearchService()
    # Mock pool search to avoid network dependencies
    with patch.object(svc._pool, "text", new_callable=AsyncMock) as mock_text, \
         patch.object(svc._reader, "read_sources", new_callable=AsyncMock) as mock_reader:
        mock_text.return_value = [
            {"title": "FastAPI Release Notes", "url": "https://fastapi.tiangolo.com/release-notes/", "body": "FastAPI version 0.115.0 released with Pydantic v2 support."}
        ]
        mock_reader.return_value = {
            1: ["FastAPI 0.115.0 includes significant performance enhancements and bug fixes."]
        }
        bundle = await svc.search("What is the latest FastAPI version?", mode=SearchMode.FAST)
        assert bundle.mode == SearchMode.FAST
        assert len(bundle.sources) >= 1
        assert "[1]" in bundle.structured_context
        assert "fastapi.tiangolo.com" in bundle.sources[0].url


@pytest.mark.asyncio
async def test_deep_research_service_pipeline():
    research_svc = ResearchService()
    with patch.object(research_svc._pool, "text", new_callable=AsyncMock) as mock_text, \
         patch.object(research_svc._reader, "read_sources", new_callable=AsyncMock) as mock_reader:
        mock_text.return_value = [
            {"title": "Humanoid Robotics State of the Art", "url": "https://ieee.org/robotics", "body": "Humanoid robotics in 2026 focuses on electric actuators, tactile sensors, and LLM-based planners."}
        ]
        mock_reader.return_value = {
            1: ["Modern humanoid robots employ full-body compliance and vision-language-action models."]
        }
        bundle = await research_svc.conduct_research("Research the current state of humanoid robotics in 2026")
        assert bundle.mode == SearchMode.DEEP
        assert bundle.research_plan is not None
        assert len(bundle.research_plan.subtasks) == 4
        assert "DEEP RESEARCH REPORT STRUCTURE" in bundle.structured_context
