import pytest
from unittest.mock import MagicMock, patch
from fastapi import HTTPException
from app.helpers import add_entity_helper

class TestCreateRack:
    """Unit tests for create_rack in add_entity_helper."""

    def test_create_rack_success(self):
        """Positive: Successfully creates a rack with all lookups resolving."""
        db = MagicMock()
        data = {
            "name": "Rack1",
            "location_name": "Loc1",
            "building_name": "Build1",
            "wing_name": "Wing1",
            "floor_name": "Floor1",
            "datacenter_name": "DC1",
            "height": 42,
            "description": "Test Rack"
        }

        # Mock helper lookups
        with patch("app.helpers.add_entity_helper.get_location_by_name") as mock_get_loc, \
             patch("app.helpers.add_entity_helper.get_building_by_name") as mock_get_build, \
             patch("app.helpers.add_entity_helper.get_wing_by_name_scoped") as mock_get_wing, \
             patch("app.helpers.add_entity_helper.get_floor_by_name_scoped") as mock_get_floor, \
             patch("app.helpers.add_entity_helper.get_datacenter_by_name_scoped") as mock_get_dc, \
             patch("app.helpers.add_entity_helper.db_operation"):

            mock_get_loc.return_value = MagicMock(id=1, name="Loc1")
            mock_get_build.return_value = MagicMock(id=2, name="Build1")
            mock_get_wing.return_value = MagicMock(id=3, name="Wing1")
            mock_get_floor.return_value = MagicMock(id=4, name="Floor1")
            mock_get_dc.return_value = MagicMock(id=5, name="DC1")

            result = add_entity_helper.create_rack(db, data)

            assert result["name"] == "Rack1"
            assert result["height"] == 42
            assert result["space_used"] == 0
            assert result["space_available"] == 42
            # Verify DB add/commit called
            db.add.assert_called_once()
            db.commit.assert_called_once()

    def test_create_rack_missing_height(self):
        """Negative: Raises HTTPException when height is missing."""
        db = MagicMock()
        data = {
            "name": "Rack1",
            "location_name": "Loc1",
            "building_name": "Build1",
            "wing_name": "Wing1",
            "floor_name": "Floor1",
            "datacenter_name": "DC1",
            # height missing
        }

        with patch("app.helpers.add_entity_helper.get_location_by_name"), \
             patch("app.helpers.add_entity_helper.get_building_by_name"), \
             patch("app.helpers.add_entity_helper.get_wing_by_name_scoped"), \
             patch("app.helpers.add_entity_helper.get_floor_by_name_scoped"), \
             patch("app.helpers.add_entity_helper.get_datacenter_by_name_scoped"), \
             patch("app.helpers.add_entity_helper.db_operation"):

            with pytest.raises(HTTPException) as exc_info:
                add_entity_helper.create_rack(db, data)
            
            assert exc_info.value.status_code == 400
            assert "Height is required" in exc_info.value.detail


