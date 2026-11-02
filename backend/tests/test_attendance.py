
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
from app.routes.attendance import attendance_bp


class TestAttendanceSessionClosure(unittest.TestCase):
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
        cls.app.register_blueprint(attendance_bp)

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
            self.department = Department(
                department_name="Computer Science",
                department_code="CSE",
            )
            db.session.add(self.department)
            db.session.flush()

            faculty_user = User(
                name="Test Faculty",
                email="faculty@test.local",
                password_hash="test-password",
                role="FACULTY",
            )
            student_user_1 = User(
                name="Present Student",
                email="present@test.local",
                password_hash="test-password",
                role="STUDENT",
            )
            student_user_2 = User(
                name="Absent Student",
                email="absent@test.local",
                password_hash="test-password",
                role="STUDENT",
            )
            student_user_3 = User(
                name="Inactive Enrollment Student",
                email="inactive@test.local",
                password_hash="test-password",
                role="STUDENT",
            )

            db.session.add_all([
                faculty_user,
                student_user_1,
                student_user_2,
                student_user_3,
            ])
            db.session.flush()

            self.faculty = Faculty(
                user_id=faculty_user.user_id,
                department_id=self.department.department_id,
                employee_id="FAC-TEST-001",
                designation="Lecturer",
            )

            self.student_1 = Student(
                user_id=student_user_1.user_id,
                department_id=self.department.department_id,
                enrollment_no="STU-TEST-001",
                semester=6,
                section="A",
                academic_year="2026-27",
            )
            self.student_2 = Student(
                user_id=student_user_2.user_id,
                department_id=self.department.department_id,
                enrollment_no="STU-TEST-002",
                semester=6,
                section="A",
                academic_year="2026-27",
            )
            self.student_3 = Student(
                user_id=student_user_3.user_id,
                department_id=self.department.department_id,
                enrollment_no="STU-TEST-003",
                semester=6,
                section="A",
                academic_year="2026-27",
            )

            db.session.add_all([
                self.faculty,
                self.student_1,
                self.student_2,
                self.student_3,
            ])
            db.session.flush()
            self.faculty_id = self.faculty.faculty_id

            self.course = Course(
                department_id=self.department.department_id,
                course_code="TEST-101",
                course_name="Test Course",
                semester=6,
                credits=3,
            )
            db.session.add(self.course)
            db.session.flush()

            self.offering = CourseOffering(
                course_id=self.course.course_id,
                faculty_id=self.faculty_id,
                academic_year="2026-27",
                semester=6,
                section="A",
                room="TEST-ROOM",
            )
            db.session.add(self.offering)
            db.session.flush()

            self.session = AttendanceSession(
                offering_id=self.offering.offering_id,
                faculty_id=self.faculty_id,
                session_date=date(2026, 10, 9),
                start_time=time(9, 0),
                status="ACTIVE",
            )
            db.session.add(self.session)
            db.session.flush()

            self.enrollment_1 = Enrollment(
                student_id=self.student_1.student_id,
                offering_id=self.offering.offering_id,
                status="ACTIVE",
            )
            self.enrollment_2 = Enrollment(
                student_id=self.student_2.student_id,
                offering_id=self.offering.offering_id,
                status="ACTIVE",
            )
            self.enrollment_3 = Enrollment(
                student_id=self.student_3.student_id,
                offering_id=self.offering.offering_id,
                status="INACTIVE",
            )

            db.session.add_all([
                self.enrollment_1,
                self.enrollment_2,
                self.enrollment_3,
            ])

            # Student 1 was recognized and marked PRESENT.
            self.present_record = AttendanceRecord(
                session_id=self.session.session_id,
                student_id=self.student_1.student_id,
                status="PRESENT",
                recognition_method="FACE",
                confidence_score=0.99,
            )

            db.session.add(self.present_record)
            db.session.commit()

            self.session_id = self.session.session_id
            self.faculty_id = self.faculty.faculty_id
            self.present_student_id = self.student_1.student_id
            self.absent_student_id = self.student_2.student_id
            self.inactive_student_id = self.student_3.student_id
            self.faculty_user_id = faculty_user.user_id

    def tearDown(self):
        with self.app.app_context():
            db.session.rollback()
            db.session.remove()

    def _faculty_headers(self):
        with self.app.app_context():
            token = create_access_token(
                identity=str(self.faculty_user_id),
                additional_claims={"role": "FACULTY"},
            )

        return {"Authorization": f"Bearer {token}"}

    def test_close_marks_unrecorded_active_student_absent(self):
        response = self.client.post(
            f"/api/faculty/attendance/sessions/{self.session_id}/close",
            headers=self._faculty_headers(),
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["data"]["status"], "CLOSED")

        with self.app.app_context():
            absent_record = AttendanceRecord.query.filter_by(
                session_id=self.session_id,
                student_id=self.absent_student_id,
            ).first()

            self.assertIsNotNone(absent_record)
            self.assertEqual(absent_record.status, "ABSENT")
            self.assertEqual(absent_record.recognition_method, "SYSTEM")

    def test_close_preserves_existing_present_record(self):
        response = self.client.post(
            f"/api/faculty/attendance/sessions/{self.session_id}/close",
            headers=self._faculty_headers(),
        )

        self.assertEqual(response.status_code, 200)

        with self.app.app_context():
            records = AttendanceRecord.query.filter_by(
                session_id=self.session_id,
                student_id=self.present_student_id,
            ).all()

            self.assertEqual(len(records), 1)
            self.assertEqual(records[0].status, "PRESENT")
            self.assertEqual(records[0].recognition_method, "FACE")

    def test_close_does_not_mark_inactive_enrollment_absent(self):
        response = self.client.post(
            f"/api/faculty/attendance/sessions/{self.session_id}/close",
            headers=self._faculty_headers(),
        )

        self.assertEqual(response.status_code, 200)

        with self.app.app_context():
            inactive_record = AttendanceRecord.query.filter_by(
                session_id=self.session_id,
                student_id=self.inactive_student_id,
            ).first()

            self.assertIsNone(inactive_record)

    def test_closing_already_closed_session_returns_conflict(self):
        first_response = self.client.post(
            f"/api/faculty/attendance/sessions/{self.session_id}/close",
            headers=self._faculty_headers(),
        )
        self.assertEqual(first_response.status_code, 200)

        second_response = self.client.post(
            f"/api/faculty/attendance/sessions/{self.session_id}/close",
            headers=self._faculty_headers(),
        )

        self.assertEqual(second_response.status_code, 409)


if __name__ == "__main__":
    unittest.main()
