import unittest
from flask import Flask
from flask_jwt_extended import JWTManager, create_access_token
from sqlalchemy.pool import StaticPool

from app.extensions import bcrypt, db
from app.models import (
    Batch,
    Course,
    CourseOffering,
    Department,
    Enrollment,
    Student,
    User,
)
from app.routes.admin import admin_bp
from app.routes.enrollment import enrollment_bp


class TestEnrollmentManagement(unittest.TestCase):
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
        cls.app.register_blueprint(enrollment_bp)

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
                department_name="Computer Science Engineering",
                department_code="CSE",
            )
            batch = Batch(batch_name="2024-2028")
            db.session.add_all([self.admin_user, dept, batch])
            db.session.commit()

            self.dept_id = dept.department_id
            self.batch_id = batch.batch_id
            self.admin_id = self.admin_user.user_id

            self.admin_token = create_access_token(
                identity=str(self.admin_id),
                additional_claims={"role": "ADMIN"},
            )
            self.admin_headers = {
                "Authorization": f"Bearer {self.admin_token}",
                "Content-Type": "application/json",
            }

    def test_summary_requires_admin(self):
        res = self.client.get("/api/admin/enrollments/summary")
        self.assertIn(res.status_code, [401, 403])

    def test_summary_and_enriched_enrollments(self):
        with self.app.app_context():
            c1 = Course(
                department_id=self.dept_id,
                course_code="CS501",
                course_name="Theory of Computation",
                semester=5,
                credits=4,
                batch="2024",
                is_active=True,
            )
            c2 = Course(
                department_id=self.dept_id,
                course_code="CS502",
                course_name="Database Systems",
                semester=5,
                credits=4,
                batch="2024",
                is_active=True,
            )
            db.session.add_all([c1, c2])
            db.session.commit()
            c1_id = c1.course_id
            c2_id = c2.course_id

            off1 = CourseOffering(
                course_id=c1.course_id,
                academic_year="2025-2026",
                semester=5,
                section="A",
            )
            off2 = CourseOffering(
                course_id=c2.course_id,
                academic_year="2025-2026",
                semester=5,
                section="A",
            )
            db.session.add_all([off1, off2])
            db.session.commit()

            u1 = User(name="John Doe", email="john@test.com", role="STUDENT", is_active=True, password_hash="h")
            u2 = User(name="Jane Smith", email="jane@test.com", role="STUDENT", is_active=True, password_hash="h")
            db.session.add_all([u1, u2])
            db.session.commit()

            s1 = Student(
                user_id=u1.user_id,
                enrollment_no="CSE2024001",
                department_id=self.dept_id,
                batch_id=self.batch_id,
                semester=5,
                section="A",
                academic_year="2024-2028",
            )
            s2 = Student(
                user_id=u2.user_id,
                enrollment_no="CSE2024002",
                department_id=self.dept_id,
                batch_id=self.batch_id,
                semester=5,
                section="A",
                academic_year="2024-2028",
            )
            db.session.add_all([s1, s2])
            db.session.commit()

            enr1 = Enrollment(student_id=s1.student_id, offering_id=off1.offering_id, status="ACTIVE")
            db.session.add(enr1)
            db.session.commit()
            enr1_id = enr1.enrollment_id

        # Test summary endpoint
        res = self.client.get("/api/admin/enrollments/summary", headers=self.admin_headers)
        self.assertEqual(res.status_code, 200)
        body = res.get_json()
        self.assertTrue(body["success"])
        data = body["data"]
        self.assertEqual(data["total_enrollments"], 1)
        self.assertEqual(data["active_enrollments"], 1)
        self.assertEqual(data["total_groups"], 1)
        group = data["groups"][0]
        self.assertEqual(group["department_code"], "CSE")
        self.assertEqual(group["semester"], 5)
        self.assertEqual(group["section"], "A")
        self.assertEqual(group["total_students"], 2)
        self.assertEqual(group["enrolled_students"], 1)
        self.assertEqual(group["pending_students"], 1)
        self.assertEqual(group["status"], "Incomplete")

        # Test list enrollments enriched data
        res_list = self.client.get("/api/admin/enrollments", headers=self.admin_headers)
        self.assertEqual(res_list.status_code, 200)
        list_body = res_list.get_json()
        self.assertEqual(len(list_body["data"]), 1)
        item = list_body["data"][0]
        self.assertEqual(item["student_name"], "John Doe")
        self.assertEqual(item["enrollment_no"], "CSE2024001")
        self.assertEqual(item["course_code"], "CS501")
        self.assertEqual(item["course_name"], "Theory of Computation")
        self.assertEqual(item["credits"], 4)

        # Test preview group enrollment
        preview_payload = {
            "department_id": self.dept_id,
            "cohort": "2024-2028",
            "semester": 5,
            "section": "A",
        }
        res_prev = self.client.post("/api/admin/enrollments/group-preview", json=preview_payload, headers=self.admin_headers)
        self.assertEqual(res_prev.status_code, 200)
        prev_data = res_prev.get_json()["data"]
        self.assertEqual(prev_data["eligible_students"], 2)
        self.assertEqual(len(prev_data["students"]), 2)
        self.assertEqual(prev_data["courses"][0]["credits"], 4)

        # Test selective bulk enrollment (enroll second student in second course)
        bulk_payload = {
            "department_id": self.dept_id,
            "cohort": "2024-2028",
            "semester": 5,
            "section": "A",
            "course_ids": [c2_id],
        }
        res_bulk = self.client.post("/api/admin/enrollments/group-bulk", json=bulk_payload, headers=self.admin_headers)
        self.assertIn(res_bulk.status_code, [200, 201])

        # Test delete enrollment
        res_del = self.client.delete(f"/api/admin/enrollments/{enr1_id}", headers=self.admin_headers)
        self.assertEqual(res_del.status_code, 200)


if __name__ == "__main__":
    unittest.main()
