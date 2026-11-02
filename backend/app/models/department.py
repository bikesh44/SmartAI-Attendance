from app.extensions import db


class Department(db.Model):
    __tablename__ = "departments"

    department_id = db.Column(
        db.Integer,
        primary_key=True,
    )

    department_name = db.Column(
        db.String(100),
        nullable=False,
    )

    department_code = db.Column(
        db.String(20),
        unique=True,
        nullable=False,
    )

    # Faculty member assigned as Head of Department.
    # A department can exist without an assigned HOD.
    head_faculty_id = db.Column(
        db.Integer,
        db.ForeignKey(
            "faculty.faculty_id",
            use_alter=True,
            name="fk_departments_head_faculty_id",
        ),
        nullable=True,
        unique=True,
    )

    # Whether the department is active.
    is_active = db.Column(
        db.Boolean,
        nullable=False,
        default=True,
        server_default=db.true(),
    )

    # Students belonging to this department.
    students = db.relationship(
        "Student",
        back_populates="department",
        lazy=True,
    )

    # All faculty members belonging to this department.
    # This relationship uses Faculty.department_id.
    faculty = db.relationship(
        "Faculty",
        back_populates="department",
        lazy=True,
        foreign_keys="Faculty.department_id",
    )

    # Courses managed by this department.
    courses = db.relationship(
        "Course",
        back_populates="department",
        lazy=True,
    )

    # The faculty member assigned as this department's HOD.
    # This uses Department.head_faculty_id, not Faculty.department_id.
    head_faculty = db.relationship(
        "Faculty",
        foreign_keys=[head_faculty_id],
        uselist=False,
    )

    def __repr__(self):
        return f"<Department {self.department_code}>"