class TestCreateDevice:
    """Unit tests for create_device in add_entity_helper."""

    def test_create_device_success(self):
        """Positive: Successfully creates a device with valid capacity."""
        db = MagicMock()
        data = {
            "name": "Dev1",
            "location_name": "Loc1",
            "building_name": "Build1",
            "wing_name": "Wing1",
            "floor_name": "Floor1",
            "datacenter_name": "DC1",
            "rack_name": "Rack1",
            "make_name": "Make1",
            "devicetype_name": "Type1",
            "model_name": "Model1",
            "asset_owner_name": "Owner1",
            "application_name": "App1",
            "position": 10,
            "face": "Front",
            "status": "active"
        }

        # Mock dependencies
        with patch("app.helpers.add_entity_helper.get_location_by_name") as m_loc, \
             patch("app.helpers.add_entity_helper.get_building_by_name") as m_bld, \
             patch("app.helpers.add_entity_helper.get_wing_by_name_scoped") as m_wng, \
             patch("app.helpers.add_entity_helper.get_floor_by_name_scoped") as m_flr, \
             patch("app.helpers.add_entity_helper.get_datacenter_by_name_scoped") as m_dc, \
             patch("app.helpers.add_entity_helper.get_rack_by_name_scoped") as m_rck, \
             patch("app.helpers.add_entity_helper.get_make_by_name") as m_mak, \
             patch("app.helpers.add_entity_helper.get_device_type_by_name_scoped") as m_dt, \
             patch("app.helpers.add_entity_helper.get_model_by_name") as m_mod, \
             patch("app.helpers.add_entity_helper.get_asset_owner_by_name") as m_ao, \
             patch("app.helpers.add_entity_helper.get_application_by_name") as m_app, \
             patch("app.helpers.add_entity_helper.sync_rack_usage"), \
             patch("app.helpers.add_entity_helper.ensure_continuous_space"), \
             patch("app.helpers.add_entity_helper.ensure_rack_capacity"), \
             patch("app.helpers.add_entity_helper.reserve_rack_capacity"), \
             patch("app.helpers.add_entity_helper.db_operation"):

            m_loc.return_value = MagicMock(id=1, name="Loc1")
            m_bld.return_value = MagicMock(id=2, name="Build1")
            m_wng.return_value = MagicMock(id=3, name="Wing1")
            m_flr.return_value = MagicMock(id=4, name="Floor1")
            m_dc.return_value = MagicMock(id=5, name="DC1")
            m_rck.return_value = MagicMock(id=6, name="Rack1")
            
            make_mock = MagicMock(id=7, name="Make1")
            m_mak.return_value = make_mock
            
            dt_mock = MagicMock(id=8, name="Type1")
            m_dt.return_value = dt_mock
            
            # Model mocks
            model_mock = MagicMock(id=9, name="Model1", make_id=7, device_type_id=8, height=2)
            m_mod.return_value = model_mock
            
            m_ao.return_value = MagicMock(id=10, name="Owner1")
            m_app.return_value = MagicMock(id=11, name="App1", asset_owner_id=10)

            result = add_entity_helper.create_device(db, data)
            
            assert result["name"] == "Dev1"
            assert result["position"] == 10
            assert result["face_front"] is True
            db.add.assert_called_once()
            db.commit.assert_called_once()


    def test_create_device_make_mismatch(self):
        """Negative: Raises 400 if model make does not match provided make."""
        db = MagicMock()
        data = {
            "name": "Dev1",
            "location_name": "Loc1",
            "building_name": "Build1",
            "wing_name": "Wing1",
            "floor_name": "Floor1",
            "datacenter_name": "DC1",
            "rack_name": "Rack1",
            "make_name": "Make1",
            "devicetype_name": "Type1",
            "model_name": "Model1",
            "asset_owner_name": "Owner1",
            "application_name": "App1"
        }

        with patch("app.helpers.add_entity_helper.get_location_by_name"), \
             patch("app.helpers.add_entity_helper.get_building_by_name"), \
             patch("app.helpers.add_entity_helper.get_wing_by_name_scoped"), \
             patch("app.helpers.add_entity_helper.get_floor_by_name_scoped"), \
             patch("app.helpers.add_entity_helper.get_datacenter_by_name_scoped"), \
             patch("app.helpers.add_entity_helper.get_rack_by_name_scoped"), \
             patch("app.helpers.add_entity_helper.get_make_by_name") as m_mak, \
             patch("app.helpers.add_entity_helper.get_device_type_by_name_scoped"), \
             patch("app.helpers.add_entity_helper.get_model_by_name") as m_mod, \
             patch("app.helpers.add_entity_helper.get_asset_owner_by_name"), \
             patch("app.helpers.add_entity_helper.get_application_by_name"), \
             patch("app.helpers.add_entity_helper.db_operation"):

            m_mak.return_value = MagicMock(id=1, name="Make1")
            m_mod.return_value = MagicMock(id=99, name="Model1", make_id=2) # Different make_id

            with pytest.raises(HTTPException) as exc_info:
                add_entity_helper.create_device(db, data)
            
            assert exc_info.value.status_code == 400
            assert "belongs to a different make" in exc_info.value.detail


