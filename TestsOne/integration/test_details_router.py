import pytest
from fastapi import status
from fastapi.testclient import TestClient

from app.main import app
from app.db.session import get_db
from app.helpers.rbac_helper import require_at_least_viewer


from app.helpers.auth_helper import get_current_user

class DummyLocationAccess:
    def __init__(self, location_id: int = 1):
        self.location_id = location_id

class DummyUser:
    def __init__(self, user_id: int = 1) -> None:
        self.id = user_id
        self.location_accesses = [DummyLocationAccess(1)]

class DummyAccessLevel:
    def __init__(self, value: str = "viewer") -> None:
        self.value = value


@pytest.fixture
def client(monkeypatch):
    """
    TestClient for /api/dcim/details with RBAC and DB dependencies stubbed.
    """
    from app.helpers import details_helper
    from app.helpers import listing_types

    # Disable DB prewarm during app lifespan to avoid requiring real DATABASE_URL
    import app.main as main_module

    async def _noop_prewarm(app_logger):  # type: ignore[unused-argument]
        return None

    main_module._prewarm_database = _noop_prewarm  # type: ignore[assignment]

    class DummyDB:
        def __init__(self) -> None:
            self.calls = []

    dummy_db = DummyDB()

    def _override_get_db():
        yield dummy_db

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[require_at_least_viewer] = lambda: DummyAccessLevel(
        "viewer"
    )
    app.dependency_overrides[get_current_user] = lambda: DummyUser(1)

    def handler(db, name: str):
        return {"name": name, "info": "details"}

    monkeypatch.setattr(
        details_helper,
        "ENTITY_DETAIL_HANDLERS",
        {listing_types.ListingType.devices: handler},
    )

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()


def test_get_entity_details_success(client):
    params = {"entity": "devices", "name": "device-1"}

    response = client.get("/api/dcim/details", params=params)

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["entity"] == "devices"
    assert data["data"]["name"] == "device-1"
    assert data["data"]["info"] == "details"


def test_get_entity_details_unsupported_entity_returns_400(client, monkeypatch):
    from app.helpers import details_helper

    monkeypatch.setattr(details_helper, "ENTITY_DETAIL_HANDLERS", {})

    response = client.get(
        "/api/dcim/details",
        params={"entity": "devices", "name": "d1"},
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "unsupported entity type" in response.json()["detail"].lower()


