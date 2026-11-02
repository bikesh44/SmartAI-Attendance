from app import create_app
from sqlalchemy import text

app = create_app()

with app.app_context():
    db = app.extensions["sqlalchemy"]

    query = text("""
        SELECT
            co.offering_id,
            co.faculty_id,
            f.user_id,
            u.name AS faculty_name,
            co.course_id,
            c.course_code,
            c.course_name,
            co.section,
            co.semester,
            co.academic_year
        FROM course_offerings co
        LEFT JOIN faculty f ON f.faculty_id = co.faculty_id
        LEFT JOIN users u ON u.user_id = f.user_id
        LEFT JOIN courses c ON c.course_id = co.course_id
        ORDER BY co.faculty_id, co.offering_id
    """)

    rows = db.session.execute(query).mappings().all()

    print(f"Total course offerings: {len(rows)}")
    for row in rows:
        print(dict(row))
