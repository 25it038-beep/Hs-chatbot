"""Design System and Color Palette Engine for HSBot Documents & Presentations.

Provides curated WCAG-compliant color palettes, typography hierarchies,
template configurations, and intelligent design specification inference
based on document type, topic, audience, and user design controls.
"""

from dataclasses import dataclass, field, asdict
from typing import Dict, Any, Optional, List
import re
import logging

logger = logging.getLogger("hsbot.document.design")


@dataclass
class ColorPalette:
    name: str
    primary: str        # Dominant brand/header color
    secondary: str      # Sub-headers, borders, dark accents
    accent: str         # Primary callout, active element, key button
    highlight: str      # Subtle secondary accent, pills, badges
    background: str     # Canvas / slide background
    text: str           # Main body text color
    card_bg: str        # Background for cards/containers
    border: str         # Card and divider border color
    is_dark: bool = False


# Curated Professional Palettes (Strictly WCAG contrast aware)
PALETTES: Dict[str, ColorPalette] = {
    "midnight_tech": ColorPalette(
        name="Midnight Tech",
        primary="#0B1020",
        secondary="#1E293B",
        accent="#3B82F6",
        highlight="#8B5CF6",
        background="#0B1020",
        text="#F8FAFC",
        card_bg="#151C32",
        border="#2A3756",
        is_dark=True,
    ),
    "graphite_professional": ColorPalette(
        name="Graphite Professional",
        primary="#171717",
        secondary="#262626",
        accent="#2563EB",
        highlight="#0EA5E9",
        background="#FAFAFA",
        text="#171717",
        card_bg="#FFFFFF",
        border="#E5E5E5",
        is_dark=False,
    ),
    "emerald_intelligence": ColorPalette(
        name="Emerald Intelligence",
        primary="#064E3B",
        secondary="#065F46",
        accent="#059669",
        highlight="#10B981",
        background="#F0FDF4",
        text="#064E3B",
        card_bg="#FFFFFF",
        border="#A7F3D0",
        is_dark=False,
    ),
    "executive_blue": ColorPalette(
        name="Executive Blue",
        primary="#0F172A",
        secondary="#1E3A5F",
        accent="#2563EB",
        highlight="#38BDF8",
        background="#F8FAFC",
        text="#0F172A",
        card_bg="#FFFFFF",
        border="#CBD5E1",
        is_dark=False,
    ),
    "minimal_monochrome": ColorPalette(
        name="Minimal Monochrome",
        primary="#111111",
        secondary="#404040",
        accent="#525252",
        highlight="#737373",
        background="#FFFFFF",
        text="#171717",
        card_bg="#F5F5F5",
        border="#E5E5E5",
        is_dark=False,
    ),
    "crimson_corporate": ColorPalette(
        name="Crimson Corporate",
        primary="#881337",
        secondary="#4C0519",
        accent="#E11D48",
        highlight="#FB7185",
        background="#FFF1F2",
        text="#1C1917",
        card_bg="#FFFFFF",
        border="#FECDD3",
        is_dark=False,
    ),
    "amber_warmth": ColorPalette(
        name="Amber Warmth",
        primary="#1E1B4B",
        secondary="#312E81",
        accent="#D97706",
        highlight="#F59E0B",
        background="#FEFCE8",
        text="#1E1B4B",
        card_bg="#FFFFFF",
        border="#FDE68A",
        is_dark=False,
    ),
    "modern_vibrant": ColorPalette(
        name="Modern Vibrant",
        primary="#082F49",
        secondary="#0C4A6E",
        accent="#0284C7",
        highlight="#38BDF8",
        background="#F0F9FF",
        text="#0F172A",
        card_bg="#FFFFFF",
        border="#BAE6FD",
        is_dark=False,
    ),
}


