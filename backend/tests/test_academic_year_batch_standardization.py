import unittest
from datetime import date, time

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
    Faculty,
    Student,
    SystemSetting,
    TimetableEntry,
    User,
)
from app.routes.admin import admin_bp
from app.routes.enrollment import enrollment_bp
from app.routes.faculty import faculty_bp
from app.routes.student import student_bp
from app.routes.timetable import timetable_bp
from app.utils.academic_year import (
    canonical_academic_year,
    extract_cohort_start_year,
    format_batch_cohort,
    get_available_academic_sessions,
    get_current_academic_session,
    is_batch_cohort,
    is_single_academic_session,
    resolve_student_academic_info,
    set_current_academic_session,
)


class TestAcademicYearBatchStandardization(unittest.TestCase):
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
        cls.app.register_blueprint(student_bp)
        cls.app.register_blueprint(faculty_bp)
        cls.app.register_blueprint(enrollment_bp)
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

            # Create default admin
            admin = User(name="Admin User", email="admin@test.local", password_hash="pw", role="ADMIN")
            dept = Department(department_name="Computer Science", department_code="CSE")
            batch_2024 = Batch(batch_name="2024-2028")
            db.session.add_all([admin, dept, batch_2024])
            db.session.commit()

            self.admin_id = admin.user_id
            self.dept_id = dept.department_id
            self.batch_id = batch_2024.batch_id

    def admin_headers(self):
        with self.app.app_context():
            token = create_access_token(identity=str(self.admin_id), additional_claims={"role": "ADMIN"})
            return {"Authorization": f"Bearer {token}"}

    def student_headers(self, user_id):
        with self.app.app_context():
            token = create_access_token(identity=str(user_id), additional_claims={"role": "STUDENT"})
            return {"Authorization": f"Bearer {token}"}

    def faculty_headers(self, user_id):
        with self.app.app_context():
            token = create_access_token(identity=str(user_id), additional_claims={"role": "FACULTY"})
            return {"Authorization": f"Bearer {token}"}

    def test_definitions_and_helpers(self):
        """Test canonical academic year and batch cohort utilities."""
        self.assertTrue(is_single_academic_session("2024-2025"))
        self.assertTrue(is_single_academic_session("2026-2027"))
        self.assertTrue(is_single_academic_session("2026 - 2027"))
        self.assertTrue(is_single_academic_session("2026-27"))
        self.assertFalse(is_single_academic_session("2024-2028"))

        self.assertTrue(is_batch_cohort("2024-2028"))
        self.assertTrue(is_batch_cohort("2024"))
        self.assertFalse(is_batch_cohort("2024-2025"))

        self.assertEqual(canonical_academic_year("2026 - 2027"), "2026-2027")
        self.assertEqual(canonical_academic_year("2025-26"), "2025-2026")

        self.assertEqual(format_batch_cohort("2024"), "2024-2028")
        self.assertEqual(format_batch_cohort("2024 - 2028"), "2024-2028")
        self.assertEqual(extract_cohort_start_year("2024-2028"), "2024")
        self.assertEqual(extract_cohort_start_year("2024"), "2024")

    def test_example_student_batch_academic_year_and_semester(self):
        """
        Requirements 1 & 2:
        Student:
        - Admission year: 2024
        - Batch: 2024-2028
        - Current academic year: 2026-2027
        - Current semester: 5

        The application must display:
        - Batch Year: 2024-2028
        - Academic Year: 2026-2027
        - Semester: 5
        """
        with self.app.app_context():
            # Configure current academic session to 2026-2027
            set_current_academic_session("2026-2027")

            user = User(name="John Doe", email="john@test.local", password_hash="pw", role="STUDENT")
            db.session.add(user)
            db.session.commit()

            student = Student(
                user_id=user.user_id,
                department_id=self.dept_id,
                batch_id=self.batch_id,
                enrollment_no="CSE2024001",
                semester=5,
                section="A",
                academic_year="2026-2027",
                admission_date="2024-08-01",
            )
            db.session.add(student)
            db.session.commit()
            student_id = student.student_id
            user_id = user.user_id

        # 1. Admin GET student
        res = self.client.get(f"/api/admin/students/{student_id}", headers=self.admin_headers())
        self.assertEqual(res.status_code, 200)
        data = res.get_json()["data"]
        self.assertEqual(data["batch_year"], "2024-2028")
        self.assertEqual(data["academic_year"], "2026-2027")
        self.assertEqual(data["semester"], 5)
        self.assertEqual(data["admission_year"], "2024")

        # 2. Student GET profile
        res_profile = self.client.get("/api/student/profile", headers=self.student_headers(user_id))
        self.assertEqual(res_profile.status_code, 200)
        p_data = res_profile.get_json()["data"]
        self.assertEqual(p_data["batch_year"], "2024-2028")
        self.assertEqual(p_data["academic_year"], "2026-2027")
        self.assertEqual(p_data["semester"], 5)
        self.assertEqual(p_data["batch"]["batch_name"], "2024-2028")

        # 3. Student GET dashboard
        res_dash = self.client.get("/api/student/dashboard", headers=self.student_headers(user_id))
        self.assertEqual(res_dash.status_code, 200)
        d_data = res_dash.get_json()["data"]
        self.assertEqual(d_data["student"]["batch_year"], "2024-2028")
        self.assertEqual(d_data["student"]["academic_year"], "2026-2027")
        self.assertEqual(d_data["student"]["semester"], 5)

    def test_changing_academic_session_does_not_change_student_batch(self):
        """
        Requirement 3:
        Changing the current academic session does not change the student's batch.
        """
        with self.app.app_context():
            set_current_academic_session("2026-2027")
            user = User(name="Jane Student", email="jane@test.local", password_hash="pw", role="STUDENT")
            db.session.add(user)
            db.session.commit()

            student = Student(
                user_id=user.user_id,
                department_id=self.dept_id,
                batch_id=self.batch_id,
                enrollment_no="CSE2024002",
                semester=5,
                section="B",
                academic_year="2026-2027",
            )
            db.session.add(student)
            db.session.commit()
            student_id = student.student_id

        # Admin changes current academic session to 2027-2028
        res_update = self.client.post(
            "/api/admin/academic-session",
            json={"academic_year": "2027-2028"},
            headers=self.admin_headers(),
        )
        self.assertEqual(res_update.status_code, 200)
        self.assertEqual(res_update.get_json()["data"]["current_academic_year"], "2027-2028")

        # Verify student still has batch 2024-2028
        res_student = self.client.get(f"/api/admin/students/{student_id}", headers=self.admin_headers())
        self.assertEqual(res_student.status_code, 200)
        data = res_student.get_json()["data"]
        self.assertEqual(data["batch_year"], "2024-2028")
        self.assertEqual(data["batch_name"], "2024-2028")

    def test_historical_attendance_preserves_original_academic_session(self):
        """
        Requirement 4:
        Historical attendance remains associated with its original academic session.
        """
        with self.app.app_context():
            course = Course(
                department_id=self.dept_id,
                course_code="CSE101",
                course_name="Programming Fundamentals",
                semester=1,
                credits=4,
                batch="2024",
                is_active=True,
            )
            # Course offering in academic year 2024-2025
            offering_hist = CourseOffering(
                course=course,
                academic_year="2024-2025",
                semester=1,
                section="A",
            )
            db.session.add_all([course, offering_hist])
            db.session.commit()

            # Create faculty for attendance session
            fac_user = User(
                name="Prof Hist",
                email="profhist@sams.edu",
                password_hash="hashed_pw",
                role="FACULTY",
                is_active=True,
            )
            db.session.add(fac_user)
            db.session.commit()
            faculty = Faculty(
                user_id=fac_user.user_id,
                department_id=self.dept_id,
                employee_id="FAC001",
                designation="Assistant Professor",
            )
            db.session.add(faculty)
            db.session.commit()

            # Session in 2024-2025
            session = AttendanceSession(
                offering_id=offering_hist.offering_id,
                faculty_id=faculty.faculty_id,
                session_date=date(2024, 10, 15),
                start_time=time(9, 30),
                end_time=time(10, 30),
                status="CLOSED",
            )
            db.session.add(session)
            db.session.commit()

            self.assertEqual(canonical_academic_year(session.offering.academic_year), "2024-2025")

    def test_course_offering_rejects_cohort_range_and_timetable_displays_session(self):
        """
        Requirement 5:
        Course offerings and timetable records display their actual academic session rather
        than student's batch range, and reject multi-year cohort spans.
        """
        with self.app.app_context():
            course = Course(
                department_id=self.dept_id,
                course_code="CSE301",
                course_name="Database Systems",
                semester=5,
                credits=4,
                is_active=True,
            )
            db.session.add(course)
            db.session.commit()
            course_id = course.course_id

        # Attempt to create offering with cohort range 2024-2028 should fail
        res_invalid = self.client.post(
            "/api/admin/course-offerings",
            json={
                "course_id": course_id,
                "academic_year": "2024-2028",
                "semester": 5,
                "section": "A",
            },
            headers=self.admin_headers(),
        )
        self.assertEqual(res_invalid.status_code, 400)
        self.assertIn("1-year academic session", res_invalid.get_json()["message"])

        # Creating offering with valid 1-year academic session succeeds
        res_valid = self.client.post(
            "/api/admin/course-offerings",
            json={
                "course_id": course_id,
                "academic_year": "2026-2027",
                "semester": 5,
                "section": "A",
            },
            headers=self.admin_headers(),
        )
        self.assertEqual(res_valid.status_code, 201)
        offering_id = res_valid.get_json()["data"]["offering_id"]

        # Create timetable entry and verify it displays academic session
        with self.app.app_context():
            entry = TimetableEntry(
                offering_id=offering_id,
                day_of_week="Monday",
                start_time=time(9, 30),
                end_time=time(10, 30),
                room="R101",
            )
            db.session.add(entry)
            db.session.commit()

        res_tt = self.client.get("/api/timetable/admin", headers=self.admin_headers())
        self.assertEqual(res_tt.status_code, 200)
        tt_data = res_tt.get_json()["data"]
        matching_entries = [e for e in tt_data if e["offering_id"] == offering_id]
        self.assertEqual(len(matching_entries), 1)
        self.assertEqual(matching_entries[0]["academic_year"], "2026-2027")

    def test_admin_filter_options_distinguishes_academic_year_from_batch_year(self):
        """
        Requirement 7:
        Filters and reports distinguish academic year (sessions) from batch year.
        """
        res = self.client.get("/api/admin/students/filter-options", headers=self.admin_headers())
        self.assertEqual(res.status_code, 200)
        data = res.get_json()["data"]

        self.assertIn("batches", data)
        self.assertIn("academic_years", data)
        self.assertIn("current_academic_year", data)

        # Batches must contain cohort duration (e.g. 2024-2028)
        batch_names = [b["batch_name"] for b in data["batches"]]
        self.assertIn("2024-2028", batch_names)

        # Academic years must contain 1-year sessions
        for ay in data["academic_years"]:
            self.assertTrue(is_single_academic_session(ay))

    def test_offering_academic_year_lifecycle_and_faculty_display(self):
        """
        Verify:
        1. Creating an offering with academic year 2025-2026.
        2. Editing and persisting the academic year to 2026-2027.
        3. Returning the saved year through GET APIs.
        4. Displaying the correct 1-year session in faculty courses API.
        5. Preserving a student's original admission batch.
        6. Correct academic-year filtering in faculty courses.
        7. Handling existing records with cohort ranges or single years.
        8. Ensuring timetable and attendance associations remain unchanged when editing offering.
        """
        # Create Course, Faculty, and Student
        with self.app.app_context():
            course = Course(
                course_code="BCSE-501",
                course_name="Software Engineering",
                department_id=self.dept_id,
                semester=5,
                credits=4,
                batch="2024",
                is_active=True,
            )
            fac_user = User(name="Prof. Sharma", email="faculty@test.local", password_hash="pw", role="FACULTY")
            stu_user = User(name="Alice Student", email="alice@test.local", password_hash="pw", role="STUDENT")
            db.session.add_all([course, fac_user, stu_user])
            db.session.flush()

            faculty = Faculty(
                user_id=fac_user.user_id,
                employee_id="EMP001",
                designation="Associate Professor",
                department_id=self.dept_id,
            )
            student = Student(
                user_id=stu_user.user_id,
                enrollment_no="ENR2024001",
                department_id=self.dept_id,
                batch_id=self.batch_id,
                semester=5,
                section="A",
                academic_year="2026-2027",
            )
            db.session.add_all([faculty, student])
            db.session.commit()

            course_id = course.course_id
            faculty_id = faculty.faculty_id
            faculty_user_id = fac_user.user_id
            student_id = student.student_id

        # 1. Create Course Offering with academic year 2025-2026
        create_res = self.client.post(
            "/api/admin/course-offerings",
            json={
                "course_id": course_id,
                "faculty_id": faculty_id,
                "academic_year": "2025-2026",
                "semester": 5,
                "section": "A",
            },
            headers=self.admin_headers(),
        )
        self.assertEqual(create_res.status_code, 201)
        offering_id = create_res.get_json()["data"]["offering_id"]

        # Add timetable entry and attendance session to verify associations remain unchanged
        with self.app.app_context():
            tt_entry = TimetableEntry(
                offering_id=offering_id,
                day_of_week="Monday",
                start_time=time(9, 0),
                end_time=time(10, 0),
                room="Room 101",
            )
            att_session = AttendanceSession(
                offering_id=offering_id,
                faculty_id=faculty_id,
                session_date=date(2025, 9, 1),
                start_time=time(9, 0),
                end_time=time(10, 0),
                status="CLOSED",
            )
            enrollment = Enrollment(
                offering_id=offering_id,
                student_id=student_id,
                status="ACTIVE",
            )
            db.session.add_all([tt_entry, att_session, enrollment])
            db.session.commit()
            tt_entry_id = tt_entry.timetable_entry_id
            att_session_id = att_session.session_id

        # 2. Edit and persist the academic year to 2026-2027
        update_res = self.client.put(
            f"/api/admin/course-offerings/{offering_id}",
            json={
                "course_id": course_id,
                "academic_year": "2026-2027",
                "semester": 5,
                "section": "A",
            },
            headers=self.admin_headers(),
        )
        self.assertEqual(update_res.status_code, 200)

        # Reject invalid cohort range on edit
        invalid_edit_res = self.client.put(
            f"/api/admin/course-offerings/{offering_id}",
            json={
                "course_id": course_id,
                "academic_year": "2026-2030",
                "semester": 5,
                "section": "A",
            },
            headers=self.admin_headers(),
        )
        self.assertEqual(invalid_edit_res.status_code, 400)

        # 3. Returning the saved year through the API
        get_res = self.client.get("/api/admin/course-offerings", headers=self.admin_headers())
        self.assertEqual(get_res.status_code, 200)
        all_offerings = get_res.get_json()["data"]
        target_offering = next((o for o in all_offerings if o["offering_id"] == offering_id), None)
        self.assertIsNotNone(target_offering)
        self.assertEqual(target_offering["academic_year"], "2026-2027")

        # 4. Displaying the correct 1-year session in the faculty portal
        with self.app.app_context():
            faculty_token = create_access_token(identity=str(faculty_user_id), additional_claims={"role": "FACULTY"})
            faculty_headers = {"Authorization": f"Bearer {faculty_token}"}

        fac_courses_res = self.client.get("/api/faculty/courses", headers=faculty_headers)
        self.assertEqual(fac_courses_res.status_code, 200)
        fac_courses = fac_courses_res.get_json()["data"]
        matching_fc = next((c for c in fac_courses if c["offering_id"] == offering_id), None)
        self.assertIsNotNone(matching_fc)
        self.assertEqual(matching_fc["academic_year"], "2026-2027")

        # 5. Preserving a student's original admission batch
        fac_course_details_res = self.client.get(f"/api/faculty/courses/{course_id}", headers=faculty_headers)
        self.assertEqual(fac_course_details_res.status_code, 200)
        details_data = fac_course_details_res.get_json()["data"]
        students_roster = details_data["offerings"][0]["students"]
        self.assertEqual(len(students_roster), 1)
        student_record = students_roster[0]
        # Student's cohort admission batch is preserved as 2024-2028
        self.assertEqual(student_record["batch_year"], "2024-2028")
        # While offering's academic session is 1-year session
        self.assertEqual(student_record["academic_year"], "2026-2027")

        # 6. Correct academic-year filtering in faculty courses
        filtered_match = self.client.get("/api/faculty/courses?academic_year=2026-2027", headers=faculty_headers)
        self.assertEqual(len(filtered_match.get_json()["data"]), 1)

        filtered_mismatch = self.client.get("/api/faculty/courses?academic_year=2024-2025", headers=faculty_headers)
        self.assertEqual(len(filtered_mismatch.get_json()["data"]), 0)

        # 7. Handling existing records with cohort ranges or single years safely
        with self.app.app_context():
            # Create a legacy record with cohort range 2026-2030 in DB
            legacy_offering = CourseOffering(
                course_id=course_id,
                faculty_id=faculty_id,
                semester=1,
                section="B",
                academic_year="2026 -2030",
            )
            db.session.add(legacy_offering)
            db.session.commit()
            legacy_id = legacy_offering.offering_id

        # GET API should resolve legacy cohort range to 1-year academic session 2026-2027
        get_legacy_res = self.client.get("/api/admin/course-offerings", headers=self.admin_headers())
        legacy_data = next((o for o in get_legacy_res.get_json()["data"] if o["offering_id"] == legacy_id), None)
        self.assertIsNotNone(legacy_data)
        self.assertEqual(legacy_data["academic_year"], "2026-2027")

        # 8. Ensuring timetable and attendance associations remain unchanged
        with self.app.app_context():
            refreshed_tt = db.session.get(TimetableEntry, tt_entry_id)
            self.assertIsNotNone(refreshed_tt)
            self.assertEqual(refreshed_tt.offering_id, offering_id)

            refreshed_att = db.session.get(AttendanceSession, att_session_id)
            self.assertIsNotNone(refreshed_att)
            self.assertEqual(refreshed_att.offering_id, offering_id)

    def test_batch_column_and_academic_year_in_courses_and_offerings(self):
        """Verify Courses and Course Offerings APIs return separate Batch and Academic Year fields."""
        with self.app.app_context():
            faculty_user = User(name="Test Prof", email="prof@test.local", password_hash="pw", role="FACULTY")
            db.session.add(faculty_user)
            db.session.flush()
            fac = Faculty(user_id=faculty_user.user_id, employee_id="EMP999", designation="Professor", department_id=self.dept_id)
            db.session.add(fac)
            db.session.commit()
            faculty_id = fac.faculty_id

        # 1. Create a course with batch and academic_year
        create_res = self.client.post(
            "/api/admin/courses",
            headers=self.admin_headers(),
            json={
                "course_code": "CS-401",
                "course_name": "Advanced Operating Systems",
                "department_id": self.dept_id,
                "semester": 4,
                "credits": 4,
                "batch": "2025",
                "academic_year": "2026-2027",
            },
        )
        self.assertEqual(create_res.status_code, 201)
        course_id = create_res.get_json()["data"]["course_id"]

        # 2. GET /api/admin/courses should include both batch and academic_year
        get_courses_res = self.client.get("/api/admin/courses", headers=self.admin_headers())
        self.assertEqual(get_courses_res.status_code, 200)
        courses_data = get_courses_res.get_json()["data"]
        matching_course = next((c for c in courses_data if c["course_id"] == course_id), None)
        self.assertIsNotNone(matching_course)
        self.assertEqual(matching_course["batch"], "2025")
        self.assertEqual(matching_course["academic_year"], "2026-2027")

        # 3. Create a course offering for this course
        offering_res = self.client.post(
            "/api/admin/course-offerings",
            headers=self.admin_headers(),
            json={
                "course_id": course_id,
                "faculty_id": faculty_id,
                "batch": "2025",
                "academic_year": "2026-2027",
                "semester": 4,
                "section": "A",
            },
        )
        self.assertEqual(offering_res.status_code, 201)
        offering_id = offering_res.get_json()["data"]["offering_id"]

        # 4. GET /api/admin/course-offerings should return batch immediately alongside academic_year
        get_offerings_res = self.client.get("/api/admin/course-offerings", headers=self.admin_headers())
        self.assertEqual(get_offerings_res.status_code, 200)
        offerings_data = get_offerings_res.get_json()["data"]
        matching_offering = next((o for o in offerings_data if o["offering_id"] == offering_id), None)
        self.assertIsNotNone(matching_offering)
        self.assertEqual(matching_offering["batch"], "2025")
        self.assertEqual(matching_offering["academic_year"], "2026-2027")

        # 5. Offering without course.batch resolves batch from enrolled student's batch
        with self.app.app_context():
            # Create a course without batch
            no_batch_course = Course(
                course_code="CS-402",
                course_name="Distributed Systems",
                department_id=self.dept_id,
                semester=5,
                credits=3,
                batch=None,
            )
            db.session.add(no_batch_course)
            db.session.flush()

            no_batch_offering = CourseOffering(
                course_id=no_batch_course.course_id,
                faculty_id=faculty_id,
                academic_year="2026-2027",
                semester=5,
                section="B",
            )
            db.session.add(no_batch_offering)
            db.session.flush()

            # Create enrolled student with batch
            stu_user = User(name="Enrolled Student", email="enrolled@test.local", password_hash="pw", role="STUDENT")
            db.session.add(stu_user)
            db.session.flush()

            stu_batch = Batch(batch_name="2024")
            db.session.add(stu_batch)
            db.session.flush()

            stu = Student(
                user_id=stu_user.user_id,
                department_id=self.dept_id,
                batch_id=stu_batch.batch_id,
                enrollment_no="ENR2024099",
                semester=5,
                section="B",
                academic_year="2026-2027",
            )
            db.session.add(stu)
            db.session.flush()

            enrollment = Enrollment(
                offering_id=no_batch_offering.offering_id,
                student_id=stu.student_id,
                status="ENROLLED",
            )
            db.session.add(enrollment)
            db.session.commit()
            no_batch_offering_id = no_batch_offering.offering_id

        # GET /api/admin/course-offerings should resolve the batch via enrollment
        res_resolved = self.client.get("/api/admin/course-offerings", headers=self.admin_headers())
        self.assertEqual(res_resolved.status_code, 200)
        resolved_offering = next((o for o in res_resolved.get_json()["data"] if o["offering_id"] == no_batch_offering_id), None)
        self.assertIsNotNone(resolved_offering)
        self.assertEqual(resolved_offering["batch"], "2024")
        self.assertEqual(resolved_offering["academic_year"], "2026-2027")

    def test_course_offerings_resolves_teaching_session_and_preserves_historical_records(self):
        """
        Regression test:
        1. Affected offerings stamped with batch admission year (e.g. 2024-2025 for Sem 5,
           or 2023-2024 for Sem 7) are resolved to their current teaching session (2026-2027).
        2. Valid historical offerings (e.g. Batch 2024 in Sem 1 in 2024-2025, or Batch 2023 in Sem 3 in 2024-2025)
           preserve their historical academic year (2024-2025) and are NOT forced to 2026-2027.
        3. Offerings already set to 2026-2027 remain unchanged.
        """
        with self.app.app_context():
            # Courses
            c_sem5 = Course(course_code="BCSE-514", course_name="Big Data", department_id=self.dept_id, semester=5, credits=3, batch="2024")
            c_sem7 = Course(course_code="CS103", course_name="Networks", department_id=self.dept_id, semester=7, credits=3, batch="2023")
            c_hist_sem1 = Course(course_code="BCSE-101", course_name="Intro CS", department_id=self.dept_id, semester=1, credits=3, batch="2024")
            c_hist_sem3 = Course(course_code="BCSE-301", course_name="Data Structures", department_id=self.dept_id, semester=3, credits=3, batch="2023")
            c_curr_sem1 = Course(course_code="BCSE-001", course_name="Problem Solving", department_id=self.dept_id, semester=1, credits=3, batch="2026")

            db.session.add_all([c_sem5, c_sem7, c_hist_sem1, c_hist_sem3, c_curr_sem1])
            db.session.flush()

            # Offerings
            # 1. Affected Offering: Batch 2024, Sem 5, stored as cohort admission session '2024 -2025'
            off_affected_sem5 = CourseOffering(course_id=c_sem5.course_id, semester=5, section="B", academic_year="2024 -2025")
            # 2. Affected Offering: Batch 2023, Sem 7, stored as cohort admission session '2023 -2024'
            off_affected_sem7 = CourseOffering(course_id=c_sem7.course_id, semester=7, section="A", academic_year="2023 -2024")
            # 3. Historical Offering: Batch 2024, Sem 1, taught in '2024-2025'
            off_hist_sem1 = CourseOffering(course_id=c_hist_sem1.course_id, semester=1, section="A", academic_year="2024-2025")
            # 4. Historical Offering: Batch 2023, Sem 3, taught in '2024-2025'
            off_hist_sem3 = CourseOffering(course_id=c_hist_sem3.course_id, semester=3, section="A", academic_year="2024-2025")
            # 5. Current Offering: Batch 2026, Sem 1, '2026-2027'
            off_curr_sem1 = CourseOffering(course_id=c_curr_sem1.course_id, semester=1, section="A", academic_year="2026-2027")

            db.session.add_all([off_affected_sem5, off_affected_sem7, off_hist_sem1, off_hist_sem3, off_curr_sem1])
            db.session.commit()

            id_aff_sem5 = off_affected_sem5.offering_id
            id_aff_sem7 = off_affected_sem7.offering_id
            id_hist_sem1 = off_hist_sem1.offering_id
            id_hist_sem3 = off_hist_sem3.offering_id
            id_curr_sem1 = off_curr_sem1.offering_id

        res = self.client.get("/api/admin/course-offerings", headers=self.admin_headers())
        self.assertEqual(res.status_code, 200)
        all_offs = {o["offering_id"]: o for o in res.get_json()["data"]}

        # 1. Affected sem 5 offering resolves to current teaching session 2026-2027
        self.assertEqual(all_offs[id_aff_sem5]["academic_year"], "2026-2027")
        self.assertEqual(all_offs[id_aff_sem5]["batch"], "2024")
        self.assertEqual(all_offs[id_aff_sem5]["raw_academic_year"], "2024 -2025")

        # 2. Affected sem 7 offering resolves to current teaching session 2026-2027
        self.assertEqual(all_offs[id_aff_sem7]["academic_year"], "2026-2027")
        self.assertEqual(all_offs[id_aff_sem7]["batch"], "2023")
        self.assertEqual(all_offs[id_aff_sem7]["raw_academic_year"], "2023 -2024")

        # 3. Historical sem 1 offering preserves 2024-2025
        self.assertEqual(all_offs[id_hist_sem1]["academic_year"], "2024-2025")
        self.assertEqual(all_offs[id_hist_sem1]["batch"], "2024")

        # 4. Historical sem 3 offering preserves 2024-2025
        self.assertEqual(all_offs[id_hist_sem3]["academic_year"], "2024-2025")
        self.assertEqual(all_offs[id_hist_sem3]["batch"], "2023")

        # 5. Current sem 1 offering remains 2026-2027
        self.assertEqual(all_offs[id_curr_sem1]["academic_year"], "2026-2027")
        self.assertEqual(all_offs[id_curr_sem1]["batch"], "2026")


if __name__ == "__main__":
    unittest.main()

