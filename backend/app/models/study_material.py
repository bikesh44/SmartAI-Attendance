"""
Study Material / Notes Model
SAMS-FR (Smart Attendance Management System)
"""

from datetime import datetime
from app.extensions import db


class StudyMaterial(db.Model):
    __tablename__ = "study_materials"

    material_id = db.Column(db.Integer, primary_key=True)
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
    category = db.Column(
        db.String(50),
        nullable=False,
        default="LECTURE_NOTES",
    )  # LECTURE_NOTES, REFERENCE, PRACTICAL, TUTORIAL, OTHER
    file_path = db.Column(db.String(500), nullable=False)
    file_name = db.Column(db.String(255), nullable=False)
    file_type = db.Column(db.String(20), nullable=False)
    file_size_bytes = db.Column(db.BigInteger, nullable=False, default=0)
    visibility = db.Column(db.String(20), nullable=False, default="PUBLISHED")  # PUBLISHED, DRAFT
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
        backref=db.backref("study_materials", cascade="all, delete-orphan", lazy="select"),
    )
    faculty = db.relationship(
        "Faculty",
        backref=db.backref("study_materials", lazy="select"),
    )

    def formatted_file_size(self):
        size = self.file_size_bytes or 0
        if size < 1024:
            return f"{size} B"
        elif size < 1024 * 1024:
            return f"{size / 1024:.1f} KB"
        else:
            return f"{size / (1024 * 1024):.1f} MB"

    def to_dict(self):
        return {
            "material_id": self.material_id,
            "offering_id": self.offering_id,
            "faculty_id": self.faculty_id,
            "title": self.title,
            "description": self.description or "",
            "category": self.category,
            "file_name": self.file_name,
            "file_type": self.file_type,
            "file_size_bytes": self.file_size_bytes,
            "formatted_size": self.formatted_file_size(),
            "visibility": self.visibility,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self):
        return f"<StudyMaterial {self.material_id}: {self.title}>"


# Convenient alias
Note = StudyMaterial
