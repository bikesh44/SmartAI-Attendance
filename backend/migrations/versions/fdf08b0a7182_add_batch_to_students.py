
"""add batch to students

Revision ID: fdf08b0a7182
Revises: 6bc211f8cf02
Create Date: 2026-10-14 09:59:59.497197

"""
from alembic import op
import sqlalchemy as sa


revision = "fdf08b0a7182"
down_revision = "6bc211f8cf02"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("students", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("batch_id", sa.Integer(), nullable=True)
        )
        batch_op.create_foreign_key(
            "fk_students_batch_id_batches",
            "batches",
            ["batch_id"],
            ["batch_id"],
        )


def downgrade():
    with op.batch_alter_table("students", schema=None) as batch_op:
        batch_op.drop_constraint(
            "fk_students_batch_id_batches",
            type_="foreignkey",
        )
        batch_op.drop_column("batch_id")
