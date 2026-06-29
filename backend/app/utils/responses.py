"""Helpers for the project-wide JSON response envelope."""

from flask import jsonify


def success(data=None, status_code=200):
    """Return a `{"success": true, "data": ...}` JSON response."""
    return jsonify({"success": True, "data": data}), status_code


def error(message, status_code=400):
    """Return a `{"success": false, "error": "..."}` JSON response."""
    return jsonify({"success": False, "error": message}), status_code
