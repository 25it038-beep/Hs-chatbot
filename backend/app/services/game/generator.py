"""Game Prompt Generator: synthesizes rigorous system prompt rules and standards for game generation.
"""

from app.services.game.models import GameGenre, GameQualityLevel, GameDesignSpec
from app.services.game.detector import GameDetector
from app.services.game.designer import GameDesigner, game_designer


class GameGenerator:
    """Produces the comprehensive system prompt instructions for game creation."""

    def build_game_system_prompt(self, user_prompt: str) -> str:
        genre = GameDetector.extract_genre(user_prompt)
        quality = GameDetector.extract_quality(user_prompt)
        spec = game_designer.create_spec(user_prompt, {"genre": genre, "quality": quality})
        gdd = game_designer.build_gdd_markdown(spec)

        return f"""
============================================================
CRITICAL GAME / WEB APP DEVELOPMENT REQUIREMENT:
============================================================
The user has requested to create or build a playable game ({genre.value.upper()}).
You must act as a professional software and game development agent.

DO NOT GENERATE A TOY PROTOTYPE OR PLACEHOLDER SHAPES!
- NEVER output primitive unstyled circles or bare rectangles on a blank canvas.
- NEVER deliver a static scene or a single movement function without an objective.
- NEVER truncate code, use "// TODO", or write "// rest of code here".

YOU MUST DELIVER A COMPLETE, POLISHED MULTI-FILE GAME WORKSPACE:
1. `index.html`: Fully semantic HTML5 structure with responsive viewport, HUD containers (Score, Timer, Health/Status), canvas element, Start Screen / Menu overlay, Pause overlay, Game Over / Victory modal, and on-screen touch controls container for mobile/tablet.
2. `styles.css`: Complete modern CSS styling. Full-screen or centered responsive game arena, sleek glassmorphism HUD, animated buttons, retro/arcade fonts or modern typography, glowing badges, touch control styling, and modal transitions.
3. `script.js`: Complete 100% playable game code including:
   - Real Game Loop (`requestAnimationFrame` with delta-time calculation).
   - Finite State Machine (`MENU`, `PLAYING`, `PAUSED`, `GOAL` or `POINT`, `GAME_OVER`, `WIN`).
   - Controls: Keyboard (WASD, Arrow keys, Space for kick/action, Shift for sprint/boost, Esc/P for pause) with `e.preventDefault()` on game keys to prevent page scrolling.
   - Visible on-screen Touch D-Pad / Buttons for mobile and tablet devices.
   - Responsive Canvas: dynamically sized or scaled with `window.devicePixelRatio` and aspect ratio preservation.
   - Zero-dependency Web Audio API procedural synthesizer (kicks, goals, whistles, chimes, mute toggle).
   - Collision detection, scoring, AI opponent logic (if applicable), and restart mechanics.
4. `package.json`: Valid project manifest with scripts.
5. `README.md`: Clear setup, controls guide, and gameplay instructions.

RULES:
- Every file must be complete, production-grade, and immediately runnable.
- Output each file in its own markdown code block with the filename as a comment on line 1.

{gdd}
============================================================
"""


game_generator = GameGenerator()
