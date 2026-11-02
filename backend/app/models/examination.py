from app.extensions import db


class Examination(db.Model):
    __tablename__ = "examinations"

    exam_id = db.Column(
        db.Integer,
        primary_key=True,
    )

    exam_name = db.Column(
        db.String(100),
        nullable=False,
    )

    exam_type = db.Column(
        db.String(30),
        nullable=False,
        default="END_TERM",
    )  # e.g., "END_TERM", "MID_TERM", "INTERNAL", "SUPPLEMENTARY"

    academic_year = db.Column(
        db.String(20),
        nullable=False,
    )

    semester = db.Column(
        db.Integer,
        nullable=False,
    )

    start_date = db.Column(
        db.Date,
        nullable=True,
    )

    end_date = db.Column(
        db.Date,
        nullable=True,
    )

    is_published = db.Column(
        db.Boolean,
        nullable=False,
        default=False,
        server_default=db.false(),
    )

    published_at = db.Column(
        db.DateTime,
        nullable=True,
    )

    created_at = db.Column(
        db.DateTime,
        server_default=db.func.now(),
        nullable=False,
    )

    # Relationships
    results = db.relationship(
        "AcademicResult",
        back_populates="examination",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        db.Index("ix_examinations_term", "academic_year", "semester"),
    )

    def __repr__(self):
        return f"<Examination {self.exam_name} ({self.academic_year} Sem {self.semester})>"
