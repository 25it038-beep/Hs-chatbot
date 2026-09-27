"""Prompt enhancer for video generation with cinematic camera, lighting, and movement syntax."""

import re
import logging
from typing import Optional, Dict
from app.services.video.schemas import EnhancePromptResponse

logger = logging.getLogger("hsbot.video.enhancer")


class VideoPromptEnhancer:
    """Enhances raw user prompts into professional cinematographic descriptions."""

    CAMERA_MOVEMENTS = {
        "cinematic": "smooth dynamic camera tracking forward, subtle slow-motion depth",
        "action": "dynamic fast-paced handheld tracking shot, energetic perspective",
        "aerial": "sweeping high-altitude cinematic drone shot, wide establishing angle",
        "portrait": "intimate 50mm close-up with shallow depth of field, gentle push-in",
        "timelapse": "hyper-lapse motion blur, fluid environmental transition",
        "macro": "extreme macro focus pull, razor-sharp details",
    }

    LIGHTINGS = {
        "cinematic": "dramatic volumetric rim lighting, soft diffuse fill, golden hour warmth",
        "dark": "low-key moody chiaroscuro lighting, deep cinematic contrast, subtle ambient bounce",
        "bright": "vibrant natural daylight, crisp soft reflections, radiant highlights",
        "neon": "cyberpunk neon glow, specular reflections on wet surfaces, vivid color contrast",
        "studio": "balanced 3-point softbox studio lighting, clean rim highlight",
    }

    ATMOSPHERES = {
        "cinematic": "photorealistic 8k detail, ultra-smooth 24fps motion, 35mm film grain, masterpiece",
        "anime": "high-end anime animation aesthetic, fluid keyframes, vibrant artistic palette",
        "realistic": "documentary grade photorealism, natural motion physics, true-to-life textures",
    }

    @classmethod
    def enhance(cls, prompt: str, style: str = "cinematic") -> EnhancePromptResponse:
        cleaned = prompt.strip()
        # Clean trailing punctuation
        cleaned = re.sub(r"[.!\s]+$", "", cleaned)

        # Detect tone or genre
        lower = cleaned.lower()
        cam_key = "cinematic"
        if any(w in lower for w in ["drone", "mountain", "city skyline", "landscape", "island"]):
            cam_key = "aerial"
        elif any(w in lower for w in ["person", "face", "portrait", "girl", "man", "woman", "eyes"]):
            cam_key = "portrait"
        elif any(w in lower for w in ["run", "car", "racing", "speed", "fight", "explosion"]):
            cam_key = "action"
        elif any(w in lower for w in ["sunset", "clouds moving", "traffic", "stars", "night to day"]):
            cam_key = "timelapse"

        light_key = "cinematic"
        if any(w in lower for w in ["neon", "cyber", "tokyo night", "synthwave"]):
            light_key = "neon"
        elif any(w in lower for w in ["night", "dark", "shadow", "horror", "mystery"]):
            light_key = "dark"
        elif any(w in lower for w in ["sunny", "day", "beach", "morning", "bright"]):
            light_key = "bright"

        style_key = style.lower() if style.lower() in cls.ATMOSPHERES else "cinematic"

        cam_text = cls.CAMERA_MOVEMENTS.get(cam_key, cls.CAMERA_MOVEMENTS["cinematic"])
        light_text = cls.LIGHTINGS.get(light_key, cls.LIGHTINGS["cinematic"])
        atmos_text = cls.ATMOSPHERES.get(style_key, cls.ATMOSPHERES["cinematic"])

        enhanced = f"{cleaned}, {cam_text}, {light_text}, {atmos_text}"

        return EnhancePromptResponse(
            original_prompt=prompt,
            enhanced_prompt=enhanced,
            camera_movement=cam_text,
            lighting=light_text,
            style=style_key,
        )


prompt_enhancer = VideoPromptEnhancer()
