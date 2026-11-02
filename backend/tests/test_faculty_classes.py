import unittest
from datetime import date, time

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
    FacultyAdjustment,
    Student,
    TimetableEntry,
    User,
)
from app.routes.analytics import analytics_bp
from app.routes.faculty import faculty_bp
from app.routes.timetable import timetable_bp


class TestFacultyClassesIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = Flask(__name__)
        cls.app.config.update(
            TESTING=True,
            SECRET_KEY="test-secret-faculty-classes",
            JWT_SECRET_KEY="test-jwt-secret-faculty-classes-32b",
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

        cls.app.register_blueprint(faculty_bp)
        cls.app.register_blueprint(timetable_bp)
        cls.app.register_blueprint(analytics_bp)

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

            # 1. Department
            self.department = Department(
                department_name="Computer Science & Engineering",
                department_code="CSE",
            )
            db.session.add(self.department)
            db.session.flush()

            # 2. Users
            self.user_faculty_a = User(
                name="Prof. Alice Smith",
                email="alice@test.local",
                password_hash="not-used",
                role="FACULTY",
            )
            self.user_faculty_b = User(
                name="Prof. Bob Jones",
                email="bob@test.local",
                password_hash="not-used",
                role="FACULTY",
            )
            self.user_student_1 = User(
                name="Charlie Brown",
                email="charlie@test.local",
                password_hash="not-used",
                role="STUDENT",
            )
            self.user_student_2 = User(
                name="Dana White",
                email="dana@test.local",
                password_hash="not-used",
                role="STUDENT",
            )
            self.user_admin = User(
                name="Admin User",
                email="admin@test.local",
                password_hash="not-used",
                role="ADMIN",
            )
            db.session.add_all([
                self.user_faculty_a,
                self.user_faculty_b,
                self.user_student_1,
                self.user_student_2,
                self.user_admin,
            ])
            db.session.flush()

            # 3. Faculty records
            self.faculty_a = Faculty(
                user_id=self.user_faculty_a.user_id,
                department_id=self.department.department_id,
                employee_id="FAC-A01",
                designation="Associate Professor",
            )
            self.faculty_b = Faculty(
                user_id=self.user_faculty_b.user_id,
                department_id=self.department.department_id,
                employee_id="FAC-B01",
                designation="Assistant Professor",
            )

            # 4. Student records
            self.student_1 = Student(
                user_id=self.user_student_1.user_id,
                department_id=self.department.department_id,
                enrollment_no="STU-001",
                semester=6,
                section="A",
                academic_year="2026-27",
            )
            self.student_2 = Student(
                user_id=self.user_student_2.user_id,
                department_id=self.department.department_id,
                enrollment_no="STU-002",
                semester=6,
                section="A",
                academic_year="2026-27",
            )
            db.session.add_all([self.faculty_a, self.faculty_b, self.student_1, self.student_2])
            db.session.flush()

            # 5. Courses
            self.course_ds = Course(
                department_id=self.department.department_id,
                course_code="CS301",
                course_name="Data Structures",
                semester=6,
                credits=4,
            )
            self.course_algo = Course(
                department_id=self.department.department_id,
                course_code="CS302",
                course_name="Design and Analysis of Algorithms",
                semester=7,
                credits=3,
            )
            self.course_os = Course(
                department_id=self.department.department_id,
                course_code="CS303",
                course_name="Operating Systems",
                semester=6,
                credits=4,
            )
            db.session.add_all([self.course_ds, self.course_algo, self.course_os])
            db.session.flush()

            # 6. Course Offerings:
            # - Faculty A teaches CS301 Sec A (with 2 enrolled students)
            # - Faculty A teaches CS301 Sec B (with 1 enrolled student)
            # - Faculty A teaches CS302 Sec A (with 0 enrolled students, 0 sessions)
            # - Faculty B teaches CS303 Sec A (only Faculty B)
            self.offering_a1 = CourseOffering(
                course_id=self.course_ds.course_id,
                faculty_id=self.faculty_a.faculty_id,
                semester=6,
                section="A",
                academic_year="2026-27",
                room="LH-101",
            )
            self.offering_a2 = CourseOffering(
                course_id=self.course_ds.course_id,
                faculty_id=self.faculty_a.faculty_id,
                semester=6,
                section="B",
                academic_year="2026-27",
                room=None,  # Room is None; will test timetable fallback
            )
            self.offering_a3 = CourseOffering(
                course_id=self.course_algo.course_id,
                faculty_id=self.faculty_a.faculty_id,
                semester=7,
                section="A",
                academic_year="2026-27",
                room="LH-201",
            )
            self.offering_b1 = CourseOffering(
                course_id=self.course_os.course_id,
                faculty_id=self.faculty_b.faculty_id,
                semester=6,
                section="A",
                academic_year="2026-27",
                room="LH-301",
            )
            db.session.add_all([self.offering_a1, self.offering_a2, self.offering_a3, self.offering_b1])
            db.session.flush()

            # 7. Enrollments
            # Student 1 enrolled in A1 and A2
            # Student 2 enrolled in A1
            self.enroll_1 = Enrollment(
                student_id=self.student_1.student_id,
                offering_id=self.offering_a1.offering_id,
                status="ACTIVE",
            )
            self.enroll_2 = Enrollment(
                student_id=self.student_2.student_id,
                offering_id=self.offering_a1.offering_id,
                status="ACTIVE",
            )
            self.enroll_3 = Enrollment(
                student_id=self.student_1.student_id,
                offering_id=self.offering_a2.offering_id,
                status="ACTIVE",
            )
            # Student 2 dropped from A2 (INACTIVE - should not be counted)
            self.enroll_inactive = Enrollment(
                student_id=self.student_2.student_id,
                offering_id=self.offering_a2.offering_id,
                status="DROPPED",
            )
            db.session.add_all([self.enroll_1, self.enroll_2, self.enroll_3, self.enroll_inactive])
            db.session.flush()

            # 8. Timetable Entries
            # Offering A1 has 2 slots (Monday 09:00, Wednesday 10:00)
            self.tt_a1_1 = TimetableEntry(
                offering_id=self.offering_a1.offering_id,
                day_of_week="Monday",
                start_time=time(9, 0),
                end_time=time(10, 0),
                room="LH-101",
            )
            self.tt_a1_2 = TimetableEntry(
                offering_id=self.offering_a1.offering_id,
                day_of_week="Wednesday",
                start_time=time(10, 0),
                end_time=time(11, 0),
                room="LH-101",
            )
            # Offering A2 has 1 slot with room "LH-102" (offering.room was None)
            self.tt_a2_1 = TimetableEntry(
                offering_id=self.offering_a2.offering_id,
                day_of_week="Tuesday",
                start_time=time(11, 0),
                end_time=time(12, 0),
                room="LH-102",
            )
            # Offering B1 has 1 slot (Faculty B's entry)
            self.tt_b1_1 = TimetableEntry(
                offering_id=self.offering_b1.offering_id,
                day_of_week="Thursday",
                start_time=time(14, 0),
                end_time=time(15, 0),
                room="LH-301",
            )
            db.session.add_all([self.tt_a1_1, self.tt_a1_2, self.tt_a2_1, self.tt_b1_1])
            db.session.flush()

            # 9. Substitute Faculty Adjustment: Faculty A substitutes for Faculty B on tt_b1_1
            self.adj = FacultyAdjustment(
                timetable_entry_id=self.tt_b1_1.timetable_entry_id,
                original_faculty_id=self.faculty_b.faculty_id,
                substitute_faculty_id=self.faculty_a.faculty_id,
                adjusted_by_user_id=self.user_admin.user_id,
                effective_date=date(2026, 10, 22),
                reason="Medical leave",
                status="APPROVED",
            )
            db.session.add(self.adj)
            db.session.flush()

            # 10. Attendance Sessions for A1
            # Closed session 1: 2 students eligible; 2 present -> 100%
            self.sess_closed_1 = AttendanceSession(
                offering_id=self.offering_a1.offering_id,
                faculty_id=self.faculty_a.faculty_id,
                session_date=date(2026, 10, 12),
                start_time=time(9, 0),
                end_time=time(10, 0),
                status="CLOSED",
            )
            # Closed session 2: 2 students eligible; 1 present, 1 absent -> 50%
            self.sess_closed_2 = AttendanceSession(
                offering_id=self.offering_a1.offering_id,
                faculty_id=self.faculty_a.faculty_id,
                session_date=date(2026, 10, 14),
                start_time=time(10, 0),
                end_time=time(11, 0),
                status="CLOSED",
            )
            # Active session: not closed -> must be excluded from completed attendance metrics
            self.sess_active = AttendanceSession(
                offering_id=self.offering_a1.offering_id,
                faculty_id=self.faculty_a.faculty_id,
                session_date=date(2026, 10, 19),
                start_time=time(9, 0),
                status="ACTIVE",
            )
            db.session.add_all([self.sess_closed_1, self.sess_closed_2, self.sess_active])
            db.session.flush()

            # Attendance records for Session 1 (both present)
            rec1 = AttendanceRecord(
                session_id=self.sess_closed_1.session_id,
                student_id=self.student_1.student_id,
                status="PRESENT",
            )
            rec2 = AttendanceRecord(
                session_id=self.sess_closed_1.session_id,
                student_id=self.student_2.student_id,
                status="PRESENT",
            )
            # Attendance records for Session 2 (1 present, 1 absent)
            rec3 = AttendanceRecord(
                session_id=self.sess_closed_2.session_id,
                student_id=self.student_1.student_id,
                status="PRESENT",
            )
            rec4 = AttendanceRecord(
                session_id=self.sess_closed_2.session_id,
                student_id=self.student_2.student_id,
                status="ABSENT",
            )
            db.session.add_all([rec1, rec2, rec3, rec4])
            db.session.commit()

            # Store scalar IDs to prevent DetachedInstanceError across test client sessions
            self.offering_a1_id = self.offering_a1.offering_id
            self.offering_a2_id = self.offering_a2.offering_id
            self.offering_a3_id = self.offering_a3.offering_id
            self.offering_b1_id = self.offering_b1.offering_id
            self.course_os_id = self.course_os.course_id
            self.tt_a1_1_id = self.tt_a1_1.timetable_entry_id
            self.tt_a1_2_id = self.tt_a1_2.timetable_entry_id
            self.tt_a2_1_id = self.tt_a2_1.timetable_entry_id
            self.tt_b1_1_id = self.tt_b1_1.timetable_entry_id

            # Generate tokens
            self.token_faculty_a = create_access_token(
                identity=str(self.user_faculty_a.user_id),
                additional_claims={"role": "FACULTY"},
            )
            self.token_faculty_b = create_access_token(
                identity=str(self.user_faculty_b.user_id),
                additional_claims={"role": "FACULTY"},
            )
            self.token_student = create_access_token(
                identity=str(self.user_student_1.user_id),
                additional_claims={"role": "STUDENT"},
            )

    def auth_headers(self, token):
        return {"Authorization": f"Bearer {token}"}

    def test_faculty_a_retrieves_only_own_offerings(self):
        """Verify Faculty A sees only their 3 assigned offerings, never Faculty B's offering."""
        res = self.client.get(
            "/api/faculty/courses",
            headers=self.auth_headers(self.token_faculty_a),
        )
        self.assertEqual(res.status_code, 200)
        body = res.get_json()
        self.assertTrue(body["success"])
        offerings = body["data"]

        # Faculty A has 3 offerings
        self.assertEqual(len(offerings), 3)
        offering_ids = {o["offering_id"] for o in offerings}
        self.assertIn(self.offering_a1_id, offering_ids)
        self.assertIn(self.offering_a2_id, offering_ids)
        self.assertIn(self.offering_a3_id, offering_ids)
        # Never includes Faculty B's offering
        self.assertNotIn(self.offering_b1_id, offering_ids)

    def test_faculty_offerings_student_count_and_room_fallback(self):
        """Verify active student counts and room fallback to timetable entry."""
        res = self.client.get(
            "/api/faculty/courses",
            headers=self.auth_headers(self.token_faculty_a),
        )
        self.assertEqual(res.status_code, 200)
        offerings = {o["offering_id"]: o for o in res.get_json()["data"]}

        # Offering A1 has 2 active students and room LH-101
        self.assertEqual(offerings[self.offering_a1_id]["student_count"], 2)
        self.assertEqual(offerings[self.offering_a1_id]["room"], "LH-101")

        # Offering A2 has 1 active student (dropped student excluded) and room LH-102 (from timetable)
        self.assertEqual(offerings[self.offering_a2_id]["student_count"], 1)
        self.assertEqual(offerings[self.offering_a2_id]["room"], "LH-102")

        # Offering A3 has 0 students
        self.assertEqual(offerings[self.offering_a3_id]["student_count"], 0)

    def test_faculty_courses_filtering_by_semester(self):
        """Verify semester query filter on get_faculty_courses."""
        res = self.client.get(
            "/api/faculty/courses?semester=7",
            headers=self.auth_headers(self.token_faculty_a),
        )
        self.assertEqual(res.status_code, 200)
        data = res.get_json()["data"]
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["offering_id"], self.offering_a3_id)

    def test_faculty_classes_summary_metrics(self):
        """Verify the dedicated classes summary endpoint matches database counts."""
        res = self.client.get(
            "/api/faculty/classes/summary",
            headers=self.auth_headers(self.token_faculty_a),
        )
        self.assertEqual(res.status_code, 200)
        summary = res.get_json()["data"]

        # Distinct courses: CS301 (offerings A1, A2) and CS302 (offering A3) -> 2 distinct courses
        self.assertEqual(summary["assigned_courses_count"], 2)
        self.assertEqual(summary["total_offerings_count"], 3)

        # Unique active students: Student 1 (in A1, A2) and Student 2 (in A1) -> 2 unique students
        self.assertEqual(summary["enrolled_students_count"], 2)
        self.assertEqual(summary["total_enrollments_count"], 3)

        # Weekly timetable slots: A1 (2 slots) + A2 (1 slot) + Substitute slot on B1 (1 slot) -> 4 slots
        self.assertEqual(summary["weekly_timetable_slots"], 4)
        self.assertEqual(summary["weekly_hours"], 4)
        self.assertEqual(summary["active_semesters_count"], 2)

        # Attendance:
        # Closed session 1: 2 eligible, 2 present
        # Closed session 2: 2 eligible, 1 present, 1 absent
        # Total possible: 4; Total present: 3; Percentage: 3/4 * 100 = 75.0%
        self.assertEqual(summary["total_closed_sessions"], 2)
        self.assertEqual(summary["total_present"], 3)
        self.assertEqual(summary["total_absent"], 1)
        self.assertEqual(summary["total_eligible_opportunities"], 4)
        self.assertEqual(summary["overall_attendance_percentage"], 75.0)

    def test_summary_zero_sessions_returns_none(self):
        """Verify that a faculty with 0 closed sessions gets overall_attendance_percentage: None (not 0.0)."""
        res = self.client.get(
            "/api/faculty/classes/summary",
            headers=self.auth_headers(self.token_faculty_b),
        )
        self.assertEqual(res.status_code, 200)
        summary = res.get_json()["data"]
        self.assertEqual(summary["total_closed_sessions"], 0)
        self.assertIsNone(summary["overall_attendance_percentage"])

    def test_analytics_attendance_zero_sessions_returns_none(self):
        """Verify attendance analytics returns None for offerings with no completed sessions."""
        res = self.client.get(
            "/api/faculty/attendance/analytics",
            headers=self.auth_headers(self.token_faculty_a),
        )
        self.assertEqual(res.status_code, 200)
        courses = {c["offering_id"]: c for c in res.get_json()["data"]["courses"]}

        # Offering A1 has 2 closed sessions: 3/4 = 75.0%
        self.assertEqual(courses[self.offering_a1_id]["total_sessions"], 2)
        self.assertEqual(courses[self.offering_a1_id]["attendance_percentage"], 75.0)
        self.assertTrue(courses[self.offering_a1_id]["has_sessions"])

        # Offering A2 has 0 closed sessions -> attendance_percentage must be None, NOT 0.0
        self.assertEqual(courses[self.offering_a2_id]["total_sessions"], 0)
        self.assertIsNone(courses[self.offering_a2_id]["attendance_percentage"])
        self.assertFalse(courses[self.offering_a2_id]["has_sessions"])

    def test_faculty_timetable_includes_assigned_and_substitute_entries(self):
        """Verify timetable endpoint includes offering entries and substitute adjustment entries."""
        res = self.client.get(
            "/api/timetable/faculty",
            headers=self.auth_headers(self.token_faculty_a),
        )
        self.assertEqual(res.status_code, 200)
        entries = res.get_json()["data"]

        # Should contain 4 entries: A1 (Mon, Wed), A2 (Tue), and B1 substitute (Thu)
        self.assertEqual(len(entries), 4)
        entry_ids = {e["timetable_entry_id"] for e in entries}
        self.assertIn(self.tt_a1_1_id, entry_ids)
        self.assertIn(self.tt_a1_2_id, entry_ids)
        self.assertIn(self.tt_a2_1_id, entry_ids)
        self.assertIn(self.tt_b1_1_id, entry_ids)

        # Substitute entry displays substitute faculty name
        sub_entry = next(e for e in entries if e["timetable_entry_id"] == self.tt_b1_1_id)
        self.assertEqual(sub_entry["effective_faculty_name"], "Prof. Alice Smith")
        self.assertIsNotNone(sub_entry["active_adjustment"])

    def test_unscheduled_offering_handled_gracefully(self):
        """Verify an offering with no timetable entry filters to an empty list without error."""
        res = self.client.get(
            f"/api/timetable/faculty?offering_id={self.offering_a3_id}",
            headers=self.auth_headers(self.token_faculty_a),
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.get_json()["data"], [])

    def test_authorization_non_faculty_rejected(self):
        """Verify student or unauthenticated users cannot access faculty endpoints."""
        # Unauthenticated
        res_unauth = self.client.get("/api/faculty/courses")
        self.assertEqual(res_unauth.status_code, 401)

        res_summary_unauth = self.client.get("/api/faculty/classes/summary")
        self.assertEqual(res_summary_unauth.status_code, 401)

        # Student token -> 403 Forbidden
        res_stu = self.client.get(
            "/api/faculty/courses",
            headers=self.auth_headers(self.token_student),
        )
        self.assertEqual(res_stu.status_code, 403)

        res_stu_sum = self.client.get(
            "/api/faculty/classes/summary",
            headers=self.auth_headers(self.token_student),
        )
        self.assertEqual(res_stu_sum.status_code, 403)

    def test_faculty_cannot_view_another_faculty_course_details(self):
        """Verify Faculty A cannot access course details for an unassigned course."""
        # Faculty A does not teach CS303 (Operating Systems)
        res = self.client.get(
            f"/api/faculty/courses/{self.course_os_id}",
            headers=self.auth_headers(self.token_faculty_a),
        )
        self.assertEqual(res.status_code, 404)
        self.assertFalse(res.get_json()["success"])


if __name__ == "__main__":
    unittest.main()
