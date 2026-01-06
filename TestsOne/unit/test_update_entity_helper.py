import pytest
from unittest.mock import MagicMock, patch
from fastapi import HTTPException
from app.helpers import update_entity_helper
from app.helpers.update_entity_helper import update_rack, update_device
from app.models.entity_models import (
    Rack, Device, Location, Building, Wing, Floor, Datacenter,
    DeviceType, Make, Model, AssetOwner, ApplicationMapped
)
from app.helpers.add_entity_helper import (
    get_wing_by_name_scoped,
    get_floor_by_name_scoped,
    get_datacenter_by_name_scoped,
    get_device_type_by_name_scoped,
    get_rack_by_name_scoped,
)
from app.helpers.db_utils import get_entity_by_name

class TestUpdateLocation:
    """Unit tests for update_location."""

    def test_update_location_success(self):
        """Positive: Updates location successfully."""
        db = MagicMock()
        loc_mock = MagicMock(spec=Location)
        loc_mock.id = 1
        loc_mock.name = "Old Name"
        
        # Mock query sequence:
        # 1. Get location by ID -> returns loc_mock
        # 2. Check conflict (check_entity_exists) -> returns False (mocked below)
        
        db.query.return_value.filter.return_value.first.return_value = loc_mock
        
        with patch("app.helpers.update_entity_helper.db_operation"), \
             patch("app.helpers.update_entity_helper.check_entity_exists", return_value=False):
            result = update_entity_helper.update_location(
                db, entity_id=1, data={"name": "New Name", "description": "Desc"}
            )
        
        assert loc_mock.name == "New Name"
        assert loc_mock.description == "Desc"
        assert result["name"] == "New Name"

    def test_update_location_not_found(self):
        """Negative: Raises 404 if location not found."""
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None
        
        with patch("app.helpers.update_entity_helper.db_operation"):
            with pytest.raises(HTTPException) as exc:
                update_entity_helper.update_location(db, 1, {})
        assert exc.value.status_code == 404

    def test_update_location_name_conflict(self):
        """Negative: Raises 409 if name exists."""
        db = MagicMock()
        loc_mock = MagicMock(spec=Location)
        loc_mock.id = 1
        loc_mock.name = "Old"
        
        db.query.return_value.filter.return_value.first.return_value = loc_mock
        
        with patch("app.helpers.update_entity_helper.db_operation"), \
             patch("app.helpers.update_entity_helper.check_entity_exists", return_value=True):
            
            with pytest.raises(HTTPException) as exc:
                update_entity_helper.update_location(db, 1, {"name": "Exists"})
        assert exc.value.status_code == 409

class TestUpdateBuilding:
    """Unit tests for update_building."""

    def test_update_building_success(self):
        """Positive: Updates building and resolves location."""
        db = MagicMock()
        bld_mock = MagicMock(spec=Building)
        bld_mock.id = 1
        bld_mock.name = "B1"
        
        loc_mock = MagicMock(spec=Location)
        loc_mock.id = 10
        
        # Mock building query
        db.query.return_value.filter.return_value.first.side_effect = [bld_mock, None, loc_mock] 
        # 1. get building -> bld_mock
        # 2. check name conflict -> None (no existing)
        # 3. get location -> loc_mock
        
        # NOTE: Side effects can be tricky if queries are added/removed.
        # Safer to mock based on call args or separate queries if possible, but side_effect is quick here 
        # assuming strict order. 
        # Actually, let's make it more robust by checking what's being queried if the order is complex.
        # But here logic is: get building, check name, get location.
        
        # Simpler approach: distinct mocks for distinct queries?
        # db.query(Building) and db.query(Location)
        # We can configure side_effect based on the model passed to query() if we mock db class, 
        # but db is a session instance.
        
        # Let's stick to sequence but ensure we account for all calls.
        # 1. Building get (id)
        # 2. Building get (name conflict) - only if name changed
        # 3. Location get (name) via get_entity_by_name
        
        db.query.return_value.filter.return_value.first.side_effect = [bld_mock, None]
        
        with patch("app.helpers.update_entity_helper.get_entity_by_name", return_value=loc_mock):
            result = update_entity_helper.update_building(
                db, 1, {"location_name": "Loc1"}
            )
        
        assert bld_mock.location_id == 10
        assert result["location_id"] == 10

    def test_update_building_not_found(self):
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None
        with pytest.raises(HTTPException) as exc:
            update_entity_helper.update_building(db, 1, {})
        assert exc.value.status_code == 404

    def test_update_building_location_not_found(self):
        """Negative: Raises 404 if location not found."""
        db = MagicMock()
        bld_mock = MagicMock(spec=Building)
        db.query.return_value.filter.return_value.first.side_effect = [bld_mock, None] # Building found, Location not
        
        with pytest.raises(HTTPException) as exc:
            update_entity_helper.update_building(db, 1, {"location_name": "Missing"})
        assert exc.value.status_code == 404
        assert "Location" in exc.value.detail