class TestCreateLocation:
    """Unit tests for create_location."""

    def test_create_location_success(self):
        """Positive: Successfully creates a location."""
        db = MagicMock()
        data = {"name": "Test Loc", "description": "Desc"}
        
        with patch("app.helpers.add_entity_helper.db_operation"), \
             patch("app.helpers.add_entity_helper.check_entity_exists", return_value=False):
            
            # Mock DB behaviors
            result = add_entity_helper.create_location(db, data)
            
            assert result["name"] == "Test Loc"
            db.add.assert_called_once()
            db.commit.assert_called_once()

    def test_create_location_conflict(self):
        """Negative: Raises 409 if location exists."""
        db = MagicMock()
        data = {"name": "Existing Loc"}
        
        with patch("app.helpers.add_entity_helper.db_operation"), \
             patch("app.helpers.add_entity_helper.check_entity_exists", return_value=True):
            
            with pytest.raises(HTTPException) as exc:
                add_entity_helper.create_location(db, data)
            assert exc.value.status_code == 409


class TestCreateBuilding:
    """Unit tests for create_building."""

    def test_create_building_success(self):
        """Positive: Successfully creates a building."""
        db = MagicMock()
        data = {
            "name": "B1", 
            "location_name": "Loc1",
            "description": "d",
            "address": "addr"
        }
        
        with patch("app.helpers.add_entity_helper.db_operation"), \
             patch("app.helpers.add_entity_helper.check_entity_exists", return_value=False), \
             patch("app.helpers.add_entity_helper.get_location_by_name") as m_loc:
             
            m_loc.return_value = MagicMock(id=1, name="Loc1")
            
            result = add_entity_helper.create_building(db, data)
            
            assert result["name"] == "B1"
            assert result["location_id"] == 1
            db.add.assert_called_once()

    def test_create_building_conflict(self):
        """Negative: Raises 409 if building name exists."""
        db = MagicMock()
        with patch("app.helpers.add_entity_helper.db_operation"), \
             patch("app.helpers.add_entity_helper.check_entity_exists", return_value=True):
            
            with pytest.raises(HTTPException) as exc:
                add_entity_helper.create_building(db, {"name": "B1"})
            assert exc.value.status_code == 409



class TestCreateWing:
    """Unit tests for create_wing."""
    
    def test_create_wing_success(self):
        """Positive: Creates wing correctly."""
        db = MagicMock()
        data = {"name": "W1", "location_name": "L1", "building_name": "B1"}
        
        with patch("app.helpers.add_entity_helper.get_location_by_name") as m_loc, \
             patch("app.helpers.add_entity_helper.get_building_by_name") as m_bld, \
             patch("app.helpers.add_entity_helper.get_or_create_wing") as m_get_create_wing:
             
            # Configure mocks to return name as string attribute, preventing it from being a mock
            loc_mock = MagicMock(id=1)
            loc_mock.name = "L1" # Explicitly set property
            m_loc.return_value = loc_mock
            
            bld_mock = MagicMock(id=2)
            bld_mock.name = "B1"
            m_bld.return_value = bld_mock
            
            wing_mock = MagicMock(id=3, location_id=1, building_id=2, description="")
            wing_mock.name = "W1"
            m_get_create_wing.return_value = wing_mock
            
            result = add_entity_helper.create_wing(db, data)
            
            assert result["id"] == 3
            assert result["name"] == "W1"
            db.commit.assert_called_once()


