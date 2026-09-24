"""Unit and integration test suite for HSBot Advanced Game Generation Engine.
"""

import pytest
from app.services.game.models import (
    GameGenre,
    GameQualityLevel,
    GameControlScheme,
    GameDesignSpec,
)
from app.services.game.detector import GameDetector, game_detector
from app.services.game.designer import GameDesigner, game_designer
from app.services.game.procedural_art import ProceduralArtEngine, procedural_art_engine
from app.services.game.generator import GameGenerator, game_generator
from app.services.game.playtester import GamePlaytester, game_playtester
from app.services.nvidia.router import ai_router
from app.services.intent.classifier import GeneralIntentClassifier
from app.services.intent.models import IntentCategory


class TestGameDetector:
    def test_detects_game_requests(self):
        positive_queries = [
            "create a football game with HTML controls and a good UI",
            "make a racing game",
            "build a platformer game with jump mechanics",
            "create an interactive browser game",
            "build a playable HTML game",
            "make a 2D shooter arcade game",
            "create a game",
        ]
        for q in positive_queries:
            assert game_detector.is_game_request(q) is True, f"Failed to detect: {q}"

    def test_ignores_non_game_queries(self):
        negative_queries = [
            "what is the score of the football game yesterday?",
            "can I play football in rainy weather?",
            "explain the history of arcade games",
            "who won the game?",
        ]
        for q in negative_queries:
            assert game_detector.is_game_request(q) is False, f"False positive for: {q}"

    def test_extract_genre(self):
        assert game_detector.extract_genre("make a football game") == GameGenre.FOOTBALL
        assert game_detector.extract_genre("build a soccer penalty game") == GameGenre.FOOTBALL
        assert game_detector.extract_genre("create a 2D car racing game") == GameGenre.RACING
        assert game_detector.extract_genre("build a jump platformer") == GameGenre.PLATFORMER
        assert game_detector.extract_genre("create a space shooter") == GameGenre.SHOOTER
        assert game_detector.extract_genre("build a tetris puzzle") == GameGenre.PUZZLE

    def test_quality_promotion(self):
        # Professional / best keywords promote to POLISHED
        assert game_detector.extract_quality("build the best football game") in (
            GameQualityLevel.POLISHED,
            GameQualityLevel.PREMIUM,
        )
        assert game_detector.extract_quality("create a professional browser game") in (
            GameQualityLevel.POLISHED,
            GameQualityLevel.PREMIUM,
        )
        # Default is POLISHED (never toy prototype)
        assert game_detector.extract_quality("make a game") == GameQualityLevel.POLISHED

    def test_ambiguity_quiz_detection(self):
        needs_quiz, reason = game_detector.needs_clarification_quiz("make a game")
        assert needs_quiz is True
        assert reason == "bare_game"

        # Explicit request with details should not require quiz
        needs_quiz, _ = game_detector.needs_clarification_quiz(
            "create a football game with keyboard controls, score, and AI opponent"
        )
        assert needs_quiz is False


class TestGameDesigner:
    def test_create_spec(self):
        spec = game_designer.create_spec("create a football game with keyboard controls")
        assert spec.genre == GameGenre.FOOTBALL
        assert spec.has_ai_opponent is True
        assert "MENU" in spec.state_machine
        assert "PLAYING" in spec.state_machine
        assert len(spec.procedural_assets) > 0

    def test_build_gdd_markdown(self):
        spec = game_designer.create_spec("make a racing game")
        gdd = game_designer.build_gdd_markdown(spec)
        assert "GAME DESIGN SPECIFICATION" in gdd
        assert "RACING" in gdd
        assert "SoundEffects" in gdd
        assert "AudioContext" in gdd


class TestProceduralArtEngine:
    def test_football_guidelines(self):
        guide = procedural_art_engine.get_genre_guidelines(GameGenre.FOOTBALL)
        assert "NEVER draw a bare white background" in guide
        assert "PITCH" in guide
        assert "BALL" in guide
        assert "PLAYERS" in guide

    def test_web_audio_code(self):
        code = procedural_art_engine.get_web_audio_code()
        assert "AudioContext" in code
        assert "playKick" in code
        assert "playGoal" in code
        assert "toggleMute" in code


