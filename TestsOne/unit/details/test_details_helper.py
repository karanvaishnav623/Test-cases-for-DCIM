"""Unit tests for details_helper.py

We focus on:
- ENTITY_DETAIL_HANDLERS mapping completeness
- Each get_*_details function raising 404 when the entity is not found (negative)
- Positive path for a representative function (get_wing_details) to verify shape
"""

from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from app.helpers import details_helper
from app.helpers.listing_types import ListingType


# ============================================================
# Tests for ENTITY_DETAIL_HANDLERS mapping
# ============================================================


class TestEntityDetailHandlersMapping:
    """Unit tests for ENTITY_DETAIL_HANDLERS mapping."""

    def test_all_expected_listing_types_have_handlers(self):
        """Positive: all supported ListingTypes have a detail handler."""
        handlers = details_helper.ENTITY_DETAIL_HANDLERS

        expected_keys = {
            ListingType.wings,
            ListingType.floors,
            ListingType.datacenters,
            ListingType.racks,
            ListingType.devices,
            ListingType.device_types,
            ListingType.asset_owner,
            ListingType.makes,
            ListingType.models,
            ListingType.applications,
        }

        assert expected_keys.issubset(set(handlers.keys()))

    def test_all_handlers_are_callable(self):
        """Positive: every handler in the mapping is callable."""
        handlers = details_helper.ENTITY_DETAIL_HANDLERS
        for lt, handler in handlers.items():
            assert callable(handler), f"Handler for {lt} is not callable"


# ============================================================
# Negative-path tests for get_*_details (404 when not found)
# ============================================================


class TestDetailsHelperNotFound:
    """Negative tests: each get_*_details raises 404 when entity is missing."""

    def _make_db_first_none(self):
        db = MagicMock()
        q = MagicMock()
        db.query.return_value = q
        q.options.return_value = q
        q.filter.return_value = q
        # For helpers that return a single model (most of them), first() -> None
        q.first.return_value = None
        # For helpers like get_rack_details that unpack a tuple, simulate empty result
        q.all.return_value = []
        return db

    def test_get_wing_details_not_found_raises_404(self):
        db = self._make_db_first_none()
        with pytest.raises(HTTPException) as exc_info:
            details_helper.get_wing_details(db, "MissingWing")
        assert exc_info.value.status_code == 404

    def test_get_floor_details_not_found_raises_404(self):
        db = self._make_db_first_none()
        with pytest.raises(HTTPException) as exc_info:
            details_helper.get_floor_details(db, "MissingFloor")
        assert exc_info.value.status_code == 404

    def test_get_datacenter_details_not_found_raises_404(self):
        db = self._make_db_first_none()
        with pytest.raises(HTTPException) as exc_info:
            details_helper.get_datacenter_details(db, "MissingDC")
        assert exc_info.value.status_code == 404
    
    def test_get_rack_details_not_found_raises_404(self):
        """Negative: get_rack_details raises 404 when rack is missing."""
        db = MagicMock()
        q = MagicMock()
        db.query.return_value = q
        # Chain methods used in get_rack_details
        q.outerjoin.return_value = q
        q.filter.return_value = q
        q.first.return_value = None  # Simulate no rack found

        with pytest.raises(HTTPException) as exc_info:
            details_helper.get_rack_details(db, "MissingRack")
        assert exc_info.value.status_code == 404

    def test_get_device_details_not_found_raises_404(self):
        db = self._make_db_first_none()
        with pytest.raises(HTTPException) as exc_info:
            details_helper.get_device_details(db, "MissingDevice")
        assert exc_info.value.status_code == 404

    def test_get_device_type_details_not_found_raises_404(self):
        db = self._make_db_first_none()
        with pytest.raises(HTTPException) as exc_info:
            details_helper.get_device_type_details(db, "MissingType")
        assert exc_info.value.status_code == 404

    def test_get_asset_owner_details_not_found_raises_404(self):
        db = self._make_db_first_none()
        with pytest.raises(HTTPException) as exc_info:
            details_helper.get_asset_owner_details(db, "MissingOwner")
        assert exc_info.value.status_code == 404

    def test_get_make_details_not_found_raises_404(self):
        db = self._make_db_first_none()
        with pytest.raises(HTTPException) as exc_info:
            details_helper.get_make_details(db, "MissingMake")
        assert exc_info.value.status_code == 404

    def test_get_model_details_not_found_raises_404(self):
        db = self._make_db_first_none()
        with pytest.raises(HTTPException) as exc_info:
            details_helper.get_model_details(db, "MissingModel")
        assert exc_info.value.status_code == 404

    def test_get_application_details_not_found_raises_404(self):
        db = self._make_db_first_none()
        with pytest.raises(HTTPException) as exc_info:
            details_helper.get_application_details(db, "MissingApp")
        assert exc_info.value.status_code == 404


