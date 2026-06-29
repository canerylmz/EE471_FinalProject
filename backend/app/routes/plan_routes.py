"""Test plan generation, lookup, and export endpoints."""

from datetime import date

from flask import Blueprint, current_app, request, send_file

from ..utils.responses import error, success

bp = Blueprint("plan", __name__, url_prefix="/api/plan")

DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


def _safe_filename(value):
    return "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in value)


@bp.post("/generate")
def generate_plan():
    data = request.get_json(force=True, silent=True) or {}
    dut_id = data.get("dut_id")
    if not dut_id:
        return error("dut_id is required.", 400)

    dut = current_app.dut_service.get(dut_id)
    if not dut:
        return error("DUT not found.", 404)

    tests, source = current_app.plan_service.generate_plan(dut)
    return success({"tests": tests, "source": source})


@bp.get("/<int:dut_id>")
def get_plan(dut_id):
    dut = current_app.dut_service.get(dut_id)
    if not dut:
        return error("DUT not found.", 404)

    tests = current_app.plan_service.get_tests_for_dut(dut_id)
    return success({"tests": tests})


@bp.get("/test/<int:test_id>")
def get_test(test_id):
    test = current_app.plan_service.get_test(test_id)
    if not test:
        return error("Test not found.", 404)
    return success(test)


@bp.get("/items/<int:dut_id>")
def get_plan_items(dut_id):
    dut = current_app.dut_service.get(dut_id)
    if not dut:
        return error("DUT not found.", 404)

    items = current_app.plan_service.get_plan_items_for_dut(dut_id)
    return success({"items": items})


@bp.get("/item/<int:plan_item_id>")
def get_plan_item(plan_item_id):
    item = current_app.plan_service.get_plan_item(plan_item_id)
    if not item:
        return error("Plan item not found.", 404)
    return success(item)


@bp.patch("/item/<int:plan_item_id>/status")
def update_plan_item_status(plan_item_id):
    data = request.get_json(force=True, silent=True) or {}
    status = data.get("status")
    if not status:
        return error("status is required.", 400)

    try:
        item = current_app.plan_service.update_plan_item_status(plan_item_id, status)
    except ValueError as exc:
        return error(str(exc), 400)

    if not item:
        return error("Plan item not found.", 404)
    return success(item)


@bp.patch("/item/<int:plan_item_id>/order")
def update_plan_item_order(plan_item_id):
    data = request.get_json(force=True, silent=True) or {}
    sort_order = data.get("sort_order")
    if sort_order is None:
        return error("sort_order is required.", 400)

    try:
        sort_order = int(sort_order)
    except (TypeError, ValueError):
        return error("sort_order must be numeric.", 400)

    item = current_app.plan_service.update_plan_item_order(plan_item_id, sort_order)
    if not item:
        return error("Plan item not found.", 404)
    return success(item)


@bp.post("/export")
def export_plan():
    data = request.get_json(force=True, silent=True) or {}
    dut_id = data.get("dut_id")
    if not dut_id:
        return error("dut_id is required.", 400)

    dut = current_app.dut_service.get(dut_id)
    if not dut:
        return error("DUT not found.", 404)

    tests = current_app.plan_service.get_tests_for_dut(dut_id)
    if not tests:
        return error("No test plan has been generated for this DUT.", 404)

    buffer = current_app.plan_service.export_docx(dut, tests)
    filename = f"TestPlan_{_safe_filename(dut['name'])}_{date.today().isoformat()}.docx"
    return send_file(
        buffer,
        as_attachment=True,
        download_name=filename,
        mimetype=DOCX_MIME,
    )
