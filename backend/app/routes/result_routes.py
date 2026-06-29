"""Test result CRUD and evaluation endpoints."""

from flask import Blueprint, current_app, request

from ..services.evaluation_service import STATUS_NOT_EVALUATED
from ..utils.responses import error, success

bp = Blueprint("result", __name__, url_prefix="/api/result")


@bp.post("")
def save_result():
    data = request.get_json(force=True, silent=True) or {}
    if not data.get("test_id") or not data.get("dut_id"):
        return error("test_id and dut_id are required.", 400)
    if not data.get("result"):
        data["result"] = STATUS_NOT_EVALUATED

    test = current_app.plan_service.get_test(data["test_id"])
    if not test:
        return error("Test was not found.", 404)

    measured_values = data.get("measured_values", {})
    validation_errors = current_app.report_service.validate_measured_values(test, measured_values)
    if validation_errors:
        return error("; ".join(validation_errors), 400)

    evaluation = current_app.evaluation_service.evaluate(test, measured_values)
    if evaluation["status"] != STATUS_NOT_EVALUATED:
        data["result"] = _result_label(evaluation["status"])

    result = current_app.report_service.save_result(data)
    current_app.evaluation_service.save_evaluation(result["id"], evaluation)
    result = current_app.report_service.get_result_by_id(result["id"])
    return success(result, 201)


@bp.get("/<int:test_id>")
def get_result(test_id):
    result = current_app.report_service.get_latest_result_for_test(test_id)
    if not result:
        return error("No saved result was found for this test.", 404)
    return success(result)


@bp.get("/schema/<int:test_id>")
def get_result_schema(test_id):
    test = current_app.plan_service.get_test(test_id)
    if not test:
        return error("Test was not found.", 404)

    return success(current_app.report_service.get_result_schema_for_test(test))


@bp.post("/evaluate/<int:test_id>")
def evaluate_result(test_id):
    test = current_app.plan_service.get_test(test_id)
    if not test:
        return error("Test was not found.", 404)

    data = request.get_json(force=True, silent=True) or {}
    measured_values = data.get("measured_values", data)
    return success(current_app.evaluation_service.evaluate(test, measured_values))


def _result_label(status):
    labels = {
        "PASS": "Pass",
        "FAIL": "Fail",
        "CONDITIONAL PASS": "Conditional Pass",
        "NOT EVALUATED": "Not Evaluated",
    }
    return labels.get(status, status)
