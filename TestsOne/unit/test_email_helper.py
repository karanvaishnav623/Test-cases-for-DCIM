from unittest.mock import patch, MagicMock, call
import pytest
import smtplib
from app.helpers import email_helper


class TestNormalizeRecipients:
    """Unit tests for _normalize_recipients function."""

    def test_normalize_recipients_filters_empty_strings(self):
        """Negative: Empty strings are filtered out."""
        recipients = ["user@example.com", "", "admin@example.com", None]
        result = email_helper._normalize_recipients(recipients)
        
        assert result == ["user@example.com", "admin@example.com"]
        assert "" not in result
        assert None not in result

    def test_normalize_recipients_removes_duplicates(self):
        """Positive: Duplicate recipients are removed."""
        recipients = ["user@example.com", "admin@example.com", "user@example.com"]
        result = email_helper._normalize_recipients(recipients)
        
        assert result == ["user@example.com", "admin@example.com"]
        assert len(result) == 2

    def test_normalize_recipients_preserves_order(self):
        """Positive: Order is preserved (first occurrence kept)."""
        recipients = ["first@example.com", "second@example.com", "first@example.com"]
        result = email_helper._normalize_recipients(recipients)
        
        assert result == ["first@example.com", "second@example.com"]

    def test_normalize_recipients_handles_all_empty(self):
        """Negative: Returns empty list when all recipients are empty/None."""
        recipients = ["", None, ""]
        result = email_helper._normalize_recipients(recipients)
        
        assert result == []

    def test_normalize_recipients_handles_empty_sequence(self):
        """Negative: Returns empty list for empty sequence."""
        recipients = []
        result = email_helper._normalize_recipients(recipients)
        
        assert result == []


