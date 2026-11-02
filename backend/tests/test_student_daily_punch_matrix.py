import unittest
from datetime import date, time

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
    Faculty,
    Student,
    TimetableEntry,
    User,
)
from app.routes.student_attendance import student_attendance_bp


class TestStudentDailyPunchMatrix(unittest.TestCase):
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
                "connect_args": {"check_same_thread": False},
            },
            JWT_TOKEN_LOCATION=["headers"],
        )

        db.init_app(cls.app)
        JWTManager(cls.app)
        cls.app.register_blueprint(student_attendance_bp)

    @classmethod
    def tearDownClass(cls):
        with cls.app.app_context():
            db.session.remove()
            db.drop_all()
            db.engine.dispose()

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

            # Faculty User & Record
            faculty_user = User(
                name="Dr. Alan Turing",
                email="alan@university.edu",
                password_hash="test-pw",
                role="FACULTY",
            )
            db.session.add(faculty_user)
            db.session.flush()

            self.faculty = Faculty(
                user_id=faculty_user.user_id,
                department_id=dept.department_id,
                employee_id="FAC-001",
                designation="Professor",
            )
            db.session.add(self.faculty)
            db.session.flush()

            # Student 1 (Authenticated test student)
            student_user1 = User(
                name="Alice Student",
                email="alice@university.edu",
                password_hash="test-pw",
                role="STUDENT",
            )
            # Student 2 (Other student for cross-student security check)
            student_user2 = User(
                name="Bob Student",
                email="bob@university.edu",
                password_hash="test-pw",
                role="STUDENT",
            )
            db.session.add_all([student_user1, student_user2])
            db.session.flush()

            self.student1 = Student(
                user_id=student_user1.user_id,
                department_id=dept.department_id,
                enrollment_no="STU-001",
                semester=4,
                section="A",
                academic_year="2026-2027",
            )
            self.student2 = Student(
                user_id=student_user2.user_id,
                department_id=dept.department_id,
                enrollment_no="STU-002",
                semester=4,
                section="B",
                academic_year="2026-2027",
            )
            db.session.add_all([self.student1, self.student2])
            db.session.flush()

            # Courses
            self.course_ds = Course(
                department_id=dept.department_id,
                course_code="CSE101",
                course_name="Data Structures",
                semester=4,
                credits=4,
            )
            self.course_cn = Course(
                department_id=dept.department_id,
                course_code="CSE102",
                course_name="Computer Networks",
                semester=4,
                credits=4,
            )
            db.session.add_all([self.course_ds, self.course_cn])
            db.session.flush()

            # Course Offerings
            self.offering_ds = CourseOffering(
                course_id=self.course_ds.course_id,
                faculty_id=self.faculty.faculty_id,
                semester=4,
                section="A",
                academic_year="2026-2027",
                room="Room 101",
            )
            self.offering_cn = CourseOffering(
                course_id=self.course_cn.course_id,
                faculty_id=self.faculty.faculty_id,
                semester=4,
                section="A",
                academic_year="2026-2027",
                room="Room 102",
            )
            db.session.add_all([self.offering_ds, self.offering_cn])
            db.session.flush()

            # Enroll Student 1 in both courses
            enr1 = Enrollment(
                student_id=self.student1.student_id,
                offering_id=self.offering_ds.offering_id,
                status="ACTIVE",
            )
            enr2 = Enrollment(
                student_id=self.student1.student_id,
                offering_id=self.offering_cn.offering_id,
                status="ACTIVE",
            )
            db.session.add_all([enr1, enr2])
            db.session.flush()

            # Timetable Entries:
            # Data Structures: Monday & Wednesday (08:00 - 09:00)
            tt_ds_mon = TimetableEntry(
                offering_id=self.offering_ds.offering_id,
                day_of_week="Monday",
                start_time=time(8, 0),
                end_time=time(9, 0),
                room="Room 101",
            )
            tt_ds_wed = TimetableEntry(
                offering_id=self.offering_ds.offering_id,
                day_of_week="Wednesday",
                start_time=time(8, 0),
                end_time=time(9, 0),
                room="Room 101",
            )
            # Computer Networks: Tuesday & Thursday (10:00 - 11:00)
            tt_cn_tue = TimetableEntry(
                offering_id=self.offering_cn.offering_id,
                day_of_week="Tuesday",
                start_time=time(10, 0),
                end_time=time(11, 0),
                room="Room 102",
            )
            tt_cn_thu = TimetableEntry(
                offering_id=self.offering_cn.offering_id,
                day_of_week="Thursday",
                start_time=time(10, 0),
                end_time=time(11, 0),
                room="Room 102",
            )
            db.session.add_all([tt_ds_mon, tt_ds_wed, tt_cn_tue, tt_cn_thu])
            db.session.flush()

            # Attendance Sessions for testing:
            # Week of May 12, 2025:
            # Mon May 12: DS Session (Closed, Alice PRESENT)
            sess_mon = AttendanceSession(
                offering_id=self.offering_ds.offering_id,
                faculty_id=self.faculty.faculty_id,
                session_date=date(2025, 5, 12),
                start_time=time(8, 0),
                end_time=time(9, 0),
                status="CLOSED",
            )
            # Tue May 13: CN Session (Closed, Alice ABSENT - no record)
            sess_tue = AttendanceSession(
                offering_id=self.offering_cn.offering_id,
                faculty_id=self.faculty.faculty_id,
                session_date=date(2025, 5, 13),
                start_time=time(10, 0),
                end_time=time(11, 0),
                status="CLOSED",
            )
            db.session.add_all([sess_mon, sess_tue])
            db.session.flush()

            # Alice marked PRESENT for Mon May 12
            rec_mon = AttendanceRecord(
                session_id=sess_mon.session_id,
                student_id=self.student1.student_id,
                status="PRESENT",
            )
            db.session.add(rec_mon)
            db.session.commit()

            self.offering_ds_id = self.offering_ds.offering_id
            self.faculty_id = self.faculty.faculty_id
            self.dept_id = dept.department_id
            self.student1_id = self.student1.student_id

            with self.app.app_context():
                self.token1 = create_access_token(
                    identity=str(student_user1.user_id),
                    additional_claims={"role": "STUDENT"},
                )
                self.token2 = create_access_token(
                    identity=str(student_user2.user_id),
                    additional_claims={"role": "STUDENT"},
                )

    def test_daily_punch_authenticated_success(self):
        """Test fetching daily punch returns 200 with structured week and matrix."""
        res = self.client.get(
            "/api/student/attendance/daily-punch?date=2025-05-12",
            headers={"Authorization": f"Bearer {self.token1}"},
        )
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["success"])
        self.assertIn("week_info", data)
        self.assertIn("summary_cards", data)
        self.assertIn("matrix", data)
        self.assertIn("today_schedule", data)
        self.assertIn("overall_summary", data)

        # Check week info
        week_info = data["week_info"]
        self.assertEqual(week_info["start_date"], "2025-05-12")
        self.assertEqual(week_info["end_date"], "2025-05-16")
        self.assertEqual(len(week_info["days"]), 5)

        # Check summary cards for May 12, 2025 (Monday)
        summary = data["summary_cards"]
        self.assertEqual(summary["selected_date"], "2025-05-12")
        self.assertEqual(summary["present_today"], 1)
        self.assertEqual(summary["total_classes_today"], 1)

    def test_weekly_matrix_cell_statuses(self):
        """Verify matrix distinguishes PRESENT, ABSENT, PENDING/UPCOMING, and NO_CLASS."""
        res = self.client.get(
            "/api/student/attendance/daily-punch?date=2025-05-12",
            headers={"Authorization": f"Bearer {self.token1}"},
        )
        data = res.get_json()
        matrix = data["matrix"]
        self.assertEqual(len(matrix), 2)  # Two enrolled courses

        ds_row = next(r for r in matrix if r["course_code"] == "CSE101")
        cn_row = next(r for r in matrix if r["course_code"] == "CSE102")

        # Mon May 12: DS was conducted and student was PRESENT
        self.assertEqual(ds_row["week_attendance"]["2025-05-12"]["status"], "PRESENT")
        self.assertTrue(ds_row["week_attendance"]["2025-05-12"]["scheduled"])

        # Mon May 12: CN was NOT scheduled
        self.assertEqual(cn_row["week_attendance"]["2025-05-12"]["status"], "NO_CLASS")
        self.assertFalse(cn_row["week_attendance"]["2025-05-12"]["scheduled"])

        # Tue May 13: CN was conducted and student was ABSENT
        self.assertEqual(cn_row["week_attendance"]["2025-05-13"]["status"], "ABSENT")
        self.assertTrue(cn_row["week_attendance"]["2025-05-13"]["scheduled"])

        # Fri May 16: Neither course is scheduled on Friday
        self.assertEqual(ds_row["week_attendance"]["2025-05-16"]["status"], "NO_CLASS")
        self.assertEqual(cn_row["week_attendance"]["2025-05-16"]["status"], "NO_CLASS")

    def test_cross_student_access_prevention(self):
        """Ensure authenticated student cannot see another student's attendance records."""
        # Query with Student 2's token: Student 2 has no enrollments
        res = self.client.get(
            "/api/student/attendance/daily-punch?date=2025-05-12",
            headers={"Authorization": f"Bearer {self.token2}"},
        )
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["matrix"], [])
        self.assertEqual(data["today_schedule"], [])
        self.assertEqual(data["summary_cards"]["present_today"], 0)

    def test_invalid_date_parameters(self):
        """Test invalid date format returns 400 Bad Request."""
        res = self.client.get(
            "/api/student/attendance/daily-punch?date=not-a-date",
            headers={"Authorization": f"Bearer {self.token1}"},
        )
        self.assertEqual(res.status_code, 400)
        self.assertIn("Invalid date", res.get_json()["message"])

        res2 = self.client.get(
            "/api/student/attendance/daily-punch?start_date=2025-05-16&end_date=2025-05-12",
            headers={"Authorization": f"Bearer {self.token1}"},
        )
        self.assertEqual(res2.status_code, 400)
        self.assertIn("start_date cannot be after end_date", res2.get_json()["message"])

    def test_multiple_sessions_same_day(self):
        """Verify multiple sessions on the same day are captured in the cell's sessions array."""
        with self.app.app_context():
            # Add a second afternoon session for DS on May 12
            sess_mon_pm = AttendanceSession(
                offering_id=self.offering_ds_id,
                faculty_id=self.faculty_id,
                session_date=date(2025, 5, 12),
                start_time=time(14, 0),
                end_time=time(15, 0),
                status="CLOSED",
            )
            db.session.add(sess_mon_pm)
            db.session.commit()

        res = self.client.get(
            "/api/student/attendance/daily-punch?date=2025-05-12",
            headers={"Authorization": f"Bearer {self.token1}"},
        )
        data = res.get_json()
        ds_row = next(r for r in data["matrix"] if r["course_code"] == "CSE101")
        mon_cell = ds_row["week_attendance"]["2025-05-12"]
        self.assertEqual(mon_cell["total_sessions"], 2)
        self.assertEqual(len(mon_cell["sessions"]), 2)

    def test_semester_attendance_calculation(self):
        """Verify semester attendance percentage is accurate."""
        res = self.client.get(
            "/api/student/attendance/daily-punch?date=2025-05-12",
            headers={"Authorization": f"Bearer {self.token1}"},
        )
        data = res.get_json()
        summary = data["overall_summary"]
        # 1 present out of 2 closed sessions = 50.0%
        self.assertEqual(summary["total_sessions"], 2)
        self.assertEqual(summary["present_sessions"], 1)
        self.assertEqual(summary["absent_sessions"], 1)
        self.assertEqual(summary["attendance_rate"], 50.0)

    def test_unauthenticated_request_rejected(self):
        """Unauthenticated requests must be rejected with 401."""
        res = self.client.get("/api/student/attendance/daily-punch")
        self.assertEqual(res.status_code, 401)

    def test_matrix_alias_route(self):
        """Verify /matrix alias route functions identically."""
        res = self.client.get(
            "/api/student/attendance/matrix?date=2025-05-12",
            headers={"Authorization": f"Bearer {self.token1}"},
        )
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.get_json()["success"])

    def test_unrecorded_scheduled_class_not_falsely_marked_absent(self):
        """Wednesday May 14 has scheduled DS class but no session was conducted. It must be UNRECORDED, not ABSENT."""
        res = self.client.get(
            "/api/student/attendance/daily-punch?date=2025-05-12",
            headers={"Authorization": f"Bearer {self.token1}"},
        )
        data = res.get_json()
        ds_row = next(r for r in data["matrix"] if r["course_code"] == "CSE101")
        wed_cell = ds_row["week_attendance"]["2025-05-14"]
        self.assertTrue(wed_cell["scheduled"])
        self.assertEqual(wed_cell["status"], "UNRECORDED")

    def test_missing_optional_faculty_and_room_defaults(self):
        """Verify offerings without assigned faculty or room display graceful fallback strings."""
        with self.app.app_context():
            course_chem = Course(
                department_id=self.dept_id,
                course_code="CHM101",
                course_name="Chemistry",
                semester=4,
                credits=3,
            )
            db.session.add(course_chem)
            db.session.flush()

            off_chem = CourseOffering(
                course_id=course_chem.course_id,
                faculty_id=None,
                semester=4,
                section="A",
                academic_year="2026-2027",
                room=None,
            )
            db.session.add(off_chem)
            db.session.flush()

            enr = Enrollment(
                student_id=self.student1_id,
                offering_id=off_chem.offering_id,
                status="ACTIVE",
            )
            db.session.add(enr)
            db.session.commit()

        res = self.client.get(
            "/api/student/attendance/daily-punch?date=2025-05-12",
            headers={"Authorization": f"Bearer {self.token1}"},
        )
        data = res.get_json()
        chem_row = next(r for r in data["matrix"] if r["course_code"] == "CHM101")
        self.assertEqual(chem_row["room"], "TBD")
        self.assertEqual(chem_row["faculty_name"], "Faculty Assigned")


if __name__ == "__main__":
    unittest.main()
