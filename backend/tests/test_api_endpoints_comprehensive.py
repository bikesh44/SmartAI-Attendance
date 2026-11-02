import os
import unittest
from datetime import date, datetime, time, timedelta

from flask import Flask
from flask_jwt_extended import JWTManager, create_access_token
from sqlalchemy.pool import StaticPool

from app.extensions import bcrypt, db
from app.models import (
    AttendanceRecord,
    AttendanceSession,
    Batch,
    Course,
    CourseOffering,
    Department,
    Enrollment,
    FaceProfile,
    Faculty,
    FacultyAdjustment,
    Student,
    SystemSetting,
    TimetableEntry,
    User,
)
from app.routes import health_bp
from app.routes.admin import admin_bp
from app.routes.admin_analytics import admin_analytics_bp
from app.routes.admin_attendance import admin_attendance_bp
from app.routes.analytics import analytics_bp
from app.routes.attendance import attendance_bp
from app.routes.auth import auth_bp
from app.routes.enrollment import enrollment_bp
from app.routes.face import face_bp
from app.routes.face_profile import face_profile_bp
from app.routes.faculty import faculty_bp
from app.routes.recognition import recognition_bp
from app.routes.reports import reports_bp
from app.routes.student import student_bp
from app.routes.student_attendance import student_attendance_bp
from app.routes.timetable import timetable_bp
from app.routes.timetable_import import timetable_import_bp


