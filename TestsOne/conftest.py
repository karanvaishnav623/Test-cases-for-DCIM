# tests/conftest.py
"""
Shared pytest fixtures and configuration for all test types.

Test Structure:
├── unit/           - Pure function tests (no DB, no HTTP)
├── integration/    - API endpoint tests with mocked DB
└── e2e/            - End-to-end tests with real DB (optional)
"""

import pytest


# ============================================================
# Shared Dummy Classes (used across multiple test files)
# ============================================================

class DummyRole:
    """Mock Role object for testing."""
    def __init__(self, code: str | None, is_active: bool = True) -> None:
        self.code = code
        self.is_active = is_active


class DummyUserRole:
    """Mock UserRole object for testing."""
    def __init__(self, role: DummyRole | None) -> None:
        self.role = role


class DummyUser:
    """Mock User object for testing."""
    def __init__(
        self,
        *,
        user_id: int = 1,
        name: str = "testuser",
        email: str = "test@example.com",
        is_active: bool = True,
        roles: list[DummyUserRole] | None = None,
    ) -> None:
        self.id = user_id
        self.name = name
        self.email = email
        self.is_active = is_active
        self.user_roles = roles or []


class DummyAccessLevel:
    """Mock AccessLevel for RBAC testing."""
    def __init__(self, value: str = "viewer") -> None:
        self.value = value


class DummyDB:
    """Mock database session for testing."""
    def __init__(self) -> None:
        self.commits = 0
        self.rollbacks = 0
        self._added = []

    def add(self, instance):
        self._added.append(instance)

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1

    def close(self):
        pass

    def refresh(self, instance):
        pass


# ============================================================
# Pytest Configuration
# ============================================================

def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line("markers", "unit: Unit tests (fast, no external deps)")
    config.addinivalue_line("markers", "integration: Integration tests (mocked DB)")
    config.addinivalue_line("markers", "e2e: End-to-end tests (real DB required)")
    config.addinivalue_line("markers", "slow: Slow running tests")


# ============================================================
# Shared Fixtures
# ============================================================

@pytest.fixture
def dummy_user():
    """Provide a basic DummyUser instance."""
    return DummyUser()


@pytest.fixture
def dummy_admin_user():
    """Provide an admin user with ADMIN role."""
    admin_role = DummyRole("ADMIN", is_active=True)
    return DummyUser(
        user_id=1,
        name="admin",
        email="admin@example.com",
        roles=[DummyUserRole(admin_role)]
    )


@pytest.fixture
def dummy_db():
    """Provide a mock database session."""
    return DummyDB()

