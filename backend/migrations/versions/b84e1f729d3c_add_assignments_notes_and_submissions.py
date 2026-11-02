"""add assignments notes and submissions

Revision ID: b84e1f729d3c
Revises: a73f91d84b2c
Create Date: 2026-10-30 22:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b84e1f729d3c'
down_revision = 'a73f91d84b2c'
branch_labels = None
depends_on = None


def upgrade():
    # 1. Create assignments table
    op.create_table(
        'assignments',
        sa.Column('assignment_id', sa.Integer(), nullable=False),
        sa.Column('offering_id', sa.Integer(), nullable=False),
        sa.Column('faculty_id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('assignment_type', sa.String(length=50), nullable=False, server_default='HOMEWORK'),
        sa.Column('attachment_path', sa.String(length=500), nullable=True),
        sa.Column('attachment_name', sa.String(length=255), nullable=True),
        sa.Column('maximum_marks', sa.Numeric(precision=5, scale=2), nullable=False, server_default='100.00'),
        sa.Column('submission_type', sa.String(length=30), nullable=False, server_default='FILE_UPLOAD'),
        sa.Column('allowed_file_types', sa.String(length=100), nullable=False, server_default='pdf,doc,docx,zip'),
        sa.Column('maximum_file_size_mb', sa.Integer(), nullable=False, server_default='10'),
        sa.Column('due_date', sa.DateTime(), nullable=False),
        sa.Column('allow_late_submission', sa.Boolean(), nullable=False, server_default=sa.text('0')),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='PUBLISHED'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['faculty_id'], ['faculty.faculty_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['offering_id'], ['course_offerings.offering_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('assignment_id'),
    )
    with op.batch_alter_table('assignments', schema=None) as batch_op:
        batch_op.create_index('ix_assignments_offering_id', ['offering_id'], unique=False)
        batch_op.create_index('ix_assignments_faculty_id', ['faculty_id'], unique=False)

    # 2. Create study_materials table
    op.create_table(
        'study_materials',
        sa.Column('material_id', sa.Integer(), nullable=False),
        sa.Column('offering_id', sa.Integer(), nullable=False),
        sa.Column('faculty_id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('category', sa.String(length=50), nullable=False, server_default='LECTURE_NOTES'),
        sa.Column('file_path', sa.String(length=500), nullable=False),
        sa.Column('file_name', sa.String(length=255), nullable=False),
        sa.Column('file_type', sa.String(length=20), nullable=False),
        sa.Column('file_size_bytes', sa.BigInteger(), nullable=False, server_default='0'),
        sa.Column('visibility', sa.String(length=20), nullable=False, server_default='PUBLISHED'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['faculty_id'], ['faculty.faculty_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['offering_id'], ['course_offerings.offering_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('material_id'),
    )
    with op.batch_alter_table('study_materials', schema=None) as batch_op:
        batch_op.create_index('ix_study_materials_offering_id', ['offering_id'], unique=False)
        batch_op.create_index('ix_study_materials_faculty_id', ['faculty_id'], unique=False)

    # 3. Create assignment_submissions table
    op.create_table(
        'assignment_submissions',
        sa.Column('submission_id', sa.Integer(), nullable=False),
        sa.Column('assignment_id', sa.Integer(), nullable=False),
        sa.Column('student_id', sa.Integer(), nullable=False),
        sa.Column('submission_text', sa.Text(), nullable=True),
        sa.Column('file_path', sa.String(length=500), nullable=True),
        sa.Column('file_name', sa.String(length=255), nullable=True),
        sa.Column('file_size_bytes', sa.BigInteger(), nullable=True),
        sa.Column('submitted_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('is_late', sa.Boolean(), nullable=False, server_default=sa.text('0')),
        sa.Column('marks_obtained', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column('feedback', sa.Text(), nullable=True),
        sa.Column('review_status', sa.String(length=20), nullable=False, server_default='PENDING'),
        sa.Column('reviewed_at', sa.DateTime(), nullable=True),
        sa.Column('reviewed_by', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['assignment_id'], ['assignments.assignment_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['student_id'], ['students.student_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['reviewed_by'], ['users.user_id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('submission_id'),
        sa.UniqueConstraint('assignment_id', 'student_id', name='uq_assignment_student'),
    )
    with op.batch_alter_table('assignment_submissions', schema=None) as batch_op:
        batch_op.create_index('ix_assignment_submissions_assignment_id', ['assignment_id'], unique=False)
        batch_op.create_index('ix_assignment_submissions_student_id', ['student_id'], unique=False)


def downgrade():
    op.drop_table('assignment_submissions')
    op.drop_table('study_materials')
    op.drop_table('assignments')
