
import pytest
from pydantic import ValidationError
from typing import get_type_hints
from app.schemas.auth_schemas import (
    LoginRequest,
    UserCreate,
    RoleCreate,
    MenuCreate,
    SubMenuCreate,
    EnvironmentCreate,
    UserUpdate,
    RoleUpdate,
    MenuUpdate,
    SubMenuUpdate,
    EnvironmentUpdate,
    RoleSubMenuAccessCreate,
    RoleSubMenuAccessUpdate,
    UserBase, RoleBase, MenuBase, SubMenuBase, EnvironmentBase
)

# =============================================================================
# Helpers
# =============================================================================

def check_field_coverage(schema_class, tested_fields):
    """
    Ensures that all fields in the schema are present in the tested_fields list.
    """
    model_fields = set(schema_class.model_fields.keys())
    assert model_fields == set(tested_fields), \
        f"Mismatch in tested fields for {schema_class.__name__}. Missing: {model_fields - set(tested_fields)}"

# =============================================================================
# LoginRequest Tests
# =============================================================================

class TestLoginRequest:
    @pytest.fixture
    def valid_data(self):
        return {
            "username": "testuser",
            "password": "secretpassword"
        }

    def test_happy_path(self, valid_data):
        model = LoginRequest(**valid_data)
        assert model.username == valid_data["username"]
        assert model.password == valid_data["password"]

    @pytest.mark.parametrize("field, invalid_value, error_type", [
        ("username", None, "string_type"), # Should be str
        ("username", 123, "string_type"),
        ("password", None, "string_type"),
        ("password", 123, "string_type"),
    ])
    def test_invalid_values(self, valid_data, field, invalid_value, error_type):
        data = valid_data.copy()
        data[field] = invalid_value
        with pytest.raises(ValidationError) as exc_info:
            LoginRequest(**data)
        errors = exc_info.value.errors()
        assert any(e["loc"] == (field,) for e in errors)

    @pytest.mark.parametrize("field", ["username", "password"])
    def test_missing_fields(self, valid_data, field):
        data = valid_data.copy()
        del data[field]
        with pytest.raises(ValidationError) as exc_info:
            LoginRequest(**data)
        assert exc_info.value.errors()[0]["type"] == "missing"
        assert exc_info.value.errors()[0]["loc"] == (field,)

    def test_field_coverage(self):
        check_field_coverage(LoginRequest, ["username", "password"])


# =============================================================================
# UserCreate Tests
# =============================================================================

class TestUserCreate:
    @pytest.fixture
    def valid_data(self):
        return {
            "name": "jdoe",
            "email": "jdoe@example.com",
            "full_name": "John Doe",
            "description": "A new user"
        }

    def test_happy_path(self, valid_data):
        model = UserCreate(**valid_data)
        assert model.name == valid_data["name"]
        assert model.email == valid_data["email"]

    @pytest.mark.parametrize("field, invalid_value", [
        ("name", None),
        ("name", 123),
        ("email", "not-an-email"),
        ("email", None),
        ("description", "x" * 256),  # Max length 255
    ])
    def test_invalid_values(self, valid_data, field, invalid_value):
        data = valid_data.copy()
        data[field] = invalid_value
        with pytest.raises(ValidationError) as exc_info:
            UserCreate(**data)
        assert any(e["loc"] == (field,) for e in exc_info.value.errors())

    @pytest.mark.parametrize("field", ["name", "email"])
    def test_missing_fields(self, valid_data, field):
        data = valid_data.copy()
        del data[field]
        with pytest.raises(ValidationError) as exc_info:
            UserCreate(**data)
        assert exc_info.value.errors()[0]["type"] == "missing"

    def test_field_coverage(self):
        # UserCreate inherits from UserBase
        check_field_coverage(UserCreate, ["name", "email", "full_name", "description"])

    @pytest.mark.parametrize("length, should_pass", [
        (255, True),  # Exact Boundary
        (256, False), # Boundary + 1
    ])
    def test_bva_description(self, valid_data, length, should_pass):
        data = valid_data.copy()
        data["description"] = "x" * length
        if should_pass:
            model = UserCreate(**data)
            assert len(model.description) == length
        else:
            with pytest.raises(ValidationError) as exc_info:
                UserCreate(**data)
            assert any(e["loc"] == ("description",) for e in exc_info.value.errors())

