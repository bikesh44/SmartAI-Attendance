from app.extensions import db


class ResultCorrection(db.Model):
    __tablename__ = "result_corrections"

    correction_id = db.Column(
        db.Integer,
        primary_key=True,
    )

    result_id = db.Column(
        db.Integer,
        db.ForeignKey("academic_results.result_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
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

    submission_id = db.Column(
        db.Integer,
        db.ForeignKey("result_submissions.submission_id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    previous_marks = db.Column(
        db.Numeric(5, 2),
        nullable=True,
    )

    new_marks = db.Column(
        db.Numeric(5, 2),
        nullable=True,
    )

    previous_grade = db.Column(
        db.String(10),
        nullable=True,
    )

    new_grade = db.Column(
        db.String(10),
        nullable=True,
    )

    previous_grade_points = db.Column(
        db.Numeric(4, 2),
        nullable=True,
    )

    new_grade_points = db.Column(
        db.Numeric(4, 2),
        nullable=True,
    )

    reason = db.Column(
        db.String(500),
        nullable=False,
    )  # Required reason for audit trail

    corrected_by_user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.user_id", ondelete="SET NULL"),
        nullable=True,
    )

    created_at = db.Column(
        db.DateTime,
        server_default=db.func.now(),
        nullable=False,
    )

    # Relationships
    result = db.relationship("AcademicResult", backref=db.backref("corrections", lazy=True))
    student = db.relationship("Student", backref=db.backref("result_corrections", lazy=True))
    course = db.relationship("Course")
    submission = db.relationship("ResultSubmission", back_populates="corrections")
    corrected_by = db.relationship("User", foreign_keys=[corrected_by_user_id])

    def __repr__(self):
        return f"<ResultCorrection Result {self.result_id} Student {self.student_id} By User {self.corrected_by_user_id}>"
