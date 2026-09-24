"""Data models and schemas for the Advanced Game Generation Engine.
"""

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class GameGenre(str, Enum):
    FOOTBALL = "football"
    RACING = "racing"
    PLATFORMER = "platformer"
    SHOOTER = "shooter"
    PUZZLE = "puzzle"
    ARCADE = "arcade"
    RPG = "rpg"
    STRATEGY = "strategy"
    CASUAL = "casual"
    OTHER = "other"


class GameQualityLevel(str, Enum):
    BASIC = "basic"
    PROTOTYPE = "prototype"
    POLISHED = "polished"
    PREMIUM = "premium"


class GameControlScheme(str, Enum):
    KEYBOARD = "keyboard"
    TOUCH = "touch"
    MOUSE = "mouse"
    HYBRID = "hybrid"


class GameDesignSpec(BaseModel):
    title: str = "HTML5 Game"
    genre: GameGenre = GameGenre.ARCADE
    quality: GameQualityLevel = GameQualityLevel.POLISHED
    controls: GameControlScheme = GameControlScheme.HYBRID
    has_ai_opponent: bool = True
    objective: str = "Achieve the highest score or reach victory condition."
    state_machine: List[str] = Field(
        default_factory=lambda: [
            "MENU",
            "PLAYING",
            "PAUSED",
            "GOAL_OR_POINT",
            "GAME_OVER",
            "WIN",
            "RESTARTING",
        ]
    )
    core_systems: List[str] = Field(
        default_factory=lambda: [
            "GameLoop",
            "InputManager",
            "PhysicsEngine",
            "CollisionDetector",
            "ScoreSystem",
            "HUD",
            "AudioManager",
        ]
    )
    procedural_assets: List[str] = Field(default_factory=list)
    audio_effects: List[str] = Field(
        default_factory=lambda: ["action", "hit", "score", "victory", "lose"]
    )
    responsive_design: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()


class GamePlaytestReport(BaseModel):
    passed: bool = True
    has_loop: bool = True
    has_fsm: bool = True
    has_controls: bool = True
    has_scoring_or_objective: bool = True
    has_procedural_graphics: bool = True
    has_responsive_canvas: bool = True
    has_audio_synth: bool = False
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    quality_score: int = 90
    summary: str = "Game passed gameplay and runtime validation."

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()


class GameVerificationChecklist(BaseModel):
    title: str = "Game Verification"
    genre: str = "arcade"
    quality: str = "polished"
    overall_score: int = 100
    all_passed: bool = True
    items: List[Dict[str, Any]] = Field(default_factory=list)
    summary: str = "All game systems and requirements verified."

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()
