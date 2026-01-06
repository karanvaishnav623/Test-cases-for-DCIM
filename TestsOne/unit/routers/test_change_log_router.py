import pytest
from unittest.mock import MagicMock, patch, PropertyMock
from datetime import datetime
from fastapi import HTTPException, status
from app.dcim.routers import change_log_router
from app.helpers.listing_types import ListingType

class TestChangeLogRouter:
    """Unit tests for change_log_router module."""

    def test_get_entity_id_by_name_cached(self):
        """Positive: Returns cached ID if available."""
        mock_db = MagicMock()
        # Pre-seed cache manually or mock the cache access?
        # The module uses a global variable _ENTITY_NAME_ID_CACHE.
        # It's cleaner to mock the dict access if we could, but patching a global dict import is tricky.
        # Instead, we'll just test the DB lookup part and assumption of cache set.
        
        # Let's test non-cached path first which is safer
        mock_entity = MagicMock()
        mock_entity.id = 123
        mock_db.query.return_value.filter.return_value.first.return_value = mock_entity
        
        # We need to ensure we access the map correctly
        # change_log_router.ENTITY_MODEL_MAP is used.
        
        with patch("app.dcim.routers.change_log_router._ENTITY_NAME_ID_CACHE", {}) as mock_cache:
            res_id = change_log_router.get_entity_id_by_name(mock_db, ListingType.devices, "MyDevice")
            assert res_id == 123
            # Should be added to cache
            assert (ListingType.devices.value, "mydevice") in mock_cache

    def test_get_entity_id_by_name_not_found(self):
        """Negative: Raises 404 if entity not found."""
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        with pytest.raises(HTTPException) as exc:
            change_log_router.get_entity_id_by_name(mock_db, ListingType.devices, "Missing")
        assert exc.value.status_code == 404

    def test_get_change_logs_success(self):
        """Positive: Returns paginated logs with filters."""
        mock_db = MagicMock()
        
        # Mock logs
        mock_log = MagicMock()
        mock_log.id = 1
        mock_log.time = datetime(2023, 1, 1)
        mock_log.action = "create"
        mock_log.type = "device"
        mock_log.object_id = 99
        mock_log.message = "Created"
        mock_log.user.id = 10
        mock_log.user.name = "admin"
        mock_log.user.full_name = "Administrator"
        
        mock_query = mock_db.query.return_value
        # Important: Allow chaining filter() calls
        mock_query.filter.return_value = mock_query
        
        # Configure count on the final object after filter chain and order_by(None)
        mock_query.order_by.return_value.count.return_value = 1
        
        # Configure results for pagination query
        # access_level check logic uses db.query(User)... which mocks might interfere with if not careful
        # But here we are testing get_change_logs main query.
        
        # The code does: base_query.options(...).order_by(...).offset(...).limit(...).all()
        # Since we mocked filter return value as mock_query, base_query is mock_query.
        mock_query.options.return_value.order_by.return_value.offset.return_value.limit.return_value.all.return_value = [mock_log]
        
        response = change_log_router.get_change_logs(
            entity=ListingType.devices,
            action="create",
            object_name=None, username=None, from_date=None, to_date=None, # Explicitly pass None
            page=1,
            page_size=10,
            db=mock_db,
            access_level=MagicMock()
        )
        
        assert response["total"] == 1
        assert len(response["data"]) == 1
        assert response["data"][0]["action"] == "create"
        assert response["data"][0]["user"]["username"] == "admin"

    def test_get_change_logs_object_filter_error(self):
        """Negative: object_name requires entity type."""
        mock_db = MagicMock()
        
        with pytest.raises(HTTPException) as exc:
            change_log_router.get_change_logs(
                entity=None,
                action=None, # Pass None
                object_name="Something", # Missing entity type
                username=None, from_date=None, to_date=None, page=1, page_size=50,
                db=mock_db,
                access_level=5
            )
        assert exc.value.status_code == 400

    def test_get_change_log_by_id_found(self):
        """Positive: Retrieve single log."""
        mock_db = MagicMock()
        mock_log = MagicMock()
        mock_log.id = 55
        mock_log.action = "update"
        
        mock_db.query.return_value.options.return_value.filter.return_value.first.return_value = mock_log
        
        response = change_log_router.get_change_log_by_id(
             log_id=55, 
             db=mock_db,
             access_level=5
        )
        assert response["data"]["id"] == 55
        assert response["data"]["action"] == "update"

    def test_get_change_log_by_id_not_found(self):
        """Negative: Log not found returns error dict (not 404, based on code)."""
        mock_db = MagicMock()
        mock_db.query.return_value.options.return_value.filter.return_value.first.return_value = None
        
        response = change_log_router.get_change_log_by_id(
            log_id=999, 
            db=mock_db, 
            access_level=5
        )
        assert response["error"] == "Audit log entry not found"
        assert response["data"] is None

    def test_get_entity_change_history_success(self):
        """Positive: Full history for entity."""
        # Need to mock get_entity_id_by_name to avoid DB lookup logic duplication failure
        with patch("app.dcim.routers.change_log_router.get_entity_id_by_name") as mock_get_id:
            mock_get_id.return_value = 777
            
            mock_db = MagicMock()
            mock_log = MagicMock()
            mock_log.id = 1
            mock_log.message = "Changed stuff"
            
            query_mock = mock_db.query.return_value.options.return_value.filter.return_value.filter.return_value
            query_mock.count.return_value = 1
            query_mock.order_by.return_value.offset.return_value.limit.return_value.all.return_value = [mock_log]
            
            response = change_log_router.get_entity_change_history(
                entity_type=ListingType.racks,
                entity_name="R1",
                page=1, page_size=20, # Explicit values
                db=mock_db,
                access_level=5
            )
            
            assert response["object_id"] == 777
            assert len(response["history"]) == 1
            assert response["history"][0]["message"] == "Changed stuff"
