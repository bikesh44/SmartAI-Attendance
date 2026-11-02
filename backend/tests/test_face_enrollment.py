import io
import unittest
from unittest.mock import patch

import numpy as np
import cv2
from flask import Flask
from flask_jwt_extended import JWTManager, create_access_token
from sqlalchemy.pool import StaticPool

from app.extensions import db
from app.models import (
    User,
    Department,
    Student,
    Faculty,
    Course,
    CourseOffering,
    Enrollment,
    FaceProfile,
    AttendanceSession,
    AttendanceRecord,
)
from app.routes.face import face_bp


class TestFaceEnrollmentAPI(unittest.TestCase):

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
                "connect_args": {
                    "check_same_thread": False,
                },
            },
            JWT_TOKEN_LOCATION=["headers"],
        )

        db.init_app(cls.app)
        JWTManager(cls.app)

        cls.app.register_blueprint(face_bp)

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
            self.department = Department(
                department_name="Computer Science",
                department_code="CSE",
            )
            db.session.add(self.department)
            db.session.flush()

            self.user = User(
                name="Test Student",
                email="student@test.local",
                password_hash="test-password",
                role="STUDENT",
            )
            db.session.add(self.user)
            db.session.flush()

            self.student = Student(
                user_id=self.user.user_id,
                department_id=self.department.department_id,
                enrollment_no="TEST001",
                semester=6,
                section="A",
                academic_year="2026-27",
            )
            db.session.add(self.student)
            db.session.commit()

            self.student_id = self.student.student_id

    def tearDown(self):
        with self.app.app_context():
            AttendanceRecord.query.delete()
            AttendanceSession.query.delete()
            FaceProfile.query.delete()
            Enrollment.query.delete()
            CourseOffering.query.delete()
            Course.query.delete()
            Faculty.query.delete()
            Student.query.delete()
            User.query.delete()
            Department.query.delete()
            db.session.commit()

    def _admin_headers(self):
        with self.app.app_context():
            token = create_access_token(
                identity="1",
                additional_claims={"role": "ADMIN"},
            )

        return {
            "Authorization": f"Bearer {token}",
        }

    def _image_file(self):
        image = np.zeros(
            (100,100,3),
            dtype = np.uint8,
        )
        success, encoded = cv2.imencode(
            ".jpg",
            image,
        )
        self.assertTrue(success)
        return(
            io.BytesIO(encoded.tobytes()),
            "face.jpg",
        )

    @patch("app.routes.face.face_service.enroll_student")
    def test_successful_enrollment(self, mock_enroll):
        encoding = np.ones(
            (1, 128),
            dtype=np.float32,
        )

        mock_enroll.return_value = {
            "status": "enrolled",
            "encoding": encoding,
        }

        response = self.client.post(
            "/api/face/enroll",
            headers=self._admin_headers(),
            data={
                "student_id": str(self.student_id),
                "image": self._image_file(),
            },
            content_type="multipart/form-data",
        )
        
        self.assertEqual(response.status_code, 201)

        body = response.get_json()

        self.assertTrue(body["success"])
        self.assertEqual(
            body["message"],
            "Face enrolled successfully",
        )
        self.assertEqual(
            body["data"]["student_id"],
            self.student_id,
        )
        self.assertEqual(
            body["data"]["status"],
            "enrolled",
        )

        with self.app.app_context():
            profile = FaceProfile.query.filter_by(
                student_id=self.student_id,
            ).first()

            self.assertIsNotNone(profile)

            self.assertEqual(
                profile.model_version,
                "sface_2021dec",
            )

            stored_encoding = np.frombuffer(
                profile.embedding,
                dtype=np.float32,
            ).reshape(1, 128)

            np.testing.assert_array_equal(
                stored_encoding,
                encoding,
            )

    def test_missing_authentication(self):
        response = self.client.post(
            "/api/face/enroll",
        )

        self.assertEqual(response.status_code, 401)

    def test_faculty_cannot_enroll_face(self):
        with self.app.app_context():
            token = create_access_token(
                identity="2",
                additional_claims={"role": "FACULTY"},
            )
        headers = {"Authorization": f"Bearer {token}"}
        response = self.client.post(
            "/api/face/enroll",
            headers=headers,
            data={
                "student_id": str(self.student_id),
                "image": self._image_file(),
            },
            content_type="multipart/form-data",
        )
        self.assertEqual(response.status_code, 403)

    def test_missing_student_id(self):
        response = self.client.post(
            "/api/face/enroll",
            headers=self._admin_headers(),
            data={
                "image": self._image_file(),
            },
            content_type="multipart/form-data",
        )

        self.assertEqual(response.status_code, 400)

        body = response.get_json()

        self.assertFalse(body["success"])
        self.assertEqual(
            body["message"],
            "student_id is required",
        )

    def test_invalid_student_id(self):
        response = self.client.post(
            "/api/face/enroll",
            headers=self._admin_headers(),
            data={
                "student_id": "abc",
                "image": self._image_file(),
            },
            content_type="multipart/form-data",
        )

        self.assertEqual(response.status_code, 400)

        body = response.get_json()

        self.assertEqual(
            body["message"],
            "student_id must be an integer",
        )

    def test_student_not_found(self):
        response = self.client.post(
            "/api/face/enroll",
            headers=self._admin_headers(),
            data={
                "student_id": "999999",
                "image": self._image_file(),
            },
            content_type="multipart/form-data",
        )

        self.assertEqual(response.status_code, 404)

        body = response.get_json()

        self.assertEqual(
            body["message"],
            "Student not found",
        )

    def test_missing_image(self):
        response = self.client.post(
            "/api/face/enroll",
            headers=self._admin_headers(),
            data={
                "student_id": str(self.student_id),
            },
            content_type="multipart/form-data",
        )

        self.assertEqual(response.status_code, 400)

        body = response.get_json()

        self.assertEqual(
            body["message"],
            "image is required",
        )

    @patch("app.routes.face.face_service.enroll_student")
    def test_invalid_image(self, mock_enroll):
        mock_enroll.return_value = {
            "status": "invalid_image",
            "encoding": None,
        }

        response = self.client.post(
            "/api/face/enroll",
            headers=self._admin_headers(),
            data={
                "student_id": str(self.student_id),
                "image": self._image_file(),
            },
            content_type="multipart/form-data",
        )

        self.assertEqual(response.status_code, 400)

        body = response.get_json()

        self.assertFalse(body["success"])
        self.assertEqual(
            body["status"],
            "invalid_image",
        )

    @patch("app.routes.face.face_service.enroll_student")
    def test_no_face(self, mock_enroll):
        mock_enroll.return_value = {
            "status": "no_face",
            "encoding": None,
        }

        response = self.client.post(
            "/api/face/enroll",
            headers=self._admin_headers(),
            data={
                "student_id": str(self.student_id),
                "image": self._image_file(),
            },
            content_type="multipart/form-data",
        )

        self.assertEqual(response.status_code, 400)

        body = response.get_json()

        self.assertEqual(
            body["status"],
            "no_face",
        )

    @patch("app.routes.face.face_service.enroll_student")
    def test_multiple_faces(self, mock_enroll):
        mock_enroll.return_value = {
            "status": "multiple_faces",
            "encoding": None,
        }

        response = self.client.post(
            "/api/face/enroll",
            headers=self._admin_headers(),
            data={
                "student_id": str(self.student_id),
                "image": self._image_file(),
            },
            content_type="multipart/form-data",
        )

        self.assertEqual(response.status_code, 400)

        body = response.get_json()

        self.assertEqual(
            body["status"],
            "multiple_faces",
        )

    @patch("app.routes.face.face_service.enroll_student")
    def test_encoding_failure(self, mock_enroll):
        mock_enroll.return_value = {
            "status": "encoding_failed",
            "encoding": None,
        }

        response = self.client.post(
            "/api/face/enroll",
            headers=self._admin_headers(),
            data={
                "student_id": str(self.student_id),
                "image": self._image_file(),
            },
            content_type="multipart/form-data",
        )

        self.assertEqual(response.status_code, 400)

        body = response.get_json()

        self.assertEqual(
            body["status"],
            "encoding_failed",
        )

    def test_face_status_registered(self):
        with self.app.app_context():
            profile = FaceProfile(
                student_id = self.student_id,
                embedding = np.zeros(
                    (1,128),
                    dtype = np.float32,
                ).tobytes(),
                model_version ="sface_2021dec",
                is_active = True,
            )
            db.session.add(profile)
            db.session.commit()
        response = self.client.get(
            f"/api/face/status/{self.student_id}",
            headers = self._admin_headers(),
        )
        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        self.assertTrue(body["success"])
        self.assertEqual(
            body["data"]["student_id"],
            self.student_id,
        )
        self.assertTrue(body["data"]["registered"])
        self.assertEqual(body["data"]["status"],"registered",)
        self.assertEqual(
            body["data"]["model_version"],
            "sface_2021dec",
        )
    def test_face_status_not_registered(self):
        response = self.client.get(
            f"/api/face/status/{self.student_id}",
            headers = self._admin_headers(),
        )
        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        self.assertTrue(body["success"])
        self.assertEqual(
            body["data"]["student_id"],
            self.student_id,
        )
        self.assertFalse(body["data"]["registered"])
        self.assertEqual(body["data"]["status"], "not_registered",)
        self.assertIsNone(body["data"]["model_version"],)

    def test_face_status_student_not_found(self):
        response = self.client.get(
            "/api/face/status/999999",
            headers = self._admin_headers(),
        )
        self.assertEqual(response.status_code, 404)
        body = response.get_json()
        self.assertFalse(body["success"])
        self.assertEqual(body["message"], "Student not found",)

    def test_face_status_missing_authentication(self):
        response = self.client.get(
            f"/api/face/status/{self.student_id}",
        )
        self.assertEqual(response.status_code, 401)
if __name__ == "__main__":
    unittest.main()