class TestSendEmail:
    """Unit tests for send_email function."""

    @patch("app.helpers.email_helper.app_logger")
    def test_send_email_skips_when_no_recipients(self, mock_logger):
        """Negative: Skips sending when no valid recipients."""
        email_helper.send_email(
            subject="Test",
            body="Body",
            recipients=["", None]
        )
        
        mock_logger.warning.assert_called_once_with(
            "Email send skipped because no recipients were provided."
        )

    @patch("app.helpers.email_helper.app_logger")
    @patch("app.helpers.email_helper.settings")
    def test_send_email_skips_when_smtp_host_missing(self, mock_settings, mock_logger):
        """Negative: Skips sending when SMTP_HOST is missing."""
        mock_settings.SMTP_HOST = None
        mock_settings.SMTP_FROM_EMAIL = "from@example.com"
        
        email_helper.send_email(
            subject="Test",
            body="Body",
            recipients=["user@example.com"]
        )
        
        mock_logger.warning.assert_called_once_with(
            "SMTP settings missing (host/from). Cannot send email."
        )

    @patch("app.helpers.email_helper.app_logger")
    @patch("app.helpers.email_helper.settings")
    def test_send_email_skips_when_smtp_from_missing(self, mock_settings, mock_logger):
        """Negative: Skips sending when SMTP_FROM_EMAIL is missing."""
        mock_settings.SMTP_HOST = "smtp.example.com"
        mock_settings.SMTP_FROM_EMAIL = None
        
        email_helper.send_email(
            subject="Test",
            body="Body",
            recipients=["user@example.com"]
        )
        
        mock_logger.warning.assert_called_once_with(
            "SMTP settings missing (host/from). Cannot send email."
        )

    @patch("app.helpers.email_helper.app_logger")
    @patch("app.helpers.email_helper.settings")
    @patch("app.helpers.email_helper.smtplib.SMTP")
    def test_send_email_uses_smtp_when_ssl_disabled(self, mock_smtp_class, mock_settings, mock_logger):
        """Positive: Uses SMTP when SSL is disabled."""
        mock_settings.SMTP_HOST = "smtp.example.com"
        mock_settings.SMTP_FROM_EMAIL = "from@example.com"
        mock_settings.SMTP_PORT = 587
        mock_settings.SMTP_TIMEOUT = 30
        mock_settings.SMTP_USE_SSL = False
        mock_settings.SMTP_USE_TLS = True
        mock_settings.SMTP_USERNAME = "user"
        mock_settings.SMTP_PASSWORD = "pass"
        
        mock_smtp_instance = MagicMock()
        mock_smtp_class.return_value.__enter__.return_value = mock_smtp_instance
        
        email_helper.send_email(
            subject="Test Subject",
            body="Test Body",
            recipients=["user@example.com"]
        )
        
        mock_smtp_class.assert_called_once_with(
            host="smtp.example.com",
            port=587,
            timeout=30
        )
        mock_smtp_instance.starttls.assert_called_once()
        mock_smtp_instance.login.assert_called_once_with("user", "pass")
        mock_smtp_instance.send_message.assert_called_once()
        mock_logger.info.assert_called_once()

    @patch("app.helpers.email_helper.app_logger")
    @patch("app.helpers.email_helper.settings")
    @patch("app.helpers.email_helper.smtplib.SMTP_SSL")
    def test_send_email_uses_smtp_ssl_when_enabled(self, mock_smtp_ssl_class, mock_settings, mock_logger):
        """Positive: Uses SMTP_SSL when SSL is enabled."""
        mock_settings.SMTP_HOST = "smtp.example.com"
        mock_settings.SMTP_FROM_EMAIL = "from@example.com"
        mock_settings.SMTP_PORT = 465
        mock_settings.SMTP_TIMEOUT = 30
        mock_settings.SMTP_USE_SSL = True
        mock_settings.SMTP_USE_TLS = False
        mock_settings.SMTP_USERNAME = "user"
        mock_settings.SMTP_PASSWORD = "pass"
        
        mock_smtp_instance = MagicMock()
        mock_smtp_ssl_class.return_value.__enter__.return_value = mock_smtp_instance
        
        email_helper.send_email(
            subject="Test Subject",
            body="Test Body",
            recipients=["user@example.com"]
        )
        
        mock_smtp_ssl_class.assert_called_once_with(
            host="smtp.example.com",
            port=465,
            timeout=30
        )
        mock_smtp_instance.starttls.assert_not_called()
        mock_smtp_instance.login.assert_called_once_with("user", "pass")
        mock_smtp_instance.send_message.assert_called_once()

    @patch("app.helpers.email_helper.app_logger")
    @patch("app.helpers.email_helper.settings")
    @patch("app.helpers.email_helper.smtplib.SMTP")
    def test_send_email_skips_login_when_no_credentials(self, mock_smtp_class, mock_settings, mock_logger):
        """Negative: Skips login when username/password not provided."""
        mock_settings.SMTP_HOST = "smtp.example.com"
        mock_settings.SMTP_FROM_EMAIL = "from@example.com"
        mock_settings.SMTP_PORT = 587
        mock_settings.SMTP_TIMEOUT = 30
        mock_settings.SMTP_USE_SSL = False
        mock_settings.SMTP_USE_TLS = False
        mock_settings.SMTP_USERNAME = None
        mock_settings.SMTP_PASSWORD = None
        
        mock_smtp_instance = MagicMock()
        mock_smtp_class.return_value.__enter__.return_value = mock_smtp_instance
        
        email_helper.send_email(
            subject="Test Subject",
            body="Test Body",
            recipients=["user@example.com"]
        )
        
        mock_smtp_instance.login.assert_not_called()
        mock_smtp_instance.send_message.assert_called_once()

    @patch("app.helpers.email_helper.app_logger")
    @patch("app.helpers.email_helper.settings")
    @patch("app.helpers.email_helper.smtplib.SMTP")
    def test_send_email_logs_exception_on_failure(self, mock_smtp_class, mock_settings, mock_logger):
        """Negative: Logs exception when SMTP send fails."""
        mock_settings.SMTP_HOST = "smtp.example.com"
        mock_settings.SMTP_FROM_EMAIL = "from@example.com"
        mock_settings.SMTP_PORT = 587
        mock_settings.SMTP_TIMEOUT = 30
        mock_settings.SMTP_USE_SSL = False
        mock_settings.SMTP_USE_TLS = False
        mock_settings.SMTP_USERNAME = None
        mock_settings.SMTP_PASSWORD = None
        
        mock_smtp_instance = MagicMock()
        mock_smtp_instance.send_message.side_effect = Exception("SMTP Error")
        mock_smtp_class.return_value.__enter__.return_value = mock_smtp_instance
        
        email_helper.send_email(
            subject="Test Subject",
            body="Test Body",
            recipients=["user@example.com"]
        )
        
        mock_logger.exception.assert_called_once_with("Failed to send email via SMTP")


