
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
from app.routes.student_attendance import student_attendance_bp


class TestStudentAttendanceSummary(unittest.TestCase):
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

            department = Department(
                department_name="Computer Science",
                department_code="CSE",
            )
            db.session.add(department)
            db.session.flush()

            faculty_user = User(
                name="Test Faculty",
                email="faculty-summary@test.local",
                password_hash="test-password",
                role="FACULTY",
            )
            student_user = User(
                name="Test Student",
                email="student-summary@test.local",
                password_hash="test-password",
                role="STUDENT",
            )
            db.session.add_all([faculty_user, student_user])
            db.session.flush()

            faculty = Faculty(
                user_id=faculty_user.user_id,
                department_id=department.department_id,
                employee_id="FAC-SUMMARY-001",
                designation="Lecturer",
            )
            student = Student(
                user_id=student_user.user_id,
                department_id=department.department_id,
                enrollment_no="STU-SUMMARY-001",
                semester=6,
                section="A",
                academic_year="2026-27",
            )
            db.session.add_all([faculty, student])
            db.session.flush()

            course = Course(
                department_id=department.department_id,
                course_code="SUM-101",
                course_name="Summary Test",
                semester=6,
                credits=3,
            )
            db.session.add(course)
            db.session.flush()

            offering = CourseOffering(
                course_id=course.course_id,
                faculty_id=faculty.faculty_id,
                academic_year="2026-27",
                semester=6,
                section="A",
                room="SUMMARY-ROOM",
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

            closed_present = AttendanceSession(
                offering_id=offering.offering_id,
                faculty_id=faculty.faculty_id,
                session_date=date(2026, 10, 7),
                start_time=time(9, 0),
                end_time=time(10, 0),
                status="CLOSED",
            )
            closed_absent = AttendanceSession(
                offering_id=offering.offering_id,
                faculty_id=faculty.faculty_id,
                session_date=date(2026, 10, 8),
                start_time=time(9, 0),
                end_time=time(10, 0),
                status="CLOSED",
            )
            active_session = AttendanceSession(
                offering_id=offering.offering_id,
                faculty_id=faculty.faculty_id,
                session_date=date(2026, 10, 9),
                start_time=time(9, 0),
                status="ACTIVE",
            )
            db.session.add_all([
                closed_present,
                closed_absent,
                active_session,
            ])
            db.session.flush()

            db.session.add_all([
                AttendanceRecord(
                    session_id=closed_present.session_id,
                    student_id=student.student_id,
                    status="PRESENT",
                    recognition_method="FACE",
                ),
                AttendanceRecord(
                    session_id=active_session.session_id,
                    student_id=student.student_id,
                    status="PRESENT",
                    recognition_method="FACE",
                ),
            ])

            db.session.commit()

            self.student_user_id = student_user.user_id
            self.offering_id = offering.offering_id

    def tearDown(self):
        with self.app.app_context():
            db.session.rollback()
            db.session.remove()

    def _headers(self):
        with self.app.app_context():
            token = create_access_token(
                identity=str(self.student_user_id),
                additional_claims={"role": "STUDENT"},
            )

        return {"Authorization": f"Bearer {token}"}

    def test_active_session_present_record_is_excluded(self):
        response = self.client.get(
            "/api/student/attendance/summary",
            headers=self._headers(),
        )

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertTrue(payload["success"])

        summary = next(
            item
            for item in payload["data"]
            if item["offering_id"] == self.offering_id
        )

        self.assertEqual(summary["total_sessions"], 2)
        self.assertEqual(summary["present_sessions"], 1)
        self.assertEqual(summary["absent_sessions"], 1)
        self.assertEqual(summary["attendance_percentage"], 50.0)

    def test_attendance_history_returns_student_records(self):
        response = self.client.get(
            "/api/student/attendance/",
            headers=self._headers(),
        )

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertTrue(payload["success"])
        self.assertIn("data", payload)
        self.assertIn("total_records", payload)
        self.assertEqual(payload["total_records"], 2)

        dates = {
            item["session_date"]
            for item in payload["data"]
        }
        self.assertEqual(
            dates,
            {"2026-10-07", "2026-10-09"},
        )

    def test_attendance_history_date_filter(self):
        response = self.client.get(
            "/api/student/attendance/?date_from=2026-10-08&date_to=2026-10-09",
            headers=self._headers(),
        )

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertTrue(payload["success"])
        self.assertEqual(payload["total_records"], 1)
        self.assertEqual(
            payload["data"][0]["session_date"],
            "2026-10-09",
        )

    def test_attendance_history_rejects_invalid_date(self):
        response = self.client.get(
            "/api/student/attendance/?date_from=invalid-date",
            headers=self._headers(),
        )

        self.assertEqual(response.status_code, 400)
        payload = response.get_json()
        self.assertFalse(payload["success"])




    def test_attendance_history_pagination(self):
        response = self.client.get(
            "/api/student/attendance/?page=1&per_page=1",
            headers=self._headers(),
        )

        self.assertEqual(response.status_code, 200)
        result = response.get_json()

        self.assertTrue(result["success"])
        self.assertEqual(result["page"], 1)
        self.assertEqual(result["per_page"], 1)
        self.assertEqual(result["total_records"], 2)
        self.assertEqual(result["total_pages"], 2)
        self.assertEqual(len(result["data"]), 1)

    def test_attendance_history_status_filter(self):
        response = self.client.get(
            "/api/student/attendance/?status=PRESENT",
            headers=self._headers(),
        )

        self.assertEqual(response.status_code, 200)
        result = response.get_json()

        self.assertTrue(result["success"])
        self.assertEqual(result["total_records"], 2)
        self.assertTrue(
            all(record["status"] == "PRESENT"
                for record in result["data"])
        )

    def test_attendance_history_rejects_invalid_status(self):
        response = self.client.get(
            "/api/student/attendance/?status=UNKNOWN",
            headers=self._headers(),
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.get_json()["success"])



    def test_attendance_history_offering_filter(self):
        response = self.client.get(
            f"/api/student/attendance/?offering_id={self.offering_id}",
            headers=self._headers(),
        )

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()

        self.assertTrue(payload["success"])
        self.assertEqual(payload["total_records"], 2)
        self.assertTrue(
            all(
                item["offering_id"] == self.offering_id
                for item in payload["data"]
            )
        )

    def test_attendance_history_course_filter(self):
        with self.app.app_context():
            offering = db.session.get(
                CourseOffering,
                self.offering_id,
            )
            course_id = offering.course_id

        response = self.client.get(
            f"/api/student/attendance/?course_id={course_id}",
            headers=self._headers(),
        )

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()

        self.assertTrue(payload["success"])
        self.assertEqual(payload["total_records"], 2)
        self.assertTrue(
            all(
                item["course_id"] == course_id
                for item in payload["data"]
            )
        )

    def test_attendance_history_rejects_invalid_pagination(self):
        response = self.client.get(
            "/api/student/attendance/?page=0",
            headers=self._headers(),
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.get_json()["success"])

    def test_attendance_history_only_returns_own_records(self):
        response = self.client.get(
            "/api/student/attendance/",
            headers=self._headers(),
        )

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()

        self.assertEqual(payload["total_records"], 2)

        with self.app.app_context():
            returned_ids = {
                item["attendance_id"]
                for item in payload["data"]
            }

            actual_ids = {
                record.attendance_id
                for record in AttendanceRecord.query.filter_by(
                    student_id=db.session.query(Student.student_id)
                    .filter_by(user_id=self.student_user_id)
                    .scalar()
                ).all()
            }

        self.assertEqual(returned_ids, actual_ids)


    def test_attendance_history_requires_authentication(self):
        response = self.client.get("/api/student/attendance/")

        self.assertEqual(response.status_code, 401)

    def test_attendance_history_rejects_wrong_role(self):
        with self.app.app_context():
            token = create_access_token(
                identity=str(self.student_user_id),
                additional_claims={"role": "FACULTY"},
            )

        response = self.client.get(
            "/api/student/attendance/",
            headers={"Authorization": f"Bearer {token}"},
        )

        self.assertEqual(response.status_code, 403)

    def test_summary_returns_zero_percentage_without_closed_sessions(self):
        with self.app.app_context():
            sessions = AttendanceSession.query.filter_by(
                offering_id=self.offering_id,
                status="CLOSED",
            ).all()

            for session in sessions:
                session.status = "ACTIVE"

            db.session.commit()

        response = self.client.get(
            "/api/student/attendance/summary",
            headers=self._headers(),
        )

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()

        self.assertTrue(payload["success"])
        self.assertEqual(payload["overall"]["total_sessions"], 0)
        self.assertEqual(payload["overall"]["present_sessions"], 0)
        self.assertEqual(payload["overall"]["absent_sessions"], 0)
        self.assertEqual(
            payload["overall"]["attendance_percentage"], 0
        )

        summary = next(
            item for item in payload["data"]
            if item["offering_id"] == self.offering_id
        )

        self.assertEqual(summary["total_sessions"], 0)
        self.assertEqual(summary["attendance_percentage"], 0)





    def test_summary_distinguishes_no_sessions_from_genuine_zero(self):
        """Verify summary distinguishes subjects with zero eligible sessions from genuine 0% attendance."""
        with self.app.app_context():
            faculty = Faculty.query.first()
            student = Student.query.filter_by(user_id=self.student_user_id).first()
            dept = Department.query.first()

            # Create a second course offering with closed sessions where student attended 0
            course_b = Course(
                course_code="BCSE-550",
                course_name="Internet of Things",
                credits=3,
                department_id=dept.department_id,
                semester=6,
            )
            db.session.add(course_b)
            db.session.flush()

            offering_b = CourseOffering(
                course_id=course_b.course_id,
                faculty_id=faculty.faculty_id,
                academic_year="2026-27",
                semester=6,
                section="A",
            )
            db.session.add(offering_b)
            db.session.flush()

            enrollment_b = Enrollment(
                student_id=student.student_id,
                offering_id=offering_b.offering_id,
                status="ACTIVE",
            )
            db.session.add(enrollment_b)
            db.session.flush()

            # Session 1 for course B: CLOSED, record is ABSENT
            sess_b1 = AttendanceSession(
                offering_id=offering_b.offering_id,
                faculty_id=faculty.faculty_id,
                session_date=date(2026, 9, 1),
                start_time=time(9, 0),
                end_time=time(10, 0),
                status="CLOSED",
            )
            db.session.add(sess_b1)
            db.session.flush()

            rec_b1 = AttendanceRecord(
                session_id=sess_b1.session_id,
                student_id=student.student_id,
                status="ABSENT",
                confidence_score=0.9,
            )
            db.session.add(rec_b1)

            # Ensure offering self.offering_id has NO closed sessions
            active_sessions = AttendanceSession.query.filter_by(offering_id=self.offering_id).all()
            for s in active_sessions:
                s.status = "ACTIVE"

            db.session.commit()

            off_b_id = offering_b.offering_id

        response = self.client.get(
            "/api/student/attendance/summary",
            headers=self._headers(),
        )

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertTrue(payload["success"])

        # Course A (self.offering_id): 0 closed sessions -> has_eligible_sessions=False, display_percentage="N/A"
        item_a = next(item for item in payload["data"] if item["offering_id"] == self.offering_id)
        self.assertEqual(item_a["total_sessions"], 0)
        self.assertFalse(item_a["has_eligible_sessions"])
        self.assertEqual(item_a["display_percentage"], "N/A")

        # Course B (off_b_id): 1 closed session, 0 attended -> genuine 0%, has_eligible_sessions=True, display_percentage="0.0%"
        item_b = next(item for item in payload["data"] if item["offering_id"] == off_b_id)
        self.assertEqual(item_b["total_sessions"], 1)
        self.assertEqual(item_b["present_sessions"], 0)
        self.assertEqual(item_b["absent_sessions"], 1)
        self.assertTrue(item_b["has_eligible_sessions"])
        self.assertEqual(item_b["attendance_percentage"], 0)
        self.assertEqual(item_b["display_percentage"], "0.0%")


if __name__ == "__main__":
    unittest.main()
