"""Application configuration."""

import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class Config:
    """Base configuration shared across environments."""

    DATABASE_PATH = os.environ.get(
        "TESTFORGE_DB_PATH", os.path.join(BASE_DIR, "data", "testforge.db")
    )
    EXPORT_DIR = os.environ.get(
        "TESTFORGE_EXPORT_DIR", os.path.join(BASE_DIR, "exports")
    )
    UPLOAD_DIR = os.environ.get(
        "TESTFORGE_UPLOAD_DIR", os.path.join(BASE_DIR, "uploads")
    )
    MAX_ATTACHMENT_SIZE = int(os.environ.get("TESTFORGE_MAX_ATTACHMENT_SIZE", str(20 * 1024 * 1024)))

    AI_BACKEND_URL = os.environ.get("AI_BACKEND_URL", "http://localhost:5001")
    AI_BACKEND_TIMEOUT = int(os.environ.get("AI_BACKEND_TIMEOUT", "130"))

    ORGANIZATION_NAME = os.environ.get("TESTFORGE_ORG_NAME", "TestForge Test Laboratory")
    ORGANIZATION_ADDRESS = os.environ.get("TESTFORGE_ORG_ADDRESS", "-")

    JSON_SORT_KEYS = False


class TestConfig(Config):
    """Configuration used for the automated test suite."""

    DATABASE_PATH = ":memory:"
    TESTING = True
    UPLOAD_DIR = os.path.join(BASE_DIR, "test_uploads")
