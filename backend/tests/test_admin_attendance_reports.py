import pytest
from flask_jwt_extended import create_access_token, get_csrf_token

from app import create_app, db
from app.models import User, Student, Faculty, Course, CourseOffering, AttendanceSession, AttendanceRecord


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


def test_admin_attendance_endpoints_access_control(app, client):
    with app.app_context():
        # 1. Unauthenticated request must return 401
        res = client.get("/api/admin/attendance/dashboard")
        assert res.status_code == 401

        # 2. Student role must return 403
        student_user = User.query.filter_by(role="STUDENT").first()
        if student_user:
            headers = get_auth_headers(client, student_user.user_id, "STUDENT")
            res = client.get("/api/admin/attendance/dashboard", headers=headers)
            assert res.status_code == 403

        # 3. Faculty role must return 403
        faculty_user = User.query.filter_by(role="FACULTY").first()
        if faculty_user:
            headers = get_auth_headers(client, faculty_user.user_id, "FACULTY")
            res = client.get("/api/admin/attendance/dashboard", headers=headers)
            assert res.status_code == 403


def test_admin_attendance_reports_workflow(app, client):
    with app.app_context():
        admin_user = User.query.filter_by(role="ADMIN").first()
        if not admin_user:
            pytest.skip("No admin user found in database")

        headers = get_auth_headers(client, admin_user.user_id, "ADMIN")

        # 1. Test Filter Options
        res = client.get("/api/admin/attendance/filter-options", headers=headers)
        assert res.status_code == 200
        res_json = res.get_json()
        assert res_json.get("success") is True
        assert "academic_years" in res_json
        assert "semesters" in res_json
        assert "sections" in res_json
        assert "courses" in res_json
        assert "faculty" in res_json
        assert "date_range" in res_json

        # 2. Test Dashboard KPI & Chart Aggregations
        res_dash = client.get("/api/admin/attendance/dashboard", headers=headers)
        assert res_dash.status_code == 200
        dash_data = res_dash.get_json()
        assert dash_data.get("success") is True
        assert "kpi" in dash_data
        assert "total_present" in dash_data["kpi"]
        assert "total_absent" in dash_data["kpi"]
        assert "total_classes" in dash_data["kpi"]
        assert "attendance_rate" in dash_data["kpi"]
        assert "trend" in dash_data
        assert "by_course" in dash_data
        assert "by_section" in dash_data

        # 3. Test Attendance Records List with Pagination
        res_rec = client.get("/api/admin/attendance/records?page=1&per_page=10", headers=headers)
        assert res_rec.status_code == 200
        rec_data = res_rec.get_json()
        assert rec_data.get("success") is True
        assert "data" in rec_data
        assert "total_records" in rec_data
        assert "total_pages" in rec_data
        assert rec_data["page"] == 1

        # 4. Test Single Record Detail (404 on invalid id)
        res_detail_404 = client.get("/api/admin/attendance/records/999999", headers=headers)
        assert res_detail_404.status_code == 404

        # 5. Test Export CSV
        res_export = client.get("/api/admin/attendance/export", headers=headers)
        assert res_export.status_code == 200
        assert "text/csv" in res_export.content_type
        assert "attendance_report" in res_export.headers.get("Content-Disposition", "")

        # 6. Test Date Validation: from_date > to_date returns 400
        res_invalid_date = client.get(
            "/api/admin/attendance/dashboard?from_date=2026-10-25&to_date=2026-10-20",
            headers=headers,
        )
        assert res_invalid_date.status_code == 400
        assert "cannot be later than" in res_invalid_date.get_json()["message"]

        res_invalid_date_rec = client.get(
            "/api/admin/attendance/records?from_date=2026-10-25&to_date=2026-10-20",
            headers=headers,
        )
        assert res_invalid_date_rec.status_code == 400

        res_invalid_date_exp = client.get(
            "/api/admin/attendance/export?from_date=2026-10-25&to_date=2026-10-20",
            headers=headers,
        )
        assert res_invalid_date_exp.status_code == 400

        # 7. Test Invalid Date Format returns 400
        res_malformed_date = client.get(
            "/api/admin/attendance/dashboard?from_date=not-a-date",
            headers=headers,
        )
        assert res_malformed_date.status_code == 400
        assert "YYYY-MM-DD" in res_malformed_date.get_json()["message"]

        # 8. Test Neutral Filters: Academic Year 'All' does not break query
        res_neutral = client.get(
            "/api/admin/attendance/dashboard?academic_year=All&semester=All&section=All",
            headers=headers,
        )
        assert res_neutral.status_code == 200
        assert res_neutral.get_json()["success"] is True