class TestApiEndpointsComprehensive(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = Flask(__name__)
        cls.app.config.update(
            TESTING=True,
            SECRET_KEY="test-secret-key",
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

        # Register all application blueprints
        cls.app.register_blueprint(health_bp)
        cls.app.register_blueprint(auth_bp)
        cls.app.register_blueprint(admin_bp)
        cls.app.register_blueprint(admin_analytics_bp)
        cls.app.register_blueprint(admin_attendance_bp)
        cls.app.register_blueprint(analytics_bp)
        cls.app.register_blueprint(attendance_bp)
        cls.app.register_blueprint(enrollment_bp)
        cls.app.register_blueprint(face_bp)
        cls.app.register_blueprint(face_profile_bp)
        cls.app.register_blueprint(faculty_bp)
        cls.app.register_blueprint(recognition_bp)
        cls.app.register_blueprint(reports_bp)
        cls.app.register_blueprint(student_bp)
        cls.app.register_blueprint(student_attendance_bp)
        cls.app.register_blueprint(timetable_bp)
        cls.app.register_blueprint(timetable_import_bp)

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

            # 1. Admin
            admin_user = User(
                name="System Admin",
                email="admin@sams.local",
                password_hash=bcrypt.generate_password_hash("AdminPass123").decode("utf-8"),
                role="ADMIN",
                is_active=True,
            )
            # 2. Faculty
            faculty_user = User(
                name="Prof. Sharma",
                email="sharma@sams.local",
                password_hash=bcrypt.generate_password_hash("FacultyPass123").decode("utf-8"),
                role="FACULTY",
                is_active=True,
            )
            # 3. Student
            student_user = User(
                name="Aarav Verma",
                email="aarav@sams.local",
                password_hash=bcrypt.generate_password_hash("StudentPass123").decode("utf-8"),
                role="STUDENT",
                is_active=True,
            )
            db.session.add_all([admin_user, faculty_user, student_user])
            db.session.flush()

            dept = Department(
                department_name="Computer Science & Engineering",
                department_code="CSE",
            )
            batch = Batch(
                batch_name="2025-2029",
                is_active=True,
            )
            db.session.add_all([dept, batch])
            db.session.flush()

            faculty = Faculty(
                user_id=faculty_user.user_id,
                employee_id="FAC001",
                department_id=dept.department_id,
                designation="Assistant Professor",
            )
            student = Student(
                user_id=student_user.user_id,
                enrollment_no="CSE2025001",
                department_id=dept.department_id,
                batch_id=batch.batch_id,
                semester=3,
                section="A",
                academic_year="2026-2027",
            )
            db.session.add_all([faculty, student])
            db.session.flush()

            course = Course(
                course_code="BCSE-301",
                course_name="Data Structures",
                department_id=dept.department_id,
                semester=3,
                credits=4,
                batch="2025",
                is_active=True,
            )
            db.session.add(course)
            db.session.flush()

            offering = CourseOffering(
                course_id=course.course_id,
                faculty_id=faculty.faculty_id,
                academic_year="2026-2027",
                semester=3,
                section="A",
                room="Room 301",
            )
            db.session.add(offering)
            db.session.flush()

            enrollment = Enrollment(
                student_id=student.student_id,
                offering_id=offering.offering_id,
                status="ACTIVE",
            )
            db.session.add(enrollment)
            db.session.commit()

            self.admin_id = admin_user.user_id
            self.faculty_id = faculty.faculty_id
            self.faculty_user_id = faculty_user.user_id
            self.student_id = student.student_id
            self.student_user_id = student_user.user_id
            self.dept_id = dept.department_id
            self.batch_id = batch.batch_id
            self.course_id = course.course_id
            self.offering_id = offering.offering_id

    def admin_headers(self):
        with self.app.app_context():
            token = create_access_token(identity=str(self.admin_id), additional_claims={"role": "ADMIN"})
            return {"Authorization": f"Bearer {token}"}

    def faculty_headers(self):
        with self.app.app_context():
            token = create_access_token(identity=str(self.faculty_user_id), additional_claims={"role": "FACULTY"})
            return {"Authorization": f"Bearer {token}"}

    def student_headers(self):
        with self.app.app_context():
            token = create_access_token(identity=str(self.student_user_id), additional_claims={"role": "STUDENT"})
            return {"Authorization": f"Bearer {token}"}

    # -------------------------------------------------------------
    # 1. Health & Diagnostics
    # -------------------------------------------------------------
    def test_health_endpoints(self):
        r1 = self.client.get("/api/health")
        self.assertEqual(r1.status_code, 200)
        self.assertEqual(r1.get_json()["status"], "ok")

        r2 = self.client.get("/api/db-health")
        self.assertEqual(r2.status_code, 200)
        self.assertEqual(r2.get_json()["database"], "ok")

    # -------------------------------------------------------------
    # 2. Authentication & Authorization Boundaries
    # -------------------------------------------------------------
    def test_auth_login_success_and_failures(self):
        # Valid login
        r = self.client.post("/api/auth/login", json={"email": "admin@sams.local", "password": "AdminPass123"})
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.get_json()["success"])

        # Invalid password
        r = self.client.post("/api/auth/login", json={"email": "admin@sams.local", "password": "WrongPassword"})
        self.assertEqual(r.status_code, 401)

        # Missing fields
        r = self.client.post("/api/auth/login", json={"email": "admin@sams.local"})
        self.assertEqual(r.status_code, 400)

        # Logout
        r = self.client.post("/api/auth/logout")
        self.assertEqual(r.status_code, 200)

    def test_auth_me_and_protected_tests(self):
        # Unauthenticated me
        r = self.client.get("/api/auth/me")
        self.assertEqual(r.status_code, 401)

        # Authenticated me
        r = self.client.get("/api/auth/me", headers=self.admin_headers())
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.get_json()["data"]["email"], "admin@sams.local")

        # Protected test with student token
        r = self.client.get("/api/auth/protected-test", headers=self.student_headers())
        self.assertEqual(r.status_code, 200)

        # Admin test with student token (Forbidden -> 403)
        r = self.client.get("/api/auth/admin-test", headers=self.student_headers())
        self.assertEqual(r.status_code, 403)

        # Admin test with admin token
        r = self.client.get("/api/auth/admin-test", headers=self.admin_headers())
        self.assertEqual(r.status_code, 200)

    # -------------------------------------------------------------
    # 3. Admin Academic & Batches
    # -------------------------------------------------------------
    def test_admin_batches_lifecycle(self):
        # Get batches
        r = self.client.get("/api/admin/batches", headers=self.admin_headers())
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.get_json()["success"])

        # Create new batch
        r = self.client.post("/api/admin/batches", headers=self.admin_headers(), json={"batch_name": "2026-2030"})
        self.assertEqual(r.status_code, 201)

        # Duplicate batch rejection
        r = self.client.post("/api/admin/batches", headers=self.admin_headers(), json={"batch_name": "2026-2030"})
        self.assertEqual(r.status_code, 409)

        # Student forbidden from creating batch
        r = self.client.post("/api/admin/batches", headers=self.student_headers(), json={"batch_name": "2027-2031"})
        self.assertEqual(r.status_code, 403)

    def test_admin_academic_session_config(self):
        # Get academic session config
        r = self.client.get("/api/admin/academic-session", headers=self.admin_headers())
        self.assertEqual(r.status_code, 200)
        self.assertIn("current_academic_year", r.get_json()["data"])

        # Update academic session config
        r = self.client.post("/api/admin/academic-session", headers=self.admin_headers(), json={"academic_year": "2026-2027"})
        self.assertEqual(r.status_code, 200)

        # PUT alias
        r = self.client.put("/api/admin/academic-session", headers=self.admin_headers(), json={"academic_year": "2026-2027"})
        self.assertEqual(r.status_code, 200)

        # Invalid academic session format rejection
        r = self.client.post("/api/admin/academic-session", headers=self.admin_headers(), json={"academic_year": "invalid-year"})
        self.assertEqual(r.status_code, 400)

    # -------------------------------------------------------------
    # 4. Admin Courses & Course Offerings
    # -------------------------------------------------------------
    def test_admin_courses_crud(self):
        # Create course
        r = self.client.post("/api/admin/courses", headers=self.admin_headers(), json={
            "course_code": "BCSE-302",
            "course_name": "Operating Systems",
            "department_id": self.dept_id,
            "semester": 3,
            "credits": 4,
            "batch": "2025"
        })
        self.assertEqual(r.status_code, 201)
        new_course_id = r.get_json()["data"]["course_id"]

        # Get single course
        r = self.client.get(f"/api/admin/courses/{new_course_id}", headers=self.admin_headers())
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.get_json()["data"]["course_code"], "BCSE-302")

        # Delete course
        r = self.client.delete(f"/api/admin/courses/{new_course_id}", headers=self.admin_headers())
        self.assertEqual(r.status_code, 200)

    def test_admin_course_offerings_crud(self):
        # Create offering
        r = self.client.post("/api/admin/course-offerings", headers=self.admin_headers(), json={
            "course_id": self.course_id,
            "faculty_id": self.faculty_id,
            "academic_year": "2026-2027",
            "semester": 3,
            "section": "B",
            "room": "Room 302"
        })
        self.assertEqual(r.status_code, 201)
        new_offering_id = r.get_json()["data"]["offering_id"]

        # Update offering via PATCH
        r = self.client.patch(f"/api/admin/course-offerings/{new_offering_id}", headers=self.admin_headers(), json={
            "room": "Room 305"
        })
        self.assertEqual(r.status_code, 200)

        # Update offering via PUT alias
        r = self.client.put(f"/api/admin/course-offerings/{new_offering_id}", headers=self.admin_headers(), json={
            "room": "Room 310"
        })
        self.assertEqual(r.status_code, 200)

        # Delete offering
        r = self.client.delete(f"/api/admin/course-offerings/{new_offering_id}", headers=self.admin_headers())
        self.assertEqual(r.status_code, 200)

    # -------------------------------------------------------------
    # 5. Admin Attendance Sessions & Analytics
    # -------------------------------------------------------------
    def test_admin_attendance_sessions_and_analytics(self):
        # Attendance sessions list
        r = self.client.get("/api/admin/attendance/sessions", headers=self.admin_headers())
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.get_json()["success"])

        # Attendance dashboard metrics
        r = self.client.get("/api/admin/attendance/dashboard", headers=self.admin_headers())
        self.assertEqual(r.status_code, 200)

        # Attendance filter options
        r = self.client.get("/api/admin/attendance/filter-options", headers=self.admin_headers())
        self.assertEqual(r.status_code, 200)

        # Admin attendance analytics
        r = self.client.get("/api/admin/attendance/analytics", headers=self.admin_headers())
        self.assertEqual(r.status_code, 200)

        # Attendance export
        r = self.client.get("/api/admin/attendance/export", headers=self.admin_headers())
        self.assertEqual(r.status_code, 200)

    # -------------------------------------------------------------
    # 6. Admin Face Profile & Duplicate Maintenance
    # -------------------------------------------------------------
    def test_admin_face_profiles_and_duplicates(self):
        # Obsolete face profile cleanup
        r = self.client.post("/api/admin/face-profiles/cleanup-obsolete", headers=self.admin_headers(), json={
            "retention_days": 30
        })
        self.assertEqual(r.status_code, 200)

        # Duplicate student scan
        r = self.client.get("/api/admin/students/duplicates", headers=self.admin_headers())
        self.assertEqual(r.status_code, 200)

        # Student face removal
        r = self.client.delete(f"/api/admin/students/{self.student_id}/face", headers=self.admin_headers())
        # Expected 404 since no face profile exists yet
        self.assertIn(r.status_code, [200, 404])

    # -------------------------------------------------------------
    # 7. Student Routes
    # -------------------------------------------------------------
    def test_student_routes_access(self):
        # Student profile
        r = self.client.get("/api/student/profile", headers=self.student_headers())
        self.assertEqual(r.status_code, 200)

        # Student courses
        r = self.client.get("/api/student/courses", headers=self.student_headers())
        self.assertEqual(r.status_code, 200)

        # Student dashboard
        r = self.client.get("/api/student/dashboard", headers=self.student_headers())
        self.assertEqual(r.status_code, 200)

        # Student attendance history
        r = self.client.get("/api/student/attendance/", headers=self.student_headers())
        self.assertEqual(r.status_code, 200)

        # Student attendance summary
        r = self.client.get("/api/student/attendance/summary", headers=self.student_headers())
        self.assertEqual(r.status_code, 200)

        # Faculty forbidden from student profile
        r = self.client.get("/api/student/profile", headers=self.faculty_headers())
        self.assertEqual(r.status_code, 403)

    # -------------------------------------------------------------
    # 8. Faculty Routes
    # -------------------------------------------------------------
    def test_faculty_routes_access(self):
        # Faculty attendance overview
        r = self.client.get("/api/faculty/attendance/overview", headers=self.faculty_headers())
        self.assertEqual(r.status_code, 200)

        # Faculty active session
        r = self.client.get("/api/faculty/attendance/sessions/active", headers=self.faculty_headers())
        self.assertEqual(r.status_code, 200)

        # Student forbidden from faculty attendance overview
        r = self.client.get("/api/faculty/attendance/overview", headers=self.student_headers())
        self.assertEqual(r.status_code, 403)


    # -------------------------------------------------------------
    # 9. Admin Dashboard & Activity Logs
    # -------------------------------------------------------------
    def test_admin_dashboard_and_activity(self):
        # Admin dashboard metrics
        r = self.client.get("/api/admin/dashboard", headers=self.admin_headers())
        self.assertEqual(r.status_code, 200)

        # Activity logs
        r = self.client.get("/api/admin/activity", headers=self.admin_headers())
        self.assertEqual(r.status_code, 200)

        # Recent activity
        r = self.client.get("/api/admin/activity/recent", headers=self.admin_headers())
        self.assertEqual(r.status_code, 200)

    # -------------------------------------------------------------
    # 10. Admin Departments Lifecycle
    # -------------------------------------------------------------
    def test_admin_departments_lifecycle(self):
        # Get departments
        r = self.client.get("/api/admin/departments", headers=self.admin_headers())
        self.assertEqual(r.status_code, 200)

        # Create department
        r = self.client.post("/api/admin/departments", headers=self.admin_headers(), json={
            "department_name": "Mechanical Engineering",
            "department_code": "ME"
        })
        self.assertEqual(r.status_code, 201)
        new_dept_id = r.get_json()["data"]["department_id"]

        # Update department
        r = self.client.patch(f"/api/admin/departments/{new_dept_id}", headers=self.admin_headers(), json={
            "department_name": "Mechanical & Aerospace Engineering"
        })
        self.assertEqual(r.status_code, 200)

        # Delete department
        r = self.client.delete(f"/api/admin/departments/{new_dept_id}", headers=self.admin_headers())
        self.assertEqual(r.status_code, 200)

    # -------------------------------------------------------------
    # 11. Admin User & Profile Management
    # -------------------------------------------------------------
    def test_admin_users_and_settings(self):
        # Users list
        r = self.client.get("/api/admin/users", headers=self.admin_headers())
        self.assertEqual(r.status_code, 200)

        # Single user
        r = self.client.get(f"/api/admin/users/{self.admin_id}", headers=self.admin_headers())
        self.assertEqual(r.status_code, 200)

        # Admin profile
        r = self.client.get("/api/admin/profile", headers=self.admin_headers())
        self.assertEqual(r.status_code, 200)

        # Change admin password
        r = self.client.post("/api/admin/change-password", headers=self.admin_headers(), json={
            "current_password": "AdminPass123",
            "new_password": "NewAdminPass123"
        })
        self.assertEqual(r.status_code, 200)

    # -------------------------------------------------------------
    # 12. Timetable Endpoints
    # -------------------------------------------------------------
    def test_timetable_routes(self):
        # Admin timetable
        r = self.client.get("/api/timetable/admin", headers=self.admin_headers())
        self.assertEqual(r.status_code, 200)

        # Faculty timetable
        r = self.client.get("/api/timetable/faculty", headers=self.faculty_headers())
        self.assertEqual(r.status_code, 200)

        # Student timetable
        r = self.client.get("/api/timetable/student", headers=self.student_headers())
        self.assertEqual(r.status_code, 200)

        # Import academic years
        r = self.client.get("/api/timetable/import/academic-years", headers=self.admin_headers())
        self.assertEqual(r.status_code, 200)

        # Faculty adjustments list (Admin authorized, Faculty forbidden)
        r = self.client.get("/api/timetable/adjustments", headers=self.admin_headers())
        self.assertEqual(r.status_code, 200)

        r_forbidden = self.client.get("/api/timetable/adjustments", headers=self.faculty_headers())
        self.assertEqual(r_forbidden.status_code, 403)

    # -------------------------------------------------------------
    # 13. Face Profile Management
    # -------------------------------------------------------------
    def test_face_profile_routes(self):
        # Admin face profiles list
        r = self.client.get("/api/admin/face-profiles", headers=self.admin_headers())
        self.assertEqual(r.status_code, 200)

        # Face status check
        r = self.client.get(f"/api/face/status/{self.student_id}", headers=self.admin_headers())
        self.assertEqual(r.status_code, 200)


    # -------------------------------------------------------------
    # 14. Admin Faculty Management & Filters
    # -------------------------------------------------------------
    def test_admin_faculty_crud_and_filters(self):
        # Faculty filter options
        r = self.client.get("/api/admin/faculty/filter-options", headers=self.admin_headers())
        self.assertEqual(r.status_code, 200)

        # Faculty summary
        r = self.client.get("/api/admin/faculty/summary", headers=self.admin_headers())
        self.assertEqual(r.status_code, 200)

        # Faculty list
        r = self.client.get("/api/admin/faculty", headers=self.admin_headers())
        self.assertEqual(r.status_code, 200)

        # Single faculty
        r = self.client.get(f"/api/admin/faculty/{self.faculty_id}", headers=self.admin_headers())
        self.assertEqual(r.status_code, 200)

        # Update faculty
        r = self.client.patch(f"/api/admin/faculty/{self.faculty_id}", headers=self.admin_headers(), json={
            "designation": "Associate Professor"
        })
        self.assertEqual(r.status_code, 200)

    # -------------------------------------------------------------
    # 15. Admin Student Management & Filters
    # -------------------------------------------------------------
    def test_admin_student_crud_and_filters(self):
        # Student filter options
        r = self.client.get("/api/admin/students/filter-options", headers=self.admin_headers())
        self.assertEqual(r.status_code, 200)

        # Student summary
        r = self.client.get("/api/admin/students/summary", headers=self.admin_headers())
        self.assertEqual(r.status_code, 200)

        # Single student
        r = self.client.get(f"/api/admin/students/{self.student_id}", headers=self.admin_headers())
        self.assertEqual(r.status_code, 200)

        # Update student
        r = self.client.patch(f"/api/admin/students/{self.student_id}", headers=self.admin_headers(), json={
            "section": "B"
        })
        self.assertEqual(r.status_code, 200)

    # -------------------------------------------------------------
    # 16. Admin Profile & User Creation
    # -------------------------------------------------------------
    def test_admin_profile_and_user_lifecycle(self):
        # Update admin profile
        r = self.client.patch("/api/admin/profile", headers=self.admin_headers(), json={
            "name": "Super Admin"
        })
        self.assertEqual(r.status_code, 200)

        # Create user via admin
        r = self.client.post("/api/admin/users", headers=self.admin_headers(), json={
            "name": "New Faculty Member",
            "email": "new.faculty@sams.local",
            "password": "Password123!",
            "role": "FACULTY"
        })
        self.assertEqual(r.status_code, 201)
        new_uid = r.get_json()["data"]["user_id"]

        # Reactivate user
        r = self.client.patch(f"/api/admin/users/{new_uid}/reactivate", headers=self.admin_headers())
        self.assertEqual(r.status_code, 200)

    # -------------------------------------------------------------
    # 17. Defensive Security Headers
    # -------------------------------------------------------------
    def test_security_headers_present(self):
        from app import create_app
        factory_app = create_app()
        client = factory_app.test_client()
        r = client.get("/api/health")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.headers.get("X-Content-Type-Options"), "nosniff")
        self.assertEqual(r.headers.get("X-Frame-Options"), "SAMEORIGIN")
        self.assertEqual(r.headers.get("Referrer-Policy"), "strict-origin-when-cross-origin")

    # -------------------------------------------------------------
    # 18. Database Health Information Disclosure Prevention
    # -------------------------------------------------------------
    def test_db_health_error_does_not_leak_details(self):
        from unittest.mock import patch
        with patch("app.extensions.db.session.execute", side_effect=RuntimeError("SensitiveInternalClusterHost:3306 syntax error")):
            r = self.client.get("/api/db-health")
            self.assertEqual(r.status_code, 500)
            data = r.get_json()
            self.assertEqual(data.get("database"), "error")
            self.assertEqual(data.get("message"), "Database connection failed")
            self.assertNotIn("SensitiveInternalClusterHost", str(data))

    # -------------------------------------------------------------
    # 19. CSV Export Formula Injection Sanitization
    # -------------------------------------------------------------
    def test_csv_export_formula_injection_sanitization(self):
        from app.routes.admin_attendance import _sanitize_csv_cell
        # Malicious formula payloads
        self.assertEqual(_sanitize_csv_cell("=cmd|'/c calc'!A0"), "'=cmd|'/c calc'!A0")
        self.assertEqual(_sanitize_csv_cell("+12345"), "'+12345")
        self.assertEqual(_sanitize_csv_cell("-malicious"), "'-malicious")
        self.assertEqual(_sanitize_csv_cell("@SUM(1+1)"), "'@SUM(1+1)")
        # Normal safe values
        self.assertEqual(_sanitize_csv_cell("John Doe"), "John Doe")
        self.assertEqual(_sanitize_csv_cell("BCSE-001"), "BCSE-001")
        self.assertEqual(_sanitize_csv_cell(None), "")


if __name__ == "__main__":
    unittest.main()
