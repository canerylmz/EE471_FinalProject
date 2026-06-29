"""Thin wrapper around the Ollama REST API for JSON-producing prompts."""

import json
import re

import requests


class OllamaError(Exception):
    """Raised when Ollama cannot be reached or returns invalid data."""


class OllamaClient:
    """Sends prompts to an Ollama server and parses JSON replies."""

    def __init__(self, base_url, model, timeout=120):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout

    def generate_json(self, prompt):
        """Send `prompt` to Ollama and parse the reply as JSON."""
        try:
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"temperature": 0.2},
                },
                timeout=self.timeout,
            )
            response.raise_for_status()
        except requests.exceptions.RequestException as exc:
            raise OllamaError(f"Ollama request failed: {exc}") from exc

        try:
            payload = response.json()
        except ValueError as exc:
            raise OllamaError(f"Ollama response is not JSON: {exc}") from exc

        text = payload.get("response", "")
        return self._extract_json(text)

    @staticmethod
    def _extract_json(text):
        """Extract a JSON array/object from a possibly noisy LLM reply."""
        text = text.strip()

        fence_match = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
        if fence_match:
            text = fence_match.group(1).strip()

        try:
            return json.loads(text)
        except ValueError:
            pass

        for open_char, close_char in (("[", "]"), ("{", "}")):
            start = text.find(open_char)
            end = text.rfind(close_char)
            if start != -1 and end != -1 and end > start:
                candidate = text[start : end + 1]
                try:
                    return json.loads(candidate)
                except ValueError:
                    continue

        raise OllamaError("Could not extract valid JSON from Ollama response")
