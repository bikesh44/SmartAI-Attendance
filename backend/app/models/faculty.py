from app.extensions import db


class Faculty(db.Model):
    __tablename__ = "faculty"

    faculty_id = db.Column(
        db.Integer,
        primary_key=True,
    )

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.user_id"),
        unique=True,
        nullable=False,
    )

    department_id = db.Column(
        db.Integer,
        db.ForeignKey("departments.department_id"),
        nullable=False,
    )

    employee_id = db.Column(
        db.String(50),
        unique=True,
        nullable=False,
    )

    designation = db.Column(
        db.String(100),
        nullable=False,
    )

    phone = db.Column(db.String(20), nullable=True)
    gender = db.Column(db.String(20), nullable=True)
    date_of_birth = db.Column(db.String(50), nullable=True)
    date_of_joining = db.Column(db.String(50), nullable=True)
    employment_status = db.Column(db.String(50), nullable=True, default="Permanent")
    qualification = db.Column(db.String(150), nullable=True)
    specialization = db.Column(db.String(255), nullable=True)
    office_cabin = db.Column(db.String(100), nullable=True)
    address = db.Column(db.String(255), nullable=True)
    city = db.Column(db.String(100), nullable=True)
    state = db.Column(db.String(100), nullable=True)
    pin_code = db.Column(db.String(20), nullable=True)
    country = db.Column(db.String(100), nullable=True, default="India")

    # The user account associated with this faculty profile.
    user = db.relationship(
        "User",
        back_populates="faculty_profile",
    )

    # The department this faculty member belongs to.
    # Explicit foreign_keys avoids ambiguity with the HOD relationship.
    department = db.relationship(
        "Department",
        back_populates="faculty",
        foreign_keys=[department_id],
    )

    course_offerings = db.relationship(
        "CourseOffering",
        back_populates="faculty",
    )

    attendance_sessions = db.relationship(
        "AttendanceSession",
        back_populates="faculty",
    )

    def __repr__(self):
        return f"<Faculty {self.employee_id}>"