def test_admin_attendance_records_semester_section_fields_and_export(app, client):
    with app.app_context():
        admin_user = User.query.filter_by(role="ADMIN").first()
        if not admin_user:
            pytest.skip("No admin user found in database")

        headers = get_auth_headers(client, admin_user.user_id, "ADMIN")

        # 1. Verify filter-options includes semester_sections mapping
        res_fo = client.get("/api/admin/attendance/filter-options", headers=headers)
        assert res_fo.status_code == 200
        fo_data = res_fo.get_json()
        assert "semester_sections" in fo_data
        assert isinstance(fo_data["semester_sections"], dict)

        # 2. Test query parameter on filter-options for specific semester
        if fo_data.get("semesters"):
            test_sem = fo_data["semesters"][0]
            res_fo_sem = client.get(f"/api/admin/attendance/filter-options?semester={test_sem}", headers=headers)
            assert res_fo_sem.status_code == 200
            fo_sem_data = res_fo_sem.get_json()
            assert "sections" in fo_sem_data

        # 3. Test /records returns semester, section, and semester_section
        res_rec = client.get("/api/admin/attendance/records?page=1&per_page=20", headers=headers)
        assert res_rec.status_code == 200
        rec_data = res_rec.get_json()
        assert rec_data.get("success") is True
        records = rec_data.get("data", [])
        if records:
            for r in records:
                assert "semester" in r
                assert "section" in r
                assert "semester_section" in r
                # Verify formatting: if semester or section present, formatted properly
                if r["semester"] is not None and r["section"] is not None:
                    assert r["semester_section"] == f"Semester {r['semester']} / Section {r['section']}"
                elif r["semester"] is None and r["section"] is None:
                    assert r["semester_section"] == "N/A"

            # Test single record endpoint also returns semester, section, semester_section
            rec_id = records[0]["attendance_id"]
            res_single = client.get(f"/api/admin/attendance/records/{rec_id}", headers=headers)
            assert res_single.status_code == 200
            single_data = res_single.get_json().get("data", {})
            assert "semester" in single_data
            assert "section" in single_data
            assert "semester_section" in single_data

        # 4. Test Export CSV contains 'Semester / Section' header
        res_exp = client.get("/api/admin/attendance/export", headers=headers)
        assert res_exp.status_code == 200
        csv_text = res_exp.data.decode("utf-8")
        assert "Semester / Section" in csv_text


def test_admin_attendance_semester_and_section_filtering(app, client):
    with app.app_context():
        admin_user = User.query.filter_by(role="ADMIN").first()
        if not admin_user:
            pytest.skip("No admin user found in database")

        headers = get_auth_headers(client, admin_user.user_id, "ADMIN")

        # Fetch filter options to obtain available semesters/sections
        res_fo = client.get("/api/admin/attendance/filter-options", headers=headers)
        fo_data = res_fo.get_json()
        semesters = fo_data.get("semesters", [])
        sections = fo_data.get("sections", [])

        # Fetch total records without filters
        res_all = client.get("/api/admin/attendance/records?page=1&per_page=50", headers=headers)
        total_unfiltered = res_all.get_json().get("total_records", 0)

        # Semester filter test
        if semesters:
            sem_val = semesters[0]
            res_sem = client.get(f"/api/admin/attendance/records?semester={sem_val}&page=1&per_page=50", headers=headers)
            assert res_sem.status_code == 200
            sem_json = res_sem.get_json()
            assert sem_json.get("success") is True
            # All returned records must have matching semester
            for rec in sem_json.get("data", []):
                assert str(rec["semester"]) == str(sem_val)

            # Dashboard should also filter by semester
            res_dash_sem = client.get(f"/api/admin/attendance/dashboard?semester={sem_val}", headers=headers)
            assert res_dash_sem.status_code == 200
            assert res_dash_sem.get_json().get("success") is True

        # Section filter test
        if sections:
            sec_val = sections[0]
            res_sec = client.get(f"/api/admin/attendance/records?section={sec_val}&page=1&per_page=50", headers=headers)
            assert res_sec.status_code == 200
            sec_json = res_sec.get_json()
            assert sec_json.get("success") is True
            for rec in sec_json.get("data", []):
                assert str(rec["section"]).strip().lower() == str(sec_val).strip().lower()

        # Both Semester and Section filter test
        if semesters and sections:
            sem_val = semesters[0]
            sec_val = sections[0]
            res_both = client.get(f"/api/admin/attendance/records?semester={sem_val}&section={sec_val}&page=1&per_page=50", headers=headers)
            assert res_both.status_code == 200
            both_json = res_both.get_json()
            assert both_json.get("success") is True
            for rec in both_json.get("data", []):
                assert str(rec["semester"]) == str(sem_val)
                assert str(rec["section"]).strip().lower() == str(sec_val).strip().lower()

        # Test All Semesters / All Sections returns all authorized records
        res_all_again = client.get("/api/admin/attendance/records?semester=All&section=All&page=1&per_page=50", headers=headers)
        assert res_all_again.status_code == 200
        assert res_all_again.get_json().get("total_records", 0) == total_unfiltered


def test_admin_attendance_authoritative_mapping_and_missing_values(app, client):
    with app.app_context():
        admin_user = User.query.filter_by(role="ADMIN").first()
        if not admin_user:
            pytest.skip("No admin user found in database")

        headers = get_auth_headers(client, admin_user.user_id, "ADMIN")

        # Verify historical CourseOffering semester/section takes precedence over Student current
        record = (
            db.session.query(AttendanceRecord)
            .join(AttendanceSession, AttendanceRecord.session_id == AttendanceSession.session_id)
            .join(CourseOffering, AttendanceSession.offering_id == CourseOffering.offering_id)
            .join(Student, AttendanceRecord.student_id == Student.student_id)
            .first()
        )

        if record:
            res = client.get(f"/api/admin/attendance/records/{record.attendance_id}", headers=headers)
            assert res.status_code == 200
            data = res.get_json().get("data", {})
            # Course offering semester and section must match what is returned
            offering = record.session.offering
            assert data["semester"] == offering.semester
            assert data["section"] == offering.section
