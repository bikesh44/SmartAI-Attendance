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
    TimetableEntry,
    User,
)
from app.routes.attendance import attendance_bp
from app.routes.faculty import faculty_bp
from app.routes.timetable import timetable_bp


class TestFacultyAttendanceAPI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = Flask(__name__)
        cls.app.config.update(
            TESTING=True,
            SECRET_KEY="test-secret-faculty-attendance",
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
        cls.app.register_blueprint(attendance_bp)
        cls.app.register_blueprint(faculty_bp)
        cls.app.register_blueprint(timetable_bp)

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

            dept = Department(
                department_name="Computer Science",
                department_code="CSE",
            )
            db.session.add(dept)
            db.session.flush()

            # Faculty A
            user_fac_a = User(
                name="Prof Alice",
                email="alice@test.local",
                password_hash="pw",
                role="FACULTY",
            )
            # Faculty B
            user_fac_b = User(
                name="Prof Bob",
                email="bob@test.local",
                password_hash="pw",
                role="FACULTY",
            )
            # Students
            user_stu_1 = User(
                name="Student One",
                email="s1@test.local",
                password_hash="pw",
                role="STUDENT",
            )
            user_stu_2 = User(
                name="Student Two",
                email="s2@test.local",
                password_hash="pw",
                role="STUDENT",
            )

            # Admin
            user_admin = User(
                name="Admin User",
                email="admin@test.local",
                password_hash="pw",
                role="ADMIN",
            )

            db.session.add_all([user_fac_a, user_fac_b, user_stu_1, user_stu_2, user_admin])
            db.session.flush()

            fac_a = Faculty(
                user_id=user_fac_a.user_id,
                department_id=dept.department_id,
                employee_id="FAC-001",
                designation="Assistant Professor",
            )
            fac_b = Faculty(
                user_id=user_fac_b.user_id,
                department_id=dept.department_id,
                employee_id="FAC-002",
                designation="Associate Professor",
            )
            stu_1 = Student(
                user_id=user_stu_1.user_id,
                department_id=dept.department_id,
                enrollment_no="ENR-101",
                semester=4,
                section="A",
                academic_year="2025-2026",
            )
            stu_2 = Student(
                user_id=user_stu_2.user_id,
                department_id=dept.department_id,
                enrollment_no="ENR-102",
                semester=4,
                section="A",
                academic_year="2025-2026",
            )

            db.session.add_all([fac_a, fac_b, stu_1, stu_2])
            db.session.flush()

            course = Course(
                course_code="CS401",
                course_name="Machine Learning",
                department_id=dept.department_id,
                semester=4,
                credits=4,
            )
            db.session.add(course)
            db.session.flush()

            offering_a = CourseOffering(
                course_id=course.course_id,
                faculty_id=fac_a.faculty_id,
                semester=4,
                section="A",
                academic_year="2025-2026",
                room="Room 301",
            )
            offering_b = CourseOffering(
                course_id=course.course_id,
                faculty_id=fac_b.faculty_id,
                semester=4,
                section="B",
                academic_year="2025-2026",
                room="Room 302",
            )
            db.session.add_all([offering_a, offering_b])
            db.session.flush()

            # Enroll stu_1 in offering_a, stu_2 in offering_b
            enr_1 = Enrollment(
                student_id=stu_1.student_id,
                offering_id=offering_a.offering_id,
                status="ACTIVE",
            )
            enr_2 = Enrollment(
                student_id=stu_2.student_id,
                offering_id=offering_b.offering_id,
                status="ACTIVE",
            )
            db.session.add_all([enr_1, enr_2])

            # Session for offering_a (active within window for test execution)
            sess_a = AttendanceSession(
                offering_id=offering_a.offering_id,
                faculty_id=fac_a.faculty_id,
                session_date=date.today(),
                start_time=time(0, 0),
                end_time=time(23, 59, 59),
                status="ACTIVE",
            )
            # Closed session for offering_a
            sess_a_closed = AttendanceSession(
                offering_id=offering_a.offering_id,
                faculty_id=fac_a.faculty_id,
                session_date=date(2026, 10, 19),
                start_time=time(9, 0),
                end_time=time(10, 0),
                status="CLOSED",
            )
            # Session for offering_b
            sess_b = AttendanceSession(
                offering_id=offering_b.offering_id,
                faculty_id=fac_b.faculty_id,
                session_date=date.today(),
                start_time=time(0, 0),
                end_time=time(23, 59, 59),
                status="ACTIVE",
            )
            db.session.add_all([sess_a, sess_a_closed, sess_b])
            db.session.commit()

            # Store scalar IDs for test isolation
            self.fac_a_user_id = user_fac_a.user_id
            self.fac_b_user_id = user_fac_b.user_id
            self.fac_a_id = fac_a.faculty_id
            self.fac_b_id = fac_b.faculty_id
            self.stu_1_id = stu_1.student_id
            self.stu_2_id = stu_2.student_id
            self.offering_a_id = offering_a.offering_id
            self.offering_b_id = offering_b.offering_id
            self.sess_a_id = sess_a.session_id
            self.sess_a_closed_id = sess_a_closed.session_id
            self.sess_b_id = sess_b.session_id
            self.admin_user_id = user_admin.user_id

    def tearDown(self):
        with self.app.app_context():
            db.session.rollback()
            db.session.remove()

    def _headers(self, user_id, role="FACULTY"):
        with self.app.app_context():
            token = create_access_token(
                identity=str(user_id),
                additional_claims={"role": role},
            )
        return {"Authorization": f"Bearer {token}"}

    def test_get_sessions_isolated_by_faculty(self):
        headers_a = self._headers(self.fac_a_user_id)
        res = self.client.get("/api/faculty/attendance/sessions", headers=headers_a)
        self.assertEqual(res.status_code, 200)
        data = res.get_json()["data"]
        session_ids = [s["session_id"] for s in data]
        self.assertIn(self.sess_a_id, session_ids)
        self.assertIn(self.sess_a_closed_id, session_ids)
        self.assertNotIn(self.sess_b_id, session_ids)

    def test_get_sessions_filtering_by_status_and_offering(self):
        headers_a = self._headers(self.fac_a_user_id)
        # Filter status=CLOSED
        res = self.client.get(
            f"/api/faculty/attendance/sessions?status=CLOSED&offering_id={self.offering_a_id}",
            headers=headers_a,
        )
        self.assertEqual(res.status_code, 200)
        data = res.get_json()["data"]
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["session_id"], self.sess_a_closed_id)
        self.assertEqual(data[0]["status"], "CLOSED")

    def test_get_active_session(self):
        headers_a = self._headers(self.fac_a_user_id)
        res = self.client.get("/api/faculty/attendance/sessions/active", headers=headers_a)
        self.assertEqual(res.status_code, 200)
        data = res.get_json()["data"]
        self.assertIsNotNone(data)
        self.assertEqual(data["session_id"], self.sess_a_id)
        self.assertEqual(data["status"], "ACTIVE")

    def test_start_session_verifies_faculty_ownership(self):
        headers_a = self._headers(self.fac_a_user_id)
        # Try to start session for offering_b (owned by Faculty B)
        res = self.client.post(
            "/api/faculty/attendance/sessions",
            json={"offering_id": self.offering_b_id},
            headers=headers_a,
        )
        self.assertEqual(res.status_code, 403)
        self.assertIn("not authorized", res.get_json()["message"].lower())

    def test_start_session_prevents_duplicate_active_sessions(self):
        headers_a = self._headers(self.fac_a_user_id)
        # Session A is already active for Faculty A
        res = self.client.post(
            "/api/faculty/attendance/sessions",
            json={"offering_id": self.offering_a_id},
            headers=headers_a,
        )
        self.assertEqual(res.status_code, 409)
        self.assertIn("already exists", res.get_json()["message"].lower())

    def test_faculty_manual_mark_attendance_forbidden(self):
        headers_a = self._headers(self.fac_a_user_id, role="FACULTY")

        # Faculty attempts to mark Student 1 PRESENT manually
        res = self.client.post(
            f"/api/faculty/attendance/sessions/{self.sess_a_id}/records",
            json={
                "student_id": self.stu_1_id,
                "status": "PRESENT",
                "recognition_method": "MANUAL",
            },
            headers=headers_a,
        )
        self.assertEqual(res.status_code, 403)
        self.assertIn("manual attendance marking by faculty is disabled", res.get_json()["message"].lower())

    def test_faculty_update_record_via_patch_forbidden(self):
        headers_a = self._headers(self.fac_a_user_id, role="FACULTY")

        # Faculty attempts PATCH update
        res = self.client.patch(
            f"/api/faculty/attendance/sessions/{self.sess_a_id}/records/{self.stu_1_id}",
            json={"status": "LATE"},
            headers=headers_a,
        )
        self.assertEqual(res.status_code, 403)
        self.assertIn("manual attendance marking by faculty is disabled", res.get_json()["message"].lower())

    def test_admin_can_mark_and_update_attendance_records(self):
        admin_headers = self._headers(self.admin_user_id, role="ADMIN")

        # Admin marks Student 1 PRESENT
        res = self.client.post(
            f"/api/faculty/attendance/sessions/{self.sess_a_id}/records",
            json={
                "student_id": self.stu_1_id,
                "status": "PRESENT",
                "recognition_method": "MANUAL",
            },
            headers=admin_headers,
        )
        self.assertEqual(res.status_code, 201)
        data = res.get_json()["data"]
        self.assertEqual(data["status"], "PRESENT")
        self.assertEqual(data["student_name"], "Student One")
        self.assertEqual(data["enrollment_no"], "ENR-101")

        # Admin updates Student 1 to LATE via PATCH
        patch_res = self.client.patch(
            f"/api/faculty/attendance/sessions/{self.sess_a_id}/records/{self.stu_1_id}",
            json={"status": "LATE"},
            headers=admin_headers,
        )
        self.assertEqual(patch_res.status_code, 200)
        self.assertEqual(patch_res.get_json()["data"]["status"], "LATE")

    def test_admin_mark_attendance_rejects_unenrolled_student(self):
        admin_headers = self._headers(self.admin_user_id, role="ADMIN")

        # Student 2 is only enrolled in offering_b, not offering_a
        res = self.client.post(
            f"/api/faculty/attendance/sessions/{self.sess_a_id}/records",
            json={
                "student_id": self.stu_2_id,
                "status": "PRESENT",
            },
            headers=admin_headers,
        )
        self.assertEqual(res.status_code, 403)
        self.assertIn("not enrolled", res.get_json()["message"].lower())

    def test_cross_faculty_attendance_records_forbidden(self):
        headers_b = self._headers(self.fac_b_user_id)

        # Faculty B attempts to view Faculty A's session records
        res = self.client.get(
            f"/api/faculty/attendance/sessions/{self.sess_a_id}/records",
            headers=headers_b,
        )
        self.assertEqual(res.status_code, 403)

        # Faculty B attempts to mark attendance in Faculty A's session
        mark_res = self.client.post(
            f"/api/faculty/attendance/sessions/{self.sess_a_id}/records",
            json={"student_id": self.stu_1_id, "status": "PRESENT"},
            headers=headers_b,
        )
        self.assertEqual(mark_res.status_code, 403)

    def test_get_session_records_enriched_format(self):
        headers_a = self._headers(self.fac_a_user_id)
        admin_headers = self._headers(self.admin_user_id, role="ADMIN")

        # Admin marks Student 1 PRESENT
        self.client.post(
            f"/api/faculty/attendance/sessions/{self.sess_a_id}/records",
            json={"student_id": self.stu_1_id, "status": "PRESENT"},
            headers=admin_headers,
        )

        res = self.client.get(
            f"/api/faculty/attendance/sessions/{self.sess_a_id}/records",
            headers=headers_a,
        )
        self.assertEqual(res.status_code, 200)
        records = res.get_json()["data"]
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["student_id"], self.stu_1_id)
        self.assertEqual(records[0]["student_name"], "Student One")
        self.assertEqual(records[0]["enrollment_no"], "ENR-101")
    def test_get_faculty_attendance_overview_default(self):
        headers_a = self._headers(self.fac_a_user_id)
        res = self.client.get("/api/faculty/attendance/overview", headers=headers_a)
        self.assertEqual(res.status_code, 200)
        data = res.get_json()["data"]
        self.assertEqual(data["active_sessions"], 1)
        self.assertTrue(data["has_active_session"])
        self.assertIsNotNone(data["active_session"])
        self.assertEqual(data["active_session"]["session_id"], self.sess_a_id)
        self.assertIsNotNone(data["selected_session"])
        self.assertEqual(data["selected_session"]["session_id"], self.sess_a_id)
        self.assertEqual(data["total_enrolled"], 1)

    def test_get_faculty_attendance_overview_with_session_and_records(self):
        with self.app.app_context():
            rec = AttendanceRecord(
                session_id=self.sess_a_closed_id,
                student_id=self.stu_1_id,
                status="PRESENT",
                recognition_method="MANUAL",
            )
            db.session.add(rec)
            db.session.commit()

        headers_a = self._headers(self.fac_a_user_id)
        res = self.client.get(
            f"/api/faculty/attendance/overview?session_id={self.sess_a_closed_id}",
            headers=headers_a,
        )
        self.assertEqual(res.status_code, 200)
        data = res.get_json()["data"]
        self.assertEqual(data["selected_session"]["session_id"], self.sess_a_closed_id)
        self.assertEqual(data["students_present"], 1)
        self.assertEqual(data["students_absent"], 0)
        self.assertEqual(data["attendance_rate"], 100.0)

    def test_get_faculty_attendance_overview_cross_faculty_forbidden(self):
        headers_a = self._headers(self.fac_a_user_id)
        res = self.client.get(
            f"/api/faculty/attendance/overview?session_id={self.sess_b_id}",
            headers=headers_a,
        )
        self.assertIn(res.status_code, [403, 404])

    def test_start_session_rejects_offering_with_no_enrolled_students(self):
        with self.app.app_context():
            sess = db.session.get(AttendanceSession, self.sess_a_id)
            sess.status = "CLOSED"

            offering_empty = CourseOffering(
                course_id=sess.offering.course_id,
                faculty_id=self.fac_a_id,
                semester=4,
                section="C",
                academic_year="2025-2026",
                room="Room 303",
            )
            db.session.add(offering_empty)
            db.session.commit()
            empty_offering_id = offering_empty.offering_id

        headers_a = self._headers(self.fac_a_user_id)
        res = self.client.post(
            "/api/faculty/attendance/sessions",
            json={"offering_id": empty_offering_id},
            headers=headers_a,
        )
        self.assertEqual(res.status_code, 400)
        self.assertIn("no active students are enrolled", res.get_json()["message"].lower())

    def test_get_sessions_pagination(self):
        with self.app.app_context():
            s1 = AttendanceSession(
                offering_id=self.offering_a_id,
                faculty_id=self.fac_a_id,
                session_date=date(2026, 10, 18),
                start_time=time(9, 0),
                end_time=time(10, 0),
                status="CLOSED",
            )
            s2 = AttendanceSession(
                offering_id=self.offering_a_id,
                faculty_id=self.fac_a_id,
                session_date=date(2026, 10, 17),
                start_time=time(9, 0),
                end_time=time(10, 0),
                status="CLOSED",
            )
            db.session.add_all([s1, s2])
            db.session.commit()

        headers_a = self._headers(self.fac_a_user_id)
        res = self.client.get(
            "/api/faculty/attendance/sessions?page=1&per_page=2",
            headers=headers_a,
        )
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(len(data["data"]), 2)
        self.assertEqual(data["page"], 1)
        self.assertEqual(data["per_page"], 2)
        self.assertGreaterEqual(data["total"], 3)

    def test_faculty_students_offering_authorization(self):
        headers_a = self._headers(self.fac_a_user_id)

        res_own = self.client.get(
            f"/api/faculty/students?offering_id={self.offering_a_id}",
            headers=headers_a,
        )
        self.assertEqual(res_own.status_code, 200)
        students = res_own.get_json()["data"]
        self.assertEqual(len(students), 1)
        self.assertEqual(students[0]["student_id"], self.stu_1_id)

        res_forbidden = self.client.get(
            f"/api/faculty/students?offering_id={self.offering_b_id}",
            headers=headers_a,
        )
        self.assertEqual(res_forbidden.status_code, 403)
        self.assertIn("not authorized", res_forbidden.get_json()["message"].lower())

        res_not_found = self.client.get(
            "/api/faculty/students?offering_id=999999",
            headers=headers_a,
        )
        self.assertEqual(res_not_found.status_code, 404)

    def test_faculty_timetable_day_filter_and_isolation(self):
        with self.app.app_context():
            tt_a_mon = TimetableEntry(
                offering_id=self.offering_a_id,
                day_of_week="Monday",
                start_time=time(9, 0),
                end_time=time(10, 0),
                room="Room 301",
            )
            tt_a_thu = TimetableEntry(
                offering_id=self.offering_a_id,
                day_of_week="Thursday",
                start_time=time(11, 0),
                end_time=time(12, 0),
                room="Room 301",
            )
            tt_b_mon = TimetableEntry(
                offering_id=self.offering_b_id,
                day_of_week="Monday",
                start_time=time(10, 0),
                end_time=time(11, 0),
                room="Room 302",
            )
            db.session.add_all([tt_a_mon, tt_a_thu, tt_b_mon])
            db.session.commit()

        headers_a = self._headers(self.fac_a_user_id)

        res_mon = self.client.get("/api/timetable/faculty?day=Monday", headers=headers_a)
        self.assertEqual(res_mon.status_code, 200)
        mon_entries = res_mon.get_json()["data"]
        self.assertEqual(len(mon_entries), 1)
        self.assertEqual(mon_entries[0]["day_of_week"], "Monday")
        self.assertEqual(mon_entries[0]["room"], "Room 301")

        res_thu = self.client.get("/api/timetable/faculty?day=Thursday", headers=headers_a)
        self.assertEqual(res_thu.status_code, 200)
        thu_entries = res_thu.get_json()["data"]
        self.assertEqual(len(thu_entries), 1)
        self.assertEqual(thu_entries[0]["day_of_week"], "Thursday")

        res_fri = self.client.get("/api/timetable/faculty?day=Friday", headers=headers_a)
        self.assertEqual(res_fri.status_code, 200)
        self.assertEqual(len(res_fri.get_json()["data"]), 0)

        res_unauth = self.client.get("/api/timetable/faculty")
        self.assertEqual(res_unauth.status_code, 401)


if __name__ == "__main__":
    unittest.main()
