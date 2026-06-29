"""Shared pytest fixtures for the TestForge backend test suite."""

import os
import shutil
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import create_app  # noqa: E402
from app.config import TestConfig  # noqa: E402


class FallbackAIClient:
    def generate_json(self, prompt):
        return {"invalid": "shape"}


@pytest.fixture
def app():
    """Create a TestForge Flask app backed by an in-memory SQLite database."""
    flask_app = create_app(TestConfig)
    flask_app.plan_service.ai_client = FallbackAIClient()
    flask_app.checklist_service.ai_client = FallbackAIClient()
    flask_app.report_service.ai_client = FallbackAIClient()
    flask_app.evaluation_service.ai_client = FallbackAIClient()
    yield flask_app
    shutil.rmtree(flask_app.config["UPLOAD_DIR"], ignore_errors=True)


@pytest.fixture
def client(app):
    """Return a Flask test client for `app`."""
    return app.test_client()


@pytest.fixture
def sample_dut(client):
    """Create a sample DUT and return its JSON record."""
    payload = {
        "name": "ECU Test Module",
        "manufacturer": "Acme Automotive",
        "part_number": "ACM-1234",
        "mounting_location": "Engine compartment",
        "power_class": "Class I",
        "nominal_voltage": "12V",
        "customer": "Demo Customer",
        "project": "Demo Project",
        "temp_min": -40,
        "temp_max": 105,
        "ip_class": "IP67",
        "notes": "Sample DUT for tests",
    }
    response = client.post("/api/dut", json=payload)
    return response.get_json()["data"]
