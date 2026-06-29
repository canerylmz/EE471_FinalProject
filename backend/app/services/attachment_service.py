"""Attachment upload, listing, download, and deletion service."""

import os
import uuid
from pathlib import Path

from werkzeug.utils import secure_filename


ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "pdf", "docx", "xlsx", "csv", "txt"}
ALLOWED_TYPES = {
    "test_photo",
    "measurement_file",
    "temperature_humidity_log",
    "calibration_certificate",
    "raw_data",
    "test_record_form",
    "supporting_document",
}


class AttachmentService:
    """Manages local supporting-file storage for DUT/test/result records."""

    def __init__(self, db, upload_dir, max_file_size):
        self.db = db
        self.upload_dir = Path(upload_dir)
        self.max_file_size = max_file_size
        self.upload_dir.mkdir(parents=True, exist_ok=True)

    def upload(self, file_storage, data):
        """Validate and persist an uploaded file and its metadata."""
        if not file_storage or not file_storage.filename:
            raise ValueError("A file is required.")

        dut_id = self._required_int(data.get("dut_id"), "dut_id")
        test_id = self._required_int(data.get("test_id"), "test_id")
        result_id = self._optional_int(data.get("result_id"), "result_id")
        attachment_type = data.get("attachment_type") or "supporting_document"
        if attachment_type not in ALLOWED_TYPES:
            raise ValueError("Invalid attachment type.")

        self._validate_references(dut_id, test_id, result_id)

        original_filename = secure_filename(file_storage.filename)
        if not original_filename:
            raise ValueError("Invalid filename.")
        extension = self._extension(original_filename)
        if extension not in ALLOWED_EXTENSIONS:
            raise ValueError("Invalid file extension.")

        file_storage.stream.seek(0, os.SEEK_END)
        file_size = file_storage.stream.tell()
        file_storage.stream.seek(0)
        if file_size > self.max_file_size:
            raise ValueError("File is too large.")

        target_dir = self.upload_dir / f"dut_{dut_id}" / f"test_{test_id}"
        target_dir.mkdir(parents=True, exist_ok=True)
        stored_filename = self._unique_filename(original_filename)
        file_path = target_dir / stored_filename
        file_storage.save(file_path)

        attachment_id = self.db.insert(
            """
            INSERT INTO test_attachments (
                dut_id, test_id, result_id, attachment_type, original_filename,
                stored_filename, file_name, file_path, mime_type, file_size,
                description, uploaded_by
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                dut_id,
                test_id,
                result_id,
                attachment_type,
                original_filename,
                stored_filename,
                original_filename,
                str(file_path),
                file_storage.mimetype,
                file_size,
                data.get("description", ""),
                data.get("uploaded_by", ""),
            ),
        )
        return self.get(attachment_id)

    def list_for_test(self, test_id):
        """Return attachments for a test."""
        return self.db.query(
            "SELECT * FROM test_attachments WHERE test_id = ? ORDER BY created_at DESC, id DESC",
            (test_id,),
        )

    def list_for_dut(self, dut_id):
        """Return attachments for a DUT."""
        return self.db.query(
            "SELECT * FROM test_attachments WHERE dut_id = ? ORDER BY created_at DESC, id DESC",
            (dut_id,),
        )

    def get(self, attachment_id):
        """Return one attachment row."""
        return self.db.query_one("SELECT * FROM test_attachments WHERE id = ?", (attachment_id,))

    def delete(self, attachment_id):
        """Delete attachment metadata and the stored file if present."""
        attachment = self.get(attachment_id)
        if not attachment:
            return None
        file_path = Path(attachment.get("file_path") or "")
        if file_path.exists() and self._is_inside_upload_dir(file_path):
            file_path.unlink()
        self.db.execute("DELETE FROM test_attachments WHERE id = ?", (attachment_id,))
        return attachment

    def _validate_references(self, dut_id, test_id, result_id):
        if not self.db.query_one("SELECT id FROM duts WHERE id = ?", (dut_id,)):
            raise ValueError("DUT not found.")
        test = self.db.query_one("SELECT id, dut_id FROM tests WHERE id = ?", (test_id,))
        if not test:
            raise ValueError("Test not found.")
        if int(test["dut_id"]) != int(dut_id):
            raise ValueError("Test does not belong to the selected DUT.")
        if result_id and not self.db.query_one("SELECT id FROM results WHERE id = ?", (result_id,)):
            raise ValueError("Result not found.")

    def _is_inside_upload_dir(self, file_path):
        try:
            file_path.resolve().relative_to(self.upload_dir.resolve())
            return True
        except ValueError:
            return False

    @staticmethod
    def _required_int(value, field):
        parsed = AttachmentService._optional_int(value, field)
        if parsed is None:
            raise ValueError(f"{field} is required.")
        return parsed

    @staticmethod
    def _optional_int(value, field):
        if value in (None, ""):
            return None
        try:
            return int(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{field} must be numeric.") from exc

    @staticmethod
    def _extension(filename):
        return filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    @staticmethod
    def _unique_filename(original_filename):
        stem, extension = os.path.splitext(original_filename)
        safe_stem = secure_filename(stem)[:80] or "attachment"
        return f"{safe_stem}_{uuid.uuid4().hex}{extension.lower()}"
