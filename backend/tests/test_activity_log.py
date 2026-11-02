import unittest
from flask import Flask
from sqlalchemy.pool import StaticPool
from flask_jwt_extended import JWTManager, create_access_token

from app.extensions import bcrypt, db
from app.models import ActivityLog, Department, User
from app.routes.admin import admin_bp
from app.routes.auth import auth_bp
from app.services.activity_service import record_activity, serialize_activity_log


class TestActivityLogging(unittest.TestCase):
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
            JWT_COOKIE_CSRF_PROTECT=False,
        )

        db.init_app(cls.app)
        bcrypt.init_app(cls.app)
        JWTManager(cls.app)
        cls.app.register_blueprint(admin_bp)
        cls.app.register_blueprint(auth_bp)

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

            pw_hash = bcrypt.generate_password_hash("Password123!").decode("utf-8")

            self.admin = User(
                name="Test Admin",
                email="admin@test.local",
                password_hash=pw_hash,
                role="ADMIN",
            )
            self.student = User(
                name="Test Student",
                email="student@test.local",
                password_hash=pw_hash,
                role="STUDENT",
            )
            db.session.add_all([self.admin, self.student])
            db.session.commit()

            self.admin_id = self.admin.user_id
            self.student_id = self.student.user_id

            self.admin_token = create_access_token(
                identity=str(self.admin_id),
                additional_claims={"role": "ADMIN"},
            )
            self.student_token = create_access_token(
                identity=str(self.student_id),
                additional_claims={"role": "STUDENT"},
            )

    def admin_headers(self):
        return {"Authorization": f"Bearer {self.admin_token}"}

    def student_headers(self):
        return {"Authorization": f"Bearer {self.student_token}"}

    def test_empty_activity_history(self):
        """When no activity exists, returns an empty list successfully."""
        res = self.client.get("/api/admin/activity/recent", headers=self.admin_headers())
        self.assertEqual(res.status_code, 200)
        body = res.get_json()
        self.assertTrue(body["success"])
        self.assertEqual(body["data"], [])

    def test_unauthorized_user_cannot_access_activity(self):
        """Non-admin users cannot access the activity API."""
        res = self.client.get("/api/admin/activity/recent", headers=self.student_headers())
        self.assertEqual(res.status_code, 403)

        res_no_auth = self.client.get("/api/admin/activity/recent")
        self.assertEqual(res_no_auth.status_code, 401)

    def test_activity_ordered_newest_first(self):
        """Activities are ordered newest first (descending by created_at and id)."""
        with self.app.app_context():
            record_activity("EVENT_1", "First event")
            record_activity("EVENT_2", "Second event")
            record_activity("EVENT_3", "Third event")

        res = self.client.get("/api/admin/activity/recent", headers=self.admin_headers())
        self.assertEqual(res.status_code, 200)
        items = res.get_json()["data"]
        self.assertEqual(len(items), 3)
        self.assertEqual(items[0]["action_type"], "EVENT_3")
        self.assertEqual(items[1]["action_type"], "EVENT_2")
        self.assertEqual(items[2]["action_type"], "EVENT_1")

    def test_limit_validated_and_capped(self):
        """Limit parameter is capped between 1 and 50."""
        with self.app.app_context():
            for i in range(15):
                record_activity(f"EVENT_{i}", f"Event {i}")

        # Limit 5
        res = self.client.get("/api/admin/activity/recent?limit=5", headers=self.admin_headers())
        self.assertEqual(len(res.get_json()["data"]), 5)

        # Default is 10
        res_default = self.client.get("/api/admin/activity/recent", headers=self.admin_headers())
        self.assertEqual(len(res_default.get_json()["data"]), 10)

    def test_user_login_creates_activity(self):
        """Successful login records a USER_LOGIN event."""
        res = self.client.post(
            "/api/auth/login",
            json={"email": "admin@test.local", "password": "Password123!"},
        )
        self.assertEqual(res.status_code, 200)

        with self.app.app_context():
            log = ActivityLog.query.filter_by(action_type="USER_LOGIN").first()
            self.assertIsNotNone(log)
            self.assertEqual(log.actor_id, self.admin_id)
            self.assertIn("logged in", log.description)

    def test_failed_login_does_not_create_activity(self):
        """Failed login attempts do not record a successful USER_LOGIN event."""
        res = self.client.post(
            "/api/auth/login",
            json={"email": "admin@test.local", "password": "WrongPassword!"},
        )
        self.assertEqual(res.status_code, 401)

        with self.app.app_context():
            log = ActivityLog.query.filter_by(action_type="USER_LOGIN").first()
            self.assertIsNone(log)

    def test_department_create_creates_activity(self):
        """Creating a department records a DEPARTMENT_CREATED activity."""
        res = self.client.post(
            "/api/admin/departments",
            headers=self.admin_headers(),
            json={"department_name": "Mechanical Engineering", "department_code": "ME"},
        )
        self.assertEqual(res.status_code, 201)

        with self.app.app_context():
            log = ActivityLog.query.filter_by(action_type="DEPARTMENT_CREATED").first()
            self.assertIsNotNone(log)
            self.assertEqual(log.entity_type, "Department")
            self.assertIn("Mechanical Engineering", log.description)

    def test_paginated_activity_endpoint(self):
        """The /api/admin/activity endpoint supports pagination."""
        with self.app.app_context():
            for i in range(25):
                record_activity(f"EVENT_{i}", f"Event {i}")

        res = self.client.get("/api/admin/activity?page=1&limit=10", headers=self.admin_headers())
        self.assertEqual(res.status_code, 200)
        body = res.get_json()
        self.assertEqual(len(body["data"]), 10)
        self.assertEqual(body["pagination"]["total"], 25)
        self.assertEqual(body["pagination"]["pages"], 3)
