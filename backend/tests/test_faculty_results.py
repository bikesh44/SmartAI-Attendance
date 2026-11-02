import unittest
from datetime import datetime
from decimal import Decimal
from flask import Flask
from flask_jwt_extended import JWTManager, create_access_token
from sqlalchemy.pool import StaticPool

from app.extensions import db
from app.models import (
    AcademicResult,
    ActivityLog,
    Assessment,
    Course,
    CourseOffering,
    Department,
    Enrollment,
    Faculty,
    ResultSubmission,
    Student,
    User,
)
from app.routes.faculty_results import faculty_results_bp


class TestFacultyResults(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = Flask(__name__)
        cls.app.config.update(
            TESTING=True,
            SECRET_KEY="test-faculty-results-secret",
            JWT_SECRET_KEY="test-jwt-faculty-results-key-32-bytes-long",
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
        cls.app.register_blueprint(faculty_results_bp)

        with cls.app.app_context():
            db.create_all()

    def setUp(self):
        self.client = self.app.test_client()
        self.ctx = self.app.app_context()
        self.ctx.push()

        db.session.remove()
        db.drop_all()
        db.create_all()

        # Create Department
        dept = Department(
            department_name="Computer Science & Engineering",
            department_code="CSE",
        )
        db.session.add(dept)
        db.session.commit()

        # Create Users
        admin_user = User(
            name="Admin User",
            email="admin@test.edu",
            password_hash="test_hash",
            role="ADMIN",
            is_active=True,
        )
        faculty_user = User(
            name="Dr. Farhan Das",
            email="farhan@test.edu",
            password_hash="test_hash",
            role="FACULTY",
            is_active=True,
        )
        other_faculty_user = User(
            name="Prof. Other",
            email="other@test.edu",
            password_hash="test_hash",
            role="FACULTY",
            is_active=True,
        )
        student_user1 = User(
            name="Aarav Sharma",
            email="aarav@test.edu",
            password_hash="test_hash",
            role="STUDENT",
            is_active=True,
        )
        student_user2 = User(
            name="Diya Patel",
            email="diya@test.edu",
            password_hash="test_hash",
            role="STUDENT",
            is_active=True,
        )
        db.session.add_all([admin_user, faculty_user, other_faculty_user, student_user1, student_user2])
        db.session.commit()

        # Create Faculty Entities
        fac = Faculty(
            user_id=faculty_user.user_id,
            department_id=dept.department_id,
            employee_id="FAC001",
            designation="Associate Professor",
        )
        other_fac = Faculty(
            user_id=other_faculty_user.user_id,
            department_id=dept.department_id,
            employee_id="FAC002",
            designation="Assistant Professor",
        )
        db.session.add_all([fac, other_fac])
        db.session.commit()

        # Create Student Entities
        stu1 = Student(
            user_id=student_user1.user_id,
            department_id=dept.department_id,
            enrollment_no="CS001",
            semester=4,
            section="A",
            academic_year="2024-2025",
        )
        stu2 = Student(
            user_id=student_user2.user_id,
            department_id=dept.department_id,
            enrollment_no="CS002",
            semester=4,
            section="A",
            academic_year="2024-2025",
        )
        db.session.add_all([stu1, stu2])
        db.session.commit()

        # Create Course & Offerings
        course = Course(
            course_code="CS101",
            course_name="Computer Science",
            department_id=dept.department_id,
            credits=4,
            semester=4,
        )
        db.session.add(course)
        db.session.commit()

        # Offering 1: Assigned to Dr. Farhan Das
        offering = CourseOffering(
            course_id=course.course_id,
            faculty_id=fac.faculty_id,
            academic_year="2024-2025",
            semester=4,
            section="A",
        )
        # Offering 2: Assigned to other faculty
        other_offering = CourseOffering(
            course_id=course.course_id,
            faculty_id=other_fac.faculty_id,
            academic_year="2024-2025",
            semester=4,
            section="B",
        )
        db.session.add_all([offering, other_offering])
        db.session.commit()

        # Enrollments
        enr1 = Enrollment(
            student_id=stu1.student_id,
            offering_id=offering.offering_id,
            status="ACTIVE",
        )
        enr2 = Enrollment(
            student_id=stu2.student_id,
            offering_id=offering.offering_id,
            status="ACTIVE",
        )
        db.session.add_all([enr1, enr2])
        db.session.commit()

        self.admin_id = admin_user.user_id
        self.faculty_id = faculty_user.user_id
        self.other_faculty_id = other_faculty_user.user_id
        self.student_id = student_user1.user_id
        self.stu1_id = stu1.student_id
        self.stu2_id = stu2.student_id
        self.offering_id = offering.offering_id
        self.other_offering_id = other_offering.offering_id

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def get_token(self, user_id, role):
        return create_access_token(
            identity=str(user_id),
            additional_claims={"role": role},
        )

    def test_faculty_can_get_assigned_courses(self):
        """Faculty receives assigned offerings; unassigned offerings are excluded."""
        token = self.get_token(self.faculty_id, "FACULTY")
        res = self.client.get(
            "/api/faculty/results/courses",
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(res.status_code, 200)
        json_data = res.get_json()
        self.assertTrue(json_data["success"])
        offerings = json_data["data"]
        self.assertEqual(len(offerings), 1)
        self.assertEqual(offerings[0]["course_code"], "CS101")
        self.assertEqual(offerings[0]["enrolled_count"], 2)

    def test_faculty_can_get_and_create_assessments(self):
        """Standard assessments are provisioned automatically; faculty can add custom assessments."""
        token = self.get_token(self.faculty_id, "FACULTY")

        # GET assessments (auto-seeds defaults)
        res = self.client.get(
            f"/api/faculty/results/assessments?offering_id={self.offering_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(res.status_code, 200)
        data = res.get_json()["data"]
        self.assertGreaterEqual(len(data), 5)
        self.assertTrue(any(a["assessment_name"] == "Internal Test 1" for a in data))

        # POST custom assessment
        res2 = self.client.post(
            "/api/faculty/results/assessments",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "offering_id": self.offering_id,
                "assessment_name": "Quiz 1",
                "assessment_type": "INTERNAL",
                "max_marks": 20,
                "weightage": 10,
            },
        )
        self.assertEqual(res2.status_code, 201)
        self.assertTrue(res2.get_json()["success"])

    def test_faculty_can_get_summary_cards(self):
        """Summary card metrics reflect real database enrollments and submission counts."""
        token = self.get_token(self.faculty_id, "FACULTY")
        res = self.client.get(
            f"/api/faculty/results/summary?offering_id={self.offering_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(res.status_code, 200)
        data = res.get_json()["data"]
        self.assertEqual(data["total_students"], 2)
        self.assertEqual(data["submission_status"], "NOT_STARTED")

    def test_faculty_can_get_students_for_entry(self):
        """Loads enrolled students with roll numbers, max marks, and pending status."""
        token = self.get_token(self.faculty_id, "FACULTY")
        res = self.client.get(
            f"/api/faculty/results/students?offering_id={self.offering_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(res.status_code, 200)
        data = res.get_json()["data"]
        self.assertEqual(len(data["students"]), 2)
        self.assertEqual(data["students"][0]["roll_no"], "CS001")
        self.assertEqual(data["students"][0]["status"], "Pending")

    def test_faculty_can_save_draft_marks(self):
        """Saving draft creates DRAFT submission, calculates grades, keeps unpublished."""
        token = self.get_token(self.faculty_id, "FACULTY")
        res = self.client.post(
            "/api/faculty/results/save-draft",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "offering_id": self.offering_id,
                "scores": [
                    {"student_id": self.stu1_id, "marks_obtained": 26.0, "remarks": "Good work"},
                    {"student_id": self.stu2_id, "marks_obtained": 22.0, "remarks": ""},
                ],
            },
        )
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.get_json()["success"])
        self.assertEqual(res.get_json()["data"]["status"], "DRAFT")

        # Check DB directly
        sub = ResultSubmission.query.filter_by(offering_id=self.offering_id).first()
        self.assertIsNotNone(sub)
        self.assertEqual(sub.status, "DRAFT")
        results = AcademicResult.query.filter_by(offering_id=self.offering_id).all()
        self.assertEqual(len(results), 2)
        self.assertFalse(results[0].is_published)

    def test_faculty_can_submit_for_review(self):
        """Submitting results transitions to SUBMITTED and logs activity."""
        token = self.get_token(self.faculty_id, "FACULTY")
        res = self.client.post(
            "/api/faculty/results/submit",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "offering_id": self.offering_id,
                "scores": [
                    {"student_id": self.stu1_id, "marks_obtained": 26.0, "remarks": "Excellent"},
                    {"student_id": self.stu2_id, "marks_obtained": 22.0, "remarks": "Good"},
                ],
            },
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.get_json()["data"]["status"], "SUBMITTED")

        # Verify activity log
        log = ActivityLog.query.filter_by(action_type="RESULT_SUBMITTED").first()
        self.assertIsNotNone(log)

    def test_faculty_cannot_modify_unassigned_course(self):
        """Faculty cannot view or submit marks for courses they do not teach (403 Forbidden)."""
        token = self.get_token(self.faculty_id, "FACULTY")
        res = self.client.get(
            f"/api/faculty/results/students?offering_id={self.other_offering_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(res.status_code, 403)

    def test_student_forbidden(self):
        """Students are strictly forbidden from accessing faculty result endpoints."""
        token = self.get_token(self.student_id, "STUDENT")
        res = self.client.get(
            "/api/faculty/results/courses",
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(res.status_code, 403)

    def test_csv_import_validation(self):
        """CSV import validates roll numbers, bounds, and flags invalid records."""
        token = self.get_token(self.faculty_id, "FACULTY")
        res = self.client.post(
            "/api/faculty/results/import",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "offering_id": self.offering_id,
                "rows": [
                    {"roll_no": "CS001", "marks_obtained": 28, "remarks": "Top score"},
                    {"roll_no": "CS999", "marks_obtained": 25, "remarks": "Fake roll"},
                    {"roll_no": "CS002", "marks_obtained": 999, "remarks": "Out of bounds"},
                ],
            },
        )
        self.assertEqual(res.status_code, 200)
        data = res.get_json()["data"]
        self.assertEqual(len(data["valid_records"]), 1)
        self.assertEqual(data["valid_records"][0]["roll_no"], "CS001")
        self.assertEqual(len(data["errors"]), 2)


if __name__ == "__main__":
    unittest.main()
