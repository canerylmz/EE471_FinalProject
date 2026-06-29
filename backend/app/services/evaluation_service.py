"""Automatic pass/fail evaluation for measured test results."""

import json
import re
from datetime import datetime, timezone

from ..ai_backend_client import AIBackendError


STATUS_PASS = "PASS"
STATUS_FAIL = "FAIL"
STATUS_CONDITIONAL = "CONDITIONAL PASS"
STATUS_NOT_EVALUATED = "NOT EVALUATED"

# Phrases where the negation/failure meaning is built into the phrase itself
# (e.g. "does not work" / "çalışmıyor") - flagged unconditionally, never
# suppressed by a nearby negation word.
_UNAMBIGUOUS_FAILURE_PHRASES = (
    "does not work", "doesn't work", "did not work", "didn't work", "not working",
    "not functional", "non-functional", "nonfunctional", "out of order",
    "stopped working", "failed to operate", "failed to function", "no longer responds",
    "çalışmıyor", "calismiyor", "çalışmadı", "calismadi", "çalışmaz", "calismaz",
    "çalışmıyordu", "calismiyordu", "tepki vermiyor", "yanıt vermiyor", "yanit vermiyor",
)

# Single ambiguous words that usually indicate a deviation, but can be
# legitimately negated in a passing observation ("no reset observed",
# "korozyon yok"). These are only flagged if no negation word appears nearby.
_AMBIGUOUS_FAILURE_WORDS = (
    "fail", "failed", "failure", "malfunction", "broken", "break", "crash", "crashed",
    "unresponsive", "reset", "restart", "rebooted", "reboot", "shutdown", "flicker",
    "flickered", "dropped", "drop", "deviation", "abnormal", "anomaly", "error", "fault",
    "defect", "damage", "damaged", "crack", "cracked", "corrosion", "corroded", "leak",
    "leaking", "burnt", "burning", "smoke", "overheat", "overheated",
    "arıza", "ariza", "arızalı", "arizali", "bozuk", "bozuldu", "hata", "hatalı", "hatali",
    "başarısız", "basarisiz", "kesildi", "durdu", "sıfırlandı", "sifirlandi", "resetlendi",
    "yandı", "yandi", "kırık", "kirik", "çatlak", "catlak", "sızıntı", "sizinti",
    "korozyon", "anormal", "sapma", "duman",
)

_NEGATION_TOKENS = {
    "no", "not", "without", "never", "non", "didn't", "doesn't", "wasn't", "weren't",
    "yok", "değil", "degil", "hiç", "hiçbir", "hicbir",
}