class TestCreateFloor:
    """Unit tests for create_floor."""
    
    def test_create_floor_success(self):
        """Positive: Creates floor correctly."""
        db = MagicMock()
        data = {"name": "F1", "wing_name": "W1", "location_name": "L1", "building_name": "B1"}
        
        with patch("app.helpers.add_entity_helper.get_location_by_name") as m_loc, \
             patch("app.helpers.add_entity_helper.get_building_by_name") as m_bld, \
             patch("app.helpers.add_entity_helper.get_or_create_wing") as m_wing, \
             patch("app.helpers.add_entity_helper.get_or_create_floor") as m_floor:
             
            loc_mock = MagicMock(id=1)
            loc_mock.name = "L1"
            m_loc.return_value = loc_mock
            
            bld_mock = MagicMock(id=2)
            bld_mock.name = "B1"
            m_bld.return_value = bld_mock
            
            wing_mock = MagicMock(id=3)
            wing_mock.name = "W1"
            m_wing.return_value = wing_mock
            
            floor_mock = MagicMock(id=4, location_id=1, building_id=2, wing_id=3, description="")
            floor_mock.name = "F1"
            m_floor.return_value = floor_mock
            
            result = add_entity_helper.create_floor(db, data)
            
            assert result["id"] == 4
            assert result["name"] == "F1"


class TestCreateDatacenter:
    """Unit tests for create_datacenter."""
    
    def test_create_datacenter_success(self):
        """Positive: Creates datacenter correctly."""
        db = MagicMock()
        data = {"name": "DC1", "floor_name": "F1", "wing_name": "W1", "location_name": "L1", "building_name": "B1", "description": "d"}
        
        with patch("app.helpers.add_entity_helper.get_location_by_name") as m_loc, \
             patch("app.helpers.add_entity_helper.get_building_by_name") as m_bld, \
             patch("app.helpers.add_entity_helper.get_or_create_wing") as m_wing, \
             patch("app.helpers.add_entity_helper.get_or_create_floor") as m_floor:
             
            loc_mock = MagicMock(id=1)
            loc_mock.name = "L1"
            m_loc.return_value = loc_mock
            
            bld_mock = MagicMock(id=2)
            bld_mock.name = "B1"
            m_bld.return_value = bld_mock
            
            wing_mock = MagicMock(id=3)
            wing_mock.name = "W1"
            m_wing.return_value = wing_mock
            
            floor_mock = MagicMock(id=4)
            floor_mock.name = "F1"
            m_floor.return_value = floor_mock
            
            result = add_entity_helper.create_datacenter(db, data)
            
            assert result["name"] == "DC1"
            assert result["location_name"] == "L1"
            db.add.assert_called_once()


class TestCreateDeviceType:
    """Unit tests for create_device_type."""
    
    def test_create_device_type_success(self):
        """Positive: Creates device type (and make) correctly."""
        db = MagicMock()
        data = {"name": "DT1", "make_name": "Make1"}
        
        with patch("app.helpers.add_entity_helper.get_or_create_make") as m_make, \
             patch("app.helpers.add_entity_helper.get_or_create_device_type") as m_dt:
             
            make_mock = MagicMock(id=1)
            make_mock.name = "Make1"
            m_make.return_value = make_mock
            
            dt_mock = MagicMock(id=2, make_id=1)
            dt_mock.name = "DT1"
            m_dt.return_value = dt_mock
            
            result = add_entity_helper.create_device_type(db, data)
            
            assert result["name"] == "DT1"
            assert result["make_name"] == "Make1"


class TestCreateAssetOwner:
    """Unit tests for create_asset_owner."""
    
    def test_create_asset_owner_success(self):
        """Positive: Creates asset owner correctly."""
        db = MagicMock()
        data = {"name": "Owner1", "location_name": "L1"}
        
        with patch("app.helpers.add_entity_helper.get_location_by_name") as m_loc, \
             patch("app.helpers.add_entity_helper.get_or_create_asset_owner_scoped") as m_ao:
             
            loc_mock = MagicMock(id=1)
            loc_mock.name = "L1"
            m_loc.return_value = loc_mock
            
            ao_mock = MagicMock(id=2, location_id=1)
            ao_mock.name = "Owner1"
            m_ao.return_value = ao_mock
            
            result = add_entity_helper.create_asset_owner(db, data)
            
            assert result["name"] == "Owner1"
            assert result["location_name"] == "L1"


