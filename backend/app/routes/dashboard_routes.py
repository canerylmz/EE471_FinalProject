"""Campaign dashboard summary endpoint."""

from flask import Blueprint, current_app

from ..utils.responses import success

bp = Blueprint("dashboard", __name__, url_prefix="/api/dashboard")


def _result_status(result):
    if not result:
        return "Pending"
    value = (result.get("result") or "").strip()
    if value in ("Pass", "Fail"):
        return value
    if value:
        return "Conditional Pass"
    return "Pending"


@bp.get("/summary")
def summary():
    duts = current_app.dut_service.list_all()

    total_tests = 0
    pass_count = 0
    fail_count = 0
    conditional_count = 0
    pending_count = 0

    dut_rows = []
    for dut in duts:
        tests = current_app.plan_service.get_tests_for_dut(dut["id"])
        test_rows = []
        for test in tests:
            result = current_app.report_service.get_latest_result_for_test(test["id"])
            status = _result_status(result)

            total_tests += 1
            if status == "Pass":
                pass_count += 1
            elif status == "Fail":
                fail_count += 1
            elif status == "Conditional Pass":
                conditional_count += 1
            else:
                pending_count += 1

            test_rows.append(
                {
                    "id": test["id"],
                    "test_name": test["test_name"],
                    "category": test["category"],
                    "status": test["status"],
                    "severity_level": test["severity_level"],
                    "result_status": status,
                }
            )

        dut_rows.append(
            {
                "id": dut["id"],
                "name": dut["name"],
                "manufacturer": dut["manufacturer"],
                "customer": dut["customer"],
                "project": dut["project"],
                "mounting_location": dut["mounting_location"],
                "nominal_voltage": dut["nominal_voltage"],
                "power_class": dut["power_class"],
                "test_count": len(tests),
                "tests": test_rows,
            }
        )

    pass_rate = round((pass_count / total_tests) * 100, 1) if total_tests else 0.0

    return success(
        {
            "summary": {
                "total_duts": len(duts),
                "total_tests": total_tests,
                "pass_rate": pass_rate,
                "pending_tests": pending_count,
                "pass_count": pass_count,
                "fail_count": fail_count,
                "conditional_count": conditional_count,
            },
            "duts": dut_rows,
        }
    )


@bp.get("/overview")
def overview():
    db = current_app.db
    duts = current_app.dut_service.list_all()
    tests = db.query(
        """
        SELECT t.*, d.name AS dut_name, d.customer, d.project
        FROM tests t
        LEFT JOIN duts d ON d.id = t.dut_id
        ORDER BY t.id DESC
        """
    )
    plan_items = db.query("SELECT * FROM test_plan_items ORDER BY id DESC")
    attachments_count = _count("test_attachments")
    linked_equipment_count = _count("test_equipment")
    equipment_items = current_app.equipment_service.list_all()

    tests_by_category = _zero_counts(("electrical", "environmental", "chemical"))
    tests_by_status = _zero_counts(("planned", "approved", "in_progress", "completed", "cancelled"))
    results_by_evaluation_status = _zero_counts(("PASS", "FAIL", "CONDITIONAL PASS", "NOT EVALUATED"))
    equipment_calibration_summary = _zero_counts(("valid", "due_soon", "expired", "not_available"))

    latest_results_by_test = {}
    completed_results = 0
    evaluation_completed = 0
    recent_results = []
    failed_tests = []
    tests_without_results = []

    for item in equipment_items:
        status = item.get("calibration_status") or "not_available"
        equipment_calibration_summary[status] = equipment_calibration_summary.get(status, 0) + 1

    for test in tests:
        category = (test.get("category") or "uncategorized").lower()
        if category in tests_by_category:
            tests_by_category[category] += 1

        plan_status = (test.get("plan_item_status") or test.get("status") or "planned").lower()
        if test.get("test_plan_item_id"):
            plan_item = next((item for item in plan_items if item["id"] == test.get("test_plan_item_id")), None)
            if plan_item:
                plan_status = (plan_item.get("status") or "planned").lower()
        if plan_status in tests_by_status:
            tests_by_status[plan_status] += 1

        result = current_app.report_service.get_latest_result_for_test(test["id"])
        latest_results_by_test[test["id"]] = result
        if result:
            completed_results += 1
            evaluation_status = result.get("evaluation_status") or "NOT EVALUATED"
            if evaluation_status in results_by_evaluation_status:
                results_by_evaluation_status[evaluation_status] += 1
            else:
                results_by_evaluation_status["NOT EVALUATED"] += 1
            if evaluation_status != "NOT EVALUATED":
                evaluation_completed += 1
            if evaluation_status == "FAIL":
                failed_tests.append(_attention_test(test, result))
        else:
            results_by_evaluation_status["NOT EVALUATED"] += 1
            tests_without_results.append(_attention_test(test, None))

    recent_results = _recent_results()
    expired_linked_equipment = _linked_equipment_by_status("expired")
    due_soon_equipment = [
        {
            "id": item["id"],
            "equipment_no": item.get("equipment_no"),
            "kind_of_equipment": item.get("kind_of_equipment"),
            "next_calibration_date": item.get("next_calibration_date"),
            "calibration_status": item.get("calibration_status"),
        }
        for item in equipment_items
        if item.get("calibration_status") == "due_soon"
    ]

    return success(
        {
            "summary": {
                "total_duts": len(duts),
                "total_test_plans": len(plan_items),
                "total_plan_items": len(plan_items),
                "total_tests": len(tests),
                "completed_results": completed_results,
                "attachments": attachments_count,
                "linked_equipment_items": linked_equipment_count,
                "pass": results_by_evaluation_status["PASS"],
                "fail": results_by_evaluation_status["FAIL"],
                "conditional_pass": results_by_evaluation_status["CONDITIONAL PASS"],
                "not_evaluated": results_by_evaluation_status["NOT EVALUATED"],
            },
            "tests_by_category": tests_by_category,
            "tests_by_status": tests_by_status,
            "results_by_evaluation_status": results_by_evaluation_status,
            "equipment_calibration_summary": equipment_calibration_summary,
            "workflow_progress": {
                "dut_registered": len(duts),
                "test_plan_generated": len(plan_items),
                "results_entered": completed_results,
                "evaluation_completed": evaluation_completed,
                "record_forms_available": "Available on demand",
                "technical_reports_available": "Available on demand",
            },
            "recent_duts": _recent_duts(duts),
            "recent_test_results": recent_results,
            "attention_required": {
                "failed_tests": failed_tests[:10],
                "tests_without_results": tests_without_results[:10],
                "expired_equipment": expired_linked_equipment[:10],
                "due_soon_equipment": due_soon_equipment[:10],
            },
        }
    )