class TestUpdateWing:
    """Unit tests for update_wing."""
    
    @patch("app.helpers.update_entity_helper.get_entity_by_name")
    def test_update_wing_success(self, mock_get_entity):
        db = MagicMock()
        wing_mock = MagicMock(spec=Wing)
        wing_mock.id = 1
        wing_mock.location_id = 10
        wing_mock.building_id = 20
        
        db.query.return_value.filter.return_value.first.return_value = wing_mock
        
        result = update_entity_helper.update_wing(db, 1, {"name": "W2"})
        assert wing_mock.name == "W2"
        assert result["name"] == "W2"

    @patch("app.helpers.update_entity_helper.get_entity_by_name")
    def test_update_wing_location_change_clears_building(self, mock_get_entity):
        """Test that changing location clears building if it doesn't match."""
        db = MagicMock()
        wing_mock = MagicMock(spec=Wing)
        wing_mock.id = 1
        wing_mock.location_id = 10
        wing_mock.building_id = 20
        
        # Mock finding the wing
        # Then finding the current building to check its location
        building_mock = MagicMock(spec=Building)
        building_mock.id = 20
        building_mock.location_id = 10 # Old location matches old building
        
        db.query.return_value.filter.return_value.first.side_effect = [wing_mock, building_mock]
        
        # Mock new location lookup
        new_loc = MagicMock(spec=Location, id=99)
        mock_get_entity.return_value = new_loc
        
        result = update_entity_helper.update_wing(db, 1, {"location_name": "NewLoc"})
        
        assert wing_mock.location_id == 99
        # Building should be cleared because building_mock.location_id (10) != new location (99)
        assert wing_mock.building_id is None

    def test_update_wing_not_found(self):
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None
        with pytest.raises(HTTPException) as exc:
            update_entity_helper.update_wing(db, 1, {})
        assert exc.value.status_code == 404


class TestUpdateFloor:
    """Unit tests for update_floor."""
    
    @patch("app.helpers.update_entity_helper.get_entity_by_name")
    @patch("app.helpers.update_entity_helper.get_wing_by_name_scoped")
    def test_update_floor_success(self, mock_get_wing, mock_get_entity):
        db = MagicMock()
        floor_mock = MagicMock(spec=Floor)
        floor_mock.id = 1
        
        db.query.return_value.filter.return_value.first.return_value = floor_mock
        
        result = update_entity_helper.update_floor(db, 1, {"description": "New"})
        assert floor_mock.description == "New"

    @patch("app.helpers.update_entity_helper.get_entity_by_name")
    @patch("app.helpers.update_entity_helper.get_wing_by_name_scoped")
    def test_update_floor_hierarchy_change(self, mock_get_wing, mock_get_entity):
        """Test hierarchical updates."""
        db = MagicMock()
        floor_mock = MagicMock(spec=Floor, id=1, location_id=10, building_id=20, wing_id=30)
        
        db.query.return_value.filter.return_value.first.return_value = floor_mock
        
        # Mock looking up new wing
        new_wing = MagicMock(id=99)
        mock_get_wing.return_value = new_wing
        
        result = update_entity_helper.update_floor(db, 1, {"wing_name": "NewWing"})
        
        assert floor_mock.wing_id == 99
        # Ensure scoped lookup was called with current IDs
        mock_get_wing.assert_called_with(db, "NewWing", location_id=10, building_id=20)

    def test_update_floor_not_found(self):
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None
        with pytest.raises(HTTPException) as exc:
            update_entity_helper.update_floor(db, 1, {})
        assert exc.value.status_code == 404
    """Unit tests for update_rack in update_entity_helper."""
class TestUpdateDeviceType:
    def test_update_dt_success(self):
        db = MagicMock()
        dt = MagicMock(spec=DeviceType, id=1)
        db.query.return_value.filter.return_value.first.return_value = dt
        
        result = update_entity_helper.update_device_type(db, 1, {"name": "NewDT"})
        assert dt.name == "NewDT"

    def test_update_dt_not_found(self):
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None
        with pytest.raises(HTTPException):
            update_entity_helper.update_device_type(db, 1, {})

class TestUpdateMake:
    def test_update_make_success(self):
        db = MagicMock()
        make = MagicMock(spec=Make, id=1, name="M1")
        
        # 1. Get make by ID -> make
        # 2. Check conflict -> None
        db.query.return_value.filter.return_value.first.side_effect = [make, None]
        
        result = update_entity_helper.update_make(db, 1, {"name": "M2"})
        assert make.name == "M2"

    def test_update_make_not_found(self):
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None
        with pytest.raises(HTTPException):
            update_entity_helper.update_make(db, 1, {})

