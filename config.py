import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

class Config:
    ENV = os.environ.get("FLASK_ENV", "development")
    SECRET_KEY = os.environ.get("SECRET_KEY")

    if not SECRET_KEY and (os.environ.get("RENDER") == "true" or ENV == "production"):
        raise RuntimeError("SECRET_KEY must be set in production.")

    if not SECRET_KEY:
        SECRET_KEY = "dev-secret-key"

    DATABASE_URL = os.environ.get("DATABASE_URL")

    if DATABASE_URL:
        # Production (Render / Supabase)
        SQLALCHEMY_DATABASE_URI = DATABASE_URL
    else:
        # Local development (SQLite)
        SQLALCHEMY_DATABASE_URI = "sqlite:///" + os.path.join(
            BASE_DIR, "instance", "school.db"
        )

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Session security
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = os.environ.get("RENDER") == "true"

    # Upload limits
    MAX_CONTENT_LENGTH = int(os.environ.get("MAX_CONTENT_LENGTH_MB", "20")) * 1024 * 1024

    QR_FOLDER = os.path.join(BASE_DIR, "static", "qr")
