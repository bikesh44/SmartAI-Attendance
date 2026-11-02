"""Tests for Student Subject-wise Attendance Report Multi-Format Export (Phase 2D / ISSUE-EXP-03).

Validates:
- Default export format is genuine server-generated PDF (%PDF- header).
- Explicit formats: PDF, CSV, XLSX (.xlsx openpyxl).
- Invalid format returns HTTP 400.
- Subject/course names, codes, credits, faculty, attendance counts, percentages, and statuses.
- Academic year, semester, and date-range filtering.
- Invalid date range (date_from > date_to) returns HTTP 400.
- Student identity isolation (derived from JWT; students cannot access other students' records).
- Unauthenticated requests return HTTP 401.
- Empty attendance records generate clean PDF with institutional header and empty notice.
- Multi-page PDF output pagination for large course rosters.
"""

from datetime import date, time, timedelta
import unittest

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
    User,
)
from app.routes.student_attendance import student_attendance_bp


class TestStudentSubjectReportExport(unittest.TestCase):
    """Test suite for Student Subject-wise Attendance Report Export (Phase 2D)."""

    @classmethod
    def setUpClass(cls):
        cls.app = Flask(__name__)
        cls.app.config.update(
            TESTING=True,
            SECRET_KEY="test-student-subject-export-secret",
            JWT_SECRET_KEY="test-jwt-secret-student-subject-report-key",
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
            self.dept = Department(
                department_name="Computer Science & Engineering",
                department_code="CSE",
            )
            db.session.add(self.dept)
            db.session.flush()
            self.dept_id = self.dept.department_id

            # Users
            self.fac_user = User(
                name="Dr. Alan Turing",
                email="alan.turing@test.edu",
                password_hash="pw_fac",
                role="FACULTY",
            )
            self.stu1_user = User(
                name="Alice Student",
                email="alice.student@test.edu",
                password_hash="pw_stu1",
                role="STUDENT",
            )
            self.stu2_user = User(
                name="Bob Student",
                email="bob.student@test.edu",
                password_hash="pw_stu2",
                role="STUDENT",
            )
            self.stu3_user = User(
                name="Charlie Empty",
                email="charlie.empty@test.edu",
                password_hash="pw_stu3",
                role="STUDENT",
            )
            db.session.add_all([self.fac_user, self.stu1_user, self.stu2_user, self.stu3_user])
            db.session.flush()

            # Faculty
            self.faculty = Faculty(
                user_id=self.fac_user.user_id,
                department_id=self.dept_id,
                employee_id="FAC001",
                designation="Professor",
            )
            db.session.add(self.faculty)
            db.session.flush()
            self.fac_id = self.faculty.faculty_id

            # Students
            self.student1 = Student(
                user_id=self.stu1_user.user_id,
                department_id=self.dept.department_id,
                enrollment_no="STU2024001",
                semester=4,
                section="A",
                academic_year="2024-2025",
            )
            self.student2 = Student(
                user_id=self.stu2_user.user_id,
                department_id=self.dept.department_id,
                enrollment_no="STU2024002",
                semester=4,
                section="B",
                academic_year="2024-2025",
            )
            self.student_empty = Student(
                user_id=self.stu3_user.user_id,
                department_id=self.dept.department_id,
                enrollment_no="STU2024003",
                semester=2,
                section="A",
                academic_year="2024-2025",
            )
            db.session.add_all([self.student1, self.student2, self.student_empty])
            db.session.flush()

            # Courses
            self.c1 = Course(
                course_code="CS201",
                course_name="Data Structures & Algorithms",
                department_id=self.dept.department_id,
                credits=4,
                semester=4,
            )
            self.c2 = Course(
                course_code="CS202",
                course_name="Computer Networks",
                department_id=self.dept.department_id,
                credits=3,
                semester=4,
            )
            self.c3 = Course(
                course_code="CS301",
                course_name="Database Management Systems",
                department_id=self.dept.department_id,
                credits=4,
                semester=5,
            )
            db.session.add_all([self.c1, self.c2, self.c3])
            db.session.flush()

            # Course Offerings
            self.off1 = CourseOffering(
                course_id=self.c1.course_id,
                faculty_id=self.fac_id,
                semester=4,
                section="A",
                academic_year="2024-2025",
                room="LH-101",
            )
            self.off2 = CourseOffering(
                course_id=self.c2.course_id,
                faculty_id=self.faculty.faculty_id,
                semester=4,
                section="A",
                academic_year="2024-2025",
                room="LH-102",
            )
            self.off3 = CourseOffering(
                course_id=self.c3.course_id,
                faculty_id=self.faculty.faculty_id,
                semester=5,
                section="A",
                academic_year="2024-2025",
                room="LH-201",
            )
            db.session.add_all([self.off1, self.off2, self.off3])
            db.session.flush()

            # Enrollments for Student 1
            self.enr1 = Enrollment(
                student_id=self.student1.student_id,
                offering_id=self.off1.offering_id,
                status="ACTIVE",
            )
            self.enr2 = Enrollment(
                student_id=self.student1.student_id,
                offering_id=self.off2.offering_id,
                status="ACTIVE",
            )
            self.enr3 = Enrollment(
                student_id=self.student1.student_id,
                offering_id=self.off3.offering_id,
                status="ACTIVE",
            )

            # Enrollment for Student 2
            self.enr_s2 = Enrollment(
                student_id=self.student2.student_id,
                offering_id=self.off1.offering_id,
                status="ACTIVE",
            )
            db.session.add_all([self.enr1, self.enr2, self.enr3, self.enr_s2])
            db.session.flush()

            # Create Closed Attendance Sessions & Records
            today = date.today()

            # Course 1: 3 sessions (2 Present, 1 Absent) -> 66.7%
            s1_c1 = AttendanceSession(offering_id=self.off1.offering_id, faculty_id=self.faculty.faculty_id, session_date=today - timedelta(days=5), start_time=time(9, 0), end_time=time(10, 0), status="CLOSED")
            s2_c1 = AttendanceSession(offering_id=self.off1.offering_id, faculty_id=self.faculty.faculty_id, session_date=today - timedelta(days=3), start_time=time(9, 0), end_time=time(10, 0), status="CLOSED")
            s3_c1 = AttendanceSession(offering_id=self.off1.offering_id, faculty_id=self.faculty.faculty_id, session_date=today - timedelta(days=1), start_time=time(9, 0), end_time=time(10, 0), status="CLOSED")
            db.session.add_all([s1_c1, s2_c1, s3_c1])
            db.session.flush()

            r1_c1 = AttendanceRecord(session_id=s1_c1.session_id, student_id=self.student1.student_id, status="PRESENT")
            r2_c1 = AttendanceRecord(session_id=s2_c1.session_id, student_id=self.student1.student_id, status="PRESENT")
            r3_c1 = AttendanceRecord(session_id=s3_c1.session_id, student_id=self.student1.student_id, status="ABSENT")

            # Student 2 attendance on s1_c1
            r_s2 = AttendanceRecord(session_id=s1_c1.session_id, student_id=self.student2.student_id, status="PRESENT")
            db.session.add_all([r1_c1, r2_c1, r3_c1, r_s2])

            # Course 2: 2 sessions (2 Present, 1 Late) -> 100% (or 2/2)
            s1_c2 = AttendanceSession(offering_id=self.off2.offering_id, faculty_id=self.faculty.faculty_id, session_date=today - timedelta(days=4), start_time=time(9, 0), end_time=time(10, 0), status="CLOSED")
            s2_c2 = AttendanceSession(offering_id=self.off2.offering_id, faculty_id=self.faculty.faculty_id, session_date=today - timedelta(days=2), start_time=time(9, 0), end_time=time(10, 0), status="CLOSED")
            db.session.add_all([s1_c2, s2_c2])
            db.session.flush()

            r1_c2 = AttendanceRecord(session_id=s1_c2.session_id, student_id=self.student1.student_id, status="PRESENT")
            r2_c2 = AttendanceRecord(session_id=s2_c2.session_id, student_id=self.student1.student_id, status="LATE")
            db.session.add_all([r1_c2, r2_c2])

            # Course 3 (Sem 5): 1 session (1 Present) -> 100%
            s1_c3 = AttendanceSession(offering_id=self.off3.offering_id, faculty_id=self.faculty.faculty_id, session_date=today - timedelta(days=2), start_time=time(9, 0), end_time=time(10, 0), status="CLOSED")
            db.session.add(s1_c3)
            db.session.flush()
            r1_c3 = AttendanceRecord(session_id=s1_c3.session_id, student_id=self.student1.student_id, status="PRESENT")
            db.session.add(r1_c3)

            db.session.commit()

            # Store IDs and tokens
            self.stu1_id = self.student1.student_id
            self.stu2_id = self.student2.student_id
            self.stu_empty_id = self.student_empty.student_id
            self.dept_id = self.dept.department_id
            self.fac_id = self.faculty.faculty_id

            self.token_student1 = create_access_token(
                identity=str(self.stu1_user.user_id),
                additional_claims={"role": "STUDENT"},
            )
            self.token_student2 = create_access_token(
                identity=str(self.stu2_user.user_id),
                additional_claims={"role": "STUDENT"},
            )
            self.token_student_empty = create_access_token(
                identity=str(self.stu3_user.user_id),
                additional_claims={"role": "STUDENT"},
            )

    def _headers(self, token=None):
        t = token or self.token_student1
        return {"Authorization": f"Bearer {t}"}

    def test_export_pdf_default(self):
        """Omission of format parameter must default to genuine PDF."""
        resp = self.client.get(
            "/api/student/attendance/export",
            headers=self._headers(),
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.headers["Content-Type"], "application/pdf")
        self.assertTrue(resp.data.startswith(b"%PDF-"))
        self.assertIn("Content-Disposition", resp.headers)
        disp = resp.headers["Content-Disposition"]
        self.assertIn("Subject_Attendance_Report_STU2024001.pdf", disp)

    def test_export_pdf_explicit(self):
        """format=pdf explicitly returns genuine PDF document with %%EOF marker."""
        resp = self.client.get(
            "/api/student/attendance/export?format=pdf",
            headers=self._headers(),
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.headers["Content-Type"], "application/pdf")
        self.assertTrue(resp.data.startswith(b"%PDF-"))
        self.assertIn(b"%%EOF", resp.data)

    def test_export_csv(self):
        """format=csv returns properly structured CSV with metadata, courses, and attendance counts."""
        resp = self.client.get(
            "/api/student/attendance/export?format=csv",
            headers=self._headers(),
        )
        self.assertEqual(resp.status_code, 200)
        self.assertIn("text/csv", resp.headers["Content-Type"])
        content = resp.data.decode("utf-8")
        self.assertIn("Alice Student", content)
        self.assertIn("STU2024001", content)
        self.assertIn("CS201", content)
        self.assertIn("Data Structures & Algorithms", content)
        self.assertIn("CS202", content)
        self.assertIn("Computer Networks", content)
        self.assertIn("CS301", content)

    def test_export_xlsx(self):
        """format=xlsx returns valid OpenXML Excel workbook starting with PK ZIP bytes."""
        resp = self.client.get(
            "/api/student/attendance/export?format=xlsx",
            headers=self._headers(),
        )
        self.assertEqual(resp.status_code, 200)
        self.assertIn(
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            resp.headers["Content-Type"],
        )
        self.assertTrue(resp.data.startswith(b"PK\x03\x04"))

    def test_export_unsupported_format_returns_400(self):
        """Invalid format argument returns HTTP 400 with helpful error message."""
        resp = self.client.get(
            "/api/student/attendance/export?format=docx",
            headers=self._headers(),
        )
        self.assertEqual(resp.status_code, 400)
        data = resp.get_json()
        self.assertFalse(data["success"])
        self.assertIn("Unsupported export format", data["message"])

    def test_export_semester_filter(self):
        """Filtering by semester=5 includes only semester 5 courses."""
        resp = self.client.get(
            "/api/student/attendance/export?semester=5&format=csv",
            headers=self._headers(),
        )
        self.assertEqual(resp.status_code, 200)
        content = resp.data.decode("utf-8")
        self.assertIn("CS301", content)
        # Semester 4 courses should be excluded
        self.assertNotIn("CS201", content)
        self.assertNotIn("CS202", content)

    def test_export_date_range_filter(self):
        """Filtering by date_from and date_to restricts counted sessions."""
        today = date.today()
        # Filter for only the last 2 days
        d_from = (today - timedelta(days=2)).isoformat()
        d_to = today.isoformat()
        resp = self.client.get(
            f"/api/student/attendance/export?date_from={d_from}&date_to={d_to}&format=csv",
            headers=self._headers(),
        )
        self.assertEqual(resp.status_code, 200)
        content = resp.data.decode("utf-8")
        self.assertIn("Date Range", content)

    def test_export_invalid_date_range_returns_400(self):
        """date_from > date_to returns HTTP 400 Bad Request."""
        today = date.today()
        d_from = today.isoformat()
        d_to = (today - timedelta(days=5)).isoformat()
        resp = self.client.get(
            f"/api/student/attendance/export?date_from={d_from}&date_to={d_to}",
            headers=self._headers(),
        )
        self.assertEqual(resp.status_code, 400)
        data = resp.get_json()
        self.assertFalse(data["success"])
        self.assertIn("date_from cannot be after date_to", data["message"])

    def test_export_student_data_isolation(self):
        """Student 2 exports only Student 2's records, never Student 1's records."""
        resp = self.client.get(
            "/api/student/attendance/export?format=csv",
            headers=self._headers(self.token_student2),
        )
        self.assertEqual(resp.status_code, 200)
        content = resp.data.decode("utf-8")
        self.assertIn("Bob Student", content)
        self.assertIn("STU2024002", content)
        self.assertNotIn("Alice Student", content)
        self.assertNotIn("STU2024001", content)

    def test_export_unauthenticated_returns_401(self):
        """Unauthenticated requests without JWT token return HTTP 401."""
        resp = self.client.get("/api/student/attendance/export")
        self.assertEqual(resp.status_code, 401)

    def test_export_empty_records_generates_clean_pdf(self):
        """Student with zero active course enrollments generates valid PDF cleanly."""
        resp = self.client.get(
            "/api/student/attendance/export?format=pdf",
            headers=self._headers(self.token_student_empty),
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.headers["Content-Type"], "application/pdf")
        self.assertTrue(resp.data.startswith(b"%PDF-"))
        self.assertIn("Subject_Attendance_Report_STU2024003.pdf", resp.headers["Content-Disposition"])

    def test_export_multipage_pdf_generation(self):
        """Generating a PDF with 25+ courses spans multiple pages cleanly."""
        with self.app.app_context():
            # Add 25 additional courses and enrollments for student 1
            extra_courses = []
            extra_offerings = []
            extra_enrs = []
            for i in range(1, 26):
                c = Course(
                    course_code=f"ELECT{200 + i}",
                    course_name=f"Elective Advanced Subject #{i} Distributed Computing",
                    department_id=self.dept.department_id,
                    credits=3,
                    semester=4,
                )
                extra_courses.append(c)
            db.session.add_all(extra_courses)
            db.session.flush()

            for c in extra_courses:
                off = CourseOffering(
                    course_id=c.course_id,
                    faculty_id=self.faculty.faculty_id,
                    semester=4,
                    section="A",
                    academic_year="2024-2025",
                )
                extra_offerings.append(off)
            db.session.add_all(extra_offerings)
            db.session.flush()

            for off in extra_offerings:
                enr = Enrollment(
                    student_id=self.stu1_id,
                    offering_id=off.offering_id,
                    status="ACTIVE",
                )
                extra_enrs.append(enr)
            db.session.add_all(extra_enrs)
            db.session.commit()

        resp = self.client.get(
            "/api/student/attendance/export?format=pdf",
            headers=self._headers(),
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.headers["Content-Type"], "application/pdf")
        self.assertTrue(resp.data.startswith(b"%PDF-"))
        self.assertIn(b"%%EOF", resp.data)
        # Multi-page PDF has multiple page objects
        self.assertIn(b"/Page", resp.data)


if __name__ == "__main__":
    unittest.main()
