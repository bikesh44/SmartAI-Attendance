"""Unit and Integration Tests for SAMS-FR Shared Export Engine.

Verifies Excel (.xlsx), PDF (.pdf), and CSV (.csv) document generation,
memory streaming, formula injection defense, empty dataset handling,
and custom exceptions.
"""

import io
import unittest
from openpyxl import load_workbook

from app.utils.export_engine import (
    CSVReportBuilder,
    ExcelReportBuilder,
    ExportValidationError,
    MIME_CSV,
    MIME_PDF,
    MIME_XLSX,
    PDFReportBuilder,
    generate_export,
    sanitize_csv_cell,
)


class TestCSVReportBuilder(unittest.TestCase):
    """Test suite for CSVReportBuilder."""

    def test_basic_csv_generation(self):
        headers = ["ID", "Name", "Score", "Status"]
        rows = [
            [1, "Alice Smith", 92.5, "Pass"],
            [2, "Bob Jones", 45.0, "Fail"],
        ]
        builder = CSVReportBuilder(
            headers=headers,
            rows=rows,
            title="Student Scores",
            metadata={"Course": "CS101", "Semester": 4},
            summary={"Total Students": 2, "Pass Rate": "50%"},
        )
        csv_str = builder.build_string()

        self.assertIn("Student Scores", csv_str)
        self.assertIn("Course:", csv_str)
        self.assertIn("CS101", csv_str)
        self.assertIn("Alice Smith", csv_str)
        self.assertIn("Bob Jones", csv_str)
        self.assertIn("ID,Name,Score,Status", csv_str)
        self.assertIn("Pass Rate:", csv_str)

    def test_formula_injection_defense(self):
        """Values starting with formula trigger chars (=, +, -, @, \\t, \\r) must be escaped."""
        self.assertEqual(sanitize_csv_cell("=cmd|' /C calc'!A0"), "'=cmd|' /C calc'!A0")
        self.assertEqual(sanitize_csv_cell("+12345"), "'+12345")
        self.assertEqual(sanitize_csv_cell("-100"), "'-100")
        self.assertEqual(sanitize_csv_cell("@SUM(A1:A10)"), "'@SUM(A1:A10)")
        self.assertEqual(sanitize_csv_cell("Normal Text"), "Normal Text")
        self.assertEqual(sanitize_csv_cell(None), "")
        self.assertEqual(sanitize_csv_cell(True), "Yes")
        self.assertEqual(sanitize_csv_cell(False), "No")

        builder = CSVReportBuilder(
            headers=["Command", "Formula"],
            rows=[["=2+2", "@alert(1)"]],
        )
        csv_str = builder.build_string()
        self.assertIn("'=2+2", csv_str)
        self.assertIn("'@alert(1)", csv_str)

    def test_empty_dataset_handling(self):
        builder = CSVReportBuilder(headers=["ColA", "ColB"], rows=[])
        csv_str = builder.build_string()
        self.assertIn("ColA,ColB", csv_str)
        self.assertIn("No records found.", csv_str)

    def test_utf8_bom_and_stream(self):
        builder = CSVReportBuilder(
            headers=["Student", "Note"],
            rows=[["Renée Müller", "Übung bestanden: 95%"]],
        )
        raw_bytes = builder.build_bytes(include_bom=True)
        self.assertTrue(raw_bytes.startswith(b"\xef\xbb\xbf"))

        stream = builder.build_stream(include_bom=True)
        self.assertIsInstance(stream, io.BytesIO)
        stream_data = stream.read()
        self.assertEqual(raw_bytes, stream_data)
        self.assertIn("Renée Müller".encode("utf-8"), stream_data)

    def test_invalid_headers_raises_validation_error(self):
        with self.assertRaises(ExportValidationError):
            CSVReportBuilder(headers=[])


