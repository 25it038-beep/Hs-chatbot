import pytest
from app.web.models import SearchMode
from app.web.search_router import (
    CurrentnessClassification,
    classify_currentness,
    determine_search_mode,
)
from app.services.retrieval.router import classify as retrieval_classify, is_non_search_intent
from app.services.nvidia.router import ai_router
from app.services.websearch import WebSearchService


def test_currentness_classification_always_current_by_default():
    # Explicit / changing queries -> CURRENT_REQUIRED
    assert classify_currentness("who is the president of india") == CurrentnessClassification.CURRENT_REQUIRED
    assert classify_currentness('"who is the president of india"') == CurrentnessClassification.CURRENT_REQUIRED
    assert classify_currentness("who is the chief minister of tamilnadu") == CurrentnessClassification.CURRENT_REQUIRED
    assert classify_currentness("latest AI models 2026") == CurrentnessClassification.CURRENT_REQUIRED
    assert classify_currentness("what is the current price of rtx 5090") == CurrentnessClassification.CURRENT_REQUIRED

    # General factual / technical queries -> CURRENT_PREFERRED (search is performed)
    assert classify_currentness("what is python") == CurrentnessClassification.CURRENT_PREFERRED
    assert classify_currentness("what is fastapi") == CurrentnessClassification.CURRENT_PREFERRED
    assert classify_currentness("how does react work") == CurrentnessClassification.CURRENT_PREFERRED
    assert classify_currentness("what is the capital of india") == CurrentnessClassification.CURRENT_PREFERRED
    assert classify_currentness("which phone should I buy") == CurrentnessClassification.CURRENT_PREFERRED


def test_currentness_classification_exceptions_skip_search():
    # Pure exceptions -> CURRENT_NOT_NEEDED
    assert classify_currentness("write a poem") == CurrentnessClassification.CURRENT_NOT_NEEDED
    assert classify_currentness("compose a haiku about autumn") == CurrentnessClassification.CURRENT_NOT_NEEDED
    assert classify_currentness("make this email more professional") == CurrentnessClassification.CURRENT_NOT_NEEDED
    assert classify_currentness("rewrite this paragraph") == CurrentnessClassification.CURRENT_NOT_NEEDED
    assert classify_currentness("translate this to tamil") == CurrentnessClassification.CURRENT_NOT_NEEDED
    assert classify_currentness("hello") == CurrentnessClassification.CURRENT_NOT_NEEDED
    assert classify_currentness("how are you doing") == CurrentnessClassification.CURRENT_NOT_NEEDED
    assert classify_currentness("calculate 25 * 40") == CurrentnessClassification.CURRENT_NOT_NEEDED


def test_determine_search_mode():
    # Factual / Technical queries get FAST mode
    mode, _ = determine_search_mode("what is python")
    assert mode == SearchMode.FAST

    mode, _ = determine_search_mode("who is the president of india")
    assert mode == SearchMode.FAST

    mode, _ = determine_search_mode("who is the chief minister of tamilnadu")
    assert mode == SearchMode.FAST

    # Comparative queries get PRO mode
    mode, _ = determine_search_mode("compare react vs vue for web development in 2026")
    assert mode == SearchMode.PRO

    # Deep research gets DEEP mode
    mode, _ = determine_search_mode("deep research into quantum computing hardware in 2026")
    assert mode == SearchMode.DEEP

    # Exceptions get NONE
    mode, _ = determine_search_mode("write a poem")
    assert mode == SearchMode.NONE

    mode, _ = determine_search_mode("make this email more professional")
    assert mode == SearchMode.NONE

    mode, _ = determine_search_mode("translate this to tamil")
    assert mode == SearchMode.NONE


def test_retrieval_router_always_current_alignment():
    # Exceptions
    assert is_non_search_intent("write a poem") is True
    assert is_non_search_intent("make this email more professional") is True
    assert is_non_search_intent("hello") is True

    # Factual queries are NOT bypassed
    assert is_non_search_intent("who is the president of india") is False
    assert is_non_search_intent("what is python") is False
    assert is_non_search_intent("what is fastapi") is False
    assert is_non_search_intent("how does react work") is False

    # Needs search is True for factual queries
    res = retrieval_classify("what is python")
    assert res["needs_search"] is True
    assert "web" in res["types"]

    res = retrieval_classify("who is the president of india")
    assert res["needs_search"] is True


def test_ai_router_requires_web_for_knowledge():
    res = ai_router.classify("who is the president of india")
    assert res.get("requires_web") is True

    res = ai_router.classify("what is python")
    assert res.get("requires_web") is True

    res = ai_router.classify("how does react work")
    assert res.get("requires_web") is True

    res = ai_router.classify("write a poem")
    assert res.get("requires_web") is False


def test_needs_web_search_facade():
    assert WebSearchService.needs_web_search("who is the president of india") is True
    assert WebSearchService.needs_web_search("what is python") is True
    assert WebSearchService.needs_web_search("what is fastapi") is True
    assert WebSearchService.needs_web_search("write a poem") is False
    assert WebSearchService.needs_web_search("make this email more professional") is False
