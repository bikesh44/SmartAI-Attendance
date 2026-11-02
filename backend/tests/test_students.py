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
    Student,
    User,
)
from app.routes.admin import admin_bp


class TestAdminStudents(unittest.TestCase):
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
        cls.app.register_blueprint(admin_bp)

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
            self.dept_id = self.department.department_id

            admin = User(
                name="Test Admin",
                email="admin@test.local",
                password_hash="not-used",
                role="ADMIN",
            )
            faculty_user = User(
                name="Test Faculty",
                email="faculty@test.local",
                password_hash="not-used",
                role="FACULTY",
            )
            student_user = User(
                name="Test Student",
                email="student@test.local",
                password_hash="not-used",
                role="STUDENT",
            )
            db.session.add_all([admin, faculty_user, student_user])
            db.session.flush()

            self.admin_token = create_access_token(
                identity=str(admin.user_id),
                additional_claims={"role": "ADMIN"},
            )
            self.faculty_token = create_access_token(
                identity=str(faculty_user.user_id),
                additional_claims={"role": "FACULTY"},
            )

            self.student = Student(
                user_id=student_user.user_id,
                department_id=self.department.department_id,
                enrollment_no="STU-001",
                semester=3,
                section="A",
                academic_year="2026-27",
            )
            self.faculty = Faculty(
                user_id=faculty_user.user_id,
                department_id=self.department.department_id,
                employee_id="FAC-001",
                designation="Lecturer",
            )
            db.session.add_all([self.student, self.faculty])
            db.session.flush()

            self.course = Course(
                department_id=self.department.department_id,
                course_code="TST101",
                course_name="Test Course",
                semester=3,
                credits=3,
            )
            db.session.add(self.course)
            db.session.flush()

            self.offering = CourseOffering(
                course_id=self.course.course_id,
                faculty_id=self.faculty.faculty_id,
                academic_year="2026-27",
                semester=3,
                section="A",
                room="R101",
            )
            db.session.add(self.offering)
            db.session.flush()

            self.session = AttendanceSession(
                offering_id=self.offering.offering_id,
                faculty_id=self.faculty.faculty_id,
                session_date=date(2026, 10, 9),
                start_time=time(9, 0),
                status="CLOSED",
            )
            db.session.add(self.session)
            db.session.flush()

            db.session.add(Enrollment(
                student_id=self.student.student_id,
                offering_id=self.offering.offering_id,
                status="ACTIVE",
            ))
            db.session.add(AttendanceRecord(
                student_id=self.student.student_id,
                session_id=self.session.session_id,
                status="PRESENT",
                recognition_method="FACE",
            ))
            db.session.commit()

            self.student_id = self.student.student_id

    def admin_headers(self):
        return {"Authorization": f"Bearer {self.admin_token}"}

    def test_list_students_includes_attendance_summary(self):
        response = self.client.get(
            "/api/admin/students",
            headers=self.admin_headers(),
        )
        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        self.assertTrue(body["success"])
        self.assertEqual(len(body["data"]), 1)

        summary = body["data"][0]["attendance_summary"]
        self.assertEqual(summary["total_sessions"], 1)
        self.assertEqual(summary["present_sessions"], 1)
        self.assertEqual(summary["absent_sessions"], 0)
        self.assertEqual(summary["attendance_percentage"], 100.0)

    def test_get_student_detail(self):
        response = self.client.get(
            f"/api/admin/students/{self.student_id}",
            headers=self.admin_headers(),
        )
        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        self.assertTrue(body["success"])
        self.assertEqual(body["data"]["enrollment_no"], "STU-001")
        self.assertIn("attendance_summary", body["data"])

    def test_missing_student_returns_404(self):
        response = self.client.get(
            "/api/admin/students/99999",
            headers=self.admin_headers(),
        )
        self.assertEqual(response.status_code, 404)
        self.assertFalse(response.get_json()["success"])

    def test_student_routes_reject_faculty_role(self):
        response = self.client.get(
            "/api/admin/students",
            headers={"Authorization": f"Bearer {self.faculty_token}"},
        )
        self.assertEqual(response.status_code, 403)

    def test_student_routes_require_authentication(self):
        response = self.client.get("/api/admin/students")
        self.assertEqual(response.status_code, 401)

    def test_update_student_rejects_user_fields(self):
        response = self.client.patch(
            f"/api/admin/students/{self.student_id}",
            headers=self.admin_headers(),
            json={"name": "Changed Name"},
        )
        self.assertEqual(response.status_code, 400)

    def test_update_missing_student_returns_404(self):
        response = self.client.patch(
            "/api/admin/students/99999",
            headers=self.admin_headers(),
            json={"section": "B"},
        )
        self.assertEqual(response.status_code, 404)

    def test_delete_student_with_attendance_is_blocked(self):
        response = self.client.delete(
            f"/api/admin/students/{self.student_id}",
            headers=self.admin_headers(),
        )
        self.assertEqual(response.status_code, 409)

    def test_delete_missing_student_returns_404(self):
        response = self.client.delete(
            "/api/admin/students/99999",
            headers=self.admin_headers(),
        )
        self.assertEqual(response.status_code, 404)

    def test_delete_user_with_attendance_deactivates_account(self):
        response = self.client.delete(
            f"/api/admin/users/{self.student.user_id}",
            headers=self.admin_headers(),
        )

        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        self.assertTrue(body["success"])
        self.assertEqual(body["action"], "deactivated")

        with self.app.app_context():
            user = db.session.get(User, self.student.user_id)
            self.assertIsNotNone(user)
            self.assertFalse(user.is_active)

            # Academic and attendance history must remain intact.
            self.assertIsNotNone(
                db.session.get(Student, self.student_id)
            )
            self.assertIsNotNone(
                AttendanceRecord.query.filter_by(
                    student_id=self.student_id
                ).first()
            )
            self.assertIsNotNone(
                Enrollment.query.filter_by(
                    student_id=self.student_id
                ).first()
            )

    def test_delete_user_without_profile_permanently_deletes_account(self):
        with self.app.app_context():
            user = User(
                name="Temporary User",
                email="temporary@test.local",
                password_hash="not-used",
                role="STUDENT",
            )
            db.session.add(user)
            db.session.commit()
            user_id = user.user_id

        response = self.client.delete(
            f"/api/admin/users/{user_id}",
            headers=self.admin_headers(),
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["action"], "deleted")

        with self.app.app_context():
            self.assertIsNone(db.session.get(User, user_id))

    def test_delete_current_admin_is_rejected(self):
        with self.app.app_context():
            admin = User.query.filter_by(role="ADMIN").first()
            admin_id = admin.user_id

        response = self.client.delete(
            f"/api/admin/users/{admin_id}",
            headers=self.admin_headers(),
        )

        self.assertEqual(response.status_code, 409)

        with self.app.app_context():
            admin = db.session.get(User, admin_id)
            self.assertIsNotNone(admin)
            self.assertTrue(admin.is_active)

    def test_update_current_admin_cannot_be_deactivated(self):
        with self.app.app_context():
            admin = User.query.filter_by(role="ADMIN").first()
            admin_id = admin.user_id

        response = self.client.patch(
            f"/api/admin/users/{admin_id}",
            headers=self.admin_headers(),
            json={"is_active": False},
        )

        self.assertEqual(response.status_code, 409)

        with self.app.app_context():
            admin = db.session.get(User, admin_id)
            self.assertTrue(admin.is_active)


    def test_last_active_admin_cannot_be_deactivated(self):
        with self.app.app_context():
            # Make the token owner's account inactive and create
            # one different, active administrator to protect.
            token_owner = User.query.filter_by(
                email="admin@test.local"
            ).first()
            token_owner.is_active = False

            target_admin = User(
                name="Only Active Admin",
                email="only-admin@test.local",
                password_hash="not-used",
                role="ADMIN",
                is_active=True,
            )
            db.session.add(target_admin)
            db.session.commit()
            target_admin_id = target_admin.user_id

        response = self.client.patch(
            f"/api/admin/users/{target_admin_id}",
            headers=self.admin_headers(),
            json={"is_active": False},
        )

        self.assertEqual(response.status_code, 409)

        with self.app.app_context():
            target_admin = db.session.get(User, target_admin_id)
            self.assertIsNotNone(target_admin)
            self.assertTrue(target_admin.is_active)

    def create_student_record(self, name, email, enrollment_no, dept_id, semester, section):
        with self.app.app_context():
            u = User(name=name, email=email, password_hash="not-used", role="STUDENT")
            db.session.add(u)
            db.session.flush()
            st = Student(
                user_id=u.user_id,
                department_id=dept_id,
                enrollment_no=enrollment_no,
                semester=semester,
                section=section,
                academic_year="2026-27",
            )
            db.session.add(st)
            db.session.commit()

    def test_get_students_filter_options(self):
        with self.app.app_context():
            dept = Department(department_name="Mechanical Engineering", department_code="ME")
            db.session.add(dept)
            db.session.commit()
            dept_id = dept.department_id

        # Seed students with specific semesters and sections
        self.create_student_record("S1", "s1@test.local", "ME001", dept_id, semester=1, section="A")
        self.create_student_record("S2", "s2@test.local", "ME002", dept_id, semester=5, section="B")
        self.create_student_record("S3", "s3@test.local", "ME003", dept_id, semester=7, section="B")

        response = self.client.get(
            "/api/admin/students/filter-options",
            headers=self.admin_headers(),
        )

        self.assertEqual(response.status_code, 200)
        data = response.get_json()["data"]
        # In setUp, semester 3 / section A is already present
        self.assertEqual(data["semesters"], [1, 3, 5, 7])
        self.assertEqual(data["sections"], ["A", "B"])
        self.assertTrue(any(d["department_name"] == "Mechanical Engineering" for d in data["departments"]))

    def test_get_students_summary_includes_semesters_and_sections(self):
        response = self.client.get(
            "/api/admin/students/summary",
            headers=self.admin_headers(),
        )

        self.assertEqual(response.status_code, 200)
        data = response.get_json()["data"]
        self.assertIn("semesters", data)
        self.assertIn("sections", data)
        self.assertIn(3, data["semesters"])
        self.assertIn("A", data["sections"])

    def test_create_student_valid_semester_and_section(self):
        with self.app.app_context():
            u = User(name="Valid Student", email="validstu@test.local", password_hash="pw", role="STUDENT")
            db.session.add(u)
            db.session.commit()
            u_id = u.user_id

        payload = {
            "user_id": u_id,
            "department_id": self.dept_id,
            "enrollment_no": "ENROLL-VALID-01",
            "semester": 6,
            "section": "  C  ",
            "academic_year": "2026-27",
        }

        response = self.client.post(
            "/api/admin/students",
            json=payload,
            headers=self.admin_headers(),
        )
        self.assertEqual(response.status_code, 201)
        body = response.get_json()
        self.assertTrue(body["success"])
        self.assertEqual(body["data"]["semester"], 6)
        self.assertEqual(body["data"]["section"], "C")

    def test_create_student_invalid_semester(self):
        with self.app.app_context():
            u = User(name="Invalid Sem Student", email="invalidsem@test.local", password_hash="pw", role="STUDENT")
            db.session.add(u)
            db.session.commit()
            u_id = u.user_id

        # Semester > 8
        payload = {
            "user_id": u_id,
            "department_id": self.dept_id,
            "enrollment_no": "ENROLL-SEM-9",
            "semester": 9,
            "section": "A",
            "academic_year": "2026-27",
        }
        response = self.client.post(
            "/api/admin/students",
            json=payload,
            headers=self.admin_headers(),
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("between 1 and 8", response.get_json()["message"])

        # Semester < 1
        payload["semester"] = 0
        response = self.client.post(
            "/api/admin/students",
            json=payload,
            headers=self.admin_headers(),
        )
        self.assertEqual(response.status_code, 400)

    def test_create_student_invalid_section(self):
        with self.app.app_context():
            u = User(name="Invalid Sec Student", email="invalidsec@test.local", password_hash="pw", role="STUDENT")
            db.session.add(u)
            db.session.commit()
            u_id = u.user_id

        # Empty section
        payload = {
            "user_id": u_id,
            "department_id": self.dept_id,
            "enrollment_no": "ENROLL-NOSEC",
            "semester": 2,
            "section": "   ",
            "academic_year": "2026-27",
        }
        response = self.client.post(
            "/api/admin/students",
            json=payload,
            headers=self.admin_headers(),
        )
        self.assertEqual(response.status_code, 400)

        # Section too long (> 20 chars)
        payload["section"] = "A" * 25
        response = self.client.post(
            "/api/admin/students",
            json=payload,
            headers=self.admin_headers(),
        )
        self.assertEqual(response.status_code, 400)


if __name__ == "__main__":
    unittest.main()