class TestUpdateModel:
    @patch("app.helpers.update_entity_helper.get_entity_by_name")
    @patch("app.helpers.update_entity_helper.get_device_type_by_name_scoped")
    def test_update_model_success(self, mock_get_dt, mock_get_entity):
        db = MagicMock()
        model = MagicMock(spec=Model, id=1, name="M1", make_id=10, device_type_id=20)
        
        # 1. Get model by ID
        # 2. Check conflict -> None (if name changed)
        # Note: name IS changed to M2. So conflict check runs.
        # 3. Validate DeviceType (if make/dt exists)
        dt_mock = MagicMock(spec=DeviceType, id=20, make_id=10)
        db.query.return_value.filter.return_value.first.side_effect = [model, None, dt_mock]
        
        result = update_entity_helper.update_model(db, 1, {"name": "M2", "height": 2})
        assert model.name == "M2"
        assert model.height == 2

    @patch("app.helpers.update_entity_helper.get_entity_by_name")
    def test_update_model_make_mismatch(self, mock_get_entity):
        """Test error when update clears device type due to make mismatch"""
        db = MagicMock()
        model = MagicMock(spec=Model, id=1, make_id=10, device_type_id=20)
        
        # 1. Get Model
        # 2. Get Make (mock lookup)
        # 3. Validation: get current device type -> fail validation
        
        # Mock Make lookup
        new_make = MagicMock(id=99)
        db.query.side_effect = None # Clear previous side effects if any on query itself? No rely on filter..first
        
        # Complex sequence:
        # q(Model).first() -> model
        # q(Make).first() -> new_make (via name lookup manually mocked? no, logic changed)
        # update_model calls:
        # 1. db.query(Model)
        # 2. db.query(Make)  (if make_name passed)
        # 3. db.query(DeviceType) (if make_id changed and device_type_id exists)
        
        # Let's mock db.query.return_value.filter.return_value.first side effects
        
        curr_dt = MagicMock(id=20, make_id=10) # Belongs to old make
        
        # Sequence:
        # 1. Get Model
        # 2. Get Make (user input)
        # 3. Get Current Device Type (to validate against new make)
        # 4. Get Make (for error message)
        db.query.return_value.filter.return_value.first.side_effect = [
            model, new_make, curr_dt, new_make 
        ]
        
        with pytest.raises(HTTPException) as exc:
             update_entity_helper.update_model(db, 1, {"make_name": "NewMake"})
        
        assert exc.value.status_code == 400
        assert "does not belong to make" in str(exc.value.detail)

    def test_update_model_not_found(self):
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None
        with pytest.raises(HTTPException):
            update_entity_helper.update_model(db, 1, {})

class TestUpdateAssetOwner:
    def test_update_ao_success(self):
        db = MagicMock()
        ao = MagicMock(spec=AssetOwner, id=1)
        db.query.return_value.filter.return_value.first.return_value = ao
        
        result = update_entity_helper.update_asset_owner(db, 1, {"name": "AO2"})
        assert ao.name == "AO2"

    def test_update_ao_not_found(self):
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None
        with pytest.raises(HTTPException):
            update_entity_helper.update_asset_owner(db, 1, {})

class TestUpdateApplication:
    def test_update_app_success(self):
        db = MagicMock()
        app = MagicMock(spec=ApplicationMapped, id=1)
        db.query.return_value.filter.return_value.first.return_value = app
        
        result = update_entity_helper.update_application(db, 1, {"name": "App2"})
        assert app.name == "App2"

    def test_update_app_not_found(self):
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None
        with pytest.raises(HTTPException):
            update_entity_helper.update_application(db, 1, {})

