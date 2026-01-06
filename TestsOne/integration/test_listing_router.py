from datetime import date

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from app.main import app
from app.db.session import get_db
from app.helpers.auth_helper import get_current_user
from app.helpers.rbac_helper import require_at_least_viewer


class DummyLocationAccess:
    def __init__(self, location_id: int = 1):
        self.location_id = location_id

class DummyUser:
    def __init__(self, user_id: int = 1) -> None:
        self.id = user_id
        self.location_accesses = [DummyLocationAccess(1)]


class DummyAccessLevel:
    # Simulate AccessLevel enum instance having a .value attribute
    def __init__(self, value: str = "viewer") -> None:
        self.value = value


class DummyListingHandler:
    def __init__(self, total: int = 1, data=None):
        self.total = total
        self.data = data or [{"id": 1, "name": "dummy"}]

    def __call__(self, db, offset: int, page_size: int, **filters):
        # Return predictable totals and data for assertions
        return self.total, self.data


@pytest.fixture
def client(monkeypatch):
    """
    Provide a TestClient with DB and auth/RBAC dependencies overridden so the
    /api/dcim/list endpoint can be exercised without real DB or JWT.
    Uses FastAPI's dependency_overrides and runs lifespan.
    """
    from app.helpers import listing_helper
    from app.helpers import listing_cache
    from app.helpers import listing_types

    # Disable DB prewarm during app lifespan to avoid requiring real DB_URL
    import app.main as main_module

    async def _noop_prewarm(app_logger):  # type: ignore[unused-argument]
        return None

    main_module._prewarm_database = _noop_prewarm  # type: ignore[assignment]

    class DummyDB:
        def __init__(self) -> None:
            self.queries = []

    dummy_db = DummyDB()

    def _override_get_db():
        yield dummy_db

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_user] = lambda: DummyUser(1)
    app.dependency_overrides[require_at_least_viewer] = lambda: DummyAccessLevel(
        "viewer"
    )

    handler = DummyListingHandler()
    monkeypatch.setattr(
        listing_helper,
        "ENTITY_LIST_HANDLERS",
        {listing_types.ListingType.locations: handler},
    )

    listing_cache.listing_cache.invalidate_all()

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()


def test_list_dcim_entities_basic_success(client):
    params = {
        "entity": "locations",
        "offset": 0,
        "page_size": 10,
    }

    response = client.get("/api/dcim/list", params=params)

    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    assert data["entity"] == "locations"
    assert data["offset"] == 0
    assert data["limit"] == 10
    assert data["total"] == 1
    assert isinstance(data["results"], list)
    assert data["results"][0]["name"] == "dummy"


def test_list_dcim_entities_unsupported_entity_returns_400(client, monkeypatch):
    # Override handlers to return empty dict so entity is unsupported
    from app.helpers import listing_helper

    monkeypatch.setattr(listing_helper, "ENTITY_LIST_HANDLERS", {})

    response = client.get(
        "/api/dcim/list",
        params={"entity": "locations"},
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "unsupported entity type" in response.json()["detail"].lower()


def test_list_dcim_entities_normalizes_and_parses_filters(client):
    # Using a short page size and various typed filters to ensure parsing
    params = {
        "entity": "locations",
        "rack_height": "42",
        "device_position": "5",
        "model_height": "2",
        "warranty_start_date": "2025-01-01",
        "warranty_end_date": "",
        "amc_start_date": "",
        "amc_end_date": "2025-12-31",
        "location_name": "",
        "rack_name": " R1 ",
    }

    response = client.get("/api/dcim/list", params=params)

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    # Core contract is still respected
    assert body["entity"] == "locations"
    assert "results" in body


