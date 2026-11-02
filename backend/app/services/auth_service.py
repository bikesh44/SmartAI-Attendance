from app.extensions import bcrypt, db
from app.models.user import User


def authenticate_user(email, password):
    user = User.query.filter_by(
        email=email.lower().strip()
    ).first()

    if not user:
        return None

    if not user.is_active:
        return None

    if not bcrypt.check_password_hash(
        user.password_hash,
        password,
    ):
        return None

    return user


def create_user(name, email, password, role):
    password_hash = bcrypt.generate_password_hash(password).decode("utf-8")

    user = User(
        name=name,
        email=email.lower().strip(),
        password_hash=password_hash,
        role=role,
    )

    db.session.add(user)
    db.session.commit()

    return user