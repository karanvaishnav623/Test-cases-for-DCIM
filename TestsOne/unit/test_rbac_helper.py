"""
=============================================================================
UNIT TESTS - rbac_helper.py
=============================================================================
"""
import pytest
import jwt
from unittest.mock import MagicMock, patch
from fastapi import HTTPException
from app.helpers.rbac_helper import (
    AccessLevel,
    _access_level_from_roles,
    get_access_level,
    require_at_least_viewer,
    require_editor_or_admin,
    require_admin,
)
from app.helpers import rbac_helper # For integration tests usage if needed

# =============================================================================
# TEST CLASS: _access_level_from_roles
# =============================================================================
class TestAccessLevelFromRoles:
    """Tests for pure logic function _access_level_from_roles"""

    def test_admin_role_returns_admin(self):
        assert _access_level_from_roles({"ADMIN"}) == AccessLevel.admin

    def test_editor_role_returns_editor(self):
        assert _access_level_from_roles({"EDITOR"}) == AccessLevel.editor

    def test_viewer_role_returns_viewer(self):
        assert _access_level_from_roles({"VIEWER"}) == AccessLevel.viewer

    def test_admin_priority_over_others(self):
        """Admin should win even if user has ALL roles"""
        roles = {"ADMIN", "EDITOR", "VIEWER"}
        assert _access_level_from_roles(roles) == AccessLevel.admin

    def test_editor_priority_over_viewer(self):
        """Editor should win over Viewer"""
        roles = {"EDITOR", "VIEWER"}
        assert _access_level_from_roles(roles) == AccessLevel.editor

    def test_unknown_role_returns_viewer(self):
        """Default fallback is viewer"""
        assert _access_level_from_roles({"UNKNOWN_ROLE"}) == AccessLevel.viewer

    def test_empty_roles_returns_viewer(self):
        """No roles defaults to viewer"""
        assert _access_level_from_roles(set()) == AccessLevel.viewer


# =============================================================================
# TEST CLASS: get_access_level
# =============================================================================
class TestGetAccessLevel:
    """Tests the FastAPI dependency that extracts access level from token"""

    def test_get_access_level_admin(self):
        with patch("app.helpers.rbac_helper.decode_access_token") as mock_decode:
            mock_decode.return_value = {"roles": ["ADMIN"]}
            level = get_access_level(authorization="Bearer token")
            assert level == AccessLevel.admin

    def test_get_access_level_superuser_flag(self):
        """Test is_superuser flag bypasses roles"""
        with patch("app.helpers.rbac_helper.decode_access_token") as mock_decode:
            mock_decode.return_value = {"roles": [], "is_superuser": True}
            level = get_access_level(authorization="Bearer token")
            assert level == AccessLevel.admin

    def test_case_insensitivity(self):
        """Lowercase roles should work"""
        with patch("app.helpers.rbac_helper.decode_access_token") as mock_decode:
            mock_decode.return_value = {"roles": ["admin"]}
            level = get_access_level(authorization="Bearer token")
            assert level == AccessLevel.admin

    def test_single_string_role_payload(self):
        """Handle if 'roles' is a string instead of list (defensive coding)"""
        with patch("app.helpers.rbac_helper.decode_access_token") as mock_decode:
            mock_decode.return_value = {"roles": "ADMIN"}
            level = get_access_level(authorization="Bearer token")
            assert level == AccessLevel.admin

    def test_malformed_roles_payload(self):
        """If roles is not iterable, handle gracefully"""
        with patch("app.helpers.rbac_helper.decode_access_token") as mock_decode:
            mock_decode.return_value = {"roles": 123} # Int is not iterable
            level = get_access_level(authorization="Bearer token")
            assert level == AccessLevel.viewer


# =============================================================================
# TEST CLASS: Role Enforcement Dependencies
# =============================================================================
class TestRoleEnforcement:

    # --- require_at_least_viewer ---
    def test_viewer_can_view(self):
        assert require_at_least_viewer(AccessLevel.viewer) == AccessLevel.viewer

    def test_editor_can_view(self):
        assert require_at_least_viewer(AccessLevel.editor) == AccessLevel.editor

    def test_admin_can_view(self):
        assert require_at_least_viewer(AccessLevel.admin) == AccessLevel.admin

    def test_unknown_level_cannot_view(self):
        with pytest.raises(HTTPException) as exc:
            require_at_least_viewer("unknown")
        assert exc.value.status_code == 403

    # --- require_editor_or_admin ---
    def test_editor_can_edit(self):
        assert require_editor_or_admin(AccessLevel.editor) == AccessLevel.editor

    def test_admin_can_edit(self):
        assert require_editor_or_admin(AccessLevel.admin) == AccessLevel.admin

    def test_viewer_cannot_edit(self):
        with pytest.raises(HTTPException) as exc:
            require_editor_or_admin(AccessLevel.viewer)
        assert exc.value.status_code == 403

    # --- require_admin ---
    def test_admin_has_full_access(self):
        assert require_admin(AccessLevel.admin) == AccessLevel.admin

    def test_editor_cannot_admin(self):
        with pytest.raises(HTTPException) as exc:
            require_admin(AccessLevel.editor)
        assert exc.value.status_code == 403

    def test_viewer_cannot_admin(self):
        with pytest.raises(HTTPException) as exc:
            require_admin(AccessLevel.viewer)
        assert exc.value.status_code == 403


# =============================================================================
# Integration Tests (using real JWT encoding)
# =============================================================================

def _make_jwt(roles, is_superuser: bool = False) -> str:
    from app.core.config import settings

    payload = {
        "sub": "1",
        "username": "jdoe",
        "roles": roles,
    }
    if is_superuser:
        payload["is_superuser"] = True

    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def test_get_access_level_uses_roles_from_jwt_integration():
    token = _make_jwt(["viewer"])
    header = f"Bearer {token}"

    level = rbac_helper.get_access_level(authorization=header)

    assert level is AccessLevel.viewer


def test_get_access_level_treats_superuser_as_admin_integration():
    token = _make_jwt(["viewer"], is_superuser=True)
    header = f"Bearer {token}"

    level = rbac_helper.get_access_level(authorization=header)

    assert level is AccessLevel.admin
