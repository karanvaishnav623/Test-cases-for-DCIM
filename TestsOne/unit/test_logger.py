import logging
import pytest
import json
import sys
from unittest.mock import MagicMock, patch
from app.core import logger
from app.core.config import settings

class TestContextManagement:
    """Tests for set_request_context and clear_request_context."""

    def test_set_request_context(self):
        """Positive: Sets request ID and context."""
        logger.clear_request_context()
        logger.set_request_context(request_id="123", user="karan")
        
        assert logger._request_id.get() == "123"
        assert logger._request_context.get() == {"user": "karan"}

    def test_set_request_context_only_id(self):
        """Positive: Sets only request ID and empty context."""
        logger.clear_request_context()
        logger.set_request_context(request_id="456")
        
        assert logger._request_id.get() == "456"
        assert logger._request_context.get() == {}

    def test_clear_request_context(self):
        """Positive: Clears request ID and context."""
        logger.set_request_context(request_id="123")
        logger.clear_request_context()
        
        assert logger._request_id.get() is None
        assert logger._request_context.get() is None


class TestRequestContextFilter:
    """Tests for RequestContextFilter."""

    def test_filter_injects_context(self):
        """Positive: Injects request_id and context into record."""
        logger.set_request_context(request_id="req-1", user_id=99)
        
        log_filter = logger.RequestContextFilter()
        record = logging.LogRecord("name", logging.INFO, "path", 1, "msg", None, None)
        
        log_filter.filter(record)
        
        assert getattr(record, "request_id") == "req-1"
        assert getattr(record, "user_id") == 99

    def test_filter_no_context(self):
        """Negative: Does nothing if no context set."""
        logger.clear_request_context()
        
        log_filter = logger.RequestContextFilter()
        record = logging.LogRecord("name", logging.INFO, "path", 1, "msg", None, None)
        
        log_filter.filter(record)
        
        assert not hasattr(record, "request_id")
        assert not hasattr(record, "user_id")


class TestCustomJsonFormatter:
    """Tests for CustomJsonFormatter."""

    def test_json_formatter_fields(self):
        """Positive: Formats log as JSON with required fields."""
        formatter = logger.CustomJsonFormatter("%(timestamp)s %(message)s")
        record = logging.LogRecord("test_logger", logging.INFO, "path", 1, "Hello", None, None)
        record.request_id = "req-123" # Simulate filter injection
        
        # Inject context for filter/formatter to pick up if it reads from contextvar directly?
        # The formatter reads from contextvar in add_fields
        logger.set_request_context(request_id="req-123", role="admin")
        
        output = formatter.format(record)
        data = json.loads(output)
        
        assert data["message"] == "Hello"
        assert data["level"] == "INFO"
        assert data["environment"] == settings.ENVIRONMENT
        assert data["request_id"] == "req-123"
        assert data["role"] == "admin"
        assert "timestamp" in data

    def test_json_formatter_exception(self):
        """Positive: Includes exception info."""
        formatter = logger.CustomJsonFormatter("%(message)s")
        try:
            raise ValueError("Test Error")
        except ValueError:
            record = logging.LogRecord("test", logging.ERROR, "p", 1, "Fail", None, sys.exc_info())
        
        output = formatter.format(record)
        data = json.loads(output)
        
        assert "exception" in data
        assert "ValueError: Test Error" in data["exception"]


    def test_json_formatter_conflict_keys(self):
        """Negative: Context keys do not overwrite standard fields."""
        formatter = logger.CustomJsonFormatter("%(message)s")
        record = logging.LogRecord("test", logging.INFO, "p", 1, "Msg", None, None)
        
        # Try to overwrite 'level' and 'timestamp'
        logger.set_request_context(level="CRITICAL", timestamp="FAKE")
        
        output = formatter.format(record)
        data = json.loads(output)
        
        assert data["level"] == "INFO"
        assert data["timestamp"] != "FAKE"
        assert "Z" in data["timestamp"]

class TestSetupLogger:
    """Tests for setup_logger."""

    def test_setup_logger_json(self):
        """Positive: Configures JSON formatter."""
        with patch.object(settings, "LOG_LEVEL", "DEBUG"), \
             patch.object(settings, "LOG_FORMAT", "json"), \
             patch.object(settings, "LOG_FILE", None), \
             patch.object(settings, "ENVIRONMENT", "dev"):
            
            l = logger.setup_logger("test_json")
            assert l.handlers[0].formatter.__class__.__name__ == "CustomJsonFormatter"
            assert l.level == logging.DEBUG

    def test_setup_logger_text(self):
        """Positive: Configures Text formatter."""
        with patch.object(settings, "LOG_LEVEL", "INFO"), \
             patch.object(settings, "LOG_FORMAT", "text"), \
             patch.object(settings, "LOG_FILE", None):
            
            l = logger.setup_logger("test_text")
            # The inner class name is TextFormatter
            assert "TextFormatter" in str(l.handlers[0].formatter.__class__)
            assert l.level == logging.INFO

    def test_setup_logger_invalid_level(self):
        """Negative: Falls back to INFO for invalid log level."""
        with patch.object(settings, "LOG_LEVEL", "INVALID_LEVEL"), \
             patch.object(settings, "LOG_FORMAT", "json"), \
             patch.object(settings, "LOG_FILE", None), \
             patch.object(settings, "ENVIRONMENT", "dev"):
            
            l = logger.setup_logger("test_invalid_level")
            assert l.level == logging.INFO

