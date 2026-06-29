"""ISO 16750 master catalog endpoints."""

from flask import Blueprint, current_app, request

from ..utils.responses import error, success

bp = Blueprint("catalog", __name__, url_prefix="/api/catalog")


@bp.get("/tests")
def list_tests():
    category = request.args.get("category") or None
    iso_part = request.args.get("iso_part") or None
    tests = current_app.catalog_service.list_tests(category=category, iso_part=iso_part)
    return success({"tests": tests})


@bp.get("/tests/<int:catalog_id>")
def get_test(catalog_id):
    test = current_app.catalog_service.get_test(catalog_id)
    if not test:
        return error("Catalog test not found.", 404)
    return success(test)