class TestUpdateRack:
    """Unit tests for update_rack."""
    def test_update_rack_invalid_height_reduction(self):
        """Negative: Cannot reduce height below used space."""
        db = MagicMock()
        rack_mock = MagicMock(spec=Rack)
        rack_mock.id = 1
        rack_mock.height = 42
        rack_mock.space_used = 20
        rack_mock.space_available = 22
        
        db.query.return_value.filter.return_value.first.return_value = rack_mock
        
        data = {"height": 10} # Less than used(20)

        with pytest.raises(HTTPException) as exc_info:
            update_entity_helper.update_rack(db, entity_id=1, data=data)
        
        assert exc_info.value.status_code == 400
        assert "Cannot reduce rack height" in exc_info.value.detail

    @patch("app.helpers.update_entity_helper.get_entity_by_name")
    @patch("app.helpers.update_entity_helper.get_datacenter_by_name_scoped")
    @patch("app.helpers.update_entity_helper.get_floor_by_name_scoped")
    @patch("app.helpers.update_entity_helper.get_wing_by_name_scoped")
    @patch("app.helpers.update_entity_helper.get_rack_by_name_scoped")
    def test_update_rack_success(self, mock_get_rack, mock_wing, mock_floor, mock_dc, mock_get_entity):
        """Positive: Successfully updates valid fields."""
        db = MagicMock()
        rack_mock = MagicMock(spec=Rack)
        rack_mock.id = 1
        rack_mock.height = 42
        rack_mock.space_used = 10
        rack_mock.location_id = 1
        rack_mock.building_id = 1
        rack_mock.wing_id = 1
        rack_mock.floor_id = 1
        rack_mock.datacenter_id = 1
        
        db.query.return_value.filter.return_value.first.return_value = rack_mock
        
        data = {"description": "New Dest", "height": 45}
        
        result = update_entity_helper.update_rack(db, entity_id=1, data=data)
        
        assert rack_mock.description == "New Dest"
        assert rack_mock.height == 45
        assert rack_mock.space_available == 35 # 45 - 10
        db.commit.assert_called_once()
        assert result["height"] == 45

    @patch("app.helpers.update_entity_helper.get_entity_by_name")
    def test_update_rack_clear_children(self, mock_get_entity):
        """Test clearing children when parent changes."""
        db = MagicMock()
        rack_mock = MagicMock(spec=Rack, id=1, location_id=10, building_id=20, wing_id=30)
        
        # Mock finding rack
        # Then finding building to check hierarchy
        current_building = MagicMock(id=20, location_id=10)
        # Add extras for deeper validation if needed (Wing, Floor, Datacenter if query propagates)
        # If wing_id=30, it might check Wing matches building(20).
        wing_mock = MagicMock(id=30, building_id=20)
        floor_mock = MagicMock(id=40, wing_id=30)
        dc_mock = MagicMock(id=50, floor_id=40)
        
        db.query.return_value.filter.return_value.first.side_effect = [
            rack_mock, current_building, wing_mock, floor_mock, dc_mock
        ]
        
        # New location
        new_loc = MagicMock(id=99)
        mock_get_entity.return_value = new_loc
        
        update_entity_helper.update_rack(db, 1, {"location_name": "NewLoc"})
        
        assert rack_mock.location_id == 99
        assert rack_mock.building_id is None # Cleared because old building doesn't match new loc


class TestUpdateDatacenter:
    """Unit tests for update_datacenter."""
    
    def test_update_datacenter_success(self):
        db = MagicMock()
        dc_mock = MagicMock(spec=Datacenter)
        dc_mock.id = 1
        
        db.query.return_value.filter.return_value.first.return_value = dc_mock
        
        result = update_entity_helper.update_datacenter(db, 1, {"name": "DC2"})
    
    @patch("app.helpers.update_entity_helper.get_datacenter_by_name_scoped")
    @patch("app.helpers.update_entity_helper.get_floor_by_name_scoped")
    @patch("app.helpers.update_entity_helper.get_wing_by_name_scoped")
    @patch("app.helpers.update_entity_helper.get_entity_by_name")
    def test_update_datacenter_hierarchy(self, mock_get, mock_wing, mock_floor, mock_dc):
        db = MagicMock()
        dc_mock = MagicMock(spec=Datacenter, id=1, location_id=1, building_id=1, wing_id=1, floor_id=1)
        db.query.return_value.filter.return_value.first.return_value = dc_mock
        
        new_floor = MagicMock(id=99)
        mock_floor.return_value = new_floor
        
        update_entity_helper.update_datacenter(db, 1, {"floor_name": "NewF"})
        
        assert dc_mock.floor_id == 99
        # assert dc_mock.name == "DC2" # Removed assertion as name not updated in this test

    def test_update_datacenter_not_found(self):
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None
        with pytest.raises(HTTPException) as exc:
            update_entity_helper.update_datacenter(db, 1, {})
        assert exc.value.status_code == 404


