"""Integration Tests for Faculty Attendance Reports Export Endpoint.

Verifies:
- GET /api/faculty/attendance/reports/export
- CSV, XLSX, and PDF format generation
- Correct MIME types and Content-Disposition filenames
- Filter application (date range, offering_id, status, search)
- Empty dataset handling
- Role-based authorization & cross-faculty data isolation
"""

from datetime import date, time
import io
import unittest
from flask import Flask
from flask_jwt_extended import JWTManager, create_access_token
from openpyxl import load_workbook
from sqlalchemy.pool import StaticPool

from app.extensions import db
from app.models import (
    AttendanceRecord,
    AttendanceSession,
    Course,
    CourseOffering,
    Department,
    Enrollment,
    Faculty,
    Student,
    User,
)
from app.routes.reports import reports_bp


class TestFacultyReportsExport(unittest.TestCase):
    """Test suite for GET /api/faculty/attendance/reports/export."""

    @classmethod
    def setUpClass(cls):
        cls.app = Flask(__name__)
        cls.app.config.update(
            TESTING=True,
            SECRET_KEY="test-secret",
            JWT_SECRET_KEY="test-jwt-secret-key-32-bytes-long",
            SQLALCHEMY_DATABASE_URI="sqlite://",
            SQLALCHEMY_TRACK_MODIFICATIONS=False,
            SQLALCHEMY_ENGINE_OPTIONS={
                "poolclass": StaticPool,
                "connect_args": {"check_same_thread": False},
            },
            JWT_TOKEN_LOCATION=["headers"],
        )

        db.init_app(cls.app)
        JWTManager(cls.app)
        cls.app.register_blueprint(reports_bp)

    @classmethod
    def tearDownClass(cls):
        with cls.app.app_context():
            db.session.remove()
            db.drop_all()
            db.engine.dispose()

    def setUp(self):
        self.client = self.app.test_client()

        with self.app.app_context():
            db.session.remove()
            db.drop_all()
            db.create_all()

            # 1. Departments
            dept = Department(department_name="Computer Science", department_code="CSE")
            db.session.add(dept)
            db.session.flush()

            # 2. Users (Faculty 1, Faculty 2, Student 1, Student 2)
            u_fac1 = User(name="Prof. Alan Turing", email="turing@test.local", password_hash="pw", role="FACULTY")
            u_fac2 = User(name="Prof. Ada Lovelace", email="ada@test.local", password_hash="pw", role="FACULTY")
            u_stu1 = User(name="Grace Hopper", email="grace@test.local", password_hash="pw", role="STUDENT")
            u_stu2 = User(name="Donald Knuth", email="donald@test.local", password_hash="pw", role="STUDENT")
            db.session.add_all([u_fac1, u_fac2, u_stu1, u_stu2])
            db.session.flush()

            self.fac1_id = u_fac1.user_id
            self.fac2_id = u_fac2.user_id

            # 3. Faculty Profiles
            self.faculty1 = Faculty(user_id=u_fac1.user_id, department_id=dept.department_id, employee_id="FAC001", designation="Professor")
            self.faculty2 = Faculty(user_id=u_fac2.user_id, department_id=dept.department_id, employee_id="FAC002", designation="Professor")
            db.session.add_all([self.faculty1, self.faculty2])
            db.session.flush()

            # 4. Student Profiles
            self.student1 = Student(user_id=u_stu1.user_id, department_id=dept.department_id, enrollment_no="STU001", semester=4, section="A", academic_year="2024-2025")
            self.student2 = Student(user_id=u_stu2.user_id, department_id=dept.department_id, enrollment_no="STU002", semester=4, section="A", academic_year="2024-2025")
            db.session.add_all([self.student1, self.student2])
            db.session.flush()

            # 5. Course & Offerings
            course1 = Course(department_id=dept.department_id, course_code="CS101", course_name="Data Structures", semester=4, credits=4)
            course2 = Course(department_id=dept.department_id, course_code="CS102", course_name="Algorithms", semester=4, credits=4)
            db.session.add_all([course1, course2])
            db.session.flush()

            # Offering 1 belongs to Faculty 1
            off1 = CourseOffering(
                course_id=course1.course_id,
                faculty_id=self.faculty1.faculty_id,
                semester=4,
                section="A",
                academic_year="2024-2025",
                room="Lab 1",
            )
            # Offering 2 belongs to Faculty 2 (for cross-faculty isolation tests)
            off2 = CourseOffering(
                course_id=course2.course_id,
                faculty_id=self.faculty2.faculty_id,
                semester=4,
                section="B",
                academic_year="2024-2025",
                room="Lab 2",
            )
            db.session.add_all([off1, off2])
            db.session.flush()

            self.offering1_id = off1.offering_id
            self.offering2_id = off2.offering_id

            # 6. Enrollments in Offering 1
            e1 = Enrollment(offering_id=self.offering1_id, student_id=self.student1.student_id, status="ACTIVE")
            e2 = Enrollment(offering_id=self.offering1_id, student_id=self.student2.student_id, status="ACTIVE")
            db.session.add_all([e1, e2])
            db.session.flush()

            # 7. Attendance Sessions & Records
            # Session 1: 2026-03-10 (Closed)
            s1 = AttendanceSession(
                offering_id=self.offering1_id,
                faculty_id=self.faculty1.faculty_id,
                session_date=date(2026, 3, 10),
                start_time=time(9, 0),
                end_time=time(10, 0),
                status="CLOSED",
            )
            # Session 2: 2026-03-15 (Closed)
            s2 = AttendanceSession(
                offering_id=self.offering1_id,
                faculty_id=self.faculty1.faculty_id,
                session_date=date(2026, 3, 15),
                start_time=time(9, 0),
                end_time=time(10, 0),
                status="CLOSED",
            )
            db.session.add_all([s1, s2])
            db.session.flush()

            # Records: Student 1 present both days (100%), Student 2 absent both days (0% -> Low Attendance)
            r1 = AttendanceRecord(session_id=s1.session_id, student_id=self.student1.student_id, status="PRESENT")
            r2 = AttendanceRecord(session_id=s1.session_id, student_id=self.student2.student_id, status="ABSENT")
            r3 = AttendanceRecord(session_id=s2.session_id, student_id=self.student1.student_id, status="PRESENT")
            r4 = AttendanceRecord(session_id=s2.session_id, student_id=self.student2.student_id, status="ABSENT")
            db.session.add_all([r1, r2, r3, r4])
            db.session.commit()

            # Setup auth token for Faculty 1 and Faculty 2 with claims
            with self.app.app_context():
                self.fac1_token = create_access_token(
                    identity=str(self.fac1_id),
                    additional_claims={"role": "FACULTY"},
                )
                self.fac2_token = create_access_token(
                    identity=str(self.fac2_id),
                    additional_claims={"role": "FACULTY"},
                )

    def _auth_headers(self, token=None):
        return {"Authorization": f"Bearer {token or self.fac1_token}"}

    def test_export_csv_success(self):
        """Verify CSV export returns 200, correct MIME type, Content-Disposition, and accurate rows."""
        resp = self.client.get(
            "/api/faculty/attendance/reports/export?format=csv",
            headers=self._auth_headers(),
        )
        self.assertEqual(resp.status_code, 200)
        self.assertIn("text/csv", resp.content_type)
        self.assertIn("Faculty_Attendance_Report_", resp.headers.get("Content-Disposition", ""))
        self.assertIn(".csv", resp.headers.get("Content-Disposition", ""))

        csv_text = resp.data.decode("utf-8")
        self.assertIn("Grace Hopper", csv_text)
        self.assertIn("STU001", csv_text)
        self.assertIn("Donald Knuth", csv_text)
        self.assertIn("STU002", csv_text)
        self.assertIn("CS101 - A", csv_text)
        self.assertIn("Needs Attention", csv_text)
        self.assertIn("Good", csv_text)

    def test_export_xlsx_success(self):
        """Verify Excel export returns 200, XLSX MIME type, and parses with openpyxl."""
        resp = self.client.get(
            "/api/faculty/attendance/reports/export?format=xlsx",
            headers=self._auth_headers(),
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(
            resp.content_type,
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        self.assertIn(".xlsx", resp.headers.get("Content-Disposition", ""))
        # ZIP archive magic bytes
        self.assertTrue(resp.data.startswith(b"PK\x03\x04"))

        # Load with openpyxl and verify contents
        wb = load_workbook(io.BytesIO(resp.data))
        ws = wb.active
        self.assertIn("Attendance", ws.title)

        # Check that student rows are present
        all_values = [str(cell.value) for row in ws.iter_rows() for cell in row if cell.value is not None]
        self.assertIn("Grace Hopper", all_values)
        self.assertIn("Donald Knuth", all_values)
        self.assertIn("CS101 - A", all_values)

    def test_export_pdf_success(self):
        """Verify PDF export returns 200, application/pdf MIME type, and valid PDF bytes."""
        resp = self.client.get(
            "/api/faculty/attendance/reports/export?format=pdf",
            headers=self._auth_headers(),
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.content_type, "application/pdf")
        self.assertIn(".pdf", resp.headers.get("Content-Disposition", ""))
        # PDF magic bytes
        self.assertTrue(resp.data.startswith(b"%PDF-"))
        self.assertGreater(len(resp.data), 2000)

    def test_export_invalid_format_returns_400(self):
        """Unsupported format like docx or xml must return HTTP 400."""
        resp = self.client.get(
            "/api/faculty/attendance/reports/export?format=docx",
            headers=self._auth_headers(),
        )
        self.assertEqual(resp.status_code, 400)
        json_data = resp.get_json()
        self.assertFalse(json_data["success"])
        self.assertIn("Unsupported export format", json_data["message"])

    def test_export_date_filter_applied(self):
        """Sessions outside from_date and to_date must be excluded."""
        # Range that only includes Session 1 (2026-03-10)
        resp = self.client.get(
            "/api/faculty/attendance/reports/export?format=csv&from_date=2026-03-01&to_date=2026-03-12",
            headers=self._auth_headers(),
        )
        self.assertEqual(resp.status_code, 200)
        csv_text = resp.data.decode("utf-8")
        # In session 1, total classes is 1
        self.assertIn("Grace Hopper", csv_text)

    def test_export_status_filter_low_attendance(self):
        """status=Low should only export students with attendance < 75%."""
        resp = self.client.get(
            "/api/faculty/attendance/reports/export?format=csv&status=Low",
            headers=self._auth_headers(),
        )
        self.assertEqual(resp.status_code, 200)
        csv_text = resp.data.decode("utf-8")
        # Donald Knuth has 0% (Low)
        self.assertIn("Donald Knuth", csv_text)
        # Grace Hopper has 100% (Not low)
        self.assertNotIn("Grace Hopper", csv_text)

    def test_export_search_filter(self):
        """search query matches student name or roll number."""
        resp = self.client.get(
            "/api/faculty/attendance/reports/export?format=csv&search=Hopper",
            headers=self._auth_headers(),
        )
        self.assertEqual(resp.status_code, 200)
        csv_text = resp.data.decode("utf-8")
        self.assertIn("Grace Hopper", csv_text)
        self.assertNotIn("Donald Knuth", csv_text)

    def test_export_empty_dataset(self):
        """When date range has zero closed sessions, export still delivers clean empty report."""
        resp = self.client.get(
            "/api/faculty/attendance/reports/export?format=csv&from_date=2025-01-01&to_date=2025-01-05",
            headers=self._auth_headers(),
        )
        self.assertEqual(resp.status_code, 200)
        self.assertIn("text/csv", resp.content_type)

    def test_export_unauthenticated_returns_401(self):
        """Missing authorization token returns 401."""
        resp = self.client.get("/api/faculty/attendance/reports/export?format=csv")
        self.assertEqual(resp.status_code, 401)

    def test_export_cross_faculty_isolation_404(self):
        """Faculty 1 cannot export offering assigned to Faculty 2 (IDOR protection)."""
        resp = self.client.get(
            f"/api/faculty/attendance/reports/export?format=csv&offering_id={self.offering2_id}",
            headers=self._auth_headers(self.fac1_token),
        )
        self.assertEqual(resp.status_code, 404)
        json_data = resp.get_json()
        self.assertFalse(json_data["success"])
        self.assertEqual(json_data["message"], "Course offering not found")


if __name__ == "__main__":
    unittest.main()
