"""merge activity logs and faculty profile migrations

Revision ID: 647357547c39
Revises: db3304e45072, 93f4e157b8a1
Create Date: 2026-10-24 16:31:24.776231

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '647357547c39'
down_revision = ('db3304e45072', '93f4e157b8a1')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