# =============================================================================
# Migrated Coverage Tests
# =============================================================================

def test_add_helper_create_location():
    db = MagicMock()
    # Mock check_entity_exists to return False
    with pytest.MonkeyPatch.context() as m:
        m.setattr(add_entity_helper, "check_entity_exists", lambda *args, **kwargs: False)
        
        data = {"name": "Test", "description": "Desc"}
        result = add_entity_helper.create_location(db, data)
        assert result["name"] == "Test"
        db.add.assert_called()
        db.commit.assert_called()

def test_add_helper_create_building():
    db = MagicMock()
    mock_loc = MagicMock()
    mock_loc.id = 1
    mock_loc.name = "L1"

    with pytest.MonkeyPatch.context() as m:
        m.setattr(add_entity_helper, "check_entity_exists", lambda *args, **kwargs: False)
        m.setattr(add_entity_helper, "get_location_by_name", lambda *args: mock_loc)

        data = {"name": "B1", "location_name": "L1"}
        result = add_entity_helper.create_building(db, data)
        assert result["name"] == "B1"
        assert result["location_id"] == 1

def test_add_helper_create_wing():
    db = MagicMock()
    mock_loc = MagicMock(); mock_loc.id = 1; mock_loc.name = "L1"
    mock_bld = MagicMock(); mock_bld.id = 2; mock_bld.name = "B1"
    mock_wing = MagicMock(); mock_wing.id = 3; mock_wing.name = "W1"

    with pytest.MonkeyPatch.context() as m:
        m.setattr(add_entity_helper, "get_location_by_name", lambda *args: mock_loc)
        m.setattr(add_entity_helper, "get_building_by_name", lambda *args: mock_bld)
        # Mock get_or_create_wing
        m.setattr(add_entity_helper, "get_or_create_wing", lambda *args: mock_wing)

        data = {"name": "W1", "location_name": "L1", "building_name": "B1"}
        result = add_entity_helper.create_wing(db, data)
        assert result["name"] == "W1"

def test_add_helper_create_floor():
    db = MagicMock()
    mock_loc = MagicMock(); mock_loc.id = 1; mock_loc.name = "L1"
    mock_bld = MagicMock(); mock_bld.id = 2; mock_bld.name = "B1"
    mock_wing = MagicMock(); mock_wing.id = 3; mock_wing.name = "W1"
    mock_floor = MagicMock(); mock_floor.id = 4; mock_floor.name = "F1"

    with pytest.MonkeyPatch.context() as m:
        m.setattr(add_entity_helper, "get_location_by_name", lambda *args: mock_loc)
        m.setattr(add_entity_helper, "get_building_by_name", lambda *args: mock_bld)
        m.setattr(add_entity_helper, "get_or_create_wing", lambda *args: mock_wing)
        m.setattr(add_entity_helper, "get_or_create_floor", lambda *args: mock_floor)

        data = {"name": "F1", "location_name": "L1", "building_name": "B1", "wing_name": "W1"}
        result = add_entity_helper.create_floor(db, data)
        assert result["name"] == "F1"

# Test create_asset_owner
def test_create_asset_owner():
    db = MagicMock()
    data = {"name": "Test Owner", "location_name": "Loc1", "description": "Desc"}
    
    mock_loc = MagicMock(); mock_loc.id = 1; mock_loc.name = "Loc1"
    mock_ao = MagicMock(); mock_ao.id = 10; mock_ao.name = "Test Owner"; mock_ao.location_id = 1
    
    with patch("app.helpers.add_entity_helper.get_location_by_name", return_value=mock_loc),          patch("app.helpers.add_entity_helper.get_or_create_asset_owner_scoped", return_value=mock_ao):
         
         result = add_entity_helper.create_asset_owner(db, data)
         
         assert result["id"] == 10
         assert result["name"] == "Test Owner"
         assert result["location_name"] == "Loc1"

