
import pytest
from pydantic import ValidationError
from datetime import date, datetime
from app.schemas.entity_schemas import (
    LocationCreate, LocationUpdate,
    BuildingCreate, BuildingUpdate,
    WingCreate, WingUpdate,
    FloorCreate, FloorUpdate,
    DatacenterCreate, DatacenterUpdate,
    RackCreate, RackUpdate,
    DeviceCreate, DeviceUpdate,
    DeviceTypeCreate, DeviceTypeUpdate,
    MakeCreate, MakeUpdate,
    ModelCreate, ModelUpdate,
    AssetOwnerCreate, AssetOwnerUpdate,
    ApplicationMappedCreate, ApplicationMappedUpdate
)

# =============================================================================
# Helpers
# =============================================================================

def check_field_coverage(schema_class, tested_fields):
    """
    Ensures that all fields in the schema are present in the tested_fields list.
    """
    model_fields = set(schema_class.model_fields.keys())
    assert model_fields == set(tested_fields), \
        f"Mismatch in tested fields for {schema_class.__name__}. Missing: {model_fields - set(tested_fields)}"

# =============================================================================
# Location Tests
# =============================================================================

class TestLocationCreate:
    @pytest.fixture
    def valid_data(self):
        return {
            "name": "New York",
            "description": "HQ",
            "build_image": "image.png"
        }

    def test_happy_path(self, valid_data):
        model = LocationCreate(**valid_data)
        assert model.name == valid_data["name"]

    @pytest.mark.parametrize("field, invalid_value", [
        ("name", ""), # min_length=1
        ("name", None),
        ("description", "x" * 256),
        ("build_image", 123), # Should be str
    ])
    def test_invalid_values(self, valid_data, field, invalid_value):
        data = valid_data.copy()
        data[field] = invalid_value
        with pytest.raises(ValidationError) as exc_info:
            LocationCreate(**data)
        assert any(e["loc"] == (field,) for e in exc_info.value.errors())

    @pytest.mark.parametrize("field, length, should_pass", [
        ("name", 255, True), ("name", 256, False),
        ("description", 255, True), ("description", 256, False),
    ])
    def test_bva_fields(self, valid_data, field, length, should_pass):
        data = valid_data.copy()
        data[field] = "x" * length
        if should_pass:
            model = LocationCreate(**data)
            assert len(getattr(model, field)) == length
        else:
            with pytest.raises(ValidationError) as exc_info:
                LocationCreate(**data)
            assert any(e["loc"] == (field,) for e in exc_info.value.errors())

    def test_missing_fields(self, valid_data):
        del valid_data["name"]
        with pytest.raises(ValidationError) as exc_info:
            LocationCreate(**valid_data)
        assert exc_info.value.errors()[0]["type"] == "missing"

    def test_field_coverage(self):
        check_field_coverage(LocationCreate, ["name", "description", "build_image"])


class TestLocationUpdate:
    @pytest.fixture
    def valid_data(self):
        return {"name": "NY Updated", "description": "Updated Desc"}

    def test_happy_path(self, valid_data):
        model = LocationUpdate(**valid_data)
        assert model.name == valid_data["name"]

    @pytest.mark.parametrize("field, length, should_pass", [
        ("name", 255, True), ("name", 256, False),
        ("description", 255, True), ("description", 256, False),
    ])
    def test_bva_fields(self, valid_data, field, length, should_pass):
        data = valid_data.copy()
        data[field] = "x" * length
        if should_pass:
            model = LocationUpdate(**data)
            assert len(getattr(model, field)) == length
        else:
            with pytest.raises(ValidationError) as exc_info:
                LocationUpdate(**data)
            assert any(e["loc"] == (field,) for e in exc_info.value.errors())

    def test_field_coverage(self):
        check_field_coverage(LocationUpdate, ["name", "description", "build_image"])


# =============================================================================
# Building Tests
# =============================================================================

