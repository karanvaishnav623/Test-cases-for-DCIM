import pytest
from unittest.mock import MagicMock, patch
from fastapi import HTTPException, status, Request
from sqlalchemy.exc import IntegrityError
from app.dcim.routers.delete_router import delete_entity
from app.helpers.listing_types import ListingType

class TestDeleteRouter:
    
    # ENTITY_DELETE_HANDLERS is local import, so we patch _get_delete_handlers directly
    @patch("app.dcim.routers.delete_router._get_delete_handlers")
    @patch("app.dcim.routers.delete_router.log_delete")
    @patch("app.dcim.routers.delete_router.invalidate_listing_cache_for_entity")
    @patch("app.dcim.routers.delete_router.invalidate_location_summary_cache")
    def test_delete_entity_success(self, mock_inv_summ, mock_inv_list, mock_log, mock_get_handlers):
        """Positive: Successful delete dispatch and logging."""
        mock_handler = MagicMock(return_value={"id": 1, "name": "test-device"})
        mock_get_handlers.return_value = {ListingType.devices: mock_handler}
        
        db = MagicMock()
        request = MagicMock(spec=Request)
        current_user = MagicMock()
        
        response = delete_entity(
            request=request,
            entity_id=1,
            entity=ListingType.devices,
            access_level="admin",
            current_user=current_user,
            db=db
        )
        
        mock_handler.assert_called_once_with(db, 1)
        mock_log.assert_called_once()
        mock_inv_list.assert_called_once_with(ListingType.devices)
        mock_inv_summ.assert_called_once()
        db.commit.assert_called_once()
        assert response["message"] == "devices deleted successfully"

    @patch("app.dcim.routers.delete_router._get_delete_handlers")
    def test_delete_entity_unsupported(self, mock_get_handlers):
        """Negative: Unsupported entity type."""
        mock_get_handlers.return_value = {} # Empty handlers
        
        with pytest.raises(HTTPException) as exc:
            delete_entity(
                request=MagicMock(),
                entity_id=1,
                entity=ListingType.devices,
                access_level="admin",
                current_user=MagicMock(),
                db=MagicMock()
            )
        assert exc.value.status_code == 400
        assert "Unsupported entity type" in exc.value.detail

    @patch("app.dcim.routers.delete_router._get_delete_handlers")
    def test_delete_entity_integrity_error(self, mock_get_handlers):
        """Negative: Database integrity error (Conflict)."""
        mock_handler = MagicMock(side_effect=IntegrityError("orig", "params", "orig"))
        mock_get_handlers.return_value = {ListingType.devices: mock_handler}
        
        db = MagicMock()
        
        with pytest.raises(HTTPException) as exc:
            delete_entity(
                request=MagicMock(),
                entity_id=1,
                entity=ListingType.devices,
                access_level="admin",
                current_user=MagicMock(),
                db=db
            )
        assert exc.value.status_code == 409
        assert "Database integrity error" in exc.value.detail
        db.rollback.assert_called_once()

    @patch("app.dcim.routers.delete_router._get_delete_handlers")
    def test_delete_entity_generic_error(self, mock_get_handlers):
        """Negative: Generic internal error."""
        mock_handler = MagicMock(side_effect=Exception("Boom"))
        mock_get_handlers.return_value = {ListingType.devices: mock_handler}
        
        db = MagicMock()
        
        with pytest.raises(HTTPException) as exc:
            delete_entity(
                request=MagicMock(),
                entity_id=1,
                entity=ListingType.devices,
                access_level="admin",
                current_user=MagicMock(),
                db=db
            )
        assert exc.value.status_code == 500
        assert "Failed to delete entity" in exc.value.detail
        db.rollback.assert_called_once()

    @patch("app.dcim.routers.delete_router._get_delete_handlers")
    def test_delete_entity_http_exception_propagation(self, mock_get_handlers):
        """Negative: Propagates HTTP exceptions from handler (e.g. 404)."""
        mock_handler = MagicMock(side_effect=HTTPException(status_code=404, detail="Not Found"))
        mock_get_handlers.return_value = {ListingType.devices: mock_handler}
        
        db = MagicMock()
        
        with pytest.raises(HTTPException) as exc:
            delete_entity(
                request=MagicMock(),
                entity_id=99,
                entity=ListingType.devices,
                access_level="admin",
                current_user=MagicMock(),
                db=db
            )
        assert exc.value.status_code == 404
        db.rollback.assert_called_once()