# =============================================================================
# UserUpdate Tests
# =============================================================================

class TestUserUpdate:
    @pytest.fixture
    def valid_data(self):
        return {
            "name": "jdoe_updated",
            "email": "jdoe_updated@example.com",
            "full_name": "John Doe Updated",
            "is_active": False,
            "description": "Updated info"
        }

    def test_happy_path(self, valid_data):
        model = UserUpdate(**valid_data)
        assert model.name == valid_data["name"]

    def test_partial_update(self):
        # All fields are optional
        model = UserUpdate(name="only_name")
        assert model.name == "only_name"
        assert model.email is None

    @pytest.mark.parametrize("field, invalid_value", [
        ("email", "not-an-email"),
        ("description", "x" * 256),
    ])
    def test_invalid_values(self, valid_data, field, invalid_value):
        data = valid_data.copy()
        data[field] = invalid_value
        with pytest.raises(ValidationError) as exc_info:
            UserUpdate(**data)
        assert any(e["loc"] == (field,) for e in exc_info.value.errors())

    def test_field_coverage(self):
        check_field_coverage(UserUpdate, ["name", "email", "full_name", "is_active", "description"])

    @pytest.mark.parametrize("length, should_pass", [
        (255, True),
        (256, False),
    ])
    def test_bva_description(self, valid_data, length, should_pass):
        data = valid_data.copy()
        data["description"] = "x" * length
        if should_pass:
            model = UserUpdate(**data)
            assert len(model.description) == length
        else:
            with pytest.raises(ValidationError) as exc_info:
                UserUpdate(**data)
            assert any(e["loc"] == ("description",) for e in exc_info.value.errors())


# =============================================================================
# RoleCreate Tests
# =============================================================================

class TestRoleCreate:
    @pytest.fixture
    def valid_data(self):
        return {
            "name": "Admin",
            "code": "admin_role_01",
            "is_active": True,
            "description": "Administrator Role"
        }

    def test_happy_path(self, valid_data):
        model = RoleCreate(**valid_data)
        assert model.name == valid_data["name"]
        assert model.code == valid_data["code"]

    @pytest.mark.parametrize("field, invalid_value", [
        ("name", "x" * 256),
        ("name", None),
        ("code", "x" * 256),
        ("code", None),
        ("description", "x" * 256),
    ])
    def test_invalid_values(self, valid_data, field, invalid_value):
        data = valid_data.copy()
        data[field] = invalid_value
        with pytest.raises(ValidationError) as exc_info:
            RoleCreate(**data)
        assert any(e["loc"] == (field,) for e in exc_info.value.errors())

    @pytest.mark.parametrize("field", ["name", "code"])
    def test_missing_fields(self, valid_data, field):
        data = valid_data.copy()
        del data[field]
        with pytest.raises(ValidationError) as exc_info:
            RoleCreate(**data)
        assert exc_info.value.errors()[0]["type"] == "missing"

    def test_field_coverage(self):
        check_field_coverage(RoleCreate, ["name", "code", "is_active", "description"])

    @pytest.mark.parametrize("field, length, should_pass", [
        ("name", 255, True), ("name", 256, False),
        ("code", 255, True), ("code", 256, False),
        ("description", 255, True), ("description", 256, False),
    ])
    def test_bva_fields(self, valid_data, field, length, should_pass):
        data = valid_data.copy()
        data[field] = "x" * length
        if should_pass:
            model = RoleCreate(**data)
            assert len(getattr(model, field)) == length
        else:
            with pytest.raises(ValidationError) as exc_info:
                RoleCreate(**data)
            assert any(e["loc"] == (field,) for e in exc_info.value.errors())

# =============================================================================
# RoleUpdate Tests
# =============================================================================

