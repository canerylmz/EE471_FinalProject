"""Service handling test results and formal report generation/export."""

import json

from ..fallbacks import fallback_report
from ..ai_backend_client import AIBackendError
from ..prompts import build_report_prompt
from ..utils.docx_export import build_report_docx
from ..utils.pdf_export import build_report_pdf

DEFAULT_RESULT_INPUT_SCHEMA = [
    {"name": "measurement", "label": "Measurement", "type": "text", "required": False},
    {
        "name": "functional_observation",
        "label": "Functional Observation",
        "type": "textarea",
        "required": False,
    },
]


class ReportService:
    """Persists test results and generates/exports formal reports."""

    def __init__(self, db, ai_client):
        self.db = db
        self.ai_client = ai_client

    def save_result(self, data):
        """Insert a test result row and return the saved record."""
        measured_values_data = data.get("measured_values", {}) or {}
        measured_values = json.dumps(measured_values_data)
        conditions = data.get("test_conditions", {}) or {}

        result_id = self.db.insert(
            """
            INSERT INTO results (
                test_id, dut_id, result, measured_values, temp, voltage, humidity,
                observations, has_deviation, deviation_description, root_cause,
                corrective_action, engineer_name
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                data.get("test_id"),
                data.get("dut_id"),
                data.get("result", ""),
                measured_values,
                conditions.get("temperature"),
                conditions.get("voltage"),
                conditions.get("humidity"),
                data.get("observations", ""),
                1 if data.get("has_deviation") else 0,
                data.get("deviation_description", ""),
                data.get("root_cause", ""),
                data.get("corrective_action", ""),
                data.get("engineer_name", ""),
            ),
        )
        return self.get_result_by_id(result_id)

    def get_result_schema_for_test(self, test):
        """Return dynamic result schema and metadata for a test."""
        schema = DEFAULT_RESULT_INPUT_SCHEMA
        evaluation_schema = {}
        catalog = None
        if test.get("iso_catalog_id"):
            catalog = self.db.query_one(
                """
                SELECT result_input_schema_json, evaluation_schema_json, severity, sample_size
                FROM iso_test_catalog
                WHERE id = ?
                """,
                (test["iso_catalog_id"],),
            )
            if catalog:
                schema = self._parse_result_schema(catalog.get("result_input_schema_json"))
                evaluation_schema = self._parse_json_object(catalog.get("evaluation_schema_json"))

        return {
            "test": {
                "id": test.get("id"),
                "test_name": test.get("test_name"),
                "iso_part": test.get("iso_part"),
                "clause_no": test.get("clause_no"),
                "category": test.get("category"),
                "operating_mode": test.get("operating_mode"),
                "functional_status": test.get("functional_status"),
                "required_test_level": test.get("required_test_level"),
                "severity": test.get("severity_level") or (catalog or {}).get("severity"),
                "sample_size": test.get("sample_size") or (catalog or {}).get("sample_size"),
            },
            "schema": schema,
            "evaluation_schema": evaluation_schema,
        }

    def validate_measured_values(self, test, measured_values):
        """Validate dynamic measured values using catalog result schema."""
        schema = self.get_result_schema_for_test(test)["schema"]
        values = measured_values or {}
        errors = []
        schema_names = {field.get("name") for field in schema if field.get("name")}
        has_schema_payload = not values or any(name in values for name in schema_names)

        for field in schema:
            name = field.get("name")
            if not name:
                continue
            value = values.get(name)
            if has_schema_payload and field.get("required") and self._is_blank(value):
                errors.append(f"{field.get('label', name)} is required.")
                continue
            if self._is_blank(value):
                continue
            if field.get("type") == "number":
                try:
                    float(value)
                except (TypeError, ValueError):
                    errors.append(f"{field.get('label', name)} must be a number.")

        return errors

    @staticmethod
    def _parse_result_schema(raw_schema):
        try:
            parsed = json.loads(raw_schema or "[]")
        except (TypeError, ValueError):
            return DEFAULT_RESULT_INPUT_SCHEMA
        if isinstance(parsed, dict) and isinstance(parsed.get("fields"), list):
            return [
                {"name": name, "label": str(name).replace("_", " ").title(), "type": "text"}
                for name in parsed["fields"]
            ]
        if not isinstance(parsed, list):
            return DEFAULT_RESULT_INPUT_SCHEMA

        schema = []
        for field in parsed:
            if not isinstance(field, dict) or not field.get("name"):
                continue
            schema.append(
                {
                    "name": field["name"],
                    "label": field.get("label") or field["name"].replace("_", " ").title(),
                    "type": field.get("type", "text"),
                    "unit": field.get("unit"),
                    "required": bool(field.get("required")),
                    "options": field.get("options", []),
                }
            )
        return schema or DEFAULT_RESULT_INPUT_SCHEMA

    @staticmethod
    def _parse_json_object(raw_value):
        try:
            parsed = json.loads(raw_value or "{}")
        except (TypeError, ValueError):
            return {}
        return parsed if isinstance(parsed, dict) else {}

    @staticmethod
    def _is_blank(value):
        return value is None or value == ""

    def get_result_by_id(self, result_id):
        """Return a single result row, with JSON fields parsed."""
        row = self.db.query_one("SELECT * FROM results WHERE id = ?", (result_id,))
        return self._parse_row(row)

    def get_latest_result_for_test(self, test_id):
        """Return the most recent result for a test, with JSON fields parsed."""
        row = self.db.query_one(
            "SELECT * FROM results WHERE test_id = ? ORDER BY created_at DESC, id DESC LIMIT 1",
            (test_id,),
        )
        return self._parse_row(row)

    @staticmethod
    def _parse_row(row):
        if row is None:
            return None
        row["measured_values"] = json.loads(row["measured_values"] or "{}")
        row["report_text"] = json.loads(row["report_text"]) if row["report_text"] else None
        row["evaluation_details"] = (
            json.loads(row["evaluation_details_json"]) if row.get("evaluation_details_json") else None
        )
        return row

    def generate_report(self, dut, test, result, result_data):
        """Generate the formal report text and persist it on the result row."""
        prompt = build_report_prompt(dut, test, result_data)
        try:
            report = self.ai_client.generate_json(prompt)
            if not isinstance(report, dict) or "sections" not in report:
                raise ValueError("Ollama response does not contain a 'sections' key")
            source = "ai-backend"
        except (AIBackendError, ValueError):
            report = fallback_report(dut, test, result_data)
            source = "fallback"

        self.db.execute(
            "UPDATE results SET report_text = ? WHERE id = ?",
            (json.dumps(report), result["id"]),
        )
        return report, source

    def export_docx(self, dut, test, result, report, attachments=None):
        """Build a formal report .docx and return a BytesIO buffer."""
        return build_report_docx(dut, test, result, report, attachments=attachments)

    def export_pdf(self, dut, test, result, report):
        """Build a formal report .pdf and return a BytesIO buffer."""
        return build_report_pdf(dut, test, result, report)
