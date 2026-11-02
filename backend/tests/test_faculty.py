import unittest

from flask import Flask
from flask_jwt_extended import JWTManager, create_access_token
from sqlalchemy.pool import StaticPool

from app.extensions import bcrypt, db
from app.models import (
    AttendanceSession,
    Course,
    CourseOffering,
    Department,
    Faculty,
    User,
)
from app.routes.admin import admin_bp


class TestAdminFaculty(unittest.TestCase):
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

            self.department = Department(
                department_name="Computer Science",
                department_code="CSE",
            )
            db.session.add(self.department)
            db.session.flush()

            admin = User(
                name="Test Admin",
                email="admin@test.local",
                password_hash="not-used",
                role="ADMIN",
            )
            faculty_user = User(
                name="Test Faculty",
                email="faculty@test.local",
                password_hash="not-used",
                role="FACULTY",
            )
            db.session.add_all([admin, faculty_user])
            db.session.flush()

            self.admin_token = create_access_token(
                identity=str(admin.user_id),
                additional_claims={"role": "ADMIN"},
            )
            self.faculty_token = create_access_token(
                identity=str(faculty_user.user_id),
                additional_claims={"role": "FACULTY"},
            )

            self.faculty = Faculty(
                user_id=faculty_user.user_id,
                department_id=self.department.department_id,
                employee_id="FAC-001",
                designation="Lecturer",
            )
            db.session.add(self.faculty)
            db.session.commit()
            self.faculty_id = self.faculty.faculty_id
            self.faculty_user_id = faculty_user.user_id
            self.department_id = self.department.department_id

    def admin_headers(self):
        return {"Authorization": f"Bearer {self.admin_token}"}

    def test_list_faculty(self):
        response = self.client.get(
            "/api/admin/faculty",
            headers=self.admin_headers(),
        )
        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        self.assertTrue(body["success"])
        self.assertEqual(len(body["data"]), 1)
        self.assertEqual(body["data"][0]["employee_id"], "FAC-001")

    def test_get_faculty_detail(self):
        response = self.client.get(
            f"/api/admin/faculty/{self.faculty_id}",
            headers=self.admin_headers(),
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.get_json()["data"]["designation"],
            "Lecturer",
        )

    def test_missing_faculty_returns_404(self):
        response = self.client.get(
            "/api/admin/faculty/99999",
            headers=self.admin_headers(),
        )
        self.assertEqual(response.status_code, 404)

    def test_faculty_routes_require_admin(self):
        response = self.client.get(
            "/api/admin/faculty",
            headers={"Authorization": f"Bearer {self.faculty_token}"},
        )
        self.assertEqual(response.status_code, 403)

    def test_create_faculty(self):
        with self.app.app_context():
            user = User(
                name="New Faculty",
                email="newfaculty@test.local",
                password_hash="not-used",
                role="FACULTY",
            )
            db.session.add(user)
            db.session.commit()
            new_user_id = user.user_id

        response = self.client.post(
            "/api/admin/faculty",
            headers=self.admin_headers(),
            json={
                "user_id": new_user_id,
                "employee_id": "FAC-002",
                "designation": "Assistant Professor",
                "department_id": self.department_id,
            },
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(
            response.get_json()["data"]["employee_id"],
            "FAC-002",
        )

    def test_create_faculty_rejects_missing_fields(self):
        response = self.client.post(
            "/api/admin/faculty",
            headers=self.admin_headers(),
            json={},
        )
        self.assertEqual(response.status_code, 400)

    def test_create_faculty_rejects_missing_user(self):
        response = self.client.post(
            "/api/admin/faculty",
            headers=self.admin_headers(),
            json={
                "user_id": 99999,
                "employee_id": "FAC-999",
                "designation": "Lecturer",
                "department_id": self.department_id,
            },
        )
        self.assertEqual(response.status_code, 404)

    def test_create_faculty_rejects_duplicate_employee_id(self):
        with self.app.app_context():
            user = User(
                name="Second Faculty",
                email="secondfaculty@test.local",
                password_hash="not-used",
                role="FACULTY",
            )
            db.session.add(user)
            db.session.commit()
            new_user_id = user.user_id

        response = self.client.post(
            "/api/admin/faculty",
            headers=self.admin_headers(),
            json={
                "user_id": new_user_id,
                "employee_id": "FAC-001",
                "designation": "Lecturer",
                "department_id": self.department_id,
            },
        )
        self.assertEqual(response.status_code, 409)

    def test_update_faculty(self):
        response = self.client.patch(
            f"/api/admin/faculty/{self.faculty_id}",
            headers=self.admin_headers(),
            json={"designation": "Associate Professor"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.get_json()["data"]["designation"],
            "Associate Professor",
        )

    def test_update_faculty_rejects_user_fields(self):
        response = self.client.patch(
            f"/api/admin/faculty/{self.faculty_id}",
            headers=self.admin_headers(),
            json={"name": "Changed Name"},
        )
        self.assertEqual(response.status_code, 400)

    def test_delete_faculty(self):
        response = self.client.delete(
            f"/api/admin/faculty/{self.faculty_id}",
            headers=self.admin_headers(),
        )
        self.assertEqual(response.status_code, 200)

        with self.app.app_context():
            self.assertIsNone(
                db.session.get(Faculty, self.faculty_id)
            )
            self.assertIsNotNone(
                db.session.get(User, self.faculty_user_id)
            )

    def test_delete_missing_faculty_returns_404(self):
        response = self.client.delete(
            "/api/admin/faculty/99999",
            headers=self.admin_headers(),
        )
        self.assertEqual(response.status_code, 404)

    def test_get_faculty_summary(self):
        response = self.client.get(
            "/api/admin/faculty/summary",
            headers=self.admin_headers(),
        )
        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        self.assertTrue(body["success"])
        data = body["data"]
        self.assertEqual(data["total_faculty"], 1)
        self.assertEqual(data["total_departments"], 1)
        self.assertIn("total_classes", data)
        self.assertIn("active_semesters", data)

    def test_get_faculty_filter_options(self):
        response = self.client.get(
            "/api/admin/faculty/filter-options",
            headers=self.admin_headers(),
        )
        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        self.assertTrue(body["success"])
        data = body["data"]
        self.assertIn("departments", data)
        self.assertIn("semesters", data)
        self.assertIn("courses", data)
        self.assertEqual(len(data["departments"]), 1)

    def test_get_faculty_detail_includes_classes_and_schedule(self):
        response = self.client.get(
            f"/api/admin/faculty/{self.faculty_id}",
            headers=self.admin_headers(),
        )
        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        self.assertTrue(body["success"])
        data = body["data"]
        self.assertIn("classes", data)
        self.assertIn("schedule", data)
        self.assertIn("assigned_courses", data)
        self.assertIn("phone", data)


if __name__ == "__main__":
    unittest.main()