class TestRoleUpdate:
    @pytest.fixture
    def valid_data(self):
        return {
            "name": "Admin Updated",
            "code": "admin_updated",
            "is_active": False,
            "description": "Updated Role"
        }

    def test_happy_path(self, valid_data):
        model = RoleUpdate(**valid_data)
        assert model.name == valid_data["name"]

    @pytest.mark.parametrize("field, invalid_value", [
        ("name", "x" * 256),
        ("code", "x" * 256),
        ("description", "x" * 256),
    ])
    def test_invalid_values(self, valid_data, field, invalid_value):
        data = valid_data.copy()
        data[field] = invalid_value
        with pytest.raises(ValidationError) as exc_info:
            RoleUpdate(**data)
        assert any(e["loc"] == (field,) for e in exc_info.value.errors())

    def test_field_coverage(self):
        check_field_coverage(RoleUpdate, ["name", "code", "is_active", "description"])

    @pytest.mark.parametrize("field, length, should_pass", [
        ("name", 255, True), ("name", 256, False),
        ("code", 255, True), ("code", 256, False),
        ("description", 255, True), ("description", 256, False),
    ])
    def test_bva_fields(self, valid_data, field, length, should_pass):
        data = valid_data.copy()
        data[field] = "x" * length
        if should_pass:
            model = RoleUpdate(**data)
            assert len(getattr(model, field)) == length
        else:
            with pytest.raises(ValidationError) as exc_info:
                RoleUpdate(**data)
            assert any(e["loc"] == (field,) for e in exc_info.value.errors())


# =============================================================================
# MenuCreate Tests
# =============================================================================

class TestMenuCreate:
    @pytest.fixture
    def valid_data(self):
        return {
            "header_name": "Dashboard",
            "code": "dashboard_menu",
            "icon": "fa-home",
            "sort_order": 1,
            "is_active": True,
            "description": "Main dashboard"
        }

    def test_happy_path(self, valid_data):
        model = MenuCreate(**valid_data)
        assert model.header_name == valid_data["header_name"]

    @pytest.mark.parametrize("field, invalid_value", [
        ("header_name", "x" * 256),
        ("header_name", None),
        ("code", "x" * 256),
        ("code", None),
        ("icon", "x" * 256),
        ("description", "x" * 256),
        ("sort_order", "not-an-int"),
    ])
    def test_invalid_values(self, valid_data, field, invalid_value):
        data = valid_data.copy()
        data[field] = invalid_value
        with pytest.raises(ValidationError) as exc_info:
            MenuCreate(**data)
        assert any(e["loc"] == (field,) for e in exc_info.value.errors())

    @pytest.mark.parametrize("field", ["header_name", "code"])
    def test_missing_fields(self, valid_data, field):
        data = valid_data.copy()
        del data[field]
        with pytest.raises(ValidationError) as exc_info:
            MenuCreate(**data)
        assert exc_info.value.errors()[0]["type"] == "missing"

    def test_field_coverage(self):
        check_field_coverage(MenuCreate, ["header_name", "code", "icon", "sort_order", "is_active", "description"])

    @pytest.mark.parametrize("field, length, should_pass", [
        ("header_name", 255, True), ("header_name", 256, False),
        ("code", 255, True), ("code", 256, False),
        ("icon", 255, True), ("icon", 256, False),
        ("description", 255, True), ("description", 256, False),
    ])
    def test_bva_fields(self, valid_data, field, length, should_pass):
        data = valid_data.copy()
        data[field] = "x" * length
        if should_pass:
            model = MenuCreate(**data)
            val = getattr(model, field)
            assert len(val) == length
        else:
            with pytest.raises(ValidationError) as exc_info:
                MenuCreate(**data)
            assert any(e["loc"] == (field,) for e in exc_info.value.errors())

# =============================================================================
# MenuUpdate Tests
# =============================================================================

class TestMenuUpdate:
    @pytest.fixture
    def valid_data(self):
        return {
            "header_name": "Dashboard Updated",
            "code": "dashboard_updated",
            "icon": "fa-home-alt",
            "sort_order": 2,
            "is_active": False,
            "description": "Updated dashboard"
        }

    def test_happy_path(self, valid_data):
        model = MenuUpdate(**valid_data)
        assert model.header_name == valid_data["header_name"]

    @pytest.mark.parametrize("field, invalid_value", [
        ("header_name", "x" * 256),
        ("code", "x" * 256),
        ("icon", "x" * 256),
        ("description", "x" * 256),
        ("sort_order", "not-an-int"),
    ])
    def test_invalid_values(self, valid_data, field, invalid_value):
        data = valid_data.copy()
        data[field] = invalid_value
        with pytest.raises(ValidationError) as exc_info:
            MenuUpdate(**data)
        assert any(e["loc"] == (field,) for e in exc_info.value.errors())

    def test_field_coverage(self):
        check_field_coverage(MenuUpdate, ["header_name", "code", "icon", "sort_order", "is_active", "description"])

    @pytest.mark.parametrize("field, length, should_pass", [
        ("header_name", 255, True), ("header_name", 256, False),
        ("code", 255, True), ("code", 256, False),
        ("icon", 255, True), ("icon", 256, False),
        ("description", 255, True), ("description", 256, False),
    ])
    def test_bva_fields(self, valid_data, field, length, should_pass):
        data = valid_data.copy()
        data[field] = "x" * length
        if should_pass:
            model = MenuUpdate(**data)
            assert len(getattr(model, field)) == length
        else:
            with pytest.raises(ValidationError) as exc_info:
                MenuUpdate(**data)
            assert any(e["loc"] == (field,) for e in exc_info.value.errors())


