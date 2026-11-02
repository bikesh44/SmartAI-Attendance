from flask_bcrypt import Bcrypt
from flask_jwt_extended import JWTManager
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()
migrate = Migrate()
jwt = JWTManager()
bcrypt = Bcrypt()


@jwt.unauthorized_loader
def handle_missing_token(error):
    return {
        "success": False,
        "message": "Authentication required",
    }, 401


@jwt.invalid_token_loader
def handle_invalid_token(error):
    return {
        "success": False,
        "message": "Invalid authentication token",
    }, 401


@jwt.expired_token_loader
def handle_expired_token(jwt_header, jwt_payload):
    return {
        "success": False,
        "message": "Authentication token has expired",
    }, 401


@jwt.revoked_token_loader
def handle_revoked_token(jwt_header, jwt_payload):
    return {
        "success": False,
        "message": "Authentication token has been revoked",
    }, 401