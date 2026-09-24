"""Procedural vector graphics and Web Audio API synthesizer generators.
Guarantees zero primitive placeholder geometry (no bare unstyled circles or rects).
"""

from typing import Dict, Any
from app.services.game.models import GameGenre


class ProceduralArtEngine:
    """Provides procedural canvas and vector rendering recipes + Web Audio synthesis."""

    @staticmethod
    def get_web_audio_code() -> str:
        """Returns self-contained Web Audio API synthesizer for rich game audio."""
        return """
// ── Procedural Web Audio Synthesizer (Zero External Audio Files Needed) ──
class SoundEffects {
  constructor() {
    this.ctx = null;
    this.muted = false;
  }
  init() {
    if (!this.ctx) {
      const AudioCtx = window.AudioContext || window.webkitAudioContext;
      if (AudioCtx) this.ctx = new AudioCtx();
    }
    if (this.ctx && this.ctx.state === 'suspended') {
      this.ctx.resume();
    }
  }
  toggleMute() {
    this.muted = !this.muted;
    return this.muted;
  }
  playTone(freq, type, duration, startVol = 0.2, endVol = 0.001) {
    if (this.muted) return;
    this.init();
    if (!this.ctx) return;
    try {
      const osc = this.ctx.createOscillator();
      const gain = this.ctx.createGain();
      osc.type = type;
      osc.frequency.setValueAtTime(freq, this.ctx.currentTime);
      gain.gain.setValueAtTime(startVol, this.ctx.currentTime);
      gain.gain.exponentialRampToValueAtTime(endVol, this.ctx.currentTime + duration);
      osc.connect(gain);
      gain.connect(this.ctx.destination);
      osc.start();
      osc.stop(this.ctx.currentTime + duration);
    } catch (e) {
      // Audio fallback silent
    }
  }
  playKick() {
    if (this.muted) return;
    this.init();
    if (!this.ctx) return;
    try {
      const osc = this.ctx.createOscillator();
      const gain = this.ctx.createGain();
      osc.frequency.setValueAtTime(140, this.ctx.currentTime);
      osc.frequency.exponentialRampToValueAtTime(30, this.ctx.currentTime + 0.12);
      gain.gain.setValueAtTime(0.3, this.ctx.currentTime);
      gain.gain.linearRampToValueAtTime(0.01, this.ctx.currentTime + 0.12);
      osc.connect(gain);
      gain.connect(this.ctx.destination);
      osc.start();
      osc.stop(this.ctx.currentTime + 0.12);
    } catch (e) {}
  }
  playWhistle() {
    this.playTone(880, 'sine', 0.25, 0.25);
    setTimeout(() => this.playTone(1174, 'sine', 0.35, 0.3), 100);
  }
  playGoal() {
    const notes = [523.25, 659.25, 783.99, 1046.50];
    notes.forEach((freq, i) => {
      setTimeout(() => this.playTone(freq, 'triangle', 0.3, 0.3), i * 110);
    });
  }
  playClick() {
    this.playTone(600, 'sine', 0.05, 0.15);
  }
  playGameOver() {
    const notes = [440, 392, 349, 293];
    notes.forEach((freq, i) => {
      setTimeout(() => this.playTone(freq, 'sawtooth', 0.25, 0.2), i * 150);
    });
  }
}
const sfx = new SoundEffects();
"""

    @staticmethod
    def get_genre_guidelines(genre: GameGenre) -> str:
        """Returns specific procedural art instructions for the requested genre."""
        if genre == GameGenre.FOOTBALL:
            return """
PROCEDURAL GRAPHICS REQUIREMENTS FOR FOOTBALL / SOCCER:
- NEVER draw a bare white background or simple solid rectangle.
- PITCH: Draw grass field with realistic alternating light-green & dark-green mowed lawn stripes.
- FIELD MARKINGS: Crisp white lines, center circle with center spot, penalty boxes (18-yard & 6-yard boxes), penalty arc, corner flags/arcs.
- GOALS: Render goal posts on left & right (or top & bottom) with post thickness, white woodwork, and semi-transparent net mesh crosshatch pattern.
- BALL: Procedural soccer ball! Draw white circle with subtle radial shadow, black pentagonal center patches, seam lines, and dynamic ground shadow beneath.
- PLAYERS: NOT a single-color circle! Draw:
  1. Ground shadow (semi-transparent dark ellipse beneath player feet).
  2. Team jersey (primary color, team stripes/number).
  3. Shorts and boots/cleats.
  4. Player head/skin tone and hair.
  5. Direction indicator or kicking leg animation when kicking.
- OPPONENT AI: Distinct contrasting jersey color, defensive positioning AI, smart chase and tackle behavior.
"""
        elif genre == GameGenre.RACING:
            return """
PROCEDURAL GRAPHICS REQUIREMENTS FOR RACING:
- TRACK: Asphalt road texture (dark slate/gray) with dual yellow/white center dashed lines.
- CURBS: Alternating red and white rumble strips (chevrons) on track boundaries.
- CAR: Procedural sleek race car! Draw:
  1. Car chassis with aerodynamic curves, spoiler, and windshield reflection.
  2. Four distinct tires with black rubber texture and hubcaps.
  3. Dual headlights emitting subtle beam gradients and glowing red taillights.
  4. Exhaust smoke / tire skid particle trails when accelerating or drifting.
- HUD: Real-time speedometer gauge, lap counter, position rank (e.g. 1st/8), race timer.
"""
        elif genre == GameGenre.PLATFORMER:
            return """
PROCEDURAL GRAPHICS REQUIREMENTS FOR PLATFORMER:
- BACKGROUND: Multi-layered parallax backdrop (sky gradient, distant mountain peaks, foreground trees).
- PLATFORMS: Styled floating platforms with grassy top surface, textured dirt/stone underneath, and beveled edges.
- CHARACTER: Animated stylized adventurer with eyes, limbs, running squash/stretch animation, and jump dust particles.
- COLLECTIBLES: Floating golden coins or gems with pulsing radial shine, rotation effect, and sparkle bursts upon pickup.
"""
        else:
            return """
PROCEDURAL GRAPHICS REQUIREMENTS FOR ARCADE / 2D GAME:
- ENVIRONMENT: Styled themed backdrop with subtle gradient and decorative grid/starfield or arena border.
- SPRITES: Rich vector-drawn objects with outlines, shading, highlights, and dynamic shadows.
- PARTICLES: Particle system emitting sparks, score popups (+100 Floating text), and explosion fragments on impact.
- HUD: Sleek game overlay with health bar, score display, pause/mute buttons, and glowing badges.
"""


procedural_art_engine = ProceduralArtEngine()
