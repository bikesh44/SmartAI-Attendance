from app.extensions import db


class AcademicResult(db.Model):
    __tablename__ = "academic_results"

    result_id = db.Column(
        db.Integer,
        primary_key=True,
    )

    student_id = db.Column(
        db.Integer,
        db.ForeignKey("students.student_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    course_id = db.Column(
        db.Integer,
        db.ForeignKey("courses.course_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    offering_id = db.Column(
        db.Integer,
        db.ForeignKey("course_offerings.offering_id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    exam_id = db.Column(
        db.Integer,
        db.ForeignKey("examinations.exam_id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    assessment_id = db.Column(
        db.Integer,
        db.ForeignKey("assessments.assessment_id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    submission_id = db.Column(
        db.Integer,
        db.ForeignKey("result_submissions.submission_id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    academic_year = db.Column(
        db.String(20),
        nullable=False,
        index=True,
    )

    semester = db.Column(
        db.Integer,
        nullable=False,
        index=True,
    )

    credits = db.Column(
        db.Integer,
        nullable=False,
        default=3,
    )

    marks_obtained = db.Column(
        db.Numeric(5, 2),
        nullable=True,
    )

    max_marks = db.Column(
        db.Numeric(5, 2),
        nullable=False,
        default=100.00,
    )

    grade = db.Column(
        db.String(10),
        nullable=False,
    )  # e.g., "O", "A+", "A", "B+", "B", "C", "P", "F"

    grade_points = db.Column(
        db.Numeric(4, 2),
        nullable=False,
    )  # e.g., 9.0, 8.5, 7.5, 6.0, 0.0

    status = db.Column(
        db.String(20),
        nullable=False,
        default="PASS",
    )  # e.g., "PASS", "FAIL", "WITHHELD", "ABSENT"

    is_published = db.Column(
        db.Boolean,
        nullable=False,
        default=True,
        server_default=db.true(),
        index=True,
    )

    published_at = db.Column(
        db.DateTime,
        nullable=True,
    )

    remarks = db.Column(
        db.String(255),
        nullable=True,
    )

    created_at = db.Column(
        db.DateTime,
        server_default=db.func.now(),
        nullable=False,
    )

    updated_at = db.Column(
        db.DateTime,
        server_default=db.func.now(),
        onupdate=db.func.now(),
        nullable=False,
    )

    # Relationships
    student = db.relationship(
        "Student",
        backref=db.backref("academic_results", lazy=True, cascade="all, delete-orphan"),
    )

    course = db.relationship(
        "Course",
        backref=db.backref("academic_results", lazy=True),
    )

    offering = db.relationship(
        "CourseOffering",
        backref=db.backref("academic_results", lazy=True),
    )

    examination = db.relationship(
        "Examination",
        back_populates="results",
    )

    __table_args__ = (
        db.UniqueConstraint(
            "student_id",
            "course_id",
            "academic_year",
            "semester",
            name="uq_student_course_term_result",
        ),
        db.Index(
            "ix_academic_results_student_sem_pub",
            "student_id",
            "semester",
            "is_published",
        ),
    )

    def __repr__(self):
        return f"<AcademicResult Student {self.student_id} Course {self.course_id} Grade {self.grade} ({self.status})>"
