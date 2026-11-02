
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
    User,
)
from app.routes.reports import reports_bp


class TestAttendanceReports(unittest.TestCase):
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
        cls.app.register_blueprint(reports_bp)

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

            department = Department(
                department_name="Computer Science",
                department_code="CSE",
            )
            db.session.add(department)
            db.session.flush()

            faculty_user = User(
                name="Test Faculty",
                email="faculty@test.local",
                password_hash="test-password",
                role="FACULTY",
            )
            student_user = User(
                name="Test Student",
                email="student@test.local",
                password_hash="test-password",
                role="STUDENT",
            )
            db.session.add_all([faculty_user, student_user])
            db.session.flush()

            self.faculty = Faculty(
                user_id=faculty_user.user_id,
                department_id=department.department_id,
                employee_id="FAC-REPORT-001",
                designation="Lecturer",
            )
            student = Student(
                user_id=student_user.user_id,
                department_id=department.department_id,
                enrollment_no="STU-REPORT-001",
                semester=6,
                section="A",
                academic_year="2026-27",
            )
            db.session.add_all([self.faculty, student])
            db.session.flush()

            course = Course(
                department_id=department.department_id,
                course_code="REP-101",
                course_name="Reporting Test",
                semester=6,
                credits=3,
            )
            db.session.add(course)
            db.session.flush()

            offering = CourseOffering(
                course_id=course.course_id,
                faculty_id=self.faculty.faculty_id,
                academic_year="2026-27",
                semester=6,
                section="A",
                room="REPORT-ROOM",
            )
            db.session.add(offering)
            db.session.flush()

            db.session.add(
                Enrollment(
                    student_id=student.student_id,
                    offering_id=offering.offering_id,
                    status="ACTIVE",
                )
            )

            session_1 = AttendanceSession(
                offering_id=offering.offering_id,
                faculty_id=self.faculty.faculty_id,
                session_date=date(2026, 10, 7),
                start_time=time(9, 0),
                end_time=time(10, 0),
                status="CLOSED",
            )
            session_2 = AttendanceSession(
                offering_id=offering.offering_id,
                faculty_id=self.faculty.faculty_id,
                session_date=date(2026, 10, 8),
                start_time=time(9, 0),
                end_time=time(10, 0),
                status="CLOSED",
            )
            session_3 = AttendanceSession(
                offering_id=offering.offering_id,
                faculty_id=self.faculty.faculty_id,
                session_date=date(2026, 10, 9),
                start_time=time(9, 0),
                status="ACTIVE",
            )
            db.session.add_all([session_1, session_2, session_3])
            db.session.flush()

            db.session.add(
                AttendanceRecord(
                    session_id=session_1.session_id,
                    student_id=student.student_id,
                    status="PRESENT",
                    recognition_method="FACE",
                )
            )
            db.session.add(
                AttendanceRecord(
                    session_id=session_2.session_id,
                    student_id=student.student_id,
                    status="ABSENT",
                    recognition_method="SYSTEM",
                )
            )
            db.session.commit()

            self.offering_id = offering.offering_id
            self.faculty_user_id = faculty_user.user_id
            self.faculty_id = self.faculty.faculty_id

    def tearDown(self):
        with self.app.app_context():
            db.session.rollback()
            db.session.remove()

    def _headers(self, role="FACULTY", user_id=None):
        if user_id is None:
            user_id = self.faculty_user_id

        with self.app.app_context():
            token = create_access_token(
                identity=str(user_id),
                additional_claims={"role": role},
            )

        return {"Authorization": f"Bearer {token}"}

    def test_report_counts_explicit_present_and_absent(self):
        response = self.client.get(
            "/api/faculty/attendance/reports",
            headers=self._headers(),
        )

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertTrue(payload["success"])

        report = next(
            item for item in payload["data"]
            if item["offering_id"] == self.offering_id
        )
        student_report = report["students"][0]

        self.assertEqual(report["total_sessions"], 2)
        self.assertEqual(student_report["present_sessions"], 1)
        self.assertEqual(student_report["absent_sessions"], 1)
        self.assertEqual(student_report["attendance_percentage"], 50.0)

    def test_missing_attendance_record_is_not_counted_as_confirmed_absence(self):
        with self.app.app_context():
            missing_session = AttendanceSession(
                offering_id=self.offering_id,
                faculty_id=self.faculty.faculty_id,
                session_date=date(2026, 10, 10),
                start_time=time(10, 0),
                end_time=time(11, 0),
                status="CLOSED",
            )
            db.session.add(missing_session)
            db.session.commit()

        response = self.client.get(
            "/api/faculty/attendance/reports",
            headers=self._headers(),
        )

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()

        report = next(
            item for item in payload["data"]
            if item["offering_id"] == self.offering_id
        )
        student_report = report["students"][0]

        self.assertEqual(report["total_sessions"], 3)
        self.assertEqual(student_report["present_sessions"], 1)
        self.assertEqual(student_report["absent_sessions"], 1)

    def test_date_filter_excludes_sessions_outside_range(self):
        response = self.client.get(
            "/api/faculty/attendance/reports",
            query_string={
                "offering_id": self.offering_id,
                "from_date": "2026-10-07",
                "to_date": "2026-10-07",
            },
            headers=self._headers(),
        )

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        report = payload["data"][0]

        self.assertEqual(report["total_sessions"], 1)
        self.assertEqual(report["students"][0]["present_sessions"], 1)
        self.assertEqual(report["students"][0]["absent_sessions"], 0)
        self.assertEqual(
            report["students"][0]["attendance_percentage"], 100.0
        )

    def test_invalid_date_returns_bad_request(self):
        response = self.client.get(
            "/api/faculty/attendance/reports",
            query_string={"from_date": "not-a-date"},
            headers=self._headers(),
        )

        self.assertEqual(response.status_code, 400)

    def test_reversed_date_range_returns_bad_request(self):
        response = self.client.get(
            "/api/faculty/attendance/reports",
            query_string={
                "from_date": "2026-10-09",
                "to_date": "2026-10-07",
            },
            headers=self._headers(),
        )

        self.assertEqual(response.status_code, 400)

    def test_missing_authentication_is_rejected(self):
        response = self.client.get("/api/faculty/attendance/reports")

        self.assertIn(response.status_code, (401, 422))


if __name__ == "__main__":
    unittest.main()
