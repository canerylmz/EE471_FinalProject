"""Test record form generation endpoints."""

import re

from flask import Blueprint, current_app, send_file

from ..services.test_record_form_service import DOCX_MIME
from ..utils.responses import error

bp = Blueprint("record_form", __name__, url_prefix="/api/record-form")


@bp.post("/generate/<int:test_id>")
def generate_record_form(test_id):
    test = current_app.plan_service.get_test(test_id)
    if not test:
        return error("Test was not found.", 404)

    dut = current_app.dut_service.get(test.get("dut_id"))
    if not dut:
        return error("DUT was not found.", 404)

    plan_item = None
    if test.get("test_plan_item_id"):
        plan_item = current_app.plan_service.get_plan_item(test["test_plan_item_id"])

    catalog = None
    if test.get("iso_catalog_id"):
        catalog = current_app.db.query_one(
            "SELECT * FROM iso_test_catalog WHERE id = ?",
            (test["iso_catalog_id"],),
        )

    result = current_app.report_service.get_latest_result_for_test(test_id)
    attachments = current_app.attachment_service.list_for_test(test_id)
    equipment = current_app.equipment_service.list_for_test(test_id)
    buffer = current_app.test_record_form_service.build_docx(
        dut=dut,
        test=test,
        plan_item=plan_item,
        catalog=catalog,
        result=result,
        attachments=attachments,
        equipment=equipment,
    )

    filename = _record_form_filename(test, plan_item)
    return send_file(
        buffer,
        as_attachment=True,
        download_name=filename,
        mimetype=DOCX_MIME,
    )


def _record_form_filename(test, plan_item):
    clause = test.get("clause_no") or (plan_item or {}).get("clause_no") or "NA"
    test_name = test.get("test_name") or "Test"
    raw = f"FR_14_03_ISO16750_{clause}_{test_name}_Test_Record_Form.docx"
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", raw).strip("_")
