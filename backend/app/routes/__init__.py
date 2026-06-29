"""Blueprint registration for the TestForge API."""

from .dut_routes import bp as dut_bp
from .catalog_routes import bp as catalog_bp
from .plan_routes import bp as plan_bp
from .checklist_routes import bp as checklist_bp
from .result_routes import bp as result_bp
from .report_routes import bp as report_bp
from .record_form_routes import bp as record_form_bp
from .technical_report_routes import bp as technical_report_bp
from .dashboard_routes import bp as dashboard_bp
from .attachment_routes import bp as attachment_bp
from .equipment_routes import bp as equipment_bp
from .demo_routes import bp as demo_bp


def register_routes(app):
    """Register all API blueprints on the Flask app."""
    app.register_blueprint(catalog_bp)
    app.register_blueprint(dut_bp)
    app.register_blueprint(plan_bp)
    app.register_blueprint(checklist_bp)
    app.register_blueprint(result_bp)
    app.register_blueprint(report_bp)
    app.register_blueprint(record_form_bp)
    app.register_blueprint(technical_report_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(attachment_bp)
    app.register_blueprint(equipment_bp)
    app.register_blueprint(demo_bp)
