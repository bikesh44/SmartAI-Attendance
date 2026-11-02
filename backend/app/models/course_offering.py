from app.extensions import db


class CourseOffering(db.Model):
    __tablename__ = "course_offerings"

    offering_id = db.Column(
        db.Integer,
        primary_key=True,
    )

    course_id = db.Column(
        db.Integer,
        db.ForeignKey("courses.course_id"),
        nullable=False,
    )

    faculty_id = db.Column(
        db.Integer,
        db.ForeignKey("faculty.faculty_id"),
        nullable=True,
    )

    academic_year = db.Column(
        db.String(20),
        nullable=False,
    )

    semester = db.Column(
        db.Integer,
        nullable=False,
    )

    section = db.Column(
        db.String(20),
        nullable=False,
    )

    room = db.Column(
        db.String(50),
        nullable=True,
    )

    course = db.relationship(
        "Course",
        back_populates="offerings",
    )

    faculty = db.relationship(
        "Faculty",
        back_populates="course_offerings",
    )

    enrollments = db.relationship(
        "Enrollment",
        back_populates="offering",
        cascade="all, delete-orphan",
    )

    attendance_sessions = db.relationship(
        "AttendanceSession",
        back_populates="offering",
        cascade="all, delete-orphan",
    )

    timetable_entries = db.relationship(
        "TimetableEntry",
        back_populates = "offering",
        cascade = "all, delete-orphan",
    )

    def __init__(
        self,
        course_id=None,
        faculty_id=None,
        academic_year=None,
        semester=None,
        section=None,
        room=None,
        **kwargs,
    ):
        super().__init__()
        self.course_id = course_id
        self.faculty_id = faculty_id
        self.academic_year = academic_year
        self.semester = semester
        self.section = section
        self.room = room
        for key, value in kwargs.items():
            setattr(self, key, value)

    def __repr__(self):
        return f"<CourseOffering {self.offering_id}>"