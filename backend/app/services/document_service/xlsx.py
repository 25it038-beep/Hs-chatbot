from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter
from typing import List, Dict, Optional

def generate_xlsx(title: str, sheets_data: Dict[str, List[List]], output_path: str):
    wb = Workbook()
    
    # Remove default sheet
    wb.remove(wb.active)
    
    for sheet_name, data in sheets_data.items():
        ws = wb.create_sheet(title=sheet_name[:31])
        
        for row_idx, row in enumerate(data, 1):
            for col_idx, value in enumerate(row, 1):
                cell = ws.cell(row=row_idx, column=col_idx, value=value)
                if row_idx == 1:
                    cell.font = Font(bold=True)
                    cell.fill = PatternFill(start_color="CCCCCC", end_color="CCCCCC", fill_type="solid")
                    cell.alignment = Alignment(horizontal="center")
        
        # Auto-size columns
        for col in ws.columns:
            max_length = 0
            column = col[0].column_letter
            for cell in col:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            adjusted_width = min(max_length + 2, 50)
            ws.column_dimensions[column].width = adjusted_width
    
    wb.save(output_path)
    return output_path

def generate_simple_xlsx(sheet_name: str, data: List[List], output_path: str):
    wb = Workbook()
    ws = wb.active
    ws.title = sheet_name[:31]
    
    for row in data:
        ws.append(row)
    
    wb.save(output_path)
    return output_path
