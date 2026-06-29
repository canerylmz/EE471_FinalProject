"""Prompt templates sent to the AI backend."""


def build_plan_prompt(dut, catalog_summary=None):
    """Build the catalog-aware test plan generation prompt for a DUT record."""
    catalog_text = "No catalog entries are available."
    if catalog_summary:
        catalog_lines = []
        for item in catalog_summary:
            catalog_lines.append(
                "- id={id}; {iso_part} clause {clause_no}; {test_name}; "
                "category={category}; operating_mode={operating_mode}; "
                "functional_status={functional_status}; level={required_test_level}; "
                "severity={severity}; applicability={applicability_rules}".format(
                    id=item.get("id"),
                    iso_part=item.get("iso_part", ""),
                    clause_no=item.get("clause_no", ""),
                    test_name=item.get("test_name", ""),
                    category=item.get("category", ""),
                    operating_mode=item.get("operating_mode", ""),
                    functional_status=item.get("functional_status", ""),
                    required_test_level=item.get("required_test_level", ""),
                    severity=item.get("severity", ""),
                    applicability_rules=item.get("applicability_rules", {}),
                )
            )
        catalog_text = "\n".join(catalog_lines)

    return f"""You are an automotive electronics test engineer expert in ISO 16750.
DUT Information:
- Name: {dut['name']}
- Mounting Location: {dut['mounting_location']}
- Nominal Voltage: {dut['nominal_voltage']}
- Power Class: {dut['power_class']}
- Operating Temperature: {dut['temp_min']} C to {dut['temp_max']} C
- IP Class: {dut['ip_class']}

Use the project catalog summary below as the source of selectable ISO 16750 test metadata.
Do not reproduce copyrighted standard text. Select applicable tests using only the short metadata.
Prefer the catalog test names and clause numbers exactly as written when applicable.

Catalog summary:
{catalog_text}

Based on the DUT and catalog summary, generate an applicable ISO 16750 test plan.
For each selected test provide:
- test_name
- iso_part (e.g. "ISO16750-2")
- clause_no
- category (electrical / environmental / chemical / general)
- operating_mode
- functional_status
- required_test_level
- severity
- sample_size
- reason

Consider mounting location carefully:
- Engine compartment -> wider temperature range, higher vibration, chemical exposure
- Passenger compartment -> moderate temperature, lower chemical exposure
- Exterior -> IP rating critical, UV/moisture exposure
- Underbody -> chemical loads (ISO 16750-5) very important

Respond ONLY with a valid JSON array. No explanation, no markdown."""


def build_checklist_prompt(test, dut):
    """Build the pre-test checklist generation prompt."""
    equipment = test.get("required_equipment") or []
    if isinstance(equipment, list):
        equipment_str = ", ".join(equipment)
    else:
        equipment_str = str(equipment)

    return f"""You are an automotive test lab engineer.
Generate a pre-test checklist for the following test:

Test Name: {test['test_name']}
Standard Reference: {test['standard_reference']}
Required Equipment: {equipment_str}
DUT: {dut['name']}
Acceptance Criteria: {test['acceptance_criteria']}

Return a JSON object with three arrays:
{{
"equipment_calibration": ["item1", "item2", ...],
"safety_precautions": ["item1", "item2", ...],
"dut_preparation": ["item1", "item2", ...]
}}
Each item should be a specific, actionable instruction.
Respond ONLY with valid JSON. No explanation, no markdown."""


def build_report_prompt(dut, test, result_data):
    """Build the formal test report generation prompt."""
    measured_values = result_data.get("measured_values", {})
    conditions = result_data.get("test_conditions", {}) or {}
    has_deviation = bool(result_data.get("has_deviation"))

    if has_deviation:
        deviation_info = (
            "Applied test parameter deviation recorded. Description: {desc}. "
            "Reason for applied difference: {root}. Approval/technical note: {corrective}."
        ).format(
            desc=result_data.get("deviation_description", ""),
            root=result_data.get("root_cause", ""),
            corrective=result_data.get("corrective_action", ""),
        )
        deviation_section = "\n7. Deviation Analysis and Corrective Action"
        sections_json_extra = '\n"sapma_analizi": "..."'
    else:
        deviation_info = "No deviation recorded."
        deviation_section = ""
        sections_json_extra = ""

    return f"""You are a technical report writer for automotive electronics testing.
Write a formal automotive laboratory test report in English using the following data.
Use concise, formal laboratory wording. Do not write a student-style essay.
Do not include Turkish headings, Turkish explanations, or copyrighted standard text.
DUT: {dut['name']} ({dut.get('part_number', '')})
Test: {test['test_name']} per {test['standard_reference']}
Result: {result_data.get('result')}
Measured Values: {measured_values}
Test Conditions: Temperature {conditions.get('temperature')} C, Humidity {conditions.get('humidity')}%
Observations: {result_data.get('observations', '')}
Deviation: {deviation_info}
Write the following sections in formal English technical language:
1. Test Purpose
2. Test Conditions
3. Measurement Results
4. Observations
5. Acceptance Criteria Evaluation
6. Result and Decision{deviation_section}

Respond with a JSON object:
{{
"sections": {{
"test_amaci": "...",
"test_kosullari": "...",
"olcum_sonuclari": "...",
"gozlemler": "...",
"kabul_degerlendirme": "...",
"sonuc": "..."{sections_json_extra}
}}
}}
Respond ONLY with valid JSON. No explanation, no markdown."""
