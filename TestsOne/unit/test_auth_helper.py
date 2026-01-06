from datetime import datetime, timedelta, timezone

import jwt
import pytest
from fastapi import HTTPException, status

from app.core.config import settings
from app.helpers import auth_helper


class DummyRole:
    def __init__(self, code: str | None, is_active: bool = True) -> None:
        self.code = code
        self.is_active = is_active


class DummyUserRole:
    def __init__(self, role: DummyRole | None) -> None:
        self.role = role


class DummyUser:
    def __init__(
        self,
        *,
        user_id: int = 1,
        name: str = "jdoe",
        email: str = "jdoe@example.com",
        is_active: bool = True,
        roles: list[DummyUserRole] | None = None,
    ) -> None:
        self.id = user_id
        self.name = name
        self.email = email
        self.is_active = is_active
        self.user_roles = roles or []


def test_get_token_from_header_valid():
    token = "abc123"
    header = f"Bearer {token}"

    result = auth_helper._get_token_from_header(header)  # type: ignore[attr-defined]

    assert result == token


@pytest.mark.parametrize(
    "header",
    [
        None,
        "",
        "Token abc",
        "Bearer ",
        "bearer",  # missing token part
    ],
)
def test_get_token_from_header_invalid(header):
    with pytest.raises(HTTPException) as exc_info:
        auth_helper._get_token_from_header(header)  # type: ignore[attr-defined]

    assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED


def test_build_jwt_payload_includes_roles_and_expiry():
    roles = [
        DummyUserRole(DummyRole("admin", is_active=True)),
        DummyUserRole(DummyRole("viewer", is_active=False)),  # inactive ignored
        DummyUserRole(DummyRole(None, is_active=True)),  # no code ignored
    ]
    user = DummyUser(user_id=42, roles=roles)

    payload = auth_helper._build_jwt_payload(user)  # type: ignore[attr-defined]

    assert payload["sub"] == str(42)
    assert payload["username"] == user.name
    assert payload["email"] == user.email
    # Only ADMIN should be present and upper-cased
    assert payload["roles"] == ["ADMIN"]
    assert payload["is_active"] is True

    now = datetime.now(timezone.utc).timestamp()
    assert payload["iat"] <= int(now)
    assert payload["exp"] > payload["iat"]


def test_create_and_decode_access_token_roundtrip():
    user = DummyUser(user_id=7)

    token = auth_helper.create_access_token_for_user(user=user)
    assert isinstance(token, str) and token

    decoded = auth_helper.decode_access_token(token)

    assert decoded["sub"] == str(7)
    assert decoded["username"] == user.name


def test_decode_access_token_expired_raises_419():
    payload = {
        "sub": "1",
        "exp": int((datetime.now(timezone.utc) - timedelta(seconds=1)).timestamp()),
    }
    expired_token = jwt.encode(
        payload,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )

    with pytest.raises(HTTPException) as exc_info:
        auth_helper.decode_access_token(expired_token)

    assert exc_info.value.status_code == 419
    assert "expired" in exc_info.value.detail.lower()


def test_decode_access_token_invalid_signature_raises_401():
    # Token signed with a different key should be rejected
    bogus_token = jwt.encode(
        {"sub": "1"},
        "wrong-key",
        algorithm=settings.JWT_ALGORITHM,
    )

    with pytest.raises(HTTPException) as exc_info:
        auth_helper.decode_access_token(bogus_token)

    assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
    assert "invalid" in exc_info.value.detail.lower()


# ============================================================
# NEW TEST: User with no roles should have empty roles list
# ============================================================
def test_build_jwt_payload_user_with_no_roles():
    """
    Test that a user with no roles gets an empty roles list in JWT payload.
    
    This is an edge case - new users might not have roles assigned yet.
    """
    # STEP 1: Create a fake user with NO roles
    user = DummyUser(
        user_id=99,
        name="newuser",
        email="newuser@example.com",
        is_active=True,
        roles=[],  # Empty roles!
    )
    
    # STEP 2: Call the function we're testing
    payload = auth_helper._build_jwt_payload(user)
    
    # STEP 3: Assert (check) the results
    assert payload["sub"] == "99"
    assert payload["username"] == "newuser"
    assert payload["email"] == "newuser@example.com"
    assert payload["roles"] == []  # Should be empty list!
    assert payload["is_active"] is True


def test_build_jwt_payload_inactive_user():
    """
    Test that inactive user flag is correctly set in JWT payload.
    """
    # Create an INACTIVE user
    user = DummyUser(
        user_id=100,
        name="inactiveuser",
        email="inactive@example.com",
        is_active=False,  # Inactive!
        roles=[],
    )
    
    payload = auth_helper._build_jwt_payload(user)
    
    assert payload["is_active"] is False  # Should be False!



from unittest.mock import MagicMock, patch, ANY

def test_get_current_refresh_token_success():
    """Positive: Successfully retrieves and validates a refresh token."""
    db = MagicMock()
    token_str = "refresh123"
    auth_header = f"Bearer {token_str}"
    
    mock_token_model = MagicMock()
    mock_token_model.token_key = token_str
    mock_token_model.token_type = "refresh"
    mock_token_model.expires = datetime.utcnow() + timedelta(hours=1)
    
    # Mock database query
    db.query.return_value.filter.return_value.first.return_value = mock_token_model
    
    with patch("app.helpers.auth_helper._get_models") as mock_get_models:
        mock_models = MagicMock()
        mock_models.Token = MagicMock()
        mock_get_models.return_value = mock_models
        
        result = auth_helper.get_current_refresh_token(db, auth_header)
        assert result == mock_token_model

