"""
config.py — Application configuration for ResumeAI.

Reads settings from environment variables (via .env file in development).
All sensitive values MUST come from the environment — never hardcode secrets here.
"""

import os
from dotenv import load_dotenv

# Load .env file when running locally
load_dotenv()


class Config:
    """Base configuration shared by all environments."""

    # ── Security ──────────────────────────────────────────────────────────────
    # Flask uses SECRET_KEY to sign session cookies and CSRF tokens.
    # Generate a strong key with: python -c "import secrets; print(secrets.token_hex(32))"
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-placeholder-key-change-in-production")

    # ── Database ──────────────────────────────────────────────────────────────
    # SQLite database stored in the instance/ folder (excluded from Git).
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    INSTANCE_DIR = os.path.join(BASE_DIR, "instance")
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",
        f"sqlite:///{os.path.join(INSTANCE_DIR, 'resumeai.db')}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False  # Suppresses a noisy deprecation warning

    # ── File uploads ──────────────────────────────────────────────────────────
    # No file size limit — any size is accepted
    MAX_CONTENT_LENGTH = None
    ALLOWED_EXTENSIONS = {"pdf", "docx", "json"}

    # ── AI configuration ──────────────────────────────────────────────────────
    GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
    GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.0-flash")

    # ── ngrok (public tunnel) ─────────────────────────────────────────────────
    NGROK_AUTHTOKEN = os.environ.get("NGROK_AUTHTOKEN", "")
    NGROK_ENABLED = os.environ.get("NGROK_ENABLED", "false").lower() == "true"

    # ── Session / cookie settings ─────────────────────────────────────────────
    SESSION_COOKIE_HTTPONLY = True   # JavaScript cannot read the session cookie
    SESSION_COOKIE_SAMESITE = "Lax" # CSRF protection for same-site requests
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_DURATION = 60 * 60 * 24 * 14  # 14 days in seconds

    # ── WTF / CSRF ────────────────────────────────────────────────────────────
    WTF_CSRF_ENABLED = True

    # ── Job description limits ────────────────────────────────────────────────
    MAX_JOB_DESCRIPTION_LENGTH = 8000  # characters


class DevelopmentConfig(Config):
    """Development-specific settings — verbose errors, no forced HTTPS."""
    DEBUG = True
    SESSION_COOKIE_SECURE = False  # Allow HTTP in local dev


class ProductionConfig(Config):
    """Production settings — stricter security, no debug output."""
    DEBUG = False
    SESSION_COOKIE_SECURE = True   # HTTPS only
    SESSION_COOKIE_SAMESITE = "Strict"

    @classmethod
    def validate(cls):
        """Refuse to start if critical secrets are still set to placeholder values."""
        placeholder = "dev-placeholder-key-change-in-production"
        if cls.SECRET_KEY == placeholder:
            raise ValueError(
                "SECRET_KEY is not set to a real value. "
                "Generate one with: python -c \"import secrets; print(secrets.token_hex(32))\""
            )
        if not cls.GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY environment variable is required in production.")


class TestingConfig(Config):
    """Configuration used by automated tests."""
    TESTING = True
    DEBUG = True
    WTF_CSRF_ENABLED = False          # Disable CSRF so tests can POST without tokens
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"  # In-memory DB, reset after each test
    SESSION_COOKIE_SECURE = False
    # Use a fixed key so tests are deterministic
    SECRET_KEY = "test-secret-key-not-for-production"


# Map environment name → config class
config_map = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
}


def get_config():
    """Return the correct config class based on the FLASK_ENV environment variable."""
    env = os.environ.get("FLASK_ENV", "development").lower()
    return config_map.get(env, DevelopmentConfig)
