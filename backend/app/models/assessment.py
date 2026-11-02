from app.extensions import db


class Assessment(db.Model):
    __tablename__ = "assessments"

    assessment_id = db.Column(
        db.Integer,
        primary_key=True,
    )

    offering_id = db.Column(
        db.Integer,
        db.ForeignKey("course_offerings.offering_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    exam_id = db.Column(
        db.Integer,
        db.ForeignKey("examinations.exam_id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    assessment_name = db.Column(
        db.String(100),
        nullable=False,
    )  # e.g., "End-Semester Examination", "Midterm Assessment"

    assessment_type = db.Column(
        db.String(30),
        nullable=False,
        default="FINAL",
    )  # "FINAL", "MIDTERM", "INTERNAL", "PRACTICAL"

    max_marks = db.Column(
        db.Numeric(5, 2),
        nullable=False,
        default=100.00,
    )

    weightage = db.Column(
        db.Numeric(5, 2),
        nullable=True,
        default=100.00,
    )

    assessment_date = db.Column(
        db.Date,
        nullable=True,
    )

    created_by = db.Column(
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
    offering = db.relationship("CourseOffering", backref=db.backref("assessments", lazy=True, cascade="all, delete-orphan"))
    examination = db.relationship("Examination", backref=db.backref("assessments", lazy=True))
    creator = db.relationship("User", foreign_keys=[created_by])

    submissions = db.relationship("ResultSubmission", back_populates="assessment", cascade="all, delete-orphan")

    __table_args__ = (
        db.UniqueConstraint("offering_id", "assessment_name", name="uq_offering_assessment"),
    )

    def __repr__(self):
        return f"<Assessment {self.assessment_name} (Offering {self.offering_id})>"
