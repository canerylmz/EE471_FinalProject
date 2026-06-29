"""Tests for the standalone AI backend Flask app and Ollama client."""

from unittest.mock import Mock, patch

import pytest
import requests

from ollama_client import OllamaClient, OllamaError


def test_health_endpoint_returns_ok(client):
    response = client.get("/api/health")

    assert response.status_code == 200
    body = response.get_json()
    assert body["success"] is True
    assert body["data"]["status"] == "ok"
    assert "model" in body["data"]
    assert "ollama_url" in body["data"]


def test_generate_requires_a_prompt(client):
    response = client.post("/api/ai/generate", json={})

    assert response.status_code == 400
    assert response.get_json()["success"] is False


def test_generate_returns_parsed_json_on_success(client):
    fake_response = Mock()
    fake_response.raise_for_status = Mock(return_value=None)
    fake_response.json = Mock(return_value={"response": '{"tests": ["DC Supply Voltage"]}'})

    with patch("ollama_client.requests.post", return_value=fake_response) as mock_post:
        response = client.post("/api/ai/generate", json={"prompt": "list ISO 16750 tests"})

    assert mock_post.called
    assert response.status_code == 200
    body = response.get_json()
    assert body["success"] is True
    assert body["data"]["result"] == {"tests": ["DC Supply Voltage"]}


def test_generate_returns_502_when_ollama_is_unreachable(client):
    with patch(
        "ollama_client.requests.post",
        side_effect=requests.exceptions.ConnectionError("connection refused"),
    ):
        response = client.post("/api/ai/generate", json={"prompt": "hello"})

    assert response.status_code == 502
    assert response.get_json()["success"] is False


def test_generate_returns_502_when_response_is_not_json(client):
    fake_response = Mock()
    fake_response.raise_for_status = Mock(return_value=None)
    fake_response.json = Mock(side_effect=ValueError("not json"))

    with patch("ollama_client.requests.post", return_value=fake_response):
        response = client.post("/api/ai/generate", json={"prompt": "hello"})

    assert response.status_code == 502
    assert response.get_json()["success"] is False


class TestOllamaClientExtractJson:
    """Unit tests for the noisy-LLM-reply JSON extraction logic."""

    def setup_method(self):
        self.client = OllamaClient("http://ollama.invalid:11434", "qwen2.5:14b")

    def test_parses_plain_json(self):
        assert self.client._extract_json('{"a": 1}') == {"a": 1}

    def test_parses_fenced_json_code_block(self):
        text = (
            'Sure, here you go:\n```json\n{"a": 1, "b": [1, 2]}\n```\n'
            "Let me know if you need more."
        )
        assert self.client._extract_json(text) == {"a": 1, "b": [1, 2]}

    def test_parses_array_surrounded_by_noise(self):
        text = "Here is the list you asked for: [1, 2, 3] -- hope that helps!"
        assert self.client._extract_json(text) == [1, 2, 3]

    def test_raises_ollama_error_on_unparseable_text(self):
        with pytest.raises(OllamaError):
            self.client._extract_json("this is not JSON at all")

    def test_generate_json_raises_when_ollama_request_fails(self):
        with patch(
            "ollama_client.requests.post",
            side_effect=requests.exceptions.Timeout("timed out"),
        ):
            with pytest.raises(OllamaError):
                self.client.generate_json("hello")
