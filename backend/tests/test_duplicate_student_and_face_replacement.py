import io
import os
import unittest
from datetime import date, datetime, time, timezone
from unittest.mock import patch

import cv2
import numpy as np
from flask import Flask
from flask_jwt_extended import JWTManager, create_access_token
from sqlalchemy.exc import IntegrityError
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
    TimetableEntry,
    User,
)
from app.routes.admin import admin_bp
from app.routes.face import face_bp
from app.routes.recognition import recognition_bp
from app.routes.student import PHOTOS_DIR, student_bp
from app.services.face_identity_service import (
    cleanup_obsolete_face_profiles,
    detect_suspected_duplicate_students,
    reconcile_duplicate_students,
    safe_replace_face_profile,
)


class TestDuplicateStudentAndFaceReplacement(unittest.TestCase):

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
        cls.app.register_blueprint(recognition_bp)
        cls.app.register_blueprint(student_bp)

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
                name="Admin User",
                email="admin@test.local",
                password_hash="pw",
                role="ADMIN",
                is_active=True,
            )
            # Faculty user & profile
            self.fac_user = User(
                name="Prof Xavier",
                email="xavier@test.local",
                password_hash="pw",
                role="FACULTY",
                is_active=True,
            )
            db.session.add_all([self.admin_user, self.fac_user])
            db.session.flush()

            self.faculty = Faculty(
                user_id=self.fac_user.user_id,
                department_id=self.dept.department_id,
                employee_id="FAC-X",
                designation="Professor",
            )
            db.session.add(self.faculty)
            db.session.flush()

            # Course & Offering
            self.course = Course(
                course_name="Data Structures",
                course_code="CS201",
                department_id=self.dept.department_id,
                semester=3,
                credits=4,
                is_active=True,
            )
            db.session.add(self.course)
            db.session.flush()

            self.offering = CourseOffering(
                course_id=self.course.course_id,
                faculty_id=self.faculty.faculty_id,
                academic_year="2026-27",
                semester=3,
                section="A",
                room="CSE-101",
            )
            db.session.add(self.offering)
            db.session.flush()

            # Timetable Entry
            self.timetable = TimetableEntry(
                offering_id=self.offering.offering_id,
                day_of_week="Wednesday",
                start_time=time(9, 30),
                end_time=time(10, 30),
                room="CSE-101",
            )
            db.session.add(self.timetable)
            db.session.flush()

            # Student 1 (Alice)
            self.u1 = User(name="Alice Smith", email="alice@test.local", password_hash="pw", role="STUDENT", is_active=True)
            # Student 2 (Bob)
            self.u2 = User(name="Bob Jones", email="bob@test.local", password_hash="pw", role="STUDENT", is_active=True)
            # Student 3 (Candidate for duplicate)
            self.u3 = User(name="Alice Duplicate", email="alice_alt@test.local", password_hash="pw", role="STUDENT", is_active=True)
            db.session.add_all([self.u1, self.u2, self.u3])
            db.session.flush()

            self.s1 = Student(
                user_id=self.u1.user_id,
                department_id=self.dept.department_id,
                enrollment_no="CSE-2026-001",
                semester=3,
                section="A",
                academic_year="2026-27",
            )
            self.s2 = Student(
                user_id=self.u2.user_id,
                department_id=self.dept.department_id,
                enrollment_no="CSE-2026-002",
                semester=3,
                section="A",
                academic_year="2026-27",
            )
            db.session.add_all([self.s1, self.s2])
            db.session.commit()

            self.s1_id = self.s1.student_id
            self.s2_id = self.s2.student_id
            self.u1_id = self.u1.user_id
            self.u2_id = self.u2.user_id
            self.u3_id = self.u3.user_id
            self.admin_uid = self.admin_user.user_id
            self.fac_uid = self.fac_user.user_id
            self.offering_id = self.offering.offering_id
            self.dept_id = self.dept.department_id
            self.faculty_id = self.faculty.faculty_id
            self.course_id = self.course.course_id

    def tearDown(self):
        with self.app.app_context():
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

    def _auth_headers(self, user_id, role="STUDENT"):
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
        v[0, index] = 1.0
        return v

    # ------------------------------------------------------------------
    # 1. First-time registration creates one canonical student record
    # ------------------------------------------------------------------
    @patch("app.routes.face.face_service.enroll_student")
    def test_01_first_time_registration_creates_one_canonical_record(self, mock_enroll):
        enc = self._unit_vector(0)
        mock_enroll.return_value = {"status": "enrolled", "encoding": enc}

        with self.app.app_context():
            # 1. First-time face enrollment
            res = self.client.post(
                "/api/face/enroll",
                headers=self._auth_headers(self.admin_uid, role="ADMIN"),
                data={"student_id": str(self.s1_id), "image": self._dummy_image()},
                content_type="multipart/form-data",
            )
            self.assertEqual(res.status_code, 201)
            body = res.get_json()
            self.assertTrue(body["success"])

            # Verify exactly ONE student and ONE active FaceProfile exist for s1
            stu_count = Student.query.filter_by(student_id=self.s1_id).count()
            self.assertEqual(stu_count, 1)

            fp_count = FaceProfile.query.filter_by(student_id=self.s1_id, is_active=True).count()
            self.assertEqual(fp_count, 1)

    # ------------------------------------------------------------------
    # 2. Re-registering updates face registration without new student ID
    # ------------------------------------------------------------------
    @patch("app.routes.face.face_service.enroll_student")
    def test_02_reregistering_updates_face_without_new_student_id(self, mock_enroll):
        enc1 = self._unit_vector(1)
        enc2 = self._unit_vector(2)

        with self.app.app_context():
            # Initial enrollment
            mock_enroll.return_value = {"status": "enrolled", "encoding": enc1}
            res1 = self.client.post(
                "/api/face/enroll",
                headers=self._auth_headers(self.admin_uid, role="ADMIN"),
                data={"student_id": str(self.s1_id), "image": self._dummy_image()},
                content_type="multipart/form-data",
            )
            self.assertEqual(res1.status_code, 201)
            initial_face_id = res1.get_json()["data"]["face_id"]

            total_students_before = Student.query.count()

            # Re-registering with new face image (safe replacement)
            mock_enroll.return_value = {"status": "enrolled", "encoding": enc2}
            res2 = self.client.post(
                "/api/face/enroll",
                headers=self._auth_headers(self.admin_uid, role="ADMIN"),
                data={"student_id": str(self.s1_id), "image": self._dummy_image()},
                content_type="multipart/form-data",
            )
            self.assertEqual(res2.status_code, 201)
            new_face_id = res2.get_json()["data"]["face_id"]
            self.assertNotEqual(initial_face_id, new_face_id)

            # Assert student count did NOT increase
            total_students_after = Student.query.count()
            self.assertEqual(total_students_before, total_students_after)

            # Assert student keeps the canonical student_id
            student = db.session.get(Student, self.s1_id)
            self.assertIsNotNone(student)
            self.assertEqual(student.enrollment_no, "CSE-2026-001")

            # Assert exactly ONE active profile exists
            active_fps = FaceProfile.query.filter_by(student_id=self.s1_id, is_active=True).all()
            self.assertEqual(len(active_fps), 1)
            self.assertEqual(active_fps[0].face_id, new_face_id)

            # Assert previous profile is now inactive
            old_fp = db.session.get(FaceProfile, initial_face_id)
            self.assertFalse(old_fp.is_active)

    # ------------------------------------------------------------------
    # 3. Failed replacement preserves previous valid face registration
    # ------------------------------------------------------------------
    @patch("app.routes.face.face_service.enroll_student")
    def test_03_failed_replacement_preserves_previous_registration(self, mock_enroll):
        enc1 = self._unit_vector(3)

        with self.app.app_context():
            # Valid initial registration
            mock_enroll.return_value = {"status": "enrolled", "encoding": enc1}
            res1 = self.client.post(
                "/api/face/enroll",
                headers=self._auth_headers(self.admin_uid, role="ADMIN"),
                data={"student_id": str(self.s1_id), "image": self._dummy_image()},
                content_type="multipart/form-data",
            )
            self.assertEqual(res1.status_code, 201)
            orig_face_id = res1.get_json()["data"]["face_id"]

            # Attempt replacement with image failing detection (no face)
            mock_enroll.return_value = {"status": "no_face", "encoding": None}
            res_fail = self.client.post(
                "/api/face/enroll",
                headers=self._auth_headers(self.admin_uid, role="ADMIN"),
                data={"student_id": str(self.s1_id), "image": self._dummy_image()},
                content_type="multipart/form-data",
            )
            self.assertEqual(res_fail.status_code, 400)
            self.assertIn("no face", res_fail.get_json()["message"].lower())

            # Verify original profile remains active and untouched
            active_fp = FaceProfile.query.filter_by(student_id=self.s1_id, is_active=True).first()
            self.assertIsNotNone(active_fp)
            self.assertEqual(active_fp.face_id, orig_face_id)
            stored_enc = np.frombuffer(active_fp.embedding, dtype=np.float32).reshape(1, 128)
            np.testing.assert_array_equal(stored_enc, enc1)

    # ------------------------------------------------------------------
    # 4. Successful replacement invalidates previous mapping and embedding
    # ------------------------------------------------------------------
    @patch("app.routes.face.face_service.enroll_student")
    def test_04_successful_replacement_invalidates_previous_mapping_and_embedding(self, mock_enroll):
        enc1 = self._unit_vector(4)
        enc2 = self._unit_vector(5)

        with self.app.app_context():
            # Initial enrollment
            mock_enroll.return_value = {"status": "enrolled", "encoding": enc1}
            self.client.post(
                "/api/face/enroll",
                headers=self._auth_headers(self.admin_uid, role="ADMIN"),
                data={"student_id": str(self.s1_id), "image": self._dummy_image()},
                content_type="multipart/form-data",
            )

            # Replacement
            mock_enroll.return_value = {"status": "enrolled", "encoding": enc2}
            self.client.post(
                "/api/face/enroll",
                headers=self._auth_headers(self.admin_uid, role="ADMIN"),
                data={"student_id": str(self.s1_id), "image": self._dummy_image()},
                content_type="multipart/form-data",
            )

            # Active recognition index query
            active_profiles = FaceProfile.query.filter_by(
                is_active=True,
                model_version="sface_2021dec",
            ).all()

            # Old embedding (enc1) must NOT be present in active profiles
            active_embeddings = [
                np.frombuffer(p.embedding, dtype=np.float32) for p in active_profiles
            ]
            for emb in active_embeddings:
                self.assertFalse(np.array_equal(emb, enc1.flatten()))

            # New embedding (enc2) MUST be present
            matched_new = any(np.array_equal(emb, enc2.flatten()) for emb in active_embeddings)
            self.assertTrue(matched_new)

    # ------------------------------------------------------------------
    # 5. A student cannot replace another student's face registration
    # ------------------------------------------------------------------
    @patch("app.routes.face.face_service.enroll_student")
    def test_05_student_cannot_replace_another_students_face(self, mock_enroll):
        enc = self._unit_vector(6)
        mock_enroll.return_value = {"status": "enrolled", "encoding": enc}

        with self.app.app_context():
            # Student 1 logs in and tries to enroll/replace Student 2's face
            res = self.client.post(
                "/api/face/enroll",
                headers=self._auth_headers(self.u1_id, role="STUDENT"),
                data={"student_id": str(self.s2_id), "image": self._dummy_image()},
                content_type="multipart/form-data",
            )
            self.assertEqual(res.status_code, 403)
            self.assertIn("only enroll your own face", res.get_json()["message"])

            # Verify Student 2 has no active face profile created by Student 1
            s2_fps = FaceProfile.query.filter_by(student_id=self.s2_id).all()
            self.assertEqual(len(s2_fps), 0)

    # ------------------------------------------------------------------
    # 6. Duplicate student identifier is rejected
    # ------------------------------------------------------------------
    def test_06_duplicate_student_identifier_is_rejected(self):
        with self.app.app_context():
            # 1. Exact match duplicate enrollment number
            res_dup_exact = self.client.post(
                "/api/admin/students",
                headers=self._auth_headers(self.admin_uid, role="ADMIN"),
                json={
                    "user_id": self.u3_id,
                    "enrollment_no": "CSE-2026-001",  # already belongs to s1
                    "semester": 3,
                    "section": "A",
                    "academic_year": "2026-27",
                    "department_id": self.dept_id,
                },
            )
            self.assertEqual(res_dup_exact.status_code, 409)
            self.assertIn("already exists", res_dup_exact.get_json()["message"].lower())

            # 2. Case-insensitive duplicate enrollment number
            res_dup_case = self.client.post(
                "/api/admin/students",
                headers=self._auth_headers(self.admin_uid, role="ADMIN"),
                json={
                    "user_id": self.u3_id,
                    "enrollment_no": "cse-2026-001",  # lowercase duplicate
                    "semester": 3,
                    "section": "A",
                    "academic_year": "2026-27",
                    "department_id": self.dept_id,
                },
            )
            self.assertEqual(res_dup_case.status_code, 409)

            # 3. Duplicate user_id (user already has student profile)
            res_dup_user = self.client.post(
                "/api/admin/students",
                headers=self._auth_headers(self.admin_uid, role="ADMIN"),
                json={
                    "user_id": self.u1_id,  # already has s1
                    "enrollment_no": "CSE-2026-999",
                    "semester": 3,
                    "section": "A",
                    "academic_year": "2026-27",
                    "department_id": self.dept_id,
                },
            )
            self.assertEqual(res_dup_user.status_code, 409)

    # ------------------------------------------------------------------
    # 7. Suspected facial match does not automatically merge two students
    # ------------------------------------------------------------------
    @patch("app.routes.face.face_service.enroll_student")
    def test_07_suspected_facial_match_does_not_automatically_merge_students(self, mock_enroll):
        shared_face = self._unit_vector(7)

        with self.app.app_context():
            # Student 1 registers shared_face
            mock_enroll.return_value = {"status": "enrolled", "encoding": shared_face}
            res1 = self.client.post(
                "/api/face/enroll",
                headers=self._auth_headers(self.admin_uid, role="ADMIN"),
                data={"student_id": str(self.s1_id), "image": self._dummy_image()},
                content_type="multipart/form-data",
            )
            self.assertEqual(res1.status_code, 201)

            # Student 2 attempts to register the same face (cross-student biometric collision)
            res2 = self.client.post(
                "/api/face/enroll",
                headers=self._auth_headers(self.admin_uid, role="ADMIN"),
                data={"student_id": str(self.s2_id), "image": self._dummy_image()},
                content_type="multipart/form-data",
            )
            # Must reject collision without merging
            self.assertEqual(res2.status_code, 409)
            body = res2.get_json()
            self.assertEqual(body["status"], "conflict_detected")

            # Verify Student 1 and Student 2 remain separate distinct entities
            s1 = db.session.get(Student, self.s1_id)
            s2 = db.session.get(Student, self.s2_id)
            self.assertIsNotNone(s1)
            self.assertIsNotNone(s2)
            self.assertNotEqual(s1.student_id, s2.student_id)

    # ------------------------------------------------------------------
    # 8. Concurrent registration requests cannot create duplicate canonical records
    # ------------------------------------------------------------------
    def test_08_concurrent_registration_cannot_create_duplicate_canonical_records(self):
        with self.app.app_context():
            # Verify DB uniqueness on active FaceProfile
            fp1 = FaceProfile(
                student_id=self.s1_id,
                embedding=self._unit_vector(8).tobytes(),
                model_version="sface_2021dec",
                is_active=True,
            )
            db.session.add(fp1)
            db.session.commit()

            # Attempting to insert a second active profile for the same student directly
            # must raise IntegrityError at DB level via uq_student_active_face index
            fp2 = FaceProfile(
                student_id=self.s1_id,
                embedding=self._unit_vector(9).tobytes(),
                model_version="sface_2021dec",
                is_active=True,
            )
            db.session.add(fp2)
            with self.assertRaises(IntegrityError):
                db.session.commit()
            db.session.rollback()

            # Multiple INACTIVE profiles are permitted
            fp_inact1 = FaceProfile(
                student_id=self.s1_id,
                embedding=self._unit_vector(10).tobytes(),
                model_version="sface_2021dec",
                is_active=False,
            )
            fp_inact2 = FaceProfile(
                student_id=self.s1_id,
                embedding=self._unit_vector(11).tobytes(),
                model_version="sface_2021dec",
                is_active=False,
            )
            db.session.add_all([fp_inact1, fp_inact2])
            db.session.commit()
            self.assertEqual(FaceProfile.query.filter_by(student_id=self.s1_id, is_active=False).count(), 2)

    # ------------------------------------------------------------------
    # 9. Old image cleaned up only when safe and permitted
    # ------------------------------------------------------------------
    def test_09_old_image_cleaned_up_only_when_safe_and_permitted(self):
        with self.app.app_context():
            # 1. Upload first photo
            dummy_bytes = b"\xff\xd8\xff\xe0" + b"\x00" * 500  # small valid jpeg header
            res1 = self.client.post(
                "/api/student/upload-photo",
                headers=self._auth_headers(self.u1_id, role="STUDENT"),
                data={"file": (io.BytesIO(dummy_bytes), "photo1.jpg")},
                content_type="multipart/form-data",
            )
            self.assertEqual(res1.status_code, 200)
            url1 = res1.get_json()["photo_url"]
            filename1 = os.path.basename(url1)
            path1 = os.path.join(PHOTOS_DIR, filename1)
            self.assertTrue(os.path.exists(path1))

            import time as _py_time
            _py_time.sleep(0.02)

            # 2. Upload replacement photo
            dummy_bytes2 = b"\xff\xd8\xff\xe0" + b"\x11" * 600
            res2 = self.client.post(
                "/api/student/upload-photo",
                headers=self._auth_headers(self.u1_id, role="STUDENT"),
                data={"file": (io.BytesIO(dummy_bytes2), "photo2.jpg")},
                content_type="multipart/form-data",
            )
            self.assertEqual(res2.status_code, 200)
            url2 = res2.get_json()["photo_url"]
            filename2 = os.path.basename(url2)
            path2 = os.path.join(PHOTOS_DIR, filename2)
            self.assertTrue(os.path.exists(path2))

            # Old photo file must have been cleaned up
            self.assertFalse(os.path.exists(path1))

            # 3. Clean up path2
            if os.path.exists(path2):
                os.remove(path2)

            # 4. Admin purge of obsolete inactive face profiles
            fp_act = FaceProfile(student_id=self.s2_id, embedding=self._unit_vector(12).tobytes(), model_version="sface_2021dec", is_active=True)
            fp_inact = FaceProfile(student_id=self.s2_id, embedding=self._unit_vector(13).tobytes(), model_version="sface_2021dec", is_active=False)
            db.session.add_all([fp_act, fp_inact])
            db.session.commit()

            purged = cleanup_obsolete_face_profiles(student_id=self.s2_id, retention_days=0)
            self.assertEqual(purged, 1)

            # Active profile MUST remain
            self.assertEqual(FaceProfile.query.filter_by(student_id=self.s2_id, is_active=True).count(), 1)
            # Inactive profile MUST be deleted
            self.assertEqual(FaceProfile.query.filter_by(student_id=self.s2_id, is_active=False).count(), 0)

    # ------------------------------------------------------------------
    # 10. Existing attendance and enrollment remain unchanged after replacement
    # ------------------------------------------------------------------
    @patch("app.routes.face.face_service.enroll_student")
    def test_10_existing_attendance_and_enrollment_remain_unchanged(self, mock_enroll):
        with self.app.app_context():
            # Create session, enrollment, and attendance records for Student 1
            enr = Enrollment(student_id=self.s1_id, offering_id=self.offering_id, status="ACTIVE")
            db.session.add(enr)
            db.session.flush()

            sess = AttendanceSession(
                offering_id=self.offering_id,
                faculty_id=self.faculty_id,
                session_date=date(2026, 10, 21),
                start_time=time(9, 30),
                end_time=time(10, 30),
                status="CLOSED",
            )
            db.session.add(sess)
            db.session.flush()

            rec = AttendanceRecord(
                session_id=sess.session_id,
                student_id=self.s1_id,
                status="PRESENT",
                confidence_score=0.92,
                recognition_method="FACE",
                marked_at=datetime(2026, 10, 21, 9, 35, 0),
            )
            db.session.add(rec)
            db.session.commit()

            rec_id = rec.attendance_id
            enr_id = enr.enrollment_id

            # Face replacement
            mock_enroll.return_value = {"status": "enrolled", "encoding": self._unit_vector(14)}
            res = self.client.post(
                "/api/face/enroll",
                headers=self._auth_headers(self.admin_uid, role="ADMIN"),
                data={"student_id": str(self.s1_id), "image": self._dummy_image()},
                content_type="multipart/form-data",
            )
            self.assertEqual(res.status_code, 201)

            # Verify attendance and enrollment remain unchanged
            db_enr = db.session.get(Enrollment, enr_id)
            self.assertIsNotNone(db_enr)
            self.assertEqual(db_enr.student_id, self.s1_id)
            self.assertEqual(db_enr.status, "ACTIVE")

            db_rec = db.session.get(AttendanceRecord, rec_id)
            self.assertIsNotNone(db_rec)
            self.assertEqual(db_rec.student_id, self.s1_id)
            self.assertEqual(db_rec.status, "PRESENT")
            self.assertEqual(db_rec.confidence_score, 0.92)

    # ------------------------------------------------------------------
    # 11. Obsolete embeddings cannot mark attendance
    # ------------------------------------------------------------------
    @patch("app.routes.face.face_service.enroll_student")
    def test_11_obsolete_embeddings_cannot_mark_attendance(self, mock_enroll):
        enc_old = self._unit_vector(15)
        enc_new = self._unit_vector(16)

        with self.app.app_context():
            # Enroll Student 1 with enc_old
            mock_enroll.return_value = {"status": "enrolled", "encoding": enc_old}
            self.client.post(
                "/api/face/enroll",
                headers=self._auth_headers(self.admin_uid, role="ADMIN"),
                data={"student_id": str(self.s1_id), "image": self._dummy_image()},
                content_type="multipart/form-data",
            )

            # Replace with enc_new
            mock_enroll.return_value = {"status": "enrolled", "encoding": enc_new}
            self.client.post(
                "/api/face/enroll",
                headers=self._auth_headers(self.admin_uid, role="ADMIN"),
                data={"student_id": str(self.s1_id), "image": self._dummy_image()},
                content_type="multipart/form-data",
            )

            # Create an active attendance session
            sess = AttendanceSession(
                offering_id=self.offering_id,
                faculty_id=self.faculty_id,
                session_date=date(2026, 10, 21),
                start_time=time(9, 30),
                end_time=time(10, 30),
                status="ACTIVE",
            )
            enr = Enrollment(student_id=self.s1_id, offering_id=self.offering_id, status="ACTIVE")
            db.session.add_all([sess, enr])
            db.session.commit()

            # Live attendance query: registered_students loaded in recognition.py
            # must NOT match enc_old
            import zoneinfo
            tz = zoneinfo.ZoneInfo("Asia/Kolkata")
            now_dt = datetime(2026, 10, 21, 9, 45, 0, tzinfo=tz)
            with patch("app.utils.schedule.get_current_institution_time", return_value=now_dt):
                with patch("app.routes.recognition.face_service.recognize_all_students") as mock_rec:
                    # Case A: Probe matches ONLY obsolete encoding -> recognition library rejects
                    mock_rec.return_value = {"matches": [], "status": "not_recognized", "detected_count": 1}

                    res_rec1 = self.client.post(
                        "/api/faculty/recognition/attendance",
                        headers=self._auth_headers(self.fac_uid, role="FACULTY"),
                        data={"session_id": str(sess.session_id), "image": self._dummy_image()},
                        content_type="multipart/form-data",
                    )
                    self.assertEqual(res_rec1.status_code, 200)
                    self.assertEqual(res_rec1.get_json()["recognized"], [])

                    # No attendance marked
                    rec_count = AttendanceRecord.query.filter_by(session_id=sess.session_id, student_id=self.s1_id).count()
                    self.assertEqual(rec_count, 0)

                    # Case B: Probe matches NEW encoding -> attendance marked
                    mock_rec.return_value = {
                        "matches": [{"student_id": self.s1_id, "similarity_score": 0.88}],
                        "status": "recognized",
                        "detected_count": 1,
                    }
                    res_rec2 = self.client.post(
                        "/api/faculty/recognition/attendance",
                        headers=self._auth_headers(self.fac_uid, role="FACULTY"),
                        data={"session_id": str(sess.session_id), "image": self._dummy_image()},
                        content_type="multipart/form-data",
                    )
                    self.assertEqual(res_rec2.status_code, 200)
                    self.assertEqual(len(res_rec2.get_json()["recognized"]), 1)
                    self.assertEqual(res_rec2.get_json()["recognized"][0]["status"], "PRESENT")

                    rec_count_after = AttendanceRecord.query.filter_by(session_id=sess.session_id, student_id=self.s1_id).count()
                    self.assertEqual(rec_count_after, 1)

    # ------------------------------------------------------------------
    # 12. Administrative duplicate detection and reconciliation workflow
    # ------------------------------------------------------------------
    def test_12_administrative_duplicate_detection_and_reconciliation(self):
        with self.app.app_context():
            # Setup: Student 1 has face profile enc_pair
            enc_pair = self._unit_vector(17)
            fp1 = FaceProfile(student_id=self.s1_id, embedding=enc_pair.tobytes(), model_version="sface_2021dec", is_active=True)
            # Student 2 has identical/very high similarity face profile
            fp2 = FaceProfile(student_id=self.s2_id, embedding=enc_pair.tobytes(), model_version="sface_2021dec", is_active=True)
            db.session.add_all([fp1, fp2])

            # Student 2 has attendance and enrollment
            enr2 = Enrollment(student_id=self.s2_id, offering_id=self.offering_id, status="ACTIVE")
            sess = AttendanceSession(offering_id=self.offering_id, faculty_id=self.faculty_id, session_date=date(2026, 10, 21), start_time=time(9, 30), end_time=time(10, 30), status="CLOSED")
            db.session.add_all([enr2, sess])
            db.session.flush()

            att2 = AttendanceRecord(session_id=sess.session_id, student_id=self.s2_id, status="PRESENT", confidence_score=0.90, recognition_method="FACE", marked_at=datetime(2026, 10, 21, 9, 40, 0))
            db.session.add(att2)
            db.session.commit()

            # 1. Detect duplicates via admin API
            res_dup = self.client.get(
                "/api/admin/students/duplicates",
                headers=self._auth_headers(self.admin_uid, role="ADMIN"),
            )
            self.assertEqual(res_dup.status_code, 200)
            body_dup = res_dup.get_json()
            self.assertTrue(body_dup["success"])
            self.assertGreaterEqual(body_dup["count"], 1)

            # 2. Reconcile: merge Student 2 into canonical Student 1
            res_rec = self.client.post(
                "/api/admin/students/reconcile-duplicates",
                headers=self._auth_headers(self.admin_uid, role="ADMIN"),
                json={
                    "canonical_student_id": self.s1_id,
                    "duplicate_student_id": self.s2_id,
                    "action": "merge_and_deactivate",
                    "reason": "Confirmed duplicate account for Alice",
                },
            )
            self.assertEqual(res_rec.status_code, 200)
            body_rec = res_rec.get_json()
            self.assertTrue(body_rec["success"])
            self.assertEqual(body_rec["reassigned_enrollments"], 1)
            self.assertEqual(body_rec["reassigned_attendance"], 1)

            # 3. Assert database state post-reconciliation:
            # - Canonical Student 1 now has the enrollment and attendance
            self.assertEqual(Enrollment.query.filter_by(student_id=self.s1_id, offering_id=self.offering_id).count(), 1)
            self.assertEqual(AttendanceRecord.query.filter_by(student_id=self.s1_id, session_id=sess.session_id).count(), 1)

            # - Duplicate Student 2 has NO active face profiles
            self.assertEqual(FaceProfile.query.filter_by(student_id=self.s2_id, is_active=True).count(), 0)

            # - Duplicate user account is deactivated
            u2 = db.session.get(User, self.u2_id)
            self.assertFalse(u2.is_active)
