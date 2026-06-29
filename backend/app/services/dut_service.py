"""Service handling Device Under Test (DUT) records."""


class DUTService:
    """CRUD operations for DUT records."""

    def __init__(self, db):
        self.db = db

    def create(self, data):
        """Insert a new DUT record and return the saved row."""
        dut_id = self.db.insert(
            """
            INSERT INTO duts (
                name, manufacturer, part_number, mounting_location, power_class,
                nominal_voltage, customer, project, temp_min, temp_max, ip_class, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                data.get("name", ""),
                data.get("manufacturer", ""),
                data.get("part_number", ""),
                data.get("mounting_location", ""),
                data.get("power_class", ""),
                data.get("nominal_voltage", ""),
                data.get("customer", ""),
                data.get("project", ""),
                data.get("temp_min"),
                data.get("temp_max"),
                data.get("ip_class", ""),
                data.get("notes", ""),
            ),
        )
        return self.get(dut_id)

    def list_all(self):
        """Return all DUTs, most recently created first."""
        return self.db.query("SELECT * FROM duts ORDER BY created_at DESC")

    def get(self, dut_id):
        """Return a single DUT by id, or None if not found."""
        return self.db.query_one("SELECT * FROM duts WHERE id = ?", (dut_id,))

    def delete(self, dut_id):
        """Delete a DUT and its dependent workflow records."""
        dut = self.get(dut_id)
        if not dut:
            return None

        tests = self.db.query("SELECT id FROM tests WHERE dut_id = ?", (dut_id,))
        test_ids = [test["id"] for test in tests]
        if test_ids:
            placeholders = ", ".join("?" for _ in test_ids)
            self.db.execute(f"DELETE FROM test_equipment WHERE test_id IN ({placeholders})", tuple(test_ids))
            self.db.execute(f"DELETE FROM results WHERE test_id IN ({placeholders})", tuple(test_ids))
            self.db.execute(f"DELETE FROM test_attachments WHERE test_id IN ({placeholders})", tuple(test_ids))
            self.db.execute(f"DELETE FROM tests WHERE id IN ({placeholders})", tuple(test_ids))

        self.db.execute("DELETE FROM test_plan_items WHERE dut_id = ?", (dut_id,))
        self.db.execute("DELETE FROM test_campaigns WHERE dut_id = ?", (dut_id,))
        self.db.execute("DELETE FROM ai_decision_logs WHERE dut_id = ?", (dut_id,))
        self.db.execute("DELETE FROM duts WHERE id = ?", (dut_id,))
        return dut
