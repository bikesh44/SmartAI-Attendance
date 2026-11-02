import unittest
from datetime import date, datetime, time, timezone

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
    User,
)
from app.routes.student_attendance import student_attendance_bp
from flask import Flask
from flask_jwt_extended import JWTManager, create_access_token
from sqlalchemy.pool import StaticPool


class TestStudentAttendanceHistoryPage(unittest.TestCase):
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
                department_name="Computer Science & Engineering",
                department_code="CSE",
            )
            db.session.add(dept)
            db.session.flush()

            # Users
            fac_user = User(
                name="Prof. Alan Turing",
                email="alan@test.local",
                password_hash="test-pass",
                role="FACULTY",
            )
            stu1_user = User(
                name="Ankit Kumar",
                email="ankit@test.local",
                password_hash="test-pass",
                role="STUDENT",
            )
            stu2_user = User(
                name="Priya Sharma",
                email="priya@test.local",
                password_hash="test-pass",
                role="STUDENT",
            )
            db.session.add_all([fac_user, stu1_user, stu2_user])
            db.session.flush()

            # Faculty
            faculty = Faculty(
                user_id=fac_user.user_id,
                department_id=dept.department_id,
                employee_id="FAC-HIST-01",
                designation="Associate Professor",
            )
            # Students
            stu1 = Student(
                user_id=stu1_user.user_id,
                department_id=dept.department_id,
                enrollment_no="STU2024001",
                semester=6,
                section="A",
                academic_year="2024-2025",
            )
            stu2 = Student(
                user_id=stu2_user.user_id,
                department_id=dept.department_id,
                enrollment_no="STU2024002",
                semester=6,
                section="B",
                academic_year="2024-2025",
            )
            db.session.add_all([faculty, stu1, stu2])
            db.session.flush()

            # Courses
            c1 = Course(
                department_id=dept.department_id,
                course_code="CSE101",
                course_name="Data Structures",
                semester=6,
                credits=4,
            )
            c2 = Course(
                department_id=dept.department_id,
                course_code="CSE102",
                course_name="Computer Networks",
                semester=6,
                credits=3,
            )
            db.session.add_all([c1, c2])
            db.session.flush()

            # Course Offerings
            off1 = CourseOffering(
                course_id=c1.course_id,
                faculty_id=faculty.faculty_id,
                academic_year="2024-2025",
                semester=6,
                section="A",
                room="Room 301",
            )
            off2 = CourseOffering(
                course_id=c2.course_id,
                faculty_id=faculty.faculty_id,
                academic_year="2024-2025",
                semester=6,
                section="A",
                room="Room 302",
            )
            db.session.add_all([off1, off2])
            db.session.flush()

            # Enrollments
            e1 = Enrollment(student_id=stu1.student_id, offering_id=off1.offering_id, status="ACTIVE")
            e2 = Enrollment(student_id=stu1.student_id, offering_id=off2.offering_id, status="ACTIVE")
            e3 = Enrollment(student_id=stu2.student_id, offering_id=off1.offering_id, status="ACTIVE")
            db.session.add_all([e1, e2, e3])
            db.session.flush()

            # Sessions for off1 (Data Structures): 3 closed sessions (Morning and Afternoon)
            s1 = AttendanceSession(
                offering_id=off1.offering_id,
                faculty_id=faculty.faculty_id,
                session_date=date(2025, 5, 10),
                start_time=time(9, 0),
                end_time=time(10, 0),
                status="CLOSED",
            )
            s2 = AttendanceSession(
                offering_id=off1.offering_id,
                faculty_id=faculty.faculty_id,
                session_date=date(2025, 5, 12),
                start_time=time(14, 0),
                end_time=time(15, 0),
                status="CLOSED",
            )
            s3 = AttendanceSession(
                offering_id=off1.offering_id,
                faculty_id=faculty.faculty_id,
                session_date=date(2025, 5, 14),
                start_time=time(9, 30),
                end_time=time(10, 30),
                status="CLOSED",
            )
            # Session for off2 (Computer Networks): 1 closed session
            s4 = AttendanceSession(
                offering_id=off2.offering_id,
                faculty_id=faculty.faculty_id,
                session_date=date(2025, 5, 15),
                start_time=time(11, 0),
                end_time=time(12, 0),
                status="CLOSED",
            )
            db.session.add_all([s1, s2, s3, s4])
            db.session.flush()

            # Records for Stu1:
            # s1: PRESENT (marked at 9:02 AM)
            # s2: LATE (marked at 2:18 PM)
            # s3: ABSENT
            # s4: PRESENT (marked at 11:05 AM)
            dt_s1 = datetime(2025, 5, 10, 9, 2, tzinfo=timezone.utc).replace(tzinfo=None)
            dt_s2 = datetime(2025, 5, 12, 14, 18, tzinfo=timezone.utc).replace(tzinfo=None)
            dt_s4 = datetime(2025, 5, 15, 11, 5, tzinfo=timezone.utc).replace(tzinfo=None)

            r1 = AttendanceRecord(
                session_id=s1.session_id,
                student_id=stu1.student_id,
                status="PRESENT",
                marked_at=dt_s1,
                recognition_method="FACE",
                confidence_score=0.96,
            )
            r2 = AttendanceRecord(
                session_id=s2.session_id,
                student_id=stu1.student_id,
                status="LATE",
                marked_at=dt_s2,
                recognition_method="FACE",
                confidence_score=0.91,
            )
            r3 = AttendanceRecord(
                session_id=s3.session_id,
                student_id=stu1.student_id,
                status="ABSENT",
                marked_at=dt_s1,
                recognition_method="SYSTEM",
            )
            r4 = AttendanceRecord(
                session_id=s4.session_id,
                student_id=stu1.student_id,
                status="PRESENT",
                marked_at=dt_s4,
                recognition_method="FACE",
                confidence_score=0.98,
            )
            # Record for Stu2
            r_stu2 = AttendanceRecord(
                session_id=s1.session_id,
                student_id=stu2.student_id,
                status="PRESENT",
                marked_at=dt_s1,
                recognition_method="FACE",
            )
            db.session.add_all([r1, r2, r3, r4, r_stu2])
            db.session.commit()

            self.stu1_user_id = stu1_user.user_id
            self.stu2_user_id = stu2_user.user_id
            self.r1_id = r1.attendance_id
            self.r_stu2_id = r_stu2.attendance_id
            self.c1_id = c1.course_id
            self.off1_id = off1.offering_id

    def tearDown(self):
        with self.app.app_context():
            db.session.rollback()
            db.session.remove()

    def _headers(self, user_id=None):
        uid = user_id or self.stu1_user_id
        with self.app.app_context():
            token = create_access_token(
                identity=str(uid),
                additional_claims={"role": "STUDENT"},
            )
        return {"Authorization": f"Bearer {token}"}

    def test_attendance_history_serialization_fields(self):
        """Verify serialize_record outputs all required columns including session, timings, faculty."""
        res = self.client.get("/api/student/attendance/", headers=self._headers())
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["success"])
        self.assertEqual(data["total_records"], 4)

        # Check first record fields
        first = data["data"][0]
        self.assertIn("course_code", first)
        self.assertIn("course_name", first)
        self.assertIn("session_date", first)
        self.assertIn("status", first)
        self.assertIn("attendance_time", first)
        self.assertIn("session_name", first)
        self.assertIn("session_timing", first)
        self.assertIn("faculty_name", first)
        self.assertEqual(first["faculty_name"], "Prof. Alan Turing")

    def test_attendance_history_academic_year_and_semester_filtering(self):
        """Verify filtering by academic year and semester works properly."""
        res = self.client.get(
            "/api/student/attendance/?academic_year=2024-2025&semester=6",
            headers=self._headers(),
        )
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["total_records"], 4)

        # Non-matching semester
        res2 = self.client.get(
            "/api/student/attendance/?semester=4",
            headers=self._headers(),
        )
        self.assertEqual(res2.status_code, 200)
        self.assertEqual(res2.get_json()["total_records"], 0)

    def test_attendance_history_course_filter(self):
        """Verify filtering by course_id restricts history to that course."""
        res = self.client.get(
            f"/api/student/attendance/?course_id={self.c1_id}",
            headers=self._headers(),
        )
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["total_records"], 3)
        self.assertTrue(all(item["course_code"] == "CSE101" for item in data["data"]))

    def test_attendance_history_date_range_filter(self):
        """Verify date range filtering works properly."""
        res = self.client.get(
            "/api/student/attendance/?date_from=2025-05-11&date_to=2025-05-14",
            headers=self._headers(),
        )
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["total_records"], 2)
        dates = {item["session_date"] for item in data["data"]}
        self.assertEqual(dates, {"2025-05-12", "2025-05-14"})

    def test_attendance_summary_aggregation_and_filters(self):
        """Verify summary returns present_days, absent_days, late_days and filter_options."""
        res = self.client.get("/api/student/attendance/summary", headers=self._headers())
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["success"])

        overall = data["overall"]
        self.assertEqual(overall["total_sessions"], 4)
        self.assertEqual(overall["present_sessions"], 2)
        self.assertEqual(overall["late_sessions"], 1)
        self.assertEqual(overall["absent_sessions"], 1)
        self.assertEqual(overall["present_days"], 2)
        self.assertEqual(overall["late_days"], 1)
        self.assertEqual(overall["absent_days"], 1)

        # Check filter_options returned
        self.assertIn("filter_options", data)
        filter_options = data["filter_options"]
        self.assertIn("2024-2025", filter_options["academic_years"])
        self.assertIn(6, filter_options["semesters"])
        course_codes = [c["course_code"] for c in filter_options["courses"]]
        self.assertIn("CSE101", course_codes)
        self.assertIn("CSE102", course_codes)

    def test_attendance_summary_with_course_filter(self):
        """Verify summary calculations when filtered by course_id."""
        res = self.client.get(
            f"/api/student/attendance/summary?course_id={self.c1_id}",
            headers=self._headers(),
        )
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        overall = data["overall"]
        self.assertEqual(overall["total_sessions"], 3)
        self.assertEqual(overall["present_sessions"], 1)
        self.assertEqual(overall["late_sessions"], 1)
        self.assertEqual(overall["absent_sessions"], 1)

    def test_attendance_record_detail_endpoint(self):
        """Verify GET /api/student/attendance/<id> returns single record detail."""
        res = self.client.get(
            f"/api/student/attendance/{self.r1_id}",
            headers=self._headers(),
        )
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["success"])
        self.assertEqual(data["data"]["attendance_id"], self.r1_id)
        self.assertEqual(data["data"]["course_code"], "CSE101")
        self.assertEqual(data["data"]["status"], "PRESENT")
        self.assertEqual(data["data"]["attendance_time"], "09:02 AM")
        self.assertEqual(data["data"]["faculty_name"], "Prof. Alan Turing")
        self.assertEqual(data["data"]["room"], "Room 301")

    def test_attendance_record_detail_cross_student_access_denied(self):
        """Verify student cannot view another student's attendance detail."""
        res = self.client.get(
            f"/api/student/attendance/{self.r_stu2_id}",
            headers=self._headers(),
        )
        # Should return 404 because query filters by student_id
        self.assertEqual(res.status_code, 404)
        self.assertFalse(res.get_json()["success"])

    def test_attendance_record_detail_not_found(self):
        """Verify 404 on non-existent record."""
        res = self.client.get(
            "/api/student/attendance/999999",
            headers=self._headers(),
        )
        self.assertEqual(res.status_code, 404)

    def test_export_student_attendance_csv(self):
        """Verify GET /api/student/attendance/export generates CSV file with student attendance."""
        res = self.client.get(
            "/api/student/attendance/export?format=csv",
            headers=self._headers(),
        )
        self.assertEqual(res.status_code, 200)
        self.assertIn("text/csv", res.content_type)
        self.assertIn("attachment; filename=Subject_Attendance_Report_STU2024001.csv", res.headers.get("Content-Disposition", ""))
        data = res.get_data(as_text=True)
        self.assertIn("Ankit Kumar", data)
        self.assertIn("STU2024001", data)
        self.assertIn("Data Structures", data)
        self.assertIn("CSE101", data)
        self.assertIn("Computer Networks", data)

    def test_export_student_attendance_pdf_default(self):
        """Verify GET /api/student/attendance/export defaults to genuine PDF."""
        res = self.client.get(
            "/api/student/attendance/export",
            headers=self._headers(),
        )
        self.assertEqual(res.status_code, 200)
        self.assertIn("application/pdf", res.content_type)
        self.assertTrue(res.data.startswith(b"%PDF-"))
        self.assertIn("Subject_Attendance_Report_STU2024001.pdf", res.headers.get("Content-Disposition", ""))

    def test_export_student_attendance_unauthenticated(self):
        """Verify export rejects unauthenticated requests."""
        res = self.client.get("/api/student/attendance/export")
        self.assertEqual(res.status_code, 401)


if __name__ == "__main__":
    unittest.main()
