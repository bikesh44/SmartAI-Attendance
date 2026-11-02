import unittest
from flask import Flask
from flask_jwt_extended import JWTManager, create_access_token
from sqlalchemy.pool import StaticPool

from app.extensions import bcrypt, db
from app.models import (
    Course,
    CourseOffering,
    Department,
    Enrollment,
    Faculty,
    Student,
    User,
)
from app.routes.admin import admin_bp


class TestAdminAcademicSummary(unittest.TestCase):
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
        bcrypt.init_app(cls.app)
        JWTManager(cls.app)
        cls.app.register_blueprint(admin_bp)

        with cls.app.app_context():
            db.create_all()

    @classmethod
    def tearDownClass(cls):
        with cls.app.app_context():
            db.session.remove()
            db.drop_all()

    def setUp(self):
        self.client = self.app.test_client()

        with self.app.app_context():
            db.session.remove()
            db.drop_all()
            db.create_all()

            self.admin_user = User(
                name="Admin User",
                email="admin@test.com",
                role="ADMIN",
                is_active=True,
                password_hash="fakehash",
            )

            dept = Department(
                department_name="Computer Science",
                department_code="CSE",
            )
            db.session.add_all([self.admin_user, dept])
            db.session.commit()

            self.dept_id = dept.department_id
            self.admin_id = self.admin_user.user_id

            self.admin_token = create_access_token(
                identity=str(self.admin_id),
                additional_claims={"role": "ADMIN"},
            )
            self.admin_headers = {
                "Authorization": f"Bearer {self.admin_token}",
                "Content-Type": "application/json",
            }

    def test_academic_summary_requires_admin(self):
        # Unauthenticated request
        response = self.client.get("/api/admin/academic/summary")
        self.assertIn(response.status_code, [401, 403])

        # Student user cannot access
        with self.app.app_context():
            student_user = User(
                name="Student User",
                email="student@test.com",
                role="STUDENT",
                is_active=True,
                password_hash="fakehash",
            )
            db.session.add(student_user)
            db.session.commit()
            student_token = create_access_token(
                identity=str(student_user.user_id),
                additional_claims={"role": "STUDENT"},
            )

        student_headers = {
            "Authorization": f"Bearer {student_token}",
            "Content-Type": "application/json",
        }
        res_student = self.client.get("/api/admin/academic/summary", headers=student_headers)
        self.assertEqual(res_student.status_code, 403)

    def test_academic_summary_empty_state(self):
        response = self.client.get("/api/admin/academic/summary", headers=self.admin_headers)
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data.get("success"))
        summary = data.get("data")
        self.assertEqual(summary["total_courses"], 0)
        self.assertEqual(summary["active_courses"], 0)
        self.assertEqual(summary["course_offerings"], 0)
        self.assertEqual(summary["enrollments"], 0)

    def test_academic_summary_accurate_counts(self):
        with self.app.app_context():
            # Create courses
            c1 = Course(
                department_id=self.dept_id,
                course_code="CS101",
                course_name="Intro to CS",
                semester=1,
                credits=4,
                batch="2024",
                is_active=True,
            )
            c2 = Course(
                department_id=self.dept_id,
                course_code="CS102",
                course_name="Data Structures",
                semester=2,
                credits=4,
                batch="2024",
                is_active=True,
            )
            c3 = Course(
                department_id=self.dept_id,
                course_code="CS103",
                course_name="Algorithms",
                semester=3,
                credits=4,
                batch="2024",
                is_active=False,
            )
            db.session.add_all([c1, c2, c3])
            db.session.commit()

            # Create offering
            offering = CourseOffering(
                course_id=c1.course_id,
                academic_year="2024-2025",
                semester=1,
                section="A",
            )
            db.session.add(offering)
            db.session.commit()

            # Create student user and student record
            student_user = User(
                name="Student 1",
                email="stu1@test.com",
                role="STUDENT",
                is_active=True,
                password_hash="fakehash",
            )
            db.session.add(student_user)
            db.session.commit()

            student = Student(
                user_id=student_user.user_id,
                enrollment_no="EN001",
                department_id=self.dept_id,
                semester=1,
                section="A",
                academic_year="2024-2025",
            )
            db.session.add(student)
            db.session.commit()

            # Create enrollment
            enrollment = Enrollment(
                student_id=student.student_id,
                offering_id=offering.offering_id,
                status="ACTIVE",
            )
            db.session.add(enrollment)
            db.session.commit()

        response = self.client.get("/api/admin/academic/summary", headers=self.admin_headers)
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data.get("success"))
        summary = data.get("data")
        self.assertEqual(summary["total_courses"], 3)
        self.assertEqual(summary["active_courses"], 2)
        self.assertEqual(summary["course_offerings"], 1)
        self.assertEqual(summary["enrollments"], 1)


if __name__ == "__main__":
    unittest.main()
