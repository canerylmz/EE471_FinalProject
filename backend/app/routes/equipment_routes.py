"""Equipment and calibration tracking endpoints."""

from flask import Blueprint, current_app, request

from ..utils.responses import error, success

bp = Blueprint("equipment", __name__, url_prefix="/api/equipment")


@bp.get("")
def list_equipment():
    return success({"equipment": current_app.equipment_service.list_all()})


@bp.post("")
def create_equipment():
    data = request.get_json(force=True, silent=True) or {}
    item = current_app.equipment_service.create(data)
    return success(item, 201)


@bp.get("/<int:equipment_id>")
def get_equipment(equipment_id):
    item = current_app.equipment_service.get(equipment_id)
    if not item:
        return error("Equipment not found.", 404)
    return success(item)


@bp.patch("/<int:equipment_id>")
def update_equipment(equipment_id):
    data = request.get_json(force=True, silent=True) or {}
    item = current_app.equipment_service.update(equipment_id, data)
    if not item:
        return error("Equipment not found.", 404)
    return success(item)


@bp.delete("/<int:equipment_id>")
def delete_equipment(equipment_id):
    item = current_app.equipment_service.delete(equipment_id)
    if not item:
        return error("Equipment not found.", 404)
    return success({"deleted": True, "equipment_id": equipment_id})


@bp.post("/link")
def link_equipment():
    data = request.get_json(force=True, silent=True) or {}
    try:
        link = current_app.equipment_service.link_to_test(
            int(data.get("test_id")),
            int(data.get("equipment_id")),
            data.get("usage_role", ""),
        )
    except (TypeError, ValueError) as exc:
        return error(str(exc), 400)
    return success(link, 201)


@bp.get("/test/<int:test_id>")
def list_test_equipment(test_id):
    return success({"equipment": current_app.equipment_service.list_for_test(test_id)})


@bp.delete("/link/<int:link_id>")
def unlink_equipment(link_id):
    link = current_app.equipment_service.unlink(link_id)
    if not link:
        return error("Equipment link not found.", 404)
    return success({"deleted": True, "link_id": link_id})
