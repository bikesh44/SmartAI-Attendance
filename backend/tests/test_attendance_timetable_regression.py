import unittest
from datetime import date, datetime, time
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
from app.services.cv.attendance_service import mark_face_attendance
from app.utils.schedule import (
    evaluate_timetable_window,
    get_offering_authoritative_entry,
    get_session_schedule_status,
)


class TestAttendanceTimetableRegression(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = Flask(__name__)
        cls.app.config.update(
            TESTING=True,
            SECRET_KEY="test-secret-regression-key",
            JWT_SECRET_KEY="test-jwt-secret-regression-key-32b",
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
                department_name="Computer Science & Engineering",
                department_code="CSE",
            )
            db.session.add(dept)
            db.session.flush()

            # Users
            user_fac_a = User(
                name="Dr. Alice Smith",
                email="alice.smith@college.edu",
                password_hash="hashed_pw",
                role="FACULTY",
            )
            user_fac_b = User(
                name="Dr. Bob Jones",
                email="bob.jones@college.edu",
                password_hash="hashed_pw",
                role="FACULTY",
            )
            user_stu_a1 = User(
                name="Aarav Sharma",
                email="aarav.a@college.edu",
                password_hash="hashed_pw",
                role="STUDENT",
            )
            user_stu_b1 = User(
                name="Bhavya Patel",
                email="bhavya.b@college.edu",
                password_hash="hashed_pw",
                role="STUDENT",
            )
            user_admin = User(
                name="System Administrator",
                email="admin@college.edu",
                password_hash="hashed_pw",
                role="ADMIN",
            )
            db.session.add_all([user_fac_a, user_fac_b, user_stu_a1, user_stu_b1, user_admin])
            db.session.flush()

            # Faculty profiles
            fac_a = Faculty(
                user_id=user_fac_a.user_id,
                department_id=dept.department_id,
                employee_id="FAC-CSE-001",
                designation="Associate Professor",
            )
            fac_b = Faculty(
                user_id=user_fac_b.user_id,
                department_id=dept.department_id,
                employee_id="FAC-CSE-002",
                designation="Assistant Professor",
            )

            # Student profiles: Aarav in Section A, Bhavya in Section B
            stu_a1 = Student(
                user_id=user_stu_a1.user_id,
                department_id=dept.department_id,
                enrollment_no="ENR-2026-CSE-5A-01",
                semester=5,
                section="A",
                academic_year="2026-2027",
            )
            stu_b1 = Student(
                user_id=user_stu_b1.user_id,
                department_id=dept.department_id,
                enrollment_no="ENR-2026-CSE-5B-01",
                semester=5,
                section="B",
                academic_year="2026-2027",
            )
            db.session.add_all([fac_a, fac_b, stu_a1, stu_b1])
            db.session.flush()

            # Course BCSE-811: R Programming
            course = Course(
                course_code="BCSE-811",
                course_name="R Programming",
                department_id=dept.department_id,
                semester=5,
                credits=4,
            )
            db.session.add(course)
            db.session.flush()

            # Course Offering A: BCSE-811, Section A, Faculty A, Room CSE-5A-05
            offering_a = CourseOffering(
                course_id=course.course_id,
                faculty_id=fac_a.faculty_id,
                semester=5,
                section="A",
                academic_year="2026-2027",
                room="CSE-5A-05",
            )
            # Course Offering B: BCSE-811, Section B, Faculty A, Room CSE-5B-06
            offering_b = CourseOffering(
                course_id=course.course_id,
                faculty_id=fac_a.faculty_id,
                semester=5,
                section="B",
                academic_year="2026-2027",
                room="CSE-5B-06",
            )
            db.session.add_all([offering_a, offering_b])
            db.session.flush()

            # Timetable entries for Wednesday (2026-10-21):
            # 1. 08:40 - 09:40: Section A, Room CSE-5A-05
            entry_a1 = TimetableEntry(
                offering_id=offering_a.offering_id,
                day_of_week="Wednesday",
                start_time=time(8, 40),
                end_time=time(9, 40),
                room="CSE-5A-05",
            )
            # 2. 09:40 - 10:40: Section A, Room CSE-5A-05
            entry_a2 = TimetableEntry(
                offering_id=offering_a.offering_id,
                day_of_week="Wednesday",
                start_time=time(9, 40),
                end_time=time(10, 40),
                room="CSE-5A-05",
            )
            # 3. 14:40 - 15:40: Section B, Room CSE-5B-06
            entry_b1 = TimetableEntry(
                offering_id=offering_b.offering_id,
                day_of_week="Wednesday",
                start_time=time(14, 40),
                end_time=time(15, 40),
                room="CSE-5B-06",
            )
            db.session.add_all([entry_a1, entry_a2, entry_b1])

            # Enrollments: Aarav -> Offering A (Section A), Bhavya -> Offering B (Section B)
            enr_a1 = Enrollment(
                student_id=stu_a1.student_id,
                offering_id=offering_a.offering_id,
                status="ACTIVE",
            )
            enr_b1 = Enrollment(
                student_id=stu_b1.student_id,
                offering_id=offering_b.offering_id,
                status="ACTIVE",
            )
            db.session.add_all([enr_a1, enr_b1])
            db.session.commit()

            # Store scalar IDs for test isolation
            self.fac_a_user_id = user_fac_a.user_id
            self.fac_b_user_id = user_fac_b.user_id
            self.admin_user_id = user_admin.user_id
            self.fac_a_id = fac_a.faculty_id
            self.fac_b_id = fac_b.faculty_id
            self.stu_a1_id = stu_a1.student_id
            self.stu_b1_id = stu_b1.student_id
            self.offering_a_id = offering_a.offering_id
            self.offering_b_id = offering_b.offering_id
            self.entry_a1_id = entry_a1.timetable_entry_id
            self.entry_a2_id = entry_a2.timetable_entry_id
            self.entry_b1_id = entry_b1.timetable_entry_id

            self.test_date = date(2026, 10, 21)
            self.tz = ZoneInfo("Asia/Kolkata")

    def tearDown(self):
        with self.app.app_context():
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
    # Test 1: Multiple timetable entries for the same course code resolve to
    # the correct individual entry.
    # =========================================================================
    def test_01_multiple_timetable_entries_same_course_code_resolve_correctly(self):
        # Current time: 09:45 AM (Wednesday) -> within 09:40-10:40 window (entry_a2)
        frozen_time = datetime(2026, 10, 21, 9, 45, 0, tzinfo=self.tz)
        with patch("app.utils.schedule.get_current_institution_time", return_value=frozen_time):
            headers = self._headers(self.fac_a_user_id)

            # Start session for Section A with exact timetable_entry_id
            res = self.client.post(
                "/api/faculty/attendance/sessions",
                json={
                    "offering_id": self.offering_a_id,
                    "timetable_entry_id": self.entry_a2_id,
                },
                headers=headers,
            )
            self.assertEqual(res.status_code, 201)
            data = res.get_json()["data"]
            self.assertEqual(data["timetable_entry_id"], self.entry_a2_id)
            self.assertEqual(data["start_time"], "09:40:00")
            self.assertEqual(data["end_time"], "10:40:00")
            self.assertEqual(data["section"], "A")
            self.assertEqual(data["room"], "CSE-5A-05")

    # =========================================================================
    # Test 2: Section A's session is never displayed as Section B's session.
    # =========================================================================
    def test_02_section_a_session_never_displayed_as_section_b_session(self):
        frozen_time = datetime(2026, 10, 21, 9, 45, 0, tzinfo=self.tz)
        with patch("app.utils.schedule.get_current_institution_time", return_value=frozen_time):
            headers = self._headers(self.fac_a_user_id)

            # Create Section A session
            res_create = self.client.post(
                "/api/faculty/attendance/sessions",
                json={"offering_id": self.offering_a_id, "timetable_entry_id": self.entry_a2_id},
                headers=headers,
            )
            self.assertEqual(res_create.status_code, 201)

            # Query active session
            res_active = self.client.get("/api/faculty/attendance/sessions/active", headers=headers)
            self.assertEqual(res_active.status_code, 200)
            active_data = res_active.get_json()["data"]

            self.assertIsNotNone(active_data)
            self.assertEqual(active_data["offering_id"], self.offering_a_id)
            self.assertEqual(active_data["section"], "A")
            self.assertEqual(active_data["room"], "CSE-5A-05")
            self.assertNotEqual(active_data["section"], "B")
            self.assertNotEqual(active_data["offering_id"], self.offering_b_id)

    # =========================================================================
    # Test 3: The active-session panel and start-session validation refer to
    # the same timetable entry.
    # =========================================================================
    def test_03_active_session_and_start_session_validation_refer_to_same_entry(self):
        frozen_time = datetime(2026, 10, 21, 9, 45, 0, tzinfo=self.tz)
        with patch("app.utils.schedule.get_current_institution_time", return_value=frozen_time):
            headers = self._headers(self.fac_a_user_id)

            res_create = self.client.post(
                "/api/faculty/attendance/sessions",
                json={"offering_id": self.offering_a_id, "timetable_entry_id": self.entry_a2_id},
                headers=headers,
            )
            created_session = res_create.get_json()["data"]

            res_active = self.client.get("/api/faculty/attendance/sessions/active", headers=headers)
            active_session = res_active.get_json()["data"]

            self.assertEqual(created_session["timetable_entry_id"], active_session["timetable_entry_id"])
            self.assertEqual(created_session["start_time"], active_session["start_time"])
            self.assertEqual(created_session["end_time"], active_session["end_time"])
            self.assertEqual(created_session["session_id"], active_session["session_id"])

    # =========================================================================
    # Test 4: The course selector does not silently select an expired timetable
    # slot when another slot exists.
    # =========================================================================
    def test_04_course_selector_does_not_silently_select_expired_slot(self):
        # At 09:45 AM, slot 08:40-09:40 has ended, but slot 09:40-10:40 is active.
        frozen_time = datetime(2026, 10, 21, 9, 45, 0, tzinfo=self.tz)
        with patch("app.utils.schedule.get_current_institution_time", return_value=frozen_time):
            headers = self._headers(self.fac_a_user_id)

            # Starting session for Offering A without passing timetable_entry_id
            # must automatically resolve to the active slot (09:40-10:40), NOT the ended slot (08:40-09:40)
            res = self.client.post(
                "/api/faculty/attendance/sessions",
                json={"offering_id": self.offering_a_id},
                headers=headers,
            )
            self.assertEqual(res.status_code, 201)
            data = res.get_json()["data"]
            self.assertEqual(data["timetable_entry_id"], self.entry_a2_id)
            self.assertEqual(data["start_time"], "09:40:00")
            self.assertEqual(data["end_time"], "10:40:00")

    # =========================================================================
    # Test 5: A future class is shown as upcoming, not as a currently attendable session.
    # =========================================================================
    def test_05_future_class_shown_as_upcoming_not_currently_attendable(self):
        # At 09:45 AM, Section B class (14:40 - 15:40) is in the future.
        frozen_time = datetime(2026, 10, 21, 9, 45, 0, tzinfo=self.tz)
        with patch("app.utils.schedule.get_current_institution_time", return_value=frozen_time):
            headers = self._headers(self.fac_a_user_id)

            # Attempting to start future class session fails
            res = self.client.post(
                "/api/faculty/attendance/sessions",
                json={"offering_id": self.offering_b_id, "timetable_entry_id": self.entry_b1_id},
                headers=headers,
            )
            self.assertEqual(res.status_code, 400)
            data = res.get_json()
            self.assertFalse(data["success"])
            self.assertIn("before the scheduled start time", data["message"].lower())
            self.assertIn("02:40 pm", data["message"].lower())

            # Schedule helper evaluates status as UPCOMING
            is_active, status_str, _, _ = evaluate_timetable_window(
                self.test_date, time(14, 40), time(15, 40), current_dt=frozen_time
            )
            self.assertFalse(is_active)
            self.assertEqual(status_str, "UPCOMING")

    # =========================================================================
    # Test 6: An expired session cannot record new attendance.
    # =========================================================================
    def test_06_expired_session_cannot_record_new_attendance(self):
        # Create an expired session in DB (ended at 09:40)
        with self.app.app_context():
            expired_session = AttendanceSession(
                offering_id=self.offering_a_id,
                faculty_id=self.fac_a_id,
                session_date=self.test_date,
                start_time=time(8, 40),
                end_time=time(9, 40),
                status="ACTIVE",
            )
            db.session.add(expired_session)
            db.session.commit()
            expired_id = expired_session.session_id

        # At 09:45 AM (after 09:40 end), attempt to mark attendance
        frozen_time = datetime(2026, 10, 21, 9, 45, 0, tzinfo=self.tz)
        with patch("app.utils.schedule.get_current_institution_time", return_value=frozen_time):
            with self.app.app_context():
                rec, msg = mark_face_attendance(
                    session_id=expired_id,
                    student_id=self.stu_a1_id,
                    confidence_score=0.92,
                    faculty_id=self.fac_a_id,
                )
                self.assertIsNone(rec)
                self.assertIn("ended", msg.lower())

                # Verify session was closed
                sess = db.session.get(AttendanceSession, expired_id)
                self.assertEqual(sess.status, "CLOSED")

    # =========================================================================
    # Test 7: An eligible student can attend only the specific authorized section and offering.
    # =========================================================================
    def test_07_eligible_student_can_attend_only_specific_authorized_section(self):
        frozen_time = datetime(2026, 10, 21, 9, 45, 0, tzinfo=self.tz)
        with patch("app.utils.schedule.get_current_institution_time", return_value=frozen_time):
            # Create active session for Section A
            with self.app.app_context():
                active_session = AttendanceSession(
                    offering_id=self.offering_a_id,
                    faculty_id=self.fac_a_id,
                    session_date=self.test_date,
                    start_time=time(9, 40),
                    end_time=time(10, 40),
                    status="ACTIVE",
                )
                db.session.add(active_session)
                db.session.commit()
                session_id = active_session.session_id

            # Student B1 (Section B) tries to attend Section A's session -> rejected
            with self.app.app_context():
                rec, msg = mark_face_attendance(
                    session_id=session_id,
                    student_id=self.stu_b1_id,
                    confidence_score=0.95,
                    faculty_id=self.fac_a_id,
                )
                self.assertIsNone(rec)
                self.assertIn("not enrolled", msg.lower())

            # Student A1 (Section A) attends Section A's session -> accepted
            with self.app.app_context():
                rec, msg = mark_face_attendance(
                    session_id=session_id,
                    student_id=self.stu_a1_id,
                    confidence_score=0.95,
                    faculty_id=self.fac_a_id,
                )
                self.assertIsNotNone(rec)
                self.assertEqual(rec.status, "PRESENT")
                self.assertEqual(rec.student_id, self.stu_a1_id)

    # =========================================================================
    # Test 8: Unauthorized faculty cannot start or access another faculty member's session.
    # =========================================================================
    def test_08_unauthorized_faculty_cannot_start_or_access_session(self):
        frozen_time = datetime(2026, 10, 21, 9, 45, 0, tzinfo=self.tz)
        with patch("app.utils.schedule.get_current_institution_time", return_value=frozen_time):
            headers_b = self._headers(self.fac_b_user_id)

            # Faculty B tries to start session for Faculty A's offering
            res = self.client.post(
                "/api/faculty/attendance/sessions",
                json={"offering_id": self.offering_a_id},
                headers=headers_b,
            )
            self.assertEqual(res.status_code, 403)
            self.assertIn("not authorized", res.get_json()["message"].lower())

    # =========================================================================
    # Test 9: The dashboard behaves correctly when there is no active session.
    # =========================================================================
    def test_09_dashboard_behaves_correctly_when_no_active_session(self):
        headers = self._headers(self.fac_a_user_id)

        # GET /api/faculty/attendance/sessions/active returns None
        res_active = self.client.get("/api/faculty/attendance/sessions/active", headers=headers)
        self.assertEqual(res_active.status_code, 200)
        json_data = res_active.get_json()
        self.assertTrue(json_data["success"])
        self.assertIsNone(json_data["data"])
        self.assertEqual(json_data["message"], "No active attendance session")

        # GET /api/timetable/faculty returns the 3 assigned timetable entries
        res_tt = self.client.get("/api/timetable/faculty", headers=headers)
        self.assertEqual(res_tt.status_code, 200)
        tt_items = res_tt.get_json()["data"]
        self.assertEqual(len(tt_items), 3)

        # Confirm all 3 slots match the user's observed classes
        slots = [(item["start_time"], item["end_time"], item["section"], item["room"]) for item in tt_items]
        self.assertIn(("08:40", "09:40", "A", "CSE-5A-05"), slots)
        self.assertIn(("09:40", "10:40", "A", "CSE-5A-05"), slots)
        self.assertIn(("14:40", "15:40", "B", "CSE-5B-06"), slots)

    # =========================================================================
    # Test 10: Existing valid attendance and timetable workflows continue to pass.
    # =========================================================================
    def test_10_existing_valid_attendance_lifecycle_passes(self):
        frozen_time = datetime(2026, 10, 21, 9, 45, 0, tzinfo=self.tz)
        with patch("app.utils.schedule.get_current_institution_time", return_value=frozen_time):
            headers = self._headers(self.fac_a_user_id)

            # 1. Start attendance session for active slot
            res_start = self.client.post(
                "/api/faculty/attendance/sessions",
                json={"offering_id": self.offering_a_id, "timetable_entry_id": self.entry_a2_id},
                headers=headers,
            )
            self.assertEqual(res_start.status_code, 201)
            session_id = res_start.get_json()["data"]["session_id"]

            # 2. Check active session endpoint
            res_active = self.client.get("/api/faculty/attendance/sessions/active", headers=headers)
            self.assertEqual(res_active.status_code, 200)
            self.assertEqual(res_active.get_json()["data"]["session_id"], session_id)

            # 3. Mark attendance via face recognition service
            with self.app.app_context():
                rec, msg = mark_face_attendance(
                    session_id=session_id,
                    student_id=self.stu_a1_id,
                    confidence_score=0.91,
                    faculty_id=self.fac_a_id,
                )
                self.assertIsNotNone(rec)
                self.assertEqual(rec.status, "PRESENT")

                # Duplicate attendance attempt
                rec_dup, msg_dup = mark_face_attendance(
                    session_id=session_id,
                    student_id=self.stu_a1_id,
                    confidence_score=0.91,
                    faculty_id=self.fac_a_id,
                )
                self.assertIn("already marked", msg_dup.lower())

            # 4. Close attendance session
            res_close = self.client.post(
                f"/api/faculty/attendance/sessions/{session_id}/close",
                headers=headers,
            )
            self.assertEqual(res_close.status_code, 200)
            self.assertEqual(res_close.get_json()["data"]["status"], "CLOSED")

            # 5. After close, active session is None
            res_active_after = self.client.get("/api/faculty/attendance/sessions/active", headers=headers)
            self.assertIsNone(res_active_after.get_json()["data"])
