"""merge timetable and course activation migrations

Revision ID: c5733e7563c5
Revises: 37f3b1327d19, 154e2456a96e
Create Date: 2026-10-13 18:53:49.494781

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c5733e7563c5'
down_revision = ('37f3b1327d19', '154e2456a96e')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
