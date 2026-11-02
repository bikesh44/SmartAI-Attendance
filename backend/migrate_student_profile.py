from app import create_app, db
from sqlalchemy import text, inspect

app = create_app()

with app.app_context():
    insp = inspect(db.engine)
    existing_cols = {c['name'] for c in insp.get_columns('students')}

    columns_to_add = [
        ('photo_url', 'TEXT NULL'),
        ('signature_url', 'TEXT NULL'),
        ('father_name', 'VARCHAR(100) NULL'),
        ('mother_name', 'VARCHAR(100) NULL'),
        ('phone', 'VARCHAR(20) NULL'),
        ('guardian_phone', 'VARCHAR(20) NULL'),
        ('blood_group', 'VARCHAR(10) NULL'),
        ('gender', 'VARCHAR(20) NULL'),
        ('date_of_birth', 'VARCHAR(50) NULL'),
        ('address', 'VARCHAR(255) NULL'),
        ('city', 'VARCHAR(100) NULL'),
        ('state', 'VARCHAR(100) NULL'),
        ('pin_code', 'VARCHAR(20) NULL'),
        ('country', "VARCHAR(100) NULL DEFAULT 'India'"),
        ('emergency_contact_name', 'VARCHAR(100) NULL'),
        ('emergency_contact_phone', 'VARCHAR(20) NULL'),
        ('admission_date', 'VARCHAR(50) NULL'),
    ]

    with db.engine.begin() as conn:
        for col_name, col_def in columns_to_add:
            if col_name not in existing_cols:
                sql = f"ALTER TABLE students ADD COLUMN {col_name} {col_def}"
                conn.execute(text(sql))
                print(f"Added column {col_name}")
            else:
                print(f"Column {col_name} already exists")

    print("Student table migration complete!")
