"""Attachment upload, listing, download, and deletion endpoints."""

from pathlib import Path

from flask import Blueprint, current_app, request, send_file

from ..utils.responses import error, success

bp = Blueprint("attachments", __name__, url_prefix="/api/attachments")


@bp.post("/upload")
def upload_attachment():
    file_storage = request.files.get("file")
    try:
        attachment = current_app.attachment_service.upload(file_storage, request.form)
    except ValueError as exc:
        return error(str(exc), 400)
    return success(attachment, 201)


@bp.get("/test/<int:test_id>")
def list_test_attachments(test_id):
    attachments = current_app.attachment_service.list_for_test(test_id)
    return success({"attachments": attachments})


@bp.get("/dut/<int:dut_id>")
def list_dut_attachments(dut_id):
    attachments = current_app.attachment_service.list_for_dut(dut_id)
    return success({"attachments": attachments})


@bp.get("/download/<int:attachment_id>")
def download_attachment(attachment_id):
    attachment = current_app.attachment_service.get(attachment_id)
    if not attachment:
        return error("Attachment not found.", 404)
    file_path = Path(attachment.get("file_path") or "")
    if not file_path.exists():
        return error("Stored file was not found.", 404)
    return send_file(
        file_path,
        as_attachment=True,
        download_name=attachment.get("original_filename") or attachment.get("file_name"),
        mimetype=attachment.get("mime_type") or "application/octet-stream",
    )


@bp.delete("/<int:attachment_id>")
def delete_attachment(attachment_id):
    attachment = current_app.attachment_service.delete(attachment_id)
    if not attachment:
        return error("Attachment not found.", 404)
    return success({"deleted": True, "attachment_id": attachment_id})
