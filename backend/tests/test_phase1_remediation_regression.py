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
from app.routes.faculty import faculty_bp
from app.routes.student import student_bp
from app.routes.student_attendance import student_attendance_bp
from app.routes.timetable import timetable_bp
from app.routes.enrollment import enrollment_bp


class TestPhase1RemediationRegression(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = Flask(__name__)
        cls.app.config.update(
            TESTING=True,
            SECRET_KEY="test-secret-phase1",
            JWT_SECRET_KEY="test-jwt-secret-key-32-bytes-long",
            SQLALCHEMY_DATABASE_URI="sqlite://",
            SQLALCHEMY_TRACK_MODIFICATIONS=False,
            SQLALCHEMY_ENGINE_OPTIONS={
                "poolclass": StaticPool,
                "connect_args": {"check_same_thread": False},
            },
            JWT_TOKEN_LOCATION=["headers"],
            INSTITUTION_TIMEZONE="Asia/Kolkata",
            CURRENT_ACADEMIC_SESSION="2026-2027",
        )

        db.init_app(cls.app)
        bcrypt.init_app(cls.app)
        JWTManager(cls.app)

        cls.app.register_blueprint(faculty_bp)
        cls.app.register_blueprint(student_bp)
        cls.app.register_blueprint(student_attendance_bp)
        cls.app.register_blueprint(timetable_bp)
        cls.app.register_blueprint(enrollment_bp)

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

            # Base Department
            dept = Department(department_name="Computer Science & Engineering", department_code="CSE")
            db.session.add(dept)
            db.session.flush()
            self.dept_id = dept.department_id

            # Faculty 1 (Dr. Mani Goyal)
            u_fac1 = User(name="Dr. Mani Goyal", email="mani.goyal@college.edu", password_hash="pw", role="FACULTY", is_active=True)
            db.session.add(u_fac1)
            db.session.flush()
            fac1 = Faculty(user_id=u_fac1.user_id, department_id=self.dept_id, employee_id="FAC001", designation="Associate Professor")
            db.session.add(fac1)
            db.session.flush()
            self.fac1_id = fac1.faculty_id
            self.fac1_user_id = u_fac1.user_id

            # Faculty 2 (Dr. Other)
            u_fac2 = User(name="Dr. Other", email="other@college.edu", password_hash="pw", role="FACULTY", is_active=True)
            db.session.add(u_fac2)
            db.session.flush()
            fac2 = Faculty(user_id=u_fac2.user_id, department_id=self.dept_id, employee_id="FAC002", designation="Assistant Professor")
            db.session.add(fac2)
            db.session.flush()
            self.fac2_id = fac2.faculty_id
            self.fac2_user_id = u_fac2.user_id

            # Admin User
            admin_user = User(name="Admin User", email="admin@college.edu", password_hash="pw", role="ADMIN", is_active=True)
            db.session.add(admin_user)
            db.session.flush()
            self.admin_user_id = admin_user.user_id

            # Students
            u_stu1 = User(name="Upendra Student", email="upendra@college.edu", password_hash="pw", role="STUDENT", is_active=True)
            u_stu2 = User(name="Inactive Student", email="inactive@college.edu", password_hash="pw", role="STUDENT", is_active=False)
            u_stu3 = User(name="Other Section Student", email="other_stu@college.edu", password_hash="pw", role="STUDENT", is_active=True)
            u_stu_hist = User(name="Historical Student", email="hist@college.edu", password_hash="pw", role="STUDENT", is_active=True)
            db.session.add_all([u_stu1, u_stu2, u_stu3, u_stu_hist])
            db.session.flush()

            stu1 = Student(user_id=u_stu1.user_id, department_id=self.dept_id, enrollment_no="ENR001", semester=7, section="A", academic_year="2026-2027")
            stu2 = Student(user_id=u_stu2.user_id, department_id=self.dept_id, enrollment_no="ENR002", semester=7, section="A", academic_year="2026-2027")
            stu3 = Student(user_id=u_stu3.user_id, department_id=self.dept_id, enrollment_no="ENR003", semester=7, section="B", academic_year="2026-2027")
            stu_hist = Student(user_id=u_stu_hist.user_id, department_id=self.dept_id, enrollment_no="ENR_HIST", semester=7, section="A", academic_year="2024-2025")
            db.session.add_all([stu1, stu2, stu3, stu_hist])
            db.session.flush()

            self.stu1_id = stu1.student_id
            self.stu1_user_id = u_stu1.user_id
            self.stu2_id = stu2.student_id
            self.stu3_id = stu3.student_id
            self.stu_hist_id = stu_hist.student_id

            # Courses
            course = Course(course_code="BCSE-701", course_name="Deep Learning", department_id=self.dept_id, semester=7, credits=4)
            course_other = Course(course_code="BCSE-702", course_name="Cloud Computing", department_id=self.dept_id, semester=7, credits=3)
            db.session.add_all([course, course_other])
            db.session.flush()
            self.course_id = course.course_id
            self.course_other_id = course_other.course_id

            # Offerings:
            # 1. Offering enroll: Course BCSE-701, Sem 7, Sec A, academic_year="2026 - 2027" (whitespace variation of 2026-2027)
            off_enroll = CourseOffering(course_id=self.course_id, faculty_id=None, semester=7, section="A", academic_year="2026 - 2027")
            # 2. Offering teach: Course BCSE-701, Sem 7, Sec A, faculty_id=Dr. Mani Goyal, academic_year="2026-2027"
            off_teach = CourseOffering(course_id=self.course_id, faculty_id=self.fac1_id, semester=7, section="A", academic_year="2026-2027", room="LAB-3")
            # 3. Offering historical: Course BCSE-701, Sem 7, Sec A, faculty_id=None, academic_year="2024-2025" (unrelated historical session)
            off_hist = CourseOffering(course_id=self.course_id, faculty_id=None, semester=7, section="A", academic_year="2024-2025")
            # 4. Offering other: Course BCSE-701, Sem 7, Sec B, faculty_id=Dr. Other, academic_year="2026-2027"
            off_other = CourseOffering(course_id=self.course_id, faculty_id=self.fac2_id, semester=7, section="B", academic_year="2026-2027", room="LAB-4")
            db.session.add_all([off_enroll, off_teach, off_hist, off_other])
            db.session.flush()

            self.offering_enroll_id = off_enroll.offering_id
            self.offering_teach_id = off_teach.offering_id
            self.offering_hist_id = off_hist.offering_id
            self.offering_other_fac_id = off_other.offering_id

            # Enrollments:
            enr1 = Enrollment(offering_id=self.offering_enroll_id, student_id=self.stu1_id, status="ACTIVE")
            enr2 = Enrollment(offering_id=self.offering_enroll_id, student_id=self.stu2_id, status="ACTIVE")
            enr3 = Enrollment(offering_id=self.offering_other_fac_id, student_id=self.stu3_id, status="ACTIVE")
            enr_hist = Enrollment(offering_id=self.offering_hist_id, student_id=self.stu_hist_id, status="ACTIVE")
            db.session.add_all([enr1, enr2, enr3, enr_hist])

            # Timetable Entries:
            # Current session slot on offering_teach (Offering 262)
            tt_entry = TimetableEntry(
                offering_id=self.offering_teach_id,
                day_of_week="Wednesday",
                start_time=time(10, 0),
                end_time=time(11, 0),
                room="LAB-3",
            )
            # Historical session slot on offering_hist (2024-2025)
            tt_hist = TimetableEntry(
                offering_id=self.offering_hist_id,
                day_of_week="Wednesday",
                start_time=time(10, 0),
                end_time=time(11, 0),
                room="OLD-ROOM",
            )
            db.session.add_all([tt_entry, tt_hist])

            # Attendance Sessions:
            # 1. Closed session for current 2026-2027 offering_teach
            session_current = AttendanceSession(
                offering_id=self.offering_teach_id,
                faculty_id=self.fac1_id,
                session_date=date(2026, 10, 20),
                start_time=time(10, 0),
                end_time=time(11, 0),
                status="CLOSED",
            )
            # 2. Closed session for historical 2024-2025 offering_hist
            session_hist = AttendanceSession(
                offering_id=self.offering_hist_id,
                faculty_id=self.fac2_id,
                session_date=date(2024, 11, 15),
                start_time=time(10, 0),
                end_time=time(11, 0),
                status="CLOSED",
            )
            db.session.add_all([session_current, session_hist])
            db.session.flush()
            self.session_id = session_current.session_id
            self.session_hist_id = session_hist.session_id

            # Attendance records
            att_rec1 = AttendanceRecord(
                session_id=self.session_id,
                student_id=self.stu1_id,
                status="PRESENT",
            )
            att_rec_hist = AttendanceRecord(
                session_id=self.session_hist_id,
                student_id=self.stu_hist_id,
                status="PRESENT",
            )
            db.session.add_all([att_rec1, att_rec_hist])
            db.session.commit()

    def _headers(self, user_id, role="FACULTY"):
        with self.app.app_context():
            token = create_access_token(identity=str(user_id), additional_claims={"role": role})
        return {"Authorization": f"Bearer {token}"}

    # =========================================================================
    # Stage B: GET /api/faculty/students
    # =========================================================================
    def test_b1_faculty_students_resolves_sibling_offering_and_preserves_real_enrollment_id(self):
        """When Dr. Mani Goyal's assigned offering (262) has 0 direct enrollments,
        it resolves students from valid sibling offering (100) for same academic session (2026-2027).
        Additionally verifies that offering_id is the real enrollment ID (100) and offering_ids
        contains both real enrollment (100) and teaching assignment (262)."""
        headers = self._headers(self.fac1_user_id, role="FACULTY")
        res = self.client.get("/api/faculty/students", headers=headers)
        self.assertEqual(res.status_code, 200)
        data = res.get_json()["data"]

        # Stu 1 should be returned
        stu1_entry = next((s for s in data if s["enrollment_no"] == "ENR001"), None)
        self.assertIsNotNone(stu1_entry)

        # Real enrollment ID accurately preserved
        self.assertEqual(stu1_entry["offering_id"], self.offering_enroll_id)
        # offering_ids accurately reflects real enrollment and teaching assignment
        self.assertIn(self.offering_enroll_id, stu1_entry["offering_ids"])
        self.assertIn(self.offering_teach_id, stu1_entry["offering_ids"])
        self.assertEqual(stu1_entry["teaching_offering_id"], self.offering_teach_id)

    def test_b2_faculty_students_excludes_unrelated_historical_academic_year(self):
        """Students enrolled under unrelated historical academic year (2024-2025) are NOT returned
        in Dr. Mani Goyal's 2026-2027 student list."""
        headers = self._headers(self.fac1_user_id, role="FACULTY")
        res = self.client.get("/api/faculty/students", headers=headers)
        data = res.get_json()["data"]
        enr_nos = [s["enrollment_no"] for s in data]
        self.assertNotIn("ENR_HIST", enr_nos)

    def test_b3_faculty_students_cross_faculty_isolation(self):
        """Offerings belonging to Dr. Other (Sec B) do not leak into Dr. Mani Goyal's student list."""
        headers = self._headers(self.fac1_user_id, role="FACULTY")
        res = self.client.get("/api/faculty/students", headers=headers)
        data = res.get_json()["data"]
        enr_nos = [s["enrollment_no"] for s in data]
        self.assertNotIn("ENR003", enr_nos)

        # Dr. Other only sees Stu 3
        headers_other = self._headers(self.fac2_user_id, role="FACULTY")
        res_other = self.client.get("/api/faculty/students", headers=headers_other)
        data_other = res_other.get_json()["data"]
        enr_nos_other = [s["enrollment_no"] for s in data_other]
        self.assertIn("ENR003", enr_nos_other)
        self.assertNotIn("ENR001", enr_nos_other)

    def test_b4_faculty_students_inactive_enrollment_excluded(self):
        """Enrollments with status='DROPPED' or inactive users are excluded from faculty student list."""
        with self.app.app_context():
            u_drop = User(name="Dropped Student", email="drop@college.edu", password_hash="pw", role="STUDENT", is_active=True)
            db.session.add(u_drop)
            db.session.flush()
            s_drop = Student(user_id=u_drop.user_id, department_id=self.dept_id, enrollment_no="ENR_DROP", semester=7, section="A", academic_year="2026-2027")
            db.session.add(s_drop)
            db.session.flush()
            e_drop = Enrollment(offering_id=self.offering_enroll_id, student_id=s_drop.student_id, status="DROPPED")
            db.session.add(e_drop)
            db.session.commit()

        headers = self._headers(self.fac1_user_id, role="FACULTY")
        res = self.client.get("/api/faculty/students", headers=headers)
        data = res.get_json()["data"]
        enr_nos = [s["enrollment_no"] for s in data]
        self.assertNotIn("ENR_DROP", enr_nos)
        self.assertNotIn("ENR002", enr_nos)

    # =========================================================================
    # Stage C: GET /api/student/attendance/summary
    # =========================================================================
    def test_c1_student_attendance_summary_resolves_compatible_sibling_sessions(self):
        """Student enrolled in Offering 100 sees attendance recorded in closed session from Offering 262."""
        headers = self._headers(self.stu1_user_id, role="STUDENT")
        res = self.client.get("/api/student/attendance/summary", headers=headers)
        self.assertEqual(res.status_code, 200)
        courses = res.get_json()["data"]
        self.assertEqual(len(courses), 1)

        c = courses[0]
        self.assertEqual(c["course_code"], "BCSE-701")
        self.assertEqual(c["total_sessions"], 1)
        self.assertEqual(c["present_sessions"], 1)
        self.assertEqual(c["absent_sessions"], 0)
        self.assertEqual(c["attendance_percentage"], 100.0)
        # Normalized session academic year
        self.assertIn("academic_year", c)
        self.assertEqual(c["academic_year"], "2026-2027")

    def test_c2_student_attendance_summary_excludes_unrelated_historical_sessions(self):
        """Sessions from unrelated historical academic year (2024-2025) are NOT included in 2026-2027 summary."""
        # Enroll stu 1 also in an absent record for a second 2026-2027 session
        with self.app.app_context():
            sess2 = AttendanceSession(
                offering_id=self.offering_teach_id,
                faculty_id=self.fac1_id,
                session_date=date(2026, 10, 21),
                start_time=time(10, 0),
                end_time=time(11, 0),
                status="CLOSED",
            )
            db.session.add(sess2)
            db.session.flush()
            rec2 = AttendanceRecord(session_id=sess2.session_id, student_id=self.stu1_id, status="ABSENT")
            db.session.add(rec2)
            db.session.commit()

        headers = self._headers(self.stu1_user_id, role="STUDENT")
        res = self.client.get("/api/student/attendance/summary", headers=headers)
        courses = res.get_json()["data"]
        c = courses[0]
        # Only 2 current sessions counted (session_current and sess2), NOT the 2024-2025 historical session!
        self.assertEqual(c["total_sessions"], 2)
        self.assertEqual(c["present_sessions"], 1)
        self.assertEqual(c["absent_sessions"], 1)

    # =========================================================================
    # Stage D: GET /api/timetable/student
    # =========================================================================
    def test_d1_student_timetable_resolves_sibling_slots_and_excludes_historical(self):
        """Student enrolled in offering 100 sees timetable entry from sibling offering 262 (2026-2027),
        while historical slots from 2024-2025 (OLD-ROOM) are strictly excluded."""
        headers = self._headers(self.stu1_user_id, role="STUDENT")
        res = self.client.get("/api/timetable/student", headers=headers)
        self.assertEqual(res.status_code, 200)
        slots = res.get_json()["data"]

        # LAB-3 should be present
        rooms = [s["room"] for s in slots]
        self.assertIn("LAB-3", rooms)
        # OLD-ROOM (historical 2024-2025) must NOT be present
        self.assertNotIn("OLD-ROOM", rooms)

    def test_d2_student_timetable_preserves_distinct_legitimate_entries(self):
        """Distinct legitimate slots (different room or different faculty) at the same time are NOT collapsed."""
        with self.app.app_context():
            # Add a parallel lab slot in LAB-4 with Dr. Other on offering_teach
            distinct_slot = TimetableEntry(
                offering_id=self.offering_teach_id,
                day_of_week="Wednesday",
                start_time=time(10, 0),
                end_time=time(11, 0),
                room="LAB-4",  # different room
            )
            db.session.add(distinct_slot)
            db.session.commit()

        headers = self._headers(self.stu1_user_id, role="STUDENT")
        res = self.client.get("/api/timetable/student", headers=headers)
        slots = res.get_json()["data"]
        wed_slots = [s for s in slots if s["day_of_week"] == "Wednesday" and s["start_time"] == "10:00"]
        rooms = [s["room"] for s in wed_slots]
        # Both LAB-3 and LAB-4 should be visible because they are distinct legitimate sessions
        self.assertIn("LAB-3", rooms)
        self.assertIn("LAB-4", rooms)
        self.assertEqual(len(wed_slots), 2)

    def test_d3_student_timetable_deduplicates_true_duplicates(self):
        """True identical duplicate slots (same course, section, day, time, room, faculty) are deduplicated."""
        with self.app.app_context():
            # Add an identical slot on offering_enroll with same day, time, room, faculty
            dup_slot = TimetableEntry(
                offering_id=self.offering_enroll_id,
                day_of_week="Wednesday",
                start_time=time(10, 0),
                end_time=time(11, 0),
                room="LAB-3",
            )
            db.session.add(dup_slot)
            db.session.commit()

        headers = self._headers(self.stu1_user_id, role="STUDENT")
        res = self.client.get("/api/timetable/student", headers=headers)
        slots = res.get_json()["data"]
        lab3_slots = [s for s in slots if s["day_of_week"] == "Wednesday" and s["room"] == "LAB-3"]
        self.assertEqual(len(lab3_slots), 1)

    # =========================================================================
    # Stage E: Enrollment Summary Academic Year Normalization
    # =========================================================================
    def test_e1_enrollment_summary_normalizes_whitespace_academic_year(self):
        """Enrollment summary normalizes whitespace-corrupted academic year '2026 - 2027' to '2026-2027'."""
        headers = self._headers(self.admin_user_id, role="ADMIN")
        res = self.client.get("/api/admin/enrollments/summary", headers=headers)
        self.assertEqual(res.status_code, 200)
        groups = res.get_json()["data"]["groups"]
        grp = next((g for g in groups if g["semester"] == 7 and g["section"] == "A"), None)
        self.assertIsNotNone(grp)
        self.assertNotIn(" -", grp["academic_year"])
        self.assertNotIn("- ", grp["academic_year"])

    def test_e2_enrollment_summary_batch_cohort_does_not_substitute_current_session(self):
        """Enrollment summary sets academic_year to None when student has only a cohort string ('2024-2028')
        without course offerings, rather than falsely substituting the current academic session."""
        with self.app.app_context():
            dept2 = Department(department_name="Mechanical", department_code="MECH")
            db.session.add(dept2)
            db.session.flush()
            u_mech = User(name="Mech Student", email="mech@college.edu", password_hash="pw", role="STUDENT", is_active=True)
            db.session.add(u_mech)
            db.session.flush()
            s_mech = Student(user_id=u_mech.user_id, department_id=dept2.department_id, enrollment_no="MECH001", semester=1, section="A", academic_year="2024-2028")
            db.session.add(s_mech)
            db.session.commit()

        headers = self._headers(self.admin_user_id, role="ADMIN")
        res = self.client.get("/api/admin/enrollments/summary", headers=headers)
        groups = res.get_json()["data"]["groups"]
        grp = next((g for g in groups if g["department_code"] == "MECH"), None)
        self.assertIsNotNone(grp)
        # Should NOT be substituted with current session ('2026-2027') nor batch range
        self.assertIsNone(grp["academic_year"])

    def test_e3_get_enrollments_resolves_canonical_academic_year(self):
        """GET /api/admin/enrollments resolves offering academic year to canonical format."""
        headers = self._headers(self.admin_user_id, role="ADMIN")
        res = self.client.get("/api/admin/enrollments", headers=headers)
        self.assertEqual(res.status_code, 200)
        data = res.get_json()["data"]
        enr_rec = next((r for r in data if r["student_id"] == self.stu1_id), None)
        self.assertIsNotNone(enr_rec)
        self.assertEqual(enr_rec["academic_year"], "2026-2027")

    # =========================================================================
    # Stage F: GET /api/student/courses
    # =========================================================================
    def test_f1_canonical_student_courses_endpoint_works(self):
        """The canonical student courses route returns complete course info including credits and faculty."""
        headers = self._headers(self.stu1_user_id, role="STUDENT")
        res = self.client.get("/api/student/courses", headers=headers)
        self.assertEqual(res.status_code, 200)
        data = res.get_json()["data"]
        self.assertEqual(len(data), 1)

        c = data[0]
        self.assertEqual(c["course_code"], "BCSE-701")
        self.assertEqual(c["course_name"], "Deep Learning")
        self.assertEqual(c["credits"], 4)
        self.assertEqual(c["semester"], 7)
        self.assertEqual(c["section"], "A")
        self.assertIn("faculty", c)

    def test_f2_student_courses_requires_auth(self):
        """Unauthorized requests are rejected."""
        res = self.client.get("/api/student/courses")
        self.assertEqual(res.status_code, 401)


if __name__ == "__main__":
    unittest.main()
