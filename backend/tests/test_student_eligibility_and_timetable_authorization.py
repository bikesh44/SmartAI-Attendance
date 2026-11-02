import io
import unittest
from datetime import date, datetime, time
from unittest.mock import patch
from zoneinfo import ZoneInfo

import cv2
import numpy as np
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
from app.routes.attendance import attendance_bp
from app.routes.recognition import recognition_bp
from app.services.cv.attendance_service import (
    mark_face_attendance,
    validate_student_attendance_eligibility,
)


class TestStudentEligibilityAndTimetableAuthorization(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tz = ZoneInfo("Asia/Kolkata")
        cls.app = Flask(__name__)
        cls.app.config.update(
            TESTING=True,
            SECRET_KEY="test-secret-eligibility-auth",
            JWT_SECRET_KEY="test-jwt-secret-key-32-bytes-eligibility",
            SQLALCHEMY_DATABASE_URI="sqlite://",
            SQLALCHEMY_TRACK_MODIFICATIONS=False,
            SQLALCHEMY_ENGINE_OPTIONS={
                "poolclass": StaticPool,
                "connect_args": {"check_same_thread": False},
            },
            JWT_TOKEN_LOCATION=["headers"],
            INSTITUTION_TIMEZONE="Asia/Kolkata",
        )

        db.init_app(cls.app)
        bcrypt.init_app(cls.app)
        JWTManager(cls.app)

        cls.app.register_blueprint(attendance_bp)
        cls.app.register_blueprint(recognition_bp)

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

            # Department
            self.dept_cse = Department(department_name="Computer Science", department_code="CSE")
            self.dept_ece = Department(department_name="Electronics", department_code="ECE")
            db.session.add_all([self.dept_cse, self.dept_ece])
            db.session.flush()

            # Batches
            self.batch_2024 = Batch(batch_name="2024-2028", is_active=True)
            self.batch_2023 = Batch(batch_name="2023-2027", is_active=True)
            db.session.add_all([self.batch_2024, self.batch_2023])
            db.session.flush()

            # Faculty Users
            self.user_fac_a = User(name="Dr. Alan Turing", email="turing@univ.edu", password_hash="pw", role="FACULTY")
            self.user_fac_b = User(name="Dr. Ada Lovelace", email="lovelace@univ.edu", password_hash="pw", role="FACULTY")
            self.user_admin = User(name="Admin User", email="admin@univ.edu", password_hash="pw", role="ADMIN")
            db.session.add_all([self.user_fac_a, self.user_fac_b, self.user_admin])
            db.session.flush()

            self.fac_a = Faculty(user_id=self.user_fac_a.user_id, department_id=self.dept_cse.department_id, employee_id="FAC-A01", designation="Professor")
            self.fac_b = Faculty(user_id=self.user_fac_b.user_id, department_id=self.dept_cse.department_id, employee_id="FAC-B02", designation="Assistant Professor")
            db.session.add_all([self.fac_a, self.fac_b])
            db.session.flush()

            # Course: CSE-501, Semester 5, Batch 2024-2028
            self.course = Course(
                department_id=self.dept_cse.department_id,
                course_code="BCSE-501",
                course_name="Machine Learning",
                semester=5,
                credits=4,
                batch="2024-2028",
                is_active=True,
            )
            db.session.add(self.course)
            db.session.flush()

            # Course Offering A: Section A, Semester 5, 2026-27, Room CSE-5A-01
            self.offering_a = CourseOffering(
                course_id=self.course.course_id,
                faculty_id=self.fac_a.faculty_id,
                academic_year="2026-27",
                semester=5,
                section="A",
                room="CSE-5A-01",
            )
            # Course Offering B: Section B, Semester 5, 2026-27, Room CSE-5B-02
            self.offering_b = CourseOffering(
                course_id=self.course.course_id,
                faculty_id=self.fac_b.faculty_id,
                academic_year="2026-27",
                semester=5,
                section="B",
                room="CSE-5B-02",
            )
            db.session.add_all([self.offering_a, self.offering_b])
            db.session.flush()

            # Timetable Entry for Offering A: Today (Wednesday), 09:30 to 10:30
            self.test_date = date(2026, 10, 21)  # Wednesday
            self.tt_a = TimetableEntry(
                offering_id=self.offering_a.offering_id,
                day_of_week="Wednesday",
                start_time=time(9, 30),
                end_time=time(10, 30),
                room="CSE-5A-01",
            )
            db.session.add(self.tt_a)
            db.session.flush()

            # Students:
            # 1. stu_eligible: Section A, Semester 5, Batch 2024, Dept CSE
            self.u_stu1 = User(name="Alice Eligible", email="alice@stu.univ.edu", password_hash="pw", role="STUDENT", is_active=True)
            db.session.add(self.u_stu1)
            db.session.flush()
            self.stu_eligible = Student(
                user_id=self.u_stu1.user_id,
                department_id=self.dept_cse.department_id,
                batch_id=self.batch_2024.batch_id,
                enrollment_no="CSE-24-001",
                semester=5,
                section="A",
                academic_year="2026-27",
            )

            # 2. stu_wrong_section: Section B, Semester 5, Batch 2024, Dept CSE
            self.u_stu2 = User(name="Bob SectionB", email="bob@stu.univ.edu", password_hash="pw", role="STUDENT", is_active=True)
            db.session.add(self.u_stu2)
            db.session.flush()
            self.stu_wrong_section = Student(
                user_id=self.u_stu2.user_id,
                department_id=self.dept_cse.department_id,
                batch_id=self.batch_2024.batch_id,
                enrollment_no="CSE-24-002",
                semester=5,
                section="B",
                academic_year="2026-27",
            )

            # 3. stu_wrong_semester: Section A, Semester 3, Batch 2024, Dept CSE
            self.u_stu3 = User(name="Charlie Sem3", email="charlie@stu.univ.edu", password_hash="pw", role="STUDENT", is_active=True)
            db.session.add(self.u_stu3)
            db.session.flush()
            self.stu_wrong_semester = Student(
                user_id=self.u_stu3.user_id,
                department_id=self.dept_cse.department_id,
                batch_id=self.batch_2024.batch_id,
                enrollment_no="CSE-24-003",
                semester=3,
                section="A",
                academic_year="2026-27",
            )

            # 4. stu_wrong_batch: Section A, Semester 5, Batch 2023, Dept CSE
            self.u_stu4 = User(name="Diana Batch23", email="diana@stu.univ.edu", password_hash="pw", role="STUDENT", is_active=True)
            db.session.add(self.u_stu4)
            db.session.flush()
            self.stu_wrong_batch = Student(
                user_id=self.u_stu4.user_id,
                department_id=self.dept_cse.department_id,
                batch_id=self.batch_2023.batch_id,
                enrollment_no="CSE-23-004",
                semester=5,
                section="A",
                academic_year="2026-27",
            )

            # 5. stu_not_enrolled: Section A, Semester 5, Batch 2024, Dept CSE (NOT in enrollments)
            self.u_stu5 = User(name="Eve Unenrolled", email="eve@stu.univ.edu", password_hash="pw", role="STUDENT", is_active=True)
            db.session.add(self.u_stu5)
            db.session.flush()
            self.stu_not_enrolled = Student(
                user_id=self.u_stu5.user_id,
                department_id=self.dept_cse.department_id,
                batch_id=self.batch_2024.batch_id,
                enrollment_no="CSE-24-005",
                semester=5,
                section="A",
                academic_year="2026-27",
            )

            # 6. stu_inactive_user: Section A, Semester 5, user is_active=False
            self.u_stu6 = User(name="Frank Inactive", email="frank@stu.univ.edu", password_hash="pw", role="STUDENT", is_active=False)
            db.session.add(self.u_stu6)
            db.session.flush()
            self.stu_inactive = Student(
                user_id=self.u_stu6.user_id,
                department_id=self.dept_cse.department_id,
                batch_id=self.batch_2024.batch_id,
                enrollment_no="CSE-24-006",
                semester=5,
                section="A",
                academic_year="2026-27",
            )

            db.session.add_all([
                self.stu_eligible,
                self.stu_wrong_section,
                self.stu_wrong_semester,
                self.stu_wrong_batch,
                self.stu_not_enrolled,
                self.stu_inactive,
            ])
            db.session.flush()

            # Enrollments:
            # stu_eligible -> offering_a
            # stu_wrong_section -> offering_b (Section B)
            # stu_wrong_batch -> offering_a
            # stu_inactive -> offering_a
            db.session.add_all([
                Enrollment(student_id=self.stu_eligible.student_id, offering_id=self.offering_a.offering_id, status="ACTIVE"),
                Enrollment(student_id=self.stu_wrong_section.student_id, offering_id=self.offering_b.offering_id, status="ACTIVE"),
                Enrollment(student_id=self.stu_wrong_batch.student_id, offering_id=self.offering_a.offering_id, status="ACTIVE"),
                Enrollment(student_id=self.stu_inactive.student_id, offering_id=self.offering_a.offering_id, status="ACTIVE"),
            ])

            # Attendance Session for Offering A
            self.session_a = AttendanceSession(
                offering_id=self.offering_a.offering_id,
                faculty_id=self.fac_a.faculty_id,
                session_date=self.test_date,
                start_time=time(9, 30),
                end_time=time(10, 30),
                status="ACTIVE",
            )
            db.session.add(self.session_a)
            db.session.flush()

            # Face profile for eligible student
            self.face_stu1 = FaceProfile(
                student_id=self.stu_eligible.student_id,
                embedding=np.ones((1, 128), dtype=np.float32).tobytes(),
                model_version="sface_2021dec",
                is_active=True,
            )
            # Face profile for section B student
            self.face_stu2 = FaceProfile(
                student_id=self.stu_wrong_section.student_id,
                embedding=np.full((1, 128), 2.0, dtype=np.float32).tobytes(),
                model_version="sface_2021dec",
                is_active=True,
            )
            db.session.add_all([self.face_stu1, self.face_stu2])
            db.session.commit()

            self.fac_a_uid = self.user_fac_a.user_id
            self.fac_b_uid = self.user_fac_b.user_id
            self.fac_a_id = self.fac_a.faculty_id
            self.fac_b_id = self.fac_b.faculty_id
            self.admin_uid = self.user_admin.user_id
            self.sess_a_id = self.session_a.session_id
            self.stu_elig_id = self.stu_eligible.student_id
            self.stu_b_id = self.stu_wrong_section.student_id
            self.stu_sem3_id = self.stu_wrong_semester.student_id
            self.stu_batch23_id = self.stu_wrong_batch.student_id
            self.stu_unenrolled_id = self.stu_not_enrolled.student_id
            self.stu_inactive_id = self.stu_inactive.student_id

    def _headers(self, user_id, role="FACULTY"):
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

    # -------------------------------------------------------------
    # 1. An eligible student is accepted during the scheduled class window
    # -------------------------------------------------------------
    def test_01_eligible_student_accepted_during_scheduled_window(self):
        active_time = datetime(2026, 10, 21, 9, 45, 0, tzinfo=self.tz)
        with self.app.app_context():
            with patch("app.utils.schedule.get_current_institution_time", return_value=active_time):
                record, message = mark_face_attendance(
                    session_id=self.sess_a_id,
                    student_id=self.stu_elig_id,
                    confidence_score=0.88,
                    faculty_id=self.fac_a_id,
                    current_dt=active_time,
                )
                self.assertIsNotNone(record)
                self.assertEqual(record.status, "PRESENT")
                self.assertEqual(message, "Attendance marked successfully")

                # Verify in DB
                db_rec = AttendanceRecord.query.filter_by(
                    session_id=self.sess_a_id,
                    student_id=self.stu_elig_id,
                ).first()
                self.assertIsNotNone(db_rec)
                self.assertEqual(db_rec.status, "PRESENT")

    # -------------------------------------------------------------
    # 2. A recognized student from another section is rejected
    # -------------------------------------------------------------
    def test_02_recognized_student_from_another_section_rejected(self):
        active_time = datetime(2026, 10, 21, 9, 45, 0, tzinfo=self.tz)
        with self.app.app_context():
            with patch("app.utils.schedule.get_current_institution_time", return_value=active_time):
                record, message = mark_face_attendance(
                    session_id=self.sess_a_id,
                    student_id=self.stu_b_id,
                    confidence_score=0.91,
                    faculty_id=self.fac_a_id,
                    current_dt=active_time,
                )
                self.assertIsNone(record)
                self.assertTrue("section" in message.lower() or "not enrolled" in message.lower())

                # Verify NO attendance record created in DB
                db_rec = AttendanceRecord.query.filter_by(
                    session_id=self.sess_a_id,
                    student_id=self.stu_b_id,
                ).first()
                self.assertIsNone(db_rec)

    # -------------------------------------------------------------
    # 3. A recognized student from another semester is rejected
    # -------------------------------------------------------------
    def test_03_recognized_student_from_another_semester_rejected(self):
        active_time = datetime(2026, 10, 21, 9, 45, 0, tzinfo=self.tz)
        with self.app.app_context():
            with patch("app.utils.schedule.get_current_institution_time", return_value=active_time):
                record, message = mark_face_attendance(
                    session_id=self.sess_a_id,
                    student_id=self.stu_sem3_id,
                    confidence_score=0.85,
                    faculty_id=self.fac_a_id,
                    current_dt=active_time,
                )
                self.assertIsNone(record)
                self.assertTrue("semester" in message.lower() or "not enrolled" in message.lower())

                # Verify NO record in DB
                db_rec = AttendanceRecord.query.filter_by(
                    session_id=self.sess_a_id,
                    student_id=self.stu_sem3_id,
                ).first()
                self.assertIsNone(db_rec)

    # -------------------------------------------------------------
    # 4. A student from another academic batch/year is rejected when course specifies batch
    # -------------------------------------------------------------
    def test_04_student_from_another_batch_rejected(self):
        active_time = datetime(2026, 10, 21, 9, 45, 0, tzinfo=self.tz)
        with self.app.app_context():
            with patch("app.utils.schedule.get_current_institution_time", return_value=active_time):
                record, message = mark_face_attendance(
                    session_id=self.sess_a_id,
                    student_id=self.stu_batch23_id,
                    confidence_score=0.87,
                    faculty_id=self.fac_a_id,
                    current_dt=active_time,
                )
                self.assertIsNone(record)
                self.assertIn("batch", message.lower())

                # Verify NO record in DB
                db_rec = AttendanceRecord.query.filter_by(
                    session_id=self.sess_a_id,
                    student_id=self.stu_batch23_id,
                ).first()
                self.assertIsNone(db_rec)

    # -------------------------------------------------------------
    # 5. A student from another course offering is rejected even if sharing department and semester
    # -------------------------------------------------------------
    def test_05_student_from_another_offering_rejected(self):
        active_time = datetime(2026, 10, 21, 9, 45, 0, tzinfo=self.tz)
        with self.app.app_context():
            with patch("app.utils.schedule.get_current_institution_time", return_value=active_time):
                # Student 2 is in Section B of the same course and semester, enrolled in offering_b, NOT offering_a
                record, message = mark_face_attendance(
                    session_id=self.sess_a_id,
                    student_id=self.stu_b_id,
                    confidence_score=0.89,
                    faculty_id=self.fac_a_id,
                    current_dt=active_time,
                )
                self.assertIsNone(record)

                db_rec = AttendanceRecord.query.filter_by(
                    session_id=self.sess_a_id,
                    student_id=self.stu_b_id,
                ).first()
                self.assertIsNone(db_rec)

    # -------------------------------------------------------------
    # 6. A student with no verifiable enrollment is rejected
    # -------------------------------------------------------------
    def test_06_student_with_no_verifiable_enrollment_rejected(self):
        active_time = datetime(2026, 10, 21, 9, 45, 0, tzinfo=self.tz)
        with self.app.app_context():
            with patch("app.utils.schedule.get_current_institution_time", return_value=active_time):
                record, message = mark_face_attendance(
                    session_id=self.sess_a_id,
                    student_id=self.stu_unenrolled_id,
                    confidence_score=0.85,
                    faculty_id=self.fac_a_id,
                    current_dt=active_time,
                )
                self.assertIsNone(record)
                self.assertIn("not enrolled", message.lower())

                db_rec = AttendanceRecord.query.filter_by(
                    session_id=self.sess_a_id,
                    student_id=self.stu_unenrolled_id,
                ).first()
                self.assertIsNone(db_rec)

    # -------------------------------------------------------------
    # 7. An unauthorized faculty member cannot mark attendance for another faculty's session
    # -------------------------------------------------------------
    def test_07_unauthorized_faculty_cannot_mark_attendance(self):
        active_time = datetime(2026, 10, 21, 9, 45, 0, tzinfo=self.tz)
        with self.app.app_context():
            with patch("app.utils.schedule.get_current_institution_time", return_value=active_time):
                # Faculty B attempts to mark attendance in Faculty A's session
                record, message = mark_face_attendance(
                    session_id=self.sess_a_id,
                    student_id=self.stu_elig_id,
                    confidence_score=0.88,
                    faculty_id=self.fac_b_id,
                    current_dt=active_time,
                )
                self.assertIsNone(record)
                self.assertIn("does not belong to this faculty", message.lower())

                # Attempt via HTTP recognition route
                res = self.client.post(
                    "/api/faculty/recognition/attendance",
                    headers=self._headers(self.fac_b_uid),
                    data={
                        "session_id": str(self.sess_a_id),
                        "image": self._dummy_image(),
                    },
                    content_type="multipart/form-data",
                )
                self.assertEqual(res.status_code, 403)

    # -------------------------------------------------------------
    # 8. A recognized but ineligible student's attendance is not inserted into the database
    # -------------------------------------------------------------
    @patch("app.routes.recognition.face_service.recognize_all_students")
    def test_08_recognized_ineligible_student_not_inserted_into_db(self, mock_rec):
        active_time = datetime(2026, 10, 21, 9, 45, 0, tzinfo=self.tz)
        mock_rec.return_value = {
            "matches": [
                {
                    "student_id": self.stu_b_id,  # Section B student recognized in Section A session
                    "similarity_score": 0.75,
                }
            ],
            "status": "recognized",
            "detected_count": 1,
        }

        with self.app.app_context():
            with patch("app.utils.schedule.get_current_institution_time", return_value=active_time):
                res = self.client.post(
                    "/api/faculty/recognition/attendance",
                    headers=self._headers(self.fac_a_uid),
                    data={
                        "session_id": str(self.sess_a_id),
                        "image": self._dummy_image(),
                    },
                    content_type="multipart/form-data",
                )
                self.assertEqual(res.status_code, 200)
                body = res.get_json()
                self.assertTrue(body["success"])

                # Assert returned item is marked ineligible
                rec_item = body["recognized"][0]
                self.assertEqual(rec_item["status"], "INELIGIBLE")
                self.assertFalse(rec_item["is_eligible"])
                self.assertIsNone(rec_item["attendance_id"])

                # Verify in DB: ABSOLUTELY NO RECORD exists
                db_rec = AttendanceRecord.query.filter_by(
                    session_id=self.sess_a_id,
                    student_id=self.stu_b_id,
                ).first()
                self.assertIsNone(db_rec)

    # -------------------------------------------------------------
    # 9. Duplicate attendance remains prevented
    # -------------------------------------------------------------
    def test_09_duplicate_attendance_remains_prevented(self):
        active_time = datetime(2026, 10, 21, 9, 45, 0, tzinfo=self.tz)
        with self.app.app_context():
            with patch("app.utils.schedule.get_current_institution_time", return_value=active_time):
                # First mark
                r1, m1 = mark_face_attendance(
                    session_id=self.sess_a_id,
                    student_id=self.stu_elig_id,
                    confidence_score=0.90,
                    faculty_id=self.fac_a_id,
                    current_dt=active_time,
                )
                self.assertIsNotNone(r1)
                self.assertEqual(m1, "Attendance marked successfully")

                # Second mark attempt
                r2, m2 = mark_face_attendance(
                    session_id=self.sess_a_id,
                    student_id=self.stu_elig_id,
                    confidence_score=0.92,
                    faculty_id=self.fac_a_id,
                    current_dt=active_time,
                )
                self.assertIsNotNone(r2)
                self.assertEqual(m2, "Attendance already marked")
                self.assertEqual(r1.attendance_id, r2.attendance_id)

                # DB records count must strictly remain 1
                count = AttendanceRecord.query.filter_by(
                    session_id=self.sess_a_id,
                    student_id=self.stu_elig_id,
                ).count()
                self.assertEqual(count, 1)

    # -------------------------------------------------------------
    # 10. Attendance is rejected before the scheduled start (e.g. 08:54 AM for 09:30 AM class)
    # -------------------------------------------------------------
    def test_10_attendance_rejected_before_scheduled_start(self):
        time_before = datetime(2026, 10, 21, 8, 54, 0, tzinfo=self.tz)
        with self.app.app_context():
            with patch("app.utils.schedule.get_current_institution_time", return_value=time_before):
                record, message = mark_face_attendance(
                    session_id=self.sess_a_id,
                    student_id=self.stu_elig_id,
                    confidence_score=0.95,
                    faculty_id=self.fac_a_id,
                    current_dt=time_before,
                )
                self.assertIsNone(record)
                self.assertIn("scheduled start time", message.lower())

                # Reset session to ACTIVE to verify HTTP endpoint's own schedule rejection
                sess = db.session.get(AttendanceSession, self.sess_a_id)
                sess.status = "ACTIVE"
                db.session.commit()

                # Attempt via HTTP
                res = self.client.post(
                    "/api/faculty/recognition/attendance",
                    headers=self._headers(self.fac_a_uid),
                    data={
                        "session_id": str(self.sess_a_id),
                        "image": self._dummy_image(),
                    },
                    content_type="multipart/form-data",
                )
                self.assertEqual(res.status_code, 400)
                self.assertIn("scheduled start time", res.get_json()["message"].lower())

                # Verify no attendance record in DB
                db_rec = AttendanceRecord.query.filter_by(
                    session_id=self.sess_a_id,
                    student_id=self.stu_elig_id,
                ).first()
                self.assertIsNone(db_rec)

    # -------------------------------------------------------------
    # 11. Attendance is accepted at the exact start boundary (09:30:00 AM)
    # -------------------------------------------------------------
    def test_11_attendance_accepted_at_exact_start_boundary(self):
        exact_start = datetime(2026, 10, 21, 9, 30, 0, tzinfo=self.tz)
        with self.app.app_context():
            with patch("app.utils.schedule.get_current_institution_time", return_value=exact_start):
                record, message = mark_face_attendance(
                    session_id=self.sess_a_id,
                    student_id=self.stu_elig_id,
                    confidence_score=0.95,
                    faculty_id=self.fac_a_id,
                    current_dt=exact_start,
                )
                self.assertIsNotNone(record)
                self.assertEqual(record.status, "PRESENT")
                self.assertEqual(message, "Attendance marked successfully")

                # Verify in DB
                db_rec = AttendanceRecord.query.filter_by(
                    session_id=self.sess_a_id,
                    student_id=self.stu_elig_id,
                ).first()
                self.assertIsNotNone(db_rec)

    # -------------------------------------------------------------
    # 12. Attendance is rejected at the exact end boundary (10:30:00 AM)
    # -------------------------------------------------------------
    def test_12_attendance_rejected_at_exact_end_boundary(self):
        exact_end = datetime(2026, 10, 21, 10, 30, 0, tzinfo=self.tz)
        with self.app.app_context():
            with patch("app.utils.schedule.get_current_institution_time", return_value=exact_end):
                record, message = mark_face_attendance(
                    session_id=self.sess_a_id,
                    student_id=self.stu_elig_id,
                    confidence_score=0.95,
                    faculty_id=self.fac_a_id,
                    current_dt=exact_end,
                )
                self.assertIsNone(record)
                self.assertIn("ended", message.lower())

                # Reset session to ACTIVE to verify HTTP endpoint's own schedule rejection
                sess = db.session.get(AttendanceSession, self.sess_a_id)
                sess.status = "ACTIVE"
                db.session.commit()

                # Attempt via HTTP
                res = self.client.post(
                    "/api/faculty/recognition/attendance",
                    headers=self._headers(self.fac_a_uid),
                    data={
                        "session_id": str(self.sess_a_id),
                        "image": self._dummy_image(),
                    },
                    content_type="multipart/form-data",
                )
                self.assertEqual(res.status_code, 409)
                self.assertIn("ended", res.get_json()["message"].lower())

                # Verify no PRESENT attendance record was recorded
                db_rec = AttendanceRecord.query.filter_by(
                    session_id=self.sess_a_id,
                    student_id=self.stu_elig_id,
                    status="PRESENT",
                ).first()
                self.assertIsNone(db_rec)

    # -------------------------------------------------------------
    # 13. A database session marked active cannot bypass student or timetable eligibility
    # -------------------------------------------------------------
    def test_13_active_db_session_cannot_bypass_eligibility_or_schedule(self):
        # Session A is explicitly marked ACTIVE in DB.
        # But test time is 08:54 AM (future class)
        premature_time = datetime(2026, 10, 21, 8, 54, 0, tzinfo=self.tz)
        with self.app.app_context():
            with patch("app.utils.schedule.get_current_institution_time", return_value=premature_time):
                # GET /active must reconcile premature session and return None
                res = self.client.get(
                    "/api/faculty/attendance/sessions/active",
                    headers=self._headers(self.fac_a_uid),
                )
                self.assertEqual(res.status_code, 200)
                self.assertIsNone(res.get_json()["data"])

                # Direct face marking attempt must be rejected
                rec, msg = mark_face_attendance(
                    session_id=self.sess_a_id,
                    student_id=self.stu_elig_id,
                    confidence_score=0.95,
                    faculty_id=self.fac_a_id,
                    current_dt=premature_time,
                )
                self.assertIsNone(rec)

    # -------------------------------------------------------------
    # 14. Manual and alternate attendance endpoints enforce equivalent authorization rules
    # -------------------------------------------------------------
    def test_14_manual_and_alternate_endpoints_enforce_equivalent_rules(self):
        admin_headers = self._headers(self.admin_uid, role="ADMIN")
        active_time = datetime(2026, 10, 21, 9, 45, 0, tzinfo=self.tz)

        with patch("app.utils.schedule.get_current_institution_time", return_value=active_time):
            # 1. Manual mark: Section B student in Section A session -> 403
            res_manual_wrong_sec = self.client.post(
                f"/api/faculty/attendance/sessions/{self.sess_a_id}/records",
                headers=admin_headers,
                json={"student_id": self.stu_b_id, "status": "PRESENT", "recognition_method": "MANUAL"},
            )
            self.assertEqual(res_manual_wrong_sec.status_code, 403)
            self.assertTrue("section" in res_manual_wrong_sec.get_json()["message"].lower() or "not enrolled" in res_manual_wrong_sec.get_json()["message"].lower())

            # 2. Manual mark: Unenrolled student -> 403
            res_manual_unenrolled = self.client.post(
                f"/api/faculty/attendance/sessions/{self.sess_a_id}/records",
                headers=admin_headers,
                json={"student_id": self.stu_unenrolled_id, "status": "PRESENT", "recognition_method": "MANUAL"},
            )
            self.assertEqual(res_manual_unenrolled.status_code, 403)
            self.assertIn("not enrolled", res_manual_unenrolled.get_json()["message"].lower())

            # 3. PATCH update: Section B student in Section A session -> 403
            res_patch = self.client.patch(
                f"/api/faculty/attendance/sessions/{self.sess_a_id}/records/{self.stu_b_id}",
                headers=admin_headers,
                json={"status": "PRESENT"},
            )
            self.assertEqual(res_patch.status_code, 403)

            # 4. Manual mark: Inactive user account -> 403
            res_inactive = self.client.post(
                f"/api/faculty/attendance/sessions/{self.sess_a_id}/records",
                headers=admin_headers,
                json={"student_id": self.stu_inactive_id, "status": "PRESENT", "recognition_method": "MANUAL"},
            )
            self.assertEqual(res_inactive.status_code, 403)
            self.assertIn("inactive", res_inactive.get_json()["message"].lower())

            # 5. Manual mark: Eligible student -> 201 Created
            res_eligible = self.client.post(
                f"/api/faculty/attendance/sessions/{self.sess_a_id}/records",
                headers=admin_headers,
                json={"student_id": self.stu_elig_id, "status": "PRESENT", "recognition_method": "MANUAL"},
            )
            self.assertEqual(res_eligible.status_code, 201)
            self.assertEqual(res_eligible.get_json()["data"]["status"], "PRESENT")

    # -------------------------------------------------------------
    # 15. Existing valid attendance, face recognition, and authorization workflows continue to pass
    # -------------------------------------------------------------
    @patch("app.routes.recognition.face_service.recognize_all_students")
    def test_15_existing_valid_attendance_lifecycle_passes(self, mock_rec):
        active_time = datetime(2026, 10, 21, 9, 45, 0, tzinfo=self.tz)
        mock_rec.return_value = {
            "matches": [
                {
                    "student_id": self.stu_elig_id,
                    "similarity_score": 0.82,
                }
            ],
            "status": "recognized",
            "detected_count": 1,
        }

        with patch("app.utils.schedule.get_current_institution_time", return_value=active_time):
            # Step A: View active session
            res_active = self.client.get(
                "/api/faculty/attendance/sessions/active",
                headers=self._headers(self.fac_a_uid),
            )
            self.assertEqual(res_active.status_code, 200)
            self.assertIsNotNone(res_active.get_json()["data"])
            self.assertEqual(res_active.get_json()["data"]["session_id"], self.sess_a_id)

            # Step B: Mark attendance via Face Recognition API
            res_rec = self.client.post(
                "/api/faculty/recognition/attendance",
                headers=self._headers(self.fac_a_uid),
                data={
                    "session_id": str(self.sess_a_id),
                    "image": self._dummy_image(),
                },
                content_type="multipart/form-data",
            )
            self.assertEqual(res_rec.status_code, 200)
            self.assertTrue(res_rec.get_json()["success"])
            self.assertEqual(res_rec.get_json()["data"]["student_id"], self.stu_elig_id)
            self.assertEqual(res_rec.get_json()["data"]["status"], "PRESENT")

            # Step C: Get session records
            res_records = self.client.get(
                f"/api/faculty/attendance/sessions/{self.sess_a_id}/records",
                headers=self._headers(self.fac_a_uid),
            )
            self.assertEqual(res_records.status_code, 200)
            records = res_records.get_json()["data"]
            self.assertEqual(len(records), 1)
            self.assertEqual(records[0]["student_id"], self.stu_elig_id)
            self.assertEqual(records[0]["status"], "PRESENT")

            # Step D: Close session
            res_close = self.client.post(
                f"/api/faculty/attendance/sessions/{self.sess_a_id}/close",
                headers=self._headers(self.fac_a_uid),
            )
            self.assertEqual(res_close.status_code, 200)
            self.assertEqual(res_close.get_json()["data"]["status"], "CLOSED")


if __name__ == "__main__":
    unittest.main()
