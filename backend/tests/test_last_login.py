import unittest
from datetime import datetime, timedelta
from flask import Flask
from sqlalchemy.pool import StaticPool
from flask_jwt_extended import JWTManager, create_access_token

from app.extensions import bcrypt, db
from app.models import User
from app.routes.auth import auth_bp
from app.routes.admin import admin_bp


class TestLastLoginTracking(unittest.TestCase):
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
        cls.app.register_blueprint(auth_bp)
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

            pw_hash = bcrypt.generate_password_hash("Secret123!").decode("utf-8")

            self.admin = User(
                name="Admin User",
                email="admin@test.local",
                password_hash=pw_hash,
                role="ADMIN",
            )
            self.user = User(
                name="Regular Student",
                email="student@test.local",
                password_hash=pw_hash,
                role="STUDENT",
            )
            db.session.add_all([self.admin, self.user])
            db.session.commit()

            self.admin_id = self.admin.user_id
            self.user_id = self.user.user_id

            self.admin_token = create_access_token(
                identity=str(self.admin_id),
                additional_claims={"role": "ADMIN"},
            )

    def admin_headers(self):
        return {"Authorization": f"Bearer {self.admin_token}"}

    def test_new_user_has_none_last_login(self):
        """A user who has never logged in has last_login as None."""
        with self.app.app_context():
            u = db.session.get(User, self.user_id)
            self.assertIsNone(u.last_login)

    def test_failed_login_does_not_update_last_login(self):
        """Failed login attempts must not touch last_login."""
        response = self.client.post(
            "/api/auth/login",
            json={
                "email": "student@test.local",
                "password": "WrongPassword!",
            },
        )
        self.assertEqual(response.status_code, 401)

        with self.app.app_context():
            u = db.session.get(User, self.user_id)
            self.assertIsNone(u.last_login)

    def test_successful_login_updates_last_login_to_real_utc_time(self):
        """Successful login records the actual UTC timestamp."""
        before = datetime.utcnow()

        response = self.client.post(
            "/api/auth/login",
            json={
                "email": "student@test.local",
                "password": "Secret123!",
            },
        )
        self.assertEqual(response.status_code, 200)

        after = datetime.utcnow()

        with self.app.app_context():
            u = db.session.get(User, self.user_id)
            self.assertIsNotNone(u.last_login)
            self.assertTrue(before <= u.last_login <= after)

    def test_subsequent_failed_login_does_not_overwrite_previous_login(self):
        """Failed attempts must preserve previous successful login timestamp."""
        # 1. Login successfully
        res1 = self.client.post(
            "/api/auth/login",
            json={
                "email": "student@test.local",
                "password": "Secret123!",
            },
        )
        self.assertEqual(res1.status_code, 200)

        with self.app.app_context():
            saved_time = db.session.get(User, self.user_id).last_login
            self.assertIsNotNone(saved_time)

        # 2. Failed login attempt
        res2 = self.client.post(
            "/api/auth/login",
            json={
                "email": "student@test.local",
                "password": "WrongPassword!",
            },
        )
        self.assertEqual(res2.status_code, 401)

        with self.app.app_context():
            after_fail_time = db.session.get(User, self.user_id).last_login
            self.assertEqual(saved_time, after_fail_time)

    def test_admin_users_api_returns_null_for_unauthenticated_user(self):
        """The user-management API returns null when user has never logged in."""
        res = self.client.get("/api/admin/users", headers=self.admin_headers())
        self.assertEqual(res.status_code, 200)
        data = res.get_json()["data"]

        student_data = next((x for x in data if x["user_id"] == self.user_id), None)
        self.assertIsNotNone(student_data)
        self.assertIsNone(student_data["last_login"])

    def test_admin_users_api_returns_iso_with_z_after_login(self):
        """The user-management API returns ISO timestamp with Z timezone indicator."""
        # Log in
        self.client.post(
            "/api/auth/login",
            json={
                "email": "student@test.local",
                "password": "Secret123!",
            },
        )

        res = self.client.get("/api/admin/users", headers=self.admin_headers())
        self.assertEqual(res.status_code, 200)
        data = res.get_json()["data"]

        student_data = next((x for x in data if x["user_id"] == self.user_id), None)
        self.assertIsNotNone(student_data)
        self.assertTrue(isinstance(student_data["last_login"], str))
        self.assertTrue(student_data["last_login"].endswith("Z"))

    def test_multiple_admin_refreshes_show_same_persisted_timestamp(self):
        """Multiple fetches must not fabricate or update the timestamp."""
        self.client.post(
            "/api/auth/login",
            json={
                "email": "student@test.local",
                "password": "Secret123!",
            },
        )

        res1 = self.client.get("/api/admin/users", headers=self.admin_headers())
        res2 = self.client.get("/api/admin/users", headers=self.admin_headers())

        ts1 = next(x for x in res1.get_json()["data"] if x["user_id"] == self.user_id)["last_login"]
        ts2 = next(x for x in res2.get_json()["data"] if x["user_id"] == self.user_id)["last_login"]

        self.assertEqual(ts1, ts2)
