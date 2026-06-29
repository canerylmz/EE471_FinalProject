"""Service handling pre-test checklist generation and PDF export."""

from ..fallbacks import fallback_checklist
from ..ai_backend_client import AIBackendError
from ..prompts import build_checklist_prompt
from ..utils.pdf_export import build_checklist_pdf

REQUIRED_KEYS = ("equipment_calibration", "safety_precautions", "dut_preparation")


class ChecklistService:
    """Generates pre-test checklists and exports them as PDF."""

    def __init__(self, ai_client):
        self.ai_client = ai_client

    def generate_checklist(self, test, dut):
        """Generate a checklist for `test`, returning (checklist, source)."""
        prompt = build_checklist_prompt(test, dut)
        try:
            data = self.ai_client.generate_json(prompt)
            if not isinstance(data, dict) or not all(key in data for key in REQUIRED_KEYS):
                raise ValueError("Ollama response does not contain the expected keys")
            for key in REQUIRED_KEYS:
                if not isinstance(data[key], list):
                    raise ValueError(f"{key} is not a list")
            return data, "ai-backend"
        except (AIBackendError, ValueError):
            return fallback_checklist(test, dut), "fallback"

    def export_pdf(self, checklist_data):
        """Build a checklist PDF and return a BytesIO buffer."""
        return build_checklist_pdf(checklist_data)
