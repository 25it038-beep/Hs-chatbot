from reportlab.lib.pagesizes import LETTER
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch
import os
from typing import List, Dict, Optional

def generate_pdf(title: str, sections: List[Dict], output_path: str, author: Optional[str] = None):
    doc = SimpleDocTemplate(output_path, pagesize=LETTER, leftMargin=72, rightMargin=72, topMargin=72, bottomMargin=72)
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='TitleCenter', parent=styles['Title'], alignment=1, spaceAfter=24))
    story = []
    
    story.append(Paragraph(title, styles['TitleCenter']))
    story.append(Spacer(1, 12))
    
    if author:
        story.append(Paragraph(f"Author: {author}", styles['Normal']))
        story.append(Spacer(1, 24))
    
    for sec in sections:
        heading = sec.get('heading', '')
        content = sec.get('content', '')
        story.append(Paragraph(heading, styles['Heading2']))
        story.append(Spacer(1, 6))
        
        # Split content into paragraphs
        for para in content.split('\n\n'):
            story.append(Paragraph(para.replace('\n', '<br/>'), styles['Normal']))
            story.append(Spacer(1, 6))
        
        # Handle tables
        if 'table' in sec:
            data = sec['table']
            t = Table(data)
            t.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.grey),
                ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
                ('ALIGN', (0,0), (-1,-1), 'LEFT'),
                ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
                ('FONTSIZE', (0,0), (-1,0), 10),
                ('BOTTOMPADDING', (0,0), (-1,0), 12),
                ('BACKGROUND', (0,1), (-1,-1), colors.beige),
                ('GRID', (0,0), (-1,-1), 1, colors.black),
            ]))
            story.append(t)
            story.append(Spacer(1, 12))
        
        story.append(PageBreak())
    
    doc.build(story)
    return output_path

def generate_simple_pdf(text: str, output_path: str, title: str = "Document"):
    doc = SimpleDocTemplate(output_path, pagesize=LETTER)
    styles = getSampleStyleSheet()
    story = [Paragraph(title, styles['Title']), Spacer(1, 12)]
    for para in text.split('\n\n'):
        story.append(Paragraph(para.replace('\n', '<br/>'), styles['Normal']))
        story.append(Spacer(1, 12))
    doc.build(story)
    return output_path
