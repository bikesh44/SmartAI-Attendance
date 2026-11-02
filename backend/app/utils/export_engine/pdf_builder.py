"""PDF Document Builder.

Generates beautiful, print-ready, professional PDF documents using ReportLab.
Features SAMS-FR institutional branding, multi-page repeated table headers,
auto-wrapping cells, zebra striping, and two-pass 'Page X of Y' page numbering.
"""

from __future__ import annotations

import datetime
import html
import io
from typing import Any, Sequence

from reportlab.lib import colors
from reportlab.lib.pagesizes import landscape, letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    HRFlowable,
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.utils.export_engine.exceptions import (
    ExportRenderingError,
    ExportValidationError,
)

# SAMS-FR Brand Color Constants
COLOR_NAVY = colors.HexColor("#1F4E78")
COLOR_NAVY_DARK = colors.HexColor("#0F2942")
COLOR_BLUE = colors.HexColor("#2563EB")
COLOR_BG_ALT = colors.HexColor("#F8FAFC")
COLOR_BORDER = colors.HexColor("#E2E8F0")
COLOR_TEXT_DARK = colors.HexColor("#1E293B")
COLOR_TEXT_MUTED = colors.HexColor("#64748B")

COLOR_GREEN_TEXT = colors.HexColor("#166534")
COLOR_GREEN_FILL = colors.HexColor("#DCFCE7")
COLOR_RED_TEXT = colors.HexColor("#991B1B")
COLOR_RED_FILL = colors.HexColor("#FEE2E2")
COLOR_AMBER_TEXT = colors.HexColor("#B45309")
COLOR_AMBER_FILL = colors.HexColor("#FEF3C7")


class _NumberedCanvas(canvas.Canvas):
    """Two-pass canvas to dynamically compute and stamp total page counts ('Page X of Y')."""

    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self._saved_page_states: list[dict[str, Any]] = []

    def showPage(self) -> None:
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self) -> None:
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self._draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def _draw_page_decorations(self, page_count: int) -> None:
        self.saveState()
        page_width, _ = self._pagesize

        # Running Footer
        self.setStrokeColor(COLOR_BORDER)
        self.setLineWidth(0.75)
        self.line(36, 32, page_width - 36, 32)

        self.setFont("Helvetica", 8)
        self.setFillColor(COLOR_TEXT_MUTED)

        now_str = datetime.datetime.now().strftime("%Y-%m-%d %I:%M %p")
        footer_left = f"Generated: {now_str} | SAMS-FR Secure Document"
        self.drawString(36, 20, footer_left)

        footer_right = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(page_width - 36, 20, footer_right)

        self.restoreState()