# ============================================================
# Positive-path test for representative helper
# ============================================================


class TestGetWingDetailsPositive:
    """Positive tests for get_wing_details (representative of detail helpers)."""

    def test_get_wing_details_returns_expected_shape(self):
        """Positive: returns a dict with expected keys when wing exists."""
        db = MagicMock()

        # First query: Wing with related location & building
        wing_query = MagicMock()
        db.query.return_value = wing_query
        wing_query.options.return_value = wing_query
        wing_query.filter.return_value = wing_query

        class DummyObj:
            pass

        wing = DummyObj()
        wing.id = 1
        wing.name = "Wing-A"
        wing.description = "Test wing"

        location = DummyObj()
        location.id = 10
        location.name = "Loc-1"
        wing.location = location

        building = DummyObj()
        building.id = 20
        building.name = "Bldg-1"
        wing.building = building

        wing_query.first.return_value = wing

        # Second query: floors
        floors_query = MagicMock()
        floors = []
        floor = DummyObj()
        floor.id = 100
        floor.name = "Floor-1"
        floors.append(floor)
        floors_query.filter.return_value = floors_query
        floors_query.all.return_value = floors

        # Third query: rack count
        rack_count_query = MagicMock()
        rack_count_query.filter.return_value = rack_count_query
        rack_count_query.scalar.return_value = 2

        # Fourth query: device count
        device_count_query = MagicMock()
        device_count_query.filter.return_value = device_count_query
        device_count_query.scalar.return_value = 5

        db.query.side_effect = [
            wing_query,
            floors_query,
            rack_count_query,
            device_count_query,
        ]

        result = details_helper.get_wing_details(db, "Wing-A")

        assert result["name"] == "Wing-A"
        assert result["location"]["name"] == "Loc-1"
        assert result["building"]["name"] == "Bldg-1"
        assert result["stats"]["total_floors"] == 1
        assert result["stats"]["total_racks"] == 2
        assert result["stats"]["total_devices"] == 5


class TestGetFloorDetailsPositive:
    """Positive tests for get_floor_details."""

    def test_success(self):
        db = MagicMock()
        floor_obj = MagicMock(id=1, description="desc")
        floor_obj.name = "Floor1"
        
        floor_obj.location.id = 10
        floor_obj.location.name = "Loc1"
        
        floor_obj.building.id = 20
        floor_obj.building.name = "Bldg1"
        
        floor_obj.wing.id = 30
        floor_obj.wing.name = "Wing1"
        
        db.query.return_value.options.return_value.filter.return_value.first.return_value = floor_obj
        
        # Mock datacenters
        dc = MagicMock(id=40)
        dc.name = "DC1"
        db.query.return_value.filter.return_value.all.return_value = [dc]
        
        # Mock scalars (racks, devices)
        db.query.return_value.filter.return_value.scalar.side_effect = [5, 10]
        
        q_floor = MagicMock()
        q_floor.options.return_value.filter.return_value.first.return_value = floor_obj
        
        q_dc = MagicMock()
        q_dc.filter.return_value.all.return_value = [dc]
        
        q_rack = MagicMock()
        q_rack.filter.return_value.scalar.return_value = 5
        
        q_dev = MagicMock()
        q_dev.filter.return_value.scalar.return_value = 10
        
        db.query.side_effect = [q_floor, q_dc, q_rack, q_dev]
        
        res = details_helper.get_floor_details(db, 1)
        assert res["name"] == "Floor1"
        assert res["wing"]["name"] == "Wing1"
        assert len(res["datacenters"]) == 1
        assert res["stats"]["total_racks"] == 5


