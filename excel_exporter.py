"""
Excel Exporter Module
Exports extracted resume data to Excel format.
Only exports: Name | Email | Phone Number | FileName
No errors included in export.
"""

from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from openpyxl.utils import get_column_letter
import io
from typing import List, Dict, Any


def export_to_excel(data: List[Dict[str, Any]]) -> bytes:
    """
    Export extraction results to Excel file.
    Only exports: Name | Email | Phone Number | FileName
    Errors are NOT included in the export.
    """
    wb = Workbook()
    ws = wb.active
    ws.title = "Candidates"
    
    header_font = Font(bold=True, size=11)
    header_alignment = Alignment(horizontal="center", vertical="center")
    cell_alignment = Alignment(horizontal="left", vertical="center")
    
    thin_border = Border(
        left=Side(style='thin', color='000000'),
        right=Side(style='thin', color='000000'),
        top=Side(style='thin', color='000000'),
        bottom=Side(style='thin', color='000000')
    )
    
    headers = ["Name", "Email", "Phone Number", "FileName"]
    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=header)
        cell.font = header_font
        cell.alignment = header_alignment
        cell.border = thin_border
    
    for row_idx, item in enumerate(data, 2):
        name_val = item.get('name') or ""
        email_val = item.get('email') or ""
        phone_val = item.get('phone') or ""
        filename_val = item.get('filename', '')
        
        name_cell = ws.cell(row=row_idx, column=1, value=name_val)
        name_cell.alignment = cell_alignment
        name_cell.border = thin_border
        
        email_cell = ws.cell(row=row_idx, column=2, value=email_val)
        email_cell.alignment = cell_alignment
        email_cell.border = thin_border
        
        phone_cell = ws.cell(row=row_idx, column=3, value=phone_val)
        phone_cell.alignment = cell_alignment
        phone_cell.border = thin_border
        
        file_cell = ws.cell(row=row_idx, column=4, value=filename_val)
        file_cell.alignment = cell_alignment
        file_cell.border = thin_border
    
    column_widths = [30, 35, 20, 40]
    for col, width in enumerate(column_widths, 1):
        ws.column_dimensions[get_column_letter(col)].width = width
    
    ws.freeze_panes = "A2"
    
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    
    return output.getvalue()


def get_export_filename() -> str:
    """Generate export filename."""
    return "resume_extraction.xlsx"
