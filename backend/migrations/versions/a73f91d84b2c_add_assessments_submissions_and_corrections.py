"""add assessments submissions and corrections

Revision ID: a73f91d84b2c
Revises: e89f1c7d2b45
Create Date: 2026-10-29 18:25:30.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a73f91d84b2c'
down_revision = 'e89f1c7d2b45'
branch_labels = None
depends_on = None


def upgrade():
    # 1. Create assessments table
    op.create_table(
        'assessments',
        sa.Column('assessment_id', sa.Integer(), nullable=False),
        sa.Column('offering_id', sa.Integer(), nullable=False),
        sa.Column('exam_id', sa.Integer(), nullable=True),
        sa.Column('assessment_name', sa.String(length=100), nullable=False),
        sa.Column('assessment_type', sa.String(length=30), nullable=False, server_default='FINAL'),
        sa.Column('max_marks', sa.Numeric(precision=5, scale=2), nullable=False, server_default='100.00'),
        sa.Column('weightage', sa.Numeric(precision=5, scale=2), nullable=True, server_default='100.00'),
        sa.Column('assessment_date', sa.Date(), nullable=True),
        sa.Column('created_by', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['offering_id'], ['course_offerings.offering_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['exam_id'], ['examinations.exam_id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['created_by'], ['users.user_id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('assessment_id'),
        sa.UniqueConstraint('offering_id', 'assessment_name', name='uq_offering_assessment'),
    )
    with op.batch_alter_table('assessments', schema=None) as batch_op:
        batch_op.create_index('ix_assessments_offering_id', ['offering_id'], unique=False)
        batch_op.create_index('ix_assessments_exam_id', ['exam_id'], unique=False)

    # 2. Create result_submissions table
    op.create_table(
        'result_submissions',
        sa.Column('submission_id', sa.Integer(), nullable=False),
        sa.Column('assessment_id', sa.Integer(), nullable=False),
        sa.Column('offering_id', sa.Integer(), nullable=False),
        sa.Column('faculty_id', sa.Integer(), nullable=False),
        sa.Column('academic_year', sa.String(length=20), nullable=False),
        sa.Column('semester', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='DRAFT'),
        sa.Column('total_students', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('passed_students', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('failed_students', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('average_marks', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column('submitted_at', sa.DateTime(), nullable=True),
        sa.Column('submitted_by_user_id', sa.Integer(), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(), nullable=True),
        sa.Column('reviewed_by_user_id', sa.Integer(), nullable=True),
        sa.Column('review_remarks', sa.String(length=500), nullable=True),
        sa.Column('published_at', sa.DateTime(), nullable=True),
        sa.Column('published_by_user_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['assessment_id'], ['assessments.assessment_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['offering_id'], ['course_offerings.offering_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['faculty_id'], ['faculty.faculty_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['submitted_by_user_id'], ['users.user_id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['reviewed_by_user_id'], ['users.user_id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['published_by_user_id'], ['users.user_id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('submission_id'),
        sa.UniqueConstraint('assessment_id', 'offering_id', name='uq_submission_assessment_offering'),
    )
    with op.batch_alter_table('result_submissions', schema=None) as batch_op:
        batch_op.create_index('ix_result_submissions_status', ['status'], unique=False)
        batch_op.create_index('ix_result_submissions_term', ['academic_year', 'semester'], unique=False)
        batch_op.create_index('ix_result_submissions_faculty_id', ['faculty_id'], unique=False)
        batch_op.create_index('ix_result_submissions_offering_id', ['offering_id'], unique=False)

    # 3. Add assessment_id and submission_id to academic_results
    with op.batch_alter_table('academic_results', schema=None) as batch_op:
        batch_op.add_column(sa.Column('assessment_id', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('submission_id', sa.Integer(), nullable=True))
        batch_op.create_foreign_key('fk_academic_results_assessment_id', 'assessments', ['assessment_id'], ['assessment_id'], ondelete='SET NULL')
        batch_op.create_foreign_key('fk_academic_results_submission_id', 'result_submissions', ['submission_id'], ['submission_id'], ondelete='SET NULL')
        batch_op.create_index('ix_academic_results_assessment_id', ['assessment_id'], unique=False)
        batch_op.create_index('ix_academic_results_submission_id', ['submission_id'], unique=False)

    # 4. Create result_corrections table
    op.create_table(
        'result_corrections',
        sa.Column('correction_id', sa.Integer(), nullable=False),
        sa.Column('result_id', sa.Integer(), nullable=False),
        sa.Column('student_id', sa.Integer(), nullable=False),
        sa.Column('course_id', sa.Integer(), nullable=False),
        sa.Column('submission_id', sa.Integer(), nullable=True),
        sa.Column('previous_marks', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column('new_marks', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column('previous_grade', sa.String(length=10), nullable=True),
        sa.Column('new_grade', sa.String(length=10), nullable=True),
        sa.Column('previous_grade_points', sa.Numeric(precision=4, scale=2), nullable=True),
        sa.Column('new_grade_points', sa.Numeric(precision=4, scale=2), nullable=True),
        sa.Column('reason', sa.String(length=500), nullable=False),
        sa.Column('corrected_by_user_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['result_id'], ['academic_results.result_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['student_id'], ['students.student_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['course_id'], ['courses.course_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['submission_id'], ['result_submissions.submission_id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['corrected_by_user_id'], ['users.user_id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('correction_id'),
    )
    with op.batch_alter_table('result_corrections', schema=None) as batch_op:
        batch_op.create_index('ix_result_corrections_result_id', ['result_id'], unique=False)
        batch_op.create_index('ix_result_corrections_student_id', ['student_id'], unique=False)


def downgrade():
    op.drop_table('result_corrections')

    with op.batch_alter_table('academic_results', schema=None) as batch_op:
        batch_op.drop_constraint('fk_academic_results_submission_id', type_='foreignkey')
        batch_op.drop_constraint('fk_academic_results_assessment_id', type_='foreignkey')
        batch_op.drop_index('ix_academic_results_submission_id')
        batch_op.drop_index('ix_academic_results_assessment_id')
        batch_op.drop_column('submission_id')
        batch_op.drop_column('assessment_id')

    op.drop_table('result_submissions')
    op.drop_table('assessments')
