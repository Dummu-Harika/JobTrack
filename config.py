
import os
from datetime import timedelta
from urllib.parse import urlsplit

from dotenv import load_dotenv

load_dotenv()


def required_env(name):
    """Read a required environment variable."""
    value = os.getenv(name)

    if not value or not value.strip():
        raise RuntimeError(
            f"Missing required environment variable: {name}"
        )

    return value.strip()


def validate_database_url(database_url):
    """Allow only supported database URL schemes."""
    parsed = urlsplit(database_url)

    if parsed.scheme not in {
        "postgresql",
        "postgresql+psycopg",
        "sqlite",
        "sqlite+pysqlite",
    }:
        raise RuntimeError(
            "DATABASE_URL must use a supported PostgreSQL "
            "or SQLite URL scheme."
        )


class Config:
    SECRET_KEY = required_env("SECRET_KEY")
    SQLALCHEMY_DATABASE_URI = required_env("DATABASE_URL")

    validate_database_url(SQLALCHEMY_DATABASE_URI)

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        "pool_timeout": 30,
    }

    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"

    # Set COOKIE_SECURE=true when deployed over HTTPS.
    SESSION_COOKIE_SECURE = (
        os.getenv("COOKIE_SECURE", "false").strip().lower()
        == "true"
    )

    PERMANENT_SESSION_LIFETIME = timedelta(minutes=30)

    # Refreshing the session extends its lifetime with activity.
    SESSION_REFRESH_EACH_REQUEST = True

    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = 3600
