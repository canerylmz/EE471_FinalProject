"""Service handling ISO 16750 test plan generation and storage."""

import json
import re
from difflib import SequenceMatcher

from ..ai_backend_client import AIBackendError
from ..fallbacks import fallback_plan
from ..prompts import build_plan_prompt
from ..utils.docx_export import build_plan_docx

PLAN_ITEM_STATUSES = {"planned", "approved", "in_progress", "completed", "cancelled"}


class PlanService:
    """Generates and persists ISO 16750 test plans for a DUT."""

    def __init__(self, db, ai_client):
        self.db = db
        self.ai_client = ai_client

    def generate_plan(self, dut):
        """Generate a test plan for `dut`, persist it, and return it."""
        catalog = self._catalog_entries()
        catalog_summary = self._catalog_summary(catalog)
        prompt = build_plan_prompt(dut, catalog_summary)

        raw_items = None
        fallback_used = False
        try:
            raw_items = self.ai_client.generate_json(prompt)
            if not isinstance(raw_items, list) or not raw_items:
                raise ValueError("AI response is not a non-empty test list")
            if any(not isinstance(item, dict) or not item.get("test_name") for item in raw_items):
                raise ValueError("AI response contains invalid test items")
            source = "ai-backend"
        except (AIBackendError, ValueError):
            raw_items = self._catalog_fallback_plan(dut, catalog)
            fallback_used = True
            source = "fallback"

        plan_items = [self._normalize_plan_item(item, catalog) for item in raw_items]

        # Replace any previously generated plan for this DUT.
        old_tests = self.db.query("SELECT id FROM tests WHERE dut_id = ?", (dut["id"],))
        for old_test in old_tests:
            self.db.execute("DELETE FROM results WHERE test_id = ?", (old_test["id"],))
        self.db.execute("DELETE FROM tests WHERE dut_id = ?", (dut["id"],))
        self.db.execute("DELETE FROM test_plan_items WHERE dut_id = ?", (dut["id"],))

        for index, item in enumerate(plan_items, start=1):
            equipment = item.get("required_equipment", [])
            if isinstance(equipment, str):
                equipment = [e.strip() for e in equipment.split(",") if e.strip()]

            plan_item_id = self._insert_plan_item(dut["id"], item, index)
            test_id = self.db.insert(
                """
                INSERT INTO tests (
                    dut_id, test_name, standard_reference, category, status,
                    duration_hours, required_equipment, acceptance_criteria,
                    severity_level, iso_catalog_id, iso_part, clause_no,
                    operating_mode, functional_status, required_test_level,
                    sample_size, selection_reason, test_plan_item_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    dut["id"],
                    item.get("test_name", ""),
                    item.get("standard_reference", ""),
                    item.get("category", ""),
                    item.get("status", "Optional"),
                    item.get("duration_hours", 0),
                    json.dumps(equipment),
                    item.get("acceptance_criteria", ""),
                    item.get("severity_level", item.get("severity", "III")),
                    item.get("iso_catalog_id"),
                    item.get("iso_part"),
                    item.get("clause_no"),
                    item.get("operating_mode"),
                    item.get("functional_status"),
                    item.get("required_test_level"),
                    item.get("sample_size"),
                    item.get("selection_reason"),
                    plan_item_id,
                ),
            )
            self.db.execute(
                """
                UPDATE test_plan_items
                SET test_id = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (test_id, plan_item_id),
            )

        tests = self.get_tests_for_dut(dut["id"])
        self._log_ai_decision(
            dut=dut,
            catalog_snapshot=catalog_summary,
            ai_response=raw_items,
            selected_tests=tests,
            fallback_used=fallback_used,
            source=source,
        )
        return tests, source

    def _insert_plan_item(self, dut_id, item, sort_order):
        planned_test_no = item.get("planned_test_no") or f"TP-{sort_order:03d}"
        return self.db.insert(
            """
            INSERT INTO test_plan_items (
                dut_id, iso_catalog_id, test_id, planned_test_no, iso_part,
                clause_no, test_name, category, operating_mode, functional_status,
                required_test_level, severity, sample_size, selection_reason,
                status, sort_order, selected_parameters_json, acceptance_criteria_override,
                updated_at
            ) VALUES (?, ?, NULL, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """,
            (
                dut_id,
                item.get("iso_catalog_id"),
                planned_test_no,
                item.get("iso_part"),
                item.get("clause_no"),
                item.get("test_name"),
                item.get("category"),
                item.get("operating_mode"),
                item.get("functional_status"),
                item.get("required_test_level"),
                item.get("severity_level", item.get("severity")),
                item.get("sample_size"),
                item.get("selection_reason"),
                item.get("plan_item_status", "planned"),
                sort_order,
                json.dumps(item.get("selected_parameters", {})),
                item.get("acceptance_criteria"),
            ),
        )

    def _catalog_entries(self):
        rows = self.db.query(
            """
            SELECT * FROM iso_test_catalog
            WHERE is_active = 1
            ORDER BY iso_part ASC, clause_number ASC, test_name ASC
            """
        )
        for row in rows:
            row["applicability_rules"] = json.loads(row.get("applicability_rules_json") or "{}")
        return rows

    @staticmethod
    def _catalog_summary(catalog):
        return [
            {
                "id": item["id"],
                "iso_part": item.get("iso_part"),
                "clause_no": item.get("clause_number"),
                "test_name": item.get("test_name"),
                "category": item.get("category"),
                "operating_mode": item.get("operating_mode"),
                "functional_status": item.get("functional_status"),
                "required_test_level": item.get("required_test_level"),
                "applicability_rules": item.get("applicability_rules", {}),
                "severity": item.get("severity"),
            }
            for item in catalog
        ]

    def _catalog_fallback_plan(self, dut, catalog):
        if not catalog:
            return fallback_plan(dut)

        mounting = (dut.get("mounting_location") or "").lower()
        selected = []
        for item in catalog:
            category = item.get("category")
            code = item.get("code") or ""
            if category == "electrical":
                selected.append(self._fallback_item_from_catalog(item, "Electrical baseline test"))
            elif category == "environmental" and code in {
                "LOW_TEMP_OPERATION",
                "HIGH_TEMP_OPERATION",
                "TEMP_CYCLING",
            }:
                selected.append(self._fallback_item_from_catalog(item, "Environmental exposure"))
            elif category == "chemical" and (
                "engine" in mounting or "underbody" in mounting or "exterior" in mounting
            ):
                selected.append(self._fallback_item_from_catalog(item, "Chemical exposure risk"))

        return selected or fallback_plan(dut)

    @staticmethod
    def _fallback_item_from_catalog(item, reason):
        iso_part = item.get("iso_part")
        clause_no = item.get("clause_number")
        return {
            "test_name": item.get("test_name"),
            "iso_part": iso_part,
            "clause_no": clause_no,
            "standard_reference": f"{iso_part} clause {clause_no}" if clause_no else iso_part,
            "category": item.get("category"),
            "operating_mode": item.get("operating_mode"),
            "functional_status": item.get("functional_status"),
            "required_test_level": item.get("required_test_level"),
            "severity": item.get("severity") or "TBD",
            "sample_size": item.get("sample_size"),
            "reason": reason,
            "status": "Mandatory",
            "duration_hours": 0,
            "required_equipment": [],
            "acceptance_criteria": item.get("purpose") or "Project-defined acceptance criteria.",
        }

    def _normalize_plan_item(self, item, catalog):
        match = self._match_catalog_item(item, catalog)
        iso_part = item.get("iso_part") or self._extract_iso_part(item.get("standard_reference"))
        clause_no = item.get("clause_no") or item.get("clause_number") or self._extract_clause(
            item.get("standard_reference")
        )

        if match:
            iso_part = iso_part or match.get("iso_part")
            clause_no = clause_no or match.get("clause_number")

        category = self._normalize_category(item.get("category") or (match or {}).get("category"))
        standard_reference = item.get("standard_reference") or self._standard_reference(
            iso_part, clause_no
        )
        reason = item.get("reason") or item.get("selection_reason")
        if match and not reason:
            reason = "Matched to ISO catalog entry."

        return {
            "test_name": item.get("test_name") or (match or {}).get("test_name", ""),
            "standard_reference": standard_reference,
            "category": category,
            "status": item.get("status", "Mandatory"),
            "duration_hours": item.get("duration_hours", 0),
            "required_equipment": item.get("required_equipment", []),
            "acceptance_criteria": item.get("acceptance_criteria")
            or (match or {}).get("purpose")
            or "Project-defined acceptance criteria.",
            "severity_level": item.get("severity_level")
            or item.get("severity")
            or (match or {}).get("severity")
            or "TBD",
            "iso_catalog_id": (match or {}).get("id"),
            "iso_part": iso_part,
            "clause_no": clause_no,
            "operating_mode": item.get("operating_mode") or (match or {}).get("operating_mode"),
            "functional_status": item.get("functional_status")
            or (match or {}).get("functional_status"),
            "required_test_level": item.get("required_test_level")
            or (match or {}).get("required_test_level"),
            "sample_size": item.get("sample_size") or (match or {}).get("sample_size"),
            "selection_reason": reason,
        }

    def _match_catalog_item(self, item, catalog):
        if not catalog:
            return None

        item_iso = self._normalize_iso_part(
            item.get("iso_part") or self._extract_iso_part(item.get("standard_reference"))
        )
        item_clause = self._normalize_clause(
            item.get("clause_no")
            or item.get("clause_number")
            or self._extract_clause(item.get("standard_reference"))
        )
        item_name = self._normalize_text(item.get("test_name"))
        item_category = self._normalize_category(item.get("category"))

        if item_clause:
            for candidate in catalog:
                same_clause = self._normalize_clause(candidate.get("clause_number")) == item_clause
                same_part = not item_iso or self._normalize_iso_part(candidate.get("iso_part")) == item_iso
                if same_clause and same_part:
                    return candidate

        if item_name:
            best_candidate = None
            best_score = 0
            for candidate in catalog:
                score = SequenceMatcher(
                    None,
                    item_name,
                    self._normalize_text(candidate.get("test_name")),
                ).ratio()
                if score > best_score:
                    best_candidate = candidate
                    best_score = score
            if best_score >= 0.72:
                return best_candidate

        if item_category and item_iso:
            matches = [
                candidate
                for candidate in catalog
                if candidate.get("category") == item_category
                and self._normalize_iso_part(candidate.get("iso_part")) == item_iso
            ]
            if len(matches) == 1:
                return matches[0]

        return None

    @staticmethod
    def _normalize_text(value):
        value = (value or "").lower()
        return re.sub(r"[^a-z0-9]+", " ", value).strip()

    @staticmethod
    def _normalize_category(value):
        value = (value or "").strip().lower()
        aliases = {
            "climatic": "environmental",
            "environment": "environmental",
            "electrical": "electrical",
            "electric": "electrical",
            "chemical": "chemical",
            "general": "general",
        }
        return aliases.get(value, value)

    @staticmethod
    def _normalize_iso_part(value):
        value = (value or "").upper().replace(" ", "")
        return value.replace("ISO16750", "ISO16750")

    @staticmethod
    def _normalize_clause(value):
        match = re.search(r"\d+(?:\.\d+)*", str(value or ""))
        return match.group(0) if match else ""

    @staticmethod
    def _extract_iso_part(value):
        match = re.search(r"ISO\s*16750\s*-?\s*(\d)", str(value or ""), re.IGNORECASE)
        return f"ISO16750-{match.group(1)}" if match else None

    def _extract_clause(self, value):
        if not value:
            return None
        candidates = re.findall(r"\d+(?:\.\d+)+", str(value))
        return candidates[-1] if candidates else None

    @staticmethod
    def _standard_reference(iso_part, clause_no):
        if iso_part and clause_no:
            return f"{iso_part} clause {clause_no}"
        return iso_part or ""

    def _log_ai_decision(
        self,
        dut,
        catalog_snapshot,
        ai_response,
        selected_tests,
        fallback_used,
        source,
    ):
        input_summary = {
            "dut_id": dut.get("id"),
            "name": dut.get("name"),
            "mounting_location": dut.get("mounting_location"),
            "nominal_voltage": dut.get("nominal_voltage"),
            "power_class": dut.get("power_class"),
            "temp_min": dut.get("temp_min"),
            "temp_max": dut.get("temp_max"),
            "ip_class": dut.get("ip_class"),
        }
        self.db.insert(
            """
            INSERT INTO ai_decision_logs (
                dut_id, decision_type, model_name, input_summary,
                catalog_snapshot, ai_response, selected_tests, fallback_used,
                source, status, response_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                dut.get("id"),
                "test_plan_generation",
                "ai-backend",
                json.dumps(input_summary),
                json.dumps(catalog_snapshot),
                json.dumps(ai_response),
                json.dumps(selected_tests),
                1 if fallback_used else 0,
                source,
                "fallback" if fallback_used else "success",
                json.dumps(ai_response),
            ),
        )

    def get_tests_for_dut(self, dut_id):
        """Return all tests for a DUT with `required_equipment` parsed."""
        tests = self.db.query(
            """
            SELECT
                tests.*,
                test_plan_items.planned_test_no AS planned_test_no,
                test_plan_items.status AS plan_item_status,
                test_plan_items.sort_order AS sort_order,
                test_plan_items.updated_at AS plan_item_updated_at
            FROM tests
            LEFT JOIN test_plan_items ON test_plan_items.id = tests.test_plan_item_id
            WHERE tests.dut_id = ?
            ORDER BY
                CASE WHEN test_plan_items.sort_order IS NULL THEN 1 ELSE 0 END,
                test_plan_items.sort_order ASC,
                tests.id ASC
            """,
            (dut_id,),
        )
        for test in tests:
            test["required_equipment"] = json.loads(test["required_equipment"] or "[]")
        return tests

    def get_test(self, test_id):
        """Return a single test with `required_equipment` parsed."""
        test = self.db.query_one(
            """
            SELECT
                tests.*,
                test_plan_items.planned_test_no AS planned_test_no,
                test_plan_items.status AS plan_item_status,
                test_plan_items.sort_order AS sort_order,
                test_plan_items.updated_at AS plan_item_updated_at
            FROM tests
            LEFT JOIN test_plan_items ON test_plan_items.id = tests.test_plan_item_id
            WHERE tests.id = ?
            """,
            (test_id,),
        )
        if test:
            test["required_equipment"] = json.loads(test["required_equipment"] or "[]")
        return test

    def get_plan_items_for_dut(self, dut_id):
        """Return official plan rows for a DUT."""
        return self.db.query(
            """
            SELECT * FROM test_plan_items
            WHERE dut_id = ?
            ORDER BY
                CASE WHEN sort_order IS NULL THEN 1 ELSE 0 END,
                sort_order ASC,
                id ASC
            """,
            (dut_id,),
        )

    def get_plan_item(self, plan_item_id):
        """Return one official plan row."""
        return self.db.query_one("SELECT * FROM test_plan_items WHERE id = ?", (plan_item_id,))

    def update_plan_item_status(self, plan_item_id, status):
        """Update one plan row status."""
        if status not in PLAN_ITEM_STATUSES:
            raise ValueError("Invalid plan item status")
        item = self.get_plan_item(plan_item_id)
        if not item:
            return None
        self.db.execute(
            """
            UPDATE test_plan_items
            SET status = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (status, plan_item_id),
        )
        return self.get_plan_item(plan_item_id)

    def update_plan_item_order(self, plan_item_id, sort_order):
        """Update one plan row sort order."""
        item = self.get_plan_item(plan_item_id)
        if not item:
            return None
        self.db.execute(
            """
            UPDATE test_plan_items
            SET sort_order = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (sort_order, plan_item_id),
        )
        return self.get_plan_item(plan_item_id)

    def export_docx(self, dut, tests):
        """Build a .docx test plan document and return a BytesIO buffer."""
        return build_plan_docx(dut, tests)
