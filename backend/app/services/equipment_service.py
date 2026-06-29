"""Equipment and calibration tracking service."""

from datetime import date, datetime, timedelta


EQUIPMENT_FIELDS = (
    "equipment_no",
    "kind_of_equipment",
    "model",
    "type",
    "manufacturer",
    "serial_no",
    "last_calibration_date",
    "next_calibration_date",
    "last_verification_date",
    "next_verification_date",
    "using_status",
    "location",
    "notes",
)


class EquipmentService:
    """CRUD and test-link operations for laboratory equipment."""

    def __init__(self, db):
        self.db = db

    def list_all(self):
        return [self._with_status(row) for row in self.db.query("SELECT * FROM equipment ORDER BY id DESC")]

    def get(self, equipment_id):
        row = self.db.query_one("SELECT * FROM equipment WHERE id = ?", (equipment_id,))
        return self._with_status(row) if row else None

    def create(self, data):
        values = self._values(data)
        name = values.get("kind_of_equipment") or values.get("equipment_no") or "Equipment"
        equipment_id = self.db.insert(
            f"""
            INSERT INTO equipment (
                name, {", ".join(EQUIPMENT_FIELDS)}, updated_at
            ) VALUES (?, {", ".join("?" for _ in EQUIPMENT_FIELDS)}, CURRENT_TIMESTAMP)
            """,
            (name, *(values[field] for field in EQUIPMENT_FIELDS)),
        )
        return self.get(equipment_id)

    def update(self, equipment_id, data):
        existing = self.get(equipment_id)
        if not existing:
            return None
        values = {field: data.get(field, existing.get(field, "")) for field in EQUIPMENT_FIELDS}
        assignments = ", ".join(f"{field} = ?" for field in EQUIPMENT_FIELDS)
        name = values.get("kind_of_equipment") or values.get("equipment_no") or "Equipment"
        self.db.execute(
            f"UPDATE equipment SET name = ?, {assignments}, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (name, *(values[field] for field in EQUIPMENT_FIELDS), equipment_id),
        )
        return self.get(equipment_id)

    def delete(self, equipment_id):
        equipment = self.get(equipment_id)
        if not equipment:
            return None
        self.db.execute("DELETE FROM test_equipment WHERE equipment_id = ?", (equipment_id,))
        self.db.execute("DELETE FROM equipment WHERE id = ?", (equipment_id,))
        return equipment

    def link_to_test(self, test_id, equipment_id, usage_role=""):
        if not self.db.query_one("SELECT id FROM tests WHERE id = ?", (test_id,)):
            raise ValueError("Test not found.")
        if not self.get(equipment_id):
            raise ValueError("Equipment not found.")
        existing = self.db.query_one(
            "SELECT * FROM test_equipment WHERE test_id = ? AND equipment_id = ?",
            (test_id, equipment_id),
        )
        if existing:
            return self._link_with_equipment(existing)
        link_id = self.db.insert(
            "INSERT INTO test_equipment (test_id, equipment_id, usage_role) VALUES (?, ?, ?)",
            (test_id, equipment_id, usage_role or ""),
        )
        return self.get_link(link_id)

    def list_for_test(self, test_id):
        rows = self.db.query(
            """
            SELECT te.id AS link_id, te.usage_role, te.created_at AS linked_at, e.*
            FROM test_equipment te
            JOIN equipment e ON e.id = te.equipment_id
            WHERE te.test_id = ?
            ORDER BY te.id DESC
            """,
            (test_id,),
        )
        return [self._with_status(row) for row in rows]

    def get_link(self, link_id):
        row = self.db.query_one(
            """
            SELECT te.id AS link_id, te.usage_role, te.created_at AS linked_at, e.*
            FROM test_equipment te
            JOIN equipment e ON e.id = te.equipment_id
            WHERE te.id = ?
            """,
            (link_id,),
        )
        return self._with_status(row) if row else None

    def unlink(self, link_id):
        link = self.get_link(link_id)
        if not link:
            return None
        self.db.execute("DELETE FROM test_equipment WHERE id = ?", (link_id,))
        return link

    def _link_with_equipment(self, link):
        return self.get_link(link["id"])

    @staticmethod
    def _values(data):
        return {field: data.get(field, "") for field in EQUIPMENT_FIELDS}

    def _with_status(self, row):
        if not row:
            return row
        row = dict(row)
        row["calibration_status"] = self.calibration_status(row.get("next_calibration_date"))
        return row

    @staticmethod
    def calibration_status(next_calibration_date):
        if not next_calibration_date:
            return "not_available"
        try:
            due_date = datetime.strptime(next_calibration_date, "%Y-%m-%d").date()
        except (TypeError, ValueError):
            return "not_available"
        today = date.today()
        if due_date < today:
            return "expired"
        if due_date <= today + timedelta(days=30):
            return "due_soon"
        return "valid"
