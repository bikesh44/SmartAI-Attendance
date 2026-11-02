import unittest
from datetime import date, datetime, time, timedelta, timezone
from unittest.mock import patch
from zoneinfo import ZoneInfo

from flask import Flask
from flask_jwt_extended import JWTManager, create_access_token
from sqlalchemy.pool import StaticPool

from app.extensions import bcrypt, db
from app.models import (
    AttendanceRecord,
    AttendanceSession,
    Course,
    CourseOffering,
    Department,
    Enrollment,
    Faculty,
    Student,
    TimetableEntry,
    User,
)
from app.routes.attendance import attendance_bp
from app.routes.recognition import recognition_bp
from app.routes.timetable import timetable_bp
from app.utils.schedule import (
    evaluate_timetable_window,
    get_current_institution_time,
    get_institution_timezone,
    get_session_schedule_status,
    get_timetable_window,
)


class TestTimetableSessionWindow(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = Flask(__name__)
        cls.app.config.update(
            TESTING=True,
            SECRET_KEY="test-secret-schedule-window",
            JWT_SECRET_KEY="test-jwt-secret-key-schedule-window-32b",
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
            db.session.remove()
            db.drop_all()
            db.create_all()

            # Department
            dept = Department(
                department_name="Computer Science",
                department_code="CSE",
            )
            db.session.add(dept)
            db.session.flush()

            # Users
            user_fac_a = User(
                name="Dr. Alice Smith",
                email="alice@college.edu",
                password_hash="pw",
                role="FACULTY",
            )
            user_fac_b = User(
                name="Dr. Bob Jones",
                email="bob@college.edu",
                password_hash="pw",
                role="FACULTY",
            )
            user_stu_1 = User(
                name="John Doe",
                email="john@college.edu",
                password_hash="pw",
                role="STUDENT",
            )
            user_stu_2 = User(
                name="Jane Doe",
                email="jane@college.edu",
                password_hash="pw",
                role="STUDENT",
            )
            user_admin = User(
                name="Admin Manager",
                email="admin@college.edu",
                password_hash="pw",
                role="ADMIN",
            )
            db.session.add_all([user_fac_a, user_fac_b, user_stu_1, user_stu_2, user_admin])
            db.session.flush()

            fac_a = Faculty(
                user_id=user_fac_a.user_id,
                department_id=dept.department_id,
                employee_id="FAC-001",
                designation="Professor",
            )
            fac_b = Faculty(
                user_id=user_fac_b.user_id,
                department_id=dept.department_id,
                employee_id="FAC-002",
                designation="Associate Professor",
            )
            stu_1 = Student(
                user_id=user_stu_1.user_id,
                department_id=dept.department_id,
                enrollment_no="ENR-001",
                semester=5,
                section="A",
                academic_year="2026-2027",
            )
            stu_2 = Student(
                user_id=user_stu_2.user_id,
                department_id=dept.department_id,
                enrollment_no="ENR-002",
                semester=5,
                section="A",
                academic_year="2026-2027",
            )
            db.session.add_all([fac_a, fac_b, stu_1, stu_2])
            db.session.flush()

            course = Course(
                course_code="CS501",
                course_name="Database Systems",
                department_id=dept.department_id,
                semester=5,
                credits=4,
            )
            db.session.add(course)
            db.session.flush()

            # Offering A: Owned by Faculty A
            offering_a = CourseOffering(
                course_id=course.course_id,
                faculty_id=fac_a.faculty_id,
                semester=5,
                section="A",
                academic_year="2026-2027",
                room="Room 301",
            )
            # Offering B: Owned by Faculty B
            offering_b = CourseOffering(
                course_id=course.course_id,
                faculty_id=fac_b.faculty_id,
                semester=5,
                section="B",
                academic_year="2026-2027",
                room="Room 302",
            )
            db.session.add_all([offering_a, offering_b])
            db.session.flush()

            # Wednesday 09:30 to 10:30 class for Offering A
            tt_entry = TimetableEntry(
                offering_id=offering_a.offering_id,
                day_of_week="Wednesday",
                start_time=time(9, 30),
                end_time=time(10, 30),
                room="Room 301",
            )
            db.session.add(tt_entry)

            # Enroll students in offering A
            enr_1 = Enrollment(
                student_id=stu_1.student_id,
                offering_id=offering_a.offering_id,
                status="ACTIVE",
            )
            enr_2 = Enrollment(
                student_id=stu_2.student_id,
                offering_id=offering_a.offering_id,
                status="ACTIVE",
            )
            db.session.add_all([enr_1, enr_2])
            db.session.commit()

            # Store IDs for tests
            self.fac_a_user_id = user_fac_a.user_id
            self.fac_b_user_id = user_fac_b.user_id
            self.admin_user_id = user_admin.user_id
            self.fac_a_id = fac_a.faculty_id
            self.fac_b_id = fac_b.faculty_id
            self.stu_1_id = stu_1.student_id
            self.stu_2_id = stu_2.student_id
            self.offering_a_id = offering_a.offering_id
            self.offering_b_id = offering_b.offering_id
            self.tt_entry_id = tt_entry.timetable_entry_id

            # Wednesday test date: 2026-10-21 is a Wednesday
            self.test_date = date(2026, 10, 21)
            self.tz = ZoneInfo("Asia/Kolkata")

    def tearDown(self):
        with self.app.app_context():
            self.app.config["INSTITUTION_TIMEZONE"] = "Asia/Kolkata"
            db.session.rollback()
            db.session.remove()

    def _headers(self, user_id, role="FACULTY"):
        with self.app.app_context():
            token = create_access_token(
                identity=str(user_id),
                additional_claims={"role": role},
            )
        return {"Authorization": f"Bearer {token}"}

    # =========================================================================
    # Test 1: A future class cannot start an attendance session.
    # =========================================================================
    def test_01_future_class_cannot_start_attendance_session(self):
        # 8:54 AM IST on Wednesday 2026-10-21 (class scheduled 09:30 - 10:30)
        frozen_time = datetime(2026, 10, 21, 8, 54, 0, tzinfo=self.tz)

        with patch("app.utils.schedule.get_current_institution_time", return_value=frozen_time):
            headers = self._headers(self.fac_a_user_id)
            res = self.client.post(
                "/api/faculty/attendance/sessions",
                json={"offering_id": self.offering_a_id},
                headers=headers,
            )

            self.assertEqual(res.status_code, 400)
            data = res.get_json()
            self.assertFalse(data["success"])
            self.assertIn("before the scheduled start time", data["message"])
            self.assertIn("09:30", data["message"])

            # Verify no session was created in DB
            with self.app.app_context():
                sessions_count = AttendanceSession.query.filter_by(
                    offering_id=self.offering_a_id,
                    session_date=self.test_date,
                ).count()
                self.assertEqual(sessions_count, 0)

    # =========================================================================
    # Test 2: A future class cannot record attendance through the API.
    # =========================================================================
    def test_02_future_class_cannot_record_attendance_through_api(self):
        # Create session in DB for 09:30 - 10:30
        with self.app.app_context():
            future_session = AttendanceSession(
                offering_id=self.offering_a_id,
                faculty_id=self.fac_a_id,
                session_date=self.test_date,
                start_time=time(9, 30),
                end_time=time(10, 30),
                status="ACTIVE",
            )
            db.session.add(future_session)
            db.session.commit()
            session_id = future_session.session_id

        # At 8:54 AM, attempt to record attendance via records API
        frozen_time = datetime(2026, 10, 21, 8, 54, 0, tzinfo=self.tz)
        with patch("app.utils.schedule.get_current_institution_time", return_value=frozen_time):
            admin_headers = self._headers(self.admin_user_id, role="ADMIN")
            res = self.client.post(
                f"/api/faculty/attendance/sessions/{session_id}/records",
                json={
                    "student_id": self.stu_1_id,
                    "status": "PRESENT",
                    "recognition_method": "MANUAL",
                },
                headers=admin_headers,
            )

            self.assertEqual(res.status_code, 400)
            data = res.get_json()
            self.assertFalse(data["success"])
            self.assertIn("before the scheduled start time", data["message"].lower())

            # Verify attendance record was NOT created
            with self.app.app_context():
                rec = AttendanceRecord.query.filter_by(session_id=session_id).first()
                self.assertIsNone(rec)

    # =========================================================================
    # Test 3: Attendance is permitted at the exact scheduled start time.
    # =========================================================================
    def test_03_attendance_permitted_at_exact_scheduled_start_time(self):
        # Exactly 09:30:00 AM IST (inclusive start boundary)
        frozen_time = datetime(2026, 10, 21, 9, 30, 0, tzinfo=self.tz)

        with patch("app.utils.schedule.get_current_institution_time", return_value=frozen_time):
            headers = self._headers(self.fac_a_user_id)
            res = self.client.post(
                "/api/faculty/attendance/sessions",
                json={"offering_id": self.offering_a_id},
                headers=headers,
            )

            self.assertEqual(res.status_code, 201)
            data = res.get_json()
            self.assertTrue(data["success"])
            self.assertEqual(data["data"]["status"], "ACTIVE")
            self.assertEqual(data["data"]["start_time"], "09:30:00")
            session_id = data["data"]["session_id"]

            # Attendance recording at exact start time succeeds
            admin_headers = self._headers(self.admin_user_id, role="ADMIN")
            rec_res = self.client.post(
                f"/api/faculty/attendance/sessions/{session_id}/records",
                json={
                    "student_id": self.stu_1_id,
                    "status": "PRESENT",
                    "recognition_method": "MANUAL",
                },
                headers=admin_headers,
            )
            self.assertEqual(rec_res.status_code, 201)
            self.assertEqual(rec_res.get_json()["data"]["status"], "PRESENT")

    # =========================================================================
    # Test 4: Attendance is permitted during the scheduled window.
    # =========================================================================
    def test_04_attendance_permitted_during_scheduled_window(self):
        # Create session started at 09:30
        with self.app.app_context():
            session = AttendanceSession(
                offering_id=self.offering_a_id,
                faculty_id=self.fac_a_id,
                session_date=self.test_date,
                start_time=time(9, 30),
                end_time=time(10, 30),
                status="ACTIVE",
            )
            db.session.add(session)
            db.session.commit()
            session_id = session.session_id

        # At 10:00 AM IST (inside window 09:30 <= 10:00 < 10:30)
        frozen_time = datetime(2026, 10, 21, 10, 0, 0, tzinfo=self.tz)
        with patch("app.utils.schedule.get_current_institution_time", return_value=frozen_time):
            headers = self._headers(self.fac_a_user_id)
            active_res = self.client.get(
                "/api/faculty/attendance/sessions/active",
                headers=headers,
            )
            self.assertEqual(active_res.status_code, 200)
            active_data = active_res.get_json()["data"]
            self.assertIsNotNone(active_data)
            self.assertEqual(active_data["session_id"], session_id)
            self.assertTrue(active_data["is_eligible_for_attendance"])
            self.assertEqual(active_data["schedule_status"], "ACTIVE")

            # Mark student attendance
            admin_headers = self._headers(self.admin_user_id, role="ADMIN")
            rec_res = self.client.post(
                f"/api/faculty/attendance/sessions/{session_id}/records",
                json={"student_id": self.stu_1_id, "status": "PRESENT"},
                headers=admin_headers,
            )
            self.assertEqual(rec_res.status_code, 201)

    # =========================================================================
    # Test 5: Attendance is rejected at the exact scheduled end time.
    # =========================================================================
    def test_05_attendance_rejected_at_exact_scheduled_end_time(self):
        # Create session started at 09:30
        with self.app.app_context():
            session = AttendanceSession(
                offering_id=self.offering_a_id,
                faculty_id=self.fac_a_id,
                session_date=self.test_date,
                start_time=time(9, 30),
                end_time=time(10, 30),
                status="ACTIVE",
            )
            db.session.add(session)
            db.session.commit()
            session_id = session.session_id

        # At exactly 10:30:00 AM IST (exclusive end boundary: current_time < end_time fails)
        frozen_time = datetime(2026, 10, 21, 10, 30, 0, tzinfo=self.tz)
        with patch("app.utils.schedule.get_current_institution_time", return_value=frozen_time):
            # 1. Starting a session at/after 10:30 is rejected
            headers = self._headers(self.fac_a_user_id)
            start_res = self.client.post(
                "/api/faculty/attendance/sessions",
                json={"offering_id": self.offering_a_id},
                headers=headers,
            )
            self.assertEqual(start_res.status_code, 400)
            self.assertIn("window has ended", start_res.get_json()["message"].lower())

            # 2. Querying active session triggers session-closing workflow
            active_res = self.client.get(
                "/api/faculty/attendance/sessions/active",
                headers=headers,
            )
            self.assertEqual(active_res.status_code, 200)
            self.assertIsNone(active_res.get_json()["data"])

            # 3. Session is now CLOSED and unrecorded enrolled students marked ABSENT
            with self.app.app_context():
                closed_session = db.session.get(AttendanceSession, session_id)
                self.assertEqual(closed_session.status, "CLOSED")

                absent_records = AttendanceRecord.query.filter_by(
                    session_id=session_id,
                    status="ABSENT",
                ).all()
                # Both stu_1 and stu_2 should be auto-marked ABSENT
                absent_student_ids = {r.student_id for r in absent_records}
                self.assertIn(self.stu_1_id, absent_student_ids)
                self.assertIn(self.stu_2_id, absent_student_ids)

    # =========================================================================
    # Test 6: An active database session flag does not bypass schedule validation.
    # =========================================================================
    def test_06_active_db_session_flag_does_not_bypass_schedule_validation(self):
        # Database row explicitly has status='ACTIVE', but class window is 09:30 - 10:30
        with self.app.app_context():
            session = AttendanceSession(
                offering_id=self.offering_a_id,
                faculty_id=self.fac_a_id,
                session_date=self.test_date,
                start_time=time(9, 30),
                end_time=time(10, 30),
                status="ACTIVE",
            )
            db.session.add(session)
            db.session.commit()
            session_id = session.session_id

        # At 8:54 AM IST:
        frozen_time = datetime(2026, 10, 21, 8, 54, 0, tzinfo=self.tz)
        with patch("app.utils.schedule.get_current_institution_time", return_value=frozen_time):
            headers = self._headers(self.fac_a_user_id)

            # Active session endpoint MUST NOT return it as active
            res = self.client.get(
                "/api/faculty/attendance/sessions/active",
                headers=headers,
            )
            self.assertEqual(res.status_code, 200)
            self.assertIsNone(res.get_json()["data"])

            # DB flag was safely reconciled to SCHEDULED
            with self.app.app_context():
                reconciled = db.session.get(AttendanceSession, session_id)
                self.assertEqual(reconciled.status, "SCHEDULED")

    # =========================================================================
    # Test 7: The faculty dashboard does not present a future class as active.
    # =========================================================================
    def test_07_faculty_dashboard_does_not_present_future_class_as_active(self):
        # At 8:54 AM IST for a 09:30 class
        frozen_time = datetime(2026, 10, 21, 8, 54, 0, tzinfo=self.tz)
        with patch("app.utils.schedule.get_current_institution_time", return_value=frozen_time):
            headers = self._headers(self.fac_a_user_id)

            # 1. No active session returned by backend
            active_res = self.client.get(
                "/api/faculty/attendance/sessions/active",
                headers=headers,
            )
            self.assertEqual(active_res.status_code, 200)
            self.assertIsNone(active_res.get_json()["data"])

            # 2. Timetable returns Wednesday class with start time 09:30
            tt_res = self.client.get(
                "/api/timetable/faculty",
                headers=headers,
            )
            self.assertEqual(tt_res.status_code, 200)
            entries = tt_res.get_json()["data"]
            wed_entries = [e for e in entries if e["day_of_week"] == "Wednesday"]
            self.assertEqual(len(wed_entries), 1)
            self.assertEqual(wed_entries[0]["start_time"], "09:30")
            self.assertEqual(wed_entries[0]["end_time"], "10:30")

    # =========================================================================
    # Test 8: A timezone mismatch cannot make a future class appear active.
    # =========================================================================
    def test_08_timezone_mismatch_cannot_make_future_class_appear_active(self):
        # In UTC, 08:54 AM IST is 03:24 AM UTC on the same day.
        # Timetable value is 09:30:00 (which is in institution timezone).
        # Test evaluate_timetable_window with UTC input and ensure it evaluates properly in IST.
        with self.app.app_context():
            utc_dt = datetime(2026, 10, 21, 3, 24, 0, tzinfo=timezone.utc)
            is_active, status_str, start_dt, end_dt = evaluate_timetable_window(
                self.test_date, time(9, 30), time(10, 30), current_dt=utc_dt
            )
            self.assertFalse(is_active)
            self.assertEqual(status_str, "UPCOMING")

            # Now test with custom configured institution timezone: America/New_York
            self.app.config["INSTITUTION_TIMEZONE"] = "America/New_York"
            try:
                ny_tz = ZoneInfo("America/New_York")
                # 8:54 AM in New York for 9:30 AM class
                ny_time = datetime(2026, 10, 21, 8, 54, 0, tzinfo=ny_tz)
                with patch("app.utils.schedule.get_current_institution_time", return_value=ny_time):
                    is_active_ny, status_str_ny, _, _ = evaluate_timetable_window(
                        self.test_date, time(9, 30), time(10, 30), current_dt=ny_time
                    )
                    self.assertFalse(is_active_ny)
                    self.assertEqual(status_str_ny, "UPCOMING")
            finally:
                self.app.config["INSTITUTION_TIMEZONE"] = "Asia/Kolkata"

    # =========================================================================
    # Test 9: Unauthorized faculty cannot take attendance for another faculty member's class.
    # =========================================================================
    def test_09_unauthorized_faculty_cannot_take_attendance(self):
        # During scheduled class window (10:00 AM)
        frozen_time = datetime(2026, 10, 21, 10, 0, 0, tzinfo=self.tz)
        with patch("app.utils.schedule.get_current_institution_time", return_value=frozen_time):
            headers_b = self._headers(self.fac_b_user_id)

            # Faculty B attempts to start session for Faculty A's offering
            res = self.client.post(
                "/api/faculty/attendance/sessions",
                json={"offering_id": self.offering_a_id},
                headers=headers_b,
            )
            self.assertEqual(res.status_code, 403)
            self.assertIn("not authorized", res.get_json()["message"].lower())

    # =========================================================================
    # Test 10: Existing valid attendance workflows continue to pass.
    # =========================================================================
    def test_10_existing_valid_attendance_workflows_continue_to_pass(self):
        # Complete valid attendance flow:
        # Step 1: Start session during scheduled window (09:40 AM)
        time_start = datetime(2026, 10, 21, 9, 40, 0, tzinfo=self.tz)
        with patch("app.utils.schedule.get_current_institution_time", return_value=time_start):
            headers_a = self._headers(self.fac_a_user_id)
            res = self.client.post(
                "/api/faculty/attendance/sessions",
                json={"offering_id": self.offering_a_id},
                headers=headers_a,
            )
            self.assertEqual(res.status_code, 201)
            session_id = res.get_json()["data"]["session_id"]

        # Step 2: Query active session -> confirmed active
        time_mid = datetime(2026, 10, 21, 9, 50, 0, tzinfo=self.tz)
        with patch("app.utils.schedule.get_current_institution_time", return_value=time_mid):
            active_res = self.client.get(
                "/api/faculty/attendance/sessions/active",
                headers=headers_a,
            )
            self.assertEqual(active_res.status_code, 200)
            self.assertEqual(active_res.get_json()["data"]["session_id"], session_id)

            # Step 3: Admin records Student 1 as PRESENT
            admin_headers = self._headers(self.admin_user_id, role="ADMIN")
            mark_res = self.client.post(
                f"/api/faculty/attendance/sessions/{session_id}/records",
                json={"student_id": self.stu_1_id, "status": "PRESENT"},
                headers=admin_headers,
            )
            self.assertEqual(mark_res.status_code, 201)
            self.assertEqual(mark_res.get_json()["data"]["status"], "PRESENT")

            # Step 4: Faculty retrieves session records
            records_res = self.client.get(
                f"/api/faculty/attendance/sessions/{session_id}/records",
                headers=headers_a,
            )
            self.assertEqual(records_res.status_code, 200)
            self.assertEqual(len(records_res.get_json()["data"]), 1)

            # Step 5: Faculty manually closes session
            close_res = self.client.post(
                f"/api/faculty/attendance/sessions/{session_id}/close",
                headers=headers_a,
            )
            self.assertEqual(close_res.status_code, 200)
            self.assertEqual(close_res.get_json()["data"]["status"], "CLOSED")

            # Unrecorded student 2 was auto-marked ABSENT
            with self.app.app_context():
                absent_rec = AttendanceRecord.query.filter_by(
                    session_id=session_id,
                    student_id=self.stu_2_id,
                ).first()
                self.assertIsNotNone(absent_rec)
                self.assertEqual(absent_rec.status, "ABSENT")
                self.assertEqual(absent_rec.recognition_method, "SYSTEM")

                # Student 1 remains PRESENT
                present_rec = AttendanceRecord.query.filter_by(
                    session_id=session_id,
                    student_id=self.stu_1_id,
                ).first()
                self.assertEqual(present_rec.status, "PRESENT")


if __name__ == "__main__":
    unittest.main()
