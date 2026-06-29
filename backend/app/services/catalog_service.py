"""Service for ISO 16750 catalog lookup."""

import json


JSON_FIELDS = (
    "parameters_json",
    "applicability_rules_json",
    "result_input_schema_json",
    "report_section_schema_json",
)


class CatalogService:
    """Reads the ISO 16750 master test catalog."""

    def __init__(self, db):
        self.db = db

    def list_tests(self, category=None, iso_part=None):
        """Return active catalog tests with optional filters."""
        clauses = ["is_active = 1"]
        params = []

        if category:
            clauses.append("category = ?")
            params.append(category)
        if iso_part:
            clauses.append("iso_part = ?")
            params.append(iso_part)

        rows = self.db.query(
            f"""
            SELECT * FROM iso_test_catalog
            WHERE {" AND ".join(clauses)}
            ORDER BY iso_part ASC, clause_number ASC, test_name ASC
            """,
            tuple(params),
        )
        return [self._parse_json_fields(row) for row in rows]

    def get_test(self, catalog_id):
        """Return one active catalog test by id."""
        row = self.db.query_one(
            "SELECT * FROM iso_test_catalog WHERE id = ? AND is_active = 1",
            (catalog_id,),
        )
        return self._parse_json_fields(row) if row else None

    @staticmethod
    def _parse_json_fields(row):
        parsed = dict(row)
        for field in JSON_FIELDS:
            parsed[field.replace("_json", "")] = json.loads(parsed.get(field) or "{}")
            parsed.pop(field, None)
        return parsed
