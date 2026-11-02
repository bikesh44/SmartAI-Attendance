from datetime import datetime

from app.extensions import db


class User(db.Model):
    __tablename__ = "users"

    user_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False)
    is_active = db.Column(
        db.Boolean,
        nullable=False,
        default=True,
        server_default=db.true(),
    )
    phone = db.Column(db.String(20), nullable=True)
    designation = db.Column(db.String(100), nullable=True, default="System Administrator")
    department = db.Column(db.String(100), nullable=True, default="Administration")

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

    updated_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    last_login = db.Column(
        db.DateTime,
        nullable=True,
        default=None,
    )
    student_profile = db.relationship(
    "Student",
    back_populates="user",
    uselist=False,
    )

    faculty_profile = db.relationship(
    "Faculty",
    back_populates="user",
    uselist=False,
   )

    def __repr__(self):
        return f"<User {self.email}>"