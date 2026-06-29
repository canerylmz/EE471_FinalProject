"""Repeatable demo data setup for presentation environments."""

import json
import os
import base64
from datetime import date, timedelta

from .evaluation_service import STATUS_NOT_EVALUATED


DEMO_MARKER = "DEMO_DATA"
DEMO_PROJECT_CODE = "DEMO-ISO16750-STAGEV"
DEMO_TEST_KEYS = (
    "ISO16750-2_DC_SUPPLY_VOLTAGE",
    "ISO16750-2_SUPERIMPOSED_ALTERNATING_VOLTAGE",
    "ISO16750-2_OVERVOLTAGE",
    "ISO16750-4_LOW_TEMPERATURE_OPERATION",
    "ISO16750-5_CHEMICAL_RESISTANCE",
)


class DemoSeedService:
    """Creates realistic ISO 16750 demo records without changing core workflows."""

    def __init__(self, db, upload_dir, evaluation_service):
        self.db = db
        self.upload_dir = upload_dir
        self.evaluation_service = evaluation_service

    def seed(self, reset_demo_data=False):
        """Create or return the demo dataset."""
        if reset_demo_data:
            self._reset_demo_data()

        existing = self._existing_demo_dut()
        if existing:
            return self._summary(existing["id"], created=False)

        client_id = self._create_client()
        project_id = self._create_project(client_id)
        dut_id = self._create_dut(client_id, project_id)
        tests = self._create_test_plan(dut_id)
        results = self._create_results(dut_id, tests)
        equipment = self._create_equipment()
        links = self._link_equipment(tests, equipment)
        attachments = self._create_attachments(dut_id, tests, results)
        return self._summary(
            dut_id,
            created=True,
            tests=tests,
            results=results,
            equipment=equipment,
            links=links,
            attachments=attachments,
        )

    def status(self):
        """Return presentation readiness information for the demo dataset."""
        dut = self._existing_demo_dut()
        if not dut:
            return {
                "demo_data_loaded": False,
                "demo_dut_id": None,
                "demo_project_no": None,
                "demo_test_count": 0,
                "demo_result_count": 0,
                "demo_attachment_count": 0,
                "demo_equipment_count": 0,
                "first_demo_test_id": None,
                "first_demo_result_test_id": None,
                "recommended_start_route": "/dashboard",
                "missing_demo_items": [
                    "Demo DUT",
                    "Demo test plan",
                    "Demo results",
                    "Demo attachments",
                    "Demo equipment",
                ],
            }

        dut_id = dut["id"]
        project_no = dut.get("project") or DEMO_PROJECT_CODE
        tests = self.db.query(
            "SELECT id, test_name, category FROM tests WHERE dut_id = ? ORDER BY id ASC",
            (dut_id,),
        )
        results = self.db.query("SELECT test_id FROM results WHERE dut_id = ?", (dut_id,))
        attachments = self.db.query("SELECT id FROM test_attachments WHERE dut_id = ?", (dut_id,))
        equipment = self.db.query("SELECT id FROM equipment WHERE notes LIKE ?", (f"%{DEMO_MARKER}%",))
        first_result_test_id = results[0]["test_id"] if results else None
        missing = []
        if not tests:
            missing.append("Demo test plan")
        if len(results) < len(DEMO_TEST_KEYS):
            missing.append("Demo results for all selected tests")
        if not attachments:
            missing.append("Demo attachments")
        if len(equipment) < 3:
            missing.append("Demo equipment")

        return {
            "demo_data_loaded": not missing,
            "demo_dut_id": dut_id,
            "demo_project_no": project_no,
            "demo_test_count": len(tests),
            "demo_result_count": len(results),
            "demo_attachment_count": len(attachments),
            "demo_equipment_count": len(equipment),
            "first_demo_test_id": tests[0]["id"] if tests else None,
            "first_demo_result_test_id": first_result_test_id,
            "recommended_start_route": f"/plan/{dut_id}" if tests else "/dashboard",
            "missing_demo_items": missing,
        }

    def _reset_demo_data(self):
        duts = self.db.query("SELECT id FROM duts WHERE notes LIKE ?", (f"%{DEMO_MARKER}%",))
        dut_ids = [row["id"] for row in duts]
        if dut_ids:
            placeholders = ", ".join("?" for _ in dut_ids)
            tests = self.db.query(f"SELECT id FROM tests WHERE dut_id IN ({placeholders})", tuple(dut_ids))
            test_ids = [row["id"] for row in tests]
            if test_ids:
                test_placeholders = ", ".join("?" for _ in test_ids)
                attachment_rows = self.db.query(
                    f"SELECT file_path FROM test_attachments WHERE test_id IN ({test_placeholders})",
                    tuple(test_ids),
                )
                for attachment in attachment_rows:
                    self._remove_file(attachment.get("file_path"))
                self.db.execute(f"DELETE FROM test_attachments WHERE test_id IN ({test_placeholders})", tuple(test_ids))
                self.db.execute(f"DELETE FROM test_equipment WHERE test_id IN ({test_placeholders})", tuple(test_ids))
                self.db.execute(f"DELETE FROM results WHERE test_id IN ({test_placeholders})", tuple(test_ids))
                self.db.execute(f"DELETE FROM test_plan_items WHERE dut_id IN ({placeholders})", tuple(dut_ids))
                self.db.execute(f"DELETE FROM tests WHERE dut_id IN ({placeholders})", tuple(dut_ids))
            self.db.execute(f"DELETE FROM duts WHERE id IN ({placeholders})", tuple(dut_ids))

        self.db.execute("DELETE FROM equipment WHERE notes LIKE ?", (f"%{DEMO_MARKER}%",))
        self.db.execute("DELETE FROM test_campaigns WHERE objective LIKE ?", (f"%{DEMO_MARKER}%",))
        self.db.execute("DELETE FROM projects WHERE description LIKE ? OR code = ?", (f"%{DEMO_MARKER}%", DEMO_PROJECT_CODE))
        self.db.execute("DELETE FROM clients WHERE notes LIKE ?", (f"%{DEMO_MARKER}%",))

    def _existing_demo_dut(self):
        return self.db.query_one(
            """
            SELECT d.*
            FROM duts d
            LEFT JOIN projects p ON p.id = d.project_id
            WHERE d.notes LIKE ? OR p.code = ?
            ORDER BY d.id DESC
            LIMIT 1
            """,
            (f"%{DEMO_MARKER}%", DEMO_PROJECT_CODE),
        )

    def _create_client(self):
        return self.db.insert(
            """
            INSERT INTO clients (name, contact_name, contact_email, contact_phone, notes)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                "Demo Automotive Systems",
                "Alex Morgan",
                "alex.morgan@example.com",
                "+90 212 555 0100",
                f"{DEMO_MARKER} presentation client",
            ),
        )

    def _create_project(self, client_id):
        return self.db.insert(
            """
            INSERT INTO projects (client_id, name, code, description, status, start_date)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                client_id,
                "Stage V Instrument Cluster Validation",
                DEMO_PROJECT_CODE,
                f"{DEMO_MARKER} ISO 16750 presentation project",
                "active",
                date.today().isoformat(),
            ),
        )

    def _create_dut(self, client_id, project_id):
        return self.db.insert(
            """
            INSERT INTO duts (
                name, manufacturer, part_number, mounting_location, power_class,
                nominal_voltage, customer, project, temp_min, temp_max, ip_class,
                notes, client_id, project_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "Stage V Instrument Cluster",
                "Demo Automotive Systems",
                "BC400 TT/B",
                "OS3: Non-Isolated Operator Station",
                "Class II",
                "12 Vdc",
                "Demo Automotive Systems",
                DEMO_PROJECT_CODE,
                -25,
                85,
                "Front Face IP66 - Rear Side IP65",
                f"{DEMO_MARKER} Product Description: Stage V Instrument Cluster; Model Name: BC400 TT/B; Working Voltage: 12 Vdc; Operating Temperature: -25 C / +85 C",
                client_id,
                project_id,
            ),
        )

    def _create_test_plan(self, dut_id):
        catalog = self._catalog_by_key()
        tests = []
        for index, key in enumerate(DEMO_TEST_KEYS, start=1):
            item = catalog[key]
            plan_item_id = self.db.insert(
                """
                INSERT INTO test_plan_items (
                    dut_id, iso_catalog_id, planned_test_no, iso_part, clause_no,
                    test_name, category, operating_mode, functional_status,
                    required_test_level, severity, sample_size, selection_reason,
                    status, sort_order, selected_parameters_json, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """,
                (
                    dut_id,
                    item["id"],
                    f"DEMO-TP-{index:03d}",
                    item.get("iso_part"),
                    item.get("clause_number"),
                    item.get("test_name"),
                    item.get("category"),
                    item.get("operating_mode"),
                    item.get("functional_status"),
                    item.get("required_test_level"),
                    item.get("severity"),
                    item.get("sample_size"),
                    "Selected for ISO 16750 presentation demo coverage.",
                    "completed" if index <= 3 else "in_progress",
                    index,
                    item.get("parameters_json") or "{}",
                ),
            )
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
                    dut_id,
                    item.get("test_name"),
                    f"{item.get('iso_part')} clause {item.get('clause_number')}",
                    item.get("category"),
                    "Mandatory",
                    2,
                    json.dumps(self._required_equipment_for(item.get("category"))),
                    item.get("purpose") or "Project-defined acceptance criteria.",
                    item.get("severity") or "TBD",
                    item["id"],
                    item.get("iso_part"),
                    item.get("clause_number"),
                    item.get("operating_mode"),
                    item.get("functional_status"),
                    item.get("required_test_level"),
                    item.get("sample_size"),
                    "Selected for ISO 16750 presentation demo coverage.",
                    plan_item_id,
                ),
            )
            self.db.execute(
                "UPDATE test_plan_items SET test_id = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (test_id, plan_item_id),
            )
            tests.append(self.db.query_one("SELECT * FROM tests WHERE id = ?", (test_id,)))
        return tests

    def _create_results(self, dut_id, tests):
        by_name = {test["test_name"]: test for test in tests}
        payloads = [
            (
                by_name["DC Supply Voltage"],
                {
                    "us_min": 9,
                    "us_max": 16,
                    "duration": 2,
                    "measured_current": 1.2,
                    "functional_observation": "Normal operation observed.",
                },
                "No abnormal behavior was observed during voltage boundary operation.",
            ),
            (
                by_name["Superimposed Alternating Voltage"],
                {
                    "test_voltage": 14.0,
                    "ac_voltage_upp": 3.5,
                    "frequency_range": "f1: 10 Hz – 30 kHz; f2: 30 kHz – 200 kHz",
                    "sweep_duration": 120,
                    "number_of_sweeps": 1,
                    "measured_current": 1.7,
                    "functional_observation": "Display flickering observed between 2 kHz and 8 kHz during f1 sweep. Disturbance ceased when ripple was removed.",
                },
                "Measured Upp (3,5 V) exceeded Severity Level 2 limit (3,0 V ± 0,2 V). Functional disturbance observed during f1 sweep.",
            ),
            (
                by_name["Overvoltage"],
                {
                    "test_voltage": 18,
                    "duration": 60,
                    "measured_current": 1.5,
                    "functional_observation": "DUT remained functional during and after 60 min overvoltage exposure at 18 V.",
                },
                "No functional failure or permanent damage observed after overvoltage exposure.",
            ),
            (
                by_name["Low Temperature Operation"],
                {
                    "test_temperature": -15,
                    "duration": 24,
                    "recovery_time": 30,
                    "functional_observation": "Normal operation observed. However, chamber stabilization logs indicate target temperature was not achieved due to a door seal fault.",
                },
                "Test temperature of −15 °C did not reach the required Tmin per ISO 16750-4:2023, Table 1. Test must be repeated.",
            ),
            (
                by_name["Chemical Resistance / Chemical Loads"],
                {
                    "chemical_agent": "AA — Diesel fuel",
                    "application_method": "II — Wiping",
                    "exposure_duration": 22,
                    "visual_inspection": "No crack, swelling, or label damage observed after exposure.",
                    "functional_observation": "Normal operation confirmed after 22 h chemical exposure. No functional degradation detected.",
                },
                "No visual damage or functional degradation was observed after 22 h diesel fuel exposure by wiping.",
            ),
        ]
        results = []
        for test, measured_values, observations in payloads:
            evaluation = self.evaluation_service.evaluate(test, measured_values)
            result_label = self._result_label(evaluation["status"])
            result_id = self.db.insert(
                """
                INSERT INTO results (
                    test_id, dut_id, result, measured_values, temp, voltage, humidity,
                    observations, has_deviation, deviation_description, engineer_name
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    test["id"],
                    dut_id,
                    result_label,
                    json.dumps(measured_values),
                    23,
                    12,
                    45,
                    observations,
                    1 if evaluation["status"] == "FAIL" else 0,
                    "Functional disturbance observed during ripple exposure." if evaluation["status"] == "FAIL" else "",
                    "Demo Test Engineer",
                ),
            )
            self.evaluation_service.save_evaluation(result_id, evaluation)
            results.append(self.db.query_one("SELECT * FROM results WHERE id = ?", (result_id,)))
        return results

    def _create_equipment(self):
        equipment_rows = [
            (
                "EQ-DEMO-001",
                "Programmable DC Power Supply",
                "PSU-1200",
                "DC Supply",
                "Kikusui",
                "PWR-1200-001",
                date.today() - timedelta(days=30),
                date.today() + timedelta(days=180),
                "available",
                "Electrical Laboratory",
            ),
            (
                "EQ-DEMO-002",
                "Digital Oscilloscope",
                "MSO-5000",
                "Measurement",
                "Tektronix",
                "OSC-5000-014",
                date.today() - timedelta(days=330),
                date.today() + timedelta(days=15),
                "available",
                "Electrical Laboratory",
            ),
            (
                "EQ-DEMO-003",
                "Climatic Chamber",
                "TC-800",
                "Environmental Chamber",
                "Weiss Technik",
                "CH-800-022",
                date.today() - timedelta(days=420),
                date.today() - timedelta(days=5),
                "blocked",
                "Environmental Laboratory",
            ),
        ]
        created = []
        for row in equipment_rows:
            equipment_id = self.db.insert(
                """
                INSERT INTO equipment (
                    name, equipment_no, kind_of_equipment, model, type, manufacturer,
                    serial_no, last_calibration_date, next_calibration_date, using_status,
                    location, notes, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """,
                (
                    row[1],
                    row[0],
                    row[1],
                    row[2],
                    row[3],
                    row[4],
                    row[5],
                    row[6].isoformat(),
                    row[7].isoformat(),
                    row[8],
                    row[9],
                    f"{DEMO_MARKER} presentation equipment",
                ),
            )
            created.append(self.db.query_one("SELECT * FROM equipment WHERE id = ?", (equipment_id,)))
        return created

    def _link_equipment(self, tests, equipment):
        by_name = {test["test_name"]: test for test in tests}
        links = [
            (by_name["DC Supply Voltage"], equipment[0], "DUT supply voltage"),
            (by_name["Superimposed Alternating Voltage"], equipment[0], "DUT supply voltage"),
            (by_name["Superimposed Alternating Voltage"], equipment[1], "Ripple measurement"),
            (by_name["Low Temperature Operation"], equipment[2], "Temperature exposure"),
        ]
        created = []
        for test, item, role in links:
            link_id = self.db.insert(
                "INSERT INTO test_equipment (test_id, equipment_id, usage_role) VALUES (?, ?, ?)",
                (test["id"], item["id"], role),
            )
            created.append(link_id)
        return created

    def _create_attachments(self, dut_id, tests, results):
        by_name = {test["test_name"]: test for test in tests}
        result_by_test = {result["test_id"]: result for result in results}
        photo_test = by_name["DC Supply Voltage"]
        csv_test = by_name["Superimposed Alternating Voltage"]
        png_placeholder = base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/p9sAAAAASUVORK5CYII="
        )
        files = [
            (
                photo_test,
                result_by_test.get(photo_test["id"]),
                "test_photo",
                "demo_test_setup.png",
                png_placeholder,
                "Test setup photo placeholder",
                "image/png",
            ),
            (
                csv_test,
                result_by_test.get(csv_test["id"]),
                "measurement_file",
                "demo_ripple_measurement.csv",
                b"time_s,voltage_v,current_a\n0,12.1,1.2\n1,12.4,1.3\n2,12.0,1.2\n",
                "Ripple measurement CSV placeholder",
                "text/csv",
            ),
        ]
        created = []
        for test, result, attachment_type, filename, content, description, mime_type in files:
            path = self._write_placeholder_file(dut_id, test["id"], filename, content)
            attachment_id = self.db.insert(
                """
                INSERT INTO test_attachments (
                    dut_id, test_id, result_id, attachment_type, original_filename,
                    stored_filename, file_name, file_path, mime_type, file_size,
                    description, uploaded_by
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    dut_id,
                    test["id"],
                    (result or {}).get("id"),
                    attachment_type,
                    filename,
                    filename,
                    filename,
                    path,
                    mime_type,
                    len(content),
                    description,
                    "Demo Seed",
                ),
            )
            created.append(self.db.query_one("SELECT * FROM test_attachments WHERE id = ?", (attachment_id,)))
        return created

    def _write_placeholder_file(self, dut_id, test_id, filename, content):
        directory = os.path.join(self.upload_dir, f"dut_{dut_id}", f"test_{test_id}")
        os.makedirs(directory, exist_ok=True)
        path = os.path.join(directory, filename)
        with open(path, "wb") as handle:
            handle.write(content)
        return path

    def _catalog_by_key(self):
        rows = self.db.query(
            f"""
            SELECT * FROM iso_test_catalog
            WHERE catalog_key IN ({", ".join("?" for _ in DEMO_TEST_KEYS)})
            """,
            DEMO_TEST_KEYS,
        )
        by_key = {row["catalog_key"]: row for row in rows}
        missing = [key for key in DEMO_TEST_KEYS if key not in by_key]
        if missing:
            raise ValueError(f"Missing ISO catalog demo entries: {', '.join(missing)}")
        return by_key

    @staticmethod
    def _required_equipment_for(category):
        if category == "electrical":
            return ["Programmable DC power supply", "Digital oscilloscope", "Data logger"]
        if category == "environmental":
            return ["Climatic chamber", "Thermocouple", "Data logger"]
        if category == "chemical":
            return ["Chemical exposure setup", "Visual inspection station"]
        return ["Laboratory equipment"]

    @staticmethod
    def _result_label(status):
        labels = {
            "PASS": "Pass",
            "FAIL": "Fail",
            "CONDITIONAL PASS": "Conditional Pass",
            STATUS_NOT_EVALUATED: "Not Evaluated",
        }
        return labels.get(status, status)

    @staticmethod
    def _remove_file(path):
        if not path:
            return
        try:
            if os.path.isfile(path):
                os.remove(path)
        except OSError:
            pass

    def _summary(self, dut_id, created, tests=None, results=None, equipment=None, links=None, attachments=None):
        tests = tests if tests is not None else self.db.query("SELECT * FROM tests WHERE dut_id = ?", (dut_id,))
        results = results if results is not None else self.db.query("SELECT * FROM results WHERE dut_id = ?", (dut_id,))
        equipment = equipment if equipment is not None else self.db.query(
            "SELECT * FROM equipment WHERE notes LIKE ?",
            (f"%{DEMO_MARKER}%",),
        )
        attachments = attachments if attachments is not None else self.db.query(
            "SELECT * FROM test_attachments WHERE dut_id = ?",
            (dut_id,),
        )
        plan_items = self.db.query("SELECT * FROM test_plan_items WHERE dut_id = ?", (dut_id,))
        return {
            "created": created,
            "dut_id": dut_id,
            "client": "Demo Automotive Systems",
            "project": DEMO_PROJECT_CODE,
            "dut": "Stage V Instrument Cluster",
            "tests": len(tests),
            "plan_items": len(plan_items),
            "results": len(results),
            "equipment": len(equipment),
            "equipment_links": len(links) if links is not None else len(self.db.query("SELECT id FROM test_equipment")),
            "attachments": len(attachments),
            "marker": DEMO_MARKER,
        }
