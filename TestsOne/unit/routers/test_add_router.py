import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from fastapi import HTTPException
from app.dcim.routers import add_router
from app.helpers.listing_types import ListingType

@pytest.mark.asyncio
class TestAddRouter:
    """Unit tests for add_router module."""

    async def test_add_entity_success(self):
        """Positive: Successfully calls handler and returns result."""
        # Mocks
        request = AsyncMock()
        request.json.return_value = {"name": "Rack1", "height": 42}
        
        access_level = MagicMock()
        current_user = MagicMock()
        db = MagicMock()

        # Schema mock
        schema_mock = MagicMock()
        schema_instance = MagicMock()
        schema_instance.model_dump.return_value = {"name": "Rack1", "height": 42}
        schema_mock.return_value = schema_instance
        # make is_required returns False to skip required check logic validation for this test
        # or we mock check_required_fields
        
        # Handler mock
        handler_mock = MagicMock(return_value={"id": 1, "name": "Rack1"})
        
        with patch("app.dcim.routers.add_router._get_create_schemas", return_value={ListingType.racks: schema_mock}), \
             patch("app.dcim.routers.add_router._get_create_handlers", return_value={ListingType.racks: handler_mock}), \
             patch("app.dcim.routers.add_router.check_required_fields"), \
             patch("app.dcim.routers.add_router.check_row_uniqueness"), \
             patch("app.dcim.routers.add_router.log_create"), \
             patch("app.dcim.routers.add_router.invalidate_listing_cache_for_entity"), \
             patch("app.dcim.routers.add_router.invalidate_location_summary_cache"):

            result = await add_router.add_entity(
                request=request,
                entity=ListingType.racks,
                access_level=access_level,
                current_user=current_user,
                db=db
            )
            
            assert result["message"] == "racks created successfully"
            assert result["data"]["id"] == 1
            handler_mock.assert_called_once()
            db.commit.assert_called_once()

    async def test_add_entity_invalid_json(self):
        """Negative: Raises 400 on invalid JSON."""
        request = AsyncMock()
        request.json.side_effect = Exception("JSON Error")
        
        with pytest.raises(HTTPException) as exc_info:
            await add_router.add_entity(
                request=request,
                entity=ListingType.racks,
                access_level=MagicMock(),
                current_user=MagicMock(),
                db=MagicMock()
            )
        
        assert exc_info.value.status_code == 400
        assert "Invalid JSON" in exc_info.value.detail

    async def test_add_entity_unsupported_type(self):
        """Negative: Raises 400 for unsupported entity (e.g. no schema)."""
        request = AsyncMock()
        request.json.return_value = {}
        
        with patch("app.dcim.routers.add_router._get_create_schemas", return_value={}):
            with pytest.raises(HTTPException) as exc_info:
                await add_router.add_entity(
                    request=request,
                    entity=ListingType.racks,
                    access_level=MagicMock(),
                    current_user=MagicMock(),
                    db=MagicMock()
                )
        
        assert exc_info.value.status_code == 400
        assert "Unsupported entity type" in exc_info.value.detail

    def test_check_required_fields_missing(self):
        """Negative: Raises 400 if required field missing."""
        data = {"name": "Test"}
        
        # Schema with required field 'height'
        field_mock = MagicMock()
        field_mock.is_required.return_value = True
        
        schema_mock = MagicMock()
        schema_mock.model_fields = {"height": field_mock, "name": MagicMock()} # name not required here?
        # make name required too to test logic
        schema_mock.model_fields["name"].is_required.return_value = True
        
        with patch("app.dcim.routers.add_router._get_create_schemas", return_value={ListingType.racks: schema_mock}):
            with pytest.raises(HTTPException) as exc_info:
                add_router.check_required_fields(ListingType.racks, data)
            
            assert exc_info.value.status_code == 400
            assert "Missing required fields" in exc_info.value.detail
            assert "height" in exc_info.value.detail

    def test_check_row_uniqueness_conflict(self):
        """Negative: Raises 409 if row exists."""
        data = {"name": "Wing1", "location_name": "L1", "building_name": "B1"}
        db = MagicMock()
        
        with patch("app.helpers.add_entity_helper.get_location_by_name"), \
             patch("app.helpers.add_entity_helper.get_building_by_name"):
            
            # Mock query to return existing object
            db.query.return_value.filter.return_value.filter.return_value.filter.return_value.first.return_value = MagicMock()
            
            with pytest.raises(HTTPException) as exc_info:
                add_router.check_row_uniqueness(ListingType.wings, data, db)
            
            assert exc_info.value.status_code == 409
            assert "already exists" in exc_info.value.detail
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from fastapi import HTTPException
from app.dcim.routers import add_router
from app.helpers.listing_types import ListingType

# ============================================================
# Extended Tests for check_row_uniqueness
# ============================================================

