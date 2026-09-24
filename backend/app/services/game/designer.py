"""Game Designer: creates the compact Game Design Specification (GDD) for implementation.
"""

from typing import Optional, Dict, Any
from app.services.game.models import (
    GameGenre,
    GameQualityLevel,
    GameControlScheme,
    GameDesignSpec,
)
from app.services.game.detector import GameDetector
from app.services.game.procedural_art import ProceduralArtEngine


class GameDesigner:
    """Designs game systems, architecture, loops, and gameplay specifications."""

    def create_spec(self, user_prompt: str, hints: Optional[Dict[str, Any]] = None) -> GameDesignSpec:
        hints = hints or {}
        genre = hints.get("genre") or GameDetector.extract_genre(user_prompt)
        quality = hints.get("quality") or GameDetector.extract_quality(user_prompt)
        controls = hints.get("controls") or GameDetector.extract_controls(user_prompt)

        title = self._generate_title(genre, user_prompt)
        objective = self._generate_objective(genre)
        assets = self._generate_assets(genre)

        return GameDesignSpec(
            title=title,
            genre=genre,
            quality=quality,
            controls=controls,
            has_ai_opponent=genre in (GameGenre.FOOTBALL, GameGenre.RACING, GameGenre.SHOOTER, GameGenre.ARCADE),
            objective=objective,
            procedural_assets=assets,
            responsive_design=True,
        )

    def _generate_title(self, genre: GameGenre, prompt: str) -> str:
        prompt_clean = prompt.strip().title()
        if "Football" in prompt_clean or "Soccer" in prompt_clean:
            return "Football Champions Arena"
        if "Racing" in prompt_clean or "Car" in prompt_clean:
            return "Turbo Velocity Racer"
        if "Platformer" in prompt_clean:
            return "Pixel Quest Odyssey"
        if "Shooter" in prompt_clean:
            return "Cosmic Striker X"
        return f"{genre.value.capitalize()} Arcade Pro"

    def _generate_objective(self, genre: GameGenre) -> str:
        if genre == GameGenre.FOOTBALL:
            return "Outscore opponent AI before match time expires (or first to 5 goals)."
        if genre == GameGenre.RACING:
            return "Complete 3 laps with the fastest time while overtaking AI competitors."
        if genre == GameGenre.PLATFORMER:
            return "Traverse obstacles, defeat enemies, collect coins, and reach the victory flag."
        if genre == GameGenre.SHOOTER:
            return "Eliminate incoming waves of enemy ships, avoid projectiles, and survive."
        return "Score points by interacting with targets, avoid obstacles, and achieve high score."

    def _generate_assets(self, genre: GameGenre) -> list[str]:
        if genre == GameGenre.FOOTBALL:
            return ["GrassPitch", "PitchMarkings", "GoalNets", "PlayerKit", "OpponentAI", "SoccerBall", "KickParticle"]
        if genre == GameGenre.RACING:
            return ["AsphaltTrack", "CurbChevrons", "PlayerCar", "AICars", "HeadlightBeams", "SkidSmoke"]
        return ["GameArena", "PlayerAvatar", "Obstacles", "Collectibles", "ParticleFX"]

    def build_gdd_markdown(self, spec: GameDesignSpec) -> str:
        """Constructs an internal Game Design Document (GDD) string."""
        genre_guidelines = ProceduralArtEngine.get_genre_guidelines(spec.genre)
        audio_code = ProceduralArtEngine.get_web_audio_code()

        return f"""
GAME DESIGN SPECIFICATION (GDD):
================================
- Title: {spec.title}
- Genre: {spec.genre.value.upper()}
- Target Quality: {spec.quality.value.upper()} (Zero Toy Prototypes / Zero Placeholder Geometry)
- Controls: {spec.controls.value.upper()} (Keyboard: WASD / Arrow keys, Space for primary action, Shift for sprint/boost; Visible on-screen Touch D-Pad / Buttons for mobile & tablet)
- Objective: {spec.objective}
- Game State Machine: {", ".join(spec.state_machine)}
- Core Systems: {", ".join(spec.core_systems)}
- Responsive Engine: Automatic canvas resizing with window.devicePixelRatio, aspect ratio preservation, touch & mouse coordinate mapping.

{genre_guidelines}

WEB AUDIO INTEGRATION:
{audio_code}
"""


game_designer = GameDesigner()
