import unittest
from datetime import date, datetime, time, timedelta

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
from app.routes.student import student_bp


class TestStudentCoursesIntegration(unittest.TestCase):
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
        bcrypt.init_app(cls.app)
        JWTManager(cls.app)
        cls.app.register_blueprint(student_bp)

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

            # Departments
            self.dept_cs = Department(
                department_name="Computer Science & Engineering",
                department_code="CSE",
            )
            self.dept_math = Department(
                department_name="Mathematics",
                department_code="MAT",
            )
            db.session.add_all([self.dept_cs, self.dept_math])
            db.session.flush()

            # Users
            u_stu1 = User(name="Alice Student", email="alice@test.edu", password_hash="hashed_pw", role="STUDENT")
            u_stu2 = User(name="Bob Other", email="bob@test.edu", password_hash="hashed_pw", role="STUDENT")
            u_fac = User(name="Dr. Rajesh Kumar", email="rajesh@test.edu", password_hash="hashed_pw", role="FACULTY")
            u_admin = User(name="Admin User", email="admin@test.edu", password_hash="hashed_pw", role="ADMIN")
            db.session.add_all([u_stu1, u_stu2, u_fac, u_admin])
            db.session.flush()

            self.stu1_uid = u_stu1.user_id
            self.stu2_uid = u_stu2.user_id
            self.fac_uid = u_fac.user_id
            self.admin_uid = u_admin.user_id

            # Students & Faculty profiles
            self.student1 = Student(
                user_id=u_stu1.user_id,
                department_id=self.dept_cs.department_id,
                enrollment_no="CSE2023001",
                semester=3,
                section="A",
                academic_year="2026-2027",
            )
            self.student2 = Student(
                user_id=u_stu2.user_id,
                department_id=self.dept_cs.department_id,
                enrollment_no="CSE2023002",
                semester=3,
                section="B",
                academic_year="2026-2027",
            )
            self.faculty1 = Faculty(
                user_id=u_fac.user_id,
                department_id=self.dept_cs.department_id,
                employee_id="FAC001",
                designation="Associate Professor",
            )
            db.session.add_all([self.student1, self.student2, self.faculty1])
            db.session.flush()

            # Courses
            self.c_ds = Course(
                department_id=self.dept_cs.department_id,
                course_code="CSE101",
                course_name="Data Structures",
                semester=3,
                credits=4,
            )
            self.c_cn = Course(
                department_id=self.dept_cs.department_id,
                course_code="CSE102",
                course_name="Computer Networks",
                semester=5,
                credits=3,
            )
            self.c_math = Course(
                department_id=self.dept_math.department_id,
                course_code="MAT101",
                course_name="Engineering Mathematics",
                semester=3,
                credits=4,
            )
            db.session.add_all([self.c_ds, self.c_cn, self.c_math])
            db.session.flush()

            # Course offerings
            self.off1 = CourseOffering(
                course_id=self.c_ds.course_id,
                faculty_id=self.faculty1.faculty_id,
                academic_year="2026-2027",
                semester=3,
                section="A",
                room="CSE-101",
            )
            self.off2 = CourseOffering(
                course_id=self.c_cn.course_id,
                faculty_id=self.faculty1.faculty_id,
                academic_year="2026-2027",
                semester=5,
                section="B",
                room="CSE-102",
            )
            self.off_bob = CourseOffering(
                course_id=self.c_math.course_id,
                faculty_id=self.faculty1.faculty_id,
                academic_year="2026-2027",
                semester=3,
                section="C",
                room="MAT-201",
            )
            db.session.add_all([self.off1, self.off2, self.off_bob])
            db.session.flush()

            # Enrollments (Student1 has off1 and off2, Student2 has off_bob)
            enr1 = Enrollment(student_id=self.student1.student_id, offering_id=self.off1.offering_id)
            enr2 = Enrollment(student_id=self.student1.student_id, offering_id=self.off2.offering_id)
            enr_bob = Enrollment(student_id=self.student2.student_id, offering_id=self.off_bob.offering_id)
            db.session.add_all([enr1, enr2, enr_bob])
            db.session.flush()

            # Timetable entries for off1: Mon, Wed, Fri 09:00 - 10:00
            tt1 = TimetableEntry(
                offering_id=self.off1.offering_id,
                day_of_week="Monday",
                start_time=time(9, 0),
                end_time=time(10, 0),
                room="CSE-101",
            )
            tt2 = TimetableEntry(
                offering_id=self.off1.offering_id,
                day_of_week="Wednesday",
                start_time=time(9, 0),
                end_time=time(10, 0),
                room="CSE-101",
            )
            tt3 = TimetableEntry(
                offering_id=self.off1.offering_id,
                day_of_week="Friday",
                start_time=time(9, 0),
                end_time=time(10, 0),
                room="CSE-101",
            )
            # Timetable entry for today's weekday
            today_day = datetime.now().strftime("%A")
            tt_today = TimetableEntry(
                offering_id=self.off2.offering_id,
                day_of_week=today_day,
                start_time=time(14, 0),
                end_time=time(15, 0),
                room="CSE-102",
            )
            db.session.add_all([tt1, tt2, tt3, tt_today])
            db.session.flush()

            # Attendance sessions for off1: 2 closed sessions, student present for 1
            sess1 = AttendanceSession(
                offering_id=self.off1.offering_id,
                faculty_id=self.faculty1.faculty_id,
                session_date=date(2026, 10, 20),
                start_time=time(9, 0),
                status="CLOSED",
            )
            sess2 = AttendanceSession(
                offering_id=self.off1.offering_id,
                faculty_id=self.faculty1.faculty_id,
                session_date=date(2026, 10, 22),
                start_time=time(9, 0),
                status="CLOSED",
            )
            db.session.add_all([sess1, sess2])
            db.session.flush()

            rec1 = AttendanceRecord(
                session_id=sess1.session_id,
                student_id=self.student1.student_id,
                status="PRESENT",
            )
            rec2 = AttendanceRecord(
                session_id=sess2.session_id,
                student_id=self.student1.student_id,
                status="ABSENT",
            )
            db.session.add_all([rec1, rec2])
            db.session.commit()

            self.off1_id = self.off1.offering_id
            self.off2_id = self.off2.offering_id
            self.off_bob_id = self.off_bob.offering_id

    def _headers(self, user_id, role="STUDENT"):
        with self.app.app_context():
            token = create_access_token(
                identity=str(user_id),
                additional_claims={"role": role},
            )
            return {"Authorization": f"Bearer {token}"}

    def test_get_student_courses_success_payload(self):
        """Student courses returns enriched data, stats, timetable, and departments."""
        headers = self._headers(self.stu1_uid, role="STUDENT")
        res = self.client.get("/api/student/courses", headers=headers)
        self.assertEqual(res.status_code, 200)

        json_data = res.get_json()
        self.assertTrue(json_data["success"])
        courses = json_data["data"]
        self.assertEqual(len(courses), 2)

        # Check course structure
        ds = next(c for c in courses if c["course_code"] == "CSE101")
        self.assertEqual(ds["course_name"], "Data Structures")
        self.assertEqual(ds["credits"], 4)
        self.assertEqual(ds["semester"], 3)
        self.assertEqual(ds["section"], "A")
        self.assertEqual(ds["department"]["department_name"], "Computer Science & Engineering")
        self.assertEqual(ds["faculty"]["name"], "Dr. Rajesh Kumar")
        self.assertEqual(ds["faculty"]["designation"], "Associate Professor")
        self.assertIn("Mon, Wed, Fri", ds["schedule_summary"])
        self.assertEqual(len(ds["schedules"]), 3)

        # Check attendance calculation
        self.assertEqual(ds["attendance"]["total_sessions"], 2)
        self.assertEqual(ds["attendance"]["present_sessions"], 1)
        self.assertEqual(ds["attendance"]["absent_sessions"], 1)
        self.assertEqual(ds["attendance"]["attendance_percentage"], 50.0)

        # Check stats payload
        stats = json_data["stats"]
        self.assertEqual(stats["total_courses"], 2)
        self.assertEqual(stats["completed_classes_semester"], 2)
        self.assertEqual(stats["overall_attendance_rate"], 50.0)
        self.assertTrue(stats["has_attendance_data"])
        self.assertGreater(stats["upcoming_classes_7_days"], 0)

        # Check today schedule
        today_sched = json_data["today_schedule"]
        self.assertTrue(any(e["course_code"] == "CSE102" for e in today_sched))

        # Check departments & semesters filter lists
        depts = json_data["departments"]
        self.assertEqual(len(depts), 1)
        self.assertEqual(depts[0]["department_code"], "CSE")

        semesters = json_data["semesters"]
        self.assertEqual(semesters, [3, 5])

    def test_filter_by_semester(self):
        """Filtering by semester returns only courses in that semester."""
        headers = self._headers(self.stu1_uid, role="STUDENT")
        res = self.client.get("/api/student/courses?semester=3", headers=headers)
        self.assertEqual(res.status_code, 200)

        courses = res.get_json()["data"]
        self.assertEqual(len(courses), 1)
        self.assertEqual(courses[0]["course_code"], "CSE101")

        # Stats still preserve overall enrolled counts
        self.assertEqual(res.get_json()["stats"]["total_courses"], 2)

    def test_filter_by_search(self):
        """Search matches course code, course name, and faculty name."""
        headers = self._headers(self.stu1_uid, role="STUDENT")
        res = self.client.get("/api/student/courses?search=networks", headers=headers)
        self.assertEqual(res.status_code, 200)

        courses = res.get_json()["data"]
        self.assertEqual(len(courses), 1)
        self.assertEqual(courses[0]["course_code"], "CSE102")

    def test_invalid_query_parameters(self):
        """Invalid non-integer semester returns 400."""
        headers = self._headers(self.stu1_uid, role="STUDENT")
        res = self.client.get("/api/student/courses?semester=invalid", headers=headers)
        self.assertEqual(res.status_code, 400)
        self.assertIn("Invalid semester", res.get_json()["message"])

    def test_course_detail_success_for_enrolled_student(self):
        """Student can view detail for course offering they are enrolled in."""
        headers = self._headers(self.stu1_uid, role="STUDENT")
        res = self.client.get(f"/api/student/courses/{self.off1_id}", headers=headers)
        self.assertEqual(res.status_code, 200)

        c = res.get_json()["data"]
        self.assertEqual(c["course_code"], "CSE101")
        self.assertEqual(c["department"]["department_name"], "Computer Science & Engineering")
        self.assertEqual(c["attendance"]["attendance_percentage"], 50.0)

    def test_course_detail_forbidden_for_non_enrolled_student(self):
        """Student cannot view detail for course offering they are NOT enrolled in."""
        headers = self._headers(self.stu1_uid, role="STUDENT")
        # off_bob belongs to student2
        res = self.client.get(f"/api/student/courses/{self.off_bob_id}", headers=headers)
        self.assertEqual(res.status_code, 403)
        self.assertIn("not enrolled", res.get_json()["message"])

    def test_course_detail_not_found(self):
        """Non-existent offering returns 404."""
        headers = self._headers(self.stu1_uid, role="STUDENT")
        res = self.client.get("/api/student/courses/999999", headers=headers)
        self.assertEqual(res.status_code, 404)

    def test_unauthenticated_request_rejected(self):
        """Unauthenticated request returns 401."""
        res = self.client.get("/api/student/courses")
        self.assertEqual(res.status_code, 401)

    def test_faculty_role_forbidden_from_student_courses(self):
        """Faculty cannot access student courses."""
        headers = self._headers(self.fac_uid, role="FACULTY")
        res = self.client.get("/api/student/courses", headers=headers)
        self.assertEqual(res.status_code, 403)


if __name__ == "__main__":
    unittest.main()
