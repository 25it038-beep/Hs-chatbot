"""Game intent detection, genre extraction, and quality calibration.
"""

import re
from typing import Optional, Dict, Any, Tuple
from app.services.game.models import (
    GameGenre,
    GameQualityLevel,
    GameControlScheme,
    GameDesignSpec,
)


GAME_VERBS = (
    r"(?:create|build|make|code|develop|program|design|generate|implement|craft)"
)

GAME_NOUNS = (
    r"(?:game|playable\s+game|browser\s+game|html5?\s+game|canvas\s+game|web\s+game|"
    r"video\s*game|mini\s*game|2d\s+game|arcade\s+game)"
)

EXPLICIT_GAME_TITLES = (
    r"(?:football|soccer|racing|racer|platformer|shooter|flappy\s*bird|snake\s*game|tetris|"
    r"pong|space\s*invaders|pacman|brick\s*breaker|tower\s*defense|runner\s*game)"
)

GAME_REQUEST_RE = re.compile(
    rf"\b{GAME_VERBS}\s+(?:a\s+|an\s+|the\s+|me\s+a\s+|me\s+an\s+)?(?:[\w\s]{{0,25}})?{GAME_NOUNS}\b|"
    rf"\b{GAME_VERBS}\s+(?:a\s+|an\s+|the\s+|me\s+a\s+|me\s+an\s+)?{EXPLICIT_GAME_TITLES}\b|"
    rf"\b(?:playable|interactive)\s+{GAME_NOUNS}\b|"
    r"\b(?:html|canvas|javascript|js)\s+game\b",
    re.I,
)


class GameDetector:
    """Detects game creation requests, extracts genre, quality, and parameters."""

    @classmethod
    def is_game_request(cls, text: str) -> bool:
        if not text:
            return False
        clean = text.strip()
        # Direct regex match
        if GAME_REQUEST_RE.search(clean):
            return True
        # Compound match: e.g. "make a football game" or "football game with controls"
        if re.search(r"\b(game|gameplay)\b", clean, re.I) and re.search(
            r"\b(football|soccer|racing|platformer|shooter|arcade|puzzle|player|controls|score|level)\b",
            clean,
            re.I,
        ):
            if re.search(rf"\b{GAME_VERBS}\b", clean, re.I) or re.search(
                r"\b(with|for|playable|interactive)\b", clean, re.I
            ):
                return True
        return False

    @classmethod
    def extract_genre(cls, text: str) -> GameGenre:
        clean = text.lower()
        if re.search(r"\b(football|soccer|penalty|fifa|goal)\b", clean):
            return GameGenre.FOOTBALL
        if re.search(r"\b(racing|car|drive|driving|track|drift|speed)\b", clean):
            return GameGenre.RACING
        if re.search(r"\b(platformer|jump|mario|run\s+and\s+jump|side\s*scroller)\b", clean):
            return GameGenre.PLATFORMER
        if re.search(r"\b(shooter|shooting|bullet|space\s*invaders|asteroids|guns?)\b", clean):
            return GameGenre.SHOOTER
        if re.search(r"\b(puzzle|tetris|match\s*3|sudoku|2048|block\s*drop)\b", clean):
            return GameGenre.PUZZLE
        if re.search(r"\b(snake|pong|brick\s*breaker|pacman|breakout|flappy|arcade)\b", clean):
            return GameGenre.ARCADE
        if re.search(r"\b(rpg|role\s*playing|dungeon|quest|hero)\b", clean):
            return GameGenre.RPG
        if re.search(r"\b(strategy|tower\s*defense|chess|checkers)\b", clean):
            return GameGenre.STRATEGY
        return GameGenre.ARCADE

    @classmethod
    def extract_quality(cls, text: str) -> GameQualityLevel:
        clean = text.lower()
        if re.search(r"\b(premium|commercial|aaa|masterpiece)\b", clean):
            return GameQualityLevel.PREMIUM
        if re.search(r"\b(best|professional|high\s*quality|advanced|complete|modern|polished)\b", clean):
            return GameQualityLevel.POLISHED
        if re.search(r"\b(quick|simple|basic|toy|sample|tiny)\b", clean):
            return GameQualityLevel.BASIC
        # Default standard is POLISHED — never toy prototypes!
        return GameQualityLevel.POLISHED

    @classmethod
    def extract_controls(cls, text: str) -> GameControlScheme:
        clean = text.lower()
        has_touch = bool(re.search(r"\b(touch|mobile|phone|tablet|d-?pad)\b", clean))
        has_key = bool(re.search(r"\b(keyboard|wasd|arrow\s*keys|keys?)\b", clean))
        has_mouse = bool(re.search(r"\b(mouse|pointer|click)\b", clean))

        if (has_touch and has_key) or not (has_touch or has_key or has_mouse):
            return GameControlScheme.HYBRID
        if has_touch:
            return GameControlScheme.TOUCH
        if has_key:
            return GameControlScheme.KEYBOARD
        if has_mouse:
            return GameControlScheme.MOUSE
        return GameControlScheme.HYBRID

    @classmethod
    def needs_clarification_quiz(cls, text: str) -> Tuple[bool, Optional[str]]:
        """Determines if the game prompt is too ambiguous and needs an adaptive quiz."""
        clean = text.strip().lower()
        # If the user specifically gave genre, controls, and details, no quiz needed
        words = clean.split()
        if len(words) < 5 and re.match(r"^(?:create|make|build)\s+(?:a\s+)?game$", clean):
            return True, "bare_game"
        if len(words) < 6 and re.match(r"^(?:create|make|build)\s+(?:a\s+)?(football|racing|shooting|arcade)\s+game$", clean):
            # Missing critical style/mechanic
            return True, "bare_genre"
        return False, None


game_detector = GameDetector()
