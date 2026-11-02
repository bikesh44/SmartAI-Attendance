"""add academic records examination results and documents tables

Revision ID: e89f1c7d2b45
Revises: 647357547c39
Create Date: 2026-10-29 18:07:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e89f1c7d2b45'
down_revision = '647357547c39'
branch_labels = None
depends_on = None


def upgrade():
    # 1. Create examinations table
    op.create_table(
        'examinations',
        sa.Column('exam_id', sa.Integer(), nullable=False),
        sa.Column('exam_name', sa.String(length=100), nullable=False),
        sa.Column('exam_type', sa.String(length=30), nullable=False, server_default='END_TERM'),
        sa.Column('academic_year', sa.String(length=20), nullable=False),
        sa.Column('semester', sa.Integer(), nullable=False),
        sa.Column('start_date', sa.Date(), nullable=True),
        sa.Column('end_date', sa.Date(), nullable=True),
        sa.Column('is_published', sa.Boolean(), nullable=False, server_default=sa.text('0')),
        sa.Column('published_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('exam_id'),
    )
    with op.batch_alter_table('examinations', schema=None) as batch_op:
        batch_op.create_index('ix_examinations_term', ['academic_year', 'semester'], unique=False)

    # 2. Create academic_results table
    op.create_table(
        'academic_results',
        sa.Column('result_id', sa.Integer(), nullable=False),
        sa.Column('student_id', sa.Integer(), nullable=False),
        sa.Column('course_id', sa.Integer(), nullable=False),
        sa.Column('offering_id', sa.Integer(), nullable=True),
        sa.Column('exam_id', sa.Integer(), nullable=True),
        sa.Column('academic_year', sa.String(length=20), nullable=False),
        sa.Column('semester', sa.Integer(), nullable=False),
        sa.Column('credits', sa.Integer(), nullable=False, server_default='3'),
        sa.Column('marks_obtained', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column('max_marks', sa.Numeric(precision=5, scale=2), nullable=False, server_default='100.00'),
        sa.Column('grade', sa.String(length=10), nullable=False),
        sa.Column('grade_points', sa.Numeric(precision=4, scale=2), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='PASS'),
        sa.Column('is_published', sa.Boolean(), nullable=False, server_default=sa.text('1')),
        sa.Column('published_at', sa.DateTime(), nullable=True),
        sa.Column('remarks', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['student_id'], ['students.student_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['course_id'], ['courses.course_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['offering_id'], ['course_offerings.offering_id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['exam_id'], ['examinations.exam_id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('result_id'),
        sa.UniqueConstraint('student_id', 'course_id', 'academic_year', 'semester', name='uq_student_course_term_result'),
    )
    with op.batch_alter_table('academic_results', schema=None) as batch_op:
        batch_op.create_index('ix_academic_results_student_id', ['student_id'], unique=False)
        batch_op.create_index('ix_academic_results_course_id', ['course_id'], unique=False)
        batch_op.create_index('ix_academic_results_offering_id', ['offering_id'], unique=False)
        batch_op.create_index('ix_academic_results_exam_id', ['exam_id'], unique=False)
        batch_op.create_index('ix_academic_results_student_sem_pub', ['student_id', 'semester', 'is_published'], unique=False)

    # 3. Create academic_documents table
    op.create_table(
        'academic_documents',
        sa.Column('document_id', sa.Integer(), nullable=False),
        sa.Column('student_id', sa.Integer(), nullable=False),
        sa.Column('document_type', sa.String(length=50), nullable=False, server_default='GRADE_CARD'),
        sa.Column('title', sa.String(length=150), nullable=False),
        sa.Column('academic_year', sa.String(length=20), nullable=True),
        sa.Column('semester', sa.Integer(), nullable=True),
        sa.Column('file_path', sa.String(length=255), nullable=True),
        sa.Column('file_size_bytes', sa.Integer(), nullable=True),
        sa.Column('is_verified', sa.Boolean(), nullable=False, server_default=sa.text('1')),
        sa.Column('issued_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['student_id'], ['students.student_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('document_id'),
    )
    with op.batch_alter_table('academic_documents', schema=None) as batch_op:
        batch_op.create_index('ix_academic_documents_student_id', ['student_id'], unique=False)
        batch_op.create_index('ix_academic_docs_student_sem', ['student_id', 'semester'], unique=False)


def downgrade():
    op.drop_table('academic_documents')
    op.drop_table('academic_results')
    op.drop_table('examinations')
