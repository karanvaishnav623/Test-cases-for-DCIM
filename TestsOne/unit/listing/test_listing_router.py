"""Unit tests for listing_router.py

These tests focus on the small, pure helper functions used by the
`/api/dcim/list` endpoint so they can be validated without HTTP or DB.

Covered:
- _normalize_empty_to_none
- _parse_optional_int
- _parse_optional_date
- _get_listing_handler (with patched ENTITY_LIST_HANDLERS)

Each behaviour has at least one positive and one negative/edge scenario.
"""

from datetime import date
from unittest.mock import patch, MagicMock

import pytest

from fastapi import HTTPException

from app.dcim.routers.listing_router import (
    _normalize_empty_to_none,
    _parse_optional_int,
    _parse_optional_date,
    _get_listing_handler,
    list_dcim_entities,
)
from app.helpers.listing_types import ListingType


# ============================================================
# Tests for _normalize_empty_to_none
# ============================================================


class TestNormalizeEmptyToNone:
    """Unit tests for _normalize_empty_to_none."""

    def test_keeps_non_empty_string(self):
        """Positive: non-empty string is returned unchanged."""
        assert _normalize_empty_to_none("abc") == "abc"

    def test_keeps_non_string_values(self):
        """Positive: non-string values are returned unchanged."""
        assert _normalize_empty_to_none(0) == 0
        d = date(2025, 1, 1)
        assert _normalize_empty_to_none(d) == d

    def test_converts_empty_string_to_none(self):
        """Negative: empty string becomes None."""
        assert _normalize_empty_to_none("") is None

    def test_converts_whitespace_string_to_none(self):
        """Negative: whitespace-only string becomes None."""
        assert _normalize_empty_to_none("   ") is None
        assert _normalize_empty_to_none("\t\n ") is None


# ============================================================
# Tests for _parse_optional_int
# ============================================================


class TestParseOptionalInt:
    """Unit tests for _parse_optional_int."""

    def test_returns_none_for_none(self):
        """Negative: None input stays None."""
        assert _parse_optional_int(None) is None

    def test_parses_valid_int_value(self):
        """Positive: integer input is returned as int."""
        assert _parse_optional_int(5) == 5

    def test_parses_valid_int_string(self):
        """Positive: numeric string is parsed to int."""
        assert _parse_optional_int("10") == 10
        assert _parse_optional_int("  7  ") == 7

    def test_returns_none_for_empty_string(self):
        """Negative: empty string becomes None."""
        assert _parse_optional_int("") is None

    def test_returns_none_for_whitespace_string(self):
        """Negative: whitespace-only string becomes None."""
        assert _parse_optional_int("   ") is None
        assert _parse_optional_int("\n\t ") is None

    def test_returns_none_for_non_numeric_string(self):
        """Negative: non-numeric string becomes None (invalid int)."""
        assert _parse_optional_int("abc") is None
        assert _parse_optional_int("123abc") is None


# ============================================================
# Tests for _parse_optional_date
# ============================================================


class TestParseOptionalDate:
    """Unit tests for _parse_optional_date."""

    def test_returns_none_for_none(self):
        """Negative: None input stays None."""
        assert _parse_optional_date(None) is None

    def test_keeps_date_instance(self):
        """Positive: date instance is returned unchanged."""
        d = date(2025, 1, 15)
        assert _parse_optional_date(d) is d

    def test_parses_valid_iso_date_string(self):
        """Positive: valid ISO date string is parsed to date."""
        result = _parse_optional_date("2025-01-15")
        assert isinstance(result, date)
        assert result == date(2025, 1, 15)

    def test_returns_none_for_empty_string(self):
        """Negative: empty string becomes None."""
        assert _parse_optional_date("") is None

    def test_returns_none_for_whitespace_string(self):
        """Negative: whitespace-only string becomes None."""
        assert _parse_optional_date("   ") is None

    def test_returns_none_for_invalid_date_string(self):
        """Negative: invalid date string becomes None."""
        assert _parse_optional_date("not-a-date") is None
        assert _parse_optional_date("2025-13-01") is None  # invalid month
        assert _parse_optional_date("2025-02-30") is None  # invalid day


# ============================================================
# Tests for _get_listing_handler
# ============================================================


class TestGetListingHandler:
    """Unit tests for _get_listing_handler."""

    def test_returns_handler_when_present(self):
        """Positive: returns the correct handler from ENTITY_LIST_HANDLERS."""
        fake_handler = MagicMock()

        # Patch the source mapping used by _get_listing_handler's lazy import
        with patch("app.helpers.listing_helper.ENTITY_LIST_HANDLERS", {ListingType.devices: fake_handler}):
            handler = _get_listing_handler(ListingType.devices)
            assert handler is fake_handler

    def test_returns_none_when_handler_missing(self):
        """Negative: returns None when no handler exists for entity."""
        # Empty mapping means no handler should be found
        with patch("app.helpers.listing_helper.ENTITY_LIST_HANDLERS", {}):
            handler = _get_listing_handler(ListingType.locations)
            assert handler is None



