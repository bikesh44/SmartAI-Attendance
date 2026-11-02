"""merge batch and timetable migrations

Revision ID: 80c87740d03d
Revises: c5733e7563c5, fdf08b0a7182
Create Date: 2026-10-15 17:23:06.021576

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '80c87740d03d'
down_revision = ('c5733e7563c5', 'fdf08b0a7182')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
