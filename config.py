"""
Application configuration for YatraSathi.

All values can be overridden with environment variables or a `.env` file
placed next to this file (see `.env.example`).
"""
import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

INSTANCE_DIR = BASE_DIR / "instance"
INSTANCE_DIR.mkdir(exist_ok=True)


class Config:
    # Flask
    SECRET_KEY = os.getenv("SECRET_KEY", "yatrasathi-dev-secret-change-me")

    # Database (SQLite file inside ./instance by default)
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL", "sqlite:///" + str(INSTANCE_DIR / "yatrasathi.db").replace("\\", "/")
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Data folder with the tourism datasets
    DATA_DIR = BASE_DIR / "data"

    # Optional: OpenAI API for richer AI answers. Leave empty to use the
    # built-in offline response generator (works without internet).
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
    OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")

    # Seed the database with demo users, trips, chats and feedback on first run
    LOAD_DEMO_DATA = os.getenv("LOAD_DEMO_DATA", "1") == "1"

    # Uploads (destination images added from the admin panel)
    UPLOAD_FOLDER = BASE_DIR / "yatrasathi" / "static" / "uploads"
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # 5 MB

    SUPPORTED_LANGUAGES = ("en", "kn", "hi")


class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False
    OPENAI_API_KEY = ""
