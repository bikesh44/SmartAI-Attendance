import unittest
from flask import Flask
from sqlalchemy.pool import StaticPool
from app.extensions import bcrypt, db
from app.models import User
from app.routes.auth import auth_bp
from datetime import timedelta
from http.cookies import SimpleCookie
from flask_jwt_extended import (
    JWTManager,
    create_access_token,
    decode_token,
)
class TestAuthentication(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = Flask(__name__)
        cls.app.config.update(
            JWT_ACCESS_TOKEN_EXPIRES=timedelta(minutes=30),
            TESTING=True,
            SECRET_KEY="test-secret",
            JWT_SECRET_KEY="test-jwt-secret-key-32-bytes-long",
            SQLALCHEMY_DATABASE_URI="sqlite://",
            SQLALCHEMY_TRACK_MODIFICATIONS=False,
            SQLALCHEMY_ENGINE_OPTIONS={
                "poolclass": StaticPool,
                "connect_args": {"check_same_thread": False},
            },
            JWT_TOKEN_LOCATION=["headers", "cookies"],
            JWT_COOKIE_CSRF_PROTECT=False,
        )

        db.init_app(cls.app)
        bcrypt.init_app(cls.app)
        JWTManager(cls.app)
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

            password_hash = bcrypt.generate_password_hash(
                "CorrectPassword123!"
            ).decode("utf-8")

            self.user = User(
                name="Test Student",
                email="student@test.local",
                password_hash=password_hash,
                role="STUDENT",
            )
            db.session.add(self.user)
            db.session.commit()

            self.user_id = self.user.user_id

            self.token = create_access_token(
                identity=str(self.user_id),
                additional_claims={"role": "STUDENT"},
            )

    def auth_headers(self):
        return {"Authorization": f"Bearer {self.token}"}

    def test_login_success(self):
        response = self.client.post(
            "/api/auth/login",
            json={
                "email": "student@test.local",
                "password": "CorrectPassword123!",
            },
        )

        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        self.assertTrue(body["success"])
        self.assertEqual(body["message"], "Login successful")
        self.assertEqual(body["data"]["email"], "student@test.local")
        self.assertEqual(body["data"]["role"], "STUDENT")
        self.assertIn("access_token_cookie", response.headers.get("Set-Cookie", ""))

    def test_login_normalizes_email(self):
        response = self.client.post(
            "/api/auth/login",
            json={
                "email": "  STUDENT@TEST.LOCAL  ",
                "password": "CorrectPassword123!",
            },
        )

        self.assertEqual(response.status_code, 200)

    def test_login_missing_credentials(self):
        response = self.client.post(
            "/api/auth/login",
            json={"email": "student@test.local"},
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.get_json()["success"])

    def test_login_empty_body(self):
        response = self.client.post(
            "/api/auth/login",
            json={},
        )

        self.assertEqual(response.status_code, 400)

    def test_login_unknown_email(self):
        response = self.client.post(
            "/api/auth/login",
            json={
                "email": "unknown@test.local",
                "password": "CorrectPassword123!",
            },
        )

        self.assertEqual(response.status_code, 401)
        self.assertEqual(
            response.get_json()["message"],
            "Invalid email or password",
        )

    def test_login_wrong_password(self):
        response = self.client.post(
            "/api/auth/login",
            json={
                "email": "student@test.local",
                "password": "WrongPassword!",
            },
        )

        self.assertEqual(response.status_code, 401)

    def test_me_returns_authenticated_user(self):
        response = self.client.get(
            "/api/auth/me",
            headers=self.auth_headers(),
        )

        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        self.assertTrue(body["success"])
        self.assertEqual(body["data"]["user_id"], self.user_id)
        self.assertEqual(body["data"]["name"], "Test Student")
        self.assertEqual(body["data"]["role"], "STUDENT")

    def test_me_requires_authentication(self):
        response = self.client.get("/api/auth/me")

        self.assertEqual(response.status_code, 401)

    def test_me_returns_404_for_deleted_user(self):
        with self.app.app_context():
            user = db.session.get(User, self.user_id)
            db.session.delete(user)
            db.session.commit()

        response = self.client.get(
            "/api/auth/me",
            headers=self.auth_headers(),
        )

        self.assertEqual(response.status_code, 404)
        self.assertFalse(response.get_json()["success"])

    def test_protected_route_allows_authenticated_user(self):
        response = self.client.get(
            "/api/auth/protected-test",
            headers=self.auth_headers(),
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.get_json()["success"])

    def test_protected_route_rejects_anonymous_user(self):
        response = self.client.get("/api/auth/protected-test")

        self.assertEqual(response.status_code, 401)

    def test_admin_route_rejects_student(self):
        response = self.client.get(
            "/api/auth/admin-test",
            headers=self.auth_headers(),
        )

        self.assertEqual(response.status_code, 403)

    def test_logout_clears_auth_cookies(self):
        response = self.client.post("/api/auth/logout")

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.get_json()["success"])
        self.assertIn("access_token_cookie", response.headers.get("Set-Cookie", ""))


    def _login_and_decode_token(self, role, email):
        with self.app.app_context():
            password_hash = bcrypt.generate_password_hash(
                "CorrectPassword123!"
            ).decode("utf-8")

            user = User(
                name=f"Test {role.title()}",
                email=email,
                password_hash=password_hash,
                role=role,
            )
            db.session.add(user)
            db.session.commit()

        response = self.client.post(
            "/api/auth/login",
            json={
                "email": email,
                "password": "CorrectPassword123!",
            },
        )

        self.assertEqual(response.status_code, 200)

        cookies = SimpleCookie()
        for header in response.headers.getlist("Set-Cookie"):
            cookies.load(header)

        self.assertIn("access_token_cookie", cookies)

        with self.app.app_context():
            return decode_token(
                cookies["access_token_cookie"].value
            )

    def test_admin_login_token_expires_after_three_hours(self):
        claims = self._login_and_decode_token(
            "ADMIN",
            "admin@test.local",
        )

        self.assertEqual(
            claims["exp"] - claims["iat"],
            3 * 60 * 60,
        )

    def test_student_login_uses_configured_default_expiry(self):
        claims = self._login_and_decode_token(
            "STUDENT",
            "another-student@test.local",
        )

        self.assertEqual(
            claims["exp"] - claims["iat"],
            30 * 60,
        )

if __name__ == "__main__":
    unittest.main()