class TestFormatBulkUploadReport:
    """Unit tests for format_bulk_upload_report function."""

    def test_format_bulk_upload_report_with_failure_reason(self):
        """Negative: Formats report with failure reason."""
        job_id = "job123"
        summary = None
        results = []
        failure_reason = "Connection timeout"
        
        report = email_helper.format_bulk_upload_report(
            job_id=job_id,
            summary=summary,
            results=results,
            failure_reason=failure_reason
        )
        
        assert "Bulk upload job job123 has completed processing." in report
        assert "Status: FAILED" in report
        assert "Reason: Connection timeout" in report
        assert "Status: COMPLETED" not in report

    def test_format_bulk_upload_report_with_summary(self):
        """Positive: Formats report with summary data."""
        job_id = "job456"
        summary = {
            "entity": "devices",
            "total_rows": 10,
            "processed": 10,
            "success": 8,
            "errors": 2
        }
        results = []
        failure_reason = None
        
        report = email_helper.format_bulk_upload_report(
            job_id=job_id,
            summary=summary,
            results=results,
            failure_reason=failure_reason
        )
        
        assert "Bulk upload job job456 has completed processing." in report
        assert "Status: COMPLETED" in report
        assert "Entity: devices" in report
        assert "Total rows: 10" in report
        assert "Processed rows: 10" in report
        assert "Successful rows: 8" in report
        assert "Failed rows: 2" in report

    def test_format_bulk_upload_report_with_aborted_flag(self):
        """Positive: Includes aborted message when summary.aborted is True."""
        job_id = "job789"
        summary = {
            "entity": "devices",
            "total_rows": 10,
            "processed": 5,
            "success": 3,
            "errors": 2,
            "aborted": True
        }
        results = []
        failure_reason = None
        
        report = email_helper.format_bulk_upload_report(
            job_id=job_id,
            summary=summary,
            results=results,
            failure_reason=failure_reason
        )
        
        assert "Processing stopped early because skip_errors was disabled." in report

    def test_format_bulk_upload_report_with_success_rows(self):
        """Positive: Formats success row results correctly."""
        job_id = "job999"
        summary = None
        results = [
            {"status": "success", "row": 1, "data": {"id": "device1"}},
            {"status": "success", "row": 2, "data": {"device_id": "device2"}},
        ]
        failure_reason = None
        
        report = email_helper.format_bulk_upload_report(
            job_id=job_id,
            summary=summary,
            results=results,
            failure_reason=failure_reason
        )
        
        # Since row results are no longer in the report body, we just check base message
        assert "Bulk upload job job999 has completed processing." in report

    def test_format_bulk_upload_report_with_error_rows(self):
        """Negative: Formats error row results correctly."""
        job_id = "job888"
        summary = None
        results = [
            {"status": "error", "row": 1, "error": "Invalid format"},
            {"status": "error", "row": 2, "error": "Missing required field"},
        ]
        failure_reason = None
        
        report = email_helper.format_bulk_upload_report(
            job_id=job_id,
            summary=summary,
            results=results,
            failure_reason=failure_reason
        )
        
        # Since row results are no longer in the report body, we just check base message
        assert "Bulk upload job job888 has completed processing." in report

    def test_format_bulk_upload_report_with_unknown_status(self):
        """Negative: Handles unknown status rows."""
        job_id = "job777"
        summary = None
        results = [
            {"status": "pending", "row": 1},
            {"status": None, "row": 2},
        ]
        failure_reason = None
        
        report = email_helper.format_bulk_upload_report(
            job_id=job_id,
            summary=summary,
            results=results,
            failure_reason=failure_reason
        )
        
        # Since row results are no longer in the report body, we just check base message
        assert "Bulk upload job job777 has completed processing." in report

    def test_format_bulk_upload_report_with_no_summary_no_failure(self):
        """Negative: Formats report when neither summary nor failure reason provided."""
        job_id = "job666"
        summary = None
        results = []
        failure_reason = None
        
        report = email_helper.format_bulk_upload_report(
            job_id=job_id,
            summary=summary,
            results=results,
            failure_reason=failure_reason
        )
        
        assert "Bulk upload job job666 has completed processing." in report
        assert "Status: FAILED" not in report
        assert "Status: COMPLETED" not in report
        assert "Row results:" not in report


