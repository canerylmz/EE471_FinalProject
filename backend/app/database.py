"""SQLite database access layer for TestForge."""

import json
import os
import sqlite3
import threading

SCHEMA = """
CREATE TABLE IF NOT EXISTS duts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    manufacturer TEXT,
    part_number TEXT,
    mounting_location TEXT,
    power_class TEXT,
    nominal_voltage TEXT,
    customer TEXT,
    project TEXT,
    temp_min REAL,
    temp_max REAL,
    ip_class TEXT,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS tests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    dut_id INTEGER REFERENCES duts(id),
    test_name TEXT,
    standard_reference TEXT,
    category TEXT,
    status TEXT,
    duration_hours REAL,
    required_equipment TEXT,
    acceptance_criteria TEXT,
    severity_level TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    test_id INTEGER REFERENCES tests(id),
    dut_id INTEGER REFERENCES duts(id),
    result TEXT,
    measured_values TEXT,
    temp REAL,
    voltage REAL,
    humidity REAL,
    observations TEXT,
    has_deviation INTEGER DEFAULT 0,
    deviation_description TEXT,
    root_cause TEXT,
    corrective_action TEXT,
    report_text TEXT,
    engineer_name TEXT,
    evaluation_status TEXT,
    evaluation_score REAL,
    evaluation_details_json TEXT,
    evaluated_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS clients (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    contact_name TEXT,
    contact_email TEXT,
    contact_phone TEXT,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS projects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id INTEGER REFERENCES clients(id),
    name TEXT NOT NULL,
    code TEXT,
    description TEXT,
    status TEXT DEFAULT 'active',
    start_date TEXT,
    end_date TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(client_id, name)
);

CREATE TABLE IF NOT EXISTS test_campaigns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER REFERENCES projects(id),
    dut_id INTEGER REFERENCES duts(id),
    name TEXT NOT NULL,
    objective TEXT,
    status TEXT DEFAULT 'draft',
    start_date TEXT,
    end_date TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS iso_test_catalog (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    catalog_key TEXT NOT NULL UNIQUE,
    iso_part TEXT NOT NULL,
    category TEXT NOT NULL,
    clause_number TEXT,
    test_name TEXT NOT NULL,
    purpose TEXT,
    operating_mode TEXT,
    functional_status TEXT,
    required_test_level TEXT,
    sample_size TEXT,
    severity TEXT,
    code TEXT,
    parameters_json TEXT DEFAULT '{}',
    applicability_rules_json TEXT DEFAULT '{}',
    result_input_schema_json TEXT DEFAULT '{}',
    evaluation_schema_json TEXT DEFAULT '{}',
    report_section_schema_json TEXT DEFAULT '{}',
    record_form_template_key TEXT,
    is_active INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS test_plan_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    campaign_id INTEGER REFERENCES test_campaigns(id),
    dut_id INTEGER REFERENCES duts(id),
    iso_catalog_id INTEGER REFERENCES iso_test_catalog(id),
    test_id INTEGER REFERENCES tests(id),
    sequence_no INTEGER,
    status TEXT DEFAULT 'planned',
    selected_parameters_json TEXT DEFAULT '{}',
    acceptance_criteria_override TEXT,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS equipment (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    equipment_no TEXT,
    kind_of_equipment TEXT,
    equipment_type TEXT,
    type TEXT,
    manufacturer TEXT,
    model TEXT,
    serial_no TEXT,
    serial_number TEXT,
    last_calibration_date TEXT,
    next_calibration_date TEXT,
    calibration_due_date TEXT,
    last_verification_date TEXT,
    next_verification_date TEXT,
    using_status TEXT,
    location TEXT,
    status TEXT DEFAULT 'available',
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS test_equipment (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    test_id INTEGER REFERENCES tests(id),
    equipment_id INTEGER REFERENCES equipment(id),
    usage_role TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS test_attachments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    dut_id INTEGER REFERENCES duts(id),
    test_id INTEGER REFERENCES tests(id),
    result_id INTEGER REFERENCES results(id),
    attachment_type TEXT,
    original_filename TEXT,
    stored_filename TEXT,
    file_name TEXT,
    file_path TEXT,
    mime_type TEXT,
    file_size INTEGER,
    description TEXT,
    uploaded_by TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS report_templates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    template_key TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    document_type TEXT,
    version TEXT DEFAULT '1.0',
    schema_json TEXT DEFAULT '{}',
    file_path TEXT,
    is_active INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS ai_decision_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    dut_id INTEGER REFERENCES duts(id),
    test_id INTEGER REFERENCES tests(id),
    iso_catalog_id INTEGER REFERENCES iso_test_catalog(id),
    decision_type TEXT,
    model_name TEXT,
    prompt TEXT,
    response_json TEXT,
    source TEXT,
    status TEXT,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

ISO_TEST_CATALOG_SEED = [
    {
        "catalog_key": "ISO16750-2_DC_SUPPLY_VOLTAGE",
        "iso_part": "ISO16750-2",
        "category": "electrical",
        "clause_number": "4.2",
        "test_name": "DC Supply Voltage",
        "purpose": "Verify operation across the declared DC supply voltage range.",
        "operating_mode": (
            "3.3 (minimum load) and 3.4 (maximum load) at Tmin and Tmax; 3.2 (typical load) at "
            "room temperature — per ISO 16750-2:2023, Table 1"
        ),
        "functional_status": "Class A/B as applicable",
        "required_test_level": "Nominal and boundary voltage levels",
        "sample_size": "TBD",
        "severity": "TBD",
        "code": "DC_SUPPLY",
        "parameters_json": '{"voltage_levels": [], "duration": "TBD"}',
        "applicability_rules_json": '{"power_supply": "dc"}',
        "result_input_schema_json": json.dumps([
            {
                "name": "us_min",
                "label": "USmin",
                "type": "number",
                "unit": "V",
                "required": True,
                "requirement": (
                    "Per ISO 16750-2:2023, Table 3 (12 V system): Code A = 9 V; Code B = 6 V; "
                    "Code C = 8 V; Code D = 10,5 V. [Specify applicable code per project spec]"
                ),
            },
            {
                "name": "us_max",
                "label": "USmax",
                "type": "number",
                "unit": "V",
                "required": True,
                "requirement": (
                    "Per ISO 16750-2:2023, Table 3 (12 V system): Codes A/B/C/D = 16 V. "
                    "[Specify applicable code per project spec]"
                ),
            },
            {
                "name": "duration",
                "label": "Duration",
                "type": "number",
                "unit": "h",
                "required": True,
                "requirement": (
                    "Dwell time ≥ 30 s at USmin/USmax (t1); ≥ 60 s at UA (t2) — "
                    "per ISO 16750-2:2023, Table 2."
                ),
            },
            {
                "name": "measured_current",
                "label": "Measured Current",
                "type": "number",
                "unit": "A",
                "required": False,
                "requirement": (
                    "[TBD — specify per project agreement between customer and supplier; "
                    "current is not separately limited by ISO 16750-2:2023, Clause 4.2]"
                ),
            },
            {
                "name": "functional_observation",
                "label": "Functional Observation",
                "type": "textarea",
                "required": True,
                "requirement": (
                    "DUT shall maintain functional status Class A per ISO 16750-1:2023, Clause "
                    "6.2, during active operating modes. Unwanted operations are not permitted. "
                    "Pass/fail is determined in the Acceptance Criteria / Result table, not by "
                    "this observation."
                ),
            },
        ]),
        "evaluation_schema_json": json.dumps({
            "rules": [
                {
                    "field": "us_min",
                    "type": "min",
                    "min": 8.0,
                    "label": "USmin",
                    "unit": "V",
                    "fail_message": (
                        "Measured USmin ({value} V) is below the minimum supply voltage required "
                        "by ISO 16750-2:2023, Table 3 for the applicable voltage code."
                    ),
                },
                {
                    "field": "us_max",
                    "type": "max",
                    "max": 18.0,
                    "label": "USmax",
                    "unit": "V",
                    "fail_message": (
                        "Measured USmax ({value} V) exceeds the maximum supply voltage permitted "
                        "by ISO 16750-2:2023, Table 3 for the applicable voltage code."
                    ),
                },
                {
                    "field": "duration",
                    "type": "min",
                    "min": 1,
                    "label": "Duration",
                    "unit": "h",
                    "fail_message": (
                        "Recorded exposure duration ({value} h) is shorter than the minimum "
                        "dwell time required by ISO 16750-2:2023, Table 2."
                    ),
                },
            ]
        }),
        "report_section_schema_json": '{"sections": ["conditions", "measurements", "assessment"]}',
        "record_form_template_key": "electrical_basic",
    },
    {
        "catalog_key": "ISO16750-2_OVERVOLTAGE",
        "iso_part": "ISO16750-2",
        "category": "electrical",
        "clause_number": "4.3",
        "test_name": "Overvoltage",
        "purpose": "Verify DUT behavior under temporary overvoltage conditions.",
        "operating_mode": (
            "3.4 (maximum load, long-term overvoltage) or 2.2/2.3 (jump start) per ISO "
            "16750-1:2023 — see applicable sub-clause (ISO 16750-2:2023, Clause 4.3.1.1 / "
            "4.3.1.2)"
        ),
        "functional_status": "Class C or project-defined",
        "required_test_level": "TBD by nominal voltage class",
        "sample_size": "TBD",
        "severity": "TBD",
        "code": "OVERVOLTAGE",
        "parameters_json": '{"voltage": "TBD", "duration": "TBD"}',
        "applicability_rules_json": '{"nominal_voltage": ["12V", "24V"]}',
        "result_input_schema_json": json.dumps([
            {
                "name": "test_voltage",
                "label": "Test Voltage",
                "type": "number",
                "unit": "V",
                "required": True,
                "requirement": (
                    "Long-term overvoltage: 18 V (12 V system) / 36 V (24 V system) per ISO "
                    "16750-2:2023, Clause 4.3.1.1.1. Jump start (Utrans): 26 V per Clause "
                    "4.3.1.2.1. [Specify applicable sub-test per project spec]"
                ),
            },
            {
                "name": "duration",
                "label": "Duration",
                "type": "number",
                "unit": "min",
                "required": True,
                "requirement": (
                    "Long-term overvoltage: 60 min per Clause 4.3.1.1.2. Jump start (ttrans): "
                    "60 s, rest time (trest) 120 s per Clause 4.3.1.2.2. [Specify applicable "
                    "sub-test per project spec]"
                ),
            },
            {
                "name": "measured_current",
                "label": "Measured Current",
                "type": "number",
                "unit": "A",
                "required": False,
                "requirement": (
                    "[TBD — specify per project agreement between customer and supplier; "
                    "not separately limited by ISO 16750-2:2023, Clause 4.3]"
                ),
            },
            {
                "name": "functional_observation",
                "label": "Functional Observation",
                "type": "textarea",
                "required": True,
                "requirement": (
                    "Long-term overvoltage: DUT shall maintain minimum functional status Class C "
                    "per ISO 16750-1:2023, Clause 6.4 (ISO 16750-2:2023, Clause 4.3.1.1.3). Jump "
                    "start: minimum functional status Class C (Clause 4.3.1.2.3). Pass/fail is "
                    "determined in the Acceptance Criteria / Result table, not by this "
                    "observation."
                ),
            },
        ]),
        "evaluation_schema_json": '{}',
        "report_section_schema_json": '{"sections": ["setup", "exposure", "post_test_function"]}',
        "record_form_template_key": "electrical_basic",
    },
    {
        "catalog_key": "ISO16750-2_SUPERIMPOSED_ALTERNATING_VOLTAGE",
        "iso_part": "ISO16750-2",
        "category": "electrical",
        "clause_number": "4.4",
        "test_name": "Superimposed Alternating Voltage",
        "purpose": "Verify immunity to AC ripple superimposed on supply voltage.",
        "operating_mode": "Reference test: 3.3; Ripple test: 3.2 — per ISO 16750-2:2023, Clause 4.4.2",
        "functional_status": "Class A unless otherwise specified",
        "required_test_level": "Amplitude/frequency TBD",
        "sample_size": "TBD",
        "severity": "TBD",
        "code": "SUP_ALT_VOLTAGE",
        "parameters_json": '{"amplitude": "TBD", "frequency_range": "TBD"}',
        "applicability_rules_json": '{"power_supply": "dc"}',
        "result_input_schema_json": json.dumps([
            {
                "name": "test_voltage",
                "label": "Test Voltage",
                "type": "number",
                "unit": "V",
                "required": True,
                "requirement": (
                    "UA or UB as applicable to the reference/ripple test per ISO 16750-2:2023, "
                    "Clause 4.4.2. [Specify per project spec]"
                ),
            },
            {
                "name": "ac_voltage_upp",
                "label": "AC Voltage Ripple — Upp (peak-to-peak)",
                "type": "number",
                "unit": "V",
                "required": True,
                "requirement": (
                    "Per severity level (ISO 16750-2:2023, Table 8): Severity 1 = 6 V ± 0,2 V; "
                    "Severity 2 = 3 V ± 0,2 V; Severity 3 = 2 V ± 0,1 V; Severity 4 (f2 "
                    "only) = 1 V ± 0,1 V. [Specify applicable severity level per project]"
                ),
            },
            {
                "name": "frequency_range",
                "label": "Frequency Range",
                "type": "text",
                "unit": "Hz",
                "required": True,
                "requirement": (
                    "f1: 10 Hz to 30 kHz; f2: 30 kHz to 200 kHz, logarithmic sweep, 2 % step "
                    "— per ISO 16750-2:2023, Clause 4.4.2."
                ),
            },
            {
                "name": "sweep_duration",
                "label": "Sweep Duration",
                "type": "number",
                "unit": "s",
                "required": True,
                "requirement": "Dwell time ≥ 2 s per frequency step — per ISO 16750-2:2023, Clause 4.4.2.",
            },
            {
                "name": "number_of_sweeps",
                "label": "Number of Sweeps",
                "type": "number",
                "required": True,
                "requirement": "1 test sequence per test combination — per ISO 16750-2:2023, Table 7.",
            },
            {
                "name": "measured_current",
                "label": "Measured Current",
                "type": "number",
                "unit": "A",
                "required": False,
                "requirement": (
                    "[TBD — specify per project agreement between customer and supplier; "
                    "not separately limited by ISO 16750-2:2023, Clause 4.4 for this measurement]"
                ),
            },
            {
                "name": "functional_observation",
                "label": "Functional Observation",
                "type": "textarea",
                "required": True,
                "requirement": (
                    "DUT shall maintain functional status Class A per ISO 16750-1:2023, Clause "
                    "6.2, during active operating modes. Unwanted operations are not permitted. "
                    "DUT impedance shall be measured before and after; deviation shall remain "
                    "within agreed tolerance (ISO 16750-2:2023, Clause 4.4.3). Pass/fail is "
                    "determined in the Acceptance Criteria / Result table, not by this "
                    "observation."
                ),
            },
        ]),
        "evaluation_schema_json": json.dumps({
            "rules": [
                {
                    "field": "test_voltage",
                    "type": "range",
                    "min": 11.0,
                    "max": 14.5,
                    "label": "Test Voltage",
                    "unit": "V",
                    "fail_message": (
                        "Measured Test Voltage ({value} V) is outside the required reference "
                        "range (11,0 V to 14,5 V) per ISO 16750-2:2023, Clause 4.4.2."
                    ),
                },
                {
                    "field": "ac_voltage_upp",
                    "type": "max",
                    "max": 3.2,
                    "label": "AC Voltage Ripple — Upp (peak-to-peak)",
                    "unit": "V",
                    "fail_message": (
                        "Measured Upp ({value} V) exceeds the maximum permitted ripple voltage "
                        "({max} V) for Severity Level 2 (3,0 V ± 0,2 V) per ISO 16750-2:2023, "
                        "Table 8. The test condition was not met."
                    ),
                },
                {
                    "field": "number_of_sweeps",
                    "type": "min",
                    "min": 1,
                    "label": "Number of Sweeps",
                    "fail_message": (
                        "Recorded number of sweeps ({value}) is below the minimum required by "
                        "ISO 16750-2:2023, Table 7."
                    ),
                },
            ]
        }),
        "report_section_schema_json": '{"sections": ["ripple_profile", "observations", "assessment"]}',
        "record_form_template_key": "electrical_sweep",
    },
    {
        "catalog_key": "ISO16750-2_SLOW_DECREASE_INCREASE_SUPPLY_VOLTAGE",
        "iso_part": "ISO16750-2",
        "category": "electrical",
        "clause_number": "4.5",
        "test_name": "Slow Decrease and Increase of Supply Voltage",
        "purpose": "Verify DUT behavior during gradual supply voltage changes.",
        "operating_mode": "3.2 (typical load) per ISO 16750-1:2023",
        "functional_status": "Project-defined",
        "required_test_level": "Ramp profile TBD",
        "sample_size": "TBD",
        "severity": "TBD",
        "code": "SLOW_VOLTAGE_RAMP",
        "parameters_json": '{"ramp_rate": "TBD", "min_voltage": "TBD", "max_voltage": "TBD"}',
        "applicability_rules_json": '{"power_supply": "dc"}',
        "result_input_schema_json": json.dumps([
            {
                "name": "ramp_rate",
                "label": "Voltage Change Rate",
                "type": "number",
                "unit": "V/s",
                "required": True,
                "requirement": (
                    "0,5 ± 0,1 V/min (linear or equal steps ≤ 25 mV) — per ISO "
                    "16750-2:2023, Clause 4.5.2."
                ),
            },
            {
                "name": "min_voltage",
                "label": "Minimum Voltage",
                "type": "number",
                "unit": "V",
                "required": True,
                "requirement": "Voltage shall be decreased to 0 V — per ISO 16750-2:2023, Clause 4.5.2.",
            },
            {
                "name": "max_voltage",
                "label": "Maximum Voltage",
                "type": "number",
                "unit": "V",
                "required": True,
                "requirement": "Voltage shall be increased back to UA — per ISO 16750-2:2023, Clause 4.5.2.",
            },
            {
                "name": "functional_observation",
                "label": "Functional Observation",
                "type": "textarea",
                "required": True,
                "requirement": (
                    "DUT shall maintain functional status Class A within the normal supply "
                    "voltage range (Table 3/4); minimum Class D is required outside this range "
                    "— per ISO 16750-2:2023, Clause 4.5.3. Pass/fail is determined in the "
                    "Acceptance Criteria / Result table, not by this observation."
                ),
            },
        ]),
        "evaluation_schema_json": '{}',
        "report_section_schema_json": '{"sections": ["ramp_profile", "functional_behavior", "assessment"]}',
        "record_form_template_key": "electrical_ramp",
    },
    {
        "catalog_key": "ISO16750-4_LOW_TEMPERATURE_OPERATION",
        "iso_part": "ISO16750-4",
        "category": "environmental",
        "clause_number": "5.1",
        "test_name": "Low Temperature Operation",
        "purpose": "Verify DUT operation at low temperature.",
        "operating_mode": "3.3 or 4.3 (minimum load) per ISO 16750-1:2023",
        "functional_status": "Class A/B as applicable",
        "required_test_level": "Minimum operating temperature TBD",
        "sample_size": "TBD",
        "severity": "TBD",
        "code": "LOW_TEMP_OPERATION",
        "parameters_json": '{"temperature": "TBD", "duration": "TBD"}',
        "applicability_rules_json": '{"environment": "low_temperature"}',
        "result_input_schema_json": json.dumps([
            {
                "name": "test_temperature",
                "label": "Test Temperature — Tmin",
                "type": "number",
                "unit": "C",
                "required": True,
                "requirement": (
                    "Per ISO 16750-4:2023, Table 1 for the applicable DUT temperature code. "
                    "[Specify DUT temperature code per project spec]"
                ),
            },
            {
                "name": "duration",
                "label": "Duration",
                "type": "number",
                "unit": "h",
                "required": True,
                "requirement": "24 h — per ISO 16750-4:2023, Clause 5.1.1.2.2.",
            },
            {
                "name": "recovery_time",
                "label": "Recovery Time",
                "type": "number",
                "unit": "min",
                "required": False,
                "requirement": "[TBD — specify per project agreement between customer and supplier]",
            },
            {
                "name": "functional_observation",
                "label": "Functional Observation",
                "type": "textarea",
                "required": True,
                "requirement": (
                    "DUT shall maintain functional status Class A per ISO 16750-1:2023, Clause "
                    "6.2 (ISO 16750-4:2023, Clause 5.1.1.2.3). Pass/fail is determined in the "
                    "Acceptance Criteria / Result table, not by this observation."
                ),
            },
        ]),
        "evaluation_schema_json": json.dumps({
            "rules": [
                {
                    "field": "test_temperature",
                    "type": "max",
                    "max": -20,
                    "label": "Test Temperature — Tmin",
                    "unit": "°C",
                    "fail_message": (
                        "Recorded Tmin ({value} °C) does not reach the required low test "
                        "temperature per ISO 16750-4:2023, Table 1 for the applicable DUT "
                        "temperature code."
                    ),
                },
                {
                    "field": "duration",
                    "type": "min",
                    "min": 1,
                    "label": "Duration",
                    "unit": "h",
                    "fail_message": (
                        "Recorded exposure duration ({value} h) is shorter than the minimum "
                        "required by ISO 16750-4:2023, Clause 5.1.1.2.2."
                    ),
                },
            ]
        }),
        "report_section_schema_json": '{"sections": ["conditions", "observations", "assessment"]}',
        "record_form_template_key": "environmental_temperature",
    },
    {
        "catalog_key": "ISO16750-4_HIGH_TEMPERATURE_OPERATION",
        "iso_part": "ISO16750-4",
        "category": "environmental",
        "clause_number": "5.2",
        "test_name": "High Temperature Operation",
        "purpose": "Verify DUT operation at high temperature.",
        "operating_mode": "3.4 or 4.4 (maximum load) per ISO 16750-1:2023",
        "functional_status": "Class A/B as applicable",
        "required_test_level": "Maximum operating temperature TBD",
        "sample_size": "TBD",
        "severity": "TBD",
        "code": "HIGH_TEMP_OPERATION",
        "parameters_json": '{"temperature": "TBD", "duration": "TBD"}',
        "applicability_rules_json": '{"environment": "high_temperature"}',
        "result_input_schema_json": json.dumps([
            {
                "name": "test_temperature",
                "label": "Test Temperature — Tmax",
                "type": "number",
                "unit": "C",
                "required": True,
                "requirement": (
                    "Per ISO 16750-4:2023, Table 1 for the applicable DUT temperature code. "
                    "[Specify DUT temperature code per project spec]"
                ),
            },
            {
                "name": "duration",
                "label": "Duration",
                "type": "number",
                "unit": "h",
                "required": True,
                "requirement": "96 h — per ISO 16750-4:2023, Clause 5.1.2.2.2.",
            },
            {
                "name": "recovery_time",
                "label": "Recovery Time",
                "type": "number",
                "unit": "min",
                "required": False,
                "requirement": "[TBD — specify per project agreement between customer and supplier]",
            },
            {
                "name": "functional_observation",
                "label": "Functional Observation",
                "type": "textarea",
                "required": True,
                "requirement": (
                    "DUT shall maintain functional status Class A per ISO 16750-1:2023, Clause "
                    "6.2 (ISO 16750-4:2023, Clause 5.1.2.2.3). Pass/fail is determined in the "
                    "Acceptance Criteria / Result table, not by this observation."
                ),
            },
        ]),
        "evaluation_schema_json": '{}',
        "report_section_schema_json": '{"sections": ["conditions", "observations", "assessment"]}',
        "record_form_template_key": "environmental_temperature",
    },
    {
        "catalog_key": "ISO16750-4_TEMPERATURE_CYCLING",
        "iso_part": "ISO16750-4",
        "category": "environmental",
        "clause_number": "5.3",
        "test_name": "Temperature Cycling",
        "purpose": "Verify DUT resistance to repeated temperature transitions.",
        "operating_mode": (
            "3.3 or 4.3 at Tmin; 3.4 or 4.4 at Tmax; 2.1 during temperature transitions — "
            "per ISO 16750-4:2023, Clause 5.3.1.2"
        ),
        "functional_status": "Post-test functional verification",
        "required_test_level": "Cycle profile TBD",
        "sample_size": "TBD",
        "severity": "TBD",
        "code": "TEMP_CYCLING",
        "parameters_json": '{"low_temperature": "TBD", "high_temperature": "TBD", "cycles": "TBD"}',
        "applicability_rules_json": '{"environment": "temperature_cycling"}',
        "result_input_schema_json": json.dumps([
            {
                "name": "tmin",
                "label": "Test Temperature — Tmin",
                "type": "number",
                "unit": "C",
                "required": True,
                "requirement": (
                    "Per ISO 16750-4:2023, Table 1 for the applicable DUT temperature code. "
                    "[Specify DUT temperature code per project spec]"
                ),
            },
            {
                "name": "tmax",
                "label": "Test Temperature — Tmax",
                "type": "number",
                "unit": "C",
                "required": True,
                "requirement": (
                    "Per ISO 16750-4:2023, Table 1 for the applicable DUT temperature code. "
                    "[Specify DUT temperature code per project spec]"
                ),
            },
            {
                "name": "cycle_count",
                "label": "Number of Cycles",
                "type": "number",
                "required": True,
                "requirement": "30 cycles — per ISO 16750-4:2023, Clause 5.3.1.2.",
            },
            {
                "name": "dwell_time",
                "label": "Dwell Time per Step",
                "type": "number",
                "unit": "min",
                "required": True,
                "requirement": (
                    "t1 (RT→Tmin) 60 min; t2 (exposure at Tmin) 90 min; t3 (Tmin→RT) "
                    "60 min; t4 (RT→Tmax) 90 min; t5 (exposure at Tmax) 110 min; t6 "
                    "(Tmax→RT) 70 min — per ISO 16750-4:2023, Clause 5.3.1.2 (IEC "
                    "60068-2-14, Test Nb)."
                ),
            },
            {
                "name": "functional_observation",
                "label": "Functional Observation",
                "type": "textarea",
                "required": True,
                "requirement": (
                    "DUT shall maintain functional status Class A per ISO 16750-1:2023, Clause "
                    "6.2, during active operating modes (ISO 16750-4:2023, Clause 5.3.1.4). "
                    "Pass/fail is determined in the Acceptance Criteria / Result table, not by "
                    "this observation."
                ),
            },
        ]),
        "evaluation_schema_json": json.dumps({
            "rules": [
                {
                    "field": "tmin",
                    "type": "max",
                    "max": -20,
                    "label": "Test Temperature — Tmin",
                    "unit": "°C",
                    "fail_message": (
                        "Recorded Tmin ({value} °C) does not reach the required low "
                        "cycling temperature per ISO 16750-4:2023, Table 1."
                    ),
                },
                {
                    "field": "tmax",
                    "type": "min",
                    "min": 80,
                    "label": "Test Temperature — Tmax",
                    "unit": "°C",
                    "fail_message": (
                        "Recorded Tmax ({value} °C) does not reach the required high "
                        "cycling temperature per ISO 16750-4:2023, Table 1."
                    ),
                },
                {
                    "field": "cycle_count",
                    "type": "min",
                    "min": 1,
                    "label": "Number of Cycles",
                    "fail_message": (
                        "Recorded number of cycles ({value}) is below the 30 cycles required by "
                        "ISO 16750-4:2023, Clause 5.3.1.2."
                    ),
                },
            ]
        }),
        "report_section_schema_json": '{"sections": ["cycle_profile", "inspection", "assessment"]}',
        "record_form_template_key": "environmental_cycling",
    },
    {
        "catalog_key": "ISO16750-5_CHEMICAL_RESISTANCE",
        "iso_part": "ISO16750-5",
        "category": "chemical",
        "clause_number": "4.1",
        "test_name": "Chemical Resistance / Chemical Loads",
        "purpose": "Verify resistance to project-defined automotive chemical exposure.",
        "operating_mode": (
            "1.2 (connected to wiring harness, no voltage applied) per ISO 16750-1:2023, Clause "
            "5.2. Operating mode 1.1 with protection seals permitted if agreed."
        ),
        "functional_status": "Post-test functional verification",
        "required_test_level": "Chemical list and exposure TBD",
        "sample_size": "TBD",
        "severity": "TBD",
        "code": "CHEMICAL_LOADS",
        "parameters_json": '{"chemicals": [], "exposure_method": "TBD", "duration": "TBD"}',
        "applicability_rules_json": '{"exposure": "chemical"}',
        "result_input_schema_json": json.dumps([
            {
                "name": "chemical_agent",
                "label": "Chemical Agent",
                "type": "text",
                "required": True,
                "requirement": (
                    'Per ISO 16750-5:2023, Table 3 (e.g. AA = Diesel fuel, AB = "Bio" diesel, '
                    "BA = Engine oil, CC = Antifreeze fluid, CD = Brake fluid, CE = Urea/NOx "
                    "reduction agent). [Specify applicable agent(s) per mounting location]"
                ),
            },
            {
                "name": "application_method",
                "label": "Application Method",
                "type": "select",
                "required": True,
                "options": [
                    "I — Spraying",
                    "II — Wiping",
                    "III — Brushing",
                    "IV — Pouring",
                    "V — Dipping",
                    "VI — Immersing",
                ],
                "requirement": (
                    "Per ISO 16750-5:2023, Table 1 and Table 2 for the applicable mounting "
                    "location: I = Spraying, II = Wiping, III = Brushing, IV = Pouring, V = "
                    "Dipping, VI = Immersing. [Specify applicable method per mounting location "
                    "and agent]"
                ),
            },
            {
                "name": "exposure_duration",
                "label": "Exposure Duration",
                "type": "number",
                "unit": "h",
                "required": True,
                "requirement": (
                    "Per ISO 16750-5:2023, Table 2: 22 h (most agents at Tmax), 10 min (some "
                    "agents at RT), or 2 h (cleaning agents at RT). [Specify applicable "
                    "agent/condition per project spec]"
                ),
            },
            {
                "name": "visual_inspection",
                "label": "Visual Inspection",
                "type": "textarea",
                "required": True,
                "requirement": (
                    "No detrimental corrosion. Marking and labelling shall remain visible and "
                    "legible after the test — per ISO 16750-5:2023, Clause 4.9."
                ),
            },
            {
                "name": "functional_observation",
                "label": "Functional Observation",
                "type": "textarea",
                "required": True,
                "requirement": (
                    "DUT shall maintain minimum functional status Class C per ISO 16750-1:2023, "
                    "Clause 6.4 (ISO 16750-5:2023, Clause 4.9). Pass/fail is determined in the "
                    "Acceptance Criteria / Result table, not by this observation."
                ),
            },
        ]),
        "evaluation_schema_json": json.dumps({
            "rules": [
                {
                    "field": "chemical_agent",
                    "type": "required",
                    "label": "Chemical Agent",
                    "fail_message": "Chemical Agent is required but was not recorded.",
                },
                {
                    "field": "exposure_duration",
                    "type": "min",
                    "min": 1,
                    "label": "Exposure Duration",
                    "unit": "h",
                    "fail_message": (
                        "Recorded exposure duration ({value} h) is shorter than the minimum "
                        "required by ISO 16750-5:2023, Table 2."
                    ),
                },
                {
                    "field": "visual_inspection",
                    "type": "not_equals",
                    "value": "crack",
                    "label": "Visual Inspection",
                    "fail_message": (
                        "Visual Inspection indicates cracking, which does not meet the "
                        "no-detrimental-damage requirement of ISO 16750-5:2023, Clause 4.9."
                    ),
                },
            ]
        }),
        "report_section_schema_json": '{"sections": ["chemical_profile", "inspection", "assessment"]}',
        "record_form_template_key": "chemical_basic",
    },
]


class Database:
    """Thread-safe wrapper around a single SQLite connection."""

    def __init__(self, db_path):
        self.db_path = db_path
        if db_path != ":memory:":
            directory = os.path.dirname(db_path)
            if directory:
                os.makedirs(directory, exist_ok=True)
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._lock = threading.Lock()
        self._init_schema()

    def _init_schema(self):
        with self._lock:
            self._conn.executescript(SCHEMA)
            self._ensure_column("duts", "client_id", "INTEGER REFERENCES clients(id)")
            self._ensure_column("duts", "project_id", "INTEGER REFERENCES projects(id)")
            self._ensure_column("tests", "iso_catalog_id", "INTEGER REFERENCES iso_test_catalog(id)")
            self._ensure_column("tests", "campaign_id", "INTEGER REFERENCES test_campaigns(id)")
            self._ensure_column("tests", "test_plan_item_id", "INTEGER REFERENCES test_plan_items(id)")
            self._ensure_column("tests", "iso_part", "TEXT")
            self._ensure_column("tests", "clause_no", "TEXT")
            self._ensure_column("tests", "operating_mode", "TEXT")
            self._ensure_column("tests", "functional_status", "TEXT")
            self._ensure_column("tests", "required_test_level", "TEXT")
            self._ensure_column("tests", "sample_size", "TEXT")
            self._ensure_column("tests", "selection_reason", "TEXT")
            self._ensure_column("results", "evaluation_status", "TEXT")
            self._ensure_column("results", "evaluation_score", "REAL")
            self._ensure_column("results", "evaluation_details_json", "TEXT")
            self._ensure_column("results", "evaluated_at", "TIMESTAMP")
            self._ensure_column("iso_test_catalog", "evaluation_schema_json", "TEXT DEFAULT '{}'")
            self._ensure_column("test_plan_items", "dut_id", "INTEGER REFERENCES duts(id)")
            self._ensure_column("test_plan_items", "campaign_id", "INTEGER REFERENCES test_campaigns(id)")
            self._ensure_column("test_plan_items", "iso_catalog_id", "INTEGER REFERENCES iso_test_catalog(id)")
            self._ensure_column("test_plan_items", "planned_test_no", "TEXT")
            self._ensure_column("test_plan_items", "iso_part", "TEXT")
            self._ensure_column("test_plan_items", "clause_no", "TEXT")
            self._ensure_column("test_plan_items", "test_name", "TEXT")
            self._ensure_column("test_plan_items", "category", "TEXT")
            self._ensure_column("test_plan_items", "operating_mode", "TEXT")
            self._ensure_column("test_plan_items", "functional_status", "TEXT")
            self._ensure_column("test_plan_items", "required_test_level", "TEXT")
            self._ensure_column("test_plan_items", "severity", "TEXT")
            self._ensure_column("test_plan_items", "sample_size", "TEXT")
            self._ensure_column("test_plan_items", "selection_reason", "TEXT")
            self._ensure_column("test_plan_items", "status", "TEXT DEFAULT 'planned'")
            self._ensure_column("test_plan_items", "sort_order", "INTEGER")
            self._ensure_column("test_plan_items", "updated_at", "TIMESTAMP")
            self._ensure_column("ai_decision_logs", "input_summary", "TEXT")
            self._ensure_column("ai_decision_logs", "catalog_snapshot", "TEXT")
            self._ensure_column("ai_decision_logs", "ai_response", "TEXT")
            self._ensure_column("ai_decision_logs", "selected_tests", "TEXT")
            self._ensure_column("ai_decision_logs", "fallback_used", "INTEGER DEFAULT 0")
            self._ensure_column("test_attachments", "original_filename", "TEXT")
            self._ensure_column("test_attachments", "stored_filename", "TEXT")
            self._ensure_column("test_attachments", "file_size", "INTEGER")
            self._ensure_column("equipment", "equipment_no", "TEXT")
            self._ensure_column("equipment", "kind_of_equipment", "TEXT")
            self._ensure_column("equipment", "model", "TEXT")
            self._ensure_column("equipment", "type", "TEXT")
            self._ensure_column("equipment", "serial_no", "TEXT")
            self._ensure_column("equipment", "last_calibration_date", "TEXT")
            self._ensure_column("equipment", "next_calibration_date", "TEXT")
            self._ensure_column("equipment", "last_verification_date", "TEXT")
            self._ensure_column("equipment", "next_verification_date", "TEXT")
            self._ensure_column("equipment", "using_status", "TEXT")
            self._ensure_column("equipment", "location", "TEXT")
            self._ensure_column("equipment", "updated_at", "TIMESTAMP")
            self._seed_iso_test_catalog()
            self._conn.commit()

    def _ensure_column(self, table, column, definition):
        existing = {
            row["name"]
            for row in self._conn.execute(f"PRAGMA table_info({table})").fetchall()
        }
        if column not in existing:
            self._conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")

    def _seed_iso_test_catalog(self):
        fields = (
            "catalog_key",
            "iso_part",
            "category",
            "clause_number",
            "test_name",
            "purpose",
            "operating_mode",
            "functional_status",
            "required_test_level",
            "sample_size",
            "severity",
            "code",
            "parameters_json",
            "applicability_rules_json",
            "result_input_schema_json",
            "evaluation_schema_json",
            "report_section_schema_json",
            "record_form_template_key",
        )
        placeholders = ", ".join("?" for _ in fields)
        updates = ", ".join(
            f"{field} = excluded.{field}" for field in fields if field != "catalog_key"
        )
        query = f"""
            INSERT INTO iso_test_catalog ({", ".join(fields)})
            VALUES ({placeholders})
            ON CONFLICT(catalog_key) DO UPDATE SET
                {updates},
                updated_at = CURRENT_TIMESTAMP
        """
        for item in ISO_TEST_CATALOG_SEED:
            self._conn.execute(query, tuple(item[field] for field in fields))

    def execute(self, query, params=()):
        """Run an INSERT/UPDATE/DELETE statement and commit."""
        with self._lock:
            cursor = self._conn.execute(query, params)
            self._conn.commit()
            return cursor

    def insert(self, query, params=()):
        """Run an INSERT statement and return the new row id."""
        cursor = self.execute(query, params)
        return cursor.lastrowid

    def query(self, query, params=()):
        """Run a SELECT statement and return a list of dicts."""
        with self._lock:
            cursor = self._conn.execute(query, params)
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def query_one(self, query, params=()):
        """Run a SELECT statement and return a single dict or None."""
        rows = self.query(query, params)
        return rows[0] if rows else None

    def close(self):
        self._conn.close()
