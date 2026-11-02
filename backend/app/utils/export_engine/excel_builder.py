"""Excel Document Builder.

Generates beautifully formatted, branded Microsoft Excel (.xlsx) workbooks
using openpyxl, featuring SAMS-FR brand palette, column auto-sizing,
alternating row zebra striping, freeze-panes, and auto-filters.
"""

from __future__ import annotations

import io
from typing import Any, Sequence

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from app.utils.export_engine.exceptions import (
    ExportRenderingError,
    ExportValidationError,
)

# SAMS-FR Institutional Brand Palette
COLOR_PRIMARY_NAVY = "1F4E78"    # Main brand header fill
COLOR_HEADER_TEXT = "FFFFFF"     # White bold text
COLOR_TITLE_BG = "0F2942"        # Title banner fill
COLOR_ROW_ALT = "F8FAFC"         # Zebra row background
COLOR_BORDER = "CBD5E1"          # Thin border gray
COLOR_LABEL = "475569"           # Metadata label dark slate
COLOR_SUCCESS_FILL = "DCFCE7"    # Light green fill for Present/Pass
COLOR_SUCCESS_TEXT = "166534"    # Dark green text
COLOR_DANGER_FILL = "FEE2E2"     # Light red fill for Absent/Fail/Low
COLOR_DANGER_TEXT = "991B1B"     # Dark red text


