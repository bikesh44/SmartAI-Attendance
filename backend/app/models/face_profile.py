from datetime import datetime

from sqlalchemy import Computed, Index

from app.extensions import db

class FaceProfile(db.Model):
    __tablename__ = "face_profiles"

    face_id = db.Column(
        db.Integer,
        primary_key=True,
    )

    student_id = db.Column(
        db.Integer,
        db.ForeignKey("students.student_id"),
        nullable=False,
    )

    embedding = db.Column(
        db.LargeBinary,
        nullable=False,
    )

    model_version = db.Column(
        db.String(50),
        nullable=False,
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

    updated_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    is_active = db.Column(
        db.Boolean,
        default=True,
        nullable=False,
    )

    active_student_id = db.Column(
        db.Integer,
        Computed(
            "CASE WHEN is_active = 1 THEN student_id ELSE NULL END",
            persisted=True,
        ),
        nullable=True,
    )

    student = db.relationship(
        "Student",
        back_populates="face_profiles",
    )

    __table_args__ = (
        Index(
            "uq_student_active_face",
            "active_student_id",
            unique=True,
        ),
    )

    def __repr__(self):
        return f"<FaceProfile {self.face_id}>"
