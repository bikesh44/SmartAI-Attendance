from app import create_app
from sqlalchemy import text

app = create_app()

with app.app_context():
    db = app.extensions["sqlalchemy"]

    tables = db.session.execute(
        text("""
            SELECT TABLE_NAME
            FROM INFORMATION_SCHEMA.TABLES
            WHERE TABLE_SCHEMA = DATABASE()
              AND TABLE_NAME LIKE '%timetable%'
        """)
    ).scalars().all()

    print("Timetable tables:", tables)

    for table in tables:
        print(f"\n--- {table} ---")
        columns = db.session.execute(
            text("""
                SELECT COLUMN_NAME, COLUMN_TYPE
                FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_SCHEMA = DATABASE()
                  AND TABLE_NAME = :table_name
                ORDER BY ORDINAL_POSITION
            """),
            {"table_name": table},
        ).mappings().all()

        for column in columns:
            print(f"{column['COLUMN_NAME']} ({column['COLUMN_TYPE']})")