# ============================================================
# Tests for list_dcim_entities (Main Endpoint)
# ============================================================


class TestListDCIMEntities:
    """Unit tests for the list_dcim_entities endpoint."""
    
    # Helper to clean up test calls - these match the optional args in the router
    # preventing them from defaulting to FastAPI Param objects (Query/Depends)
    SAFE_DEFAULTS = {
        "location_name": None, "location_description": None,
        "building_name": None, "building_status": None, "building_description": None,
        "wing_name": None, "wing_description": None,
        "floor_name": None, "floor_description": None,
        "rack_name": None, "rack_status": None, "rack_height": None, "rack_description": None,
        "device_name": None, "device_status": None, "device_position": None, "device_face": None,
        "device_description": None, "serial_number": None, "ip_address": None, "po_number": None,
        "asset_user": None, "asset_owner": None, "applications_mapped_name": None,
        "warranty_start_date": None, "warranty_end_date": None,
        "amc_start_date": None, "amc_end_date": None,
        "device_type": None, "device_type_description": None,
        "make_name": None, "make_description": None,
        "model_name": None, "model_description": None, "model_height": None,
        "datacenter_name": None, "datacenter_description": None,
        "asset_owner_name": None, "asset_owner_description": None,
        "application_name": None, "application_description": None,
    }

    def test_success_calls_handler_and_caches(self):
        """Positive: verification of handler call and cache setting."""
        mock_db = MagicMock()
        mock_user = MagicMock(id=1)
        mock_access = MagicMock(value="admin")
        
        mock_handler = MagicMock(return_value=(100, [{"id": 1}]))
        
        with patch("app.dcim.routers.listing_router._get_listing_handler", return_value=mock_handler), \
             patch("app.dcim.routers.listing_router.listing_cache") as mock_cache, \
             patch("app.dcim.routers.listing_router.build_listing_cache_key", return_value="cache_key"), \
             patch("app.dcim.routers.listing_router.get_allowed_location_ids", return_value={10, 20}):
            
            mock_cache.get.return_value = None
            
            # Create args with defaults, then override device_name
            call_args = self.SAFE_DEFAULTS.copy()
            call_args["device_name"] = "test_device"
            
            result = list_dcim_entities(
                entity=ListingType.devices,
                offset=0,
                page_size=10,
                access_level=mock_access,
                db=mock_db,
                current_user=mock_user,
                **call_args
            )
            
            mock_handler.assert_called_once()
            call_kwargs = mock_handler.call_args[1]
            assert call_kwargs["db"] == mock_db
            assert call_kwargs["device_name"] == "test_device"
            assert call_kwargs["allowed_location_ids"] == {10, 20}
            
            assert result["total"] == 100
            assert result["results"] == [{"id": 1}]
            
            mock_cache.set.assert_called_once()

    def test_returns_cached_response(self):
        """Positive: returns cached payload immediately if found."""
        mock_db = MagicMock()
        cached_payload = {"total": 50, "results": [], "cached": True}
        
        with patch("app.dcim.routers.listing_router.listing_cache") as mock_cache, \
             patch("app.dcim.routers.listing_router.build_listing_cache_key"), \
             patch("app.dcim.routers.listing_router._get_listing_handler") as mock_get_handler, \
             patch("app.dcim.routers.listing_router.get_allowed_location_ids"):
            
            mock_cache.get.return_value = cached_payload
            
            result = list_dcim_entities(
                entity=ListingType.locations,
                db=mock_db,
                current_user=MagicMock(),
                access_level=MagicMock(),
                **self.SAFE_DEFAULTS
            )
            
            assert result == cached_payload
            mock_get_handler.assert_not_called()

    def test_unsupported_entity_raises_400(self):
        """Negative: raises 400 if no handler found."""
        with patch("app.dcim.routers.listing_router.listing_cache") as mock_cache, \
             patch("app.dcim.routers.listing_router.build_listing_cache_key"), \
             patch("app.dcim.routers.listing_router._get_listing_handler", return_value=None), \
             patch("app.dcim.routers.listing_router.get_allowed_location_ids"):
            
            mock_cache.get.return_value = None
            
            with pytest.raises(HTTPException) as exc:
                list_dcim_entities(
                    entity=ListingType.locations,
                    db=MagicMock(),
                    current_user=MagicMock(),
                    access_level=MagicMock(),
                    **self.SAFE_DEFAULTS
                )
            
            assert exc.value.status_code == 400
            assert "Unsupported entity type" in exc.value.detail