class PDFReportBuilder:
    """Builds styled PDF reports using ReportLab in memory."""

    def __init__(
        self,
        headers: Sequence[str],
        rows: Sequence[Sequence[Any]] | None = None,
        title: str | None = None,
        subtitle: str | None = None,
        metadata: dict[str, Any] | Sequence[tuple[str, Any]] | None = None,
        summary: dict[str, Any] | Sequence[tuple[str, Any]] | None = None,
        orientation: str = "auto",  # 'auto', 'portrait', or 'landscape'
    ):
        if not headers or not isinstance(headers, (list, tuple)):
            raise ExportValidationError("PDF report requires a non-empty list of headers.")

        self.headers = [str(h) for h in headers]
        self.rows = list(rows) if rows is not None else []
        self.title = str(title).strip() if title else "SAMS-FR Report"
        self.subtitle = str(subtitle).strip() if subtitle else None
        self.metadata = metadata
        self.summary = summary
        self.orientation = orientation

    def _resolve_page_size(self) -> tuple[float, float]:
        if self.orientation == "landscape":
            return landscape(letter)
        if self.orientation == "portrait":
            return letter
        # Auto-switch to landscape if table exceeds 7 columns
        return landscape(letter) if len(self.headers) > 7 else letter

    def build_bytes(self) -> bytes:
        """Render the complete PDF document to in-memory bytes."""
        try:
            buf = io.BytesIO()
            page_size = self._resolve_page_size()
            page_width, _ = page_size
            content_width = page_width - 72  # 36pt margins left and right

            doc = SimpleDocTemplate(
                buf,
                pagesize=page_size,
                leftMargin=36,
                rightMargin=36,
                topMargin=36,
                bottomMargin=48,
            )

            styles = getSampleStyleSheet()

            # Custom typography styles
            style_banner_title = ParagraphStyle(
                "SamsBannerTitle",
                parent=styles["Normal"],
                fontName="Helvetica-Bold",
                fontSize=14,
                leading=17,
                textColor=COLOR_NAVY_DARK,
                alignment=0,  # Left
            )

            style_banner_inst = ParagraphStyle(
                "SamsBannerInst",
                parent=styles["Normal"],
                fontName="Helvetica-Bold",
                fontSize=8.5,
                leading=11,
                textColor=COLOR_BLUE,
                alignment=0,
            )

            style_subtitle = ParagraphStyle(
                "SamsSubtitle",
                parent=styles["Normal"],
                fontName="Helvetica-Bold",
                fontSize=10.5,
                leading=13,
                textColor=COLOR_TEXT_DARK,
                alignment=0,
            )

            style_header_cell = ParagraphStyle(
                "SamsHeaderCell",
                parent=styles["Normal"],
                fontName="Helvetica-Bold",
                fontSize=8.5,
                leading=11,
                textColor=colors.white,
                alignment=1,  # Center
            )

            style_data_cell = ParagraphStyle(
                "SamsDataCell",
                parent=styles["Normal"],
                fontName="Helvetica",
                fontSize=8,
                leading=10.5,
                textColor=COLOR_TEXT_DARK,
                alignment=0,  # Left
            )

            style_data_cell_center = ParagraphStyle(
                "SamsDataCellCenter",
                parent=style_data_cell,
                alignment=1,
            )

            style_data_cell_right = ParagraphStyle(
                "SamsDataCellRight",
                parent=style_data_cell,
                alignment=2,
            )

            style_meta_label = ParagraphStyle(
                "SamsMetaLabel",
                parent=styles["Normal"],
                fontName="Helvetica-Bold",
                fontSize=8,
                leading=10,
                textColor=COLOR_TEXT_MUTED,
            )

            style_meta_val = ParagraphStyle(
                "SamsMetaVal",
                parent=styles["Normal"],
                fontName="Helvetica-Bold",
                fontSize=8.5,
                leading=10.5,
                textColor=COLOR_TEXT_DARK,
            )

            story: list[Any] = []

            # 1. Header Banner Box
            banner_data = [
                [
                    Paragraph("SMART ATTENDANCE & ACADEMIC MANAGEMENT SYSTEM", style_banner_inst),
                ],
                [
                    Paragraph(html.escape(self.title), style_banner_title),
                ],
            ]
            if self.subtitle:
                banner_data.append([
                    Paragraph(html.escape(self.subtitle), style_subtitle),
                ])

            banner_table = Table(banner_data, colWidths=[content_width])
            banner_table.setStyle(TableStyle([
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 1),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ]))
            story.append(banner_table)
            story.append(Spacer(1, 8))
            story.append(HRFlowable(width="100%", thickness=1.5, color=COLOR_NAVY, spaceAfter=8))

            # 2. Metadata Grid (Optional Key-Value Cards)
            if self.metadata:
                items = (
                    list(self.metadata.items())
                    if isinstance(self.metadata, dict)
                    else list(self.metadata)
                )

                # Arrange metadata in 2 or 3 balanced columns
                num_meta_cols = 3 if len(items) >= 4 else 2
                meta_col_w = content_width / num_meta_cols

                meta_cells: list[list[Any]] = []
                row_accum: list[Any] = []

                for k, v in items:
                    v_str = html.escape(str(v if v is not None else ""))
                    k_str = html.escape(str(k))
                    cell_flow = [
                        Paragraph(k_str.upper(), style_meta_label),
                        Paragraph(v_str, style_meta_val),
                    ]
                    row_accum.append(cell_flow)
                    if len(row_accum) == num_meta_cols:
                        meta_cells.append(row_accum)
                        row_accum = []

                if row_accum:
                    while len(row_accum) < num_meta_cols:
                        row_accum.append("")
                    meta_cells.append(row_accum)

                meta_table = Table(meta_cells, colWidths=[meta_col_w] * num_meta_cols)
                meta_table.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (-1, -1), COLOR_BG_ALT),
                    ("BOX", (0, 0), (-1, -1), 0.75, COLOR_BORDER),
                    ("INNERGRID", (0, 0), (-1, -1), 0.5, COLOR_BORDER),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                    ("LEFTPADDING", (0, 0), (-1, -1), 8),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ]))
                story.append(meta_table)
                story.append(Spacer(1, 10))

            # 3. Main Data Table
            num_cols = len(self.headers)
            base_col_w = content_width / num_cols

            table_data: list[list[Any]] = []

            # Header row wrapped in Flowables
            header_row = [
                Paragraph(html.escape(h), style_header_cell)
                for h in self.headers
            ]
            table_data.append(header_row)

            # Data rows wrapped in Flowables
            if self.rows:
                for row in self.rows:
                    row_cells = []
                    for col_idx in range(num_cols):
                        val = row[col_idx] if col_idx < len(row) else ""
                        val_str = html.escape(str(val if val is not None else ""))

                        # Center-align statuses/percentages; right-align numbers; left-align text
                        upper_val = val_str.upper()
                        if val_str.endswith("%") or upper_val in (
                            "PASS", "FAIL", "PRESENT", "ABSENT", "LATE", "EXCELLENT", "GOOD", "NEEDS ATTENTION"
                        ):
                            if upper_val in ("PASS", "PRESENT", "EXCELLENT"):
                                cell_p = Paragraph(f"<b><font color='{COLOR_GREEN_TEXT.hexval()}'>{val_str}</font></b>", style_data_cell_center)
                            elif upper_val in ("FAIL", "ABSENT", "NEEDS ATTENTION"):
                                cell_p = Paragraph(f"<b><font color='{COLOR_RED_TEXT.hexval()}'>{val_str}</font></b>", style_data_cell_center)
                            elif upper_val == "LATE":
                                cell_p = Paragraph(f"<b><font color='{COLOR_AMBER_TEXT.hexval()}'>{val_str}</font></b>", style_data_cell_center)
                            else:
                                cell_p = Paragraph(val_str, style_data_cell_center)
                        elif isinstance(val, (int, float)):
                            cell_p = Paragraph(val_str, style_data_cell_right)
                        else:
                            cell_p = Paragraph(val_str, style_data_cell)

                        row_cells.append(cell_p)
                    table_data.append(row_cells)
            else:
                # Empty table notice
                empty_cell = Paragraph(
                    "<i>No records found matching the specified criteria.</i>",
                    style_data_cell_center,
                )
                table_data.append([empty_cell] + [""] * (num_cols - 1))

            main_table = Table(
                table_data,
                colWidths=[base_col_w] * num_cols,
                repeatRows=1,  # Repeats table headers across page breaks!
            )

            t_styles = [
                ("BACKGROUND", (0, 0), (-1, 0), COLOR_NAVY),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("ALIGN", (0, 0), (-1, 0), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("BOX", (0, 0), (-1, -1), 0.75, COLOR_BORDER),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, COLOR_BORDER),
            ]

            # Alternating row background for data rows
            if self.rows:
                for r_idx in range(1, len(table_data)):
                    if r_idx % 2 == 0:
                        t_styles.append(("BACKGROUND", (0, r_idx), (-1, r_idx), COLOR_BG_ALT))
            else:
                # Span empty notice across all columns
                t_styles.append(("SPAN", (0, 1), (-1, 1)))
                t_styles.append(("BACKGROUND", (0, 1), (-1, 1), COLOR_BG_ALT))

            main_table.setStyle(TableStyle(t_styles))
            story.append(main_table)

            # 4. Summary Block (Optional)
            if self.summary:
                story.append(Spacer(1, 12))
                summary_items = (
                    list(self.summary.items())
                    if isinstance(self.summary, dict)
                    else list(self.summary)
                )

                summary_cells = []
                for k, v in summary_items:
                    k_flow = Paragraph(f"<b>{html.escape(str(k))}:</b>", style_meta_label)
                    v_flow = Paragraph(f"<b>{html.escape(str(v if v is not None else ''))}</b>", style_meta_val)
                    summary_cells.append([k_flow, v_flow])

                sum_table = Table(summary_cells, colWidths=[180, content_width - 180])
                sum_table.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (-1, -1), COLOR_BG_ALT),
                    ("BOX", (0, 0), (-1, -1), 0.75, COLOR_NAVY),
                    ("INNERGRID", (0, 0), (-1, -1), 0.5, COLOR_BORDER),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                    ("LEFTPADDING", (0, 0), (-1, -1), 8),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ]))
                story.append(KeepTogether([sum_table]))

            # Build the document with two-pass NumberedCanvas
            doc.build(story, canvasmaker=_NumberedCanvas)
            return buf.getvalue()
        except Exception as exc:
            if isinstance(exc, ExportValidationError):
                raise
            raise ExportRenderingError(f"Failed to generate PDF document: {exc}") from exc

    def build_stream(self) -> io.BytesIO:
        """Render the complete PDF document into an in-memory BytesIO stream positioned at 0."""
        stream = io.BytesIO(self.build_bytes())
        stream.seek(0)
        return stream
