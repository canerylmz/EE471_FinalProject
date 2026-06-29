"""DUT registration and lookup endpoints."""

from flask import Blueprint, current_app, request

from ..utils.responses import error, success

bp = Blueprint("dut", __name__, url_prefix="/api/dut")


@bp.post("")
def create_dut():
    data = request.get_json(force=True, silent=True) or {}
    if not data.get("name"):
        return error("DUT name is required.", 400)

    dut = current_app.dut_service.create(data)
    return success(dut, 201)


@bp.get("")
def list_duts():
    duts = current_app.dut_service.list_all()
    return success(duts)


@bp.get("/<int:dut_id>")
def get_dut(dut_id):
    dut = current_app.dut_service.get(dut_id)
    if not dut:
        return error("DUT not found.", 404)
    return success(dut)


@bp.delete("/<int:dut_id>")
def delete_dut(dut_id):
    dut = current_app.dut_service.get(dut_id)
    if not dut:
        return error("DUT not found.", 404)

    for attachment in current_app.attachment_service.list_for_dut(dut_id):
        current_app.attachment_service.delete(attachment["id"])

    deleted = current_app.dut_service.delete(dut_id)
    return success({"deleted": True, "dut_id": deleted["id"]})
