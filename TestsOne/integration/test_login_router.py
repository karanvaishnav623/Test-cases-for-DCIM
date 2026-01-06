from datetime import datetime

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from app.main import app
from app.db.session import get_db


class DummyQuery:
    def __init__(self, result):
        self._result = result

    def filter(self, *_, **__):
        return self

    def get(self, *_, **__):
        return self._result

    def first(self):
        return self._result

    def delete(self):
        # No-op for tests
        return 0

    def join(self, *_, **__):
        return self

    def order_by(self, *_, **__):
        return self

    def all(self):
        return []


class DummyDBSession:
    def __init__(self, user=None, token=None) -> None:
        self._user = user
        self._token = token
        self._added = []

    # SQLAlchemy-like API used in login_router
    def query(self, *args):
        if len(args) == 1:
            model = args[0]
            if getattr(model, "__name__", "") == "User":
                return DummyQuery(self._user)
            if getattr(model, "__name__", "") == "Token":
                return DummyQuery(self._token)
        return DummyQuery(None)

    def add(self, instance):
        self._added.append(instance)

    def commit(self):
        # no-op
        pass

    def refresh(self, instance):
        # no-op for tests
        pass


class DummyRole:
    def __init__(self, code="ADMIN", is_active=True):
        self.code = code
        self.is_active = is_active


class DummyUserRole:
    def __init__(self, role):
        self.role = role


class DummyUser:
    def __init__(self, name="admin", is_active=True):
        self.id = 1
        self.name = name
        self.created_at = datetime.utcnow()
        self.email = "admin@example.com"
        self.is_active = is_active
        self.user_roles = [DummyUserRole(DummyRole("ADMIN", True))]
        self.last_login: datetime | None = None


@pytest.fixture
def client():
    """
    Provide a TestClient with the get_db dependency overridden via FastAPI's
    dependency_overrides so we don't touch the real database during tests.
    Routers are loaded during lifespan, so we use TestClient as a context
    manager.
    """
    # Disable DB prewarm during app lifespan to avoid requiring real DB_URL
    import app.main as main_module

    async def _noop_prewarm(app_logger):  # type: ignore[unused-argument]
        return None

    main_module._prewarm_database = _noop_prewarm  # type: ignore[assignment]

    dummy_user = DummyUser()
    dummy_db = DummyDBSession(user=dummy_user)

    def _override_get_db():
        yield dummy_db

    app.dependency_overrides[get_db] = _override_get_db

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()


def test_login_success_returns_tokens_and_user(client):
    payload = {"username": "admin", "password": "secret"}

    response = client.post("/api/dcim/login", json=payload)

    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    assert "access_token" in data and data["access_token"]
    assert "refresh_token" in data and data["refresh_token"]
    assert "user" in data
    assert data["user"]["name"] == "admin"
    # Configure flags should be present
    assert data["configure"]["is_editable"] is True
    assert data["configure"]["is_deletable"] is True
    assert data["configure"]["is_viewer"] is True


def test_login_invalid_user_returns_401():
    dummy_db = DummyDBSession(user=None)

    def _override_get_db():
        yield dummy_db

    app.dependency_overrides[get_db] = _override_get_db

    with TestClient(app) as client:
        response = client.post(
        "/api/dcim/login",
        json={"username": "unknown", "password": "secret"},
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert "invalid username or password" in response.json()["detail"].lower()

    app.dependency_overrides.clear()