class TestGameGenerator:
    def test_build_game_system_prompt(self):
        prompt = game_generator.build_game_system_prompt("create a football game with great UI")
        assert "CRITICAL GAME / WEB APP DEVELOPMENT REQUIREMENT" in prompt
        assert "DO NOT GENERATE A TOY PROTOTYPE" in prompt
        assert "index.html" in prompt
        assert "styles.css" in prompt
        assert "script.js" in prompt
        assert "requestAnimationFrame" in prompt
        assert "FOOTBALL" in prompt


class TestGamePlaytester:
    def test_valid_game_code_passes(self):
        html_content = """<!DOCTYPE html>
<html>
<head><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Football</title></head>
<body>
  <div id="hud"><span id="score">0 - 0</span><span id="timer">90s</span></div>
  <canvas id="gameCanvas" width="800" height="500"></canvas>
  <button id="touch-kick">Kick</button>
</body>
</html>"""
        js_content = """
const canvas = document.getElementById('gameCanvas');
const ctx = canvas.getContext('2d');
let gameState = 'MENU';
let score = 0;
let lastTime = 0;

window.addEventListener('keydown', (e) => {
  if (['Space', 'ArrowUp', 'ArrowDown'].includes(e.code)) e.preventDefault();
});

const audio = new (window.AudioContext || window.webkitAudioContext)();

function update(dt) {
  if (gameState === 'PLAYING') {
    score += 1;
  }
}

function render() {
  ctx.fillStyle = '#2e7d32';
  ctx.fillRect(0, 0, canvas.width, canvas.height);
  ctx.beginPath();
  ctx.arc(100, 100, 10, 0, Math.PI * 2);
  ctx.fillStyle = '#ffffff';
  ctx.fill();
}

function gameLoop(time) {
  const dt = (time - lastTime) / 1000;
  lastTime = time;
  update(dt);
  render();
  requestAnimationFrame(gameLoop);
}
requestAnimationFrame(gameLoop);
"""
        files = [
            {"path": "index.html", "content": html_content},
            {"path": "styles.css", "content": "body { margin: 0; }"},
            {"path": "script.js", "content": js_content},
        ]
        report = game_playtester.test_code(files, genre=GameGenre.FOOTBALL)
        assert report.passed is True
        assert report.has_loop is True
        assert report.has_controls is True
        assert report.has_fsm is True
        assert report.has_procedural_graphics is True
        assert report.has_audio_synth is True
        assert report.quality_score >= 80

        checklist = game_playtester.generate_verification_checklist(report, genre=GameGenre.FOOTBALL)
        assert checklist.all_passed is True
        assert checklist.overall_score >= 80
        assert len(checklist.items) >= 5

    def test_toy_prototype_detected_with_warnings_or_errors(self):
        # A bad toy prototype with no loop and no input listeners
        files = [
            {"path": "index.html", "content": "<div>Static Rect</div>"},
            {"path": "script.js", "content": "console.log('No game loop here');"},
        ]
        report = game_playtester.test_code(files)
        assert report.passed is False
        assert report.has_loop is False
        assert report.has_controls is False
        assert len(report.errors) >= 2


class TestAIRouterGameIntegration:
    def test_router_classifies_game_development(self):
        decision = ai_router.classify("create a football game with good UI")
        assert decision["primary_intent"] == "game_development"
        assert decision["requires_verification"] is True

        task = ai_router.detect_task("make a 2D racing game")
        assert task == "game_development"


class TestIntentClassifierGameIntegration:
    def test_intent_classifier_game_request(self):
        res = GeneralIntentClassifier.classify("make a football game with controls")
        assert res.primary_intent == IntentCategory.GAME_DEVELOPMENT
        assert res.needs_quiz is False

    def test_intent_classifier_bare_game_triggers_quiz(self):
        res = GeneralIntentClassifier.classify("make a game")
        assert res.primary_intent == IntentCategory.GAME_DEVELOPMENT
        assert res.needs_quiz is True
        assert res.quiz is not None
        assert len(res.quiz.options) >= 3
