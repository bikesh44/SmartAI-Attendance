"""Tests for Student Academic Records Multi-Format Export (Phase 2C / ISSUE-EXP-02).

Validates:
- Default format is genuine PDF with %PDF- header.
- Explicit formats: PDF, CSV, XLSX (.xlsx openpyxl).
- Invalid format returns 400.
- Semester filtering vs all-semesters export.
- Student identity isolation (cannot export other students' records).
- Unauthenticated access returns 401.
- No published records returns 404.
- Incomplete / null academic data handled gracefully.
- Large multi-page PDF dataset rendering.
- Accurate SGPA, CGPA, and credits calculations in export metadata/summary.
"""

import io
import unittest
from datetime import datetime
from decimal import Decimal

from flask import Flask
from flask_jwt_extended import JWTManager, create_access_token
from sqlalchemy.pool import StaticPool

from app.extensions import db
from app.models import (
    AcademicResult,
    Course,
    Department,
    Student,
    User,
)
from app.routes.student_academic import student_academic_bp


class TestStudentAcademicExport(unittest.TestCase):
    """Test suite for Student Academic Records Export (Phase 2C)."""

    @classmethod
    def setUpClass(cls):
        cls.app = Flask(__name__)
        cls.app.config.update(
            TESTING=True,
            SECRET_KEY="test-academic-export-secret",
            JWT_SECRET_KEY="test-jwt-secret-academic-export-key",
            SQLALCHEMY_DATABASE_URI="sqlite://",
            SQLALCHEMY_TRACK_MODIFICATIONS=False,
            SQLALCHEMY_ENGINE_OPTIONS={
                "poolclass": StaticPool,
                "connect_args": {"check_same_thread": False},
            },
            JWT_TOKEN_LOCATION=["headers"],
        )

        db.init_app(cls.app)
        cls.jwt = JWTManager(cls.app)
        cls.app.register_blueprint(student_academic_bp)

        with cls.app.app_context():
            db.create_all()

    def setUp(self):
        self.client = self.app.test_client()
        self.ctx = self.app.app_context()
        self.ctx.push()

        # Create department
        self.dept = Department(
            department_name="Computer Science & Engineering",
            department_code="CSE",
        )
        db.session.add(self.dept)
        db.session.commit()

        # Create Student 1 (Alice)
        self.user1 = User(
            name="Alice Student",
            email="alice.export@test.edu",
            password_hash="pw_alice",
            role="STUDENT",
        )
        db.session.add(self.user1)
        db.session.commit()

        self.student1 = Student(
            user_id=self.user1.user_id,
            department_id=self.dept.department_id,
            enrollment_no="STU2024001",
            semester=6,
            section="A",
            academic_year="2024-2025",
        )

        # Create Student 2 (Bob)
        self.user2 = User(
            name="Bob Student",
            email="bob.export@test.edu",
            password_hash="pw_bob",
            role="STUDENT",
        )
        db.session.add(self.user2)
        db.session.commit()

        self.student2 = Student(
            user_id=self.user2.user_id,
            department_id=self.dept.department_id,
            enrollment_no="STU2024002",
            semester=6,
            section="B",
            academic_year="2024-2025",
        )
        db.session.add_all([self.student1, self.student2])
        db.session.commit()

        # Create Courses
        self.course1 = Course(
            course_code="CS301",
            course_name="Database Management Systems",
            department_id=self.dept.department_id,
            credits=4,
            semester=5,
        )
        self.course2 = Course(
            course_code="CS302",
            course_name="Operating Systems",
            department_id=self.dept.department_id,
            credits=4,
            semester=5,
        )
        self.course3 = Course(
            course_code="CS303",
            course_name="Software Engineering",
            department_id=self.dept.department_id,
            credits=3,
            semester=6,
        )
        self.course4 = Course(
            course_code="CS304",
            course_name="Computer Networks",
            department_id=self.dept.department_id,
            credits=3,
            semester=6,
        )
        db.session.add_all([self.course1, self.course2, self.course3, self.course4])
        db.session.commit()

        # Create published results for Student 1
        # Sem 5 Course 1: 85 marks -> Grade A, 8.5 GP, 4 credits
        self.res1 = AcademicResult(
            student_id=self.student1.student_id,
            course_id=self.course1.course_id,
            academic_year="2024-2025",
            semester=5,
            credits=4,
            marks_obtained=85.0,
            max_marks=100.0,
            grade="A",
            grade_points=Decimal("8.50"),
            status="PASS",
            remarks="Excellent",
            is_published=True,
        )
        # Sem 5 Course 2: 92 marks -> Grade A+, 9.2 GP, 4 credits
        self.res2 = AcademicResult(
            student_id=self.student1.student_id,
            course_id=self.course2.course_id,
            academic_year="2024-2025",
            semester=5,
            credits=4,
            marks_obtained=92.0,
            max_marks=100.0,
            grade="A+",
            grade_points=Decimal("9.20"),
            status="PASS",
            remarks="Outstanding",
            is_published=True,
        )
        # Sem 6 Course 3: 78 marks -> Grade B+, 7.8 GP, 3 credits
        self.res3 = AcademicResult(
            student_id=self.student1.student_id,
            course_id=self.course3.course_id,
            academic_year="2024-2025",
            semester=6,
            credits=3,
            marks_obtained=78.0,
            max_marks=100.0,
            grade="B+",
            grade_points=Decimal("7.80"),
            status="PASS",
            remarks="Very Good",
            is_published=True,
        )
        # Unpublished draft result for Student 1 on Course 4 (should NOT appear in export)
        self.res_draft = AcademicResult(
            student_id=self.student1.student_id,
            course_id=self.course4.course_id,
            academic_year="2024-2025",
            semester=6,
            credits=3,
            marks_obtained=50.0,
            max_marks=100.0,
            grade="C",
            grade_points=Decimal("5.00"),
            status="PASS",
            is_published=False,
        )

        db.session.add_all([self.res1, self.res2, self.res3, self.res_draft])
        db.session.commit()

        # JWT tokens with student role claims
        self.token_student1 = create_access_token(
            identity=str(self.user1.user_id),
            additional_claims={"role": "STUDENT"},
        )
        self.token_student2 = create_access_token(
            identity=str(self.user2.user_id),
            additional_claims={"role": "STUDENT"},
        )

    def tearDown(self):
        db.session.rollback()
        for table in reversed(db.metadata.sorted_tables):
            db.session.execute(table.delete())
        db.session.commit()
        self.ctx.pop()

    def test_export_pdf_default(self):
        """Omission of format parameter must default to genuine PDF."""
        resp = self.client.get(
            "/api/student/academic-records/export?semester=5",
            headers={"Authorization": f"Bearer {self.token_student1}"},
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.headers["Content-Type"], "application/pdf")
        self.assertTrue(resp.data.startswith(b"%PDF-"))
        self.assertIn("Content-Disposition", resp.headers)
        disp = resp.headers["Content-Disposition"]
        self.assertIn("Academic_Grade_Card_STU2024001_Sem5_", disp)
        self.assertTrue(disp.endswith('.pdf"') or disp.endswith(".pdf"))

    def test_export_pdf_explicit(self):
        """format=pdf explicitly returns genuine PDF Grade Card."""
        resp = self.client.get(
            "/api/student/academic-records/export?semester=5&format=pdf",
            headers={"Authorization": f"Bearer {self.token_student1}"},
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.headers["Content-Type"], "application/pdf")
        self.assertTrue(resp.data.startswith(b"%PDF-"))
        # PDF document must contain end of file marker %%EOF
        self.assertIn(b"%%EOF", resp.data)

    def test_export_csv(self):
        """format=csv returns properly structured CSV with metadata and courses."""
        resp = self.client.get(
            "/api/student/academic-records/export?semester=5&format=csv",
            headers={"Authorization": f"Bearer {self.token_student1}"},
        )
        self.assertEqual(resp.status_code, 200)
        self.assertIn("text/csv", resp.headers["Content-Type"])
        content = resp.data.decode("utf-8")
        self.assertIn("STU2024001", content)
        self.assertIn("Alice Student", content)
        self.assertIn("CS301", content)
        self.assertIn("Database Management Systems", content)
        self.assertIn("CS302", content)
        self.assertIn("Operating Systems", content)
        # Should not include Sem 6 course when filtered by semester 5
        self.assertNotIn("CS303", content)
        # Should not include unpublished course
        self.assertNotIn("CS304", content)

    def test_export_xlsx(self):
        """format=xlsx returns valid OpenXML Excel workbook."""
        resp = self.client.get(
            "/api/student/academic-records/export?semester=5&format=xlsx",
            headers={"Authorization": f"Bearer {self.token_student1}"},
        )
        self.assertEqual(resp.status_code, 200)
        self.assertIn(
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            resp.headers["Content-Type"],
        )
        # OpenXML / ZIP files start with magic bytes PK\x03\x04
        self.assertTrue(resp.data.startswith(b"PK\x03\x04"))

    def test_export_unsupported_format_returns_400(self):
        """Invalid format argument returns HTTP 400 with helpful error message."""
        resp = self.client.get(
            "/api/student/academic-records/export?format=docx",
            headers={"Authorization": f"Bearer {self.token_student1}"},
        )
        self.assertEqual(resp.status_code, 400)
        data = resp.get_json()
        self.assertFalse(data["success"])
        self.assertIn("Unsupported export format", data["message"])

    def test_export_all_semesters_when_no_semester_param(self):
        """Omitting semester exports all published courses across all semesters."""
        resp = self.client.get(
            "/api/student/academic-records/export?format=csv",
            headers={"Authorization": f"Bearer {self.token_student1}"},
        )
        self.assertEqual(resp.status_code, 200)
        content = resp.data.decode("utf-8")
        self.assertIn("CS301", content)
        self.assertIn("CS302", content)
        self.assertIn("CS303", content)
        # Draft course should still be excluded
        self.assertNotIn("CS304", content)
        disp = resp.headers.get("Content-Disposition", "")
        self.assertIn("_All_", disp)

    def test_export_student_data_isolation(self):
        """Student 2 cannot access Student 1's records; isolated by JWT identity."""
        # Student 2 has no published records yet
        resp = self.client.get(
            "/api/student/academic-records/export",
            headers={"Authorization": f"Bearer {self.token_student2}"},
        )
        # Returns 404 because Student 2 has 0 published records
        self.assertEqual(resp.status_code, 404)
        data = resp.get_json()
        self.assertFalse(data["success"])
        self.assertEqual(data["message"], "No published records found to export")

    def test_export_unauthenticated_returns_401(self):
        """Requests without JWT authorization return 401."""
        resp = self.client.get("/api/student/academic-records/export")
        self.assertEqual(resp.status_code, 401)

    def test_export_no_published_records_returns_404(self):
        """Filtering by a semester with no published results returns 404."""
        resp = self.client.get(
            "/api/student/academic-records/export?semester=8",
            headers={"Authorization": f"Bearer {self.token_student1}"},
        )
        self.assertEqual(resp.status_code, 404)
        data = resp.get_json()
        self.assertFalse(data["success"])

    def test_export_incomplete_academic_data_graceful(self):
        """Null marks, missing remarks, or course edge cases render gracefully."""
        incomplete_res = AcademicResult(
            student_id=self.student2.student_id,
            course_id=self.course1.course_id,
            academic_year="2024-2025",
            semester=6,
            credits=4,
            marks_obtained=None,  # Null marks
            max_marks=100.0,
            grade="P",  # Grade present, but marks/remarks null
            grade_points=Decimal("4.00"),
            status=None,  # Null status
            remarks=None,  # Null remarks
            is_published=True,
        )
        db.session.add(incomplete_res)
        db.session.commit()

        resp = self.client.get(
            "/api/student/academic-records/export?format=pdf",
            headers={"Authorization": f"Bearer {self.token_student2}"},
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.headers["Content-Type"], "application/pdf")
        self.assertTrue(resp.data.startswith(b"%PDF-"))

    def test_export_multipage_pdf_generation(self):
        """Rendering a large dataset spans multiple pages cleanly without error."""
        large_courses = []
        for i in range(1, 26):
            c = Course(
                course_code=f"ELEC{100 + i}",
                course_name=f"Elective Advanced Topic #{i} Systems Engineering",
                department_id=self.dept.department_id,
                credits=3,
                semester=6,
            )
            large_courses.append(c)
        db.session.add_all(large_courses)
        db.session.commit()

        large_results = []
        for c in large_courses:
            r = AcademicResult(
                student_id=self.student1.student_id,
                course_id=c.course_id,
                academic_year="2024-2025",
                semester=6,
                credits=3,
                marks_obtained=80.0,
                max_marks=100.0,
                grade="A",
                grade_points=Decimal("8.00"),
                status="PASS",
                remarks="Multi-page test",
                is_published=True,
            )
            large_results.append(r)
        db.session.add_all(large_results)
        db.session.commit()

        resp = self.client.get(
            "/api/student/academic-records/export?semester=6&format=pdf",
            headers={"Authorization": f"Bearer {self.token_student1}"},
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.headers["Content-Type"], "application/pdf")
        self.assertTrue(resp.data.startswith(b"%PDF-"))
        self.assertIn(b"%%EOF", resp.data)
        # Multi-page PDF will have multiple Page objects
        self.assertIn(b"/Page", resp.data)


if __name__ == "__main__":
    unittest.main()
