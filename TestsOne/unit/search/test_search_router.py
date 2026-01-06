"""Unit tests for search_router.py (global DCIM search).

We focus on:
- Helper search functions (_search_locations, _search_buildings, ...):
  - Positive: return mapped dicts when DB returns rows
  - Edge/negative: respect allowed_location_ids filters (where applicable)
- global_search():
  - Negative: rejects empty/whitespace query with 400
  - Positive: calls underlying helpers and aggregates counts/total correctly
"""

from typing import Any, Dict, List, Optional, Set
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from app.dcim.routers.search_router import (
    _search_locations,
    _search_buildings,
    _search_racks,
    _search_devices,
    _search_device_types,
    _search_makes,
    _search_models,
    _search_datacenters,
    _search_asset_owners,
    _search_applications,
    global_search,
)


# Simple dummy user/access objects used when calling global_search directly
class DummyUser:
    def __init__(self, user_id: int = 1) -> None:
        self.id = user_id


class DummyAccessLevel:
    def __init__(self, value: str = "viewer") -> None:
        self.value = value


# ============================================================
# Helper to create a mock query chain
# ============================================================


def _mock_query_single_model(return_rows: List[Any]):
    """Create a MagicMock db where db.query(...).all() returns given rows."""
    db = MagicMock()
    q = MagicMock()
    db.query.return_value = q
    # Chain filters/order/limit to return same mock
    q.filter.return_value = q
    q.order_by.return_value = q
    q.limit.return_value = q
    q.all.return_value = return_rows
    return db, q


# ============================================================
# Tests for _search_locations
# ============================================================


class TestSearchLocations:
    def test_search_locations_returns_mapped_results(self):
        """Positive: returns list of dicts with expected keys."""
        class DummyLoc:
            def __init__(self, id, name, description):
                self.id = id
                self.name = name
                self.description = description

        loc = DummyLoc(1, "Loc1", "Test location")
        db, _ = _mock_query_single_model([loc])

        results = _search_locations(db, search_term="loc", limit=5, allowed_location_ids=None)

        assert isinstance(results, list)
        assert results[0]["id"] == 1
        assert results[0]["name"] == "Loc1"
        assert results[0]["description"] == "Test location"
        assert results[0]["type"] == "location"

    def test_search_locations_applies_allowed_location_filter(self):
        """Edge: when allowed_location_ids provided, IN filter is added."""
        db = MagicMock()
        q = MagicMock()
        db.query.return_value = q
        q.filter.return_value = q
        q.order_by.return_value = q
        q.limit.return_value = q
        q.all.return_value = []

        allowed_ids = {1, 2}
        _search_locations(db, search_term="x", limit=5, allowed_location_ids=allowed_ids)

        # Expect final filter to be called with Location.id.in_(allowed_ids)
        assert q.filter.call_count >= 2  # base conditions + allowed_ids filter


# ============================================================
# Tests for a couple of other helper search functions
# (we don't deeply test SQL, just mapping and that they run)
# ============================================================


class TestSearchBuildings:
    def test_search_buildings_returns_mapped_results(self):
        """Positive: buildings search maps tuples to dicts."""
        class DummyBldg:
            def __init__(self, id, name, status, description, address):
                self.id = id
                self.name = name
                self.status = status
                self.description = description
                self.address = address

        class DummyLoc:
            def __init__(self, name):
                self.name = name

        building = DummyBldg(1, "B1", "ACTIVE", "Test", "Address 1")
        location = DummyLoc("Loc1")

        db, q = _mock_query_single_model([(building, location)])
        # Need join() for this helper
        q.join.return_value = q

        results = _search_buildings(db, search_term="b1", limit=5, allowed_location_ids=None)

        assert results[0]["id"] == 1
        assert results[0]["name"] == "B1"
        assert results[0]["status"] == "ACTIVE"
        assert results[0]["location"] == "Loc1"
        assert results[0]["type"] == "building"

    def test_search_buildings_applies_allowed_location_filter(self):
        """Edge: when allowed_location_ids provided, IN filter is added."""
        db = MagicMock()
        q = MagicMock()
        db.query.return_value = q
        q.join.return_value = q
        q.filter.return_value = q
        q.order_by.return_value = q
        q.limit.return_value = q
        q.all.return_value = []

        allowed_ids = {1, 2}
        _search_buildings(db, search_term="x", limit=5, allowed_location_ids=allowed_ids)

        # Expect filters: base OR condition + allowed_ids filter
        assert q.filter.call_count >= 2