class TestBuildingCreate:
    @pytest.fixture
    def valid_data(self):
        return {
            "name": "Building A",
            "status": "Active",
            "location_name": "New York",
            "description": "Main Building",
            "address": "123 St"
        }

    def test_happy_path(self, valid_data):
        model = BuildingCreate(**valid_data)
        assert model.name == valid_data["name"]

    @pytest.mark.parametrize("field, invalid_value", [
        ("name", ""),
        ("status", ""),
        ("location_name", ""),
        ("address", "x" * 501),
    ])
    def test_invalid_values(self, valid_data, field, invalid_value):
        data = valid_data.copy()
        data[field] = invalid_value
        with pytest.raises(ValidationError) as exc_info:
            BuildingCreate(**data)
        assert any(e["loc"] == (field,) for e in exc_info.value.errors())

    @pytest.mark.parametrize("field, length, should_pass", [
        ("name", 255, True), ("name", 256, False),
        ("status", 255, True), ("status", 256, False),
        ("location_name", 255, True), ("location_name", 256, False),
        ("description", 255, True), ("description", 256, False),
        ("address", 500, True), ("address", 501, False),
    ])
    def test_bva_fields(self, valid_data, field, length, should_pass):
        data = valid_data.copy()
        data[field] = "x" * length
        if should_pass:
            model = BuildingCreate(**data)
            assert len(getattr(model, field)) == length
        else:
            with pytest.raises(ValidationError) as exc_info:
                BuildingCreate(**data)
            assert any(e["loc"] == (field,) for e in exc_info.value.errors())

    @pytest.mark.parametrize("field", ["name", "status", "location_name"])
    def test_missing_fields(self, valid_data, field):
        data = valid_data.copy()
        del data[field]
        with pytest.raises(ValidationError) as exc_info:
            BuildingCreate(**data)
        assert exc_info.value.errors()[0]["type"] == "missing"

    def test_field_coverage(self):
        check_field_coverage(BuildingCreate, ["name", "status", "location_name", "description", "address"])


class TestBuildingUpdate:
    @pytest.fixture
    def valid_data(self):
        return {"name": "Building B", "location_id": 1}

    @pytest.mark.parametrize("field, length, should_pass", [
        ("name", 255, True), ("name", 256, False),
        ("status", 255, True), ("status", 256, False),
        ("location_name", 255, True), ("location_name", 256, False),
        ("description", 255, True), ("description", 256, False),
        ("address", 500, True), ("address", 501, False),
    ])
    def test_bva_fields(self, valid_data, field, length, should_pass):
        data = valid_data.copy()
        data[field] = "x" * length
        if should_pass:
            model = BuildingUpdate(**data)
            assert len(getattr(model, field)) == length
        else:
            with pytest.raises(ValidationError) as exc_info:
                BuildingUpdate(**data)
            assert any(e["loc"] == (field,) for e in exc_info.value.errors())

    def test_invalid_refs(self, valid_data):
        valid_data["location_id"] = 0
        with pytest.raises(ValidationError):
            BuildingUpdate(**valid_data)

    def test_field_coverage(self):
        check_field_coverage(BuildingUpdate, ["name", "status", "location_id", "location_name", "description", "address"])

# =============================================================================
# Wing Tests
# =============================================================================

class TestWingCreate:
    @pytest.fixture
    def valid_data(self):
        return {
            "name": "East Wing",
            "location_name": "New York",
            "building_name": "Building A",
            "description": "East side"
        }

    @pytest.mark.parametrize("field, length, should_pass", [
        ("name", 255, True), ("name", 256, False),
        ("location_name", 255, True), ("location_name", 256, False),
        ("building_name", 255, True), ("building_name", 256, False),
        ("description", 255, True), ("description", 256, False),
    ])
    def test_bva_fields(self, valid_data, field, length, should_pass):
        data = valid_data.copy()
        data[field] = "x" * length
        if should_pass:
            WingCreate(**data)
        else:
            with pytest.raises(ValidationError):
                WingCreate(**data)

    @pytest.mark.parametrize("field", ["name", "location_name", "building_name"])
    def test_missing_fields(self, valid_data, field):
        del valid_data[field]
        with pytest.raises(ValidationError) as exc_info:
            WingCreate(**valid_data)
        assert exc_info.value.errors()[0]["type"] == "missing"

    def test_field_coverage(self):
        check_field_coverage(WingCreate, ["name", "location_name", "building_name", "description"])


