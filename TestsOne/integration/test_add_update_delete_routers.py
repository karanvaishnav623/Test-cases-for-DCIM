import pytest
from fastapi import status
from fastapi.testclient import TestClient

from app.main import app
from app.db.session import get_db
from app.helpers.auth_helper import get_current_user
from app.helpers.rbac_helper import require_editor_or_admin, require_admin


class DummyAccessLevel:
    def __init__(self, value: str = "editor") -> None:
        self.value = value


class DummyAdminAccess(DummyAccessLevel):
    def __init__(self) -> None:
        super().__init__("admin")


class DummyLocationAccess:
    def __init__(self, location_id: int = 1):
        self.location_id = location_id

class DummyUser:
    def __init__(self, user_id: int = 1) -> None:
        self.id = user_id
        self.name = "tester"
        self.email = "tester@example.com"
        self.is_active = True
        self.created_at = None
        from datetime import datetime
        self.created_at = datetime.utcnow()
        self.location_accesses = [DummyLocationAccess(1)]


@pytest.fixture
def client(monkeypatch):
    """
    TestClient for /api/dcim/add, /api/dcim/update, /api/dcim/delete with
    DB/auth/RBAC/audit/listing helpers stubbed.
    """
    from app.helpers import audit_helper
    from app.helpers import listing_cache
    from app.helpers import summary_cache
    from app.helpers import add_entity_helper
    from app.helpers import update_entity_helper
    from app.helpers import delete_entity_helper
    from app.helpers import listing_types
    from app.schemas import entity_schemas

    # Disable DB prewarm during app lifespan to avoid requiring real DATABASE_URL
    import app.main as main_module

    async def _noop_prewarm(app_logger):  # type: ignore[unused-argument]
        return None

    main_module._prewarm_database = _noop_prewarm  # type: ignore[assignment]

    class DummyDB:
        def __init__(self) -> None:
            self.commits = 0
            self.rollbacks = 0

        def commit(self):
            self.commits += 1

        def rollback(self):
            self.rollbacks += 1

        def close(self):
            pass

    dummy_db = DummyDB()

    def _override_get_db():
        try:
            yield dummy_db
        finally:
            dummy_db.close()

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_user] = lambda: DummyUser(1)
    app.dependency_overrides[require_editor_or_admin] = lambda: DummyAccessLevel(
        "editor"
    )
    app.dependency_overrides[require_admin] = lambda: DummyAdminAccess()

    # Minimal audit helper stubs
    class DummyAuditEntry:
        def __init__(self, entry_id: int = 1) -> None:
            self.id = entry_id

    monkeypatch.setattr(
        audit_helper, "build_audit_context", lambda **_: {"ctx": "dummy"}
    )
    monkeypatch.setattr(
        audit_helper,
        "log_create",
        lambda **_: DummyAuditEntry(1),
    )
    monkeypatch.setattr(
        audit_helper,
        "log_update",
        lambda **_: DummyAuditEntry(2),
    )
    monkeypatch.setattr(
        audit_helper,
        "log_delete",
        lambda **_: DummyAuditEntry(3),
    )

    # Invalidate cache no-ops
    monkeypatch.setattr(
        listing_cache, "invalidate_listing_cache_for_entity", lambda *_, **__: None
    )
    monkeypatch.setattr(
        summary_cache, "invalidate_location_summary_cache", lambda *_, **__: None
    )

    # Provide simple create/update/delete handlers and schemas
    def create_location(db, data):
        return {"id": 1, **data}

    def update_location(db, name, data):
        return {"id": 1, "name": name, **data}

    def delete_location(db, name):
        return {"id": 1, "name": name}

    monkeypatch.setattr(
        add_entity_helper,
        "ENTITY_CREATE_HANDLERS",
        {listing_types.ListingType.locations: create_location},
    )
    monkeypatch.setattr(
        update_entity_helper,
        "ENTITY_UPDATE_HANDLERS",
        {listing_types.ListingType.locations: update_location},
    )
    monkeypatch.setattr(
        delete_entity_helper,
        "ENTITY_DELETE_HANDLERS",
        {listing_types.ListingType.locations: delete_location},
    )

    # Minimal schemas for locations create/update
    from pydantic import BaseModel

    class LocationCreate(BaseModel):
        name: str
        description: str

    class LocationUpdate(BaseModel):
        description: str | None = None

    monkeypatch.setattr(
        entity_schemas,
        "ENTITY_CREATE_SCHEMAS",
        {listing_types.ListingType.locations: LocationCreate},
    )
    monkeypatch.setattr(
        entity_schemas,
        "ENTITY_UPDATE_SCHEMAS",
        {listing_types.ListingType.locations: LocationUpdate},
    )

    listing_cache.listing_cache.invalidate_all()
    
    # Manually include routers to avoid deferred loading race condition in tests
    from app.dcim.routers import add_router, update_router, delete_router
    app.include_router(add_router.router)
    app.include_router(update_router.router)
    app.include_router(delete_router.router)

    # Use TestClient as context manager to trigger startup events
    with TestClient(app) as c:
        yield c
    
    app.dependency_overrides.clear()


def test_add_entity_location_success(client):
    payload = {
        "name": "Loc1",
        "description": "Test Location",
    }

    response = client.post(
        "/api/dcim/add",
        params={"entity": "locations"},
        json=payload,
    )

    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["entity"] == "locations"
    assert data["data"]["name"] == "Loc1"


def test_update_entity_location_success(client):
    payload = {"description": "Updated"}

    # Use ID '1' as expected by the endpoint
    response = client.put(
        "/api/dcim/update/1",
        params={"entity": "locations"},
        json=payload,
    )

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["entity"] == "locations"
    assert body["data"]["id"] == 1


def test_delete_entity_location_success(client):
    # Use ID '1' as expected by the endpoint
    response = client.delete(
        "/api/dcim/delete/1",
        params={"entity": "locations"},
    )

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["entity"] == "locations"
    assert body["data"]["id"] == 1
