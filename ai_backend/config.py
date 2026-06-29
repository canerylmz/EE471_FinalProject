"""Configuration for the TestForge AI backend."""

import os


class Config:
    """Runtime settings for the AI service."""

    OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
    OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "qwen2.5:14b")
    OLLAMA_TIMEOUT = int(os.environ.get("OLLAMA_TIMEOUT", "120"))
    JSON_SORT_KEYS = False
