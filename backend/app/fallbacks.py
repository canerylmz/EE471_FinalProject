"""Fallback responses used when the AI backend is unreachable.

These keep the UI functional without a running LLM while preserving English
laboratory wording for all user-facing output.
"""


def fallback_plan(dut):
    """Return a representative ISO 16750 test plan for a DUT."""
    mounting = (dut.get("mounting_location") or "").lower()

    plan = [
        {
            "test_name": "Continuous Operating Voltage",
            "standard_reference": "ISO 16750-2 clause 4.3",
            "category": "Electrical",
            "status": "Mandatory",
            "duration_hours": 4,
            "required_equipment": ["Programmable DC power supply", "Multimeter", "Data logger"],
            "acceptance_criteria": (
                "The DUT shall maintain functional performance within the nominal voltage range."
            ),
            "severity_level": "I",
        },
        {
            "test_name": "Overvoltage",
            "standard_reference": "ISO 16750-2 clause 4.6",
            "category": "Electrical",
            "status": "Mandatory",
            "duration_hours": 1,
            "required_equipment": ["Programmable DC power supply", "Oscilloscope"],
            "acceptance_criteria": (
                "The DUT shall withstand the overvoltage condition without permanent damage."
            ),
            "severity_level": "I",
        },
        {
            "test_name": "Voltage Drop / Reset Behavior",
            "standard_reference": "ISO 16750-2 clause 4.4",
            "category": "Electrical",
            "status": "Mandatory",
            "duration_hours": 2,
            "required_equipment": ["Programmable DC power supply", "Data logger"],
            "acceptance_criteria": (
                "The DUT shall reset in a defined manner or continue operation after the voltage drop."
            ),
            "severity_level": "II",
        },
        {
            "test_name": "Load Dump",
            "standard_reference": "ISO 16750-2 clause 4.6.4",
            "category": "Electrical",
            "status": "Mandatory" if dut.get("nominal_voltage") in ("12V", "24V") else "Optional",
            "duration_hours": 1,
            "required_equipment": ["Load dump simulator", "Oscilloscope"],
            "acceptance_criteria": (
                "The DUT shall not be damaged during or after the alternator load dump pulse."
            ),
            "severity_level": "I",
        },
        {
            "test_name": "High Temperature Endurance",
            "standard_reference": "ISO 16750-4 clause 5.1.1.2",
            "category": "Environmental",
            "status": "Mandatory",
            "duration_hours": 24 if "engine" in mounting else 16,
            "required_equipment": ["Climatic chamber", "Thermocouple", "Data logger"],
            "acceptance_criteria": (
                f"The DUT shall maintain functional performance at {dut.get('temp_max', 85)} C "
                "for the specified duration."
            ),
            "severity_level": "I",
        },
        {
            "test_name": "Low Temperature Operation",
            "standard_reference": "ISO 16750-4 clause 5.1.2.2",
            "category": "Environmental",
            "status": "Mandatory",
            "duration_hours": 4,
            "required_equipment": ["Climatic chamber", "Thermocouple"],
            "acceptance_criteria": (
                f"The DUT shall complete start-up and functional checks at {dut.get('temp_min', -40)} C."
            ),
            "severity_level": "I",
        },
        {
            "test_name": "Thermal Shock",
            "standard_reference": "ISO 16750-4 clause 5.3",
            "category": "Environmental",
            "status": "Mandatory",
            "duration_hours": 12,
            "required_equipment": ["Two-zone climatic chamber", "Thermocouple"],
            "acceptance_criteria": (
                "No mechanical or functional damage shall occur during abrupt temperature changes."
            ),
            "severity_level": "II",
        },
        {
            "test_name": "Damp Heat, Cyclic",
            "standard_reference": "ISO 16750-4 clause 5.6",
            "category": "Environmental",
            "status": (
                "Mandatory" if "exterior" in mounting or "underbody" in mounting else "Optional"
            ),
            "duration_hours": 144,
            "required_equipment": ["Humidity controlled climatic chamber", "Data logger"],
            "acceptance_criteria": (
                "Insulation resistance and DUT function shall remain acceptable after humidity cycling."
            ),
            "severity_level": "II",
        },
        {
            "test_name": "IP Code Verification",
            "standard_reference": "ISO 16750-1 clause 5",
            "category": "Environmental",
            "status": (
                "Mandatory" if "exterior" in mounting or "underbody" in mounting else "Optional"
            ),
            "duration_hours": 2,
            "required_equipment": ["Water spray test setup", "Dust chamber"],
            "acceptance_criteria": (
                f"The DUT shall meet the declared {dut.get('ip_class', 'IP')} protection class."
            ),
            "severity_level": "I",
        },
        {
            "test_name": "Chemical Resistance",
            "standard_reference": "ISO 16750-5 clause 4.2",
            "category": "Chemical",
            "status": (
                "Mandatory" if "underbody" in mounting or "engine" in mounting else "Optional"
            ),
            "duration_hours": 24,
            "required_equipment": ["Chemical exposure setup", "Test fluid set"],
            "acceptance_criteria": (
                "No cracking, deformation, or functional impairment shall be observed after exposure."
            ),
            "severity_level": "II",
        },
        {
            "test_name": "Salt Spray / Mist",
            "standard_reference": "ISO 16750-5 clause 4.3",
            "category": "Chemical",
            "status": (
                "Mandatory" if "underbody" in mounting or "exterior" in mounting else "Optional"
            ),
            "duration_hours": 96,
            "required_equipment": ["Salt mist chamber"],
            "acceptance_criteria": (
                "Corrosion shall not impair connector function or electrical performance."
            ),
            "severity_level": "III",
        },
        {
            "test_name": "Vibration",
            "standard_reference": "ISO 16750-3 clause 4.1",
            "category": "Mechanical",
            "status": "Mandatory" if "engine" in mounting else "Optional",
            "duration_hours": 8,
            "required_equipment": ["Vibration table", "Accelerometer"],
            "acceptance_criteria": (
                "Electrical continuity shall be maintained during and after the vibration profile."
            ),
            "severity_level": "II",
        },
    ]

    return plan


