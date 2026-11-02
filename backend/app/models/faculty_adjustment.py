from datetime import datetime

from app.extensions import db


class FacultyAdjustment(db.Model):
    __tablename__ = "faculty_adjustments"

    adjustment_id = db.Column(
        db.Integer,
        primary_key=True,
    )

    timetable_entry_id = db.Column(
        db.Integer,
        db.ForeignKey("timetable_entries.timetable_entry_id"),
        nullable=False,
        index=True,
    )

    original_faculty_id = db.Column(
        db.Integer,
        db.ForeignKey("faculty.faculty_id"),
        nullable=False,
    )

    substitute_faculty_id = db.Column(
        db.Integer,
        db.ForeignKey("faculty.faculty_id"),
        nullable=False,
    )

    adjusted_by_user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.user_id"),
        nullable=False,
    )

    effective_date = db.Column(
        db.Date,
        nullable=False,
    )

    reason = db.Column(
        db.String(255),
        nullable=False,
    )

    status = db.Column(
        db.String(20),
        default="APPROVED",
        nullable=False,
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

    timetable_entry = db.relationship(
        "TimetableEntry",
        backref=db.backref("adjustments", lazy="dynamic", cascade="all, delete-orphan"),
    )

    original_faculty = db.relationship(
        "Faculty",
        foreign_keys=[original_faculty_id],
    )

    substitute_faculty = db.relationship(
        "Faculty",
        foreign_keys=[substitute_faculty_id],
    )

    adjusted_by = db.relationship(
        "User",
        foreign_keys=[adjusted_by_user_id],
    )

    def to_dict(self):
        return {
            "adjustment_id": self.adjustment_id,
            "timetable_entry_id": self.timetable_entry_id,
            "original_faculty_id": self.original_faculty_id,
            "original_faculty_name": (
                self.original_faculty.user.name
                if self.original_faculty and self.original_faculty.user
                else "Unknown"
            ),
            "substitute_faculty_id": self.substitute_faculty_id,
            "substitute_faculty_name": (
                self.substitute_faculty.user.name
                if self.substitute_faculty and self.substitute_faculty.user
                else "Unknown"
            ),
            "adjusted_by_user_id": self.adjusted_by_user_id,
            "adjusted_by_name": (
                self.adjusted_by.name
                if self.adjusted_by
                else f"User #{self.adjusted_by_user_id}"
            ),
            "effective_date": self.effective_date.strftime("%Y-%m-%d"),
            "reason": self.reason,
            "status": self.status,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S") if self.created_at else "",
            "course_code": (
                self.timetable_entry.offering.course.course_code
                if self.timetable_entry and self.timetable_entry.offering and self.timetable_entry.offering.course
                else ""
            ),
            "course_name": (
                self.timetable_entry.offering.course.course_name
                if self.timetable_entry and self.timetable_entry.offering and self.timetable_entry.offering.course
                else ""
            ),
            "day_of_week": (
                self.timetable_entry.day_of_week
                if self.timetable_entry
                else ""
            ),
            "start_time": (
                self.timetable_entry.start_time.strftime("%H:%M")
                if self.timetable_entry and self.timetable_entry.start_time
                else ""
            ),
            "end_time": (
                self.timetable_entry.end_time.strftime("%H:%M")
                if self.timetable_entry and self.timetable_entry.end_time
                else ""
            ),
            "room": (
                self.timetable_entry.room
                if self.timetable_entry
                else ""
            ),
            "section": (
                self.timetable_entry.offering.section
                if self.timetable_entry and self.timetable_entry.offering
                else ""
            ),
            "semester": (
                self.timetable_entry.offering.semester
                if self.timetable_entry and self.timetable_entry.offering
                else None
            ),
        }

    def __init__(
        self,
        timetable_entry_id=None,
        original_faculty_id=None,
        substitute_faculty_id=None,
        adjusted_by_user_id=None,
        effective_date=None,
        reason=None,
        status="APPROVED",
        **kwargs,
    ):
        super().__init__()
        self.timetable_entry_id = timetable_entry_id
        self.original_faculty_id = original_faculty_id
        self.substitute_faculty_id = substitute_faculty_id
        self.adjusted_by_user_id = adjusted_by_user_id
        self.effective_date = effective_date
        self.reason = reason
        self.status = status
        for key, value in kwargs.items():
            setattr(self, key, value)

    def __repr__(self):
        return (
            f"<FacultyAdjustment {self.adjustment_id}: "
            f"Entry {self.timetable_entry_id} -> Sub {self.substitute_faculty_id}>"
        )
