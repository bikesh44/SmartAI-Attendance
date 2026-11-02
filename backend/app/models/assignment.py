"""
Course Assignment Model
SAMS-FR (Smart Attendance Management System)
"""

from datetime import datetime
from app.extensions import db


class CourseAssignment(db.Model):
    __tablename__ = "assignments"

    assignment_id = db.Column(db.Integer, primary_key=True)
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
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    assignment_type = db.Column(db.String(50), nullable=False, default="HOMEWORK")
    attachment_path = db.Column(db.String(500), nullable=True)
    attachment_name = db.Column(db.String(255), nullable=True)
    maximum_marks = db.Column(db.Numeric(5, 2), nullable=False, default=100.00)
    submission_type = db.Column(db.String(30), nullable=False, default="FILE_UPLOAD")
    allowed_file_types = db.Column(db.String(100), nullable=False, default="pdf,doc,docx,zip")
    maximum_file_size_mb = db.Column(db.Integer, nullable=False, default=10)
    due_date = db.Column(db.DateTime, nullable=False)
    allow_late_submission = db.Column(db.Boolean, nullable=False, default=False)
    status = db.Column(db.String(20), nullable=False, default="PUBLISHED")
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    # Relationships
    offering = db.relationship(
        "CourseOffering",
        backref=db.backref("assignments", cascade="all, delete-orphan", lazy="select"),
    )
    faculty = db.relationship(
        "Faculty",
        backref=db.backref("assignments", lazy="select"),
    )
    submissions = db.relationship(
        "AssignmentSubmission",
        back_populates="assignment",
        cascade="all, delete-orphan",
        lazy="select",
    )

    def to_dict(self):
        return {
            "assignment_id": self.assignment_id,
            "offering_id": self.offering_id,
            "faculty_id": self.faculty_id,
            "title": self.title,
            "description": self.description or "",
            "assignment_type": self.assignment_type,
            "has_attachment": bool(self.attachment_path),
            "attachment_name": self.attachment_name or "",
            "maximum_marks": float(self.maximum_marks) if self.maximum_marks is not None else 100.0,
            "submission_type": self.submission_type,
            "allowed_file_types": self.allowed_file_types,
            "maximum_file_size_mb": self.maximum_file_size_mb,
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "allow_late_submission": self.allow_late_submission,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self):
        return f"<CourseAssignment {self.assignment_id}: {self.title}>"


# Convenient alias
Assignment = CourseAssignment
