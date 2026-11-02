from app.extensions import db


class Enrollment(db.Model):
    __tablename__ = "enrollments"

    enrollment_id = db.Column(
        db.Integer,
        primary_key=True,
    )

    student_id = db.Column(
        db.Integer,
        db.ForeignKey("students.student_id"),
        nullable=False,
    )

    offering_id = db.Column(
        db.Integer,
        db.ForeignKey("course_offerings.offering_id"),
        nullable=False,
    )

    enrolled_at = db.Column(
        db.DateTime,
        server_default=db.func.now(),
        nullable=False,
    )

    status = db.Column(
        db.String(20),
        nullable=False,
        default="ACTIVE",
    )

    student = db.relationship(
        "Student",
        back_populates="enrollments",
    )

    offering = db.relationship(
        "CourseOffering",
        back_populates="enrollments",
    )

    __table_args__ = (
        db.UniqueConstraint(
            "student_id",
            "offering_id",
            name="uq_student_offering",
        ),
    )

    def __repr__(self):
        return f"<Enrollment {self.enrollment_id}>"