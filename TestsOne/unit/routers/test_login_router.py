import pytest
from unittest.mock import MagicMock, patch
from fastapi import HTTPException
from app.dcim.routers import login_router
from app.schemas import auth_schemas as schemas

class TestLoginRouter:
    """Unit tests for login_router module."""

    def test_login_success(self):
        """Positive: Successful login returns token pair and menu."""
        credentials = schemas.LoginRequest(username="admin", password="password")
        db = MagicMock()
        
        user_mock = MagicMock()
        user_mock.id = 1
        user_mock.name = "admin"
        user_mock.is_active = True
        user_mock.email = "admin@example.com"
        user_mock.full_name = "Admin User"
        user_mock.description = "System Admin"
        
        # Mock user lookup
        db.query.return_value.filter.return_value.first.return_value = user_mock
        
        with patch("app.dcim.routers.login_router._get_auth_models") as mock_models, \
             patch("app.dcim.routers.login_router.create_token_pair_for_user") as mock_create_tokens, \
             patch("app.dcim.routers.login_router.build_menu_for_user") as mock_build_menu, \
             patch("app.dcim.routers.login_router._build_configure_flags") as mock_flags:
            
            mock_create_tokens.return_value = ("access_token", MagicMock(token_key="refresh_token"))
            mock_build_menu.return_value = {"menuList": []}
            mock_flags.return_value = schemas.ConfigureFlags(is_editable=True, is_deletable=True, is_viewer=True)
            
            response = login_router.login(credentials, db)
            
            assert response.access_token == "access_token"
            assert response.refresh_token == "refresh_token"
            assert response.user.name == "admin"
            assert response.user.email == "admin@example.com"
            
            # Verify last_login update
            assert user_mock.last_login is not None
            db.commit.assert_called()

    def test_login_invalid_credentials(self):
        """Negative: Raises 401 if user not found."""
        credentials = schemas.LoginRequest(username="unknown", password="password")
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None
        
        with patch("app.dcim.routers.login_router._get_auth_models"):
            with pytest.raises(HTTPException) as exc_info:
                login_router.login(credentials, db)
            
            assert exc_info.value.status_code == 401
            assert "Invalid username" in exc_info.value.detail

    def test_login_inactive_user(self):
        """Negative: Raises 403 if user inactive."""
        credentials = schemas.LoginRequest(username="inactive", password="password")
        db = MagicMock()
        user_mock = MagicMock()
        user_mock.is_active = False
        db.query.return_value.filter.return_value.first.return_value = user_mock
        
        with patch("app.dcim.routers.login_router._get_auth_models"):
            with pytest.raises(HTTPException) as exc_info:
                login_router.login(credentials, db)
            
            assert exc_info.value.status_code == 403
            assert "inactive" in exc_info.value.detail

    def test_logout(self):
        """Positive: Clears tokens on logout."""
        db = MagicMock()
        current_user = MagicMock(id=1)
        
        with patch("app.dcim.routers.login_router._get_auth_models"):
            login_router.logout(current_user, db)
            
            # verify delete called on token query
            db.query.return_value.filter.return_value.delete.assert_called_once()
            db.commit.assert_called_once()
import pytest
from unittest.mock import MagicMock, patch
from fastapi import HTTPException
from app.dcim.routers import login_router
from app.schemas import auth_schemas as schemas
from app.models import auth_models as models

# ============================================================
# Extended Tests for Login Router
# ============================================================

def test_build_configure_flags():
    """Test RBAC flag generation logic."""
    # User with Admin role
    admin_user = MagicMock(spec=models.User)
    role_admin = MagicMock(spec=models.Role, code="ADMIN", is_active=True)
    admin_user.user_roles = [MagicMock(role=role_admin)]
    
    flags = login_router._build_configure_flags(admin_user)
    assert flags.is_editable is True
    assert flags.is_deletable is True
    assert flags.is_viewer is True
    
    # User with Viewer role
    viewer_user = MagicMock(spec=models.User)
    role_viewer = MagicMock(spec=models.Role, code="VIEWER", is_active=True)
    viewer_user.user_roles = [MagicMock(role=role_viewer)]
    
    flags = login_router._build_configure_flags(viewer_user)
    assert flags.is_editable is False
    assert flags.is_deletable is False
    assert flags.is_viewer is True

    # User with Editor role
    editor_user = MagicMock(spec=models.User)
    role_editor = MagicMock(spec=models.Role, code="EDITOR", is_active=True)
    editor_user.user_roles = [MagicMock(role=role_editor)]
    
    flags = login_router._build_configure_flags(editor_user)
    assert flags.is_editable is True
    assert flags.is_deletable is False
    assert flags.is_viewer is True

class TestRefreshToken:
    
    def test_refresh_token_success(self):
        """Positive: Refresh token flow."""
        db = MagicMock()
        
        user_mock = MagicMock(spec=models.User, id=1, is_active=True)
        user_mock.name = "admin"
        user_mock.email = "admin@example.com"
        user_mock.full_name = "Admin User"
        user_mock.description = "Admin"
        user_mock.created_at = "2023-01-01" # datetime or string depending on schema, schema usually allows str for datetime
        # Actually UserRead schema expects datetime usually, but let's see. 
        # Better to assume Pydantic handles MagicMock if spec is right? No, value must be right type.
        
        refresh_token_model = MagicMock(user=user_mock, token_key="old_refresh")
        
        configure_flags = schemas.ConfigureFlags(is_editable=True, is_deletable=False, is_viewer=True)
        
        with patch("app.dcim.routers.login_router.create_access_token_for_user", return_value="new_access"), \
             patch("app.dcim.routers.login_router.build_menu_for_user", return_value={"menuList": []}), \
             patch("app.dcim.routers.login_router._build_configure_flags", return_value=configure_flags), \
             patch("app.dcim.routers.login_router._get_auth_models"):
             
            response = login_router.refresh_token(refresh_token_model, db)
            
            assert response.access_token == "new_access"
            assert response.refresh_token == "old_refresh"
            assert user_mock.last_login is not None
            db.commit.assert_called()

    def test_refresh_token_inactive_user(self):
        """Negative: Raises 401 if user from token inactive."""
        db = MagicMock()
        user_mock = MagicMock(spec=models.User, is_active=False)
        refresh_token_model = MagicMock(user=user_mock)
        
        with pytest.raises(HTTPException) as exc:
            login_router.refresh_token(refresh_token_model, db)
        assert exc.value.status_code == 401
        assert "Inactive" in exc.value.detail

    def test_refresh_token_no_user(self):
        """Negative: Raises 401 if token has no associated user."""
        db = MagicMock()
        refresh_token_model = MagicMock(user=None)
        
        with pytest.raises(HTTPException) as exc:
            login_router.refresh_token(refresh_token_model, db)
        assert exc.value.status_code == 401
