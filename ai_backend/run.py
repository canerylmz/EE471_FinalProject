"""Standalone Flask server for TestForge AI generation."""

from flask import Flask, request
from flask_cors import CORS

from config import Config
from ollama_client import OllamaClient, OllamaError


def create_app(config_class=Config):
    """Create the AI backend application."""
    app = Flask(__name__)
    app.config.from_object(config_class)
    CORS(app, resources={r"/api/*": {"origins": "*"}})

    ollama = OllamaClient(
        app.config["OLLAMA_URL"],
        app.config["OLLAMA_MODEL"],
        app.config["OLLAMA_TIMEOUT"],
    )

    @app.get("/api/health")
    def health():
        return {
            "success": True,
            "data": {
                "status": "ok",
                "model": app.config["OLLAMA_MODEL"],
                "ollama_url": app.config["OLLAMA_URL"],
            },
        }

    @app.post("/api/ai/generate")
    def generate():
        payload = request.get_json(silent=True) or {}
        prompt = payload.get("prompt")
        if not prompt:
            return {"success": False, "error": "prompt is required"}, 400

        try:
            result = ollama.generate_json(prompt)
        except OllamaError as exc:
            return {"success": False, "error": str(exc)}, 502

        return {"success": True, "data": {"result": result}}

    return app


if __name__ == "__main__":
    create_app().run(host="0.0.0.0", port=5001, debug=True)