def _count(table):
    row = current_app.db.query_one(f"SELECT COUNT(*) AS count FROM {table}")
    return row["count"] if row else 0


def _zero_counts(keys):
    return {key: 0 for key in keys}


def _recent_duts(duts):
    sorted_duts = sorted(duts, key=lambda item: item.get("created_at") or "", reverse=True)
    return [
        {
            "id": dut["id"],
            "name": dut.get("name"),
            "manufacturer": dut.get("manufacturer"),
            "customer": dut.get("customer"),
            "project": dut.get("project"),
            "created_at": dut.get("created_at"),
        }
        for dut in sorted_duts[:5]
    ]


def _recent_results():
    rows = current_app.db.query(
        """
        SELECT r.id, r.test_id, r.dut_id, r.result, r.evaluation_status, r.evaluation_score,
               r.created_at, t.test_name, t.category, d.name AS dut_name
        FROM results r
        LEFT JOIN tests t ON t.id = r.test_id
        LEFT JOIN duts d ON d.id = r.dut_id
        ORDER BY r.created_at DESC, r.id DESC
        LIMIT 5
        """
    )
    return [
        {
            "id": row["id"],
            "test_id": row["test_id"],
            "dut_id": row["dut_id"],
            "dut_name": row.get("dut_name"),
            "test_name": row.get("test_name"),
            "category": row.get("category"),
            "evaluation_status": row.get("evaluation_status") or "NOT EVALUATED",
            "evaluation_score": row.get("evaluation_score"),
            "created_at": row.get("created_at"),
        }
        for row in rows
    ]


def _attention_test(test, result):
    return {
        "test_id": test["id"],
        "dut_id": test.get("dut_id"),
        "dut_name": test.get("dut_name"),
        "test_name": test.get("test_name"),
        "category": test.get("category"),
        "evaluation_status": (result or {}).get("evaluation_status") or "NOT EVALUATED",
    }


def _linked_equipment_by_status(expected_status):
    rows = current_app.db.query(
        """
        SELECT te.id AS link_id, te.test_id, te.usage_role, e.*, t.test_name, t.dut_id,
               d.name AS dut_name
        FROM test_equipment te
        JOIN equipment e ON e.id = te.equipment_id
        JOIN tests t ON t.id = te.test_id
        LEFT JOIN duts d ON d.id = t.dut_id
        LEFT JOIN test_plan_items tpi ON tpi.id = t.test_plan_item_id
        WHERE COALESCE(tpi.status, 'planned') NOT IN ('completed', 'cancelled')
        ORDER BY te.id DESC
        """
    )
    items = []
    for row in rows:
        status = current_app.equipment_service.calibration_status(row.get("next_calibration_date"))
        if status != expected_status:
            continue
        items.append(
            {
                "link_id": row["link_id"],
                "equipment_id": row["id"],
                "equipment_no": row.get("equipment_no"),
                "kind_of_equipment": row.get("kind_of_equipment"),
                "next_calibration_date": row.get("next_calibration_date"),
                "calibration_status": status,
                "test_id": row.get("test_id"),
                "test_name": row.get("test_name"),
                "dut_id": row.get("dut_id"),
                "dut_name": row.get("dut_name"),
            }
        )
    return items
