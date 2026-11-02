"""CSV Document Builder.

Provides memory-efficient, RFC 4180-compliant CSV generation with
formula injection defense and Unicode/UTF-8 support.
"""

from __future__ import annotations

import csv
import io
from typing import Any, Sequence

from app.utils.export_engine.exceptions import (
    ExportRenderingError,
    ExportValidationError,
)

# Characters that trigger spreadsheet formula execution when opened in Excel/Sheets
FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


def sanitize_csv_cell(val: Any) -> str:
    """Sanitize a single CSV cell value against spreadsheet formula injection.

    If a text value starts with '=', '+', '-', '@', tab, or carriage return,
    prefix it with a single quote (') so spreadsheet engines treat it strictly
    as plain text.
    """
    if val is None:
        return ""

    if isinstance(val, bool):
        return "Yes" if val else "No"

    text = str(val)

    # Protect against formula injection
    if text.startswith(FORMULA_PREFIXES):
        return f"'{text}"

    return text


class CSVReportBuilder:
    """Builds structured CSV reports in memory."""

    def __init__(
        self,
        headers: Sequence[str],
        rows: Sequence[Sequence[Any]] | None = None,
        title: str | None = None,
        metadata: dict[str, Any] | Sequence[tuple[str, Any]] | None = None,
        summary: dict[str, Any] | Sequence[tuple[str, Any]] | None = None,
    ):
        if not headers or not isinstance(headers, (list, tuple)):
            raise ExportValidationError("CSV report requires a non-empty list of headers.")

        self.headers = [str(h) for h in headers]
        self.rows = list(rows) if rows is not None else []
        self.title = str(title).strip() if title else None
        self.metadata = metadata
        self.summary = summary

    def build_string(self) -> str:
        """Render the complete CSV report as a UTF-8 string with CRLF line endings."""
        try:
            output = io.StringIO()
            writer = csv.writer(output, lineterminator="\r\n")

            # 1. Optional Main Title Banner
            if self.title:
                writer.writerow([sanitize_csv_cell(self.title)])
                writer.writerow([])

            # 2. Optional Metadata Key-Value Block
            if self.metadata:
                items = (
                    self.metadata.items()
                    if isinstance(self.metadata, dict)
                    else self.metadata
                )
                for key, val in items:
                    writer.writerow([
                        sanitize_csv_cell(f"{key}:"),
                        sanitize_csv_cell(val),
                    ])
                writer.writerow([])

            # 3. Column Headers
            writer.writerow([sanitize_csv_cell(h) for h in self.headers])

            # 4. Data Rows
            if self.rows:
                for row in self.rows:
                    writer.writerow([sanitize_csv_cell(cell) for cell in row])
            else:
                # Informative placeholder row for empty datasets
                empty_row = ["No records found."] + [""] * (len(self.headers) - 1)
                writer.writerow(empty_row)

            # 5. Optional Summary Block
            if self.summary:
                writer.writerow([])
                writer.writerow(["--- SUMMARY ---"])
                items = (
                    self.summary.items()
                    if isinstance(self.summary, dict)
                    else self.summary
                )
                for key, val in items:
                    writer.writerow([
                        sanitize_csv_cell(f"{key}:"),
                        sanitize_csv_cell(val),
                    ])

            return output.getvalue()
        except Exception as exc:
            if isinstance(exc, ExportValidationError):
                raise
            raise ExportRenderingError(f"Failed to generate CSV document: {exc}") from exc

    def build_bytes(self, include_bom: bool = True) -> bytes:
        """Render CSV report to bytes.

        Args:
            include_bom: If True, prepends UTF-8 BOM (\\xef\\xbb\\xbf) so Excel
                         displays non-ASCII Unicode characters accurately.
        """
        csv_str = self.build_string()
        raw_bytes = csv_str.encode("utf-8")
        if include_bom:
            return b"\xef\xbb\xbf" + raw_bytes
        return raw_bytes

    def build_stream(self, include_bom: bool = True) -> io.BytesIO:
        """Render CSV report into an in-memory BytesIO stream positioned at 0."""
        stream = io.BytesIO(self.build_bytes(include_bom=include_bom))
        stream.seek(0)
        return stream
