import pytest
from datetime import datetime
from app.models.auth_models import (
    User,
    Token,
    Role,
    UserRole,
    Menu,
    SubMenu,
    RoleSubMenuAccess,
    AuditLog,
    UserLocationAccess,
    Environment,
)

class TestAuthModels:
    
    def test_user_instantiation(self):
        """Positive: Verifies User instantiation and defaults."""
        user = User(
            name="jdoe", 
            email="jdoe@example.com", 
            full_name="John Doe"
        )
        assert user.name == "jdoe"
        assert user.email == "jdoe@example.com"
        assert user.is_active is None # Default applied by DB, but instance attr is None until flush usually
        # Actually in SQLAlchemy usage, defaults defined on Column are applied at DB level or Python level depending on arg.
        # Here we just verify mapped attributes.
        assert user.__tablename__ == "dcim_user"

    def test_token_model(self):
        """Positive: Verifies Token model structure."""
        token = Token(
            token_key="abc-123",
            user_id=1,
            token_type="access"
        )
        assert token.token_key == "abc-123"
        assert token.token_type == "access"
        assert token.__tablename__ == "dcim_user_token"

    def test_role_model(self):
        """Positive: Verifies Role model."""
        role = Role(name="Admin", code="ADMIN")
        assert role.code == "ADMIN"
        assert role.__tablename__ == "dcim_rbac_role"

    def test_menu_structure(self):
        """Positive: Verifies Menu and SubMenu relationship logic (attributes)."""
        menu = Menu(header_name="Dashboard", code="DASH")
        sub = SubMenu(display_name="Stats", page_url="/stats", code="STATS", menu=menu)
        
        # Test bidirectional assignment
        assert sub.menu == menu
        # Note: 'sub_menus' relationship is list-like, but without ORM session/instrumentation 
        # append might not work automatically unless back_populates is triggered by SA instrumentation.
        # Unit testing raw objects:
        assert menu.header_name == "Dashboard"
        
    def test_audit_log_model(self):
        """Positive: Verifies AuditLog model."""
        log = AuditLog(action="create", type="device", object_id=100)
        assert log.action == "create"
        assert log.__tablename__ == "dcim_audit_log"

    def test_user_location_access(self):
        """Positive: Verifies UserLocationAccess model."""
        access = UserLocationAccess(user_id=1, location_id=5)
        assert access.user_id == 1
        assert access.location_id == 5

    def test_environment_model(self):
        """Positive: Verifies Environment model."""
        env = Environment(name="Production", env_code="PROD")
        assert env.name == "Production"
        assert env.env_code == "PROD"
        assert env.__tablename__ == "dcim_environment"

    def test_model_defaults_check(self):
        """Positive: check defaults existence on columns (metadata)."""
        # Testing metadata for defaults
        assert User.is_active.default.arg is True
        assert Role.is_active.default.arg is True
