import pytest
from flask_jwt_extended import create_access_token, get_csrf_token

from app import create_app, db
from app.models import User, Student, Faculty, Enrollment, CourseOffering, Course, TimetableEntry, AttendanceRecord


@pytest.fixture
def app():
    app = create_app()
    app.config["TESTING"] = True
    return app


@pytest.fixture
def client(app):
    return app.test_client()


def get_auth_headers(client, user_id, role):
    token = create_access_token(
        identity=str(user_id),
        additional_claims={"role": role},
    )
    csrf = get_csrf_token(token)
    client.set_cookie("access_token_cookie", token)
    client.set_cookie("csrf_access_token", csrf)
    return {"X-CSRF-TOKEN": csrf}


def test_student_profile_zero_records_fallback(app, client):
    """Fix 2: Verify student profile returns 0.0 attendance rate when student has 0 records."""
    with app.app_context():
        # Find or create a student with 0 attendance records
        students = Student.query.all()
        target_student = None
        for s in students:
            rec_count = AttendanceRecord.query.filter_by(student_id=s.student_id).count()
            if rec_count == 0:
                target_student = s
                break

        if not target_student:
            pytest.skip("All existing students have attendance records; skipping zero-record student check.")

        headers = get_auth_headers(client, target_student.user_id, "STUDENT")
        res = client.get("/api/student/profile", headers=headers)
        assert res.status_code == 200
        data = res.get_json()["data"]
        stats = data.get("stats", {})
        assert stats.get("total_attendance_records") == 0
        assert stats.get("attendance_percentage") == 0.0  # Must be 0.0, NOT 100.0


def test_student_dashboard_zero_session_week_trend(app, client):
    """Fix 3: Verify that weeks with zero sessions do not inherit overall_attendance."""
    with app.app_context():
        student = Student.query.first()
        if not student:
            pytest.skip("No student in database")

        headers = get_auth_headers(client, student.user_id, "STUDENT")
        res = client.get("/api/student/dashboard?weeks=12", headers=headers)
        assert res.status_code == 200
        data = res.get_json()["data"]
        trend = data.get("attendance_trend", {})
        points = trend.get("points", [])
        assert len(points) > 0

        # For any point with total == 0, rate must be None
        for pt in points:
            if pt.get("total") == 0:
                assert pt.get("rate") is None, f"Zero-session week has fabricated rate: {pt}"


def test_faculty_missing_profile_returns_404_without_auto_provisioning(app, client):
    """Fix 4: Verify that a faculty user without a Faculty table entry receives 404 without synthetic creation."""
    with app.app_context():
        # Create a transient test user with role FACULTY that has NO entry in Faculty table
        test_email = "temp_unprovisioned_faculty@test.com"
        user = User.query.filter_by(email=test_email).first()
        if not user:
            user = User(
                name="Transient Faculty User",
                email=test_email,
                role="FACULTY",
                password_hash="fakehash",
                is_active=True,
            )
            db.session.add(user)
            db.session.commit()

        try:
            # Ensure no Faculty profile exists for this user_id
            existing_fac = Faculty.query.filter_by(user_id=user.user_id).first()
            if existing_fac:
                db.session.delete(existing_fac)
                db.session.commit()

            headers = get_auth_headers(client, user.user_id, "FACULTY")
            res = client.get("/api/faculty/profile", headers=headers)

            # Must return 404 with instruction to contact administration
            assert res.status_code == 404
            json_body = res.get_json()
            assert json_body["success"] is False
            assert "contact administration" in json_body["message"].lower()

            # Verify no synthetic record was created
            after_fac = Faculty.query.filter_by(user_id=user.user_id).first()
            assert after_fac is None, "A synthetic faculty profile was illegally inserted!"

        finally:
            # Cleanup transient test user
            db.session.delete(user)
            db.session.commit()


def test_student_timetable_endpoint_authorization_and_data(app, client):
    """Fix 1 backend: Verify student timetable endpoint authorization and response format."""
    with app.app_context():
        # 1. Unauthenticated request must return 401
        res_unauth = client.get("/api/timetable/student")
        assert res_unauth.status_code == 401

        # 2. Faculty token must return 403
        faculty_user = User.query.filter_by(role="FACULTY").first()
        if faculty_user:
            headers_fac = get_auth_headers(client, faculty_user.user_id, "FACULTY")
            res_fac = client.get("/api/timetable/student", headers=headers_fac)
            assert res_fac.status_code == 403

        # 3. Authenticated student receives 200 with structured timetable entries
        student = Student.query.first()
        if student:
            headers_stu = get_auth_headers(client, student.user_id, "STUDENT")
            res_stu = client.get("/api/timetable/student", headers=headers_stu)
            assert res_stu.status_code == 200
            json_data = res_stu.get_json()
            assert json_data["success"] is True
            assert isinstance(json_data["data"], list)
