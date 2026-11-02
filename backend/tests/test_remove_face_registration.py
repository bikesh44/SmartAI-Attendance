import io
import unittest
from datetime import date, datetime, time
from unittest.mock import patch

import cv2
import numpy as np
from flask import Flask
from flask_jwt_extended import JWTManager, create_access_token
from sqlalchemy.pool import StaticPool

from app.extensions import db
from app.models import (
    ActivityLog,
    AttendanceRecord,
    AttendanceSession,
    Course,
    CourseOffering,
    Department,
    Enrollment,
    FaceProfile,
    Faculty,
    Student,
    TimetableEntry,
    User,
)
from app.routes.admin import admin_bp
from app.routes.face import face_bp


class TestRemoveFaceRegistration(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = Flask(__name__)
        cls.app.config.update(
            TESTING=True,
            SECRET_KEY="test-secret-canonical",
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

        cls.app.register_blueprint(admin_bp)
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
            # Create base department
            self.dept = Department(
                department_name="Computer Science & Engineering",
                department_code="CSE",
            )
            db.session.add(self.dept)
            db.session.flush()

            # Admin user
            self.admin_user = User(
                name="System Administrator",
                email="admin@test.local",
                password_hash="hashed_pw",
                role="ADMIN",
                is_active=True,
            )
            # Faculty user & profile
            self.faculty_user = User(
                name="Prof Xavier",
                email="xavier@test.local",
                password_hash="hashed_pw",
                role="FACULTY",
                is_active=True,
            )
            db.session.add_all([self.admin_user, self.faculty_user])
            db.session.flush()

            self.faculty = Faculty(
                user_id=self.faculty_user.user_id,
                department_id=self.dept.department_id,
                employee_id="FAC-001",
                designation="Professor",
            )
            db.session.add(self.faculty)
            db.session.flush()

            # Course & Offering
            self.course = Course(
                course_name="Machine Learning",
                course_code="CS401",
                department_id=self.dept.department_id,
                semester=5,
                credits=4,
                is_active=True,
            )
            db.session.add(self.course)
            db.session.flush()

            self.offering = CourseOffering(
                course_id=self.course.course_id,
                faculty_id=self.faculty.faculty_id,
                academic_year="2026-27",
                semester=5,
                section="A",
                room="LAB-3",
            )
            db.session.add(self.offering)
            db.session.flush()

            # Student 1 (Shyam)
            self.u1 = User(
                name="Shyam Kumar",
                email="shyam@test.local",
                password_hash="hashed_pw",
                role="STUDENT",
                is_active=True,
            )
            # Student 2 (Ram)
            self.u2 = User(
                name="Ram Sharma",
                email="ram@test.local",
                password_hash="hashed_pw",
                role="STUDENT",
                is_active=True,
            )
            db.session.add_all([self.u1, self.u2])
            db.session.flush()

            self.s1 = Student(
                user_id=self.u1.user_id,
                department_id=self.dept.department_id,
                enrollment_no="ENR-SHYAM-01",
                academic_year="2026-27",
                semester=5,
                section="A",
            )
            self.s2 = Student(
                user_id=self.u2.user_id,
                department_id=self.dept.department_id,
                enrollment_no="ENR-RAM-02",
                academic_year="2026-27",
                semester=5,
                section="A",
            )
            db.session.add_all([self.s1, self.s2])
            db.session.flush()

            self.s1_id = self.s1.student_id
            self.s2_id = self.s2.student_id
            self.dept_id = self.dept.department_id
            self.faculty_id = self.faculty.faculty_id
            self.admin_uid = self.admin_user.user_id
            self.faculty_uid = self.faculty_user.user_id
            self.student_u1_id = self.u1.user_id
            self.offering_id = self.offering.offering_id

            db.session.commit()

    def tearDown(self):
        with self.app.app_context():
            ActivityLog.query.delete()
            AttendanceRecord.query.delete()
            AttendanceSession.query.delete()
            FaceProfile.query.delete()
            Enrollment.query.delete()
            TimetableEntry.query.delete()
            CourseOffering.query.delete()
            Course.query.delete()
            Student.query.delete()
            Faculty.query.delete()
            User.query.delete()
            Department.query.delete()
            db.session.commit()

    def _auth_headers(self, user_id, role="ADMIN"):
        with self.app.app_context():
            token = create_access_token(
                identity=str(user_id),
                additional_claims={"role": role},
            )
        return {"Authorization": f"Bearer {token}"}

    def _dummy_image(self):
        img = np.zeros((100, 100, 3), dtype=np.uint8)
        _, enc = cv2.imencode(".jpg", img)
        return io.BytesIO(enc.tobytes()), "frame.jpg"

    def _unit_vector(self, index, dim=128):
        v = np.zeros((1, dim), dtype=np.float32)
        v[0, index % dim] = 1.0
        return v

    def _enroll_student_face(self, student_id, vector_index=0):
        enc = self._unit_vector(vector_index)
        with patch("app.routes.face.face_service.enroll_student") as mock_enroll:
            mock_enroll.return_value = {"status": "enrolled", "encoding": enc}
            res = self.client.post(
                "/api/face/enroll",
                headers=self._auth_headers(self.admin_uid, role="ADMIN"),
                data={"student_id": str(student_id), "image": self._dummy_image()},
                content_type="multipart/form-data",
            )
            self.assertEqual(res.status_code, 201)
            return enc

    # ------------------------------------------------------------------
    # 1. An authorized administrator can remove a registered face
    # ------------------------------------------------------------------
    def test_01_authorized_admin_can_remove_registered_face(self):
        self._enroll_student_face(self.s1_id, vector_index=0)

        # Confirm active registration
        with self.app.app_context():
            fp = FaceProfile.query.filter_by(student_id=self.s1_id, is_active=True).first()
            self.assertIsNotNone(fp)

        # Admin calls DELETE endpoint
        res = self.client.delete(
            f"/api/admin/students/{self.s1_id}/face",
            headers=self._auth_headers(self.admin_uid, role="ADMIN"),
            json={"reason": "Wrong person registered by mistake"},
        )
        self.assertEqual(res.status_code, 200)
        body = res.get_json()
        self.assertTrue(body["success"])
        self.assertFalse(body["data"]["face_registered"])
        self.assertIn("removed_face_ids", body["data"])

        # Check database: profile is deactivated, updated_at set
        with self.app.app_context():
            active_fp = FaceProfile.query.filter_by(student_id=self.s1_id, is_active=True).first()
            self.assertIsNone(active_fp)

            inactive_fp = FaceProfile.query.filter_by(student_id=self.s1_id, is_active=False).first()
            self.assertIsNotNone(inactive_fp)
            self.assertIsNotNone(inactive_fp.updated_at)

    # ------------------------------------------------------------------
    # 2. An unauthorized user cannot remove it
    # ------------------------------------------------------------------
    def test_02_unauthorized_user_cannot_remove_face(self):
        self._enroll_student_face(self.s1_id, vector_index=0)

        # 1. Unauthenticated request (no JWT token) -> 401
        res = self.client.delete(f"/api/admin/students/{self.s1_id}/face")
        self.assertEqual(res.status_code, 401)

        # 2. Student role attempt -> 403 Forbidden
        student_headers = self._auth_headers(self.student_u1_id, role="STUDENT")
        res = self.client.delete(
            f"/api/admin/students/{self.s1_id}/face",
            headers=student_headers,
        )
        self.assertEqual(res.status_code, 403)

        # 3. Faculty role attempt -> 403 Forbidden
        faculty_headers = self._auth_headers(self.faculty_uid, role="FACULTY")
        res = self.client.delete(
            f"/api/admin/students/{self.s1_id}/face",
            headers=faculty_headers,
        )
        self.assertEqual(res.status_code, 403)

        # Verify face profile remains active
        with self.app.app_context():
            fp = FaceProfile.query.filter_by(student_id=self.s1_id, is_active=True).first()
            self.assertIsNotNone(fp)

    # ------------------------------------------------------------------
    # 3. Missing student, missing registration, or ID mismatch error handling
    # ------------------------------------------------------------------
    def test_03_missing_student_or_registration_returns_correct_error(self):
        admin_headers = self._auth_headers(self.admin_uid, role="ADMIN")

        # 1. Missing student ID (999999) -> 404
        res = self.client.delete(
            "/api/admin/students/999999/face",
            headers=admin_headers,
        )
        self.assertEqual(res.status_code, 404)
        body = res.get_json()
        self.assertFalse(body["success"])
        self.assertEqual(body["status"], "student_not_found")

        # 2. Student exists (s1) but has NO face registered -> 404
        res = self.client.delete(
            f"/api/admin/students/{self.s1_id}/face",
            headers=admin_headers,
        )
        self.assertEqual(res.status_code, 404)
        body = res.get_json()
        self.assertFalse(body["success"])
        self.assertEqual(body["status"], "not_registered")

        # 3. Specific face_id mismatch (attempting to delete face belonging to another student)
        self._enroll_student_face(self.s1_id, vector_index=0)
        with self.app.app_context():
            s1_face = FaceProfile.query.filter_by(student_id=self.s1_id, is_active=True).first()
            s1_face_id = s1_face.face_id

        # Ask to remove s1_face_id under s2 -> 400 profile_student_mismatch
        res = self.client.delete(
            f"/api/admin/students/{self.s2_id}/face",
            headers=admin_headers,
            json={"face_id": s1_face_id},
        )
        self.assertEqual(res.status_code, 400)
        body = res.get_json()
        self.assertFalse(body["success"])
        self.assertEqual(body["status"], "profile_student_mismatch")

    # ------------------------------------------------------------------
    # 4. Student account, enrollment, and attendance history remain unchanged
    # ------------------------------------------------------------------
    def test_04_student_account_and_attendance_history_remain_unchanged(self):
        self._enroll_student_face(self.s1_id, vector_index=0)

        with self.app.app_context():
            # Create enrollment
            enrollment = Enrollment(
                student_id=self.s1_id,
                offering_id=self.offering_id,
                enrolled_at=datetime(2026, 9, 1, 10, 0),
                status="ACTIVE",
            )
            db.session.add(enrollment)
            db.session.flush()

            # Create attendance session & record
            session = AttendanceSession(
                offering_id=self.offering_id,
                faculty_id=self.faculty_id,
                session_date=date(2026, 10, 20),
                start_time=time(9, 0),
                end_time=time(10, 0),
                status="COMPLETED",
            )
            db.session.add(session)
            db.session.flush()

            record = AttendanceRecord(
                session_id=session.session_id,
                student_id=self.s1_id,
                status="PRESENT",
                marked_at=datetime(2026, 10, 20, 9, 5),
                recognition_method="FACE",
                confidence_score=0.98,
            )
            db.session.add(record)
            db.session.commit()

            session_id = session.session_id
            att_id = record.attendance_id

        # Admin removes student face
        res = self.client.delete(
            f"/api/admin/students/{self.s1_id}/face",
            headers=self._auth_headers(self.admin_uid, role="ADMIN"),
        )
        self.assertEqual(res.status_code, 200)

        # Verify Student, User, Enrollment, Session, and Record are 100% intact
        with self.app.app_context():
            student = db.session.get(Student, self.s1_id)
            self.assertIsNotNone(student)
            self.assertEqual(student.enrollment_no, "ENR-SHYAM-01")

            user = db.session.get(User, self.student_u1_id)
            self.assertIsNotNone(user)
            self.assertEqual(user.email, "shyam@test.local")

            enr = Enrollment.query.filter_by(student_id=self.s1_id, offering_id=self.offering_id).first()
            self.assertIsNotNone(enr)
            self.assertEqual(enr.status, "ACTIVE")

            att_record = db.session.get(AttendanceRecord, att_id)
            self.assertIsNotNone(att_record)
            self.assertEqual(att_record.status, "PRESENT")
            self.assertEqual(att_record.student_id, self.s1_id)
            self.assertEqual(att_record.session_id, session_id)

    # ------------------------------------------------------------------
    # 5. Removed face is no longer treated as an active registration
    # ------------------------------------------------------------------
    def test_05_removed_face_is_no_longer_treated_as_active(self):
        self._enroll_student_face(self.s1_id, vector_index=0)

        # Check status before removal
        status_res = self.client.get(
            f"/api/face/status/{self.s1_id}",
            headers=self._auth_headers(self.admin_uid, role="ADMIN"),
        )
        self.assertEqual(status_res.status_code, 200)
        self.assertTrue(status_res.get_json()["data"]["registered"])

        # Remove face
        del_res = self.client.delete(
            f"/api/admin/students/{self.s1_id}/face",
            headers=self._auth_headers(self.admin_uid, role="ADMIN"),
        )
        self.assertEqual(del_res.status_code, 200)

        # Check status after removal
        status_res = self.client.get(
            f"/api/face/status/{self.s1_id}",
            headers=self._auth_headers(self.admin_uid, role="ADMIN"),
        )
        self.assertEqual(status_res.status_code, 200)
        data = status_res.get_json()["data"]
        self.assertFalse(data["registered"])
        self.assertEqual(data["status"], "not_registered")

    # ------------------------------------------------------------------
    # 6. The student can register the correct face again
    # ------------------------------------------------------------------
    def test_06_student_can_register_correct_face_again(self):
        # Initial incorrect enrollment (e.g. Ram's face vector 0 enrolled on Shyam)
        self._enroll_student_face(self.s1_id, vector_index=0)

        # Admin removes the incorrect biometric registration
        res = self.client.delete(
            f"/api/admin/students/{self.s1_id}/face",
            headers=self._auth_headers(self.admin_uid, role="ADMIN"),
            json={"reason": "Ram's face was registered on Shyam by accident"},
        )
        self.assertEqual(res.status_code, 200)

        # Now Shyam enrolls his OWN correct face (vector index 1)
        self._enroll_student_face(self.s1_id, vector_index=1)

        # Verify active profile for s1 is now vector 1
        with self.app.app_context():
            active_fp = FaceProfile.query.filter_by(student_id=self.s1_id, is_active=True).first()
            self.assertIsNotNone(active_fp)
            # Old profile is inactive
            inactive_fps = FaceProfile.query.filter_by(student_id=self.s1_id, is_active=False).all()
            self.assertEqual(len(inactive_fps), 1)

    # ------------------------------------------------------------------
    # 7. Duplicate registration against another active student remains blocked,
    #    but succeeds once incorrect registration is removed
    # ------------------------------------------------------------------
    def test_07_duplicate_face_behavior_and_conflict_resolution(self):
        # Scenario: Ram's face (vector 0) was accidentally registered to Shyam (s1)
        self._enroll_student_face(self.s1_id, vector_index=0)

        # Ram (s2) tries to register his face (vector 0).
        # Cross-student duplicate detection MUST block it with 409 Conflict.
        with patch("app.routes.face.face_service.enroll_student") as mock_enroll:
            mock_enroll.return_value = {"status": "enrolled", "encoding": self._unit_vector(0)}
            res = self.client.post(
                "/api/face/enroll",
                headers=self._auth_headers(self.admin_uid, role="ADMIN"),
                data={"student_id": str(self.s2_id), "image": self._dummy_image()},
                content_type="multipart/form-data",
            )
            self.assertEqual(res.status_code, 409)
            body = res.get_json()
            self.assertFalse(body["success"])
            self.assertIn("conflict", body.get("status", "").lower())

        # Now the Administrator removes the incorrect registration from Shyam (s1)
        del_res = self.client.delete(
            f"/api/admin/students/{self.s1_id}/face",
            headers=self._auth_headers(self.admin_uid, role="ADMIN"),
            json={"reason": "Ram's face was accidentally registered under Shyam's ID"},
        )
        self.assertEqual(del_res.status_code, 200)

        # Now Ram (s2) registers his face (vector 0) again. It MUST SUCCEED now!
        self._enroll_student_face(self.s2_id, vector_index=0)

        with self.app.app_context():
            ram_fp = FaceProfile.query.filter_by(student_id=self.s2_id, is_active=True).first()
            self.assertIsNotNone(ram_fp)

        # Another third student attempts to steal Ram's face -> blocked with 409
        u3 = User(name="Third Student", email="third@test.local", password_hash="pw", role="STUDENT")
        with self.app.app_context():
            db.session.add(u3)
            db.session.flush()
            s3 = Student(
                user_id=u3.user_id,
                department_id=self.dept_id,
                enrollment_no="ENR-THIRD-03",
                academic_year="2026-27",
                semester=5,
                section="A",
            )
            db.session.add(s3)
            db.session.commit()
            s3_id = s3.student_id

        with patch("app.routes.face.face_service.enroll_student") as mock_enroll:
            mock_enroll.return_value = {"status": "enrolled", "encoding": self._unit_vector(0)}
            res = self.client.post(
                "/api/face/enroll",
                headers=self._auth_headers(self.admin_uid, role="ADMIN"),
                data={"student_id": str(s3_id), "image": self._dummy_image()},
                content_type="multipart/form-data",
            )
            self.assertEqual(res.status_code, 409)

    # ------------------------------------------------------------------
    # 8. Repeated removal requests behave safely
    # ------------------------------------------------------------------
    def test_08_repeated_removal_requests_behave_safely(self):
        self._enroll_student_face(self.s1_id, vector_index=0)
        admin_headers = self._auth_headers(self.admin_uid, role="ADMIN")

        # First removal succeeds (200)
        res1 = self.client.delete(
            f"/api/admin/students/{self.s1_id}/face",
            headers=admin_headers,
            json={"reason": "First removal request"},
        )
        self.assertEqual(res1.status_code, 200)

        # Second removal returns safe 404 not_registered without server crash
        res2 = self.client.delete(
            f"/api/admin/students/{self.s1_id}/face",
            headers=admin_headers,
            json={"reason": "Accidental duplicate click"},
        )
        self.assertEqual(res2.status_code, 404)
        body = res2.get_json()
        self.assertFalse(body["success"])
        self.assertEqual(body["status"], "not_registered")

    # ------------------------------------------------------------------
    # 9. Audit logging is performed
    # ------------------------------------------------------------------
    def test_09_audit_logging_records_administrator_and_reason(self):
        self._enroll_student_face(self.s1_id, vector_index=0)

        admin_headers = self._auth_headers(self.admin_uid, role="ADMIN")
        reason_text = "Incorrect registration of student Ram on Shyam's profile"

        res = self.client.delete(
            f"/api/admin/students/{self.s1_id}/face",
            headers=admin_headers,
            json={"reason": reason_text},
        )
        self.assertEqual(res.status_code, 200)

        with self.app.app_context():
            log = ActivityLog.query.filter_by(
                action_type="FACE_BIOMETRIC_REMOVED",
                entity_id=str(self.s1_id),
            ).first()

            self.assertIsNotNone(log)
            self.assertEqual(log.actor_id, self.admin_uid)
            self.assertEqual(log.entity_type, "Student")
            self.assertEqual(log.status, "SUCCESS")
            self.assertIsNotNone(log.details)
            self.assertEqual(log.details.get("reason"), reason_text)
            self.assertEqual(log.details.get("enrollment_no"), "ENR-SHYAM-01")

            # Verify no raw biometric templates or embeddings are exposed in details
            self.assertNotIn("embedding", log.details)
            self.assertNotIn("embeddings", log.details)

    # ------------------------------------------------------------------
    # 10. Permanent deletion option works cleanly
    # ------------------------------------------------------------------
    def test_10_permanent_deletion_removes_profile_completely(self):
        self._enroll_student_face(self.s1_id, vector_index=0)

        admin_headers = self._auth_headers(self.admin_uid, role="ADMIN")
        res = self.client.delete(
            f"/api/admin/students/{self.s1_id}/face",
            headers=admin_headers,
            json={"permanent": True, "reason": "GDPR compliance right to be forgotten"},
        )
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.get_json()["data"]["permanent"])

        with self.app.app_context():
            # Completely removed from table
            count = FaceProfile.query.filter_by(student_id=self.s1_id).count()
            self.assertEqual(count, 0)

    # ------------------------------------------------------------------
    # 11. Alternate route alias via /api/face/student/<id> works
    # ------------------------------------------------------------------
    def test_11_face_blueprint_alias_route_works(self):
        self._enroll_student_face(self.s1_id, vector_index=0)

        admin_headers = self._auth_headers(self.admin_uid, role="ADMIN")
        res = self.client.delete(
            f"/api/face/student/{self.s1_id}",
            headers=admin_headers,
            json={"reason": "Removed via face blueprint alias"},
        )
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.get_json()["success"])


if __name__ == "__main__":
    unittest.main()