# =============================================================================
# SubMenuCreate Tests
# =============================================================================

class TestSubMenuCreate:
    @pytest.fixture
    def valid_data(self):
        return {
            "display_name": "Overview",
            "page_url": "/dashboard/overview",
            "code": "overview_sub_01",
            "menu_id": 10,
            "icon": "fa-chart",
            "sort_order": 5,
            "is_active": True,
            "description": "Dashboard overview page"
        }

    def test_happy_path(self, valid_data):
        model = SubMenuCreate(**valid_data)
        assert model.display_name == valid_data["display_name"]
        assert model.menu_id == valid_data["menu_id"]

    @pytest.mark.parametrize("field, invalid_value", [
        ("display_name", "x" * 256),
        ("display_name", None),
        ("page_url", "x" * 256),
        ("page_url", None),
        ("code", "x" * 256),
        ("code", None),
        ("menu_id", "not-an-int"),
        ("menu_id", None),
        ("icon", "x" * 256),
        ("description", "x" * 256),
        ("sort_order", "not-an-int"),
    ])
    def test_invalid_values(self, valid_data, field, invalid_value):
        data = valid_data.copy()
        data[field] = invalid_value
        with pytest.raises(ValidationError) as exc_info:
            SubMenuCreate(**data)
        assert any(e["loc"] == (field,) for e in exc_info.value.errors())

    @pytest.mark.parametrize("field", ["display_name", "page_url", "code", "menu_id"])
    def test_missing_fields(self, valid_data, field):
        data = valid_data.copy()
        del data[field]
        with pytest.raises(ValidationError) as exc_info:
            SubMenuCreate(**data)
        assert exc_info.value.errors()[0]["type"] == "missing"

    def test_field_coverage(self):
        check_field_coverage(SubMenuCreate, ["display_name", "page_url", "code", "menu_id", "icon", "sort_order", "is_active", "description"])

    @pytest.mark.parametrize("field, length, should_pass", [
        ("display_name", 255, True), ("display_name", 256, False),
        ("page_url", 255, True), ("page_url", 256, False),
        ("code", 255, True), ("code", 256, False),
        ("icon", 255, True), ("icon", 256, False),
        ("description", 255, True), ("description", 256, False),
    ])
    def test_bva_fields(self, valid_data, field, length, should_pass):
        data = valid_data.copy()
        data[field] = "x" * length
        if should_pass:
            model = SubMenuCreate(**data)
            assert len(getattr(model, field)) == length
        else:
            with pytest.raises(ValidationError) as exc_info:
                SubMenuCreate(**data)
            assert any(e["loc"] == (field,) for e in exc_info.value.errors())

# =============================================================================
# SubMenuUpdate Tests
# =============================================================================

