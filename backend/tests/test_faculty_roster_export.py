"""Integration Tests for Faculty Class Roster Export Endpoint.

Verifies:
- GET /api/faculty/classes/<offering_id>/roster/export
- GET /api/faculty/classes/<offering_id>/roster (JSON)
- XLSX, PDF, and CSV format generation
- Correct MIME types and Content-Disposition filenames
- Role-based authorization & cross-faculty data isolation (returns 404 for unauthorized)
- Empty class handling (0 enrolled students exports cleanly)
- Enrollment isolation between course offerings
- Multi-page PDF generation with 35+ enrolled students
"""

import io
import unittest
from flask import Flask
from flask_jwt_extended import JWTManager, create_access_token
from openpyxl import load_workbook
from sqlalchemy.pool import StaticPool

from app.extensions import db
from app.models import (
    Course,
    CourseOffering,
    Department,
    Enrollment,
    Faculty,
    Student,
    User,
)
from app.routes.faculty import faculty_bp


class TestFacultyRosterExport(unittest.TestCase):
    """Test suite for GET /api/faculty/classes/<offering_id>/roster/export."""

    @classmethod
    def setUpClass(cls):
        cls.app = Flask(__name__)
        cls.app.config.update(
            TESTING=True,
            SECRET_KEY="test-roster-export-secret",
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
        cls.app.register_blueprint(faculty_bp)

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
            dept = Department(department_name="Computer Science & Engineering", department_code="CSE")
            db.session.add(dept)
            db.session.flush()

            # 2. Users (Faculty 1, Faculty 2, Student 1, Student 2, Student 3)
            u_fac1 = User(name="Prof. Charles Babbage", email="babbage@test.local", password_hash="pw", role="FACULTY")
            u_fac2 = User(name="Prof. Grace Hopper", email="grace_prof@test.local", password_hash="pw", role="FACULTY")
            u_stu1 = User(name="Alice Walker", email="alice@test.local", password_hash="pw", role="STUDENT")
            u_stu2 = User(name="Bob Smith", email="bob@test.local", password_hash="pw", role="STUDENT")
            u_stu3 = User(name="Charlie Brown", email="charlie@test.local", password_hash="pw", role="STUDENT")
            db.session.add_all([u_fac1, u_fac2, u_stu1, u_stu2, u_stu3])
            db.session.flush()

            self.fac1_user_id = u_fac1.user_id
            self.fac2_user_id = u_fac2.user_id

            # 3. Faculty Profiles
            self.faculty1 = Faculty(user_id=u_fac1.user_id, department_id=dept.department_id, employee_id="FAC001", designation="Associate Professor")
            self.faculty2 = Faculty(user_id=u_fac2.user_id, department_id=dept.department_id, employee_id="FAC002", designation="Professor")
            db.session.add_all([self.faculty1, self.faculty2])
            db.session.flush()

            # 4. Student Profiles
            self.student1 = Student(user_id=u_stu1.user_id, department_id=dept.department_id, enrollment_no="ENR2024001", semester=4, section="A", academic_year="2024-2025")
            self.student2 = Student(user_id=u_stu2.user_id, department_id=dept.department_id, enrollment_no="ENR2024002", semester=4, section="A", academic_year="2024-2025")
            self.student3 = Student(user_id=u_stu3.user_id, department_id=dept.department_id, enrollment_no="ENR2024003", semester=4, section="B", academic_year="2024-2025")
            db.session.add_all([self.student1, self.student2, self.student3])
            db.session.flush()

            # 5. Course & Offerings
            course1 = Course(department_id=dept.department_id, course_code="CS201", course_name="Data Structures", semester=4, credits=4)
            course2 = Course(department_id=dept.department_id, course_code="CS202", course_name="Operating Systems", semester=4, credits=3)
            db.session.add_all([course1, course2])
            db.session.flush()

            # Offering 1: Faculty 1, CS201 Section A (Enrolled: student1, student2)
            off1 = CourseOffering(
                course_id=course1.course_id,
                faculty_id=self.faculty1.faculty_id,
                semester=4,
                section="A",
                academic_year="2024-2025",
                room="Room 301",
            )
            # Offering 2: Faculty 2, CS202 Section B (Enrolled: student3) - cross-faculty isolation test
            off2 = CourseOffering(
                course_id=course2.course_id,
                faculty_id=self.faculty2.faculty_id,
                semester=4,
                section="B",
                academic_year="2024-2025",
                room="Room 302",
            )
            # Offering 3: Faculty 1, CS201 Section C (Empty class - 0 enrollments)
            off3 = CourseOffering(
                course_id=course1.course_id,
                faculty_id=self.faculty1.faculty_id,
                semester=4,
                section="C",
                academic_year="2024-2025",
                room="Room 303",
            )
            db.session.add_all([off1, off2, off3])
            db.session.flush()

            self.offering1_id = off1.offering_id
            self.offering2_id = off2.offering_id
            self.offering3_id = off3.offering_id

            # 6. Enrollments
            e1 = Enrollment(offering_id=self.offering1_id, student_id=self.student1.student_id, status="ACTIVE")
            e2 = Enrollment(offering_id=self.offering1_id, student_id=self.student2.student_id, status="ACTIVE")
            e3 = Enrollment(offering_id=self.offering2_id, student_id=self.student3.student_id, status="ACTIVE")
            db.session.add_all([e1, e2, e3])
            db.session.commit()

            # Generate tokens
            self.fac1_token = create_access_token(
                identity=str(self.fac1_user_id),
                additional_claims={"role": "FACULTY"},
            )
            self.fac2_token = create_access_token(
                identity=str(self.fac2_user_id),
                additional_claims={"role": "FACULTY"},
            )

    def _auth_headers(self, token=None):
        return {"Authorization": f"Bearer {token or self.fac1_token}"}

    def test_export_roster_xlsx(self):
        """Test exporting roster as Excel (.xlsx) returns 200, valid MIME, and accurate records."""
        res = self.client.get(
            f"/api/faculty/classes/{self.offering1_id}/roster/export?format=xlsx",
            headers=self._auth_headers(),
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(
            res.mimetype,
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        self.assertTrue(res.data.startswith(b"PK\x03\x04"))
        disp = res.headers.get("Content-Disposition", "")
        self.assertIn("attachment", disp)
        self.assertIn("Class_Roster_CS201_A_", disp)
        self.assertIn(".xlsx", disp)

        wb = load_workbook(io.BytesIO(res.data))
        self.assertIn("ClassRoster", wb.sheetnames)
        ws = wb["ClassRoster"]

        text_cells = [str(cell.value) for row in ws.iter_rows() for cell in row if cell.value is not None]
        self.assertTrue(any("Alice Walker" in c for c in text_cells))
        self.assertTrue(any("Bob Smith" in c for c in text_cells))
        self.assertTrue(any("ENR2024001" in c for c in text_cells))
        self.assertTrue(any("ENR2024002" in c for c in text_cells))
        # Ensure student from offering 2 is not present
        self.assertFalse(any("Charlie Brown" in c for c in text_cells))

    def test_export_roster_pdf(self):
        """Test exporting roster as PDF returns 200, valid PDF signature, and proper headers."""
        res = self.client.get(
            f"/api/faculty/classes/{self.offering1_id}/roster/export?format=pdf",
            headers=self._auth_headers(),
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.mimetype, "application/pdf")
        self.assertTrue(res.data.startswith(b"%PDF-"))
        self.assertTrue(b"%%EOF" in res.data[-1024:])
        disp = res.headers.get("Content-Disposition", "")
        self.assertIn("attachment", disp)
        self.assertIn("Class_Roster_CS201_A_", disp)
        self.assertIn(".pdf", disp)

    def test_export_roster_csv(self):
        """Test exporting roster as CSV returns 200, text/csv, and accurate CSV rows."""
        res = self.client.get(
            f"/api/faculty/classes/{self.offering1_id}/roster/export?format=csv",
            headers=self._auth_headers(),
        )
        self.assertEqual(res.status_code, 200)
        self.assertIn("text/csv", res.mimetype)
        disp = res.headers.get("Content-Disposition", "")
        self.assertIn("attachment", disp)
        self.assertIn(".csv", disp)

        csv_text = res.data.decode("utf-8-sig")
        self.assertIn("CLASS ROSTER REPORT", csv_text)
        self.assertIn("Enrollment No", csv_text)
        self.assertIn("Student Name", csv_text)
        self.assertIn("ENR2024001", csv_text)
        self.assertIn("Alice Walker", csv_text)
        self.assertIn("ENR2024002", csv_text)
        self.assertIn("Bob Smith", csv_text)
        # Ensure isolation
        self.assertNotIn("Charlie Brown", csv_text)
        self.assertNotIn("ENR2024003", csv_text)

    def test_export_roster_default_format_is_xlsx(self):
        """Test omitting the format parameter defaults to Excel (.xlsx)."""
        res = self.client.get(
            f"/api/faculty/classes/{self.offering1_id}/roster/export",
            headers=self._auth_headers(),
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(
            res.mimetype,
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        self.assertTrue(res.data.startswith(b"PK\x03\x04"))

    def test_export_roster_unsupported_format_returns_400(self):
        """Test invalid format query parameter returns 400 Bad Request."""
        res = self.client.get(
            f"/api/faculty/classes/{self.offering1_id}/roster/export?format=docx",
            headers=self._auth_headers(),
        )
        self.assertEqual(res.status_code, 400)
        data = res.get_json()
        self.assertFalse(data["success"])
        self.assertIn("Unsupported export format", data["message"])

    def test_export_roster_unauthenticated_returns_401(self):
        """Test unauthenticated request without token returns 401."""
        res = self.client.get(
            f"/api/faculty/classes/{self.offering1_id}/roster/export?format=xlsx",
        )
        self.assertEqual(res.status_code, 401)

    def test_export_roster_unauthorized_faculty_returns_404(self):
        """Test Faculty B cannot export Faculty A's offering roster; returns 404 for security."""
        # Faculty 2 attempts to export Offering 1 (owned by Faculty 1)
        res = self.client.get(
            f"/api/faculty/classes/{self.offering1_id}/roster/export?format=xlsx",
            headers=self._auth_headers(self.fac2_token),
        )
        self.assertEqual(res.status_code, 404)
        data = res.get_json()
        self.assertFalse(data["success"])
        self.assertIn("not found or unauthorized", data["message"].lower())

    def test_export_roster_nonexistent_offering_returns_404(self):
        """Test requesting export for a non-existent offering ID returns 404."""
        res = self.client.get(
            "/api/faculty/classes/99999/roster/export?format=xlsx",
            headers=self._auth_headers(),
        )
        self.assertEqual(res.status_code, 404)
        data = res.get_json()
        self.assertFalse(data["success"])

    def test_export_roster_empty_class_generates_valid_document(self):
        """Test an offering with 0 enrolled students exports cleanly without error."""
        for fmt in ("xlsx", "pdf", "csv"):
            res = self.client.get(
                f"/api/faculty/classes/{self.offering3_id}/roster/export?format={fmt}",
                headers=self._auth_headers(),
            )
            self.assertEqual(res.status_code, 200, f"Failed for format {fmt}")
            self.assertGreater(len(res.data), 0)

    def test_export_roster_excludes_students_from_other_offerings(self):
        """Test strict enrollment isolation between offerings."""
        # Export Offering 2 (owned by Faculty 2, contains Charlie Brown only)
        res = self.client.get(
            f"/api/faculty/classes/{self.offering2_id}/roster/export?format=csv",
            headers=self._auth_headers(self.fac2_token),
        )
        self.assertEqual(res.status_code, 200)
        csv_text = res.data.decode("utf-8-sig")
        self.assertIn("Charlie Brown", csv_text)
        self.assertIn("ENR2024003", csv_text)
        self.assertNotIn("Alice Walker", csv_text)
        self.assertNotIn("Bob Smith", csv_text)

    def test_export_roster_multipage_pdf(self):
        """Test offering with 35+ enrolled students generates multi-page PDF without crash."""
        with self.app.app_context():
            dept = Department.query.first()
            # Add 35 students to offering 3
            bulk_users = []
            for i in range(1, 36):
                bulk_users.append(
                    User(
                        name=f"Bulk Student {i:02d}",
                        email=f"bulk{i:02d}@test.local",
                        password_hash="pw",
                        role="STUDENT",
                    )
                )
            db.session.add_all(bulk_users)
            db.session.flush()

            bulk_students = []
            for i, u in enumerate(bulk_users, start=1):
                bulk_students.append(
                    Student(
                        user_id=u.user_id,
                        department_id=dept.department_id,
                        enrollment_no=f"BULK{i:03d}",
                        semester=4,
                        section="C",
                        academic_year="2024-2025",
                    )
                )
            db.session.add_all(bulk_students)
            db.session.flush()

            bulk_enrollments = []
            for s in bulk_students:
                bulk_enrollments.append(
                    Enrollment(
                        offering_id=self.offering3_id,
                        student_id=s.student_id,
                        status="ACTIVE",
                    )
                )
            db.session.add_all(bulk_enrollments)
            db.session.commit()

        res = self.client.get(
            f"/api/faculty/classes/{self.offering3_id}/roster/export?format=pdf",
            headers=self._auth_headers(),
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.mimetype, "application/pdf")
        self.assertTrue(res.data.startswith(b"%PDF-"))
        self.assertGreater(len(res.data), 5000)

    def test_get_class_roster_json(self):
        """Test GET /api/faculty/classes/<offering_id>/roster returns structured JSON."""
        res = self.client.get(
            f"/api/faculty/classes/{self.offering1_id}/roster",
            headers=self._auth_headers(),
        )
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["success"])
        self.assertEqual(data["data"]["total_students"], 2)
        students = data["data"]["students"]
        self.assertEqual(len(students), 2)
        names = [s["name"] for s in students]
        self.assertIn("Alice Walker", names)
        self.assertIn("Bob Smith", names)

    def test_get_class_roster_json_unauthorized_returns_404(self):
        """Test GET /api/faculty/classes/<offering_id>/roster returns 404 for unauthorized faculty."""
        res = self.client.get(
            f"/api/faculty/classes/{self.offering1_id}/roster",
            headers=self._auth_headers(self.fac2_token),
        )
        self.assertEqual(res.status_code, 404)
        data = res.get_json()
        self.assertFalse(data["success"])


if __name__ == "__main__":
    unittest.main()