class TestWingUpdate:
    @pytest.fixture
    def valid_data(self):
        return {"name": "West Wing"}

    @pytest.mark.parametrize("field, length, should_pass", [
        ("name", 255, True), ("name", 256, False),
        ("location_name", 255, True), ("location_name", 256, False),
        ("building_name", 255, True), ("building_name", 256, False),
        ("description", 255, True), ("description", 256, False),
    ])
    def test_bva_fields(self, valid_data, field, length, should_pass):
        data = valid_data.copy()
        data[field] = "x" * length
        if should_pass:
            WingUpdate(**data)
        else:
            with pytest.raises(ValidationError):
                WingUpdate(**data)

    def test_field_coverage(self):
        check_field_coverage(WingUpdate, ["name", "location_id", "building_id", "location_name", "building_name", "description"])


# =============================================================================
# Floor Tests
# =============================================================================

class TestFloorCreate:
    @pytest.fixture
    def valid_data(self):
        return {
            "name": "1st Floor",
            "location_name": "New York",
            "building_name": "Building A",
            "wing_name": "East Wing",
            "description": "Ground floor"
        }

    @pytest.mark.parametrize("field, length, should_pass", [
        ("name", 255, True), ("name", 256, False),
        ("location_name", 255, True), ("location_name", 256, False),
        ("building_name", 255, True), ("building_name", 256, False),
        ("wing_name", 255, True), ("wing_name", 256, False),
        ("description", 255, True), ("description", 256, False),
    ])
    def test_bva_fields(self, valid_data, field, length, should_pass):
        data = valid_data.copy()
        data[field] = "x" * length
        if should_pass:
            FloorCreate(**data)
        else:
            with pytest.raises(ValidationError):
                FloorCreate(**data)

    @pytest.mark.parametrize("field", ["name", "location_name", "building_name", "wing_name"])
    def test_missing_fields(self, valid_data, field):
        del valid_data[field]
        with pytest.raises(ValidationError) as exc_info:
            FloorCreate(**valid_data)
        assert exc_info.value.errors()[0]["type"] == "missing"

    def test_field_coverage(self):
        check_field_coverage(FloorCreate, ["name", "location_name", "building_name", "wing_name", "description"])


class TestFloorUpdate:
    @pytest.fixture
    def valid_data(self):
        return {"name": "2nd Floor"}

    @pytest.mark.parametrize("field, length, should_pass", [
        ("name", 255, True), ("name", 256, False),
        ("location_name", 255, True), ("location_name", 256, False),
        ("building_name", 255, True), ("building_name", 256, False),
        ("wing_name", 255, True), ("wing_name", 256, False),
        ("description", 255, True), ("description", 256, False),
    ])
    def test_bva_fields(self, valid_data, field, length, should_pass):
        data = valid_data.copy()
        data[field] = "x" * length
        if should_pass:
            FloorUpdate(**data)
        else:
            with pytest.raises(ValidationError):
                FloorUpdate(**data)

    def test_field_coverage(self):
        check_field_coverage(FloorUpdate, ["name", "location_id", "building_id", "wing_id", "location_name", "building_name", "wing_name", "description"])


# =============================================================================
# Datacenter Tests
# =============================================================================

class TestDatacenterCreate:
    @pytest.fixture
    def valid_data(self):
        return {
            "name": "DC 1",
            "location_name": "New York",
            "building_name": "Building A",
            "wing_name": "East Wing",
            "floor_name": "1st Floor",
            "description": "Main DC"
        }

    @pytest.mark.parametrize("field, length, should_pass", [
        ("name", 255, True), ("name", 256, False),
        ("location_name", 255, True), ("location_name", 256, False),
        ("building_name", 255, True), ("building_name", 256, False),
        ("wing_name", 255, True), ("wing_name", 256, False),
        ("floor_name", 255, True), ("floor_name", 256, False),
        ("description", 255, True), ("description", 256, False),
    ])
    def test_bva_fields(self, valid_data, field, length, should_pass):
        data = valid_data.copy()
        data[field] = "x" * length
        if should_pass:
            DatacenterCreate(**data)
        else:
            with pytest.raises(ValidationError):
                DatacenterCreate(**data)

    @pytest.mark.parametrize("field", ["name", "location_name", "building_name", "wing_name", "floor_name"])
    def test_missing_fields(self, valid_data, field):
        del valid_data[field]
        with pytest.raises(ValidationError) as exc_info:
            DatacenterCreate(**valid_data)
        assert exc_info.value.errors()[0]["type"] == "missing"

    def test_field_coverage(self):
        check_field_coverage(DatacenterCreate, ["name", "location_name", "building_name", "wing_name", "floor_name", "description"])