class TestCheckRowUniquenessExtended:
    
    @pytest.fixture
    def mock_db_exist(self):
        """Returns a DB mock that finds an existing record."""
        db = MagicMock()
        # Mock finding an existing record
        db.query.return_value.filter.return_value.filter.return_value.filter.return_value.filter.return_value.filter.return_value.first.return_value = MagicMock()
        # Also need to make sure chained filters don't crash before .first()
        db.query.return_value.filter.return_value.filter.return_value.filter.return_value.first.return_value = MagicMock()
        return db

    def test_uniqueness_floor(self):
        data = {"name": "F1", "location_name": "L1", "building_name": "B1", "wing_name": "W1"}
        db = MagicMock()
        # Mock existence
        db.query.return_value.filter.return_value.filter.return_value.filter.return_value.filter.return_value.first.return_value = MagicMock()
        
        with patch("app.helpers.add_entity_helper.get_location_by_name"), \
             patch("app.helpers.add_entity_helper.get_building_by_name"), \
             patch("app.helpers.add_entity_helper.get_wing_by_name"):
             
            with pytest.raises(HTTPException) as exc:
                add_router.check_row_uniqueness(ListingType.floors, data, db)
            assert exc.value.status_code == 409
            assert "Floor with name" in exc.value.detail

    def test_uniqueness_datacenter(self):
        data = {"name": "DC1", "location_name": "L1", "building_name": "B1", "wing_name": "W1", "floor_name": "F1"}
        db = MagicMock()
        # Mock existence for long chain
        q = MagicMock()
        q.filter.return_value = q 
        q.first.return_value = MagicMock()
        db.query.return_value = q

        with patch("app.helpers.add_entity_helper.get_location_by_name"), \
             patch("app.helpers.add_entity_helper.get_building_by_name"), \
             patch("app.helpers.add_entity_helper.get_wing_by_name"), \
             patch("app.helpers.add_entity_helper.get_floor_by_name"):
             
            with pytest.raises(HTTPException) as exc:
                add_router.check_row_uniqueness(ListingType.datacenters, data, db)
            assert exc.value.status_code == 409

    def test_uniqueness_rack(self):
        data = {"name": "R1", "location_name": "L1", "building_name": "B1", "wing_name": "W1", "floor_name": "F1", "datacenter_name": "DC1"}
        db = MagicMock()
        q = MagicMock()
        q.filter.return_value = q 
        q.first.return_value = MagicMock()
        db.query.return_value = q
        
        with patch("app.helpers.add_entity_helper.get_location_by_name"), \
             patch("app.helpers.add_entity_helper.get_building_by_name"), \
             patch("app.helpers.add_entity_helper.get_wing_by_name"), \
             patch("app.helpers.add_entity_helper.get_floor_by_name"), \
             patch("app.helpers.add_entity_helper.get_datacenter_by_name"):

            with pytest.raises(HTTPException) as exc:
                add_router.check_row_uniqueness(ListingType.racks, data, db)
            assert exc.value.status_code == 409

    def test_uniqueness_application(self):
        data = {"name": "App1", "asset_owner_name": "AO1"}
        db = MagicMock()
        q = MagicMock()
        q.filter.return_value = q 
        q.first.return_value = MagicMock()
        db.query.return_value = q
        
        with patch("app.helpers.add_entity_helper.get_asset_owner_by_name"):
            with pytest.raises(HTTPException) as exc:
                add_router.check_row_uniqueness(ListingType.applications, data, db)
            assert exc.value.status_code == 409

    def test_uniqueness_device_type(self):
        data = {"name": "DT1", "make_name": "M1"}
        db = MagicMock()
        q = MagicMock()
        q.filter.return_value = q 
        q.first.return_value = MagicMock()
        db.query.return_value = q
        
        with patch("app.helpers.add_entity_helper.get_make_by_name"):
            with pytest.raises(HTTPException) as exc:
                add_router.check_row_uniqueness(ListingType.device_types, data, db)
            assert exc.value.status_code == 409

# ============================================================
# Extended Tests for check_required_fields
# ============================================================

def test_check_required_fields_empty_values():
    """Test that empty string or None raises error for required fields."""
    data = {"name": ""} # Empty string
    
    field_mock = MagicMock()
    field_mock.is_required.return_value = True
    schema_mock = MagicMock()
    schema_mock.model_fields = {"name": field_mock}
    
    with patch("app.dcim.routers.add_router._get_create_schemas", return_value={ListingType.locations: schema_mock}):
        with pytest.raises(HTTPException) as exc:
            add_router.check_required_fields(ListingType.locations, data)
        assert exc.value.status_code == 400
        assert "Empty or null values" in exc.value.detail

# ============================================================
# Extended Tests for add_entity Error Handling
# ============================================================

@pytest.mark.asyncio
async def test_add_entity_generic_exception():
    """Test generic exception handling (500)."""
    request = AsyncMock()
    request.json.return_value = {"name": "Foo"}
    
    # Mock schema retrieval to raise Exception
    with patch("app.dcim.routers.add_router._get_create_schemas", side_effect=Exception("Unexpected Error")):
        with pytest.raises(Exception) as exc:
            await add_router.add_entity(
                request=request, 
                entity=ListingType.racks, 
                access_level=MagicMock(), 
                current_user=MagicMock(), 
                db=MagicMock()
            )
        assert "Unexpected Error" in str(exc.value)