class TestSearchRacks:
    def test_search_racks_returns_mapped_results(self):
        """Positive: racks search maps (Rack, Location, Building) to dict."""
        class Dummy:
            def __init__(self, **kwargs):
                self.__dict__.update(kwargs)

        rack = Dummy(id=1, name="R1", status="ACTIVE", description="d", height=42)
        loc = Dummy(name="Loc1")
        bldg = Dummy(name="B1")

        db, q = _mock_query_single_model([(rack, loc, bldg)])
        q.join.return_value = q

        results = _search_racks(db, search_term="r1", limit=5, allowed_location_ids=None)

        assert results[0]["id"] == 1
        assert results[0]["name"] == "R1"
        assert results[0]["status"] == "ACTIVE"
        assert results[0]["description"] == "d"
        assert results[0]["location"] == "Loc1"
        assert results[0]["building"] == "B1"
        assert results[0]["height"] == 42
        assert results[0]["type"] == "rack"

    def test_search_racks_applies_allowed_location_filter(self):
        """Negative/edge: ensure allowed_location_ids further restricts the query."""
        db = MagicMock()
        q = MagicMock()
        db.query.return_value = q
        q.join.return_value = q
        q.filter.return_value = q
        q.order_by.return_value = q
        q.limit.return_value = q
        q.all.return_value = []

        allowed_ids = {1, 2}
        _search_racks(db, search_term="x", limit=5, allowed_location_ids=allowed_ids)

        # There should be at least one filter call using Rack.location_id.in_(allowed_ids)
        assert q.filter.call_count >= 2


class TestSearchDevices:
    def test_search_devices_returns_mapped_results(self):
        """Positive: devices search returns dicts with key fields."""
        class Dummy:
            def __init__(self, **kwargs):
                self.__dict__.update(kwargs)

        device = Dummy(
            id=1,
            name="Dev1",
            status="ACTIVE",
            description="test",
            serial_no="SN1",
            ip="1.1.1.1",
            po_number="PO1",
            asset_user="user1",
            position=1,
        )
        location = Dummy(name="Loc1")
        building = Dummy(name="B1")
        rack = Dummy(name="R1")
        make = Dummy(name="Make1")
        device_type = Dummy(name="Type1")
        application = Dummy(name="App1")
        asset_owner = Dummy(name="Owner1")

        db, q = _mock_query_single_model(
            [(device, location, building, rack, make, device_type, application, asset_owner)]
        )
        q.outerjoin.return_value = q

        results = _search_devices(db, search_term="dev1", limit=5, allowed_location_ids=None)

        assert results[0]["id"] == 1
        assert results[0]["name"] == "Dev1"
        assert results[0]["location"] == "Loc1"
        assert results[0]["building"] == "B1"
        assert results[0]["rack"] == "R1"
        assert results[0]["make"] == "Make1"
        assert results[0]["device_type"] == "Type1"
        assert results[0]["application"] == "App1"
        assert results[0]["asset_owner"] == "Owner1"
        assert results[0]["type"] == "device"

    def test_search_devices_applies_allowed_location_filter(self):
        """Edge: when allowed_location_ids provided, IN filter is added."""
        db = MagicMock()
        q = MagicMock()
        db.query.return_value = q
        q.outerjoin.return_value = q
        q.filter.return_value = q
        q.order_by.return_value = q
        q.limit.return_value = q
        q.all.return_value = []

        allowed_ids = {1, 2}
        _search_devices(db, search_term="x", limit=5, allowed_location_ids=allowed_ids)

        assert q.filter.call_count >= 2


# ============================================================
# Tests for remaining helper functions
# ============================================================


class TestSearchDeviceTypes:
    def test_search_device_types_returns_mapped_results(self):
        """Positive: device_types search maps tuples to dicts."""
        class Dummy:
            def __init__(self, **kwargs):
                self.__dict__.update(kwargs)

        device_type = Dummy(id=1, name="DT1", description="desc")
        make = Dummy(name="Make1")

        db, q = _mock_query_single_model([(device_type, make)])
        q.outerjoin.return_value = q

        results = _search_device_types(db, search_term="dt1", limit=5)
        assert results[0]["id"] == 1
        assert results[0]["name"] == "DT1"
        assert results[0]["description"] == "desc"
        assert results[0]["make"] == "Make1"
        assert results[0]["type"] == "device_type"

    def test_search_device_types_no_results(self):
        """Negative: returns empty list when no matches."""
        db, _ = _mock_query_single_model([])
        results = _search_device_types(db, search_term="nada", limit=5)
        assert results == []


