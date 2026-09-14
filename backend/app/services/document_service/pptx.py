import os
from typing import List, Dict, Optional
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN


def generate_pptx(
    title: str,
    slides: List[Dict],
    output_path: str,
    subtitle: Optional[str] = None,
) -> str:
    """Generates a professionally structured PowerPoint presentation."""
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    prs = Presentation()
    prs.slide_width = Inches(13.333)  # 16:9 widescreen
    prs.slide_height = Inches(7.5)

    # Theme colors
    PRIMARY = RGBColor(15, 23, 42)     # #0F172A
    SECONDARY = RGBColor(59, 130, 246) # #3B82F6
    TEXT_DARK = RGBColor(51, 65, 85)   # #334155
    MUTED = RGBColor(100, 116, 139)    # #64748B

    # Slide 1: Title Slide (Layout 0)
    title_layout = prs.slide_layouts[0]
    slide = prs.slides.add_slide(title_layout)

    title_shape = slide.shapes.title
    title_shape.text = title
    title_p = title_shape.text_frame.paragraphs[0]
    title_p.font.size = Pt(44)
    title_p.font.bold = True
    title_p.font.color.rgb = PRIMARY

    if slide.placeholders and len(slide.placeholders) > 1:
        sub_shape = slide.placeholders[1]
        sub_text = subtitle or "Created with HSBot"
        sub_shape.text = sub_text
        sub_p = sub_shape.text_frame.paragraphs[0]
        sub_p.font.size = Pt(20)
        sub_p.font.color.rgb = MUTED

    # Content Slides
    for i, slide_data in enumerate(slides, 1):
        s_title = slide_data.get("title", f"Slide {i+1}")
        s_content = slide_data.get("content", [])

        # Layout 1: Title & Content
        content_layout = prs.slide_layouts[1]
        c_slide = prs.slides.add_slide(content_layout)

        # Title
        c_title_shape = c_slide.shapes.title
        c_title_shape.text = s_title
        c_p = c_title_shape.text_frame.paragraphs[0]
        c_p.font.size = Pt(32)
        c_p.font.bold = True
        c_p.font.color.rgb = PRIMARY

        # Body
        body_shape = c_slide.placeholders[1]
        tf = body_shape.text_frame
        tf.word_wrap = True

        if isinstance(s_content, str):
            points = [p.strip().lstrip("-*• ") for p in s_content.split("\n") if p.strip()]
        else:
            points = list(s_content)

        if not points:
            points = ["Key insight and analysis."]

        tf.clear()
        for idx, pt in enumerate(points):
            p = tf.paragraphs[0] if idx == 0 else tf.add_paragraph()
            p.text = str(pt)
            p.font.size = Pt(18)
            p.font.color.rgb = TEXT_DARK
            p.space_after = Pt(14)
            p.level = 0

    prs.save(output_path)
    return output_path


def generate_simple_pptx(title: str, bullet_points: List[str], output_path: str) -> str:
    """Generates a presentation from a list of bullet points or sections."""
    slides = []
    chunk_size = 4
    for i in range(0, max(len(bullet_points), 1), chunk_size):
        chunk = bullet_points[i:i + chunk_size]
        slide_num = (i // chunk_size) + 1
        slides.append({
            "title": f"Key Discussion Points ({slide_num})",
            "content": chunk or ["Information point."],
        })

    if not slides:
        slides = [{"title": "Overview", "content": ["Introduction to the topic."]}]

    return generate_pptx(title=title, slides=slides, output_path=output_path)