# Test create_application 
def test_create_application():
    db = MagicMock()
    data = {"name": "App1", "asset_owner_name": "Owner1", "location_name": "Loc1", "description": "Desc"}
    
    mock_owner = MagicMock(); mock_owner.id = 10
    
    with patch("app.helpers.add_entity_helper.get_asset_owner_by_name", return_value=mock_owner):
         
         # db.add side effect to set ID on the passed object
         def add_side_effect(obj):
             obj.id = 100
         db.add.side_effect = add_side_effect
         
         # create_application returns a dict
         result = add_entity_helper.create_application(db, data)
         assert result["id"] == 100
         assert result["name"] == "App1"

# Test create_make
def test_create_make():
    db = MagicMock()
    data = {"name": "Make1"}
    
    mock_make = MagicMock(); mock_make.id = 5; mock_make.name = "Make1"
    
    with patch("app.helpers.add_entity_helper.get_or_create_make", return_value=mock_make):
        result = add_entity_helper.create_make(db, data)
        assert result["id"] == 5

# Test create_device_type
def test_create_device_type():
    db = MagicMock()
    data = {"name": "DT1", "make_name": "Make1"}
    
    mock_make = MagicMock(); mock_make.id = 5; mock_make.name = "Make1"
    mock_dt = MagicMock(); mock_dt.id = 6; mock_dt.name = "DT1"; mock_dt.make_id = 5
    
    with patch("app.helpers.add_entity_helper.get_or_create_make", return_value=mock_make),          patch("app.helpers.add_entity_helper.get_or_create_device_type", return_value=mock_dt):
         
         result = add_entity_helper.create_device_type(db, data)
         assert result["id"] == 6
         assert result["make_name"] == "Make1"

# Test create_model
def test_create_model():
    db = MagicMock()
    data = {"name": "Model1", "make_name": "Make1", "devicetype_name": "DT1", "height": 2}
    
    mock_make = MagicMock(); mock_make.id = 5; mock_make.name = "Make1"
    mock_dt = MagicMock(); mock_dt.id = 6; mock_dt.name = "DT1"
    
    query_mock = MagicMock()
    filter_mock = MagicMock()
    query_mock.filter.return_value = filter_mock
    filter_mock.filter.return_value = filter_mock 
    filter_mock.first.return_value = None # No existing model
    db.query.return_value = query_mock
    
    with patch("app.helpers.add_entity_helper.get_or_create_make", return_value=mock_make),          patch("app.helpers.add_entity_helper.get_or_create_device_type", return_value=mock_dt):
         
         def add_side_effect(obj):
             obj.id = 7
         db.add.side_effect = add_side_effect
         
         result = add_entity_helper.create_model(db, data)
         assert result["id"] == 7
import pytest
from unittest.mock import MagicMock, patch
from fastapi import HTTPException
from datetime import date
from app.helpers.add_entity_helper import (
    create_device,
    create_rack,
    get_wing_by_name_scoped,
    get_floor_by_name_scoped,
    get_datacenter_by_name_scoped,
    get_device_type_by_name_scoped,
    get_rack_by_name_scoped
)

# ============================================================
# Tests for Scoped Lookups (Error Paths)
# ============================================================

def test_get_wing_by_name_scoped_not_found():
    db = MagicMock()
    db.query.return_value.filter.return_value.filter.return_value.filter.return_value.first.return_value = None
    with pytest.raises(HTTPException) as exc:
        get_wing_by_name_scoped(db, "Missing", 1, 1)
    assert exc.value.status_code == 404

def test_get_floor_by_name_scoped_not_found():
    db = MagicMock()
    db.query.return_value.filter.return_value.filter.return_value.filter.return_value.filter.return_value.first.return_value = None
    with pytest.raises(HTTPException) as exc:
        get_floor_by_name_scoped(db, "Missing", 1, 1, 1)
    assert exc.value.status_code == 404