class TestDatacenterUpdate:
    @pytest.fixture
    def valid_data(self):
        return {"name": "DC 2"}

    @pytest.mark.parametrize("field, length, should_pass", [
        ("name", 255, True), ("name", 256, False),
        ("location_name", 255, True), ("location_name", 256, False),
        ("building_name", 255, True), ("building_name", 256, False),
        ("wing_name", 255, True), ("wing_name", 256, False),
        ("floor_name", 255, True), ("floor_name", 256, False),
        ("description", 255, True), ("description", 256, False),
    ])
    def test_bva_fields(self, valid_data, field, length, should_pass):
        data = valid_data.copy()
        data[field] = "x" * length
        if should_pass:
            DatacenterUpdate(**data)
        else:
            with pytest.raises(ValidationError):
                DatacenterUpdate(**data)

    def test_field_coverage(self):
        check_field_coverage(DatacenterUpdate, ["name", "location_id", "building_id", "wing_id", "floor_id", "location_name", "building_name", "wing_name", "floor_name", "description"])

# =============================================================================
# Rack Tests
# =============================================================================

class TestRackCreate:
    @pytest.fixture
    def valid_data(self):
        return {
            "name": "Rack 1",
            "location_name": "NY", "building_name": "B1", "wing_name": "W1", "floor_name": "F1",
            "datacenter_name": "DC1", "status": "Active", "height": 42,
            "description": "Server Rack"
        }

    @pytest.mark.parametrize("field, length, should_pass", [
        ("name", 255, True), ("name", 256, False),
        ("location_name", 255, True), ("location_name", 256, False),
        ("building_name", 255, True), ("building_name", 256, False),
        ("wing_name", 255, True), ("wing_name", 256, False),
        ("floor_name", 255, True), ("floor_name", 256, False),
        ("datacenter_name", 255, True), ("datacenter_name", 256, False),
        ("status", 255, True), ("status", 256, False),
        ("description", 255, True), ("description", 256, False),
    ])
    def test_bva_fields(self, valid_data, field, length, should_pass):
        data = valid_data.copy()
        data[field] = "x" * length
        if should_pass:
            RackCreate(**data)
        else:
            with pytest.raises(ValidationError):
                RackCreate(**data)

    def test_invalid_height(self, valid_data):
        valid_data["height"] = 0
        with pytest.raises(ValidationError):
            RackCreate(**valid_data)

    @pytest.mark.parametrize("field", ["name", "location_name", "building_name", "wing_name", "floor_name", "datacenter_name", "status", "height"])
    def test_missing_fields(self, valid_data, field):
        del valid_data[field]
        with pytest.raises(ValidationError) as exc_info:
            RackCreate(**valid_data)
        assert exc_info.value.errors()[0]["type"] == "missing"

    def test_field_coverage(self):
        check_field_coverage(RackCreate, ["name", "location_name", "building_name", "wing_name", "floor_name", "datacenter_name", "status", "height", "description"])

class TestRackUpdate:
    @pytest.fixture
    def valid_data(self):
        return {"name": "Rack Updated"}

    @pytest.mark.parametrize("field, length, should_pass", [
        ("name", 255, True), ("name", 256, False),
        ("location_name", 255, True), ("location_name", 256, False),
        ("building_name", 255, True), ("building_name", 256, False),
        ("wing_name", 255, True), ("wing_name", 256, False),
        ("floor_name", 255, True), ("floor_name", 256, False),
        ("datacenter_name", 255, True), ("datacenter_name", 256, False),
        ("status", 255, True), ("status", 256, False),
        ("description", 255, True), ("description", 256, False),
    ])
    def test_bva_fields(self, valid_data, field, length, should_pass):
        data = valid_data.copy()
        data[field] = "x" * length
        if should_pass:
            RackUpdate(**data)
        else:
            with pytest.raises(ValidationError):
                RackUpdate(**data)

    def test_field_coverage(self):
        check_field_coverage(RackUpdate, ["name", "building_id", "location_id", "wing_id", "floor_id", "datacenter_id", "building_name", "location_name", "wing_name", "floor_name", "datacenter_name", "status", "height", "description"])


