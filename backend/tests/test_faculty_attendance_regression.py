import unittest
import uuid
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
from app.routes.faculty import faculty_bp
from app.routes.timetable import timetable_bp
from app.routes.analytics import analytics_bp


class TestFacultyAttendanceRegression(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = Flask(__name__)
        cls.app.config.update(
            TESTING=True,
            SECRET_KEY="test-secret-regression",
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
        bcrypt.init_app(cls.app)
        JWTManager(cls.app)
        cls.app.register_blueprint(attendance_bp)
        cls.app.register_blueprint(faculty_bp)
        cls.app.register_blueprint(timetable_bp)
        cls.app.register_blueprint(analytics_bp)

        cls.tz = ZoneInfo("Asia/Kolkata")
        cls.frozen_time = datetime(2026, 10, 21, 10, 0, 0, tzinfo=cls.tz)
        cls.clock_patcher = patch("app.utils.schedule.get_current_institution_time", return_value=cls.frozen_time)
        cls.clock_patcher.start()

        with cls.app.app_context():
            db.create_all()

    @classmethod
    def tearDownClass(cls):
        cls.clock_patcher.stop()
        with cls.app.app_context():
            db.session.remove()
            db.drop_all()

    def setUp(self):
        self.client = self.app.test_client()

        with self.app.app_context():
            db.session.remove()
            db.drop_all()
            db.create_all()

            # Create Department
            dept = Department(department_name="Computer Science Engineering", department_code="CSE")
            db.session.add(dept)
            db.session.flush()
            self.dept_id = dept.department_id

            # Create Dr. Sahil Sharma (Faculty)
            sahil_user = User(
                name="Dr. Sahil Sharma",
                email="sahil.sharma@test.local",
                password_hash="pw",
                role="FACULTY",
                is_active=True,
            )
            # Create another faculty
            other_user = User(
                name="Dr. Other Faculty",
                email="other.faculty@test.local",
                password_hash="pw",
                role="FACULTY",
                is_active=True,
            )
            db.session.add_all([sahil_user, other_user])
            db.session.flush()

            sahil_fac = Faculty(
                user_id=sahil_user.user_id,
                employee_id="FAC-071",
                designation="Associate Professor",
                department_id=self.dept_id,
            )
            other_fac = Faculty(
                user_id=other_user.user_id,
                employee_id="FAC-099",
                designation="Assistant Professor",
                department_id=self.dept_id,
            )
            db.session.add_all([sahil_fac, other_fac])

            # Create Course BCSE-634
            course = Course(
                course_code="BCSE-634",
                course_name="Information Security and IPR",
                department_id=self.dept_id,
                semester=7,
                credits=3,
                batch="2025-2026",
                is_active=True,
            )
            db.session.add(course)
            db.session.flush()

            self.sahil_user_id = sahil_user.user_id
            self.sahil_fac_id = sahil_fac.faculty_id
            self.other_user_id = other_user.user_id
            self.other_fac_id = other_fac.faculty_id
            self.course_id = course.course_id

            # Create Offering 347 (Sec A, 2025-2026 assigned to Sahil)
            offering = CourseOffering(
                course_id=self.course_id,
                faculty_id=self.sahil_fac_id,
                semester=7,
                section="A",
                academic_year="2025-2026",
            )
            db.session.add(offering)
            db.session.flush()
            self.offering_id = offering.offering_id

            # Create Timetable Entry for fixed test day (Wednesday, matching frozen clock 2026-10-21)
            tt = TimetableEntry(
                offering_id=self.offering_id,
                day_of_week="Wednesday",
                start_time=time(0, 0),
                end_time=time(23, 59, 59),
                room="CSE-7A-07",
            )
            db.session.add(tt)
            db.session.commit()
            self.tt_id = tt.timetable_entry_id

    def sahil_headers(self):
        with self.app.app_context():
            token = create_access_token(identity=str(self.sahil_user_id), additional_claims={"role": "FACULTY"})
            return {"Authorization": f"Bearer {token}"}

    def other_faculty_headers(self):
        with self.app.app_context():
            token = create_access_token(identity=str(self.other_user_id), additional_claims={"role": "FACULTY"})
            return {"Authorization": f"Bearer {token}"}

    def _create_students_and_enroll(self, count=10, is_active=True, enrollment_status="ACTIVE", offering_id=None):
        target_offering = offering_id or self.offering_id
        student_ids = []
        with self.app.app_context():
            for i in range(1, count + 1):
                uid = uuid.uuid4().hex[:8]
                u = User(
                    name=f"Student {uid}",
                    email=f"student_{uid}@test.local",
                    password_hash="pw",
                    role="STUDENT",
                    is_active=is_active,
                )
                db.session.add(u)
                db.session.flush()

                s = Student(
                    user_id=u.user_id,
                    enrollment_no=f"ENR_{uid}",
                    department_id=self.dept_id,
                    semester=7,
                    section="A",
                    academic_year="2025-2026",
                )
                db.session.add(s)
                db.session.flush()
                student_ids.append(s.student_id)

                enr = Enrollment(
                    offering_id=target_offering,
                    student_id=s.student_id,
                    status=enrollment_status,
                )
                db.session.add(enr)
            db.session.commit()
        return student_ids

    # Scenario 1: Starting session with 10 active enrolled students succeeds
    def test_01_start_session_with_10_active_enrolled_students(self):
        self._create_students_and_enroll(10)

        res = self.client.post(
            "/api/faculty/attendance/sessions",
            json={"offering_id": self.offering_id, "timetable_entry_id": self.tt_id},
            headers=self.sahil_headers(),
        )
        self.assertEqual(res.status_code, 201)
        data = res.get_json()["data"]
        self.assertEqual(data["status"], "ACTIVE")
        self.assertEqual(data["offering_id"], self.offering_id)
        self.assertIsNotNone(data["session_id"])

    # Scenario 2: Rejecting offering with zero eligible students
    def test_02_reject_offering_with_zero_eligible_students(self):
        # Offering has 0 enrollments
        res = self.client.post(
            "/api/faculty/attendance/sessions",
            json={"offering_id": self.offering_id, "timetable_entry_id": self.tt_id},
            headers=self.sahil_headers(),
        )
        self.assertEqual(res.status_code, 400)
        self.assertIn("No active students are enrolled", res.get_json()["message"])

    # Scenario 3: Rejecting inactive students and inactive enrollments
    def test_03_reject_inactive_students_and_inactive_enrollments(self):
        # 5 students with inactive user accounts, 5 with DROPPED status
        self._create_students_and_enroll(5, is_active=False, enrollment_status="ACTIVE")
        self._create_students_and_enroll(5, is_active=True, enrollment_status="DROPPED")

        res = self.client.post(
            "/api/faculty/attendance/sessions",
            json={"offering_id": self.offering_id, "timetable_entry_id": self.tt_id},
            headers=self.sahil_headers(),
        )
        self.assertEqual(res.status_code, 400)
        self.assertIn("No active students are enrolled", res.get_json()["message"])

    # Scenario 4: Rejecting mismatched timetable slot and offering
    def test_04_reject_mismatched_timetable_slot_and_offering(self):
        self._create_students_and_enroll(10)

        # Create another timetable entry for a different dummy offering
        with self.app.app_context():
            other_offering = CourseOffering(
                course_id=self.course_id,
                faculty_id=self.other_fac_id,
                semester=7,
                section="B",
                academic_year="2025-2026",
            )
            db.session.add(other_offering)
            db.session.flush()

            mismatched_tt = TimetableEntry(
                offering_id=other_offering.offering_id,
                day_of_week="Monday",
                start_time=time(14, 0),
                end_time=time(15, 0),
                room="Room 202",
            )
            db.session.add(mismatched_tt)
            db.session.commit()
            mismatched_tt_id = mismatched_tt.timetable_entry_id

        res = self.client.post(
            "/api/faculty/attendance/sessions",
            json={"offering_id": self.offering_id, "timetable_entry_id": mismatched_tt_id},
            headers=self.sahil_headers(),
        )
        self.assertEqual(res.status_code, 400)
        self.assertIn("does not belong", res.get_json()["message"].lower())

    # Scenario 5: Preventing unauthorized faculty access
    def test_05_prevent_unauthorized_faculty_access(self):
        self._create_students_and_enroll(10)

        # Other faculty tries to start session on Dr. Sahil's offering
        res = self.client.post(
            "/api/faculty/attendance/sessions",
            json={"offering_id": self.offering_id, "timetable_entry_id": self.tt_id},
            headers=self.other_faculty_headers(),
        )
        self.assertEqual(res.status_code, 403)

    # Scenario 6: Returning accurate attendance overview / analytics
    def test_06_accurate_attendance_overview_and_analytics(self):
        student_ids = self._create_students_and_enroll(10)

        # Create a closed session with 8 present and 2 absent
        with self.app.app_context():
            closed_sess = AttendanceSession(
                offering_id=self.offering_id,
                faculty_id=self.sahil_fac_id,
                session_date=date(2025, 10, 1),
                start_time=time(9, 0),
                end_time=time(10, 0),
                status="CLOSED",
            )
            db.session.add(closed_sess)
            db.session.flush()

            for idx, sid in enumerate(student_ids):
                rec = AttendanceRecord(
                    session_id=closed_sess.session_id,
                    student_id=sid,
                    status="PRESENT" if idx < 8 else "ABSENT",
                )
                db.session.add(rec)
            db.session.commit()
            closed_session_id = closed_sess.session_id

        # Overview endpoint
        overview_res = self.client.get(
            f"/api/faculty/attendance/overview?session_id={closed_session_id}",
            headers=self.sahil_headers(),
        )
        self.assertEqual(overview_res.status_code, 200)
        overview_data = overview_res.get_json()["data"]
        self.assertEqual(overview_data["students_present"], 8)
        self.assertEqual(overview_data["students_absent"], 2)
        self.assertEqual(overview_data["total_enrolled"], 10)
        self.assertEqual(overview_data["attendance_rate"], 80.0)

        # Analytics endpoint
        analytics_res = self.client.get(
            "/api/faculty/attendance/analytics",
            headers=self.sahil_headers(),
        )
        self.assertEqual(analytics_res.status_code, 200)
        analytics_data = analytics_res.get_json()["data"]
        self.assertEqual(analytics_data["total_sessions"], 1)
        self.assertEqual(analytics_data["total_present"], 8)
        self.assertEqual(analytics_data["total_absent"], 2)
        self.assertEqual(analytics_data["overall_attendance_percentage"], 80.0)

    # Scenario 7: Handling faculty with no attendance sessions gracefully
    def test_07_handle_faculty_with_no_attendance_sessions_gracefully(self):
        # Other faculty has zero sessions
        res = self.client.get(
            "/api/faculty/attendance/analytics",
            headers=self.other_faculty_headers(),
        )
        self.assertEqual(res.status_code, 200)
        data = res.get_json()["data"]
        self.assertEqual(data["total_sessions"], 0)
        self.assertIsNone(data["overall_attendance_percentage"])
        self.assertEqual(data["total_present"], 0)
        self.assertEqual(data["total_absent"], 0)

    # Scenario 8: Avoiding duplicate course offering options in dropdown
    def test_08_avoid_duplicate_course_offering_options(self):
        # Create offering for Sec B
        with self.app.app_context():
            offering_b = CourseOffering(
                course_id=self.course_id,
                faculty_id=self.sahil_fac_id,
                semester=7,
                section="B",
                academic_year="2025-2026",
            )
            db.session.add(offering_b)
            db.session.commit()

        res = self.client.get("/api/faculty/courses", headers=self.sahil_headers())
        self.assertEqual(res.status_code, 200)
        offerings = res.get_json()["data"]
        # Exactly 2 distinct offerings for Dr. Sahil: Sec A and Sec B
        self.assertEqual(len(offerings), 2)
        sections = [o["section"] for o in offerings]
        self.assertIn("A", sections)
        self.assertIn("B", sections)

    # Scenario 9: Sibling fallback enables attendance on active offering
    def test_09_sibling_fallback_enables_attendance_on_active_offering(self):
        # Create an orphan sibling offering with enrollments
        with self.app.app_context():
            sibling_offering = CourseOffering(
                course_id=self.course_id,
                faculty_id=self.sahil_fac_id,
                semester=7,
                section="A",
                academic_year="2024-2025",
            )
            db.session.add(sibling_offering)
            db.session.commit()
            sibling_id = sibling_offering.offering_id

        # Enroll students on the sibling offering
        self._create_students_and_enroll(10, offering_id=sibling_id)

        # Dr. Sahil starts attendance on active offering 347 (fallback picks up sibling active students)
        res = self.client.post(
            "/api/faculty/attendance/sessions",
            json={"offering_id": self.offering_id, "timetable_entry_id": self.tt_id},
            headers=self.sahil_headers(),
        )
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.get_json()["data"]["status"], "ACTIVE")

    # Scenario 10: Preserving existing attendance history
    def test_10_preserve_existing_attendance_history(self):
        student_ids = self._create_students_and_enroll(10)

        # Start session
        start_res = self.client.post(
            "/api/faculty/attendance/sessions",
            json={"offering_id": self.offering_id, "timetable_entry_id": self.tt_id},
            headers=self.sahil_headers(),
        )
        session_id = start_res.get_json()["data"]["session_id"]

        # Mark attendance records
        with self.app.app_context():
            for sid in student_ids:
                rec = AttendanceRecord(
                    session_id=session_id,
                    student_id=sid,
                    status="PRESENT",
                )
                db.session.add(rec)
            db.session.commit()

        # Close session
        close_res = self.client.post(
            f"/api/faculty/attendance/sessions/{session_id}/close",
            json={},
            headers=self.sahil_headers(),
        )
        self.assertEqual(close_res.status_code, 200)

        # Verify history is preserved
        with self.app.app_context():
            closed_s = db.session.get(AttendanceSession, session_id)
            self.assertEqual(closed_s.status, "CLOSED")
            records = AttendanceRecord.query.filter_by(session_id=session_id).all()
            self.assertEqual(len(records), 10)
            self.assertTrue(all(r.status == "PRESENT" for r in records))


if __name__ == "__main__":
    unittest.main()
