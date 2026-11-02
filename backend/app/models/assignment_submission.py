"""
Assignment Submission Model
SAMS-FR (Smart Attendance Management System)
"""

from datetime import datetime
from app.extensions import db


class AssignmentSubmission(db.Model):
    __tablename__ = "assignment_submissions"

    submission_id = db.Column(db.Integer, primary_key=True)
    assignment_id = db.Column(
        db.Integer,
        db.ForeignKey("assignments.assignment_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    student_id = db.Column(
        db.Integer,
        db.ForeignKey("students.student_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    submission_text = db.Column(db.Text, nullable=True)
    file_path = db.Column(db.String(500), nullable=True)
    file_name = db.Column(db.String(255), nullable=True)
    file_size_bytes = db.Column(db.BigInteger, nullable=True)
    submitted_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    is_late = db.Column(db.Boolean, nullable=False, default=False)
    marks_obtained = db.Column(db.Numeric(5, 2), nullable=True)
    feedback = db.Column(db.Text, nullable=True)
    review_status = db.Column(
        db.String(20),
        nullable=False,
        default="PENDING",
    )  # PENDING, REVIEWED, RETURNED
    reviewed_at = db.Column(db.DateTime, nullable=True)
    reviewed_by = db.Column(
        db.Integer,
        db.ForeignKey("users.user_id", ondelete="SET NULL"),
        nullable=True,
    )

    __table_args__ = (
        db.UniqueConstraint(
            "assignment_id",
            "student_id",
            name="uq_assignment_student",
        ),
    )

    # Relationships
    assignment = db.relationship(
        "CourseAssignment",
        back_populates="submissions",
    )
    student = db.relationship(
        "Student",
        backref=db.backref("assignment_submissions", cascade="all, delete-orphan", lazy="select"),
    )
    reviewer = db.relationship(
        "User",
        foreign_keys=[reviewed_by],
    )

    def to_dict(self):
        return {
            "submission_id": self.submission_id,
            "assignment_id": self.assignment_id,
            "student_id": self.student_id,
            "has_file": bool(self.file_path),
            "file_name": self.file_name or "",
            "file_size_bytes": self.file_size_bytes,
            "submission_text": self.submission_text or "",
            "submitted_at": self.submitted_at.isoformat() if self.submitted_at else None,
            "is_late": self.is_late,
            "marks_obtained": float(self.marks_obtained) if self.marks_obtained is not None else None,
            "feedback": self.feedback or "",
            "review_status": self.review_status,
            "reviewed_at": self.reviewed_at.isoformat() if self.reviewed_at else None,
            "reviewed_by": self.reviewed_by,
        }

    def __repr__(self):
        return f"<AssignmentSubmission {self.submission_id}: Assignment {self.assignment_id}, Student {self.student_id}>"