class TestSearchMakes:
    def test_search_makes_returns_mapped_results(self):
        """Positive: makes search returns dicts with basic fields."""
        class Dummy:
            def __init__(self, **kwargs):
                self.__dict__.update(kwargs)

        make = Dummy(id=1, name="Make1", description="desc")
        db, _ = _mock_query_single_model([make])

        results = _search_makes(db, search_term="make1", limit=5)
        assert results[0]["id"] == 1
        assert results[0]["name"] == "Make1"
        assert results[0]["description"] == "desc"
        assert results[0]["type"] == "make"

    def test_search_makes_no_results(self):
        """Negative: returns empty list when no matches."""
        db, _ = _mock_query_single_model([])
        results = _search_makes(db, search_term="nada", limit=5)
        assert results == []


class TestSearchModels:
    def test_search_models_returns_mapped_results(self):
        """Positive: models search maps (Model, Make, DeviceType) to dict."""
        class Dummy:
            def __init__(self, **kwargs):
                self.__dict__.update(kwargs)

        model = Dummy(id=1, name="M1", description="d", height=2)
        make = Dummy(name="Make1")
        device_type = Dummy(name="DT1")

        db, q = _mock_query_single_model([(model, make, device_type)])
        q.join.return_value = q

        results = _search_models(db, search_term="m1", limit=5)
        assert results[0]["id"] == 1
        assert results[0]["name"] == "M1"
        assert results[0]["height"] == 2
        assert results[0]["make"] == "Make1"
        assert results[0]["device_type"] == "DT1"
        assert results[0]["type"] == "model"

    def test_search_models_no_results(self):
        """Negative: returns empty list when no matches."""
        db, _ = _mock_query_single_model([])
        results = _search_models(db, search_term="nada", limit=5)
        assert results == []


class TestSearchDatacenters:
    def test_search_datacenters_returns_mapped_results(self):
        """Positive: datacenters search maps (Datacenter, Location, Building)."""
        class Dummy:
            def __init__(self, **kwargs):
                self.__dict__.update(kwargs)

        dc = Dummy(id=1, name="DC1", description="d")
        loc = Dummy(name="Loc1")
        bldg = Dummy(name="B1")

        db, q = _mock_query_single_model([(dc, loc, bldg)])
        q.join.return_value = q

        results = _search_datacenters(db, search_term="dc1", limit=5, allowed_location_ids=None)
        assert results[0]["id"] == 1
        assert results[0]["name"] == "DC1"
        assert results[0]["location"] == "Loc1"
        assert results[0]["building"] == "B1"
        assert results[0]["type"] == "datacenter"

    def test_search_datacenters_applies_allowed_location_filter(self):
        """Edge: when allowed_location_ids provided, IN filter is added."""
        db = MagicMock()
        q = MagicMock()
        db.query.return_value = q
        q.join.return_value = q
        q.filter.return_value = q
        q.order_by.return_value = q
        q.limit.return_value = q
        q.all.return_value = []

        allowed_ids = {1, 2}
        _search_datacenters(db, search_term="x", limit=5, allowed_location_ids=allowed_ids)

        assert q.filter.call_count >= 2


class TestSearchAssetOwners:
    def test_search_asset_owners_returns_mapped_results(self):
        """Positive: asset_owners search maps (AssetOwner, Location)."""
        class Dummy:
            def __init__(self, **kwargs):
                self.__dict__.update(kwargs)

        owner = Dummy(id=1, name="Owner1", description="d")
        loc = Dummy(name="Loc1")

        db, q = _mock_query_single_model([(owner, loc)])
        q.outerjoin.return_value = q

        results = _search_asset_owners(db, search_term="owner1", limit=5, allowed_location_ids=None)
        assert results[0]["id"] == 1
        assert results[0]["name"] == "Owner1"
        assert results[0]["location"] == "Loc1"
        assert results[0]["type"] == "asset_owner"

    def test_search_asset_owners_applies_allowed_location_filter(self):
        """Edge: when allowed_location_ids provided, IN filter is added."""
        db = MagicMock()
        q = MagicMock()
        db.query.return_value = q
        q.outerjoin.return_value = q
        q.filter.return_value = q
        q.order_by.return_value = q
        q.limit.return_value = q
        q.all.return_value = []

        allowed_ids = {1, 2}
        _search_asset_owners(db, search_term="x", limit=5, allowed_location_ids=allowed_ids)

        assert q.filter.call_count >= 2


