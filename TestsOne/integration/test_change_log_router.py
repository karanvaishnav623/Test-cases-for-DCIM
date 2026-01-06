import pytest
from fastapi import status
from fastapi.testclient import TestClient

from app.main import app
from app.db.session import get_db
from app.helpers.rbac_helper import require_at_least_viewer


class DummyAccessLevel:
    def __init__(self, value: str = "viewer") -> None:
        self.value = value


@pytest.fixture
def client(monkeypatch):
    """
    TestClient for /api/dcim/change-logs* routes with DB and RBAC stubbed.
    """
    from app.models import auth_models

    class DummyAuditLog:
        def __init__(self, log_id: int = 1) -> None:
            self.id = log_id
            self.time = None
            self.action = "create"
            self.type = "locations"
            self.object_id = 1
            self.message = "created"
            self.user = None

    class DummyQuery:
        def __init__(self, result_list=None, count_value: int = 1):
            self._list = result_list or [DummyAuditLog()]
            self._count = count_value

        def filter(self, *_, **__):
            return self

        def order_by(self, *_, **__):
            return self

        def offset(self, *_):
            return self

        def limit(self, *_):
            return self

        def all(self):
            return self._list

        def first(self):
            return self._list[0] if self._list else None

        def count(self):
            return self._count

        def options(self, *_):
            return self

    # Disable DB prewarm during app lifespan to avoid requiring real DB_URL
    import app.main as main_module

    async def _noop_prewarm(app_logger):  # type: ignore[unused-argument]
        return None

    main_module._prewarm_database = _noop_prewarm  # type: ignore[assignment]

    class DummyDB:
        def __init__(self) -> None:
            pass

        def query(self, model):
            if model is auth_models.AuditLog:
                return DummyQuery()
            if model is auth_models.User:
                # simulate user not found in username filtering tests by default
                return DummyQuery(result_list=[], count_value=0)
            return DummyQuery()

    dummy_db = DummyDB()

    def _override_get_db():
        yield dummy_db

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[require_at_least_viewer] = lambda: DummyAccessLevel(
        "viewer"
    )

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()


def test_get_change_logs_basic_success(client):
    response = client.get("/api/dcim/change-logs")

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["total"] == 1
    assert body["page"] == 1
    assert isinstance(body["data"], list)


def test_get_change_log_by_id_not_found_returns_placeholder(monkeypatch):
    """
    When log is missing, router returns a structured error payload with data None.
    """
    from app.models import auth_models

    class EmptyQuery:
        def options(self, *_):
            return self

        def filter(self, *_, **__):
            return self

        def first(self):
            return None

    class DummyDB:
        def query(self, model):
            if model is auth_models.AuditLog:
                return EmptyQuery()
            return EmptyQuery()

    def _override_get_db():
        yield DummyDB()

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[require_at_least_viewer] = lambda: DummyAccessLevel(
        "viewer"
    )

    with TestClient(app) as client:
        response = client.get("/api/dcim/change-logs/999")

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["error"] == "Audit log entry not found"
    assert body["data"] is None

    app.dependency_overrides.clear()