def test_get_current_refresh_token_not_found():
    """Negative: 401 if refresh token not found in DB."""
    db = MagicMock()
    auth_header = "Bearer unknown"
    db.query.return_value.filter.return_value.first.return_value = None
    
    with patch("app.helpers.auth_helper._get_models"):
        with pytest.raises(HTTPException) as exc:
            auth_helper.get_current_refresh_token(db, auth_header)
        assert exc.value.status_code == 401
        assert "not found" in exc.value.detail

def test_get_current_refresh_token_expired():
    """Negative: 401 if refresh token is expired."""
    db = MagicMock()
    auth_header = "Bearer expired"
    
    mock_token = MagicMock()
    mock_token.token_type = "refresh"
    mock_token.expires = datetime.utcnow() - timedelta(seconds=1)
    
    db.query.return_value.filter.return_value.first.return_value = mock_token
    
    with patch("app.helpers.auth_helper._get_models"):
        with pytest.raises(HTTPException) as exc:
            auth_helper.get_current_refresh_token(db, auth_header)
        assert exc.value.status_code == 401
        assert "expired" in exc.value.detail

def test_get_current_user_success():
    """Positive: Successfully retrieves active user from access token."""
    db = MagicMock()
    user_id = 99
    
    # Mock user in DB
    mock_user = MagicMock()
    mock_user.id = user_id
    mock_user.is_active = True
    db.query.return_value.get.return_value = mock_user
    
    # Mock payload decoding
    with patch("app.helpers.auth_helper.decode_access_token") as mock_decode, \
         patch("app.helpers.auth_helper._get_models"):
        
        mock_decode.return_value = {"sub": str(user_id)}
        
        result = auth_helper.get_current_user("Bearer valid_token", db)
        assert result == mock_user

def test_get_current_user_invalid_sub():
    """Negative: 401 if sub is missing or invalid."""
    db = MagicMock()
    with patch("app.helpers.auth_helper.decode_access_token") as mock_decode:
        mock_decode.return_value = {} # Missing sub
        
        with pytest.raises(HTTPException) as exc:
            auth_helper.get_current_user("Bearer token", db)
        assert exc.value.status_code == 401
        assert "missing subject" in exc.value.detail

def test_get_current_user_not_found_or_inactive():
    """Negative: 401 if user doesn't exist or is inactive."""
    db = MagicMock()
    # Case 1: User not found
    db.query.return_value.get.return_value = None
    
    with patch("app.helpers.auth_helper.decode_access_token") as mock_decode, \
         patch("app.helpers.auth_helper._get_models"):
         
        mock_decode.return_value = {"sub": "1"}
        
        with pytest.raises(HTTPException) as exc:
            auth_helper.get_current_user("Bearer token", db)
        assert exc.value.status_code == 401

def test_build_menu_for_user_admin():
    """Positive: Admin user gets all menus."""
    db = MagicMock()
    user_id = 1
    
    # Mock user with admin role
    mock_user = MagicMock()
    mock_role = MagicMock()
    mock_role.code = "ADMIN"
    mock_user_role = MagicMock()
    mock_user_role.role = mock_role
    mock_user.user_roles = [mock_user_role]
    
    db.query.return_value.get.return_value = mock_user
    
    # Mock menu query results
    mock_menu = MagicMock()
    mock_menu.id = 1
    mock_menu.header_name = "AdminMenu"
    mock_menu.icon = "admin_icon"
    
    mock_submenu = MagicMock()
    mock_submenu.display_name = "Dashboard"
    mock_submenu.page_url = "/admin"
    mock_submenu.icon = "dash_icon"
    
    # Return list of (Menu, SubMenu) tuples
    db.query.return_value.join.return_value.filter.return_value.filter.return_value.order_by.return_value.all.return_value = [
        (mock_menu, mock_submenu)
    ]
    
    with patch("app.helpers.auth_helper._get_models"):
        result = auth_helper.build_menu_for_user(db, user_id)
        
        menu_list = result["menuList"]
        assert len(menu_list) == 1
        assert menu_list[0]["MenuHeaderName"] == "AdminMenu"
        assert menu_list[0]["sub_menu_details"][0]["display_name"] == "Dashboard"

def test_create_token_pair_for_user():
    """Positive: Creates both access and refresh tokens."""
    db = MagicMock()
    user = DummyUser(user_id=5)
    
    with patch("app.helpers.auth_helper.create_access_token_for_user") as mock_create_access, \
         patch("app.helpers.auth_helper.create_token_for_user") as mock_create_refresh:
         
        mock_create_access.return_value = "access_token_str"
        mock_create_refresh.return_value = MagicMock(token_key="refresh_key")
        
        access, refresh = auth_helper.create_token_pair_for_user(user=user, db=db) # type: ignore
        
        assert access == "access_token_str"
        assert refresh.token_key == "refresh_key"