# =============================================================================
# Make, Model, DeviceType Tests
# =============================================================================

class TestMakeCreate:
    @pytest.fixture
    def valid_data(self):
        return {"name": "Cisco", "description": "Networking"}
    
    @pytest.mark.parametrize("field, length, should_pass", [
        ("name", 255, True), ("name", 256, False),
        ("description", 255, True), ("description", 256, False),
    ])
    def test_bva(self, valid_data, field, length, should_pass):
        data = valid_data.copy()
        data[field] = "x" * length
        if should_pass: MakeCreate(**data)
        else: 
            with pytest.raises(ValidationError): MakeCreate(**data)

    @pytest.mark.parametrize("field", ["name"])
    def test_missing_fields(self, valid_data, field):
        del valid_data[field]
        with pytest.raises(ValidationError) as exc_info:
            MakeCreate(**valid_data)
        assert exc_info.value.errors()[0]["type"] == "missing"

    def test_field_coverage(self): check_field_coverage(MakeCreate, ["name", "description"])

class TestMakeUpdate:
    @pytest.fixture
    def valid_data(self): return {"name": "CiscoUpdated"}
    
    def test_bva(self, valid_data):
        data = valid_data.copy()
        data["name"] = "x" * 256
        with pytest.raises(ValidationError): MakeUpdate(**data)

    def test_field_coverage(self): check_field_coverage(MakeUpdate, ["name", "description"])

class TestDeviceTypeCreate:
    @pytest.fixture
    def valid_data(self):
        return {"name": "Switch", "make_name": "Cisco", "description": "L2 Switch"}

    @pytest.mark.parametrize("field, length, should_pass", [
        ("name", 255, True), ("name", 256, False),
        ("make_name", 255, True), ("make_name", 256, False),
        ("description", 255, True), ("description", 256, False),
    ])
    def test_bva(self, valid_data, field, length, should_pass):
        data = valid_data.copy()
        data[field] = "x" * length
        if should_pass: DeviceTypeCreate(**data)
        else: 
            with pytest.raises(ValidationError): DeviceTypeCreate(**data)

    @pytest.mark.parametrize("field", ["name", "make_name"])
    def test_missing_fields(self, valid_data, field):
        del valid_data[field]
        with pytest.raises(ValidationError) as exc_info:
            DeviceTypeCreate(**valid_data)
        assert exc_info.value.errors()[0]["type"] == "missing"

    def test_field_coverage(self): check_field_coverage(DeviceTypeCreate, ["name", "make_name", "description"])

class TestDeviceTypeUpdate:
    def test_field_coverage(self): check_field_coverage(DeviceTypeUpdate, ["name", "make_id", "make_name", "description"])


class TestModelCreate:
    @pytest.fixture
    def valid_data(self):
        return {
            "name": "C9300", "make_name": "Cisco", "devicetype_name": "Switch", "height": 1,
            "description": "Catalyst 9300", "front_image": "abc", "rear_image": "xyz"
        }

    @pytest.mark.parametrize("field, length, should_pass", [
        ("name", 255, True), ("name", 256, False),
        ("make_name", 255, True), ("make_name", 256, False),
        ("devicetype_name", 255, True), ("devicetype_name", 256, False),
        ("description", 255, True), ("description", 256, False),
    ])
    def test_bva(self, valid_data, field, length, should_pass):
        data = valid_data.copy()
        data[field] = "x" * length
        if should_pass: ModelCreate(**data)
        else: 
            with pytest.raises(ValidationError): ModelCreate(**data)

    @pytest.mark.parametrize("field", ["name", "make_name", "devicetype_name", "height"])
    def test_missing_fields(self, valid_data, field):
        del valid_data[field]
        with pytest.raises(ValidationError) as exc_info:
            ModelCreate(**valid_data)
        assert exc_info.value.errors()[0]["type"] == "missing"

    def test_field_coverage(self):
        check_field_coverage(ModelCreate, ["name", "make_name", "devicetype_name", "height", "description", "front_image", "rear_image"])

