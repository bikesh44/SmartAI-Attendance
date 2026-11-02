from app import create_app
from sqlalchemy import text

app = create_app()

with app.app_context():
    db = app.extensions["sqlalchemy"]

    tables = [
        "users",
        "faculty",
        "course_offerings",
        "courses",
        "enrollments",
        "attendance_sessions",
        "attendance_records",
    ]

    for table in tables:
        print(f"\n--- {table} ---")
        try:
            rows = db.session.execute(
                text("""
                    SELECT COLUMN_NAME, COLUMN_TYPE
                    FROM INFORMATION_SCHEMA.COLUMNS
                    WHERE TABLE_SCHEMA = DATABASE()
                      AND TABLE_NAME = :table_name
                    ORDER BY ORDINAL_POSITION
                """),
                {"table_name": table},
            ).mappings().all()

            if not rows:
                print("Table not found")
            else:
                for row in rows:
                    print(f"{row['COLUMN_NAME']} ({row['COLUMN_TYPE']})")
        except Exception as exc:
            print(f"Error: {exc}")

    print("\n--- Faculty user relationships ---")
    try:
        rows = db.session.execute(
            text("""
                SELECT u.user_id, u.name, u.role, f.faculty_id
                FROM users u
                LEFT JOIN faculty f ON f.user_id = u.user_id
                WHERE UPPER(u.role) = :role
                ORDER BY u.user_id
            """),
            {"role": "FACULTY"},
        ).mappings().all()

        for row in rows:
            print(dict(row))
    except Exception as exc:
        print(f"Error: {exc}")
