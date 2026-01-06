import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from fastapi import HTTPException
from app.dcim.routers import update_router, delete_router
from app.helpers.listing_types import ListingType

@pytest.mark.asyncio
class TestUpdateRouter:
    """Unit tests for update_router module."""

    async def test_update_entity_success(self):
        """Positive: Successfully updates entity."""
        request = AsyncMock()
        request.json.return_value = {"name": "UpdatedName"}
        
        handler_mock = MagicMock(return_value={"id": 1, "name": "UpdatedName"})
        db = MagicMock()
        
        schema_mock = MagicMock()
        schema_instance = MagicMock()
        schema_instance.model_dump.return_value = {"name": "UpdatedName"}
        schema_mock.return_value = schema_instance
        
        with patch("app.dcim.routers.update_router._get_update_handlers", return_value={ListingType.racks: handler_mock}), \
             patch("app.dcim.routers.update_router._get_update_schemas", return_value={ListingType.racks: schema_mock}), \
             patch("app.dcim.routers.update_router.log_update"), \
             patch("app.dcim.routers.update_router.invalidate_listing_cache_for_entity"), \
             patch("app.dcim.routers.update_router.invalidate_location_summary_cache"):

            result = await update_router.update_entity(
                request=request,
                entity_id=1,
                entity=ListingType.racks,
                access_level=MagicMock(),
                current_user=MagicMock(),
                db=db
            )
            
            assert result["message"] == "racks updated successfully"
            handler_mock.assert_called_once()
            db.commit.assert_called_once()

    async def test_update_entity_validation_error(self):
        """Negative: Raises 422 if schema validation fails."""
        request = AsyncMock()
        request.json.return_value = {"name": "X"}
        
        schema_mock = MagicMock()
        schema_mock.side_effect = Exception("Validation Failed")
        
        with patch("app.dcim.routers.update_router._get_update_handlers", return_value={ListingType.racks: MagicMock()}), \
             patch("app.dcim.routers.update_router._get_update_schemas", return_value={ListingType.racks: schema_mock}):

            with pytest.raises(HTTPException) as exc_info:
                await update_router.update_entity(
                    request=request,
                    entity_id=1,
                    entity=ListingType.racks,
                    access_level=MagicMock(),
                    current_user=MagicMock(),
                    db=MagicMock()
                )
            
            assert exc_info.value.status_code == 422
            assert "Validation error" in exc_info.value.detail

class TestDeleteRouter:
    """Unit tests for delete_router module."""

    def test_delete_entity_success(self):
        """Positive: Successfully deletes entity."""
        request = MagicMock()
        db = MagicMock()
        handler_mock = MagicMock(return_value={"id": 1})
        
        with patch("app.dcim.routers.delete_router._get_delete_handlers", return_value={ListingType.racks: handler_mock}), \
             patch("app.dcim.routers.delete_router.log_delete"), \
             patch("app.dcim.routers.delete_router.invalidate_listing_cache_for_entity"), \
             patch("app.dcim.routers.delete_router.invalidate_location_summary_cache"):

            result = delete_router.delete_entity(
                request=request,
                entity_id=1,
                entity=ListingType.racks,
                access_level=MagicMock(),
                current_user=MagicMock(),
                db=db
            )
            
            assert result["message"] == "racks deleted successfully"
            handler_mock.assert_called_once_with(db, 1)
            db.commit.assert_called_once()

    def test_delete_entity_unsupported(self):
        """Negative: Raises 400 if handler not found."""
        with patch("app.dcim.routers.delete_router._get_delete_handlers", return_value={}):
            with pytest.raises(HTTPException) as exc_info:
                delete_router.delete_entity(
                    request=MagicMock(),
                    entity_id=1,
                    entity=ListingType.racks,
                    access_level=MagicMock(),
                    current_user=MagicMock(),
                    db=MagicMock()
                )
            
            assert exc_info.value.status_code == 400
            assert "Unsupported entity type" in exc_info.value.detail
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from app.dcim.routers import update_router
from app.helpers.listing_types import ListingType