class TestModelUpdate:
    def test_field_coverage(self):
        check_field_coverage(ModelUpdate, ["name", "make_id", "make_name", "devicetype_name", "height", "description", "front_image", "rear_image"])


# =============================================================================
# AssetOwner & ApplicationMapped Tests
# =============================================================================

class TestAssetOwnerCreate:
    @pytest.fixture
    def valid_data(self):
        return {"name": "Network Team", "location_name": "NY", "description": "NetOps"}
    
    @pytest.mark.parametrize("field, length, should_pass", [
        ("name", 255, True), ("name", 256, False),
        ("location_name", 255, True), ("location_name", 256, False),
        ("description", 255, True), ("description", 256, False),
    ])
    def test_bva(self, valid_data, field, length, should_pass):
        data = valid_data.copy()
        data[field] = "x" * length
        if should_pass: AssetOwnerCreate(**data)
        else: 
            with pytest.raises(ValidationError): AssetOwnerCreate(**data)

    @pytest.mark.parametrize("field", ["name", "location_name"])
    def test_missing_fields(self, valid_data, field):
        del valid_data[field]
        with pytest.raises(ValidationError) as exc_info:
            AssetOwnerCreate(**valid_data)
        assert exc_info.value.errors()[0]["type"] == "missing"

    def test_field_coverage(self): check_field_coverage(AssetOwnerCreate, ["name", "location_name", "description"])

class TestAssetOwnerUpdate:
    def test_field_coverage(self): check_field_coverage(AssetOwnerUpdate, ["name", "location_id", "location_name", "description"])

class TestApplicationMappedCreate:
    @pytest.fixture
    def valid_data(self):
        return {"name": "CRM", "asset_owner_name": "IT", "description": "Customer DB"}
    
    def test_bva(self, valid_data):
        data = valid_data.copy()
        data["name"] = "x" * 256
        with pytest.raises(ValidationError): ApplicationMappedCreate(**data)

    @pytest.mark.parametrize("field", ["name", "asset_owner_name"])
    def test_missing_fields(self, valid_data, field):
        del valid_data[field]
        with pytest.raises(ValidationError) as exc_info:
            ApplicationMappedCreate(**valid_data)
        assert exc_info.value.errors()[0]["type"] == "missing"

    def test_field_coverage(self): check_field_coverage(ApplicationMappedCreate, ["name", "asset_owner_name", "description"])

# =============================================================================
# Device Tests
# =============================================================================

