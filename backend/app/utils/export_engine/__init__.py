"""SAMS-FR Multi-Format Document Export Engine.

Provides unified, secure, memory-efficient generators for PDF, Excel (.xlsx),
and CSV reports across SAMS-FR portals.
"""

from __future__ import annotations

import io
from typing import Any, Sequence

from app.utils.export_engine.csv_builder import CSVReportBuilder, sanitize_csv_cell
from app.utils.export_engine.excel_builder import ExcelReportBuilder
from app.utils.export_engine.exceptions import (
    ExportEngineError,
    ExportRenderingError,
    ExportValidationError,
)
from app.utils.export_engine.pdf_builder import PDFReportBuilder

MIME_XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
MIME_PDF = "application/pdf"
MIME_CSV = "text/csv; charset=utf-8"


def generate_export(
    format_type: str,
    headers: Sequence[str],
    rows: Sequence[Sequence[Any]] | None = None,
    title: str | None = None,
    subtitle: str | None = None,
    metadata: dict[str, Any] | Sequence[tuple[str, Any]] | None = None,
    summary: dict[str, Any] | Sequence[tuple[str, Any]] | None = None,
    base_filename: str = "report",
    sheet_name: str = "Report",
    orientation: str = "auto",
) -> tuple[io.BytesIO, str, str]:
    """Unified dispatcher to generate exports in Excel, PDF, or CSV format.

    Args:
        format_type: 'xlsx' (or 'excel'), 'pdf', or 'csv'.
        headers: Column headers list.
        rows: Data rows (list of lists/tuples).
        title: Report main title.
        subtitle: Secondary subtitle.
        metadata: Key-value metadata block.
        summary: Key-value summary block.
        base_filename: Base filename without extension.
        sheet_name: Excel worksheet title.
        orientation: PDF orientation ('auto', 'portrait', 'landscape').

    Returns:
        tuple of (stream: io.BytesIO, mimetype: str, filename: str)
    """
    fmt = (format_type or "").strip().lower()

    if fmt in ("xlsx", "excel"):
        builder = ExcelReportBuilder(
            headers=headers,
            rows=rows,
            title=title,
            subtitle=subtitle,
            metadata=metadata,
            summary=summary,
            sheet_name=sheet_name,
        )
        stream = builder.build_stream()
        mimetype = MIME_XLSX
        filename = f"{base_filename}.xlsx"

    elif fmt == "pdf":
        builder = PDFReportBuilder(
            headers=headers,
            rows=rows,
            title=title,
            subtitle=subtitle,
            metadata=metadata,
            summary=summary,
            orientation=orientation,
        )
        stream = builder.build_stream()
        mimetype = MIME_PDF
        filename = f"{base_filename}.pdf"

    elif fmt == "csv":
        builder = CSVReportBuilder(
            headers=headers,
            rows=rows,
            title=title,
            metadata=metadata,
            summary=summary,
        )
        stream = builder.build_stream(include_bom=True)
        mimetype = MIME_CSV
        filename = f"{base_filename}.csv"

    else:
        raise ExportValidationError(
            f"Unsupported export format '{format_type}'. Must be 'xlsx', 'pdf', or 'csv'."
        )

    return stream, mimetype, filename


__all__ = [
    "CSVReportBuilder",
    "ExcelReportBuilder",
    "ExportEngineError",
    "ExportRenderingError",
    "ExportValidationError",
    "MIME_CSV",
    "MIME_PDF",
    "MIME_XLSX",
    "PDFReportBuilder",
    "generate_export",
    "sanitize_csv_cell",
]
