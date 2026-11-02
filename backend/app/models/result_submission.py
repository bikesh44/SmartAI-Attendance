from app.extensions import db


class ResultSubmission(db.Model):
    __tablename__ = "result_submissions"

    submission_id = db.Column(
        db.Integer,
        primary_key=True,
    )

    assessment_id = db.Column(
        db.Integer,
        db.ForeignKey("assessments.assessment_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    offering_id = db.Column(
        db.Integer,
        db.ForeignKey("course_offerings.offering_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    faculty_id = db.Column(
        db.Integer,
        db.ForeignKey("faculty.faculty_id", ondelete="CASCADE"),
        nullable=False,
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

    status = db.Column(
        db.String(20),
        nullable=False,
        default="DRAFT",
        server_default="DRAFT",
        index=True,
    )  # "DRAFT", "SUBMITTED", "RETURNED", "APPROVED", "PUBLISHED"

    total_students = db.Column(
        db.Integer,
        nullable=False,
        default=0,
    )

    passed_students = db.Column(
        db.Integer,
        nullable=False,
        default=0,
    )

    failed_students = db.Column(
        db.Integer,
        nullable=False,
        default=0,
    )

    average_marks = db.Column(
        db.Numeric(5, 2),
        nullable=True,
    )

    submitted_at = db.Column(
        db.DateTime,
        nullable=True,
    )

    submitted_by_user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.user_id", ondelete="SET NULL"),
        nullable=True,
    )

    reviewed_at = db.Column(
        db.DateTime,
        nullable=True,
    )

    reviewed_by_user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.user_id", ondelete="SET NULL"),
        nullable=True,
    )

    review_remarks = db.Column(
        db.String(500),
        nullable=True,
    )  # Reason for return, or approval note

    published_at = db.Column(
        db.DateTime,
        nullable=True,
    )

    published_by_user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.user_id", ondelete="SET NULL"),
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
    assessment = db.relationship("Assessment", back_populates="submissions")
    offering = db.relationship("CourseOffering", backref=db.backref("result_submissions", lazy=True))
    faculty = db.relationship("Faculty", backref=db.backref("result_submissions", lazy=True))

    submitted_by = db.relationship("User", foreign_keys=[submitted_by_user_id])
    reviewed_by = db.relationship("User", foreign_keys=[reviewed_by_user_id])
    published_by = db.relationship("User", foreign_keys=[published_by_user_id])

    results = db.relationship("AcademicResult", backref=db.backref("submission", lazy=True), cascade="all, delete-orphan")
    corrections = db.relationship("ResultCorrection", back_populates="submission", cascade="all, delete-orphan")

    __table_args__ = (
        db.UniqueConstraint("assessment_id", "offering_id", name="uq_submission_assessment_offering"),
        db.Index("ix_result_submissions_term", "academic_year", "semester"),
    )

    def __repr__(self):
        return f"<ResultSubmission {self.submission_id} (Assessment {self.assessment_id}) - {self.status}>"
