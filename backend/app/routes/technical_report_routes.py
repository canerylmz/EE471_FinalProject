"""Final ISO 16750 technical report generation endpoints."""

import re

from flask import Blueprint, current_app, request, send_file

from ..ai_backend_client import AIBackendError
from ..services.technical_report_service import DOCX_MIME, VALID_CATEGORIES
from ..utils.responses import error

bp = Blueprint("technical_report", __name__, url_prefix="/api/technical-report")


@bp.post("/generate/<int:dut_id>")
def generate_technical_report(dut_id):
    data = request.get_json(force=True, silent=True) or {}
    category = (data.get("category") or "all").lower()
    report_format = (data.get("format") or "docx").lower()
    use_ai = bool(data.get("use_ai"))

    if category not in VALID_CATEGORIES:
        return error("Invalid report category.", 400)
    if report_format != "docx":
        return error("Only DOCX format is currently supported.", 400)

    dut = current_app.dut_service.get(dut_id)
    if not dut:
        return error("DUT was not found.", 404)

    entries = _load_entries(dut_id, category)
    if not entries:
        return error("No tests were found for the selected category.", 404)

    ai_sections = None
    if use_ai:
        try:
            ai_sections = _generate_ai_sections(dut, entries, category)
        except AIBackendError as exc:
            return error(f"AI technical report generation failed: {exc}", 502)

    buffer = current_app.technical_report_service.build_docx(
        dut,
        entries,
        category,
        ai_sections=ai_sections,
    )
    report_no = current_app.technical_report_service.report_number(dut, category)
    suffix = "AI_Technical_Report" if use_ai else "Technical_Report"
    filename = _safe_filename(f"{report_no}_{suffix}.docx")
    return send_file(buffer, as_attachment=True, download_name=filename, mimetype=DOCX_MIME)


def _load_entries(dut_id, category):
    tests = current_app.plan_service.get_tests_for_dut(dut_id)
    entries = []
    for test in tests:
        test_category = (test.get("category") or "").lower()
        if category != "all" and test_category != category:
            continue

        catalog = None
        if test.get("iso_catalog_id"):
            catalog = current_app.db.query_one(
                "SELECT * FROM iso_test_catalog WHERE id = ?",
                (test["iso_catalog_id"],),
            )
        result = current_app.report_service.get_latest_result_for_test(test["id"])
        attachments = current_app.attachment_service.list_for_test(test["id"])
        equipment = current_app.equipment_service.list_for_test(test["id"])
        entries.append(
            {
                "test": test,
                "catalog": catalog,
                "result": result,
                "attachments": attachments,
                "equipment": equipment,
            }
        )
    return entries


def _safe_filename(value):
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", value).strip("_")


def _generate_ai_sections(dut, entries, category):
    prompt = _build_ai_prompt(dut, entries, category)
    result = current_app.report_service.ai_client.generate_json(prompt)
    if not isinstance(result, dict):
        raise AIBackendError("AI response must be a JSON object.")

    required = ("executive_summary", "conformity_assessment", "technical_comments", "limitations")
    missing = [key for key in required if not result.get(key)]
    if missing:
        raise AIBackendError(f"AI response is missing required fields: {', '.join(missing)}")

    optional = ("function_description", "lab_comment")
    sections = {key: str(result.get(key, "")).strip() for key in required}
    sections.update({key: str(result.get(key, "")).strip() for key in optional if result.get(key)})
    return sections


def _build_ai_prompt(dut, entries, category):
    tests = []
    for entry in entries:
        test = entry["test"]
        result = entry.get("result") or {}
        tests.append(
            {
                "test_name": test.get("test_name"),
                "iso_part": test.get("iso_part"),
                "clause_no": test.get("clause_no"),
                "category": test.get("category"),
                "operating_mode": test.get("operating_mode"),
                "required_test_level": test.get("required_test_level"),
                "evaluation_status": result.get("evaluation_status") or result.get("result"),
                "evaluation_score": result.get("evaluation_score"),
                "observations": result.get("observations"),
                "deviation": result.get("deviation_description") if result.get("has_deviation") else None,
            }
        )

    return f"""
You are writing a formal automotive laboratory technical report section in English.
Use a concise, professional laboratory style. Do not write Turkish. Do not include generic student-style explanations.
Do not reproduce copyrighted standard text. Use only the recorded metadata and results below.

Return only valid JSON with these string fields. The first four are required; the last two
are optional narrative fields used elsewhere in the report (omit them if you have nothing
specific to add, do not invent data):
{{
  "executive_summary": "...",
  "conformity_assessment": "...",
  "technical_comments": "...",
  "limitations": "...",
  "function_description": "... (one paragraph describing the DUT function and test scope, for report Section 1.1)",
  "lab_comment": "... (one paragraph laboratory comment for the report Comments section)"
}}

DUT:
{{
  "product_description": "{dut.get('name')}",
  "manufacturer": "{dut.get('manufacturer')}",
  "model_name": "{dut.get('part_number')}",
  "project": "{dut.get('project')}",
  "customer": "{dut.get('customer')}",
  "nominal_voltage": "{dut.get('nominal_voltage')}",
  "mounting_location": "{dut.get('mounting_location')}",
  "ip_class": "{dut.get('ip_class')}"
}}

Report category: {category}
Recorded tests and results:
{tests}
""".strip()
