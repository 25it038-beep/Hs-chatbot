from docx import Document
from docx.shared import Inches, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
from typing import List, Dict, Optional

def generate_docx(title: str, sections: List[Dict], output_path: str, author: Optional[str] = None):
    doc = Document()
    
    # Title
    title_para = doc.add_heading(title, level=0)
    title_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    
    if author:
        doc.add_paragraph(f"Author: {author}")
    
    for sec in sections:
        heading = sec.get('heading', '')
        content = sec.get('content', '')
        
        if heading:
            doc.add_heading(heading, level=1)
        
        for para in content.split('\n\n'):
            doc.add_paragraph(para)
        
        if 'table' in sec:
            data = sec['table']
            table = doc.add_table(rows=1, cols=len(data[0]))
            table.style = 'Light Grid Accent 1'
            hdr_cells = table.rows[0].cells
            for i, header in enumerate(data[0]):
                hdr_cells[i].text = str(header)
            
            for row in data[1:]:
                row_cells = table.add_row().cells
                for i, cell in enumerate(row):
                    row_cells[i].text = str(cell)
        
        doc.add_page_break()
    
    doc.save(output_path)
    return output_path

def generate_simple_docx(title: str, text: str, output_path: str):
    doc = Document()
    doc.add_heading(title, 0)
    for para in text.split('\n\n'):
        doc.add_paragraph(para)
    doc.save(output_path)
    return output_path
