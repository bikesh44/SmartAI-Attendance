from app.extensions import db


class AcademicDocument(db.Model):
    __tablename__ = "academic_documents"

    document_id = db.Column(
        db.Integer,
        primary_key=True,
    )

    student_id = db.Column(
        db.Integer,
        db.ForeignKey("students.student_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    document_type = db.Column(
        db.String(50),
        nullable=False,
        default="GRADE_CARD",
    )  # "GRADE_CARD", "TRANSCRIPT", "CERTIFICATE", "BONAFIDE"

    title = db.Column(
        db.String(150),
        nullable=False,
    )

    academic_year = db.Column(
        db.String(20),
        nullable=True,
    )

    semester = db.Column(
        db.Integer,
        nullable=True,
    )

    file_path = db.Column(
        db.String(255),
        nullable=True,
    )

    file_size_bytes = db.Column(
        db.Integer,
        nullable=True,
    )

    is_verified = db.Column(
        db.Boolean,
        nullable=False,
        default=True,
        server_default=db.true(),
    )

    issued_at = db.Column(
        db.DateTime,
        server_default=db.func.now(),
        nullable=False,
    )

    created_at = db.Column(
        db.DateTime,
        server_default=db.func.now(),
        nullable=False,
    )

    # Relationship
    student = db.relationship(
        "Student",
        backref=db.backref("academic_documents", lazy=True, cascade="all, delete-orphan"),
    )

    __table_args__ = (
        db.Index("ix_academic_docs_student_sem", "student_id", "semester"),
    )

    def __repr__(self):
        return f"<AcademicDocument {self.title} (Student {self.student_id})>"