class TestGetDatacenterDetailsPositive:
    """Positive tests for get_datacenter_details."""

    def test_success(self):
        db = MagicMock()
        dc_obj = MagicMock(id=1, description="desc")
        dc_obj.name = "DC1"
        
        dc_obj.location.id = 10
        dc_obj.location.name = "Loc1"
        
        r1 = MagicMock(id=100, height=42, space_used=10, space_available=32)
        r2 = MagicMock(id=101, height=42, space_used=20, space_available=22)
        
        q_dc = MagicMock()
        q_dc.options.return_value.filter.return_value.first.return_value = dc_obj
        
        q_racks = MagicMock()
        q_racks.filter.return_value.all.return_value = [r1, r2]
        
        q_dev_count = MagicMock()
        q_dev_count.filter.return_value.scalar.return_value = 50
        
        db.query.side_effect = [q_dc, q_racks, q_dev_count]
        
        res = details_helper.get_datacenter_details(db, 1)
        assert res["name"] == "DC1"
        assert res["stats"]["total_racks"] == 2
        assert res["stats"]["total_devices"] == 50
        assert res["stats"]["total_capacity"] == 84
        assert res["stats"]["used_space"] == 30


class TestGetRackDetailsPositive:
    """Positive tests for get_rack_details."""

    def test_success(self):
        db = MagicMock()
        
        rack = MagicMock(id=1, height=42, space_used=10, space_available=32)
        rack.name = "R1"
        
        loc = MagicMock(id=10)
        loc.name = "L1"
        
        bldg = MagicMock(id=20)
        bldg.name = "B1"
        
        wing = MagicMock(id=30)
        wing.name = "W1"
        
        floor = MagicMock(id=40)
        floor.name = "F1"
        
        dc = MagicMock(id=50)
        dc.name = "DC1"
        
        q_rack = MagicMock()
        q_rack.outerjoin.return_value.outerjoin.return_value.outerjoin.return_value.outerjoin.return_value.outerjoin.return_value.filter.return_value.first.return_value = (
            rack, loc, bldg, wing, floor, dc
        )
        
        dev = MagicMock(id=99, position=1, space_required=2)
        dev.name = "Dev1"
        dev.status = "active"
        
        dt = MagicMock()
        dt.name = "Server"
        
        mk = MagicMock()
        mk.name = "Dell"
        
        md = MagicMock(front_image="f.jpg", rear_image="r.jpg")
        
        q_devs = MagicMock()
        q_devs.outerjoin.return_value.outerjoin.return_value.outerjoin.return_value.filter.return_value.order_by.return_value.all.return_value = [
            (dev, dt, mk, md)
        ]
        
        db.query.side_effect = [q_rack, q_devs]
        
        res = details_helper.get_rack_details(db, 1)
        assert res["name"] == "R1"
        assert res["location"]["name"] == "L1"
        assert res["devices"][0]["name"] == "Dev1"
        assert res["devices"][0]["front_image"] == "f.jpg"
        assert res["stats"]["utilization_percent"] == 23.81


class TestGetDeviceDetailsPositive:
    """Positive tests for get_device_details."""

    def test_success(self):
        db = MagicMock()
        
        dev = MagicMock(id=1, rack_id=10)
        dev.name = "D1"
        dev.location.name = "Loc1"
        dev.rack.name = "R1"
        dev.model.height = 2
        dev.device_type.name = "Type1"
        dev.application_mapped = None 
        
        q_dev = MagicMock()
        q_dev.options.return_value.filter.return_value.first.return_value = dev
        
        neighbor = MagicMock(id=2)
        neighbor.name = "D2"
        
        q_neighbors = MagicMock()
        q_neighbors.outerjoin.return_value.outerjoin.return_value.outerjoin.return_value.filter.return_value.order_by.return_value.all.return_value = [
            (neighbor, MagicMock(), MagicMock(), MagicMock())
        ]
        
        db.query.side_effect = [q_dev, q_neighbors]
        
        res = details_helper.get_device_details(db, 1)
        assert res["name"] == "D1"
        assert res["rack"]["name"] == "R1"
        assert len(res["devices"]) == 1
        assert res["devices"][0]["id"] == 2