class TestExcelReportBuilder(unittest.TestCase):
    """Test suite for ExcelReportBuilder."""

    def test_valid_xlsx_output_and_parsing(self):
        headers = ["Roll No", "Name", "Attendance %", "Status"]
        rows = [
            ["CS001", "Aarav Sharma", "92%", "Present"],
            ["CS002", "Diya Patel", "64%", "Needs Attention"],
        ]
        builder = ExcelReportBuilder(
            headers=headers,
            rows=rows,
            title="Class Attendance Report",
            subtitle="Semester 4 - Section A",
            metadata={"Faculty": "Dr. Farhan Das", "Course": "CS101"},
            summary={"Total Enrolled": 2, "Average": "78%"},
            sheet_name="Attendance",
        )
        xlsx_bytes = builder.build_bytes()

        # Check XLSX ZIP archive magic bytes
        self.assertTrue(xlsx_bytes.startswith(b"PK\x03\x04"))

        # Verify openpyxl can load and read the structure
        stream = io.BytesIO(xlsx_bytes)
        wb = load_workbook(stream)
        self.assertIn("Attendance", wb.sheetnames)
        ws = wb["Attendance"]

        # Check title and content
        self.assertEqual(ws["A1"].value, "Class Attendance Report")
        self.assertEqual(ws["A2"].value, "Semester 4 - Section A")

        # Header row is at row 7
        header_values = [cell.value for cell in ws[7]]
        self.assertEqual(header_values, headers)

        # Check header styling (brand navy color)
        header_cell = ws["A7"]
        self.assertEqual(header_cell.fill.fgColor.rgb, "001F4E78")
        self.assertEqual(header_cell.font.color.rgb, "00FFFFFF")
        self.assertTrue(header_cell.font.bold)

        # Verify data rows
        row1_values = [ws.cell(row=8, column=c).value for c in range(1, 5)]
        self.assertEqual(row1_values, ["CS001", "Aarav Sharma", "92%", "Present"])

        # Check freeze panes
        self.assertEqual(ws.freeze_panes, "A8")

    def test_empty_dataset_handling(self):
        builder = ExcelReportBuilder(
            headers=["Course Code", "Course Name", "Credits"],
            rows=[],
            title="Empty Course List",
        )
        xlsx_bytes = builder.build_bytes()
        self.assertTrue(xlsx_bytes.startswith(b"PK\x03\x04"))

        wb = load_workbook(io.BytesIO(xlsx_bytes))
        ws = wb.active
        # Row 1 is title, Row 2 is headers, Row 3 is empty notice
        self.assertEqual(ws["A2"].value, "Course Code")
        self.assertIn("No records found", str(ws["A3"].value))

    def test_special_characters_and_sheet_name_sanitization(self):
        # Sheet name with forbidden characters and length > 31
        builder = ExcelReportBuilder(
            headers=["Subject", "Grade"],
            rows=[["Algorithms & Data Structures (CS:201) [Lab]", "A+"]],
            sheet_name="Test:Invalid/Sheet*Name?[TooLongToFitInExcel]",
        )
        wb = builder.build_workbook()
        self.assertNotIn(":", wb.active.title)
        self.assertNotIn("/", wb.active.title)
        self.assertNotIn("*", wb.active.title)
        self.assertLessEqual(len(wb.active.title), 31)

    def test_invalid_headers_raises_validation_error(self):
        with self.assertRaises(ExportValidationError):
            ExcelReportBuilder(headers=[])


