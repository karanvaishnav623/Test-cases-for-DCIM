import pytest
from datetime import date, datetime
from app.models.entity_models import (
    Location,
    Building,
    Wing,
    Floor,
    Datacenter,
    Rack,
    Make,
    Model,
    DeviceType,
    AssetOwner,
    ApplicationMapped,
    Device,
)

class TestEntityModels:
    
    def test_location_model(self):
        """Positive: Verifies Location model."""
        loc = Location(name="NYC", description="Headquarters")
        assert loc.name == "NYC"
        assert loc.__tablename__ == "dcim_location"

    def test_hierarchy_models(self):
        """Positive: Verifies Building, Wing, Floor, Datacenter instantiation."""
        # Just checking instantiation and FK fields existence (at object level)
        bldg = Building(name="B1", location_id=1, status="active")
        assert bldg.status == "active"
        
        wing = Wing(name="West", location_id=1, building_id=1)
        assert wing.name == "West"
        
        floor = Floor(name="1st", location_id=1, building_id=1, wing_id=1)
        assert floor.name == "1st"
        
        dc = Datacenter(name="Main DC", location_id=1, building_id=1, wing_id=1, floor_id=1)
        assert dc.name == "Main DC"

    def test_rack_model(self):
        """Positive: Verifies Rack model and default capacity fields."""
        rack = Rack(
            name="R-01", 
            location_id=1, building_id=1, wing_id=1, floor_id=1, datacenter_id=1,
            height=42
        )
        assert rack.name == "R-01"
        assert rack.height == 42
        assert rack.status is None # Default on Column "active" applied on flush
        # Check defaults logic if we were using a session, but here checking mapped attributes
        assert rack.__tablename__ == "dcim_rack"

    def test_hardware_models(self):
        """Positive: Verifies Make, Model, DeviceType."""
        make = Make(name="Cisco")
        assert make.name == "Cisco"
        
        dtype = DeviceType(name="Switch", make_id=1)
        assert dtype.name == "Switch"
        
        model = Model(name="C9300", make_id=1, device_type_id=1, height=1)
        assert model.name == "C9300"
        assert model.height == 1

    def test_device_model(self):
        """Positive: Verifies Device model structure and fields."""
        dev = Device(
            name="sw-core-01",
            serial_no="SN12345",
            position=10,
            face_front=True,
            status="active",
            location_id=1, building_id=1,
            warranty_start_date=date(2023, 1, 1),
            space_required=2
        )
        assert dev.name == "sw-core-01"
        assert dev.face_front is True
        assert dev.warranty_start_date == date(2023, 1, 1)
        assert dev.space_required == 2
        assert dev.__tablename__ == "dcim_device"

    def test_asset_app_models(self):
        """Positive: Verifies AssetOwner and ApplicationMapped."""
        owner = AssetOwner(name="Finance", location_id=1)
        assert owner.name == "Finance"
        
        app = ApplicationMapped(name="ERP", asset_owner_id=1)
        assert app.name == "ERP"

    def test_relationships_exist(self):
        """Positive: Quick check that relationships are defined (by attribute access)."""
        # We can't fully test SQLAlchemy relationship mechanics without a session/DB,
        # but we can verify the class attributes exist.
        assert hasattr(Location, 'buildings')
        assert hasattr(Rack, 'devices')
        assert hasattr(Device, 'rack')
        assert hasattr(Device, 'model')
