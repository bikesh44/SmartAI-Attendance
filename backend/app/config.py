
from datetime import timedelta
import os

from dotenv import load_dotenv
from sqlalchemy.engine import URL

load_dotenv(
    os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        ".env",
    )
)


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY")

    JWT_TOKEN_LOCATION = ["cookies", "headers"]
    JWT_COOKIE_SECURE = False
    JWT_COOKIE_HTTPONLY = True
    JWT_COOKIE_SAMESITE = "Lax"
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(days=7)

    SQLALCHEMY_DATABASE_URI = URL.create(
        "mysql+pymysql",
        username=os.getenv("LOCAL_DB_USER", "root"),
        password=os.getenv("LOCAL_DB_PASSWORD", ""),
        host=os.getenv("LOCAL_DB_HOST", "localhost"),
        database=os.getenv("LOCAL_DB_NAME", "sams_db"),
    )

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    CORS_ORIGINS = os.getenv(
        "CORS_ORIGINS",
        "http://localhost:3000",
    )

    INSTITUTION_TIMEZONE = os.getenv(
        "INSTITUTION_TIMEZONE",
        "Asia/Kolkata",
    )
