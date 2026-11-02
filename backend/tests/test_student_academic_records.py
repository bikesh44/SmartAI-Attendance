"""
Unit and integration tests for Student Academic Records, Grading Policy, and APIs.
Tests run using an isolated SQLite in-memory database to prevent modifying live records.
"""

import unittest
from datetime import datetime
from decimal import Decimal

from flask import Flask
from flask_jwt_extended import JWTManager, create_access_token
from sqlalchemy.pool import StaticPool

from app.extensions import db
from app.models import (
    AcademicDocument,
    AcademicResult,
    Course,
    Department,
    Examination,
    Student,
    User,
)
from app.routes.student_academic import student_academic_bp
from app.utils.grading_policy import (
    calculate_cgpa,
    calculate_credits_earned,
    calculate_sgpa,
    determine_grade_and_points,
    generate_academic_insights,
)


class TestStudentAcademicRecords(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = Flask(__name__)
        cls.app.config.update(
            TESTING=True,
            SECRET_KEY="test-academic-secret",
            JWT_SECRET_KEY="test-jwt-secret-academic-records-key",
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

        # Create test users and students
        self.user1 = User(
            name="Alice Student",
            email="alice@test.edu",
            password_hash="hashed_pw_alice",
            role="STUDENT",
        )
        self.user2 = User(
            name="Bob Student",
            email="bob@test.edu",
            password_hash="hashed_pw_bob",
            role="STUDENT",
        )
        self.admin_user = User(
            name="Admin Staff",
            email="admin@test.edu",
            password_hash="hashed_pw_admin",
            role="ADMIN",
        )
        db.session.add_all([self.user1, self.user2, self.admin_user])
        db.session.commit()

        self.dept = Department(
            department_name="Computer Science & Engineering",
            department_code="CSE",
        )
        db.session.add(self.dept)
        db.session.commit()

        self.student1 = Student(
            user_id=self.user1.user_id,
            department_id=self.dept.department_id,
            enrollment_no="STU2024001",
            semester=6,
            section="A",
            academic_year="2024-2025",
        )
        self.student2 = Student(
            user_id=self.user2.user_id,
            department_id=self.dept.department_id,
            enrollment_no="STU2024002",
            semester=6,
            section="A",
            academic_year="2024-2025",
        )
        db.session.add_all([self.student1, self.student2])
        db.session.commit()

        # Create test courses
        self.course1 = Course(
            department_id=self.dept.department_id,
            course_code="CSE101",
            course_name="Data Structures",
            semester=6,
            credits=4,
        )
        self.course2 = Course(
            department_id=self.dept.department_id,
            course_code="CSE102",
            course_name="Computer Networks",
            semester=6,
            credits=4,
        )
        self.course3 = Course(
            department_id=self.dept.department_id,
            course_code="ENG101",
            course_name="English",
            semester=5,
            credits=2,
        )
        db.session.add_all([self.course1, self.course2, self.course3])
        db.session.commit()

        # Generate tokens
        self.token_student1 = create_access_token(
            identity=str(self.user1.user_id),
            additional_claims={"role": "STUDENT"},
        )
        self.token_student2 = create_access_token(
            identity=str(self.user2.user_id),
            additional_claims={"role": "STUDENT"},
        )
        self.token_admin = create_access_token(
            identity=str(self.admin_user.user_id),
            additional_claims={"role": "ADMIN"},
        )

    def tearDown(self):
        db.session.rollback()
        # Clean test records
        for table in reversed(db.metadata.sorted_tables):
            db.session.execute(table.delete())
        db.session.commit()
        self.ctx.pop()

    # ----------------------------------------------------
    # GRADING POLICY TESTS
    # ----------------------------------------------------

    def test_determine_grade_and_points(self):
        grade, gp, status = determine_grade_and_points(marks=92.0)
        self.assertEqual(grade, "A+")
        self.assertEqual(gp, Decimal("9.20"))
        self.assertEqual(status, "PASS")

        grade, gp, status = determine_grade_and_points(marks=86.0)
        self.assertEqual(grade, "A")
        self.assertEqual(gp, Decimal("8.60"))
        self.assertEqual(status, "PASS")

        grade, gp, status = determine_grade_and_points(marks=35.0)
        self.assertEqual(grade, "F")
        self.assertEqual(gp, Decimal("0.00"))
        self.assertEqual(status, "FAIL")

    def test_gpa_calculations(self):
        class DummyResult:
            def __init__(self, credits, grade_points, status="PASS"):
                self.credits = credits
                self.grade_points = grade_points
                self.status = status

        results = [
            DummyResult(4, 8.5),
            DummyResult(4, 7.5),
            DummyResult(2, 9.0),
        ]
        # (4*8.5 + 4*7.5 + 2*9.0) / 10 = (34 + 30 + 18) / 10 = 82 / 10 = 8.20
        sgpa = calculate_sgpa(results)
        self.assertEqual(sgpa, 8.20)
        self.assertEqual(calculate_credits_earned(results), 10)

    # ----------------------------------------------------
    # API AUTHORIZATION & EMPTY STATE TESTS
    # ----------------------------------------------------

    def test_unauthenticated_overview_denied(self):
        res = self.client.get("/api/student/academic-records/overview")
        self.assertEqual(res.status_code, 401)

    def test_empty_overview_returns_clean_state(self):
        res = self.client.get(
            "/api/student/academic-records/overview",
            headers={"Authorization": f"Bearer {self.token_student1}"},
        )
        self.assertEqual(res.status_code, 200)
        payload = res.get_json()
        self.assertTrue(payload["success"])
        metrics = payload["data"]["metrics"]
        self.assertIsNone(metrics["current_gpa"])
        self.assertIsNone(metrics["cgpa"])
        self.assertFalse(metrics["has_published_results"])
        self.assertEqual(payload["data"]["student"]["enrollment_no"], "STU2024001")

    def test_empty_results_returns_empty_list(self):
        res = self.client.get(
            "/api/student/academic-records/results",
            headers={"Authorization": f"Bearer {self.token_student1}"},
        )
        self.assertEqual(res.status_code, 200)
        payload = res.get_json()
        self.assertTrue(payload["success"])
        self.assertEqual(payload["data"]["results"], [])
        self.assertIsNone(payload["data"]["sgpa"])

    # ----------------------------------------------------
    # PUBLISHED VS UNPUBLISHED & CROSS-STUDENT ISOLATION
    # ----------------------------------------------------

    def test_published_vs_unpublished_results(self):
        # Result 1: Published for Student 1
        res1 = AcademicResult(
            student_id=self.student1.student_id,
            course_id=self.course1.course_id,
            academic_year="2024-2025",
            semester=6,
            credits=4,
            marks_obtained=86.0,
            grade="A",
            grade_points=Decimal("8.50"),
            status="PASS",
            is_published=True,
        )
        # Result 2: Unpublished draft for Student 1
        res2 = AcademicResult(
            student_id=self.student1.student_id,
            course_id=self.course2.course_id,
            academic_year="2024-2025",
            semester=6,
            credits=4,
            marks_obtained=78.0,
            grade="B+",
            grade_points=Decimal("7.50"),
            status="PASS",
            is_published=False,  # NOT published!
        )
        db.session.add_all([res1, res2])
        db.session.commit()

        # Student 1 query
        resp = self.client.get(
            "/api/student/academic-records/results?semester=6",
            headers={"Authorization": f"Bearer {self.token_student1}"},
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()["data"]
        # Only the published record should be returned
        self.assertEqual(len(data["results"]), 1)
        self.assertEqual(data["results"][0]["subject_code"], "CSE101")
        self.assertEqual(data["sgpa"], 8.5)

    def test_cross_student_isolation(self):
        # Result for Student 1
        res1 = AcademicResult(
            student_id=self.student1.student_id,
            course_id=self.course1.course_id,
            academic_year="2024-2025",
            semester=6,
            credits=4,
            marks_obtained=90.0,
            grade="A+",
            grade_points=Decimal("9.00"),
            status="PASS",
            is_published=True,
        )
        # Result for Student 2
        res2 = AcademicResult(
            student_id=self.student2.student_id,
            course_id=self.course2.course_id,
            academic_year="2024-2025",
            semester=6,
            credits=4,
            marks_obtained=60.0,
            grade="B",
            grade_points=Decimal("6.00"),
            status="PASS",
            is_published=True,
        )
        db.session.add_all([res1, res2])
        db.session.commit()

        # When Student 1 requests results, they must only see their own
        resp1 = self.client.get(
            "/api/student/academic-records/results",
            headers={"Authorization": f"Bearer {self.token_student1}"},
        )
        results1 = resp1.get_json()["data"]["results"]
        self.assertEqual(len(results1), 1)
        self.assertEqual(results1[0]["subject_code"], "CSE101")

        # When Student 2 requests results, they must only see Student 2's
        resp2 = self.client.get(
            "/api/student/academic-records/results",
            headers={"Authorization": f"Bearer {self.token_student2}"},
        )
        results2 = resp2.get_json()["data"]["results"]
        self.assertEqual(len(results2), 1)
        self.assertEqual(results2[0]["subject_code"], "CSE102")

    # ----------------------------------------------------
    # MULTI-SEMESTER PROGRESSION & EXPORT TESTS
    # ----------------------------------------------------

    def test_performance_history_progression(self):
        # Add Semester 5 result
        res_sem5 = AcademicResult(
            student_id=self.student1.student_id,
            course_id=self.course3.course_id,
            academic_year="2024-2025",
            semester=5,
            credits=2,
            marks_obtained=90.0,
            grade="A+",
            grade_points=Decimal("9.00"),
            status="PASS",
            is_published=True,
        )
        # Add Semester 6 result
        res_sem6 = AcademicResult(
            student_id=self.student1.student_id,
            course_id=self.course1.course_id,
            academic_year="2024-2025",
            semester=6,
            credits=4,
            marks_obtained=80.0,
            grade="A",
            grade_points=Decimal("8.00"),
            status="PASS",
            is_published=True,
        )
        db.session.add_all([res_sem5, res_sem6])
        db.session.commit()

        resp = self.client.get(
            "/api/student/academic-records/performance-history",
            headers={"Authorization": f"Bearer {self.token_student1}"},
        )
        self.assertEqual(resp.status_code, 200)
        history = resp.get_json()["data"]
        self.assertEqual(len(history), 2)
        self.assertEqual(history[0]["semester"], 5)
        self.assertEqual(history[0]["gpa"], 9.0)
        self.assertEqual(history[1]["semester"], 6)
        self.assertEqual(history[1]["gpa"], 8.0)
        # Progressive CGPA: (2*9.0 + 4*8.0) / 6 = (18 + 32) / 6 = 50 / 6 = 8.33
        self.assertEqual(history[1]["cgpa"], 8.33)

    def test_export_report_csv(self):
        res1 = AcademicResult(
            student_id=self.student1.student_id,
            course_id=self.course1.course_id,
            academic_year="2024-2025",
            semester=6,
            credits=4,
            marks_obtained=86.0,
            grade="A",
            grade_points=Decimal("8.50"),
            status="PASS",
            is_published=True,
        )
        db.session.add(res1)
        db.session.commit()

        resp = self.client.get(
            "/api/student/academic-records/export?semester=6&format=csv",
            headers={"Authorization": f"Bearer {self.token_student1}"},
        )
        self.assertEqual(resp.status_code, 200)
        self.assertIn("text/csv", resp.headers["Content-Type"])
        content = resp.data.decode("utf-8")
        self.assertIn("STU2024001", content)
        self.assertIn("CSE101", content)
        self.assertIn("Data Structures", content)

    def test_export_report_pdf_default(self):
        res1 = AcademicResult(
            student_id=self.student1.student_id,
            course_id=self.course1.course_id,
            academic_year="2024-2025",
            semester=6,
            credits=4,
            marks_obtained=86.0,
            grade="A",
            grade_points=Decimal("8.50"),
            status="PASS",
            is_published=True,
        )
        db.session.add(res1)
        db.session.commit()

        # Omit format parameter to verify PDF is default
        resp = self.client.get(
            "/api/student/academic-records/export?semester=6",
            headers={"Authorization": f"Bearer {self.token_student1}"},
        )
        self.assertEqual(resp.status_code, 200)
        self.assertIn("application/pdf", resp.headers["Content-Type"])
        self.assertTrue(resp.data.startswith(b"%PDF-"))
        self.assertIn("Academic_Grade_Card_STU2024001_Sem6", resp.headers["Content-Disposition"])