@pytest.mark.asyncio
class TestUpdateRouterExtended:

    async def test_update_entity_invalid_json(self):
        """Negative: Raises 400 on invalid JSON."""
        request = AsyncMock()
        request.json.side_effect = Exception("JSON Error")
        
        with pytest.raises(HTTPException) as exc:
            await update_router.update_entity(
                request=request, 
                entity_id=1, 
                entity=ListingType.racks, 
                access_level=MagicMock(), 
                current_user=MagicMock(), 
                db=MagicMock()
            )
        assert exc.value.status_code == 400
        assert "Invalid JSON" in exc.value.detail

    async def test_update_entity_unsupported_type(self):
        """Negative: Raises 400 if entity unsupported."""
        request = AsyncMock()
        request.json.return_value = {}
        
        with patch("app.dcim.routers.update_router._get_update_handlers", return_value={}):
            with pytest.raises(HTTPException) as exc:
                await update_router.update_entity(
                    request=request, 
                    entity_id=1, 
                    entity=ListingType.racks, # Not in empty dict
                    access_level=MagicMock(),
                    current_user=MagicMock(),
                    db=MagicMock()
                )
        assert exc.value.status_code == 400
        assert "Unsupported entity type" in exc.value.detail

    async def test_update_entity_integrity_error(self):
        """Negative: Raises 409 on DB integrity error."""
        request = AsyncMock()
        request.json.return_value = {"name": "Dup"}
        
        # Mock handler to raise IntegrityError
        handler = MagicMock(side_effect=IntegrityError("stmt", "params", "orig"))
        
        with patch("app.dcim.routers.update_router._get_update_handlers", return_value={ListingType.racks: handler}), \
             patch("app.dcim.routers.update_router._get_update_schemas", return_value={}), \
             patch("app.dcim.routers.update_router.log_update"): # Should not reach log update if handler fails?
             # Check code: result = updater(db, ...) happens before log_update
             
             with pytest.raises(HTTPException) as exc:
                 await update_router.update_entity(
                     request=request, 
                     entity_id=1, 
                     entity=ListingType.racks, 
                     access_level=MagicMock(), 
                     current_user=MagicMock(), 
                     db=MagicMock()
                 )
        assert exc.value.status_code == 409
        assert "Database integrity error" in exc.value.detail

    async def test_update_entity_generic_exception_caught(self):
        """Negative: Raises 500 on unexpected error (caught by router)."""
        request = AsyncMock()
        request.json.return_value = {"name": "Kermit"}
        
        # Mock handler to raise Generic Exception
        handler = MagicMock(side_effect=Exception("Boom"))
        
        with patch("app.dcim.routers.update_router._get_update_handlers", return_value={ListingType.racks: handler}), \
             patch("app.dcim.routers.update_router._get_update_schemas", return_value={}):

             with pytest.raises(HTTPException) as exc:
                 await update_router.update_entity(
                     request=request, 
                     entity_id=1, 
                     entity=ListingType.racks, 
                     access_level=MagicMock(), 
                     current_user=MagicMock(), 
                     db=MagicMock()
                 )
        assert exc.value.status_code == 500
        assert "Failed to update entity" in exc.value.detail

    async def test_update_entity_http_exception_propagates(self):
        """Negative: Propagates internal HTTPException (e.g. 404 from helper)."""
        request = AsyncMock()
        request.json.return_value = {}
        
        # Mock handler to raise 404
        handler = MagicMock(side_effect=HTTPException(404, "Not Found"))
        
        with patch("app.dcim.routers.update_router._get_update_handlers", return_value={ListingType.racks: handler}), \
             patch("app.dcim.routers.update_router._get_update_schemas", return_value={}):

             with pytest.raises(HTTPException) as exc:
                 await update_router.update_entity(
                     request=request, 
                     entity_id=1, 
                     entity=ListingType.racks, 
                     access_level=MagicMock(), 
                     current_user=MagicMock(), 
                     db=MagicMock()
                 )
        assert exc.value.status_code == 404
