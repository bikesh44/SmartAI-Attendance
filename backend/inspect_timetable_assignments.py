from app import create_app
from sqlalchemy import text

app = create_app()

with app.app_context():
    db = app.extensions["sqlalchemy"]

    sql = text("""
        SELECT
            co.offering_id,
            co.faculty_id,
            c.course_code,
            c.course_name,
            c.semester,
            co.section,
            co.academic_year,
            te.day_of_week,
            te.start_time,
            te.end_time,
            te.room
        FROM course_offerings co
        LEFT JOIN courses c
            ON c.course_id = co.course_id
        LEFT JOIN timetable_entries te
            ON te.offering_id = co.offering_id
        ORDER BY
            c.semester,
            c.course_code,
            co.section,
            te.day_of_week,
            te.start_time
    """)

    rows = db.session.execute(sql).mappings().all()

    print("Total timetable/course rows:", len(rows))
    for row in rows:
        print(dict(row))