def fallback_checklist(test, dut):
    """Return a representative checklist for a given test."""
    equipment = test.get("required_equipment") or []
    if isinstance(equipment, str):
        equipment = [e.strip() for e in equipment.split(",") if e.strip()]

    equipment_calibration = [
        f"Verify the calibration certificate validity for {item}." for item in equipment
    ] or ["Verify the calibration status of all test equipment."]
    equipment_calibration.append("Zero the data logger channels and take a reference reading.")

    safety_precautions = [
        "Wear the required personal protective equipment.",
        "Verify that the emergency stop button is accessible in the test area.",
        "Confirm that high-voltage and high-temperature warning labels are visible.",
        "Confirm that test room ventilation is operating.",
    ]

    dut_preparation = [
        f"Record the serial number and software version of {dut['name']}.",
        "Install the DUT in the test setup according to manufacturer instructions.",
        "Verify that all connector interfaces are secure.",
        f"Inspect the DUT visually for damage before the {test['test_name']} test.",
        "Perform the pre-test reference functional check.",
    ]

    return {
        "equipment_calibration": equipment_calibration,
        "safety_precautions": safety_precautions,
        "dut_preparation": dut_preparation,
    }


def fallback_report(dut, test, result_data):
    """Return a representative formal report when the LLM is unavailable."""
    measured_values = result_data.get("measured_values", {})
    conditions = result_data.get("test_conditions", {}) or {}
    result = result_data.get("result", "NOT EVALUATED")
    has_deviation = bool(result_data.get("has_deviation"))

    measured_str = ", ".join(f"{k}: {v}" for k, v in measured_values.items()) or "Not specified"

    sections = {
        "test_amaci": (
            f"The purpose of this report is to document the {test['test_name']} test performed "
            f"on {dut['name']} ({dut.get('part_number', '')}) according to "
            f"{test['standard_reference']} and to record the conformity assessment."
        ),
        "test_kosullari": (
            f"The test was performed at {conditions.get('temperature', 'not specified')} C, "
            f"{conditions.get('humidity', 'not specified')} % relative humidity."
        ),
        "olcum_sonuclari": f"Recorded measured or applied values: {measured_str}.",
        "gozlemler": (
            result_data.get("observations")
            or "No special observation was recorded during the test."
        ),
        "kabul_degerlendirme": (
            f"The recorded values were compared with the acceptance criteria defined for "
            f"{test['standard_reference']}. The assessment result is {result}."
        ),
        "sonuc": (
            f"The final laboratory assessment for {test['test_name']} is {result}. "
            "This conclusion is supported by the recorded test data and observations."
        ),
    }

    if has_deviation:
        sections["sapma_analizi"] = (
            f"Applied test parameter deviation: {result_data.get('deviation_description', 'not specified')}. "
            f"Reason for applied difference: {result_data.get('root_cause', 'not specified')}. "
            f"Approval/technical note: {result_data.get('corrective_action', 'not specified')}."
        )

    return {"sections": sections}
