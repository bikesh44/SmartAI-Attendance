from datetime import datetime, timezone

from app.extensions import db


class AttendanceRecord(db.Model):
    __tablename__ = "attendance_records"

    attendance_id = db.Column(
        db.Integer,
        primary_key=True,
    )

    session_id = db.Column(
        db.Integer,
        db.ForeignKey("attendance_sessions.session_id"),
        nullable=False,
    )

    student_id = db.Column(
        db.Integer,
        db.ForeignKey("students.student_id"),
        nullable=False,
    )

    status = db.Column(
        db.String(20),
        nullable=False,
        default="PRESENT",
    )

    marked_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
        nullable=False,
    )

    confidence_score = db.Column(
        db.Float,
        nullable=True,
    )

    recognition_method = db.Column(
        db.String(20),
        nullable=False,
        default="FACE",
    )

    session = db.relationship(
        "AttendanceSession",
        back_populates="attendance_records",
    )

    student = db.relationship(
        "Student",
        back_populates="attendance_records",
    )

    __table_args__ = (
        db.UniqueConstraint(
            "session_id",
            "student_id",
            name="uq_session_student_attendance",
        ),
    )

    def __repr__(self):
        return f"<AttendanceRecord {self.attendance_id}>"