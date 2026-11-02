from app.extensions import db


class Student(db.Model):
    __tablename__ = "students"

    student_id = db.Column(db.Integer, primary_key=True)

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

    batch_id = db.Column(
        db.Integer,
        db.ForeignKey("batches.batch_id"),
        nullable=True,
    )

    enrollment_no = db.Column(
        db.String(50),
        unique=True,
        nullable=False,
    )

    semester = db.Column(db.Integer, nullable=False)
    section = db.Column(db.String(20), nullable=False)
    academic_year = db.Column(db.String(20), nullable=False)

    photo_url = db.Column(db.Text, nullable=True)
    signature_url = db.Column(db.Text, nullable=True)
    father_name = db.Column(db.String(100), nullable=True)
    mother_name = db.Column(db.String(100), nullable=True)
    phone = db.Column(db.String(20), nullable=True)
    guardian_phone = db.Column(db.String(20), nullable=True)
    blood_group = db.Column(db.String(10), nullable=True)
    gender = db.Column(db.String(20), nullable=True)
    date_of_birth = db.Column(db.String(50), nullable=True)
    address = db.Column(db.String(255), nullable=True)
    city = db.Column(db.String(100), nullable=True)
    state = db.Column(db.String(100), nullable=True)
    pin_code = db.Column(db.String(20), nullable=True)
    country = db.Column(db.String(100), nullable=True, default="India")
    emergency_contact_name = db.Column(db.String(100), nullable=True)
    emergency_contact_phone = db.Column(db.String(20), nullable=True)
    admission_date = db.Column(db.String(50), nullable=True)


    user = db.relationship(
        "User",
        back_populates="student_profile",
    )

    department = db.relationship(
        "Department",
        back_populates="students",
    )

    batch = db.relationship(
        "Batch",
        backref="students",
    )

    face_profiles = db.relationship(
        "FaceProfile",
        back_populates="student",
        cascade="all, delete-orphan",
    )

    enrollments = db.relationship(
        "Enrollment",
        back_populates="student",
        cascade="all, delete-orphan",
    )

    attendance_records = db.relationship(
        "AttendanceRecord",
        back_populates="student",
    )

    def __repr__(self):
        return f"<Student {self.enrollment_no}>"