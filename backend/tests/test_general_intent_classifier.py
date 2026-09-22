import pytest
from app.services.intent import (
    GeneralIntentClassifier,
    IntentCategory,
    IntentConfidence,
    QuizGenerator,
    AnswerVerifier,
    ChatRequirementSnapshot,
)


def test_clear_leadership_queries_skip_quiz():
    """Clear queries about office holders MUST never show a quiz (Minimum-Question Principle)."""
    queries = [
        "Who is the CM of Tamil Nadu?",
        "who is the chief minister of tamil nadu",
        "Who is the president of India?",
        "Name the CEO of Apple",
        "who is the current prime minister of the UK",
    ]
    for q in queries:
        res = GeneralIntentClassifier.classify(q)
        assert res.primary_intent == IntentCategory.CURRENT_FACTUAL, f"Failed for {q}"
        assert res.confidence == IntentConfidence.HIGH, f"Failed confidence for {q}"
        assert res.needs_quiz is False, f"Must not quiz for {q}"
        assert res.requires_web is True
        assert res.requires_current_data is True


def test_live_time_and_weather_skip_quiz():
    """Live tools for time and weather must execute directly without quizzes."""
    time_res = GeneralIntentClassifier.classify("What time is it in Chennai?")
    assert time_res.primary_intent == IntentCategory.TIME
    assert time_res.needs_quiz is False
    assert time_res.requires_live_tool == "time"

    weather_res = GeneralIntentClassifier.classify("What is the weather in Paris today?")
    assert weather_res.primary_intent == IntentCategory.WEATHER
    assert weather_res.needs_quiz is False
    assert weather_res.requires_live_tool == "weather"


def test_clear_translation_and_math_skip_quiz():
    """Direct translation and calculation must not trigger quizzes."""
    trans_res = GeneralIntentClassifier.classify("Translate hello world into French")
    assert trans_res.primary_intent == IntentCategory.TRANSLATION
    assert trans_res.needs_quiz is False

    math_res = GeneralIntentClassifier.classify("calculate 45 * 12 + 8")
    assert math_res.primary_intent == IntentCategory.CALCULATION
    assert math_res.needs_quiz is False


def test_ambiguous_entity_opening_triggers_quiz():
    """Vague prompt like 'Tell me about Tamil Nadu CM' or 'about the president' should offer an adaptive quiz."""
    res = GeneralIntentClassifier.classify("Tell me about Tamil Nadu CM")
    assert res.needs_quiz is True
    assert res.quiz is not None
    assert len(res.quiz.options) >= 2
    assert any("Current office holder" in opt for opt in res.quiz.options)


def test_ambiguous_recommendation_triggers_quiz():
    """Open-ended recommendation like 'Suggest me a phone' should quiz for priorities."""
    res = GeneralIntentClassifier.classify("Suggest me a phone")
    assert res.needs_quiz is True
    assert res.quiz is not None
    assert res.primary_intent == IntentCategory.RECOMMENDATION
    assert any("Camera" in opt or "Performance" in opt or "Budget" in opt for opt in res.quiz.options)


def test_ambiguous_presentation_triggers_quiz():
    """Open-ended presentation requests should ask for presentation style / type."""
    res = GeneralIntentClassifier.classify("Make a presentation")
    assert res.needs_quiz is True
    assert res.quiz is not None
    assert res.primary_intent == IntentCategory.PRESENTATION_REQUEST


def test_anti_quiz_loop_logic():
    """If user is responding to a previous quiz in context, never loop back to another quiz."""
    context = [
        {"role": "user", "content": "Tell me about Tamil Nadu CM"},
        {
            "role": "assistant",
            "content": "What would you like to know about Tamil Nadu CM?",
            "extra_data": {
                "quiz": {
                    "id": "quiz_leader",
                    "question": "What would you like to know?",
                    "options": ["Current office holder", "Biography & background"],
                }
            },
        },
    ]
    # User clicks or types an option
    res = GeneralIntentClassifier.classify("Current office holder", context=context)
    assert res.needs_quiz is False, "Anti-looping must prevent second quiz"
    assert res.primary_intent == IntentCategory.CURRENT_FACTUAL


def test_answer_verifier_rules():
    """AnswerVerifier should verify sources and selectively surface satisfaction checks."""
    # 1. Direct factual answer without clarification should NOT bother user with satisfaction check
    snap_factual = ChatRequirementSnapshot(
        goal="Identify office holder",
        intent=IntentCategory.CURRENT_FACTUAL,
        confidence=IntentConfidence.HIGH,
        freshness="current",
    )
    v1 = AnswerVerifier.verify(
        content="The current Chief Minister of Tamil Nadu is M. K. Stalin.",
        snapshot=snap_factual,
        sources=[{"title": "Govt of TN", "url": "https://tn.gov.in"}],
        was_clarified=False,
    )
    assert v1.answer_verified is True
    assert v1.sources_verified is True
    assert v1.satisfaction_check is False  # Simple factual answer does not annoy user

    # 2. Clarified answer SHOULD offer satisfaction check
    v2 = AnswerVerifier.verify(
        content="Here is the detailed overview you requested...",
        snapshot=snap_factual,
        sources=[{"title": "Govt of TN", "url": "https://tn.gov.in"}],
        was_clarified=True,
    )
    assert v2.satisfaction_check is True

    # 3. Subjective recommendation SHOULD offer satisfaction check
    snap_rec = ChatRequirementSnapshot(
        goal="Recommend phone",
        intent=IntentCategory.RECOMMENDATION,
        confidence=IntentConfidence.MEDIUM,
    )
    v3 = AnswerVerifier.verify(
        content="Based on your focus on camera quality, here are the top 3 phones: 1. Pixel 9 Pro...",
        snapshot=snap_rec,
        sources=[],
        was_clarified=False,
    )
    assert v3.satisfaction_check is True