# Presentation & Document Templates
TEMPLATES = {
    "executive": {
        "name": "Executive",
        "description": "Dark title slide, clean content slides, large typography, restrained corporate styling.",
        "default_palette": "executive_blue",
        "font_heading": "Calibri",
        "font_body": "Calibri",
    },
    "technology": {
        "name": "Technology",
        "description": "Modern tech aesthetic, geometric elements, architecture diagrams, code/data sections.",
        "default_palette": "midnight_tech",
        "font_heading": "Calibri",
        "font_body": "Calibri",
    },
    "startup_pitch": {
        "name": "Startup Pitch",
        "description": "Large headlines, minimal text, bold visual metrics, problem-solution-traction structure.",
        "default_palette": "amber_warmth",
        "font_heading": "Arial",
        "font_body": "Arial",
    },
    "academic": {
        "name": "Academic",
        "description": "Clean white background, strong typography, research-oriented layout, charts and citations.",
        "default_palette": "graphite_professional",
        "font_heading": "Times New Roman",
        "font_body": "Times New Roman",
    },
    "hackathon": {
        "name": "Hackathon",
        "description": "Energetic, problem -> solution -> architecture -> implementation -> impact flow.",
        "default_palette": "midnight_tech",
        "font_heading": "Calibri",
        "font_body": "Calibri",
    },
    "minimal_premium": {
        "name": "Minimal Premium",
        "description": "Extremely clean, large typography, generous whitespace, subtle accents.",
        "default_palette": "minimal_monochrome",
        "font_heading": "Helvetica",
        "font_body": "Helvetica",
    },
    "dark_cinematic": {
        "name": "Dark Cinematic",
        "description": "Dark background, elegant typography, controlled accent lighting, premium visual hierarchy.",
        "default_palette": "midnight_tech",
        "font_heading": "Calibri",
        "font_body": "Calibri",
    },
}


@dataclass
class TypographySpec:
    heading_font: str = "Calibri"
    body_font: str = "Calibri"
    title_size: int = 40
    subtitle_size: int = 20
    h1_size: int = 28
    h2_size: int = 20
    h3_size: int = 16
    body_size: int = 14
    caption_size: int = 10


@dataclass
class DesignSpec:
    document_type: str                  # technical_report, pitch_deck, hackathon, research_paper, resume, etc.
    target_audience: str               # engineers, executives, investors, judges, general
    style: str                         # modern_professional, academic, startup_bold, minimal_clean, etc.
    template: str                      # executive, technology, startup_pitch, academic, hackathon, minimal_premium, dark_cinematic
    palette_name: str                  # midnight_tech, executive_blue, etc.
    palette: Dict[str, str]            # primary, secondary, accent, highlight, background, text, card_bg, border
    typography: Dict[str, Any]         # font and size hierarchy
    layout: str = "standard_widescreen" # standard_widescreen (16:9) or standard_letter (8.5x11)
    is_dark: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def hex_to_rgb(hex_str: str) -> tuple[int, int, int]:
    """Convert hex string (e.g. #0F172A) to RGB tuple."""
    hex_str = hex_str.lstrip("#")
    if len(hex_str) == 3:
        hex_str = "".join(c * 2 for c in hex_str)
    return tuple(int(hex_str[i:i+2], 16) for i in (0, 2, 4))


