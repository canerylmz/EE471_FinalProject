"""Flask application factory for TestForge."""

from flask import Flask
from flask_cors import CORS

from .ai_backend_client import AIBackendClient
from .config import Config
from .database import Database
from .services import (
    CatalogService,
    AttachmentService,
    ChecklistService,
    DemoSeedService,
    DUTService,
    EvaluationService,
    EquipmentService,
    PlanService,
    ReportService,
    TestRecordFormService,
    TechnicalReportService,
)


def create_app(config_class=Config):
    """Create and configure the Flask application."""
    app = Flask(__name__)
    app.config.from_object(config_class)

    CORS(app, resources={r"/api/*": {"origins": "*"}})

    db = Database(app.config["DATABASE_PATH"])
    ai_backend = AIBackendClient(
        app.config["AI_BACKEND_URL"],
        app.config["AI_BACKEND_TIMEOUT"],
    )

    app.db = db
    app.catalog_service = CatalogService(db)
    app.attachment_service = AttachmentService(
        db,
        app.config["UPLOAD_DIR"],
        app.config["MAX_ATTACHMENT_SIZE"],
    )
    app.evaluation_service = EvaluationService(db, ai_backend)
    app.equipment_service = EquipmentService(db)
    app.demo_seed_service = DemoSeedService(db, app.config["UPLOAD_DIR"], app.evaluation_service)
    app.test_record_form_service = TestRecordFormService()
    app.technical_report_service = TechnicalReportService(
        app.config["ORGANIZATION_NAME"],
        app.config["ORGANIZATION_ADDRESS"],
    )
    app.dut_service = DUTService(db)
    app.plan_service = PlanService(db, ai_backend)
    app.checklist_service = ChecklistService(ai_backend)
    app.report_service = ReportService(db, ai_backend)

    from .routes import register_routes

    register_routes(app)

    @app.get("/api/health")
    def health():
        return {"success": True, "data": {"status": "ok"}}

    return app