def test_get_datacenter_by_name_scoped_not_found():
    db = MagicMock()
    # Chain is long: query().filter()...first()
    mock_q = MagicMock()
    mock_q.filter.return_value = mock_q
    mock_q.first.return_value = None
    db.query.return_value = mock_q
    
    with pytest.raises(HTTPException) as exc:
        get_datacenter_by_name_scoped(db, "Missing", 1, 1, 1, 1)
    assert exc.value.status_code == 404

def test_get_device_type_by_name_scoped_not_found():
    db = MagicMock()
    mock_q = MagicMock()
    mock_q.filter.return_value = mock_q
    mock_q.first.return_value = None
    db.query.return_value = mock_q
    
    with pytest.raises(HTTPException) as exc:
        get_device_type_by_name_scoped(db, "Missing", 1)
    assert exc.value.status_code == 404

def test_get_rack_by_name_scoped_not_found():
    db = MagicMock()
    mock_q = MagicMock()
    mock_q.filter.return_value = mock_q
    mock_q.first.return_value = None
    db.query.return_value = mock_q
    
    with pytest.raises(HTTPException) as exc:
        get_rack_by_name_scoped(db, "Missing", 1,1,1,1,1)
    assert exc.value.status_code == 404


# ============================================================
# Tests for create_rack Validations
# ============================================================

def test_create_rack_missing_height():
    db = MagicMock()
    data = {"name": "R1", "location_name": "L1", "building_name": "B1", "wing_name": "W1", "floor_name": "F1", "datacenter_name": "DC1"}
    
    # Mock lookups to succeed
    with patch("app.helpers.add_entity_helper.get_location_by_name"), \
         patch("app.helpers.add_entity_helper.get_building_by_name"), \
         patch("app.helpers.add_entity_helper.get_wing_by_name_scoped"), \
         patch("app.helpers.add_entity_helper.get_floor_by_name_scoped"), \
         patch("app.helpers.add_entity_helper.get_datacenter_by_name_scoped"), \
         patch("app.helpers.add_entity_helper.db_operation"):
         
         with pytest.raises(HTTPException) as exc:
             create_rack(db, data)
         assert exc.value.status_code == 400
         assert "Height is required" in exc.value.detail


# ============================================================
# Tests for create_device Validations
# ============================================================