def infer_design_spec(
    topic: str,
    doc_format: str,
    user_prompt: str = "",
    existing_spec: Optional[DesignSpec] = None,
) -> DesignSpec:
    """Intelligently infers a complete, professional design specification.

    Analyzes topic, format, and user preferences (e.g. 'dark theme', 'blue', 'minimal').
    If existing_spec is provided (for regeneration), preserves properties while applying overrides.
    """
    text_corpus = f"{topic} {user_prompt}".lower()

    # 1. Check for explicit user style / palette overrides
    selected_palette_key = None
    is_dark_requested = False

    if any(w in text_corpus for w in ["dark theme", "dark mode", "dark background", "cinematic"]):
        is_dark_requested = True
        selected_palette_key = "midnight_tech"
    elif any(w in text_corpus for w in ["minimal", "monochrome", "black and white", "simple"]):
        selected_palette_key = "minimal_monochrome"
    elif any(w in text_corpus for w in ["emerald", "green", "nature", "environment", "sustainability"]):
        selected_palette_key = "emerald_intelligence"
    elif any(w in text_corpus for w in ["blue", "executive", "corporate", "consulting", "enterprise"]):
        selected_palette_key = "executive_blue"
    elif any(w in text_corpus for w in ["amber", "orange", "warm", "creative"]):
        selected_palette_key = "amber_warmth"
    elif any(w in text_corpus for w in ["crimson", "red", "ruby", "bold"]):
        selected_palette_key = "crimson_corporate"
    elif any(w in text_corpus for w in ["vibrant", "cyan", "colorful"]):
        selected_palette_key = "modern_vibrant"

    # 2. Determine Document Type & Audience
    if any(w in text_corpus for w in ["hackathon", "hack", "prototype", "devpost"]):
        doc_type = "hackathon"
        audience = "hackathon_judges"
        template = "hackathon"
        default_palette = "midnight_tech"
    elif any(w in text_corpus for w in ["pitch", "investor", "seed", "venture", "startup"]):
        doc_type = "startup_pitch"
        audience = "investors"
        template = "startup_pitch"
        default_palette = "amber_warmth"
    elif any(w in text_corpus for w in ["resume", "cv", "curriculum vitae"]):
        doc_type = "resume"
        audience = "recruiters_hiring_managers"
        template = "minimal_premium"
        default_palette = "graphite_professional"
    elif any(w in text_corpus for w in ["research", "paper", "academic", "study", "thesis", "journal"]):
        doc_type = "research_paper"
        audience = "academics_researchers"
        template = "academic"
        default_palette = "graphite_professional"
    elif any(w in text_corpus for w in ["report", "quarterly", "business", "proposal", "strategic"]):
        doc_type = "business_report"
        audience = "executives_management"
        template = "executive"
        default_palette = "executive_blue"
    elif any(w in text_corpus for w in ["portfolio", "showcase", "creative"]):
        doc_type = "portfolio"
        audience = "clients_public"
        template = "dark_cinematic"
        default_palette = "midnight_tech"
    elif any(w in text_corpus for w in ["lecture", "college", "university", "student", "class"]):
        doc_type = "college_presentation"
        audience = "students_educators"
        template = "technology"
        default_palette = "modern_vibrant"
    else:
        # Default technical project
        doc_type = "technical_project"
        audience = "engineers_technical_leads"
        template = "technology"
        default_palette = "midnight_tech" if is_dark_requested else "executive_blue"

    # 3. Resolve Palette
    if not selected_palette_key:
        if existing_spec and not is_dark_requested:
            selected_palette_key = existing_spec.palette_name
        else:
            selected_palette_key = default_palette

    palette_obj = PALETTES.get(selected_palette_key, PALETTES["executive_blue"])
    palette_dict = {
        "primary": palette_obj.primary,
        "secondary": palette_obj.secondary,
        "accent": palette_obj.accent,
        "highlight": palette_obj.highlight,
        "background": palette_obj.background,
        "text": palette_obj.text,
        "card_bg": palette_obj.card_bg,
        "border": palette_obj.border,
    }

    # 4. Resolve Template & Typography
    template_config = TEMPLATES.get(template, TEMPLATES["technology"])
    heading_font = template_config.get("font_heading", "Calibri")
    body_font = template_config.get("font_body", "Calibri")

    typo = TypographySpec(
        heading_font=heading_font,
        body_font=body_font,
        title_size=40 if doc_format == "pptx" else 26,
        subtitle_size=18 if doc_format == "pptx" else 13,
        h1_size=28 if doc_format == "pptx" else 16,
        h2_size=20 if doc_format == "pptx" else 13,
        h3_size=16 if doc_format == "pptx" else 11,
        body_size=14 if doc_format == "pptx" else 10,
        caption_size=10 if doc_format == "pptx" else 9,
    )

    layout = "standard_widescreen" if doc_format == "pptx" else "standard_letter"

    return DesignSpec(
        document_type=doc_type,
        target_audience=audience,
        style=template,
        template=template,
        palette_name=selected_palette_key,
        palette=palette_dict,
        typography=asdict(typo),
        layout=layout,
        is_dark=palette_obj.is_dark,
    )
