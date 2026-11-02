from datetime import datetime

from app.extensions import db


class AttendanceSession(db.Model):
    __tablename__ = "attendance_sessions"

    session_id = db.Column(
        db.Integer,
        primary_key=True,
    )

    offering_id = db.Column(
        db.Integer,
        db.ForeignKey("course_offerings.offering_id"),
        nullable=False,
    )

    faculty_id = db.Column(
        db.Integer,
        db.ForeignKey("faculty.faculty_id"),
        nullable=False,
    )

    session_date = db.Column(
        db.Date,
        nullable=False,
    )

    start_time = db.Column(
        db.Time,
        nullable=False,
    )

    end_time = db.Column(
        db.Time,
        nullable=True,
    )

    status = db.Column(
        db.String(20),
        nullable=False,
        default="ACTIVE",
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

    offering = db.relationship(
        "CourseOffering",
        back_populates="attendance_sessions",
    )

    faculty = db.relationship(
        "Faculty",
        back_populates="attendance_sessions",
    )

    attendance_records = db.relationship(
        "AttendanceRecord",
        back_populates="session",
        cascade="all, delete-orphan",
    )

    def __repr__(self):
        return f"<AttendanceSession {self.session_id}>"