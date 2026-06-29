"""Formal report generation and export endpoints."""

from flask import Blueprint, current_app, request, send_file

from ..utils.responses import error, success

bp = Blueprint("report", __name__, url_prefix="/api/report")

DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


def _load_context(data):
    """Resolve dut, test, and result records referenced by a request body."""
    dut_id = data.get("dut_id")
    test_id = data.get("test_id")
    if not dut_id or not test_id:
        return None, None, None, error("dut_id and test_id are required.", 400)

    dut = current_app.dut_service.get(dut_id)
    test = current_app.plan_service.get_test(test_id)
    if not dut or not test:
        return None, None, None, error("DUT or test not found.", 404)

    result = current_app.report_service.get_latest_result_for_test(test_id)
    if not result:
        return None, None, None, error("A result must be saved before generating a report.", 400)

    return dut, test, result, None


@bp.post("/generate")
def generate_report():
    data = request.get_json(force=True, silent=True) or {}
    dut, test, result, err_response = _load_context(data)
    if err_response:
        return err_response

    result_data = data.get("result_data") or {
        "result": result["result"],
        "measured_values": result["measured_values"],
        "test_conditions": {
            "temperature": result["temp"],
            "humidity": result["humidity"],
        },
        "observations": result["observations"],
        "has_deviation": bool(result["has_deviation"]),
        "deviation_description": result["deviation_description"],
        "root_cause": result["root_cause"],
        "corrective_action": result["corrective_action"],
    }

    report, source = current_app.report_service.generate_report(dut, test, result, result_data)
    return success({"report": report, "source": source})


@bp.post("/export/docx")
def export_report_docx():
    data = request.get_json(force=True, silent=True) or {}
    dut, test, result, err_response = _load_context(data)
    if err_response:
        return err_response

    if not result.get("report_text"):
        return error("No report has been generated for this test yet.", 400)

    attachments = current_app.attachment_service.list_for_test(test["id"])
    buffer = current_app.report_service.export_docx(
        dut,
        test,
        result,
        result["report_text"],
        attachments=attachments,
    )
    return send_file(
        buffer,
        as_attachment=True,
        download_name=f"TestReport_{test_id_safe(test)}.docx",
        mimetype=DOCX_MIME,
    )


@bp.post("/export/pdf")
def export_report_pdf():
    data = request.get_json(force=True, silent=True) or {}
    dut, test, result, err_response = _load_context(data)
    if err_response:
        return err_response

    if not result.get("report_text"):
        return error("No report has been generated for this test yet.", 400)

    buffer = current_app.report_service.export_pdf(dut, test, result, result["report_text"])
    return send_file(
        buffer,
        as_attachment=True,
        download_name=f"TestReport_{test_id_safe(test)}.pdf",
        mimetype="application/pdf",
    )


def test_id_safe(test):
    return "".join(
        c if c.isalnum() or c in ("-", "_") else "_" for c in test.get("test_name", "Test")
    )
