"""Demo data setup endpoint."""

from flask import Blueprint, current_app, request

from ..utils.responses import error, success

bp = Blueprint("demo", __name__, url_prefix="/api/demo")


@bp.get("/status")
def demo_status():
    return success(current_app.demo_seed_service.status())


@bp.post("/seed")
def seed_demo_data():
    data = request.get_json(force=True, silent=True) or {}
    try:
        result = current_app.demo_seed_service.seed(
            reset_demo_data=bool(data.get("reset_demo_data", False))
        )
    except ValueError as exc:
        return error(str(exc), 400)
    return success(result, 201 if result.get("created") else 200)
