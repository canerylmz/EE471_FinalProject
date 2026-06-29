"""Shared pytest fixtures for the TestForge AI backend test suite."""

import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config import Config  # noqa: E402
from run import create_app  # noqa: E402


class TestConfig(Config):
    """Configuration used for the automated test suite."""

    OLLAMA_URL = "http://ollama.invalid:11434"
    TESTING = True


@pytest.fixture
def app():
    """Create an AI backend Flask app pointed at an unreachable Ollama URL."""
    return create_app(TestConfig)


@pytest.fixture
def client(app):
    """Return a Flask test client for `app`."""
    return app.test_client()
