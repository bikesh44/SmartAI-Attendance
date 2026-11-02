"""Enforce unique active face profile per student.

Revision ID: 93f4e157b8a1
Revises: eb61b4d69f1f
Create Date: 2026-10-22 22:30:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "93f4e157b8a1"
down_revision = "eb61b4d69f1f"
branch_labels = None
depends_on = None

TABLE_NAME = "face_profiles"
INDEX_NAME = "uq_student_active_face"
GENERATED_COLUMN = "active_student_id"


def upgrade():
    bind = op.get_bind()

    if bind.dialect.name == "mysql":
        columns = {
            column["name"]
            for column in sa.inspect(bind).get_columns(TABLE_NAME)
        }

        if GENERATED_COLUMN not in columns:
            op.add_column(
                TABLE_NAME,
                sa.Column(
                    GENERATED_COLUMN,
                    sa.Integer(),
                    sa.Computed(
                        "CASE WHEN is_active = 1 "
                        "THEN student_id ELSE NULL END",
                        persisted=True,
                    ),
                    nullable=True,
                ),
            )

        indexes = {
            index["name"]
            for index in sa.inspect(bind).get_indexes(TABLE_NAME)
        }

        if INDEX_NAME not in indexes:
            op.create_index(
                INDEX_NAME,
                TABLE_NAME,
                [GENERATED_COLUMN],
                unique=True,
            )

    elif bind.dialect.name == "sqlite":
        indexes = {
            index["name"]
            for index in sa.inspect(bind).get_indexes(TABLE_NAME)
        }

        if INDEX_NAME not in indexes:
            op.create_index(
                INDEX_NAME,
                TABLE_NAME,
                ["student_id"],
                unique=True,
                sqlite_where=sa.text("is_active = 1"),
            )

    else:
        raise RuntimeError(
            f"Unsupported database dialect: {bind.dialect.name}"
        )


def downgrade():
    bind = op.get_bind()
    indexes = {
        index["name"]
        for index in sa.inspect(bind).get_indexes(TABLE_NAME)
    }

    if INDEX_NAME in indexes:
        op.drop_index(INDEX_NAME, table_name=TABLE_NAME)

    if bind.dialect.name == "mysql":
        columns = {
            column["name"]
            for column in sa.inspect(bind).get_columns(TABLE_NAME)
        }

        if GENERATED_COLUMN in columns:
            op.drop_column(TABLE_NAME, GENERATED_COLUMN)