class TestUpdateDevice:
    """Unit tests for update_device in update_entity_helper."""

    def test_update_device_not_found(self):
        """Negative: Raises 404 if device not found."""
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None
        
        with patch("app.helpers.update_entity_helper.db_operation"):
            with pytest.raises(HTTPException) as exc_info:
                update_entity_helper.update_device(db, entity_id=999, data={})
            
            assert exc_info.value.status_code == 404
            assert "not found" in exc_info.value.detail

    @patch("app.helpers.update_entity_helper.get_entity_by_name")
    @patch("app.helpers.update_entity_helper.get_device_type_by_name_scoped")
    @patch("app.helpers.update_entity_helper._get_model_by_name_scoped")
    @patch("app.helpers.update_entity_helper.get_datacenter_by_name_scoped")
    @patch("app.helpers.update_entity_helper.get_floor_by_name_scoped")
    @patch("app.helpers.update_entity_helper.get_wing_by_name_scoped")
    @patch("app.helpers.update_entity_helper.get_rack_by_name_scoped")
    def test_update_device_success_simple(self, mock_rack, mock_wing, mock_floor, mock_dc, mock_model, mock_dt, mock_get_entity):
        """Positive: Updates basic fields without moving rack."""
        db = MagicMock()
        device_mock = MagicMock(spec=Device)
        device_mock.id = 1
        device_mock.rack = MagicMock(id=10) # Existing rack
        device_mock.space_required = 2
        device_mock.position = 5
        device_mock.make_id = 1
        device_mock.devicetype_id = 1
        device_mock.model_id = 1
        device_mock.location_id = 1
        device_mock.building_id = 1
        device_mock.wings_id = 1
        device_mock.floor_id = 1
        device_mock.dc_id = 1
        
        device_mock.wings_id = 1
        device_mock.floor_id = 1
        device_mock.dc_id = 1
        
        # Mock validation queries
        dt_mock = MagicMock(spec=DeviceType, id=1, make_id=1)
        model_mock = MagicMock(spec=Model, id=1, make_id=1, device_type_id=1)
        bld_mock = MagicMock(spec=Building, id=1, location_id=1)
        wing_mock = MagicMock(spec=Wing, id=1, location_id=1, building_id=1)
        floor_mock = MagicMock(spec=Floor, id=1, location_id=1, building_id=1, wing_id=1)
        dc_mock = MagicMock(spec=Datacenter, id=1, location_id=1, building_id=1, wing_id=1, floor_id=1)
        
        # Sequence: Device -> DeviceType -> Model -> Building -> Wing -> Floor -> Datacenter
        # Add extras to avoid StopIteration if internal logic checks more
        extra_mock = MagicMock()
        db.query.return_value.filter.return_value.first.side_effect = [
            device_mock, dt_mock, model_mock, bld_mock, wing_mock, floor_mock, dc_mock, extra_mock, extra_mock
        ]
        
        data = {"description": "Updated", "serial_no": "ABC"}

        with patch("app.helpers.update_entity_helper.db_operation"), \
             patch("app.helpers.update_entity_helper.sync_rack_usage"), \
             patch("app.helpers.update_entity_helper.ensure_continuous_space"), \
             patch("app.helpers.update_entity_helper.reserve_rack_capacity"), \
             patch("app.helpers.update_entity_helper.release_rack_capacity"):

            result = update_entity_helper.update_device(db, entity_id=1, data=data)
            
            assert device_mock.description == "Updated"
            assert device_mock.serial_no == "ABC"
            db.commit.assert_called_once()
            
    @patch("app.helpers.update_entity_helper.get_entity_by_name")
    @patch("app.helpers.update_entity_helper.get_rack_by_name_scoped")
    def test_update_device_move_rack(self, mock_get_rack_scoped, mock_get_entity):
        """Positive: Moves device to new rack, handling capacity."""
        db = MagicMock()
        device_mock = MagicMock(spec=Device)
        device_mock.space_required = 2
        device_mock.position = 5
        # Set FKs to None to avoid validation queries
        device_mock.make_id = None
        device_mock.devicetype_id = None
        device_mock.model_id = None
        device_mock.building_id = None
        device_mock.wings_id = None
        device_mock.floor_id = None
        device_mock.dc_id = None
        device_mock.location_id = None
        
        new_rack_mock = MagicMock(spec=Rack, id=20)
        mock_get_rack_scoped.return_value = new_rack_mock
        
        with patch("app.helpers.update_entity_helper.db_operation"), \
             patch("app.helpers.update_entity_helper.sync_rack_usage"), \
             patch("app.helpers.update_entity_helper.ensure_continuous_space") as mock_ensure, \
             patch("app.helpers.update_entity_helper.reserve_rack_capacity") as mock_reserve, \
             patch("app.helpers.update_entity_helper.release_rack_capacity") as mock_release:

            # Only device query needed if no other FKs set or updated
            db.query.return_value.filter.return_value.first.side_effect = [device_mock]
            
            data = {"rack_name": "NewRack", "position": 10}
            
            update_entity_helper.update_device(db, 1, data)
            
            # Verify capacity logic
            mock_release.assert_called_with(device_mock.rack, 2)
            mock_reserve.assert_called_with(new_rack_mock, 2)
            mock_ensure.assert_called()
            assert device_mock.rack_id == 20


# ============================================================
# Tests for update_rack Reference Failures
# ============================================================