class TestSearchApplications:
    def test_search_applications_returns_mapped_results(self):
        """Positive: applications search maps (Application, AssetOwner)."""
        class Dummy:
            def __init__(self, **kwargs):
                self.__dict__.update(kwargs)

        app = Dummy(id=1, name="App1", description="d")
        owner = Dummy(name="Owner1")

        db, q = _mock_query_single_model([(app, owner)])
        q.outerjoin.return_value = q

        results = _search_applications(db, search_term="app1", limit=5)
        assert results[0]["id"] == 1
        assert results[0]["name"] == "App1"
        assert results[0]["asset_owner"] == "Owner1"
        assert results[0]["type"] == "application"

    def test_search_applications_no_results(self):
        """Negative: returns empty list when no matches."""
        db, _ = _mock_query_single_model([])
        results = _search_applications(db, search_term="nada", limit=5)
        assert results == []


# ============================================================
# Tests for global_search
# ============================================================


class TestGlobalSearch:
    def test_rejects_empty_query_with_400(self):
        """Negative: empty/whitespace q should raise 400."""
        db = MagicMock()
        access_level = DummyAccessLevel()
        user = DummyUser()

        with pytest.raises(HTTPException) as exc_info:
            global_search(
                q="   ",
                limit_per_type=10,
                access_level=access_level,
                db=db,
                current_user=user,
            )
        assert exc_info.value.status_code == 400
        assert "cannot be empty" in exc_info.value.detail.lower()

    def test_aggregates_results_from_all_helpers(self):
        """Positive: global_search aggregates counts and totals across helpers."""

        db = MagicMock()
        access_level = DummyAccessLevel()
        user = DummyUser()

        # Each helper returns a list with different lengths
        helper_returns: Dict[str, List[Dict[str, Any]]] = {
            "locations": [{"id": 1}],
            "buildings": [{"id": 2}, {"id": 3}],
            "racks": [],
            "devices": [{"id": 4}],
            "device_types": [{"id": 5}],
            "makes": [],
            "models": [{"id": 6}, {"id": 7}, {"id": 8}],
            "datacenters": [],
            "asset_owners": [{"id": 9}],
            "applications": [],
        }

        patches = [
            patch("app.dcim.routers.search_router._search_locations", return_value=helper_returns["locations"]),
            patch("app.dcim.routers.search_router._search_buildings", return_value=helper_returns["buildings"]),
            patch("app.dcim.routers.search_router._search_racks", return_value=helper_returns["racks"]),
            patch("app.dcim.routers.search_router._search_devices", return_value=helper_returns["devices"]),
            patch("app.dcim.routers.search_router._search_device_types", return_value=helper_returns["device_types"]),
            patch("app.dcim.routers.search_router._search_makes", return_value=helper_returns["makes"]),
            patch("app.dcim.routers.search_router._search_models", return_value=helper_returns["models"]),
            patch("app.dcim.routers.search_router._search_datacenters", return_value=helper_returns["datacenters"]),
            patch("app.dcim.routers.search_router._search_asset_owners", return_value=helper_returns["asset_owners"]),
            patch("app.dcim.routers.search_router._search_applications", return_value=helper_returns["applications"]),
            patch("app.dcim.routers.search_router.get_allowed_location_ids", return_value={1, 2}),
        ]

        with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5], patches[6], patches[7], patches[8], patches[9], patches[10]:
            result = global_search(
                q="test",
                limit_per_type=10,
                access_level=access_level,
                db=MagicMock(),
                current_user=user,
            )

        # Check query and limit echoed
        assert result["query"] == "test"
        assert result["limit_per_type"] == 10

        # Counts per type should match lengths
        expected_counts = {k: len(v) for k, v in helper_returns.items()}
        assert result["counts"] == expected_counts

        # Total should be sum of all lengths
        assert result["total"] == sum(expected_counts.values())


