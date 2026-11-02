import os
import time
import unittest
from datetime import datetime, timedelta

from flask import Flask, jsonify
from flask_jwt_extended import JWTManager, create_access_token, get_csrf_token
from sqlalchemy.pool import StaticPool

from app.extensions import bcrypt, db
from app.models import Department, Student, User
from app.routes.auth import auth_bp
from app.routes.student import (
    PHOTOS_DIR,
    SIGNATURES_DIR,
    student_bp,
)
from app.utils.token_blocklist import TokenBlocklist, token_blocklist


class TestFinalSecurityRemediations(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = Flask(__name__)
        cls.app.config.update(
            TESTING=True,
            SECRET_KEY="test-secret-key-32-bytes-minimum-length!",
            JWT_SECRET_KEY="test-jwt-secret-key-32-bytes-long!",
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
        cls.jwt = JWTManager(cls.app)

        # Register blocklist callbacks matching app/__init__.py
        @cls.jwt.token_in_blocklist_loader
        def check_if_token_is_revoked(jwt_header, jwt_payload: dict):
            jti = jwt_payload.get("jti")
            return token_blocklist.is_revoked(jti)

        @cls.jwt.revoked_token_loader
        def revoked_token_callback(jwt_header, jwt_payload):
            return jsonify({
                "success": False,
                "message": "Token has been revoked",
            }), 401

        cls.app.register_blueprint(auth_bp)
        cls.app.register_blueprint(student_bp)

        with cls.app.app_context():
            db.create_all()

            # Create Department
            cls.dept = Department(
                department_name="Computer Science",
                department_code="CSE",
            )
            db.session.add(cls.dept)
            db.session.flush()

            # Create Admin User
            cls.admin_user = User(
                name="Admin User",
                email="admin@test.edu",
                password_hash=bcrypt.generate_password_hash("AdminPass123!").decode("utf-8"),
                role="ADMIN",
                is_active=True,
            )
            db.session.add(cls.admin_user)

            # Create Faculty User
            cls.faculty_user = User(
                name="Faculty User",
                email="faculty@test.edu",
                password_hash=bcrypt.generate_password_hash("FacultyPass123!").decode("utf-8"),
                role="FACULTY",
                is_active=True,
            )
            db.session.add(cls.faculty_user)

            # Create Student 1 User & Profile
            cls.student1_user = User(
                name="Student One",
                email="student1@test.edu",
                password_hash=bcrypt.generate_password_hash("StudentPass123!").decode("utf-8"),
                role="STUDENT",
                is_active=True,
            )
            db.session.add(cls.student1_user)
            db.session.flush()

            cls.student1 = Student(
                user_id=cls.student1_user.user_id,
                department_id=cls.dept.department_id,
                enrollment_no="CSE001",
                semester=3,
                section="A",
                academic_year="2026-2027",
            )
            db.session.add(cls.student1)

            # Create Student 2 User & Profile
            cls.student2_user = User(
                name="Student Two",
                email="student2@test.edu",
                password_hash=bcrypt.generate_password_hash("StudentPass123!").decode("utf-8"),
                role="STUDENT",
                is_active=True,
            )
            db.session.add(cls.student2_user)
            db.session.flush()

            cls.student2 = Student(
                user_id=cls.student2_user.user_id,
                department_id=cls.dept.department_id,
                enrollment_no="CSE002",
                semester=3,
                section="A",
                academic_year="2026-2027",
            )
            db.session.add(cls.student2)
            db.session.commit()

            cls.student1_id = cls.student1.student_id
            cls.student1_user_id = cls.student1_user.user_id
            cls.student2_id = cls.student2.student_id
            cls.student2_user_id = cls.student2_user.user_id
            cls.admin_user_id = cls.admin_user.user_id
            cls.faculty_user_id = cls.faculty_user.user_id

        cls.client = cls.app.test_client()

        # Create temporary sample files for student 1
        cls.photo_filename = f"student_photo_{cls.student1_id}_999999999.jpg"
        cls.sig_filename = f"student_sig_{cls.student1_id}_999999999.png"
        cls.photo_path = os.path.join(PHOTOS_DIR, cls.photo_filename)
        cls.sig_path = os.path.join(SIGNATURES_DIR, cls.sig_filename)

        with open(cls.photo_path, "wb") as f:
            f.write(b"MOCK_PHOTO_DATA_STUDENT_1")
        with open(cls.sig_path, "wb") as f:
            f.write(b"MOCK_SIGNATURE_DATA_STUDENT_1")

    @classmethod
    def tearDownClass(cls):
        # Clean up temporary test files
        if os.path.exists(cls.photo_path):
            try:
                os.remove(cls.photo_path)
            except OSError:
                pass
        if os.path.exists(cls.sig_path):
            try:
                os.remove(cls.sig_path)
            except OSError:
                pass

    def setUp(self):
        token_blocklist.clear()

    def get_auth_header(self, user_id, role, expires_delta=None):
        with self.app.app_context():
            kwargs = {}
            if expires_delta is not None:
                kwargs["expires_delta"] = expires_delta
            token = create_access_token(
                identity=str(user_id),
                additional_claims={"role": role},
                **kwargs,
            )
            return {"Authorization": f"Bearer {token}"}

    # ============================================================
    # PHASE 1: STUDENT UPLOADS AUTHORIZATION & TRAVERSAL (SEC-07)
    # ============================================================

    def test_student_upload_unauthenticated_rejected(self):
        """Unauthenticated requests to photos and signatures must return 401."""
        res_photo = self.client.get(f"/api/student/uploads/photos/{self.photo_filename}")
        self.assertEqual(res_photo.status_code, 401)

        res_sig = self.client.get(f"/api/student/uploads/signatures/{self.sig_filename}")
        self.assertEqual(res_sig.status_code, 401)

    def test_student_upload_invalid_category_rejected(self):
        """Folders other than photos and signatures must return 404."""
        headers = self.get_auth_header(self.admin_user_id, "ADMIN")
        res = self.client.get("/api/student/uploads/documents/some_file.pdf", headers=headers)
        self.assertEqual(res.status_code, 404)
        self.assertFalse(res.get_json()["success"])

    def test_student_upload_path_traversal_rejected(self):
        """Attempts to traverse directories with .. or slashes must return 400."""
        headers = self.get_auth_header(self.admin_user_id, "ADMIN")

        traversal_attempts = [
            "../etc/passwd",
            "..\\windows\\win.ini",
            "..%2F..%2Ftest.txt",
            f"student_photo_{self.student1_id}_999999999.jpg/..",
        ]
        for payload in traversal_attempts:
            res = self.client.get(f"/api/student/uploads/photos/{payload}", headers=headers)
            self.assertIn(res.status_code, [400, 404])

    def test_student_upload_cross_student_access_forbidden(self):
        """Student 2 attempting to view Student 1's photo or signature must receive 403."""
        headers_student2 = self.get_auth_header(self.student2_user_id, "STUDENT")

        # Student 2 accessing Student 1 photo -> 403
        res_photo = self.client.get(
            f"/api/student/uploads/photos/{self.photo_filename}",
            headers=headers_student2,
        )
        self.assertEqual(res_photo.status_code, 403)
        self.assertFalse(res_photo.get_json()["success"])

        # Student 2 accessing Student 1 signature -> 403
        res_sig = self.client.get(
            f"/api/student/uploads/signatures/{self.sig_filename}",
            headers=headers_student2,
        )
        self.assertEqual(res_sig.status_code, 403)
        self.assertFalse(res_sig.get_json()["success"])

    def test_student_upload_student_own_access_allowed(self):
        """Student 1 accessing their own photo and signature must succeed (200)."""
        headers_student1 = self.get_auth_header(self.student1_user_id, "STUDENT")

        res_photo = self.client.get(
            f"/api/student/uploads/photos/{self.photo_filename}",
            headers=headers_student1,
        )
        self.assertEqual(res_photo.status_code, 200)
        self.assertEqual(res_photo.data, b"MOCK_PHOTO_DATA_STUDENT_1")

        res_sig = self.client.get(
            f"/api/student/uploads/signatures/{self.sig_filename}",
            headers=headers_student1,
        )
        self.assertEqual(res_sig.status_code, 200)
        self.assertEqual(res_sig.data, b"MOCK_SIGNATURE_DATA_STUDENT_1")

    def test_student_upload_faculty_photo_allowed_signature_forbidden(self):
        """Faculty can view student photos (200) but MUST NOT view signatures (403)."""
        headers_faculty = self.get_auth_header(self.faculty_user_id, "FACULTY")

        # Faculty reading photo -> 200 OK
        res_photo = self.client.get(
            f"/api/student/uploads/photos/{self.photo_filename}",
            headers=headers_faculty,
        )
        self.assertEqual(res_photo.status_code, 200)
        self.assertEqual(res_photo.data, b"MOCK_PHOTO_DATA_STUDENT_1")

        # Faculty reading signature -> 403 Forbidden
        res_sig = self.client.get(
            f"/api/student/uploads/signatures/{self.sig_filename}",
            headers=headers_faculty,
        )
        self.assertEqual(res_sig.status_code, 403)
        self.assertFalse(res_sig.get_json()["success"])

    def test_student_upload_admin_allowed_both(self):
        """Admin can view both student photos and signatures."""
        headers_admin = self.get_auth_header(self.admin_user_id, "ADMIN")

        res_photo = self.client.get(
            f"/api/student/uploads/photos/{self.photo_filename}",
            headers=headers_admin,
        )
        self.assertEqual(res_photo.status_code, 200)

        res_sig = self.client.get(
            f"/api/student/uploads/signatures/{self.sig_filename}",
            headers=headers_admin,
        )
        self.assertEqual(res_sig.status_code, 200)

    def test_student_upload_missing_file_returns_404(self):
        """When authorized caller requests a non-existent file, return 404."""
        headers_admin = self.get_auth_header(self.admin_user_id, "ADMIN")
        missing_filename = f"student_photo_{self.student1_id}_111111111.jpg"
        res = self.client.get(
            f"/api/student/uploads/photos/{missing_filename}",
            headers=headers_admin,
        )
        self.assertEqual(res.status_code, 404)
        self.assertFalse(res.get_json()["success"])

    def test_student_upload_malformed_filename_rejected(self):
        """Malformed filenames that do not match the strict regex pattern must return 404."""
        headers = self.get_auth_header(self.admin_user_id, "ADMIN")
        malformed = [
            f"student_photo_{self.student1_id}_abc.jpg",
            f"student_photo_{self.student1_id}_123.exe",
            f"student_photo_notanid_123.jpg",
            f"student_sig_{self.student1_id}_123.sh",
        ]
        for name in malformed:
            res = self.client.get(f"/api/student/uploads/photos/{name}", headers=headers)
            self.assertEqual(res.status_code, 404)

    # ============================================================
    # PHASE 2: JWT LOGOUT AND SERVER-SIDE REVOCATION (SEC-05)
    # ============================================================

    def test_token_blocklist_manager_unit(self):
        """Unit tests for TokenBlocklist TTL and revocation logic."""
        tb = TokenBlocklist()
        self.assertFalse(tb.is_revoked("non-existent-jti"))

        # Revoke token with future exp
        tb.revoke("test-jti-1", time.time() + 100)
        self.assertTrue(tb.is_revoked("test-jti-1"))

        # Revoke token with past exp (already expired)
        tb.revoke("test-jti-expired", time.time() - 10)
        self.assertFalse(tb.is_revoked("test-jti-expired"))

    def test_jwt_logout_revokes_token_successfully(self):
        """Logging out with Bearer authentication must revoke token so subsequent requests are rejected."""
        # 1. Generate active token
        auth_headers = self.get_auth_header(self.student1_user_id, "STUDENT")

        # 2. Verify token works on protected endpoint
        res_valid = self.client.get("/api/auth/me", headers=auth_headers)
        self.assertEqual(res_valid.status_code, 200)

        # 3. Call logout with the active token
        res_logout = self.client.post("/api/auth/logout", headers=auth_headers)
        self.assertEqual(res_logout.status_code, 200)
        self.assertTrue(res_logout.get_json()["success"])

        # 4. Attempt to reuse the logged-out token -> must return 401 Revoked
        res_revoked = self.client.get("/api/auth/me", headers=auth_headers)
        self.assertEqual(res_revoked.status_code, 401)
        self.assertIn("revoked", res_revoked.get_json().get("message", "").lower())

    def test_jwt_logout_revokes_token_cookie_auth(self):
        """Logging out via cookie authentication must revoke token so subsequent requests are rejected."""
        with self.app.app_context():
            token = create_access_token(
                identity=str(self.student1_user_id),
                additional_claims={"role": "STUDENT"},
            )

        self.client.set_cookie("access_token_cookie", token)

        # 1. Verify access works with cookie
        res_me = self.client.get("/api/auth/me")
        self.assertEqual(res_me.status_code, 200)

        # 2. Call logout with cookie
        res_logout = self.client.post("/api/auth/logout")
        self.assertEqual(res_logout.status_code, 200)
        self.assertTrue(res_logout.get_json()["success"])

        # 3. Subsequent request with the same revoked token in cookie returns 401 Revoked
        self.client.set_cookie("access_token_cookie", token)
        res_revoked = self.client.get("/api/auth/me")
        self.assertEqual(res_revoked.status_code, 401)
        self.assertIn("revoked", res_revoked.get_json().get("message", "").lower())

    def test_jwt_expired_token_rejected(self):
        """Expired tokens must be rejected with 401."""
        expired_headers = self.get_auth_header(
            self.student1_user_id,
            "STUDENT",
            expires_delta=timedelta(seconds=-10),
        )
        res = self.client.get("/api/auth/me", headers=expired_headers)
        self.assertEqual(res.status_code, 401)


if __name__ == "__main__":
    unittest.main()