def test_update_rack_building_not_found():
    db = MagicMock()
    rack_mock = MagicMock(spec=Rack, id=1)
    
    # 1. Get rack -> found
    # 2. Get building -> not found
    db.query.return_value.filter.return_value.first.side_effect = [rack_mock, None]
    
    with pytest.raises(HTTPException) as exc:
        update_rack(db, 1, {"building_name": "Missing"})
    assert exc.value.status_code == 404
    assert "Building with name" in exc.value.detail

def test_update_rack_location_not_found():
    db = MagicMock()
    rack_mock = MagicMock(spec=Rack, id=1)
    
    # 1. Get rack -> found
    # 2. Get location -> not found
    db.query.return_value.filter.return_value.first.side_effect = [rack_mock, None]
    
    with pytest.raises(HTTPException) as exc:
        update_rack(db, 1, {"location_name": "Missing"})
    assert exc.value.status_code == 404
    assert "Location with name" in exc.value.detail

# ============================================================
# Tests for update_device Edge Cases
# ============================================================

class TestUpdateDeviceExtended:
    
    def test_update_device_invalid_space(self):
        db = MagicMock()
        # Set FKs to None to avoid validation queries that cause AttributeError on spec=Device
        dev_mock = MagicMock(spec=Device, id=1, rack=None, space_required=1,
                             make_id=None, devicetype_id=None, model_id=None,
                             location_id=None, building_id=None, wings_id=None,
                             floor_id=None, dc_id=None)
        db.query.return_value.filter.return_value.first.return_value = dev_mock
        
        with patch("app.helpers.update_entity_helper.db_operation"):
            with pytest.raises(HTTPException) as exc:
                update_device(db, 1, {"space_required": 0})
            assert exc.value.status_code == 400
            assert "space_required must be greater than zero" in exc.value.detail

    def test_update_device_face_conversion(self):
        db = MagicMock()
        dev_mock = MagicMock(spec=Device, id=1, rack=None,
                             make_id=None, devicetype_id=None, model_id=None,
                             location_id=None, building_id=None, wings_id=None,
                             floor_id=None, dc_id=None)
        dev_mock.space_required = 1 # Set explicit int value
        db.query.return_value.filter.return_value.first.return_value = dev_mock
        
        with patch("app.helpers.update_entity_helper.db_operation"):
            # Test "Front"
            update_device(db, 1, {"face": "Front"})
            # Check implicit mutations on device mock data (which isn't strictly tracked unless we check setattr)
            # But the function writes back to data/fields
            # We can verify by return value if mapped
            
            # Re-mock for checking return dict
            result = update_device(db, 1, {"face": "Rear"})
            assert result["face_front"] == False
            assert result["face_rear"] == True

    def test_update_device_clear_rack(self):
        """Test clearing rack assignment (rack_name=empty)."""
        db = MagicMock()
        # Initial: Assigned to rack 10
        old_rack = MagicMock(spec=Rack, id=10)
        dev_mock = MagicMock(spec=Device, id=1, rack=old_rack, rack_id=10, space_required=2,
                             make_id=None, devicetype_id=None, model_id=None,
                             location_id=None, building_id=None, wings_id=None,
                             floor_id=None, dc_id=None)
        dev_mock.position = 5
        
        db.query.return_value.filter.return_value.first.return_value = dev_mock
        
        with patch("app.helpers.update_entity_helper.db_operation"), \
             patch("app.helpers.update_entity_helper.release_rack_capacity") as mock_release, \
             patch("app.helpers.update_entity_helper.reserve_rack_capacity") as mock_reserve, \
             patch("app.helpers.update_entity_helper.get_entity_by_name"): # Not called if rack_name empty string?
             
             # Passing empty string or None for rack_name should clear it? 
             # Code: if rack_name: ... else: target_rack=None
             # But if rack_name is "", get_entity_by_name might not be called if check is `if rack_name:`
             
             update_device(db, 1, {"rack_name": ""}) # Falsey string
             
             # Should release old rack capacity
             mock_release.assert_called_with(old_rack, 2)
             # Should NOT reserve new capacity
             mock_reserve.assert_not_called()
             # Device rack_id cleared
             assert dev_mock.rack_id is None