class TestCreateDeviceValidations:
    
    @pytest.fixture
    def mock_deps(self):
        """Setup common mocks for create_device."""
        mocks = {}
        patcher_loc = patch("app.helpers.add_entity_helper.get_location_by_name")
        patcher_bld = patch("app.helpers.add_entity_helper.get_building_by_name")
        patcher_wing = patch("app.helpers.add_entity_helper.get_wing_by_name_scoped")
        patcher_floor = patch("app.helpers.add_entity_helper.get_floor_by_name_scoped")
        patcher_dc = patch("app.helpers.add_entity_helper.get_datacenter_by_name_scoped")
        patcher_rack = patch("app.helpers.add_entity_helper.get_rack_by_name_scoped")
        patcher_make = patch("app.helpers.add_entity_helper.get_make_by_name")
        patcher_dt = patch("app.helpers.add_entity_helper.get_device_type_by_name_scoped")
        patcher_model = patch("app.helpers.add_entity_helper.get_model_by_name")
        patcher_ao = patch("app.helpers.add_entity_helper.get_asset_owner_by_name")
        patcher_app = patch("app.helpers.add_entity_helper.get_application_by_name")
        patcher_op = patch("app.helpers.add_entity_helper.db_operation")
        
        mocks["loc"] = patcher_loc.start()
        mocks["bld"] = patcher_bld.start()
        mocks["wing"] = patcher_wing.start()
        mocks["floor"] = patcher_floor.start()
        mocks["dc"] = patcher_dc.start()
        mocks["rack"] = patcher_rack.start()
        mocks["make"] = patcher_make.start()
        mocks["dt"] = patcher_dt.start()
        mocks["model"] = patcher_model.start()
        mocks["ao"] = patcher_ao.start()
        mocks["app"] = patcher_app.start()
        patcher_op.start()
        
        yield mocks
        
        patcher_loc.stop()
        patcher_bld.stop()
        patcher_wing.stop()
        patcher_floor.stop()
        patcher_dc.stop()
        patcher_rack.stop()
        patcher_make.stop()
        patcher_dt.stop()
        patcher_model.stop()
        patcher_ao.stop()
        patcher_app.stop()
        patcher_op.stop()

    def test_incompatible_make(self, mock_deps):
        db = MagicMock()
        data = {
            "location_name": "L1", "building_name": "B1", "wing_name": "W1", "floor_name": "F1", 
            "datacenter_name": "DC1", "rack_name": "R1", "make_name": "M1", 
            "devicetype_name": "DT1", "model_name": "Mod1", "asset_owner_name": "AO1", "application_name": "App1"
        }
        
        mock_deps["make"].return_value.id = 1
        mock_deps["model"].return_value.make_id = 2 # Mismatch
        
        with pytest.raises(HTTPException) as exc:
            create_device(db, data)
        assert exc.value.status_code == 400
        assert "belongs to a different make" in exc.value.detail

    def test_incompatible_device_type(self, mock_deps):
        db = MagicMock()
        data = {
            "location_name": "L1", "building_name": "B1", "wing_name": "W1", "floor_name": "F1", 
            "datacenter_name": "DC1", "rack_name": "R1", "make_name": "M1", 
            "devicetype_name": "DT1", "model_name": "Mod1", "asset_owner_name": "AO1", "application_name": "App1"
        }
        
        mock_deps["make"].return_value.id = 1
        mock_deps["model"].return_value.make_id = 1
        mock_deps["dt"].return_value.id = 10
        mock_deps["model"].return_value.device_type_id = 11 # Mismatch
        
        with pytest.raises(HTTPException) as exc:
            create_device(db, data)
        assert exc.value.status_code == 400
        assert "not linked to device type" in exc.value.detail

    def test_invalid_date_range(self, mock_deps):
        db = MagicMock()
        data = {
            "location_name": "L1", "building_name": "B1", "wing_name": "W1", "floor_name": "F1", 
            "datacenter_name": "DC1", "rack_name": "R1", "make_name": "M1", 
            "devicetype_name": "DT1", "model_name": "Mod1", "asset_owner_name": "AO1", "application_name": "App1",
            "warranty_start_date": date(2023, 1, 10),
            "warranty_end_date": date(2023, 1, 1), # End before Start
        }
        
        # Valid makes/models
        mock_deps["make"].return_value.id = 1
        mock_deps["model"].return_value.make_id = 1
        mock_deps["dt"].return_value.id = 10
        mock_deps["model"].return_value.device_type_id = 10
        
        with pytest.raises(HTTPException) as exc:
            create_device(db, data)
        assert exc.value.status_code == 400
        assert "Warranty end date cannot be before start date" in exc.value.detail

    def test_missing_position(self, mock_deps):
        db = MagicMock()
        data = {
            "location_name": "L1", "building_name": "B1", "wing_name": "W1", "floor_name": "F1", 
            "datacenter_name": "DC1", "rack_name": "R1", "make_name": "M1", 
            "devicetype_name": "DT1", "model_name": "Mod1", "asset_owner_name": "AO1", "application_name": "App1",
            # No position
        }
        
        mock_deps["make"].return_value.id = 1
        mock_deps["model"].return_value.make_id = 1
        mock_deps["dt"].return_value.id = 10
        mock_deps["model"].return_value.device_type_id = 10
        mock_deps["model"].return_value.height = 2
        
        with pytest.raises(HTTPException) as exc:
            create_device(db, data)
        assert exc.value.status_code == 400
        assert "Position is required" in exc.value.detail
