"""Unit tests for details_router.py

Covers the small helper functions used by `/api/dcim/details`:
- _get_detail_handlers (lazy import of ENTITY_DETAIL_HANDLERS)
- _ensure_entity_in_location_scope (location-based RBAC check)

Each behavior has at least one positive and one negative/edge scenario.
"""

from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from app.dcim.routers.details_router import (
    _get_detail_handlers,
    _get_detail_handlers,
    _ensure_entity_in_location_scope,
    get_entity_details,
)
from app.helpers.listing_types import ListingType


# ============================================================
# Tests for _get_detail_handlers
# ============================================================


class TestGetDetailHandlers:
    """Unit tests for _get_detail_handlers helper."""

    def test_returns_handlers_mapping(self):
        """Positive: returns the mapping imported from details_helper."""
        fake_mapping = {"key": "value"}

        # Patch the source mapping in details_helper, which _get_detail_handlers imports lazily
        with patch("app.helpers.details_helper.ENTITY_DETAIL_HANDLERS", fake_mapping):
            handlers = _get_detail_handlers()
            assert handlers is fake_mapping


# ============================================================
# Tests for _ensure_entity_in_location_scope
# ============================================================


class TestEnsureEntityInLocationScope:
    """Unit tests for _ensure_entity_in_location_scope."""

    def test_no_allowed_location_ids_skips_check(self):
        """Edge: when allowed_location_ids is None, no query should be executed."""
        db = MagicMock()

        _ensure_entity_in_location_scope(
            db=db,
            entity=ListingType.locations,
            entity_id=1,
            allowed_location_ids=None,
        )

        db.query.assert_not_called()

    def test_entity_not_in_scope_map_skips_check(self):
        """Edge: entities not in scope map should bypass location filter."""
        db = MagicMock()

        _ensure_entity_in_location_scope(
            db=db,
            entity=ListingType.device_types,  # not in scope_map
            entity_id=1,
            allowed_location_ids={1, 2},
        )

        db.query.assert_not_called()

    def test_entity_in_scope_and_found_does_not_raise(self):
        """Positive: when entity is in allowed locations, no exception is raised."""
        db = MagicMock()
        mock_query = MagicMock()
        db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = object()  # Something truthy

        _ensure_entity_in_location_scope(
            db=db,
            entity=ListingType.locations,
            entity_id=1,
            allowed_location_ids={1, 2},
        )

        db.query.assert_called_once()
        mock_query.filter.assert_called()

    def test_entity_in_scope_and_not_found_raises_404(self):
        """Negative: when entity is outside allowed locations, 404 is raised."""
        db = MagicMock()
        mock_query = MagicMock()
        db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = None  # Not found in allowed scope

        with pytest.raises(HTTPException) as exc_info:
            _ensure_entity_in_location_scope(
                db=db,
                entity=ListingType.locations,
                entity_id=1,
                allowed_location_ids={1, 2},
            )

        assert exc_info.value.status_code == 404
        assert "not found or access denied" in exc_info.value.detail

# ============================================================
# Tests for get_entity_details (Main Endpoint)
# ============================================================


class TestGetEntityDetails:
    """Unit tests for the get_entity_details endpoint function."""

    def test_success_calls_correct_handler(self):
        """Positive: invokes specific handler and returns wrapped data."""
        # 1. Setup Dependencies
        mock_db = MagicMock()
        mock_user = MagicMock()
        mock_access = MagicMock()
        
        # 2. Setup Mocks for internal calls
        mock_handler_func = MagicMock(return_value={"some": "details"})
        mock_handlers_map = {ListingType.locations: mock_handler_func}
        
        # We need to patch the internal functions used by get_entity_details:
        # - _get_detail_handlers (to return our mock map)
        # - get_allowed_location_ids (to return some IDs)
        # - _ensure_entity_in_location_scope (to pass silently)
        
        with patch("app.dcim.routers.details_router._get_detail_handlers", return_value=mock_handlers_map), \
             patch("app.dcim.routers.details_router.get_allowed_location_ids", return_value={1, 2}) as mock_get_allowed, \
             patch("app.dcim.routers.details_router._ensure_entity_in_location_scope") as mock_ensure:
            
            # 3. Call execution
            result = get_entity_details(
                entity=ListingType.locations,
                id=10,
                access_level=mock_access,
                db=mock_db,
                current_user=mock_user,
            )
            
            # 4. Assertions
            mock_Get_allowed = mock_get_allowed # variable name aliasing fix if needed
            mock_get_allowed.assert_called_once_with(mock_user, mock_access)
            
            mock_ensure.assert_called_once_with(mock_db, ListingType.locations, 10, {1, 2})
            
            mock_handler_func.assert_called_once_with(mock_db, 10)
            
            assert result == {
                "entity": ListingType.locations,
                "data": {"some": "details"},
            }

    def test_unsupported_entity_raises_400(self):
        """Negative: raises 400 if entity type is not in handlers map."""
        mock_db = MagicMock()
        
        # Empty handlers map
        with patch("app.dcim.routers.details_router._get_detail_handlers", return_value={}):
            with pytest.raises(HTTPException) as exc:
                get_entity_details(
                    entity=ListingType.locations, # Even if valid enum, if handler missing -> 400
                    id=1,
                    access_level=MagicMock(),
                    db=mock_db,
                    current_user=MagicMock(),
                )
            
            assert exc.value.status_code == 400
            assert "Unsupported entity type" in exc.value.detail

    def test_access_denied_propagates_exception(self):
        """Negative: if _ensure_entity_in_location_scope raises 404, it propagates."""
        mock_db = MagicMock()
        
        # Handler exists
        mock_handlers_map = {ListingType.locations: MagicMock()}
        
        with patch("app.dcim.routers.details_router._get_detail_handlers", return_value=mock_handlers_map), \
             patch("app.dcim.routers.details_router.get_allowed_location_ids", return_value=None), \
             patch("app.dcim.routers.details_router._ensure_entity_in_location_scope", side_effect=HTTPException(status_code=404, detail="Not found")):
            
            with pytest.raises(HTTPException) as exc:
                get_entity_details(
                    entity=ListingType.locations,
                    id=1,
                    access_level=MagicMock(),
                    db=mock_db,
                    current_user=MagicMock(),
                )
            
            assert exc.value.status_code == 404
            assert "Not found" in exc.value.detail