@patch("app.helpers.update_entity_helper.sync_rack_usage")
@patch("app.helpers.update_entity_helper.reserve_rack_capacity")
@patch("app.helpers.update_entity_helper.release_rack_capacity")
@patch("app.helpers.update_entity_helper.ensure_continuous_space")
class TestUpdateDeviceHierarchicalClearing:
    """Test that changing a parent entity clears mismatched children in Device update."""

    @patch("app.helpers.update_entity_helper.get_entity_by_name")
    def test_update_device_location_change_clears_building(self, mock_get_entity, mock_ensure, mock_release, mock_reserve, mock_sync):
        db = MagicMock()
        dev = MagicMock(spec=Device, id=1, 
                        location_id=1, building_id=2, wings_id=3, 
                        floor_id=4, dc_id=5, rack_id=6,
                        space_required=1,
                        make_id=None, devicetype_id=None, model_id=None)
        
        new_loc = MagicMock(spec=Location, id=99)
        mock_get_entity.return_value = new_loc
        
        cur_bld = MagicMock(spec=Building, id=2, location_id=1)
        cur_wing = MagicMock(spec=Wing, id=3, location_id=1)
        cur_floor = MagicMock(spec=Floor, id=4, location_id=1)
        cur_dc = MagicMock(spec=Datacenter, id=5, location_id=1)
        cur_rack = MagicMock(spec=Rack, id=6, location_id=1) 
        
        db.query.return_value.filter.return_value.first.side_effect = [
            dev, cur_bld, cur_wing, cur_floor, cur_dc, cur_rack
        ]
        
        update_entity_helper.update_device(db, 1, {"location_name": "NewLoc"})
        
        assert dev.location_id == 99
        assert dev.building_id is None
        assert dev.wings_id is None
        assert dev.floor_id is None
        assert dev.dc_id is None
        assert dev.rack_id is None 

    @patch("app.helpers.update_entity_helper.get_entity_by_name")
    def test_update_device_location_change_keeps_compliant_building(self, mock_get_entity, mock_ensure, mock_release, mock_reserve, mock_sync):
        """Test that if location changes but building is already in new location, it stays."""
        db = MagicMock()
        dev = MagicMock(spec=Device, id=1, 
                        location_id=1, building_id=2, wings_id=3, 
                        floor_id=4, dc_id=5, rack_id=6,
                        space_required=1,
                        make_id=None, devicetype_id=None, model_id=None)
        
        # New location
        new_loc = MagicMock(spec=Location, id=99)
        mock_get_entity.return_value = new_loc
        
        # Verify Building: ID=2, Location=99 (Already moved or shared)
        cur_bld = MagicMock(spec=Building, id=2, location_id=99)
        # Wing matches building and loc
        cur_wing = MagicMock(spec=Wing, id=3, building_id=2, location_id=99)
        # Floor matches hierarchy
        cur_floor = MagicMock(spec=Floor, id=4, wing_id=3, building_id=2, location_id=99)
        # DC matches hierarchy
        cur_dc = MagicMock(spec=Datacenter, id=5, floor_id=4, wing_id=3, building_id=2, location_id=99)
        # Rack matches hierarchy
        cur_rack = MagicMock(spec=Rack, id=6, datacenter_id=5, floor_id=4, wing_id=3, building_id=2, location_id=99)

        db.query.return_value.filter.return_value.first.side_effect = [
            dev, cur_bld, cur_wing, cur_floor, cur_dc, cur_rack
        ]
        
        update_entity_helper.update_device(db, 1, {"location_name": "NewLoc"})
        
        assert dev.location_id == 99
        assert dev.building_id == 2 # Kept
        assert dev.wings_id == 3 # Kept
        assert dev.floor_id == 4 # Kept
        assert dev.dc_id == 5 # Kept
        assert dev.rack_id == 6 # Kept

    def test_update_device_make_change_clears_dt_model(self, mock_ensure, mock_release, mock_reserve, mock_sync):
        db = MagicMock()
        dev = MagicMock(spec=Device, id=1, make_id=1, devicetype_id=2, model_id=3,
                        location_id=None, building_id=None, wings_id=None, floor_id=None, dc_id=None, rack_id=None,
                        space_required=1)
        
        with patch("app.helpers.update_entity_helper.get_entity_by_name") as mock_get_make:
            new_make = MagicMock(spec=Make, id=99)
            mock_get_make.return_value = new_make
            
            cur_dt = MagicMock(spec=DeviceType, id=2, make_id=1) 
            cur_model = MagicMock(spec=Model, id=3, make_id=1, device_type_id=2)
            
            db.query.return_value.filter.return_value.first.side_effect = [
                dev, cur_dt, cur_model
            ]
            
            update_entity_helper.update_device(db, 1, {"make_name": "NewMake"})
            
            assert dev.make_id == 99
            assert dev.devicetype_id is None
            assert dev.model_id is None

    def test_update_device_make_change_keeps_compliant_dt_model(self, mock_ensure, mock_release, mock_reserve, mock_sync):
        db = MagicMock()
        dev = MagicMock(spec=Device, id=1, make_id=1, devicetype_id=2, model_id=3,
                        location_id=None, building_id=None, wings_id=None, floor_id=None, dc_id=None, rack_id=None,
                        space_required=1)
        
        with patch("app.helpers.update_entity_helper.get_entity_by_name") as mock_get_make:
            new_make = MagicMock(spec=Make, id=99)
            mock_get_make.return_value = new_make
            
            # Current DT belongs to new make
            cur_dt = MagicMock(spec=DeviceType, id=2, make_id=99) 
            # Current Model belongs to new make and dt
            cur_model = MagicMock(spec=Model, id=3, make_id=99, device_type_id=2)
            
            db.query.return_value.filter.return_value.first.side_effect = [
                dev, cur_dt, cur_model
            ]
            
            update_entity_helper.update_device(db, 1, {"make_name": "NewMake"})
            
            assert dev.make_id == 99
            assert dev.devicetype_id == 2 # Kept
            assert dev.model_id == 3 # Kept

    @patch("app.helpers.update_entity_helper.get_entity_by_name")
    def test_update_device_building_change_clears_wing(self, mock_get_entity, mock_ensure, mock_release, mock_reserve, mock_sync):
        db = MagicMock()
        dev = MagicMock(spec=Device, id=1, location_id=1, building_id=2, wings_id=3,
                        make_id=None, devicetype_id=None, model_id=None, floor_id=None, dc_id=None, rack_id=None,
                        space_required=1)
        
        new_bld = MagicMock(spec=Building, id=99, location_id=1)
        mock_get_entity.return_value = new_bld
        
        cur_wing = MagicMock(spec=Wing, id=3, building_id=2)
        
        db.query.return_value.filter.return_value.first.side_effect = [dev, cur_wing]
        
        update_entity_helper.update_device(db, 1, {"building_name": "NewBld"})
        
        assert dev.building_id == 99
        assert dev.wings_id is None

    @patch("app.helpers.update_entity_helper.get_wing_by_name_scoped")
    def test_update_device_wing_change_clears_floor(self, mock_get_wing, mock_ensure, mock_release, mock_reserve, mock_sync):
        db = MagicMock()
        dev = MagicMock(spec=Device, id=1, building_id=2, wings_id=3, floor_id=4,
                        make_id=None, devicetype_id=None, model_id=None, dc_id=None, location_id=None, rack_id=None,
                        space_required=1)
        
        new_wing = MagicMock(spec=Wing, id=99, building_id=2)
        mock_get_wing.return_value = new_wing
        
        cur_floor = MagicMock(spec=Floor, id=4, wing_id=3)
        
        db.query.return_value.filter.return_value.first.side_effect = [dev, cur_floor]
        
        update_entity_helper.update_device(db, 1, {"wing_name": "NewWing"})
        
        assert dev.wings_id == 99
        assert dev.floor_id is None

