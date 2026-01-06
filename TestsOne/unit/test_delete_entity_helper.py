import pytest
from unittest.mock import MagicMock, patch
from fastapi import HTTPException
from app.helpers import delete_entity_helper
from app.models.entity_models import (
    Location, Device, Rack, Building, Wing, Floor, Datacenter, 
    DeviceType, AssetOwner, Make, Model, ApplicationMapped
)

class TestDeleteEntityHelper:
    """Unit tests for delete_entity_helper module."""

    def test_delete_location_success(self):
        """Positive: Successfully deletes a location."""
        db = MagicMock()
        loc_mock = MagicMock(spec=Location)
        loc_mock.id = 1
        loc_mock.name = "Loc1"
        
        db.query.return_value.filter.return_value.first.return_value = loc_mock
        
        with patch("app.helpers.delete_entity_helper.db_operation"):
            result = delete_entity_helper.delete_location(db, entity_id=1)
            
            assert result["name"] == "Loc1"
            db.delete.assert_called_once_with(loc_mock)
            db.commit.assert_called_once()

    def test_delete_location_not_found(self):
        """Negative: Raises 404 if location not found."""
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None
        
        with patch("app.helpers.delete_entity_helper.db_operation"):
            with pytest.raises(HTTPException) as exc_info:
                delete_entity_helper.delete_location(db, entity_id=1)
            
            assert exc_info.value.status_code == 404
            assert "not found" in exc_info.value.detail

    def test_delete_device_releases_rack_capacity(self):
        """Positive: Deleting device releases rack capacity."""
        db = MagicMock()
        device_mock = MagicMock(spec=Device)
        device_mock.id = 10
        device_mock.name = "Dev1"
        device_mock.rack_id = 5
        device_mock.space_required = 2
        
        rack_mock = MagicMock(spec=Rack)
        device_mock.rack = rack_mock
        
        db.query.return_value.filter.return_value.first.return_value = device_mock
        
        with patch("app.helpers.delete_entity_helper.db_operation"), \
             patch("app.helpers.delete_entity_helper.release_rack_capacity") as mock_release:
            
            delete_entity_helper.delete_device(db, entity_id=10)
            
            mock_release.assert_called_once_with(rack_mock, 2)
            db.delete.assert_called_once_with(device_mock)
            db.commit.assert_called_once()

    def test_delete_building(self):
        """Positive: Successfully deletes a building."""
        db = MagicMock()
        bld_mock = MagicMock(spec=Building)
        bld_mock.id = 2
        bld_mock.name = "B1" # Explicitly set attribute
        bld_mock.status = "active"
        bld_mock.location_id = 1
        
        db.query.return_value.filter.return_value.first.return_value = bld_mock
        
        result = delete_entity_helper.delete_building(db, 2)
        assert result["name"] == "B1"
        db.delete.assert_called_once_with(bld_mock)

    def test_delete_building_not_found(self):
        """Negative: Raises 404 if building not found."""
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None
        with pytest.raises(HTTPException) as exc:
            delete_entity_helper.delete_building(db, 2)
        assert exc.value.status_code == 404

    def test_delete_wing(self):
        """Positive: Successfully deletes a wing."""
        db = MagicMock()
        wing_mock = MagicMock(spec=Wing)
        wing_mock.id = 3
        wing_mock.name = "W1"
        db.query.return_value.filter.return_value.first.return_value = wing_mock
        
        result = delete_entity_helper.delete_wing(db, 3)
        assert result["name"] == "W1"
        db.delete.assert_called_once_with(wing_mock)

    def test_delete_wing_not_found(self):
        """Negative: Raises 404 if wing not found."""
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None
        with pytest.raises(HTTPException) as exc:
            delete_entity_helper.delete_wing(db, 3)
        assert exc.value.status_code == 404

    def test_delete_floor(self):
        """Positive: Successfully deletes a floor."""
        db = MagicMock()
        floor_mock = MagicMock(spec=Floor)
        floor_mock.id = 4
        floor_mock.name = "F1"
        db.query.return_value.filter.return_value.first.return_value = floor_mock
        
        result = delete_entity_helper.delete_floor(db, 4)
        assert result["name"] == "F1"
        db.delete.assert_called_once_with(floor_mock)

    def test_delete_floor_not_found(self):
        """Negative: Raises 404 if floor not found."""
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None
        with pytest.raises(HTTPException) as exc:
            delete_entity_helper.delete_floor(db, 4)
        assert exc.value.status_code == 404

    def test_delete_datacenter(self):
        """Positive: Successfully deletes a datacenter."""
        db = MagicMock()
        dc_mock = MagicMock(spec=Datacenter)
        dc_mock.id = 5
        dc_mock.name = "DC1"
        db.query.return_value.filter.return_value.first.return_value = dc_mock
        
        result = delete_entity_helper.delete_datacenter(db, 5)
        assert result["name"] == "DC1"
        db.delete.assert_called_once_with(dc_mock)

    def test_delete_datacenter_not_found(self):
        """Negative: Raises 404 if datacenter not found."""
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None
        with pytest.raises(HTTPException) as exc:
            delete_entity_helper.delete_datacenter(db, 5)
        assert exc.value.status_code == 404

    def test_delete_rack(self):
        """Positive: Successfully deletes a rack."""
        db = MagicMock()
        rack_mock = MagicMock(spec=Rack)
        rack_mock.id = 6
        rack_mock.name = "R1"
        rack_mock.building_id = 1
        rack_mock.location_id = 1
        rack_mock.status = "active"
        db.query.return_value.filter.return_value.first.return_value = rack_mock
        
        result = delete_entity_helper.delete_rack(db, 6)
        assert result["name"] == "R1"
        db.delete.assert_called_once_with(rack_mock)

    def test_delete_rack_not_found(self):
        """Negative: Raises 404 if rack not found."""
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None
        with pytest.raises(HTTPException) as exc:
            delete_entity_helper.delete_rack(db, 6)
        assert exc.value.status_code == 404

    def test_delete_device_type(self):
        """Positive: Successfully deletes a device type."""
        db = MagicMock()
        dt_mock = MagicMock(spec=DeviceType)
        dt_mock.id = 7
        dt_mock.name = "DT1"
        dt_mock.make_id = 1
        db.query.return_value.filter.return_value.first.return_value = dt_mock
        
        result = delete_entity_helper.delete_device_type(db, 7)
        assert result["name"] == "DT1"
        db.delete.assert_called_once_with(dt_mock)

    def test_delete_device_type_not_found(self):
        """Negative: Raises 404 if device type not found."""
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None
        with pytest.raises(HTTPException) as exc:
            delete_entity_helper.delete_device_type(db, 7)
        assert exc.value.status_code == 404

    def test_delete_asset_owner(self):
        """Positive: Successfully deletes an asset owner."""
        db = MagicMock()
        ao_mock = MagicMock(spec=AssetOwner)
        ao_mock.id = 8
        ao_mock.name = "Owner1"
        ao_mock.location_id = 1
        db.query.return_value.filter.return_value.first.return_value = ao_mock
        
        result = delete_entity_helper.delete_asset_owner(db, 8)
        assert result["name"] == "Owner1"
        db.delete.assert_called_once_with(ao_mock)

    def test_delete_asset_owner_not_found(self):
        """Negative: Raises 404 if asset owner not found."""
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None
        with pytest.raises(HTTPException) as exc:
            delete_entity_helper.delete_asset_owner(db, 8)
        assert exc.value.status_code == 404

    def test_delete_make(self):
        """Positive: Successfully deletes a make."""
        db = MagicMock()
        make_mock = MagicMock(spec=Make)
        make_mock.id = 9
        make_mock.name = "Make1"
        db.query.return_value.filter.return_value.first.return_value = make_mock
        
        result = delete_entity_helper.delete_make(db, 9)
        assert result["name"] == "Make1"
        db.delete.assert_called_once_with(make_mock)

    def test_delete_make_not_found(self):
        """Negative: Raises 404 if make not found."""
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None
        with pytest.raises(HTTPException) as exc:
            delete_entity_helper.delete_make(db, 9)
        assert exc.value.status_code == 404

    def test_delete_model(self):
        """Positive: Successfully deletes a model."""
        db = MagicMock()
        model_mock = MagicMock(spec=Model)
        model_mock.id = 10
        model_mock.name = "Model1"
        model_mock.make_id = 9
        db.query.return_value.filter.return_value.first.return_value = model_mock
        
        result = delete_entity_helper.delete_model(db, 10)
        assert result["name"] == "Model1"
        db.delete.assert_called_once_with(model_mock)

    def test_delete_model_not_found(self):
        """Negative: Raises 404 if model not found."""
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None
        with pytest.raises(HTTPException) as exc:
            delete_entity_helper.delete_model(db, 10)
        assert exc.value.status_code == 404

    def test_delete_application(self):
        """Positive: Successfully deletes an application."""
        db = MagicMock()
        app_mock = MagicMock(spec=ApplicationMapped)
        app_mock.id = 11
        app_mock.name = "App1"
        db.query.return_value.filter.return_value.first.return_value = app_mock
        
        result = delete_entity_helper.delete_application(db, 11)
        assert result["name"] == "App1"
        db.delete.assert_called_once_with(app_mock)

    def test_delete_application_not_found(self):
        """Negative: Raises 404 if application not found."""
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None
        with pytest.raises(HTTPException) as exc:
            delete_entity_helper.delete_application(db, 11)
        assert exc.value.status_code == 404