class TestPDFReportBuilder(unittest.TestCase):
    """Test suite for PDFReportBuilder."""

    def test_valid_pdf_generation(self):
        headers = ["Code", "Course Name", "Credits", "Grade", "Status"]
        rows = [
            ["CS101", "Data Structures", 4, "A", "Pass"],
            ["CS102", "Computer Networks", 4, "B+", "Pass"],
            ["CS103", "Operating Systems", 3, "F", "Fail"],
        ]
        builder = PDFReportBuilder(
            headers=headers,
            rows=rows,
            title="Official Academic Grade Card",
            subtitle="Spring Semester 2025",
            metadata={
                "Student": "Ankit Kumar",
                "Enrollment No": "STU2024001",
                "SGPA": "8.42",
                "CGPA": "8.26",
            },
            summary={"Total Credits": 11, "Academic Standing": "Good Standing"},
        )
        pdf_bytes = builder.build_bytes()

        # PDF magic bytes
        self.assertTrue(pdf_bytes.startswith(b"%PDF-"))
        self.assertGreater(len(pdf_bytes), 2000)

        # Stream verification
        stream = builder.build_stream()
        self.assertIsInstance(stream, io.BytesIO)
        stream_bytes = stream.read()
        self.assertTrue(stream_bytes.startswith(b"%PDF-"))
        self.assertGreater(len(stream_bytes), 2000)

    def test_multi_page_table_with_repeated_headers(self):
        """Long tables (120 rows) must paginate and render cleanly without errors."""
        headers = ["#", "Enrollment No", "Student Name", "Attended", "Absent", "Attendance %"]
        rows = [
            [i, f"STU2024{i:03d}", f"Student Number {i}", 38, 2, "95%"]
            for i in range(1, 121)
        ]
        builder = PDFReportBuilder(
            headers=headers,
            rows=rows,
            title="Annual Attendance Register",
            subtitle="Academic Year 2024-2025",
        )
        pdf_bytes = builder.build_bytes()
        self.assertTrue(pdf_bytes.startswith(b"%PDF-"))
        self.assertGreater(len(pdf_bytes), 8000)

    def test_empty_dataset_handling(self):
        builder = PDFReportBuilder(
            headers=["Header 1", "Header 2"],
            rows=[],
            title="Empty Test Report",
        )
        pdf_bytes = builder.build_bytes()
        self.assertTrue(pdf_bytes.startswith(b"%PDF-"))

    def test_special_characters_escaping(self):
        """XML/HTML characters (<, >, &, \", ') must be escaped in PDF Paragraph flowables."""
        headers = ["Topic <Important>", "Description & Details"]
        rows = [
            ["C++ & OOP <Basics>", "Memory 'allocation' & \"deallocation\" in C++"],
        ]
        builder = PDFReportBuilder(
            headers=headers,
            rows=rows,
            title="Programming <CS101> & Algorithms",
            subtitle="Syntax & Semantics",
            metadata={"Condition": "x < y && y > z"},
        )
        pdf_bytes = builder.build_bytes()
        self.assertTrue(pdf_bytes.startswith(b"%PDF-"))

    def test_invalid_headers_raises_validation_error(self):
        with self.assertRaises(ExportValidationError):
            PDFReportBuilder(headers=[])


class TestUnifiedExportDispatcher(unittest.TestCase):
    """Test suite for the unified generate_export dispatcher."""

    def setUp(self):
        self.headers = ["ID", "Name", "Score"]
        self.rows = [[101, "Jane Doe", 98], [102, "John Smith", 84]]
        self.metadata = {"Class": "CSE-A"}

    def test_dispatch_excel(self):
        stream, mimetype, filename = generate_export(
            format_type="xlsx",
            headers=self.headers,
            rows=self.rows,
            title="Test Excel",
            metadata=self.metadata,
            base_filename="student_scores",
        )
        self.assertEqual(mimetype, MIME_XLSX)
        self.assertEqual(filename, "student_scores.xlsx")
        self.assertTrue(stream.read().startswith(b"PK\x03\x04"))

    def test_dispatch_pdf(self):
        stream, mimetype, filename = generate_export(
            format_type="pdf",
            headers=self.headers,
            rows=self.rows,
            title="Test PDF",
            metadata=self.metadata,
            base_filename="student_scores",
        )
        self.assertEqual(mimetype, MIME_PDF)
        self.assertEqual(filename, "student_scores.pdf")
        self.assertTrue(stream.read().startswith(b"%PDF-"))

    def test_dispatch_csv(self):
        stream, mimetype, filename = generate_export(
            format_type="csv",
            headers=self.headers,
            rows=self.rows,
            title="Test CSV",
            metadata=self.metadata,
            base_filename="student_scores",
        )
        self.assertEqual(mimetype, MIME_CSV)
        self.assertEqual(filename, "student_scores.csv")
        self.assertTrue(stream.read().startswith(b"\xef\xbb\xbf"))

    def test_unsupported_format_raises_validation_error(self):
        with self.assertRaises(ExportValidationError):
            generate_export(
                format_type="docx",
                headers=self.headers,
                rows=self.rows,
            )


if __name__ == "__main__":
    unittest.main()