class EvaluationService:
    """Evaluates measured values against catalog-defined rules and reviews
    free-text functional observations for failure language."""

    def __init__(self, db, ai_client=None):
        self.db = db
        self.ai_client = ai_client

    def evaluate(self, test, measured_values):
        """Return evaluation status, score, failed rules, and details."""
        schema = self._evaluation_schema_for_test(test)
        rules = schema.get("rules", []) if isinstance(schema, dict) else []
        values = measured_values or {}

        details = []
        failed_rules = []

        rule_fields = {rule.get("field") for rule in rules if rule.get("field")}
        apply_rules = bool(rules) and (not values or any(field in values for field in rule_fields))
        if apply_rules:
            for rule in rules:
                detail = self._evaluate_rule(rule, values)
                details.append(detail)
                if not detail["passed"]:
                    failed_rules.append(detail)

        functional_detail = self._evaluate_functional_observation(test, values)
        if functional_detail:
            details.append(functional_detail)
            if not functional_detail["passed"]:
                failed_rules.append(functional_detail)

        if not details:
            return {
                "status": STATUS_NOT_EVALUATED,
                "score": None,
                "failed_rules": [],
                "evaluation_details": [],
            }

        passed_count = len(details) - len(failed_rules)
        score = round((passed_count / len(details)) * 100, 1) if details else None
        if not failed_rules:
            status = STATUS_PASS
        elif score and score >= 80:
            status = STATUS_CONDITIONAL
        else:
            status = STATUS_FAIL

        return {
            "status": status,
            "score": score,
            "failed_rules": failed_rules,
            "evaluation_details": details,
        }

    def evaluate_by_test_id(self, test_id, measured_values):
        """Resolve a test and evaluate values."""
        test = self.db.query_one("SELECT * FROM tests WHERE id = ?", (test_id,))
        if not test:
            return None
        return self.evaluate(test, measured_values)

    def save_evaluation(self, result_id, evaluation):
        """Persist evaluation output on a result row."""
        self.db.execute(
            """
            UPDATE results
            SET evaluation_status = ?,
                evaluation_score = ?,
                evaluation_details_json = ?,
                evaluated_at = ?
            WHERE id = ?
            """,
            (
                evaluation.get("status"),
                evaluation.get("score"),
                json.dumps(evaluation),
                datetime.now(timezone.utc).isoformat(timespec="seconds"),
                result_id,
            ),
        )

    def _evaluation_schema_for_test(self, test):
        if not test.get("iso_catalog_id"):
            return {}
        row = self.db.query_one(
            "SELECT evaluation_schema_json FROM iso_test_catalog WHERE id = ?",
            (test["iso_catalog_id"],),
        )
        if not row:
            return {}
        try:
            parsed = json.loads(row.get("evaluation_schema_json") or "{}")
        except (TypeError, ValueError):
            return {}
        return parsed if isinstance(parsed, dict) else {}

    def _evaluate_rule(self, rule, values):
        rule_type = rule.get("type")
        field = rule.get("field")
        value = values.get(field)
        passed = False

        if rule_type == "required":
            passed = not self._is_blank(value)
        elif rule_type == "range":
            number = self._to_number(value)
            passed = number is not None and rule.get("min") <= number <= rule.get("max")
        elif rule_type == "min":
            number = self._to_number(value)
            passed = number is not None and number >= rule.get("min")
        elif rule_type == "max":
            number = self._to_number(value)
            passed = number is not None and number <= rule.get("max")
        elif rule_type == "equals":
            passed = self._normalize(value) == self._normalize(rule.get("value"))
        elif rule_type == "not_equals":
            passed = self._normalize(value) != self._normalize(rule.get("value"))
        elif rule_type == "contains":
            passed = self._normalize(rule.get("value")) in self._normalize(value)

        return {
            "field": field,
            "type": rule_type,
            "expected": self._expected(rule),
            "actual": value,
            "passed": passed,
            "message": self._message(rule, value, passed),
        }

    @staticmethod
    def _expected(rule):
        rule_type = rule.get("type")
        if rule_type == "range":
            return {"min": rule.get("min"), "max": rule.get("max")}
        if rule_type in ("min", "max"):
            return {rule_type: rule.get(rule_type)}
        if rule_type in ("equals", "not_equals", "contains"):
            return rule.get("value")
        if rule_type == "required":
            return "required"
        return None

    @staticmethod
    def _message(rule, value, passed):
        """Build a human-readable, non-technical evaluation message.

        Never surfaces the raw internal field key; uses the catalog-provided
        "label" (falling back to the field key only if no label was set) and an
        optional rule-specific "fail_message"/"pass_message" template.
        """
        label = rule.get("label") or rule.get("field")
        unit = f" {rule.get('unit')}" if rule.get("unit") else ""
        template = rule.get("pass_message") if passed else rule.get("fail_message")
        if template:
            try:
                return template.format(
                    value=value,
                    min=rule.get("min"),
                    max=rule.get("max"),
                    expected=rule.get("value"),
                    label=label,
                )
            except (KeyError, IndexError):
                pass
        if passed:
            return f"{label} met the requirement."
        rule_type = rule.get("type")
        if rule_type == "min":
            return f"{label} ({value}{unit}) is below the required minimum ({rule.get('min')}{unit})."
        if rule_type == "max":
            return f"{label} ({value}{unit}) exceeds the required maximum ({rule.get('max')}{unit})."
        if rule_type == "range":
            return f"{label} ({value}{unit}) is outside the required range ({rule.get('min')}{unit} to {rule.get('max')}{unit})."
        if rule_type == "required":
            return f"{label} is required but was not recorded."
        return f"{label} did not meet the requirement (recorded value: {value})."

    def _evaluate_functional_observation(self, test, values):
        """Review the free-text functional observation for failure language.

        This never relies on a brittle "contains 'normal'" string match. It
        asks the configured AI service to judge whether the observation
        describes the DUT meeting its required functional status; if the AI
        service is unavailable or returns something unusable, it falls back
        to a negation-aware keyword scan (English and Turkish).
        """
        observation = values.get("functional_observation")
        if self._is_blank(observation):
            return None

        observation = str(observation)
        required_class = test.get("functional_status") or "the required functional status"
        passed, message, source = self._assess_observation(observation, required_class)

        return {
            "field": "functional_observation",
            "type": "functional_status_review",
            "expected": required_class,
            "actual": observation,
            "passed": passed,
            "message": message,
            "source": source,
        }

    def _assess_observation(self, observation, required_class):
        if self.ai_client:
            try:
                passed, message = self._assess_with_ai(observation, required_class)
                return passed, message, "ai"
            except (AIBackendError, ValueError, TypeError, KeyError):
                pass
        passed, message = self._assess_with_keywords(observation, required_class)
        return passed, message, "keyword-fallback"

    def _assess_with_ai(self, observation, required_class):
        prompt = (
            "You are a laboratory test engineer assessing an automotive component test "
            "observation against ISO 16750-1:2023 functional status classes.\n"
            f'Required functional status: "{required_class}".\n'
            f'Technician observation (English or Turkish): "{observation}"\n'
            "Decide whether the observation shows the DUT meeting the required functional "
            "status (function performed as designed, no unwanted operation) or shows a "
            "functional deviation/failure (for example: the sample did not work, reset, "
            "stopped responding, displayed a fault, was damaged, or otherwise failed to "
            "perform as designed).\n"
            "Respond ONLY with valid JSON in this exact shape, no markdown, no explanation "
            'outside the JSON: {"meets_requirement": true or false, "reason": "one short '
            'sentence in English"}'
        )
        result = self.ai_client.generate_json(prompt)
        if not isinstance(result, dict) or "meets_requirement" not in result:
            raise ValueError("AI response is missing 'meets_requirement'.")
        passed = bool(result["meets_requirement"])
        reason = str(result.get("reason") or "").strip()
        if passed:
            return True, reason or "Functional Observation meets the required functional status."
        return False, reason or (
            f"Functional Observation indicates a deviation from the required functional "
            f"status ({required_class})."
        )

    @staticmethod
    def _assess_with_keywords(observation, required_class):
        text = observation.lower()
        for phrase in _UNAMBIGUOUS_FAILURE_PHRASES:
            if phrase in text:
                return False, (
                    f'Functional Observation ("{observation.strip()}") indicates the DUT did '
                    f"not meet the required functional status ({required_class})."
                )

        tokens = re.findall(r"[^\W\d_]+", text, flags=re.UNICODE)
        for index, token in enumerate(tokens):
            if token in _AMBIGUOUS_FAILURE_WORDS and not EvaluationService._has_nearby_negation(tokens, index):
                return False, (
                    f'Functional Observation ("{observation.strip()}") indicates a possible '
                    f"deviation from the required functional status ({required_class}); "
                    "manual review recommended."
                )

        return True, "Functional Observation does not indicate a deviation from the required functional status."

    @staticmethod
    def _has_nearby_negation(tokens, index, window=4):
        start = max(0, index - window)
        end = min(len(tokens), index + window + 1)
        for i in range(start, end):
            if i != index and tokens[i] in _NEGATION_TOKENS:
                return True
        return False

    @staticmethod
    def _is_blank(value):
        return value is None or value == ""

    @staticmethod
    def _to_number(value):
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _normalize(value):
        return str(value or "").strip().lower()