class TestGetDeviceTypeDetailsPositive:
    """Positive tests for get_device_type_details."""

    def test_success(self):
        db = MagicMock()
        
        dt = MagicMock(id=1)
        dt.name = "DT1"
        
        model = MagicMock(id=10, height=2)
        model.name = "M1"
        
        dt.models = [model]
        dt.make.name = "Make1"
        
        q_dt = MagicMock()
        q_dt.options.return_value.filter.return_value.first.return_value = dt
        
        q_count = MagicMock()
        q_count.filter.return_value.scalar.return_value = 100
        
        db.query.side_effect = [q_dt, q_count]
        
        res = details_helper.get_device_type_details(db, 1)
        assert res["name"] == "DT1"
        assert res["model"]["name"] == "M1"
        assert res["stats"]["device_count"] == 100


class TestGetAssetOwnerDetailsPositive:
    """Positive tests for get_asset_owner_details."""

    def test_success(self):
        db = MagicMock()
        
        owner = MagicMock(id=1)
        owner.name = "Owner1"
        owner.location.name = "Loc1"
        
        q_owner = MagicMock()
        q_owner.options.return_value.filter.return_value.first.return_value = owner
        
        app = MagicMock(id=10)
        app.name = "App1"
        
        q_apps = MagicMock()
        q_apps.filter.return_value.all.return_value = [app]
        
        db.query.side_effect = [q_owner, q_apps]
        
        res = details_helper.get_asset_owner_details(db, 1)
        assert res["name"] == "Owner1"
        assert res["stats"]["total_applications"] == 1


class TestGetMakeDetailsPositive:
    """Positive tests for get_make_details."""

    def test_success(self):
        db = MagicMock()
        
        make = MagicMock(id=1)
        make.name = "Make1"
        
        q_make = MagicMock()
        q_make.filter.return_value.first.return_value = make
        
        model = MagicMock(id=10)
        model.name = "M1"
        
        q_models = MagicMock()
        q_models.filter.return_value.all.return_value = [model]
        
        dt = MagicMock(id=20)
        dt.name = "DT1"
        dt.models = [MagicMock(height=2)]
        
        q_dts = MagicMock()
        q_dts.filter.return_value.all.return_value = [dt]
        
        q_dev_count = MagicMock()
        q_dev_count.filter.return_value.scalar.return_value = 50
        
        q_rack_count = MagicMock()
        q_rack_count.filter.return_value.scalar.return_value = 5
        
        db.query.side_effect = [q_make, q_models, q_dts, q_dev_count, q_rack_count]
        
        res = details_helper.get_make_details(db, 1)
        assert res["name"] == "Make1"
        assert res["stats"]["total_models"] == 1
        assert res["stats"]["total_devices"] == 50


class TestGetModelDetailsPositive:
    """Positive tests for get_model_details."""

    def test_success(self):
        db = MagicMock()
        
        mod = MagicMock(id=1, height=2, front_image="f.png", rear_image="r.png")
        mod.name = "M1"
        mod.make.name = "Make1"
        mod.device_type.name = "DT1"
        
        q_mod = MagicMock()
        q_mod.options.return_value.filter.return_value.first.return_value = mod
        
        db.query.return_value = q_mod
        
        res = details_helper.get_model_details(db, 1)
        assert res["name"] == "M1"
        assert res["front_image"] == "f.png"
        assert res["device_type"]["name"] == "DT1"


class TestGetApplicationDetailsPositive:
    """Positive tests for get_application_details."""

    def test_success(self):
        db = MagicMock()
        
        app = MagicMock(id=1)
        app.name = "App1"
        app.asset_owner.name = "Owner1"
        
        q_app = MagicMock()
        q_app.options.return_value.filter.return_value.first.return_value = app
        
        dev = MagicMock(id=10)
        dev.name = "D1"
        
        q_devs = MagicMock()
        q_devs.filter.return_value.all.return_value = [dev]
        
        db.query.side_effect = [q_app, q_devs]
        
        res = details_helper.get_application_details(db, 1)
        assert res["name"] == "App1"
        assert res["asset_owner"]["name"] == "Owner1"
        assert res["stats"]["total_devices"] == 1


