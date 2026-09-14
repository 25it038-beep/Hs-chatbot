"""Premium Excel (XLSX) Spreadsheet Design Engine for HSBot.

Renders executive-grade workbooks with:
- Top KPI Summary Banner (KPI cards with large figures and labels)
- Themed table headers matching palette primary colors
- Clean zebra striping and thin borders
- Professional number, currency, and percentage formatting
- Auto-adjusted column widths with padding
"""

import os
from typing import List, Dict, Union, Any, Optional
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

from app.services.document_service.design_system import (
    DesignSpec, ColorPalette, hex_to_rgb, infer_design_spec
)


def _to_openpyxl_hex(hex_str: str) -> str:
    """Strips '#' from hex string for openpyxl ARGB/RGB format."""
    return hex_str.lstrip("#").upper()


def generate_xlsx(
    title: str,
    sheets_data: Dict[str, List[List[Any]]],
    output_path: str,
    design_spec: Optional[DesignSpec] = None,
    kpis: Optional[List[Dict[str, Any]]] = None,
) -> str:
    """Generates an executive-styled Excel workbook with one or more sheets."""
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    wb = Workbook()
    wb.remove(wb.active)  # Remove default blank sheet

    # Resolve design spec
    if not design_spec:
        design_spec = infer_design_spec(title, "xlsx")

    palette = design_spec.palette
    primary_hex = _to_openpyxl_hex(palette["primary"])
    accent_hex = _to_openpyxl_hex(palette["accent"])
    card_bg_hex = _to_openpyxl_hex(palette["card_bg"] if palette["card_bg"] != "#FFFFFF" else "F8FAFC")
    border_hex = _to_openpyxl_hex(palette["border"])

    header_fill = PatternFill(start_color=primary_hex, end_color=primary_hex, fill_type="solid")
    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    zebra_fill = PatternFill(start_color=card_bg_hex, end_color=card_bg_hex, fill_type="solid")
    regular_font = Font(name="Calibri", size=10, color="0F172A")
    kpi_val_font = Font(name="Calibri", size=16, bold=True, color=accent_hex)
    kpi_lbl_font = Font(name="Calibri", size=9, bold=True, color=primary_hex)

    thin_border = Border(
        left=Side(style='thin', color=border_hex),
        right=Side(style='thin', color=border_hex),
        top=Side(style='thin', color=border_hex),
        bottom=Side(style='thin', color=border_hex),
    )

    for sheet_name, rows in sheets_data.items():
        clean_sheet_name = (sheet_name or "Sheet1")[:31].replace(":", "").replace("/", "").replace("\\", "").replace("?", "").replace("*", "").replace("[", "").replace("]", "")
        ws = wb.create_sheet(title=clean_sheet_name or "Sheet1")
        ws.views.sheetView[0].showGridLines = True

        current_row = 1

        # 1. Top KPI Summary Cards (if provided or if table has numerical summary)
        if kpis and len(kpis) > 0 and current_row == 1:
            for k_idx, k_item in enumerate(kpis[:4]):
                start_col = 1 + (k_idx * 3)
                end_col = start_col + 2

                # Merge cell for KPI Value
                ws.merge_cells(start_row=1, start_column=start_col, end_row=1, end_column=end_col)
                c_val = ws.cell(row=1, column=start_col, value=k_item.get("metric", k_item.get("value", "N/A")))
                c_val.font = kpi_val_font
                c_val.alignment = Alignment(horizontal="center", vertical="center")
                c_val.fill = zebra_fill
                c_val.border = thin_border

                # Merge cell for KPI Label
                ws.merge_cells(start_row=2, start_column=start_col, end_row=2, end_column=end_col)
                c_lbl = ws.cell(row=2, column=start_col, value=k_item.get("label", "Metric"))
                c_lbl.font = kpi_lbl_font
                c_lbl.alignment = Alignment(horizontal="center", vertical="center")
                c_lbl.fill = zebra_fill
                c_lbl.border = thin_border

            current_row = 4  # spacer row

        # 2. Render Data Table
        if rows:
            for r_offset, row in enumerate(rows):
                row_idx = current_row + r_offset
                is_header = (r_offset == 0)

                for col_idx, val in enumerate(row, 1):
                    cell = ws.cell(row=row_idx, column=col_idx, value=val)
                    cell.border = thin_border

                    if is_header:
                        cell.fill = header_fill
                        cell.font = header_font
                        cell.alignment = Alignment(horizontal="center", vertical="center")
                    else:
                        cell.font = regular_font
                        if r_offset % 2 == 0:
                            cell.fill = zebra_fill

                        # Data Formatting
                        if isinstance(val, (int, float)):
                            cell.alignment = Alignment(horizontal="right", vertical="center")
                            # Detect currency or decimal
                            if isinstance(val, float) and 0 < val <= 1.0 and ("rate" in str(row[0]).lower() or "%" in str(row[0])):
                                cell.number_format = '0.0%'
                            elif isinstance(val, (int, float)) and val > 100 and any(kw in str(rows[0][col_idx-1]).lower() for kw in ["cost", "price", "budget", "amount", "revenue"]):
                                cell.number_format = '$#,##0.00'
                            elif isinstance(val, float):
                                cell.number_format = '#,##0.00'
                            else:
                                cell.number_format = '#,##0'
                        else:
                            cell.alignment = Alignment(horizontal="left", vertical="center")

        # 3. Auto-size columns with sensible limits
        for col in ws.columns:
            max_len = 0
            col_letter = get_column_letter(col[0].column)
            for cell in col:
                val_str = str(cell.value or "")
                max_len = max(max_len, len(val_str))
            ws.column_dimensions[col_letter].width = max(max_len + 4, 14)

    wb.save(output_path)
    return output_path


def generate_simple_xlsx(sheet_name: str, data: List[List[Any]], output_path: str) -> str:
    """Generates an Excel workbook from a single 2D array."""
    return generate_xlsx(title=sheet_name, sheets_data={sheet_name: data}, output_path=output_path)
