import concurrent.futures
import io
import json
import time
import unittest
from datetime import date, datetime, time as py_time
from unittest.mock import patch

import cv2
import numpy as np
from flask import Flask
from flask_jwt_extended import JWTManager, create_access_token
from sqlalchemy.pool import StaticPool

from app.extensions import db
from app.models import (
    AttendanceRecord,
    AttendanceSession,
    Course,
    CourseOffering,
    Department,
    Enrollment,
    FaceProfile,
    Faculty,
    Student,
    User,
)
from app.routes.attendance import attendance_bp
from app.routes.recognition import recognition_bp
from app.services.cv.liveness_service import (
    CHALLENGE_TURN_LEFT,
    CHALLENGE_TURN_RIGHT,
    CHALLENGE_NOD_DOWN,
    CHALLENGE_BLINK,
    liveness_manager,
    pad_detector,
    PresentationAttackDetector,
)


class TestLivenessDetectionAndAntiSpoofing(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = Flask(__name__)
        cls.app.config.update(
            TESTING=True,
            REQUIRE_LIVENESS_VERIFICATION=True,
            SECRET_KEY="test-liveness-secret",
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
        JWTManager(cls.app)
        cls.app.register_blueprint(recognition_bp)
        cls.app.register_blueprint(attendance_bp)

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
            self.dept = Department(
                department_name="Computer Science",
                department_code="CSE",
            )
            db.session.add(self.dept)
            db.session.flush()

            self.faculty_user = User(
                name="Prof. Sharma",
                email="sharma@test.local",
                password_hash="pwd",
                role="FACULTY",
            )
            db.session.add(self.faculty_user)
            db.session.flush()

            self.faculty = Faculty(
                user_id=self.faculty_user.user_id,
                department_id=self.dept.department_id,
                employee_id="FAC101",
                designation="Professor",
            )
            db.session.add(self.faculty)
            db.session.flush()

            # Second faculty for cross-faculty authorization tests
            self.other_faculty_user = User(
                name="Prof. Gupta",
                email="gupta@test.local",
                password_hash="pwd",
                role="FACULTY",
            )
            db.session.add(self.other_faculty_user)
            db.session.flush()

            self.other_faculty = Faculty(
                user_id=self.other_faculty_user.user_id,
                department_id=self.dept.department_id,
                employee_id="FAC102",
                designation="Associate Professor",
            )
            db.session.add(self.other_faculty)
            db.session.flush()

            # Admin user for manual attendance tests
            self.admin_user = User(
                name="Admin User",
                email="admin@test.local",
                password_hash="pwd",
                role="ADMIN",
            )
            db.session.add(self.admin_user)
            db.session.flush()

            # Student 1
            self.student1_user = User(
                name="Student One",
                email="s1@test.local",
                password_hash="pwd",
                role="STUDENT",
            )
            db.session.add(self.student1_user)
            db.session.flush()

            self.student1 = Student(
                user_id=self.student1_user.user_id,
                department_id=self.dept.department_id,
                enrollment_no="STU001",
                semester=6,
                section="A",
                academic_year="2026-27",
            )
            db.session.add(self.student1)
            db.session.flush()

            # Student 2
            self.student2_user = User(
                name="Student Two",
                email="s2@test.local",
                password_hash="pwd",
                role="STUDENT",
            )
            db.session.add(self.student2_user)
            db.session.flush()

            self.student2 = Student(
                user_id=self.student2_user.user_id,
                department_id=self.dept.department_id,
                enrollment_no="STU002",
                semester=6,
                section="A",
                academic_year="2026-27",
            )
            db.session.add(self.student2)
            db.session.flush()

            # Course & Offering
            self.course = Course(
                department_id=self.dept.department_id,
                course_code="CSE601",
                course_name="Machine Learning",
                semester=6,
                credits=4,
            )
            db.session.add(self.course)
            db.session.flush()

            self.offering = CourseOffering(
                course_id=self.course.course_id,
                faculty_id=self.faculty.faculty_id,
                academic_year="2026-27",
                semester=6,
                section="A",
            )
            db.session.add(self.offering)
            db.session.flush()

            # Enrollments
            self.enr1 = Enrollment(
                student_id=self.student1.student_id,
                offering_id=self.offering.offering_id,
                status="ACTIVE",
            )
            self.enr2 = Enrollment(
                student_id=self.student2.student_id,
                offering_id=self.offering.offering_id,
                status="ACTIVE",
            )
            db.session.add_all([self.enr1, self.enr2])
            db.session.flush()

            # Active attendance session
            now = datetime.now()
            self.session = AttendanceSession(
                offering_id=self.offering.offering_id,
                faculty_id=self.faculty.faculty_id,
                session_date=now.date(),
                start_time=py_time(0, 0, 1),
                end_time=py_time(23, 59, 59),
                status="ACTIVE",
            )
            db.session.add(self.session)
            db.session.flush()

            # Face profile for student 1
            self.profile1 = FaceProfile(
                student_id=self.student1.student_id,
                embedding=np.ones((1, 128), dtype=np.float32).tobytes(),
                model_version="sface_2021dec",
                is_active=True,
            )
            db.session.add(self.profile1)
            db.session.commit()

            self.session_id = self.session.session_id
            self.student1_id = self.student1.student_id
            self.student2_id = self.student2.student_id
            self.faculty_id = self.faculty.faculty_id
            self.faculty_user_id = self.faculty_user.user_id
            self.other_faculty_user_id = self.other_faculty_user.user_id
            self.admin_user_id = self.admin_user.user_id

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

    def _auth_headers(self, user_id: int, role: str = "FACULTY"):
        with self.app.app_context():
            token = create_access_token(
                identity=str(user_id),
                additional_claims={"role": role},
            )
        return {"Authorization": f"Bearer {token}"}

    def _create_sample_face_frame(self, variation: str = "center") -> np.ndarray:
        """Create a synthetic realistic face frame with skin tones and landmarks."""
        img = np.full((320, 320, 3), (220, 220, 220), dtype=np.uint8)
        # Skin ellipse
        center = (160, 160)
        axes = (70, 95)
        # BGR skin tone: B=140, G=170, R=215
        cv2.ellipse(img, center, axes, 0, 0, 360, (140, 170, 215), -1)

        # Eyes
        if variation == "left":
            # Head turned left: eye positions and nose shifted
            cv2.circle(img, (135, 135), 8, (60, 60, 60), -1)
            cv2.circle(img, (175, 135), 8, (60, 60, 60), -1)
            cv2.circle(img, (145, 165), 6, (120, 140, 190), -1)
        elif variation == "right":
            # Head turned right
            cv2.circle(img, (145, 135), 8, (60, 60, 60), -1)
            cv2.circle(img, (185, 135), 8, (60, 60, 60), -1)
            cv2.circle(img, (175, 165), 6, (120, 140, 190), -1)
        elif variation == "nod":
            cv2.circle(img, (140, 135), 8, (60, 60, 60), -1)
            cv2.circle(img, (180, 135), 8, (60, 60, 60), -1)
            cv2.circle(img, (160, 185), 6, (120, 140, 190), -1)
        else:
            cv2.circle(img, (140, 135), 8, (60, 60, 60), -1)
            cv2.circle(img, (180, 135), 8, (60, 60, 60), -1)
            cv2.circle(img, (160, 165), 6, (120, 140, 190), -1)

        # Mouth
        cv2.ellipse(img, (160, 205), (20, 8), 0, 0, 180, (80, 80, 170), -1)
        return img

    def _frame_to_bytes_io(self, img: np.ndarray, filename: str = "frame.jpg"):
        _, enc = cv2.imencode(".jpg", img)
        return io.BytesIO(enc.tobytes()), filename

    # =========================================================================
    # 1. Challenge Issuance & Randomization Tests
    # =========================================================================

    def test_challenge_issuance_success(self):
        """Test authenticated faculty can request a fresh randomized challenge."""
        headers = self._auth_headers(self.faculty_user_id, "FACULTY")
        response = self.client.post(
            "/api/faculty/recognition/liveness/challenge",
            headers=headers,
            json={"session_id": self.session_id},
        )
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data["success"])
        self.assertIn("challenge_id", data)
        self.assertIn("challenge_type", data)
        self.assertIn("instruction", data)
        self.assertIn("nonce", data)
        self.assertEqual(data["session_id"], self.session_id)

    def test_challenge_issuance_forbidden_for_other_faculty(self):
        """Test unauthorized faculty cannot request a challenge for another faculty's session."""
        headers = self._auth_headers(self.other_faculty_user_id, "FACULTY")
        response = self.client.post(
            "/api/faculty/recognition/liveness/challenge",
            headers=headers,
            json={"session_id": self.session_id},
        )
        self.assertEqual(response.status_code, 403)

    # =========================================================================
    # 2. Presentation Attack Detection (PAD) Tests
    # =========================================================================

    def test_printed_photograph_rejection(self):
        """Test that printed photo with halftone pattern / desaturation is rejected by PAD."""
        # Create image with excessive high frequency periodic noise (printer halftone dots)
        img = self._create_sample_face_frame("center")
        h, w = img.shape[:2]
        # Inject artificial halftone dot noise
        noise = np.random.normal(0, 45, (h, w)).astype(np.float32)
        spoof_img = np.clip(img.astype(np.float32) + noise[:, :, None], 0, 255).astype(np.uint8)

        # Test PAD detector directly
        pad_res = pad_detector.analyze_frame(spoof_img)
        self.assertFalse(pad_res.is_live)
        self.assertIn(pad_res.attack_type, ["printed_photo_detected", "screen_replay_detected"])

    def test_screen_replay_moiré_rejection(self):
        """Test that screen display photo with high-frequency moiré patterns is rejected."""
        img = self._create_sample_face_frame("center")
        h, w = img.shape[:2]
        # Add periodic moiré grid lines (typical of screen pixel pitch beat frequencies)
        grid = np.zeros((h, w), dtype=np.float32)
        grid[::4, :] += 50
        grid[:, ::4] += 50
        spoof_screen = np.clip(img.astype(np.float32) + grid[:, :, None], 0, 255).astype(np.uint8)

        pad_res = pad_detector.analyze_frame(spoof_screen)
        self.assertFalse(pad_res.is_live)
        self.assertEqual(pad_res.attack_type, "screen_replay_detected")

    def test_screen_replay_rejected_in_verification_endpoint(self):
        """Test evidence submission endpoint rejects screen replay presentation attacks."""
        challenge = liveness_manager.create_challenge(self.session_id, self.faculty_id)
        headers = self._auth_headers(self.faculty_user_id, "FACULTY")

        # Create screen replay spoof frames
        img = self._create_sample_face_frame("center")
        h, w = img.shape[:2]
        grid = np.zeros((h, w), dtype=np.float32)
        grid[::4, :] += 55
        grid[:, ::4] += 55
        spoof_frame = np.clip(img.astype(np.float32) + grid[:, :, None], 0, 255).astype(np.uint8)

        f0 = self._frame_to_bytes_io(spoof_frame, "f0.jpg")
        f1 = self._frame_to_bytes_io(spoof_frame, "f1.jpg")

        response = self.client.post(
            "/api/faculty/recognition/liveness/verify",
            headers=headers,
            data={
                "session_id": str(self.session_id),
                "challenge_id": challenge["challenge_id"],
                "frames": [f0, f1],
            },
            content_type="multipart/form-data",
        )
        self.assertEqual(response.status_code, 400)
        data = response.get_json()
        self.assertFalse(data["success"])
        self.assertEqual(data["status"], "spoof_suspected")

    # =========================================================================
    # 3. Active Liveness Movement & Anti-Replay Tests
    # =========================================================================

    def test_static_photograph_replay_rejected(self):
        """Test submitting the exact same static photo across frames is rejected as a static replay."""
        challenge = liveness_manager.create_challenge(self.session_id, self.faculty_id)
        headers = self._auth_headers(self.faculty_user_id, "FACULTY")

        # Clean genuine-looking frame submitted twice with zero movement
        img = self._create_sample_face_frame("center")
        f0 = self._frame_to_bytes_io(img, "f0.jpg")
        f1 = self._frame_to_bytes_io(img, "f1.jpg")

        # Mock face detector so frame difference check is reached
        with patch("app.routes.recognition.face_service.detect_faces") as mock_detect:
            mock_detect.return_value = [{
                "bbox": [50, 50, 150, 150],
                "landmarks": [[80, 80], [140, 80], [110, 110], [90, 140], [130, 140]],
                "confidence": 0.95,
            }]
            response = self.client.post(
                "/api/faculty/recognition/liveness/verify",
                headers=headers,
                data={
                    "session_id": str(self.session_id),
                    "challenge_id": challenge["challenge_id"],
                    "frames": [f0, f1],
                },
                content_type="multipart/form-data",
            )
            self.assertEqual(response.status_code, 400)
            data = response.get_json()
            self.assertFalse(data["success"])
            self.assertEqual(data["status"], "challenge_failed")
            self.assertIn("Static photograph", data["message"])

    def test_failed_or_incomplete_challenge(self):
        """Test that user who does not move in the requested direction fails active verification."""
        challenge = liveness_manager.create_challenge(self.session_id, self.faculty_id)
        challenge_type = challenge["challenge_type"]

        headers = self._auth_headers(self.faculty_user_id, "FACULTY")

        img0 = self._create_sample_face_frame("center")
        img1 = self._create_sample_face_frame("center")
        # Add slight natural camera jitter so it's not a static frame
        img1[0, 0, 0] = (int(img1[0, 0, 0]) + 15) % 255

        f0 = self._frame_to_bytes_io(img0, "f0.jpg")
        f1 = self._frame_to_bytes_io(img1, "f1.jpg")

        # Landmarks have zero pose displacement
        with patch("app.routes.recognition.face_service.detect_faces") as mock_detect:
            mock_detect.return_value = [{
                "bbox": [50, 50, 150, 150],
                "landmarks": [[80, 80], [140, 80], [110, 110], [90, 140], [130, 140]],
                "confidence": 0.95,
            }]
            response = self.client.post(
                "/api/faculty/recognition/liveness/verify",
                headers=headers,
                data={
                    "session_id": str(self.session_id),
                    "challenge_id": challenge["challenge_id"],
                    "frames": [f0, f1],
                },
                content_type="multipart/form-data",
            )
            self.assertEqual(response.status_code, 400)
            data = response.get_json()
            self.assertEqual(data["status"], "challenge_failed")

    def test_expired_challenge_rejected(self):
        """Test that submitting evidence for an expired challenge is rejected."""
        challenge = liveness_manager.create_challenge(self.session_id, self.faculty_id)
        # Manually expire challenge
        liveness_manager._challenges[challenge["challenge_id"]]["expires_at"] = time.time() - 10

        headers = self._auth_headers(self.faculty_user_id, "FACULTY")
        img0 = self._create_sample_face_frame("center")
        img1 = self._create_sample_face_frame("left")
        f0 = self._frame_to_bytes_io(img0, "f0.jpg")
        f1 = self._frame_to_bytes_io(img1, "f1.jpg")

        response = self.client.post(
            "/api/faculty/recognition/liveness/verify",
            headers=headers,
            data={
                "session_id": str(self.session_id),
                "challenge_id": challenge["challenge_id"],
                "frames": [f0, f1],
            },
            content_type="multipart/form-data",
        )
        self.assertEqual(response.status_code, 400)
        data = response.get_json()
        self.assertEqual(data["status"], "challenge_expired")

    # =========================================================================
    # 4. Genuine Live-User Success & Verification Token Issuance
    # =========================================================================

    def test_genuine_live_user_verification_and_attendance_flow(self):
        """Test full successful lifecycle: challenge -> evidence -> token -> attendance marking."""
        # 1. Request challenge
        challenge = liveness_manager.create_challenge(self.session_id, self.faculty_id)
        # Set challenge type to TURN_HEAD_LEFT
        liveness_manager._challenges[challenge["challenge_id"]]["challenge_type"] = CHALLENGE_TURN_LEFT
        challenge_id = challenge["challenge_id"]

        headers = self._auth_headers(self.faculty_user_id, "FACULTY")

        img0 = self._create_sample_face_frame("center")
        img1 = self._create_sample_face_frame("left")
        f0 = self._frame_to_bytes_io(img0, "f0.jpg")
        f1 = self._frame_to_bytes_io(img1, "f1.jpg")

        # Frame 0: Frontal landmarks. Frame 1: Left-turned landmarks
        lm_center = [[80, 80], [140, 80], [110, 110], [90, 140], [130, 140]]
        lm_left = [[80, 80], [140, 80], [88, 110], [90, 140], [130, 140]]

        detect_calls = {"count": 0}

        def mock_detect_side_effect(frame):
            call_idx = detect_calls["count"]
            detect_calls["count"] += 1
            if call_idx % 2 == 1:
                return [{"bbox": [50, 50, 150, 150], "landmarks": lm_left, "confidence": 0.95}]
            return [{"bbox": [50, 50, 150, 150], "landmarks": lm_center, "confidence": 0.95}]

        with patch("app.routes.recognition.face_service.detect_faces", side_effect=mock_detect_side_effect):
            with patch("app.routes.recognition.face_service.recognize_all_students") as mock_rec:
                mock_rec.return_value = {
                    "matches": [{
                        "student_id": self.student1_id,
                        "similarity_score": 0.88,
                    }],
                    "status": "recognized",
                    "detected_count": 1,
                }

                # 2. Verify evidence
                verify_resp = self.client.post(
                    "/api/faculty/recognition/liveness/verify",
                    headers=headers,
                    data={
                        "session_id": str(self.session_id),
                        "challenge_id": challenge_id,
                        "frames": [f0, f1],
                    },
                    content_type="multipart/form-data",
                )
                self.assertEqual(verify_resp.status_code, 200)
                vdata = verify_resp.get_json()
                self.assertTrue(vdata["success"])
                self.assertEqual(vdata["status"], "verified")
                self.assertIn("verification_token", vdata)
                self.assertEqual(vdata["student_id"], self.student1_id)

                verification_token = vdata["verification_token"]

                # 3. Mark attendance using the single-use verification token
                att_resp = self.client.post(
                    "/api/faculty/recognition/attendance",
                    headers=headers,
                    json={
                        "session_id": self.session_id,
                        "verification_token": verification_token,
                        "student_id": self.student1_id,
                    },
                )
                self.assertEqual(att_resp.status_code, 200)
                att_data = att_resp.get_json()
                self.assertTrue(att_data["success"])
                self.assertEqual(att_data["status"], "recognized")
                self.assertEqual(att_data["data"]["student_id"], self.student1_id)

                # Verify database record exists
                with self.app.app_context():
                    rec = AttendanceRecord.query.filter_by(
                        session_id=self.session_id,
                        student_id=self.student1_id,
                    ).first()
                    self.assertIsNotNone(rec)
                    self.assertEqual(rec.status, "PRESENT")
                    self.assertEqual(rec.recognition_method, "FACE")

    # =========================================================================
    # 5. Token Security & Anti-Replay Tests
    # =========================================================================

    def test_direct_attendance_request_without_verification_rejected(self):
        """Test attendance API call without a verification token is strictly rejected with 403."""
        headers = self._auth_headers(self.faculty_user_id, "FACULTY")
        img = self._create_sample_face_frame("center")
        f = self._frame_to_bytes_io(img, "frame.jpg")

        response = self.client.post(
            "/api/faculty/recognition/attendance",
            headers=headers,
            data={
                "session_id": str(self.session_id),
                "image": f,
            },
            content_type="multipart/form-data",
        )
        self.assertEqual(response.status_code, 403)
        data = response.get_json()
        self.assertFalse(data["success"])
        self.assertEqual(data["status"], "verification_token_required")

    def test_forged_or_fabricated_token_rejected(self):
        """Test calling attendance API with an illegitimate token returns 403."""
        headers = self._auth_headers(self.faculty_user_id, "FACULTY")
        response = self.client.post(
            "/api/faculty/recognition/attendance",
            headers=headers,
            json={
                "session_id": self.session_id,
                "verification_token": "vtok_fabricated_fake_token_12345678",
                "student_id": self.student1_id,
            },
        )
        self.assertEqual(response.status_code, 403)
        data = response.get_json()
        self.assertEqual(data["status"], "invalid_verification_token")

    def test_reused_token_rejected(self):
        """Test that single-use verification token cannot be consumed a second time."""
        token = liveness_manager.issue_verification_token(
            challenge_id="c_test",
            student_id=self.student1_id,
            session_id=self.session_id,
            faculty_id=self.faculty_id,
            confidence_score=0.92,
            pad_score=0.98,
        )
        headers = self._auth_headers(self.faculty_user_id, "FACULTY")

        # First consumption -> Success
        resp1 = self.client.post(
            "/api/faculty/recognition/attendance",
            headers=headers,
            json={
                "session_id": self.session_id,
                "verification_token": token,
            },
        )
        self.assertEqual(resp1.status_code, 200)

        # Second consumption with the SAME token -> 403 Forbidden
        resp2 = self.client.post(
            "/api/faculty/recognition/attendance",
            headers=headers,
            json={
                "session_id": self.session_id,
                "verification_token": token,
            },
        )
        self.assertEqual(resp2.status_code, 403)
        data2 = resp2.get_json()
        self.assertIn("already been used", data2["message"].lower())

    def test_token_mismatched_student_rejected(self):
        """Test that token bound to Student 1 cannot mark attendance for Student 2."""
        token = liveness_manager.issue_verification_token(
            challenge_id="c_test",
            student_id=self.student1_id,
            session_id=self.session_id,
            faculty_id=self.faculty_id,
            confidence_score=0.90,
            pad_score=0.98,
        )
        headers = self._auth_headers(self.faculty_user_id, "FACULTY")

        response = self.client.post(
            "/api/faculty/recognition/attendance",
            headers=headers,
            json={
                "session_id": self.session_id,
                "verification_token": token,
                "student_id": self.student2_id,  # Mismatched student ID
            },
        )
        self.assertEqual(response.status_code, 403)
        data = response.get_json()
        self.assertIn("student", data["message"].lower())

    def test_token_mismatched_session_rejected(self):
        """Test that token bound to Session 1 cannot mark attendance for Session 2."""
        token = liveness_manager.issue_verification_token(
            challenge_id="c_test",
            student_id=self.student1_id,
            session_id=self.session_id,
            faculty_id=self.faculty_id,
            confidence_score=0.90,
            pad_score=0.98,
        )
        headers = self._auth_headers(self.faculty_user_id, "FACULTY")

        response = self.client.post(
            "/api/faculty/recognition/attendance",
            headers=headers,
            json={
                "session_id": self.session_id + 9999,  # Mismatched session
                "verification_token": token,
            },
        )
        self.assertEqual(response.status_code, 404)  # Session not found or mismatch

    def test_expired_token_rejected(self):
        """Test that an expired verification token cannot be consumed."""
        token = liveness_manager.issue_verification_token(
            challenge_id="c_test",
            student_id=self.student1_id,
            session_id=self.session_id,
            faculty_id=self.faculty_id,
            confidence_score=0.90,
            pad_score=0.98,
        )
        # Manually expire token
        liveness_manager._tokens[token]["expires_at"] = time.time() - 5

        headers = self._auth_headers(self.faculty_user_id, "FACULTY")
        response = self.client.post(
            "/api/faculty/recognition/attendance",
            headers=headers,
            json={
                "session_id": self.session_id,
                "verification_token": token,
            },
        )
        self.assertEqual(response.status_code, 403)
        data = response.get_json()
        self.assertIn("expired", data["message"].lower())

    def test_concurrent_token_consumption_is_atomic(self):
        """Test concurrent requests attempting to consume the same token result in exactly one success."""
        token = liveness_manager.issue_verification_token(
            challenge_id="c_concurrent",
            student_id=self.student1_id,
            session_id=self.session_id,
            faculty_id=self.faculty_id,
            confidence_score=0.90,
            pad_score=0.95,
        )
        headers = self._auth_headers(self.faculty_user_id, "FACULTY")

        def submit():
            return self.client.post(
                "/api/faculty/recognition/attendance",
                headers=headers,
                json={
                    "session_id": self.session_id,
                    "verification_token": token,
                },
            )

        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            future1 = executor.submit(submit)
            future2 = executor.submit(submit)
            res1 = future1.result()
            res2 = future2.result()

        status_codes = [res1.status_code, res2.status_code]
        # Exactly one must succeed (200) and one must be rejected (403)
        self.assertIn(200, status_codes)
        self.assertIn(403, status_codes)
        self.assertEqual(sorted(status_codes), [200, 403])

        # Verify rejection payload contract
        rejected_res = res1 if res1.status_code == 403 else res2
        rej_json = rejected_res.get_json()
        self.assertFalse(rej_json["success"])
        self.assertEqual(rej_json["status"], "invalid_verification_token")
        self.assertIn("already been used", rej_json["message"].lower())

        # Verify exactly one attendance record is persisted
        with self.app.app_context():
            records = AttendanceRecord.query.filter_by(
                session_id=self.session_id,
                student_id=self.student1_id,
            ).all()
            self.assertEqual(len(records), 1)
            self.assertEqual(records[0].status, "PRESENT")

        # Verify subsequent attempt with the same token is also strictly rejected with 403
        res3 = self.client.post(
            "/api/faculty/recognition/attendance",
            headers=headers,
            json={
                "session_id": self.session_id,
                "verification_token": token,
            },
        )
        self.assertEqual(res3.status_code, 403)

    def test_concurrent_token_manager_atomicity(self):
        """Test that liveness_manager.consume_verification_token is atomic across many concurrent threads."""
        token = liveness_manager.issue_verification_token(
            challenge_id="c_manager_atomicity",
            student_id=self.student1_id,
            session_id=self.session_id,
            faculty_id=self.faculty_id,
            confidence_score=0.90,
            pad_score=0.95,
        )

        def consume():
            return liveness_manager.consume_verification_token(
                token=token,
                expected_session_id=self.session_id,
                expected_student_id=self.student1_id,
                expected_faculty_id=self.faculty_id,
            )

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(consume) for _ in range(10)]
            results = [f.result() for f in futures]

        success_count = sum(1 for success, reason, data in results if success)
        failure_count = sum(1 for success, reason, data in results if not success)

        self.assertEqual(success_count, 1)
        self.assertEqual(failure_count, 9)
        reasons = [reason for success, reason, data in results if not success]
        self.assertTrue(all("already been used" in r for r in reasons))

    # =========================================================================
    # 6. Quality, Multiple Faces, and Fail-Closed Tests
    # =========================================================================

    def test_multiple_faces_in_evidence_frame_rejected(self):
        """Test submitting evidence frames with multiple faces returns 400 multiple_faces."""
        challenge = liveness_manager.create_challenge(self.session_id, self.faculty_id)
        headers = self._auth_headers(self.faculty_user_id, "FACULTY")

        img0 = self._create_sample_face_frame("center")
        img1 = self._create_sample_face_frame("left")
        f0 = self._frame_to_bytes_io(img0, "f0.jpg")
        f1 = self._frame_to_bytes_io(img1, "f1.jpg")

        with patch("app.routes.recognition.face_service.detect_faces") as mock_detect:
            # 2 faces detected in frame 1
            mock_detect.return_value = [
                {"bbox": [20, 20, 80, 80], "landmarks": [[40, 40]] * 5},
                {"bbox": [150, 20, 80, 80], "landmarks": [[170, 40]] * 5},
            ]
            response = self.client.post(
                "/api/faculty/recognition/liveness/verify",
                headers=headers,
                data={
                    "session_id": str(self.session_id),
                    "challenge_id": challenge["challenge_id"],
                    "frames": [f0, f1],
                },
                content_type="multipart/form-data",
            )
            self.assertEqual(response.status_code, 400)
            data = response.get_json()
            self.assertEqual(data["status"], "multiple_faces")

    def test_fail_closed_when_pad_model_missing(self):
        """Test fail-closed behavior: when FAIL_CLOSED_ON_MISSING_MODEL is active and model is absent, challenge fails safely."""
        with self.app.app_context():
            self.app.config["FAIL_CLOSED_ON_MISSING_MODEL"] = True
            self.app.config["PAD_MODEL_PATH"] = "non_existent_weights.onnx"

        headers = self._auth_headers(self.faculty_user_id, "FACULTY")
        response = self.client.post(
            "/api/faculty/recognition/liveness/challenge",
            headers=headers,
            json={"session_id": self.session_id},
        )
        self.assertEqual(response.status_code, 503)
        data = response.get_json()
        self.assertFalse(data["success"])
        self.assertEqual(data["status"], "liveness_model_unavailable")

        # Reset config
        with self.app.app_context():
            self.app.config["FAIL_CLOSED_ON_MISSING_MODEL"] = False

    # =========================================================================
    # 7. Integration & Manual Attendance Integrity
    # =========================================================================

    def test_manual_admin_attendance_remains_intact(self):
        """Test that administrator manual attendance override is not blocked by face liveness."""
        headers = self._auth_headers(self.admin_user_id, "ADMIN")
        response = self.client.post(
            f"/api/faculty/attendance/sessions/{self.session_id}/records",
            headers=headers,
            json={
                "student_id": self.student2_id,
                "status": "PRESENT",
                "recognition_method": "MANUAL",
            },
        )
        self.assertEqual(response.status_code, 201)
        data = response.get_json()
        self.assertTrue(data["success"])
    def test_quality_warning_on_blurry_frame(self):
        """Test that a severely blurred frame triggers quality_warning rather than spoof_suspected."""
        challenge = liveness_manager.create_challenge(self.session_id, self.faculty_id)
        headers = self._auth_headers(self.faculty_user_id, "FACULTY")

        # Create heavily blurred frame with zero high-frequency edges
        img = np.full((320, 320, 3), 180, dtype=np.uint8)
        f0 = self._frame_to_bytes_io(img, "f0.jpg")
        f1 = self._frame_to_bytes_io(img, "f1.jpg")

        with patch("app.routes.recognition.face_service.detect_faces") as mock_detect:
            mock_detect.return_value = [{
                "bbox": [50, 50, 150, 150],
                "landmarks": [[80, 80], [140, 80], [110, 110], [90, 140], [130, 140]],
                "confidence": 0.95,
            }]
            response = self.client.post(
                "/api/faculty/recognition/liveness/verify",
                headers=headers,
                data={
                    "session_id": str(self.session_id),
                    "challenge_id": challenge["challenge_id"],
                    "frames": [f0, f1],
                },
                content_type="multipart/form-data",
            )
            self.assertEqual(response.status_code, 400)
            data = response.get_json()
            self.assertFalse(data["success"])
            self.assertEqual(data["status"], "quality_warning")
            self.assertEqual(data["attack_type"], "blurred_or_low_quality")
            self.assertIn("blurry", data["message"].lower())

    def test_multiframe_peak_movement_detected_at_frame_2(self):
        """Test multi-frame challenge where user movement reaches peak amplitude at frame 2."""
        challenge = liveness_manager.create_challenge(self.session_id, self.faculty_id)
        liveness_manager._challenges[challenge["challenge_id"]]["challenge_type"] = CHALLENGE_TURN_LEFT
        challenge_id = challenge["challenge_id"]
        headers = self._auth_headers(self.faculty_user_id, "FACULTY")

        img0 = self._create_sample_face_frame("center")
        img1 = self._create_sample_face_frame("center")
        img2 = self._create_sample_face_frame("left")
        # Add slight pixel jitter across frames to pass anti-replay
        img1[0, 0, 0] = (int(img1[0, 0, 0]) + 15) % 255
        img2[0, 0, 0] = (int(img2[0, 0, 0]) + 30) % 255

        f0 = self._frame_to_bytes_io(img0, "f0.jpg")
        f1 = self._frame_to_bytes_io(img1, "f1.jpg")
        f2 = self._frame_to_bytes_io(img2, "f2.jpg")

        lm_center = [[80, 80], [140, 80], [110, 110], [90, 140], [130, 140]]
        # Frame 1: minimal movement (user still reading instruction)
        lm_slight = [[80, 80], [140, 80], [108, 110], [90, 140], [130, 140]]
        # Frame 2: peak head turn
        lm_left = [[80, 80], [140, 80], [88, 110], [90, 140], [130, 140]]

        detect_calls = {"count": 0}

        def mock_detect_multiframe(frame):
            c = detect_calls["count"]
            detect_calls["count"] += 1
            if c % 3 == 0:
                return [{"bbox": [50, 50, 150, 150], "landmarks": lm_center, "confidence": 0.95}]
            elif c % 3 == 1:
                return [{"bbox": [50, 50, 150, 150], "landmarks": lm_slight, "confidence": 0.95}]
            else:
                return [{"bbox": [50, 50, 150, 150], "landmarks": lm_left, "confidence": 0.95}]

        with patch("app.routes.recognition.face_service.detect_faces", side_effect=mock_detect_multiframe):
            with patch("app.routes.recognition.face_service.recognize_all_students") as mock_rec:
                mock_rec.return_value = {
                    "matches": [{
                        "student_id": self.student1_id,
                        "similarity_score": 0.88,
                    }],
                    "status": "recognized",
                    "detected_count": 1,
                }
                response = self.client.post(
                    "/api/faculty/recognition/liveness/verify",
                    headers=headers,
                    data={
                        "session_id": str(self.session_id),
                        "challenge_id": challenge_id,
                        "frames": [f0, f1, f2],
                        "timestamps": json.dumps([0, 1200, 2000]),
                        "mirrored": "true",
                    },
                    content_type="multipart/form-data",
                )
                self.assertEqual(response.status_code, 200)
                data = response.get_json()
                self.assertTrue(data["success"])
                self.assertEqual(data["status"], "verified")
                self.assertIn("verification_token", data)


if __name__ == "__main__":
    unittest.main()
