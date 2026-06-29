"""Pre-test checklist generation and PDF export endpoints."""

from flask import Blueprint, current_app, request, send_file

from ..utils.responses import error, success

bp = Blueprint("checklist", __name__, url_prefix="/api/checklist")


@bp.post("/generate")
def generate_checklist():
    data = request.get_json(force=True, silent=True) or {}
    dut_id = data.get("dut_id")
    test_id = data.get("test_id")
    if not dut_id or not test_id:
        return error("dut_id and test_id are required.", 400)

    dut = current_app.dut_service.get(dut_id)
    test = current_app.plan_service.get_test(test_id)
    if not dut or not test:
        return error("DUT or test not found.", 404)

    checklist, source = current_app.checklist_service.generate_checklist(test, dut)
    return success({"checklist": checklist, "source": source})


@bp.post("/export")
def export_checklist():
    data = request.get_json(force=True, silent=True) or {}
    checklist_data = data.get("checklist_data")
    if not checklist_data:
        return error("checklist_data is required.", 400)

    buffer = current_app.checklist_service.export_pdf(checklist_data)
    return send_file(
        buffer,
        as_attachment=True,
        download_name="Checklist.pdf",
        mimetype="application/pdf",
    )
