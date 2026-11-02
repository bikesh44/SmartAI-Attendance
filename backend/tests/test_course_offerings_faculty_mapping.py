import pytest
from flask_jwt_extended import create_access_token, get_csrf_token
from sqlalchemy import event

from app import create_app, db
from app.models import (
    Course,
    CourseOffering,
    Department,
    Faculty,
    TimetableEntry,
    User,
)


@pytest.fixture
def app():
    app = create_app()
    app.config["TESTING"] = True
    return app


@pytest.fixture
def client(app):
    return app.test_client()


def get_admin_headers(client, app):
    with app.app_context():
        admin_user = User.query.filter_by(role="ADMIN").first()
        token = create_access_token(
            identity=str(admin_user.user_id),
            additional_claims={"role": "ADMIN"},
        )
        csrf = get_csrf_token(token)
        client.set_cookie("access_token_cookie", token)
        client.set_cookie("csrf_access_token", csrf)
        return {"X-CSRF-TOKEN": csrf}


def test_course_offerings_returns_real_faculty_name(app, client):
    """Offerings with a valid faculty assignment must return the real faculty display name."""
    headers = get_admin_headers(client, app)

    assigned_id = None
    with app.app_context():
        offering = CourseOffering.query.filter(CourseOffering.faculty_id.isnot(None)).first()
        if not offering:
            offering = CourseOffering.query.first()
            faculty = Faculty.query.first()
            if offering and faculty:
                offering.faculty_id = faculty.faculty_id
                db.session.commit()
                assigned_id = offering.offering_id

    try:
        res = client.get("/api/admin/course-offerings", headers=headers)
        assert res.status_code == 200
        data = res.get_json()
        assert data["success"] is True

        assigned_offerings = [o for o in data["data"] if o["faculty_id"] is not None]
        assert len(assigned_offerings) > 0, "Expected at least one assigned course offering in DB"

        for off in assigned_offerings:
            assert off["faculty_name"] is not None
            assert not off["faculty_name"].startswith("Faculty #null")
            assert off["faculty_name"] != "Unassigned"
            assert len(off["faculty_name"].strip()) > 0
    finally:
        if assigned_id is not None:
            with app.app_context():
                off = db.session.get(CourseOffering, assigned_id)
                if off:
                    off.faculty_id = None
                    db.session.commit()


def test_course_offerings_without_assignment_returns_unassigned(app, client):
    """Offerings without a faculty assignment must return 'Unassigned' and not 'Faculty #null'."""
    headers = get_admin_headers(client, app)
    res = client.get("/api/admin/course-offerings", headers=headers)
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True

    unassigned_offerings = [o for o in data["data"] if o["faculty_id"] is None]
    assert len(unassigned_offerings) > 0, "Expected at least one unassigned course offering in DB"

    for off in unassigned_offerings:
        assert off["faculty_id"] is None
        assert off["faculty_name"] == "Unassigned"
        assert off["faculty_name"] != "Faculty #null"


def test_course_offerings_query_performance_and_no_n_plus_1(app, client):
    """Fetching course offerings must be constant-query (eager loaded), not N+1."""
    headers = get_admin_headers(client, app)

    queries = []
    def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        queries.append(statement)

    with app.app_context():
        event.listen(db.engine, "before_cursor_execute", before_cursor_execute)
        try:
            res = client.get("/api/admin/course-offerings", headers=headers)
            assert res.status_code == 200
            # Constant number of queries regardless of 200+ course offerings:
            # 1: offerings joinedload course and faculty user
            # 2: group by offering_id enrollment count
            # 3: group by offering_id attendance session count
            assert len(queries) <= 6, f"Expected <= 6 queries, got {len(queries)}"
        finally:
            event.remove(db.engine, "before_cursor_execute", before_cursor_execute)


def test_timetable_commit_persists_faculty_and_reupload_does_not_duplicate(app, client):
    """
    Timetable import commit must persist faculty assignment on CourseOffering,
    and re-uploading the same timetable must not create duplicate offerings or entries.
    """
    headers = get_admin_headers(client, app)

    with app.app_context():
        course = Course.query.first()
        faculty = Faculty.query.first()
        faculty_id = faculty.faculty_id
        expected_faculty_name = faculty.user.name
        course_id = course.course_id
        test_ay = "2029-2030"
        test_sec = "TEST-SEC-1"

        # Clean up any previous test artifact
        existing_off = CourseOffering.query.filter_by(
            course_id=course_id,
            section=test_sec,
            academic_year=test_ay,
        ).first()
        if existing_off:
            TimetableEntry.query.filter_by(offering_id=existing_off.offering_id).delete()
            db.session.delete(existing_off)
            db.session.commit()

    payload = {
        "academic_year": "2029-2030",
        "import_mode": "add_missing",
        "entries": [
            {
                "course_id": course_id,
                "faculty_id": faculty_id,
                "semester": 1,
                "section": "TEST-SEC-1",
                "room": "Room-901",
                "day_of_week": "Monday",
                "start_time": "09:00",
                "end_time": "10:00",
            }
        ],
    }

    # First upload
    res1 = client.post("/api/timetable/import/commit", json=payload, headers=headers)
    assert res1.status_code == 200
    d1 = res1.get_json()
    assert d1["success"] is True
    assert d1["data"]["created_offerings"] == 1
    assert d1["data"]["created_entries"] == 1

    with app.app_context():
        off = CourseOffering.query.filter_by(
            course_id=course_id,
            section="TEST-SEC-1",
            academic_year="2029-2030",
        ).first()
        assert off is not None
        assert off.faculty_id == faculty_id
        off_id = off.offering_id

    # Verify through /api/admin/course-offerings endpoint
    res_list = client.get("/api/admin/course-offerings", headers=headers)
    assert res_list.status_code == 200
    items = [x for x in res_list.get_json()["data"] if x["offering_id"] == off_id]
    assert len(items) == 1
    assert items[0]["faculty_name"] == expected_faculty_name
    assert items[0]["faculty_id"] == faculty_id

    # Second upload (re-upload identical timetable)
    res2 = client.post("/api/timetable/import/commit", json=payload, headers=headers)
    assert res2.status_code == 200
    d2 = res2.get_json()
    assert d2["success"] is True
    # Offering must NOT be duplicated
    assert d2["data"]["created_offerings"] == 0
    # Entry must be skipped without duplication
    assert d2["data"]["skipped_entries"] == 1

    with app.app_context():
        matching_offs = CourseOffering.query.filter_by(
            course_id=course_id,
            section="TEST-SEC-1",
            academic_year="2029-2030",
        ).all()
        assert len(matching_offs) == 1, "Duplicate course offering created on re-upload!"

        # Clean up
        to_del = db.session.get(CourseOffering, off_id)
        if to_del:
            TimetableEntry.query.filter_by(offering_id=off_id).delete()
            db.session.delete(to_del)
            db.session.commit()