class TestDeviceCreate:
    @pytest.fixture
    def valid_data(self):
        return {
            "name": "Server-01",
            "serial_no": "SN123456",
            "position": 10,
            "face": "Front",
            "status": "Active",
            "devicetype_name": "Server",
            "location_name": "NY",
            "building_name": "B1",
            "rack_name": "R1",
            "datacenter_name": "DC1",
            "wing_name": "W1",
            "floor_name": "F1",
            "make_name": "Dell",
            "model_name": "PowerEdge",
            "ip": "192.168.1.10",
            "po_number": "PO-999",
            "asset_user": "John",
            "asset_owner_name": "IT",
            "application_name": "App1",
            "warranty_start_date": date.today(),
            "warranty_end_date": date.today(),
            "amc_start_date": date.today(),
            "amc_end_date": date.today(),
            "description": "Primary Server"
        }

    @pytest.mark.parametrize("field, length, should_pass", [
        ("name", 255, True), ("name", 256, False),
        ("serial_no", 255, True), ("serial_no", 256, False),
        ("face", 255, True), ("face", 256, False),
        ("status", 255, True), ("status", 256, False),
        ("devicetype_name", 255, True), ("devicetype_name", 256, False),
        ("location_name", 255, True), ("location_name", 256, False),
        ("building_name", 255, True), ("building_name", 256, False),
        ("rack_name", 255, True), ("rack_name", 256, False),
        ("datacenter_name", 255, True), ("datacenter_name", 256, False),
        ("wing_name", 255, True), ("wing_name", 256, False),
        ("floor_name", 255, True), ("floor_name", 256, False),
        ("make_name", 255, True), ("make_name", 256, False),
        ("model_name", 255, True), ("model_name", 256, False),
        ("ip", 255, True), ("ip", 256, False),
        ("po_number", 255, True), ("po_number", 256, False),
        ("asset_user", 255, True), ("asset_user", 256, False),
        ("asset_owner_name", 255, True), ("asset_owner_name", 256, False),
        ("application_name", 255, True), ("application_name", 256, False),
        ("description", 255, True), ("description", 256, False),
    ])
    def test_bva_fields(self, valid_data, field, length, should_pass):
        data = valid_data.copy()
        data[field] = "x" * length
        if should_pass:
            DeviceCreate(**data)
        else:
            with pytest.raises(ValidationError):
                DeviceCreate(**data)

    @pytest.mark.parametrize("field", [
        "name", "serial_no", "position", "face", "status",
        "devicetype_name", "location_name", "building_name", "rack_name", "datacenter_name",
        "wing_name", "floor_name", "make_name", "model_name",
        "ip", "po_number", "asset_user", "asset_owner_name", "application_name",
        "warranty_start_date", "warranty_end_date", "amc_start_date", "amc_end_date"
    ])
    def test_missing_fields(self, valid_data, field):
        del valid_data[field]
        with pytest.raises(ValidationError) as exc_info:
            DeviceCreate(**valid_data)
        assert exc_info.value.errors()[0]["type"] == "missing"

    def test_field_coverage(self):
        check_field_coverage(DeviceCreate, [
            "name", "serial_no", "position", "face", "status",
            "devicetype_name", "location_name", "building_name", "rack_name", "datacenter_name",
            "wing_name", "floor_name", "make_name", "model_name",
            "ip", "po_number", "asset_user", "asset_owner_name", "application_name",
            "warranty_start_date", "warranty_end_date", "amc_start_date", "amc_end_date",
            "description"
        ])


class TestDeviceUpdate:
    @pytest.fixture
    def valid_data(self):
        return {"name": "Server-01-Updated"}

    @pytest.mark.parametrize("field, length, should_pass", [
        ("name", 255, True), ("name", 256, False),
        ("serial_no", 255, True), ("serial_no", 256, False),
        ("face", 255, True), ("face", 256, False),
        ("status", 255, True), ("status", 256, False),
        ("model_name", 255, True), ("model_name", 256, False),
        ("devicetype_name", 255, True), ("devicetype_name", 256, False),
        ("building_name", 255, True), ("building_name", 256, False),
        ("location_name", 255, True), ("location_name", 256, False),
        ("rack_name", 255, True), ("rack_name", 256, False),
        ("datacenter_name", 255, True), ("datacenter_name", 256, False),
        ("wing_name", 255, True), ("wing_name", 256, False),
        ("floor_name", 255, True), ("floor_name", 256, False),
        ("make_name", 255, True), ("make_name", 256, False),
        ("application_name", 255, True), ("application_name", 256, False),
        ("ip", 255, True), ("ip", 256, False),
        ("po_number", 255, True), ("po_number", 256, False),
        ("asset_user", 255, True), ("asset_user", 256, False),
        ("description", 255, True), ("description", 256, False),
    ])
    def test_bva_fields(self, valid_data, field, length, should_pass):
        data = valid_data.copy()
        data[field] = "x" * length
        if should_pass:
            DeviceUpdate(**data)
        else:
            with pytest.raises(ValidationError):
                DeviceUpdate(**data)

    def test_field_coverage(self):
        check_field_coverage(DeviceUpdate, [
            "name", "serial_no", "position", "face", "status",
            "devicetype_id", "building_id", "location_id", "rack_id", "dc_id", 
            "wings_id", "floor_id", "make_id", "model_id",
            "model_name", "devicetype_name", "building_name", "location_name", "rack_name", 
            "datacenter_name", "wing_name", "floor_name", "make_name", "application_name",
            "ip", "po_number", "asset_user", "applications_mapped_id",
            "warranty_start_date", "warranty_end_date", "amc_start_date", "amc_end_date",
            "space_required", "description"
        ])
