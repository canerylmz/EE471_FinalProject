"""HTTP client for the separate TestForge AI backend."""

import requests


class AIBackendError(Exception):
    """Raised when the AI backend cannot produce a valid response."""


class AIBackendClient:
    """Sends prompts to the AI backend and returns parsed JSON results."""

    def __init__(self, base_url, timeout=130):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def generate_json(self, prompt):
        """Send `prompt` to the AI backend and return its JSON result."""
        try:
            response = requests.post(
                f"{self.base_url}/api/ai/generate",
                json={"prompt": prompt},
                timeout=self.timeout,
            )
            response.raise_for_status()
        except requests.exceptions.RequestException as exc:
            raise AIBackendError(f"AI backend request failed: {exc}") from exc

        try:
            payload = response.json()
        except ValueError as exc:
            raise AIBackendError(f"AI backend response is not JSON: {exc}") from exc

        if not payload.get("success"):
            raise AIBackendError(payload.get("error", "AI backend generation failed"))

        try:
            return payload["data"]["result"]
        except (KeyError, TypeError) as exc:
            raise AIBackendError("AI backend response is missing data.result") from exc