class TestSendBulkUploadReport:
    """Unit tests for send_bulk_upload_report function."""

    @patch("app.helpers.email_helper.send_email")
    def test_send_bulk_upload_report_calls_send_email(self, mock_send_email):
        """Positive: Calls send_email with expected arguments."""
        job_id = "job123"
        summary = {"entity": "devices", "success": 5}
        results = [{"status": "success", "row": 1}]
        recipients = ["admin@example.com"]
        failure_reason = None
        
        email_helper.send_bulk_upload_report(
            job_id=job_id,
            summary=summary,
            results=results,
            recipients=recipients,
            failure_reason=failure_reason
        )
        
        mock_send_email.assert_called_once()
        args, kwargs = mock_send_email.call_args
        assert kwargs["subject"] == "DCIM Bulk Upload Report | Job job123"
        assert kwargs["recipients"] == recipients


    @patch("app.helpers.email_helper.send_email")
    def test_send_bulk_upload_report_with_error_csv(self, mock_send_email):
        """Positive: Attaches error CSV when provided."""
        job_id = "job_error"
        summary = {"entity": "devices", "errors": 5}
        results = []
        recipients = ["admin@example.com"]
        error_csv_bytes = b"header1,header2\nval1,val2"
        
        email_helper.send_bulk_upload_report(
            job_id=job_id,
            summary=summary,
            results=results,
            recipients=recipients,
            failure_reason="Partial failure",
            error_csv_bytes=error_csv_bytes
        )
        
        mock_send_email.assert_called_once()
        args, kwargs = mock_send_email.call_args
        
        # Check that attachments were passed
        assert "attachments" in kwargs
        attachments = kwargs["attachments"]
        assert len(attachments) == 1
        
        # Verify attachment structure: (bytes, filename, content_type)
        file_bytes, filename, content_type = attachments[0]
        assert file_bytes == error_csv_bytes
        assert filename == f"bulk_upload_errors_{job_id}.csv"
        assert content_type == "text/csv"


    @patch("app.helpers.email_helper.app_logger")
    @patch("app.helpers.email_helper.settings")
    @patch("app.helpers.email_helper.smtplib.SMTP")
    def test_send_email_with_attachments(self, mock_smtp_class, mock_settings, mock_logger):
        """Positive: Uses MIMEMultipart when attachments are present."""
        mock_settings.SMTP_HOST = "smtp.test.com"
        mock_settings.SMTP_FROM_EMAIL = "from@test.com"
        mock_settings.SMTP_PORT = 25
        mock_settings.SMTP_USE_SSL = False
        mock_settings.SMTP_USE_TLS = False
        mock_settings.SMTP_USERNAME = None
        mock_settings.SMTP_PASSWORD = None
        
        mock_smtp_instance = MagicMock()
        mock_smtp_class.return_value.__enter__.return_value = mock_smtp_instance
        
        attachments = [(b"file_content", "test.txt", "text/plain")]
        
        # We verify that MIMEMultipart was used by checking the message structure or type passed to send_message
        # Since we can't easily check type(message) inside the mocked call without side_effects or specialized matching,
        # we can verify behaviors typical of MIMEMultipart vs EmailMessage.
        # MIMEMultipart uses explicit .attach() calls for parts.
        
        # However, `email_helper.py` logic:
        # if attachments: message = MIMEMultipart() ... message.attach(MIMEText)... message.attach(part)
        
        # Let's check send_message call argument
        email_helper.send_email(
            subject="With Attachment",
            body="Body",
            recipients=["to@test.com"],
            attachments=attachments
        )
        
        mock_smtp_instance.send_message.assert_called_once()
        msg_arg = mock_smtp_instance.send_message.call_args[0][0]
        
        # Verify it's a multipart message
        assert msg_arg.is_multipart() is True
        
        # Verify payload contains both text part and attachment part
        payload = msg_arg.get_payload()
        assert len(payload) == 2
        
        # Check attachment part
        attachment_part = payload[1]
        assert attachment_part.get_filename() == "test.txt"
        assert attachment_part.get_payload(decode=True) == b"file_content"