@patch("app.helpers.update_entity_helper.sync_rack_usage")
@patch("app.helpers.update_entity_helper.reserve_rack_capacity")
@patch("app.helpers.update_entity_helper.release_rack_capacity")
@patch("app.helpers.update_entity_helper.ensure_continuous_space")
class TestUpdateDeviceScopedLookups:
    
    @patch("app.helpers.update_entity_helper.get_wing_by_name_scoped")
    @patch("app.helpers.update_entity_helper.get_entity_by_name") 
    def test_update_device_wing_scoped(self, mock_get_entity, mock_get_wing, mock_ensure, mock_release, mock_reserve, mock_sync):
        db = MagicMock()
        dev = MagicMock(spec=Device, id=1, location_id=10, building_id=20,
                        make_id=None, devicetype_id=None, model_id=None, wings_id=None, floor_id=None, dc_id=None, rack_id=None,
                        space_required=1)
        db.query.return_value.filter.return_value.first.return_value = dev
        
        mock_wing = MagicMock(id=99)
        mock_get_wing.return_value = mock_wing
        
        update_entity_helper.update_device(db, 1, {"wing_name": "W"})
        
        mock_get_wing.assert_called_with(db, "W", location_id=10, building_id=20)

    @patch("app.helpers.update_entity_helper.get_device_type_by_name_scoped")
    def test_update_device_type_scoped(self, mock_get_dt, mock_ensure, mock_release, mock_reserve, mock_sync):
        db = MagicMock()
        dev = MagicMock(spec=Device, id=1, make_id=10,
                        devicetype_id=None, model_id=None, location_id=None, building_id=None, wings_id=None, floor_id=None, dc_id=None, rack_id=None,
                        space_required=1)
        db.query.return_value.filter.return_value.first.return_value = dev
        
        mock_dt = MagicMock(id=99)
        mock_get_dt.return_value = mock_dt
        
        update_entity_helper.update_device(db, 1, {"devicetype_name": "DT"})
        
        mock_get_dt.assert_called_with(db, "DT", 10)