class ExcelReportBuilder:
    """Builds branded .xlsx Excel spreadsheets in memory."""

    def __init__(
        self,
        headers: Sequence[str],
        rows: Sequence[Sequence[Any]] | None = None,
        title: str | None = None,
        subtitle: str | None = None,
        metadata: dict[str, Any] | Sequence[tuple[str, Any]] | None = None,
        summary: dict[str, Any] | Sequence[tuple[str, Any]] | None = None,
        sheet_name: str = "Report",
    ):
        if not headers or not isinstance(headers, (list, tuple)):
            raise ExportValidationError("Excel report requires a non-empty list of headers.")

        self.headers = [str(h) for h in headers]
        self.rows = list(rows) if rows is not None else []
        self.title = str(title).strip() if title else None
        self.subtitle = str(subtitle).strip() if subtitle else None
        self.metadata = metadata
        self.summary = summary
        # Excel sheet names have a 31-character limit and forbidden characters \ / ? * : [ ]
        safe_name = "".join(c for c in sheet_name if c not in r"\/?*:[ ]")[:31].strip()
        self.sheet_name = safe_name or "Report"

    def build_workbook(self) -> Workbook:
        """Construct the styled openpyxl Workbook object."""
        try:
            wb = Workbook()
            ws = wb.active
            ws.title = self.sheet_name
            ws.views.sheetView[0].showGridLines = True

            current_row = 1
            num_cols = max(len(self.headers), 1)

            # Border definitions
            thin_border = Border(
                left=Side(style="thin", color=COLOR_BORDER),
                right=Side(style="thin", color=COLOR_BORDER),
                top=Side(style="thin", color=COLOR_BORDER),
                bottom=Side(style="thin", color=COLOR_BORDER),
            )
            header_border = Border(
                left=Side(style="thin", color="1E3A8A"),
                right=Side(style="thin", color="1E3A8A"),
                top=Side(style="medium", color="0F2942"),
                bottom=Side(style="medium", color="0F2942"),
            )

            # 1. Main Title Banner (Optional)
            if self.title:
                ws.merge_cells(
                    start_row=current_row,
                    start_column=1,
                    end_row=current_row,
                    end_column=num_cols,
                )
                cell = ws.cell(row=current_row, column=1, value=self.title)
                cell.font = Font(name="Calibri", size=14, bold=True, color="FFFFFF")
                cell.fill = PatternFill(fill_type="solid", fgColor=COLOR_TITLE_BG)
                cell.alignment = Alignment(horizontal="center", vertical="center")
                ws.row_dimensions[current_row].height = 32
                current_row += 1

            # 2. Subtitle (Optional)
            if self.subtitle:
                ws.merge_cells(
                    start_row=current_row,
                    start_column=1,
                    end_row=current_row,
                    end_column=num_cols,
                )
                cell = ws.cell(row=current_row, column=1, value=self.subtitle)
                cell.font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
                cell.fill = PatternFill(fill_type="solid", fgColor=COLOR_PRIMARY_NAVY)
                cell.alignment = Alignment(horizontal="center", vertical="center")
                ws.row_dimensions[current_row].height = 24
                current_row += 1

            # 3. Metadata Block (Optional Key-Value rows)
            if self.metadata:
                if self.title or self.subtitle:
                    current_row += 1  # Add spacing row

                items = (
                    list(self.metadata.items())
                    if isinstance(self.metadata, dict)
                    else list(self.metadata)
                )
                for key, val in items:
                    label_cell = ws.cell(row=current_row, column=1, value=f"{key}:")
                    label_cell.font = Font(name="Calibri", size=10, bold=True, color=COLOR_LABEL)
                    label_cell.alignment = Alignment(horizontal="left", vertical="center")

                    val_str = str(val if val is not None else "")
                    val_cell = ws.cell(row=current_row, column=2, value=val_str)
                    val_cell.font = Font(name="Calibri", size=10, bold=False, color="0F172A")
                    val_cell.alignment = Alignment(horizontal="left", vertical="center")
                    current_row += 1

                current_row += 1  # Blank line before table

            # 4. Table Header Row
            header_row_idx = current_row
            ws.row_dimensions[header_row_idx].height = 26

            for col_idx, header_text in enumerate(self.headers, start=1):
                cell = ws.cell(row=header_row_idx, column=col_idx, value=header_text)
                cell.font = Font(name="Calibri", size=11, bold=True, color=COLOR_HEADER_TEXT)
                cell.fill = PatternFill(fill_type="solid", fgColor=COLOR_PRIMARY_NAVY)
                cell.alignment = Alignment(horizontal="center", vertical="center")
                cell.border = header_border

            current_row += 1

            # 5. Table Data Rows
            if self.rows:
                for row_data in self.rows:
                    ws.row_dimensions[current_row].height = 20
                    is_alt = (current_row % 2 == 0)
                    row_fill = (
                        PatternFill(fill_type="solid", fgColor=COLOR_ROW_ALT)
                        if is_alt
                        else None
                    )

                    for col_idx in range(1, num_cols + 1):
                        val = row_data[col_idx - 1] if col_idx - 1 < len(row_data) else ""
                        cell = ws.cell(row=current_row, column=col_idx, value=val)
                        cell.font = Font(name="Calibri", size=10, color="1E293B")
                        cell.border = thin_border
                        if row_fill:
                            cell.fill = row_fill

                        # Smart formatting based on type and content
                        if isinstance(val, (int, float)):
                            cell.alignment = Alignment(horizontal="right", vertical="center")
                        elif isinstance(val, str) and (
                            val.endswith("%") or val in ("Pass", "Fail", "Present", "Absent", "Late", "Excellent", "Good", "Needs Attention")
                        ):
                            cell.alignment = Alignment(horizontal="center", vertical="center")
                            # Highlight specific status badges
                            upper_val = val.upper()
                            if upper_val in ("PASS", "PRESENT", "EXCELLENT"):
                                cell.font = Font(name="Calibri", size=10, bold=True, color=COLOR_SUCCESS_TEXT)
                                cell.fill = PatternFill(fill_type="solid", fgColor=COLOR_SUCCESS_FILL)
                            elif upper_val in ("FAIL", "ABSENT", "NEEDS ATTENTION"):
                                cell.font = Font(name="Calibri", size=10, bold=True, color=COLOR_DANGER_TEXT)
                                cell.fill = PatternFill(fill_type="solid", fgColor=COLOR_DANGER_FILL)
                        else:
                            cell.alignment = Alignment(horizontal="left", vertical="center")

                    current_row += 1
            else:
                # Empty dataset notice
                ws.row_dimensions[current_row].height = 24
                ws.merge_cells(
                    start_row=current_row,
                    start_column=1,
                    end_row=current_row,
                    end_column=num_cols,
                )
                cell = ws.cell(
                    row=current_row,
                    column=1,
                    value="No records found matching the specified criteria.",
                )
                cell.font = Font(name="Calibri", size=10, italic=True, color="64748B")
                cell.alignment = Alignment(horizontal="center", vertical="center")
                cell.border = thin_border
                current_row += 1

            # 6. Summary Block (Optional)
            if self.summary:
                current_row += 1
                summary_items = (
                    list(self.summary.items())
                    if isinstance(self.summary, dict)
                    else list(self.summary)
                )
                for key, val in summary_items:
                    k_cell = ws.cell(row=current_row, column=1, value=f"{key}:")
                    k_cell.font = Font(name="Calibri", size=10, bold=True, color=COLOR_PRIMARY_NAVY)
                    k_cell.alignment = Alignment(horizontal="left", vertical="center")

                    v_cell = ws.cell(row=current_row, column=2, value=str(val if val is not None else ""))
                    v_cell.font = Font(name="Calibri", size=10, bold=True, color="0F172A")
                    v_cell.alignment = Alignment(horizontal="left", vertical="center")
                    current_row += 1

            # 7. Auto-adjust Column Widths (min 12, max 45)
            for col in ws.columns:
                col_letter = get_column_letter(col[0].column)
                max_len = 0
                for cell in col:
                    # Skip merged cells from width calculation
                    if cell.coordinate in ws.merged_cells:
                        continue
                    if cell.value is not None:
                        val_str = str(cell.value)
                        max_len = max(max_len, len(val_str))
                ws.column_dimensions[col_letter].width = max(12, min(max_len + 4, 45))

            # 8. Freeze header row & apply auto-filter
            ws.freeze_panes = f"A{header_row_idx + 1}"
            last_col_letter = get_column_letter(num_cols)
            last_data_row = max(header_row_idx + len(self.rows), header_row_idx)
            ws.auto_filter.ref = f"A{header_row_idx}:{last_col_letter}{last_data_row}"

            return wb
        except Exception as exc:
            if isinstance(exc, ExportValidationError):
                raise
            raise ExportRenderingError(f"Failed to generate Excel workbook: {exc}") from exc

    def build_bytes(self) -> bytes:
        """Render the complete Excel workbook to in-memory bytes."""
        wb = self.build_workbook()
        buf = io.BytesIO()
        wb.save(buf)
        return buf.getvalue()

    def build_stream(self) -> io.BytesIO:
        """Render the complete Excel workbook into an in-memory BytesIO stream positioned at 0."""
        stream = io.BytesIO(self.build_bytes())
        stream.seek(0)
        return stream
