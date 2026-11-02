import os
import unittest
from datetime import date, datetime, time, timedelta

from flask import Flask
from flask_jwt_extended import JWTManager, create_access_token
from sqlalchemy.pool import StaticPool

from app.extensions import bcrypt, db
from app.models import (
    AttendanceRecord,
    AttendanceSession,
    Batch,
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
from app.routes.attendance import attendance_bp
from app.routes.auth import auth_bp
from app.routes.face import face_bp
from app.routes.face_profile import face_profile_bp
from app.routes.faculty import faculty_bp
from app.routes.recognition import recognition_bp
from app.routes.student import student_bp
from app.routes.student_attendance import student_attendance_bp
from app.routes.timetable import timetable_bp
from app.services.cv.face_service import serialize_embedding
from app.services.cv.liveness_service import liveness_manager


class TestFocusedAuthorizationBiometrics(unittest.TestCase):
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
            JWT_TOKEN_LOCATION=["headers"],
            JWT_COOKIE_CSRF_PROTECT=False,
        )
        db.init_app(cls.app)
        bcrypt.init_app(cls.app)
        cls.jwt = JWTManager(cls.app)

        cls.app.register_blueprint(auth_bp)
        cls.app.register_blueprint(admin_bp)
        cls.app.register_blueprint(faculty_bp)
        cls.app.register_blueprint(student_bp)
        cls.app.register_blueprint(face_bp)
        cls.app.register_blueprint(face_profile_bp)
        cls.app.register_blueprint(attendance_bp)
        cls.app.register_blueprint(student_attendance_bp)
        cls.app.register_blueprint(recognition_bp)
        cls.app.register_blueprint(timetable_bp)

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
            # Clean tables
            AttendanceRecord.query.delete()
            AttendanceSession.query.delete()
            Enrollment.query.delete()
            FaceProfile.query.delete()
            TimetableEntry.query.delete()
            CourseOffering.query.delete()
            Course.query.delete()
            Student.query.delete()
            Faculty.query.delete()
            User.query.delete()
            Department.query.delete()
            db.session.commit()

            # Seed test department
            dept = Department(department_code="CSE", department_name="Computer Science")
            db.session.add(dept)
            db.session.flush()

            # Seed Admin User
            pw_hash = bcrypt.generate_password_hash("AdminPass123!").decode("utf-8")
            self.admin_user = User(name="Admin User", email="admin@sams.local", password_hash=pw_hash, role="ADMIN")
            db.session.add(self.admin_user)

            # Seed Faculty User 1 & Profile
            fac_pw = bcrypt.generate_password_hash("FacultyPass123!").decode("utf-8")
            self.fac1_user = User(name="Prof Alice", email="alice@sams.local", password_hash=fac_pw, role="FACULTY")
            db.session.add(self.fac1_user)
            db.session.flush()
            self.fac1 = Faculty(user_id=self.fac1_user.user_id, department_id=dept.department_id, employee_id="FAC001", designation="Associate Professor")
            db.session.add(self.fac1)

            # Seed Faculty User 2 & Profile
            self.fac2_user = User(name="Prof Bob", email="bob@sams.local", password_hash=fac_pw, role="FACULTY")
            db.session.add(self.fac2_user)
            db.session.flush()
            self.fac2 = Faculty(user_id=self.fac2_user.user_id, department_id=dept.department_id, employee_id="FAC002", designation="Assistant Professor")
            db.session.add(self.fac2)

            # Seed Student User 1 & Profile
            stu_pw = bcrypt.generate_password_hash("StudentPass123!").decode("utf-8")
            self.stu1_user = User(name="Student Charlie", email="charlie@sams.local", password_hash=stu_pw, role="STUDENT")
            db.session.add(self.stu1_user)
            db.session.flush()
            self.stu1 = Student(user_id=self.stu1_user.user_id, department_id=dept.department_id, enrollment_no="CSE2026001", semester=1, section="A", academic_year="2026-2027")
            db.session.add(self.stu1)

            # Seed Student User 2 & Profile
            self.stu2_user = User(name="Student Dave", email="dave@sams.local", password_hash=stu_pw, role="STUDENT")
            db.session.add(self.stu2_user)
            db.session.flush()
            self.stu2 = Student(user_id=self.stu2_user.user_id, department_id=dept.department_id, enrollment_no="CSE2026002", semester=1, section="A", academic_year="2026-2027")
            db.session.add(self.stu2)

            # Seed Course & Offerings
            crs = Course(course_code="CS101", course_name="Introduction to Programming", department_id=dept.department_id, credits=4, semester=1)
            db.session.add(crs)
            db.session.flush()

            # Offering 1 assigned to Faculty 1
            self.off1 = CourseOffering(course_id=crs.course_id, faculty_id=self.fac1.faculty_id, semester=1, section="A", batch=2026, academic_year="2026-2027")
            db.session.add(self.off1)
            # Offering 2 assigned to Faculty 2
            self.off2 = CourseOffering(course_id=crs.course_id, faculty_id=self.fac2.faculty_id, semester=1, section="B", batch=2026, academic_year="2026-2027")
            db.session.add(self.off2)
            db.session.flush()

            # Enroll Student 1 in Offering 1
            enr1 = Enrollment(student_id=self.stu1.student_id, offering_id=self.off1.offering_id, status="ACTIVE")
            db.session.add(enr1)

            # Seed Face Profiles (128-d floats for sface_2021dec)
            emb1 = (b"\x00\x00\x80?" * 128)  # 1.0f repeated 128 times
            emb2 = (b"\x00\x00\x00@" * 128)  # 2.0f repeated 128 times
            self.face1 = FaceProfile(student_id=self.stu1.student_id, embedding=emb1, model_version="sface_2021dec", is_active=True)
            self.face2 = FaceProfile(student_id=self.stu2.student_id, embedding=emb2, model_version="sface_2021dec", is_active=True)
            db.session.add(self.face1)
            db.session.add(self.face2)

            db.session.commit()

            # Cache IDs
            self.admin_id = self.admin_user.user_id
            self.fac1_id = self.fac1_user.user_id
            self.fac2_id = self.fac2_user.user_id
            self.stu1_id = self.stu1_user.user_id
            self.stu2_id = self.stu2_user.user_id
            self.student1_id = self.stu1.student_id
            self.student2_id = self.stu2.student_id
            self.offering1_id = self.off1.offering_id
            self.offering2_id = self.off2.offering_id
            self.fac1_profile_id = self.fac1.faculty_id
            self.fac2_profile_id = self.fac2.faculty_id
            self.face1_id = self.face1.face_id
            self.face2_id = self.face2.face_id

    def token_for(self, user_id, role, expires_delta=timedelta(hours=1)):
        with self.app.app_context():
            return create_access_token(
                identity=str(user_id),
                additional_claims={"role": role},
                expires_delta=expires_delta,
            )

    def auth_headers(self, user_id, role):
        return {"Authorization": f"Bearer {self.token_for(user_id, role)}"}

    # -----------------------------------------------------------------
    # 1. Missing, Malformed, and Expired JWT Tokens
    # -----------------------------------------------------------------
    def test_missing_and_malformed_jwt(self):
        # Missing auth header on protected endpoint
        r = self.client.get("/api/admin/users")
        self.assertEqual(r.status_code, 401)

        # Malformed JWT header
        r = self.client.get("/api/admin/users", headers={"Authorization": "Bearer not-a-valid-jwt-token"})
        self.assertIn(r.status_code, (401, 422))

    def test_expired_jwt(self):
        # Issue an expired JWT (10 seconds in the past)
        expired_token = self.token_for(self.admin_id, "ADMIN", expires_delta=timedelta(seconds=-10))
        r = self.client.get("/api/admin/users", headers={"Authorization": f"Bearer {expired_token}"})
        self.assertEqual(r.status_code, 401)
        data = r.get_json() or {}
        self.assertTrue("expired" in data.get("msg", "").lower() or "expired" in data.get("message", "").lower())

    # -----------------------------------------------------------------
    # 2. Portal Role Boundaries (ADMIN vs FACULTY vs STUDENT)
    # -----------------------------------------------------------------
    def test_role_boundaries_admin_faculty_student(self):
        admin_h = self.auth_headers(self.admin_id, "ADMIN")
        fac_h = self.auth_headers(self.fac1_id, "FACULTY")
        stu_h = self.auth_headers(self.stu1_id, "STUDENT")

        # Admin route (/api/admin/users):
        self.assertEqual(self.client.get("/api/admin/users", headers=stu_h).status_code, 403)
        self.assertEqual(self.client.get("/api/admin/users", headers=fac_h).status_code, 403)
        self.assertEqual(self.client.get("/api/admin/users", headers=admin_h).status_code, 200)

        # Faculty route (/api/faculty/courses):
        self.assertEqual(self.client.get("/api/faculty/courses", headers=stu_h).status_code, 403)
        self.assertEqual(self.client.get("/api/faculty/courses", headers=fac_h).status_code, 200)

        # Student route (/api/student/dashboard):
        self.assertEqual(self.client.get("/api/student/dashboard", headers=fac_h).status_code, 403)
        self.assertEqual(self.client.get("/api/student/dashboard", headers=stu_h).status_code, 200)

    # -----------------------------------------------------------------
    # 3. Cross-Student Face Profile Access & BOLA/IDOR Defenses
    # -----------------------------------------------------------------
    def test_cross_student_face_profile_isolation(self):
        stu1_h = self.auth_headers(self.stu1_id, "STUDENT")
        stu2_h = self.auth_headers(self.stu2_id, "STUDENT")
        admin_h = self.auth_headers(self.admin_id, "ADMIN")
        fac_h = self.auth_headers(self.fac1_id, "FACULTY")

        # Student 1 fetches own face profile
        r1 = self.client.get("/api/student/face-profile", headers=stu1_h)
        self.assertEqual(r1.status_code, 200)
        self.assertEqual(r1.get_json()["data"]["student_id"], self.student1_id)

        # Student 1 deactivates own face profile
        r_del = self.client.delete("/api/student/face-profile", headers=stu1_h)
        self.assertEqual(r_del.status_code, 200)

        with self.app.app_context():
            p1 = db.session.get(FaceProfile, self.face1_id)
            p2 = db.session.get(FaceProfile, self.face2_id)
            self.assertFalse(p1.is_active, "Student 1's profile should be deactivated")
            self.assertTrue(p2.is_active, "Student 2's profile must remain untouched")

        # Student 1 attempts to enroll face for Student 2 -> MUST BE 403
        r_enroll_spoof = self.client.post("/api/face/enroll", headers=stu1_h, json={
            "student_id": self.student2_id,
            "image": "invalid_placeholder",
        })
        self.assertEqual(r_enroll_spoof.status_code, 403)
        self.assertIn("own face", r_enroll_spoof.get_json()["message"].lower())

        # Student 1 attempts to view Student 2's face status -> MUST BE 403 (BOLA Fix)
        r_status_spoof = self.client.get(f"/api/face/status/{self.student2_id}", headers=stu1_h)
        self.assertEqual(r_status_spoof.status_code, 403)

        # Student 2 views own face status -> 200 OK
        r_status_own = self.client.get(f"/api/face/status/{self.student2_id}", headers=stu2_h)
        self.assertEqual(r_status_own.status_code, 200)

        # Faculty and Admin can inspect student face registration status
        self.assertEqual(self.client.get(f"/api/face/status/{self.student2_id}", headers=fac_h).status_code, 200)
        self.assertEqual(self.client.get(f"/api/face/status/{self.student2_id}", headers=admin_h).status_code, 200)

    # -----------------------------------------------------------------
    # 4. Cross-Student Attendance Scoping
    # -----------------------------------------------------------------
    def test_cross_student_attendance_isolation(self):
        stu1_h = self.auth_headers(self.stu1_id, "STUDENT")
        stu2_h = self.auth_headers(self.stu2_id, "STUDENT")

        # Seed attendance session and record for Student 1 only
        with self.app.app_context():
            sess = AttendanceSession(
                offering_id=self.offering1_id,
                faculty_id=self.fac1_profile_id,
                session_date=date.today(),
                start_time=time(9, 0),
                end_time=time(10, 0),
                status="CLOSED",
            )
            db.session.add(sess)
            db.session.flush()

            rec1 = AttendanceRecord(
                session_id=sess.session_id,
                student_id=self.student1_id,
                status="PRESENT",
                recognition_method="FACE",
                confidence_score=92.5,
                marked_at=datetime.utcnow(),
            )
            db.session.add(rec1)
            db.session.commit()

        # Student 1 attendance history contains 1 record
        r1 = self.client.get("/api/student/attendance/", headers=stu1_h)
        self.assertEqual(r1.status_code, 200)
        self.assertEqual(r1.get_json()["total_records"], 1)

        # Student 2 attendance history contains 0 records (isolated)
        r2 = self.client.get("/api/student/attendance/", headers=stu2_h)
        self.assertEqual(r2.status_code, 200)
        self.assertEqual(r2.get_json()["total_records"], 0)

    # -----------------------------------------------------------------
    # 5. Cross-Faculty Attendance & Session Authorization
    # -----------------------------------------------------------------
    def test_cross_faculty_attendance_isolation(self):
        fac1_h = self.auth_headers(self.fac1_id, "FACULTY")
        fac2_h = self.auth_headers(self.fac2_id, "FACULTY")

        # Faculty 2 attempts to start attendance for Offering 1 (assigned to Faculty 1) -> 403
        r_start = self.client.post("/api/faculty/attendance/sessions", headers=fac2_h, json={
            "offering_id": self.offering1_id,
        })
        self.assertEqual(r_start.status_code, 403)
        self.assertIn("not authorized", r_start.get_json()["message"].lower())

        # Start active session under Faculty 1
        with self.app.app_context():
            sess = AttendanceSession(
                offering_id=self.offering1_id,
                faculty_id=self.fac1_profile_id,
                session_date=date.today(),
                start_time=time(8, 0),
                end_time=time(18, 0),
                status="ACTIVE",
            )

            db.session.add(sess)
            db.session.commit()
            sess_id = sess.session_id

        # Faculty 2 attempts to close Faculty 1's active session -> 403
        r_close = self.client.post(f"/api/faculty/attendance/sessions/{sess_id}/close", headers=fac2_h)
        self.assertEqual(r_close.status_code, 403)

        # Faculty 2 attempts to view records of Faculty 1's session -> 403
        r_view = self.client.get(f"/api/faculty/attendance/sessions/{sess_id}/records", headers=fac2_h)
        self.assertEqual(r_view.status_code, 403)

        # Faculty 1 can view records -> 200
        r_own_view = self.client.get(f"/api/faculty/attendance/sessions/{sess_id}/records", headers=fac1_h)
        self.assertEqual(r_own_view.status_code, 200)

    # -----------------------------------------------------------------
    # 6. Biometric Deletion Authorization
    # -----------------------------------------------------------------
    def test_biometric_deletion_authorization(self):
        stu1_h = self.auth_headers(self.stu1_id, "STUDENT")
        fac1_h = self.auth_headers(self.fac1_id, "FACULTY")
        admin_h = self.auth_headers(self.admin_id, "ADMIN")

        # Student cannot delete biometric via admin route
        r_stu = self.client.delete(f"/api/face/{self.student1_id}", headers=stu1_h)
        self.assertEqual(r_stu.status_code, 403)

        # Faculty cannot delete biometric via admin route
        r_fac = self.client.delete(f"/api/face/{self.student1_id}", headers=fac1_h)
        self.assertEqual(r_fac.status_code, 403)

        # Admin can delete/deactivate biometric
        r_adm = self.client.delete(f"/api/face/{self.student1_id}", headers=admin_h, json={
            "reason": "Administrative reset for test",
        })
        self.assertEqual(r_adm.status_code, 200)
        self.assertTrue(r_adm.get_json()["success"])

    # -----------------------------------------------------------------
    # 7. Liveness Challenge Binding, Replay Prevention, and Expiry
    # -----------------------------------------------------------------
    def test_liveness_challenge_lifecycle_binding_and_replay(self):
        session_id = 999
        faculty_id = self.fac1_id
        student_id = self.student1_id

        # 1. Challenge generation
        challenge = liveness_manager.create_challenge(session_id=session_id, faculty_id=faculty_id)
        cid = challenge["challenge_id"]
        self.assertTrue(cid.startswith("clv_"))
        self.assertIn("nonce", challenge)

        # 2. Challenge retrieval & verification token issuance
        retrieved = liveness_manager.get_challenge(cid)
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved["session_id"], session_id)
        self.assertEqual(retrieved["faculty_id"], faculty_id)

        vtok = liveness_manager.issue_verification_token(
            challenge_id=cid,
            student_id=student_id,
            session_id=session_id,
            faculty_id=faculty_id,
            confidence_score=0.94,
            pad_score=0.96,
        )
        self.assertTrue(vtok.startswith("vtok_"))

        # 3. Session mismatch check
        ok_wrong_sess, reason, _ = liveness_manager.consume_verification_token(
            token=vtok,
            expected_session_id=888,  # Mismatched session
            expected_student_id=student_id,
            expected_faculty_id=faculty_id,
        )
        self.assertFalse(ok_wrong_sess)
        self.assertIn("does not match attendance session", reason)

        # 4. Faculty mismatch check
        ok_wrong_fac, reason, _ = liveness_manager.consume_verification_token(
            token=vtok,
            expected_session_id=session_id,
            expected_student_id=student_id,
            expected_faculty_id=9999,  # Mismatched faculty
        )
        self.assertFalse(ok_wrong_fac)
        self.assertIn("authorized faculty member", reason)

        # 5. Student mismatch check
        ok_wrong_stu, reason, _ = liveness_manager.consume_verification_token(
            token=vtok,
            expected_session_id=session_id,
            expected_student_id=9999,  # Mismatched student
            expected_faculty_id=faculty_id,
        )
        self.assertFalse(ok_wrong_stu)
        self.assertIn("student identity", reason)

        # 6. Valid atomic consumption
        ok, reason, token_data = liveness_manager.consume_verification_token(
            token=vtok,
            expected_session_id=session_id,
            expected_student_id=student_id,
            expected_faculty_id=faculty_id,
        )
        self.assertTrue(ok)
        self.assertTrue(token_data["is_consumed"])

        # 7. Replay attack rejection (attempt to reuse consumed token)
        ok_replay, replay_reason, _ = liveness_manager.consume_verification_token(
            token=vtok,
            expected_session_id=session_id,
            expected_student_id=student_id,
            expected_faculty_id=faculty_id,
        )
        self.assertFalse(ok_replay)
        self.assertIn("already been used", replay_reason)

    # -----------------------------------------------------------------
    # 8. Faculty Manual Attendance Override Disabled
    # -----------------------------------------------------------------
    def test_faculty_manual_attendance_disabled(self):
        fac1_h = self.auth_headers(self.fac1_id, "FACULTY")

        # Faculty calling POST /records -> 403
        r_post = self.client.post("/api/faculty/attendance/sessions/1/records", headers=fac1_h, json={
            "student_id": self.student1_id,
            "status": "PRESENT",
        })
        self.assertEqual(r_post.status_code, 403)
        self.assertIn("manual attendance marking by faculty is disabled", r_post.get_json()["message"].lower())

        # Faculty calling PATCH /records/<id> -> 403
        r_patch = self.client.patch(f"/api/faculty/attendance/sessions/1/records/{self.student1_id}", headers=fac1_h, json={
            "status": "PRESENT",
        })
        self.assertEqual(r_patch.status_code, 403)
        self.assertIn("manual attendance marking by faculty is disabled", r_patch.get_json()["message"].lower())

    # -----------------------------------------------------------------
    # 9. Logout Cookie Handling & Stateless JWT Limitation
    # -----------------------------------------------------------------
    def test_logout_unsets_cookies(self):
        r = self.client.post("/api/auth/logout")
        self.assertEqual(r.status_code, 200)
        set_cookie = r.headers.get("Set-Cookie", "")
        # Verifies that logout unsets the JWT access cookie
        self.assertIn("access_token_cookie=;", set_cookie)

    # -----------------------------------------------------------------
    # 10. Invalid Identifiers and Malformed Request Payloads
    # -----------------------------------------------------------------
    def test_invalid_identifiers_and_malformed_payloads(self):
        admin_h = self.auth_headers(self.admin_id, "ADMIN")

        # Non-integer identifier in URL path
        r_invalid_id = self.client.get("/api/admin/users/not-an-id", headers=admin_h)
        self.assertEqual(r_invalid_id.status_code, 404)

        # Malformed non-JSON payload when JSON expected
        r_malformed = self.client.post(
            "/api/admin/users",
            headers={**admin_h, "Content-Type": "application/json"},
            data="not-valid-json-string{",
        )
        self.assertEqual(r_malformed.status_code, 400)


if __name__ == "__main__":
    unittest.main()
