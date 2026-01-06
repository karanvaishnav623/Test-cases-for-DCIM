import pytest
from unittest.mock import MagicMock
from app.helpers import audit_helper
from app.models.auth_models import AuditLog, User

class TestAuditHelper:
    """Unit tests for audit_helper module."""

    def test_create_audit_log_success(self):
        """Positive: Creates an AuditLog entry."""
        db = MagicMock()
        user = MagicMock(spec=User)
        user.id = 1
        
        log = audit_helper.create_audit_log(
            db=db,
            user=user,
            action="create",
            entity_type="device",
            object_id=10,
            data={"foo": "bar"}
        )
        
        assert log.action == "create"
        assert log.type == "device"
        assert log.user_id == 1
        assert "foo" in log.message
        
        db.add.assert_called_once_with(log)


    def test_log_create_wrapper(self):
        """Positive: log_create uses create_audit_log correctly."""
        db = MagicMock()
        user = MagicMock(spec=User)
        
        log = audit_helper.log_create(
            db=db,
            user=user,
            entity_type="rack",
            object_id=5,
            entity_data={"name": "R1"}
        )
        
        assert log.action == "create"
        assert "created" in log.message
        db.add.assert_called_once()

    def test_create_audit_log_system_action(self):
        """Positive: Creates audit log without a user (system action)."""
        db = MagicMock()
        
        log = audit_helper.create_audit_log(
            db=db,
            user=None,
            action="system_check",
            entity_type="system",
        )
        
        assert log.user_id is None
        assert log.action == "system_check"
        db.add.assert_called_once()

    def test_create_audit_log_defaults(self):
        """Positive: Handles missing optional fields gracefully."""
        db = MagicMock()
        user = MagicMock(spec=User)
        user.id = 1
        
        log = audit_helper.create_audit_log(
            db=db,
            user=user,
            action="ping",
            entity_type="monitor"
        )
        
        assert log.message is None # Should arguably be empty JSON or similar, but code says None if no payload/msg
        assert log.object_id is None

    def test_log_update(self):
        """Positive: log_update creates correctly formatted log."""
        db = MagicMock()
        user = MagicMock(spec=User)
        changes = {"status": "inactive"}
        
        log = audit_helper.log_update(
            db=db,
            user=user,
            entity_type="device",
            object_id=99,
            changes=changes
        )
        
        assert log.action == "update"
        assert "updated_fields" in log.message
        assert "status" in log.message

    def test_log_delete(self):
        """Positive: log_delete creates correctly formatted log."""
        db = MagicMock()
        user = MagicMock(spec=User)
        
        log = audit_helper.log_delete(
            db=db,
            user=user,
            entity_type="location",
            object_id=3
        )
        
        assert log.action == "delete"
        db.add.assert_called_once()

    def test_build_audit_context_full(self):
        """Positive: Builds full context dictionary."""
        request = MagicMock()
        request.url.path = "/api/v1/test"
        request.method = "POST"
        
        context = audit_helper.build_audit_context(
            router="test_router",
            action="test_action",
            entity="test_entity",
            request=request,
            extra={"foo": "bar"}
        )
        
        assert context["router"] == "test_router"
        assert context["path"] == "/api/v1/test"
        assert context["entity"] == "test_entity"
        assert context["foo"] == "bar"

    def test_build_audit_context_minimal(self):
        """Positive: Builds minimal context dictionary."""
        context = audit_helper.build_audit_context(
            router="simple",
            action="check"
        )
        
        assert context["router"] == "simple"
        assert "entity" not in context
        assert "path" not in context
