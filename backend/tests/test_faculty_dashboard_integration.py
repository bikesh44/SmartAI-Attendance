import unittest
import uuid
from datetime import date, time, datetime

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


class TestFacultyDashboardIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = Flask(__name__)
        cls.app.config.update(
            TESTING=True,
            SECRET_KEY="test-secret-dashboard-integration",
            JWT_SECRET_KEY="test-jwt-secret-key-dashboard-32b",
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
            db.session.query(AttendanceRecord).delete()
            db.session.query(AttendanceSession).delete()
            db.session.query(TimetableEntry).delete()
            db.session.query(Enrollment).delete()
            db.session.query(Student).delete()
            db.session.query(CourseOffering).delete()
            db.session.query(Course).delete()
            db.session.query(Faculty).delete()
            db.session.query(User).delete()
            db.session.query(Department).delete()
            db.session.commit()

            # Create Department
            self.dept = Department(department_name="Computer Science", department_code="CSE")
            db.session.add(self.dept)
            db.session.flush()

            # Create Faculty 1 (Dr. Raheem - active teacher with courses and closed sessions)
            self.user_f1 = User(
                email="raheem@university.edu",
                password_hash=bcrypt.generate_password_hash("password").decode("utf-8"),
                role="FACULTY",
                name="Dr. Abdul Raheem",
                is_active=True,
            )
            db.session.add(self.user_f1)
            db.session.flush()

            self.fac1 = Faculty(
                user_id=self.user_f1.user_id,
                department_id=self.dept.department_id,
                employee_id="FAC-RAHEEM-01",
                designation="Professor",
            )
            db.session.add(self.fac1)
            db.session.flush()

            # Create Faculty 2 (New Faculty - newly created account, 0 sessions)
            self.user_f2 = User(
                email="newfaculty@university.edu",
                password_hash=bcrypt.generate_password_hash("password").decode("utf-8"),
                role="FACULTY",
                name="Dr. New Faculty",
                is_active=True,
            )
            db.session.add(self.user_f2)
            db.session.flush()

            self.fac2 = Faculty(
                user_id=self.user_f2.user_id,
                department_id=self.dept.department_id,
                employee_id="FAC-NEW-02",
                designation="Assistant Professor",
            )
            db.session.add(self.fac2)
            db.session.flush()

            # Courses
            self.course1 = Course(
                course_code="CS-301",
                course_name="Database Systems",
                department_id=self.dept.department_id,
                semester=5,
                credits=3,
                is_active=True,
            )
            self.course2 = Course(
                course_code="CS-401",
                course_name="Machine Learning",
                department_id=self.dept.department_id,
                semester=7,
                credits=4,
                is_active=True,
            )
            db.session.add_all([self.course1, self.course2])
            db.session.flush()

            # Offerings for Faculty 1
            self.offering_f1 = CourseOffering(
                course_id=self.course1.course_id,
                faculty_id=self.fac1.faculty_id,
                semester=5,
                section="A",
                academic_year="2025-2026",
                room="LAB-101",
            )
            db.session.add(self.offering_f1)

            # Offerings for Faculty 2
            self.offering_f2 = CourseOffering(
                course_id=self.course2.course_id,
                faculty_id=self.fac2.faculty_id,
                semester=7,
                section="B",
                academic_year="2025-2026",
                room="HALL-202",
            )
            db.session.add(self.offering_f2)
            db.session.flush()

            # Timetable for Faculty 1
            today_weekday = datetime.now().strftime("%A")
            self.tt_f1 = TimetableEntry(
                offering_id=self.offering_f1.offering_id,
                faculty_id=self.fac1.faculty_id,
                day_of_week=today_weekday,
                start_time=time(9, 0),
                end_time=time(10, 0),
                room="LAB-101",
            )
            db.session.add(self.tt_f1)

            # 4 Students for Faculty 1's offering
            self.students = []
            for i in range(1, 5):
                u = User(
                    email=f"student{i}@university.edu",
                    password_hash=bcrypt.generate_password_hash("password").decode("utf-8"),
                    role="STUDENT",
                    name=f"Student {i}",
                    is_active=True,
                )
                db.session.add(u)
                db.session.flush()
                st = Student(
                    user_id=u.user_id,
                    department_id=self.dept.department_id,
                    enrollment_no=f"ENR-00{i}",
                    semester=5,
                    section="A",
                    academic_year="2025-2026",
                )
                db.session.add(st)
                db.session.flush()
                enr = Enrollment(
                    student_id=st.student_id,
                    offering_id=self.offering_f1.offering_id,
                    status="ACTIVE",
                )
                db.session.add(enr)
                self.students.append(st)

            # 1 Closed Session for Faculty 1:
            # 3 Present, 1 Absent (75.0% attendance)
            self.session_f1_closed = AttendanceSession(
                offering_id=self.offering_f1.offering_id,
                faculty_id=self.fac1.faculty_id,
                session_date=date(2026, 10, 20),
                start_time=time(9, 0),
                end_time=time(10, 0),
                status="CLOSED",
            )
            db.session.add(self.session_f1_closed)
            db.session.flush()

            for i, st in enumerate(self.students):
                status_val = "PRESENT" if i < 3 else "ABSENT"
                rec = AttendanceRecord(
                    session_id=self.session_f1_closed.session_id,
                    student_id=st.student_id,
                    status=status_val,
                    marked_at=datetime.utcnow(),
                    recognition_method="FACE_AUTOMATIC" if status_val == "PRESENT" else "SYSTEM",
                )
                db.session.add(rec)

            db.session.commit()

            # Store IDs and tokens
            self.f1_user_id = self.user_f1.user_id
            self.f1_id = self.fac1.faculty_id
            self.f2_user_id = self.user_f2.user_id
            self.f2_id = self.fac2.faculty_id
            self.offering_f1_id = self.offering_f1.offering_id
            self.offering_f2_id = self.offering_f2.offering_id

            with self.app.test_request_context():
                self.token_f1 = create_access_token(
                    identity=str(self.f1_user_id),
                    additional_claims={"role": "FACULTY"},
                )
                self.token_f2 = create_access_token(
                    identity=str(self.f2_user_id),
                    additional_claims={"role": "FACULTY"},
                )

    def _headers(self, token):
        return {"Authorization": f"Bearer {token}"}

    def test_01_existing_faculty_receives_own_dashboard_and_analytics(self):
        """1. An existing faculty account receives its own dynamic dashboard data."""
        res_dash = self.client.get("/api/faculty/dashboard", headers=self._headers(self.token_f1))
        self.assertEqual(res_dash.status_code, 200)
        data = res_dash.get_json()["data"]
        self.assertEqual(data["role"], "FACULTY")
        self.assertEqual(data["faculty_id"], self.f1_id)
        self.assertEqual(data["faculty_name"], "Dr. Abdul Raheem")
        self.assertEqual(data["assigned_courses_count"], 1)
        self.assertEqual(data["todays_classes_count"], 1)
        self.assertEqual(data["has_attendance_history"], True)
        self.assertEqual(data["attendance_overview"]["closed_sessions"], 1)
        self.assertEqual(data["attendance_overview"]["present"], 3)
        self.assertEqual(data["attendance_overview"]["absent"], 1)
        self.assertEqual(data["attendance_overview"]["attendance_percentage"], 75.0)

        # Verify analytics endpoint as well
        res_analytics = self.client.get(
            "/api/faculty/attendance/analytics",
            headers=self._headers(self.token_f1),
        )
        self.assertEqual(res_analytics.status_code, 200)
        adata = res_analytics.get_json()["data"]
        self.assertEqual(adata["total_courses"], 1)
        self.assertEqual(adata["total_sessions"], 1)
        self.assertEqual(adata["total_present"], 3)
        self.assertEqual(adata["total_absent"], 1)
        self.assertEqual(adata["overall_attendance_percentage"], 75.0)
        self.assertEqual(adata["has_sessions"], True)

    def test_02_newly_created_faculty_zero_history_empty_state(self):
        """2. A newly created faculty account with no attendance history receives valid empty-state."""
        res_dash = self.client.get("/api/faculty/dashboard", headers=self._headers(self.token_f2))
        self.assertEqual(res_dash.status_code, 200)
        data = res_dash.get_json()["data"]
        self.assertEqual(data["role"], "FACULTY")
        self.assertEqual(data["faculty_id"], self.f2_id)
        self.assertEqual(data["faculty_name"], "Dr. New Faculty")
        self.assertEqual(data["assigned_courses_count"], 1)
        self.assertEqual(data["has_attendance_history"], False)
        self.assertIsNone(data["average_attendance_percentage"])
        self.assertEqual(data["attendance_overview"]["closed_sessions"], 0)
        self.assertEqual(data["attendance_overview"]["present"], 0)
        self.assertEqual(data["attendance_overview"]["absent"], 0)
        self.assertIsNone(data["attendance_overview"]["attendance_percentage"])

        # Analytics endpoint empty state
        res_analytics = self.client.get(
            "/api/faculty/attendance/analytics",
            headers=self._headers(self.token_f2),
        )
        self.assertEqual(res_analytics.status_code, 200)
        adata = res_analytics.get_json()["data"]
        self.assertEqual(adata["total_courses"], 1)
        self.assertEqual(adata["total_sessions"], 0)
        self.assertEqual(adata["total_present"], 0)
        self.assertEqual(adata["total_absent"], 0)
        self.assertIsNone(adata["overall_attendance_percentage"])
        self.assertEqual(adata["has_sessions"], False)

    def test_03_two_faculty_accounts_receive_different_data(self):
        """3. Two different faculty accounts receive different data when their assignments differ."""
        res1 = self.client.get("/api/faculty/dashboard", headers=self._headers(self.token_f1))
        res2 = self.client.get("/api/faculty/dashboard", headers=self._headers(self.token_f2))
        d1 = res1.get_json()["data"]
        d2 = res2.get_json()["data"]

        self.assertNotEqual(d1["faculty_id"], d2["faculty_id"])
        self.assertNotEqual(d1["faculty_name"], d2["faculty_name"])
        self.assertNotEqual(d1["attendance_overview"]["closed_sessions"], d2["attendance_overview"]["closed_sessions"])
        self.assertEqual(d1["attendance_overview"]["closed_sessions"], 1)
        self.assertEqual(d2["attendance_overview"]["closed_sessions"], 0)

    def test_04_cross_faculty_isolation(self):
        """4. One faculty cannot access another faculty's private analytics or dashboard."""
        # Faculty 2 trying to query offering_id owned by Faculty 1
        res = self.client.get(
            f"/api/faculty/attendance/analytics?offering_id={self.offering_f1_id}",
            headers=self._headers(self.token_f2),
        )
        # Should return 404 because offering does not belong to Faculty 2
        self.assertEqual(res.status_code, 404)

        # Faculty 1 querying own offering succeeds
        res_ok = self.client.get(
            f"/api/faculty/attendance/analytics?offering_id={self.offering_f1_id}",
            headers=self._headers(self.token_f1),
        )
        self.assertEqual(res_ok.status_code, 200)

    def test_05_dynamic_identity_from_jwt(self):
        """5. Faculty identity is derived from JWT authentication, not client parameters."""
        res = self.client.get(
            "/api/faculty/dashboard?faculty_id=9999",
            headers=self._headers(self.token_f1),
        )
        self.assertEqual(res.status_code, 200)
        # Must resolve to authenticated faculty_id, not 9999
        self.assertEqual(res.get_json()["data"]["faculty_id"], self.f1_id)

    def test_06_unauthenticated_request_rejected(self):
        """6. Unauthenticated requests are rejected."""
        res_dash = self.client.get("/api/faculty/dashboard")
        self.assertIn(res_dash.status_code, (401, 422))

        res_analytics = self.client.get("/api/faculty/attendance/analytics")
        self.assertIn(res_analytics.status_code, (401, 422))


if __name__ == "__main__":
    unittest.main()
