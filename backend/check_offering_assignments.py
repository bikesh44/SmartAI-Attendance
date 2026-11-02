from app import create_app
from sqlalchemy import text

app = create_app()

with app.app_context():
    db = app.extensions["sqlalchemy"]

    queries = {
        "Offering assignment summary": """
            SELECT
                COUNT(*) AS total_offerings,
                SUM(faculty_id IS NULL) AS unassigned_offerings,
                COUNT(DISTINCT faculty_id) AS distinct_nonnull_faculty_ids
            FROM course_offerings
        """,
        "Offerings grouped by faculty": """
            SELECT faculty_id, COUNT(*) AS offering_count
            FROM course_offerings
            GROUP BY faculty_id
            ORDER BY faculty_id
        """,
        "Faculty with no offerings": """
            SELECT f.faculty_id, f.user_id, u.name
            FROM faculty f
            JOIN users u ON u.user_id = f.user_id
            LEFT JOIN course_offerings co ON co.faculty_id = f.faculty_id
            GROUP BY f.faculty_id, f.user_id, u.name
            HAVING COUNT(co.offering_id) = 0
            ORDER BY f.faculty_id
        """
    }

    for title, sql in queries.items():
        print(f"\n--- {title} ---")
        rows = db.session.execute(text(sql)).mappings().all()
        for row in rows:
            print(dict(row))