class TestSubMenuUpdate:
    @pytest.fixture
    def valid_data(self):
        return {
            "display_name": "Overview Updated",
            "page_url": "/dashboard/overview-updated",
            "code": "overview_updated",
            "menu_id": 11,
            "icon": "fa-chart-alt",
            "sort_order": 6,
            "is_active": False,
            "description": "Updated overview"
        }

    def test_happy_path(self, valid_data):
        model = SubMenuUpdate(**valid_data)
        assert model.display_name == valid_data["display_name"]

    @pytest.mark.parametrize("field, invalid_value", [
        ("display_name", "x" * 256),
        ("page_url", "x" * 256),
        ("code", "x" * 256),
        ("menu_id", "not-an-int"),
        ("icon", "x" * 256),
        ("description", "x" * 256),
        ("sort_order", "not-an-int"),
    ])
    def test_invalid_values(self, valid_data, field, invalid_value):
        data = valid_data.copy()
        data[field] = invalid_value
        with pytest.raises(ValidationError) as exc_info:
            SubMenuUpdate(**data)
        assert any(e["loc"] == (field,) for e in exc_info.value.errors())

    def test_field_coverage(self):
        check_field_coverage(SubMenuUpdate, ["display_name", "page_url", "code", "menu_id", "icon", "sort_order", "is_active", "description"])

    @pytest.mark.parametrize("field, length, should_pass", [
        ("display_name", 255, True), ("display_name", 256, False),
        ("page_url", 255, True), ("page_url", 256, False),
        ("code", 255, True), ("code", 256, False),
        ("icon", 255, True), ("icon", 256, False),
        ("description", 255, True), ("description", 256, False),
    ])
    def test_bva_fields(self, valid_data, field, length, should_pass):
        data = valid_data.copy()
        data[field] = "x" * length
        if should_pass:
            model = SubMenuUpdate(**data)
            assert len(getattr(model, field)) == length
        else:
            with pytest.raises(ValidationError) as exc_info:
                SubMenuUpdate(**data)
            assert any(e["loc"] == (field,) for e in exc_info.value.errors())


# =============================================================================
# RoleSubMenuAccessCreate Tests
# =============================================================================

class TestRoleSubMenuAccessCreate:
    @pytest.fixture
    def valid_data(self):
        return {
            "role_id": 1,
            "sub_menu_id": 2,
            "can_view": True,
            "description": "Access allowed"
        }

    def test_happy_path(self, valid_data):
        model = RoleSubMenuAccessCreate(**valid_data)
        assert model.role_id == valid_data["role_id"]

    @pytest.mark.parametrize("field, invalid_value", [
        ("role_id", "not-an-int"),
        ("role_id", None),
        ("sub_menu_id", "not-an-int"),
        ("sub_menu_id", None),
        ("description", "x" * 256),
    ])
    def test_invalid_values(self, valid_data, field, invalid_value):
        data = valid_data.copy()
        data[field] = invalid_value
        with pytest.raises(ValidationError) as exc_info:
            RoleSubMenuAccessCreate(**data)
        assert any(e["loc"] == (field,) for e in exc_info.value.errors())

    @pytest.mark.parametrize("field", ["role_id", "sub_menu_id"])
    def test_missing_fields(self, valid_data, field):
        data = valid_data.copy()
        del data[field]
        with pytest.raises(ValidationError) as exc_info:
            RoleSubMenuAccessCreate(**data)
        assert exc_info.value.errors()[0]["type"] == "missing"

    def test_field_coverage(self):
        check_field_coverage(RoleSubMenuAccessCreate, ["role_id", "sub_menu_id", "can_view", "description"])

    @pytest.mark.parametrize("length, should_pass", [
        (255, True),
        (256, False),
    ])
    def test_bva_description(self, valid_data, length, should_pass):
        data = valid_data.copy()
        data["description"] = "x" * length
        if should_pass:
            model = RoleSubMenuAccessCreate(**data)
            assert len(model.description) == length
        else:
            with pytest.raises(ValidationError) as exc_info:
                RoleSubMenuAccessCreate(**data)
            assert any(e["loc"] == ("description",) for e in exc_info.value.errors())


# =============================================================================
# RoleSubMenuAccessUpdate Tests
# =============================================================================

class TestRoleSubMenuAccessUpdate:
    @pytest.fixture
    def valid_data(self):
        return {
            "can_view": False,
            "description": "Access revoked"
        }

    def test_happy_path(self, valid_data):
        model = RoleSubMenuAccessUpdate(**valid_data)
        assert model.can_view == valid_data["can_view"]

    @pytest.mark.parametrize("field, invalid_value", [
        ("description", "x" * 256),
    ])
    def test_invalid_values(self, valid_data, field, invalid_value):
        data = valid_data.copy()
        data[field] = invalid_value
        with pytest.raises(ValidationError) as exc_info:
            RoleSubMenuAccessUpdate(**data)
        assert any(e["loc"] == (field,) for e in exc_info.value.errors())

    def test_field_coverage(self):
        check_field_coverage(RoleSubMenuAccessUpdate, ["can_view", "description"])

    @pytest.mark.parametrize("length, should_pass", [
        (255, True),
        (256, False),
    ])
    def test_bva_description(self, valid_data, length, should_pass):
        data = valid_data.copy()
        data["description"] = "x" * length
        if should_pass:
            model = RoleSubMenuAccessUpdate(**data)
            assert len(model.description) == length
        else:
            with pytest.raises(ValidationError) as exc_info:
                RoleSubMenuAccessUpdate(**data)
            assert any(e["loc"] == ("description",) for e in exc_info.value.errors())


# =============================================================================
# EnvironmentCreate Tests
# =============================================================================

class TestEnvironmentCreate:
    @pytest.fixture
    def valid_data(self):
        return {
            "name": "Production",
            "env_code": "PROD",
            "description": "Live environment"
        }

    def test_happy_path(self, valid_data):
        model = EnvironmentCreate(**valid_data)
        assert model.name == valid_data["name"]

    @pytest.mark.parametrize("field, invalid_value", [
        ("name", "x" * 256),
        ("name", None),
        ("env_code", "x" * 65), # Max 64
        ("env_code", None),
        ("description", "x" * 256),
    ])
    def test_invalid_values(self, valid_data, field, invalid_value):
        data = valid_data.copy()
        data[field] = invalid_value
        with pytest.raises(ValidationError) as exc_info:
            EnvironmentCreate(**data)
        assert any(e["loc"] == (field,) for e in exc_info.value.errors())

    @pytest.mark.parametrize("field", ["name", "env_code"])
    def test_missing_fields(self, valid_data, field):
        data = valid_data.copy()
        del data[field]
        with pytest.raises(ValidationError) as exc_info:
            EnvironmentCreate(**data)
        assert exc_info.value.errors()[0]["type"] == "missing"

    def test_field_coverage(self):
        check_field_coverage(EnvironmentCreate, ["name", "env_code", "description"])

    @pytest.mark.parametrize("field, length, should_pass", [
        ("name", 255, True), ("name", 256, False),
        ("env_code", 64, True), ("env_code", 65, False),
        ("description", 255, True), ("description", 256, False),
    ])
    def test_bva_fields(self, valid_data, field, length, should_pass):
        data = valid_data.copy()
        data[field] = "x" * length
        if should_pass:
            model = EnvironmentCreate(**data)
            assert len(getattr(model, field)) == length
        else:
            with pytest.raises(ValidationError) as exc_info:
                EnvironmentCreate(**data)
            assert any(e["loc"] == (field,) for e in exc_info.value.errors())

# =============================================================================
# EnvironmentUpdate Tests
# =============================================================================

class TestEnvironmentUpdate:
    @pytest.fixture
    def valid_data(self):
        return {
            "name": "Production Updated",
            "env_code": "PROD2",
            "description": "Live environment updated"
        }

    def test_happy_path(self, valid_data):
        model = EnvironmentUpdate(**valid_data)
        assert model.name == valid_data["name"]

    @pytest.mark.parametrize("field, invalid_value", [
        ("name", "x" * 256),
        ("env_code", "x" * 65),
        ("description", "x" * 256),
    ])
    def test_invalid_values(self, valid_data, field, invalid_value):
        data = valid_data.copy()
        data[field] = invalid_value
        with pytest.raises(ValidationError) as exc_info:
            EnvironmentUpdate(**data)
        assert any(e["loc"] == (field,) for e in exc_info.value.errors())

    def test_field_coverage(self):
        check_field_coverage(EnvironmentUpdate, ["name", "env_code", "description"])

    @pytest.mark.parametrize("field, length, should_pass", [
        ("name", 255, True), ("name", 256, False),
        ("env_code", 64, True), ("env_code", 65, False),
        ("description", 255, True), ("description", 256, False),
    ])
    def test_bva_fields(self, valid_data, field, length, should_pass):
        data = valid_data.copy()
        data[field] = "x" * length
        if should_pass:
            model = EnvironmentUpdate(**data)
            assert len(getattr(model, field)) == length
        else:
            with pytest.raises(ValidationError) as exc_info:
                EnvironmentUpdate(**data)
            assert any(e["loc"] == (field,) for e in exc_info.value.errors())
