# tests/integration/test_listing_helper.py
"""
Integration tests for listing_helper.py

Tests the entity listing functions with mocked database sessions.
These tests verify:
- Filter application logic
- Pagination behavior
- Data transformation/mapping
- Error handling
"""

import pytest
from unittest.mock import MagicMock, patch, PropertyMock
from datetime import date

from app.helpers.listing_helper import (
    apply_filters,
    _restrict_to_locations,
    ENTITY_LIST_HANDLERS,
)
from app.helpers.listing_types import ListingType


# ============================================================
# Tests for apply_filters function
# ============================================================

class TestApplyFilters:
    """Tests for the apply_filters helper function."""

    def test_apply_filters_skips_none_values(self):
        """Test that None filter values are skipped."""
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        
        # Create a mock column
        mock_column = MagicMock()
        
        filter_config = {
            'name': (mock_column, 'exact'),
        }
        filters = {
            'name': None,  # Should be skipped
        }
        
        result = apply_filters(mock_query, filters, filter_config)
        
        # filter() should NOT be called since value is None
        mock_query.filter.assert_not_called()
        assert result == mock_query

    def test_apply_filters_skips_empty_strings(self):
        """Test that empty string filter values are skipped."""
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        
        mock_column = MagicMock()
        
        filter_config = {
            'name': (mock_column, 'exact'),
        }
        filters = {
            'name': "",  # Should be skipped
        }
        
        result = apply_filters(mock_query, filters, filter_config)
        
        mock_query.filter.assert_not_called()
        assert result == mock_query

    def test_apply_filters_skips_whitespace_only_strings(self):
        """Test that whitespace-only filter values are skipped."""
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        
        mock_column = MagicMock()
        
        filter_config = {
            'name': (mock_column, 'exact'),
        }
        filters = {
            'name': "   ",  # Should be skipped
        }
        
        result = apply_filters(mock_query, filters, filter_config)
        
        mock_query.filter.assert_not_called()
        assert result == mock_query

    def test_apply_filters_skips_unknown_filter_names(self):
        """Test that filters not in config are skipped."""
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        
        filter_config = {}  # Empty config
        filters = {
            'unknown_filter': "value",  # Not in config
        }
        
        result = apply_filters(mock_query, filters, filter_config)
        
        mock_query.filter.assert_not_called()
        assert result == mock_query

    def test_apply_filters_exact_match(self):
        """Test exact match filter type."""
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        
        mock_column = MagicMock()
        
        filter_config = {
            'name': (mock_column, 'exact'),
        }
        filters = {
            'name': "TestValue",
        }
        
        result = apply_filters(mock_query, filters, filter_config)
        
        # filter() should be called once
        assert mock_query.filter.called
        assert result == mock_query

    def test_apply_filters_contains_match(self):
        """Test contains match filter type."""
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        
        mock_column = MagicMock()
        
        filter_config = {
            'description': (mock_column, 'contains'),
        }
        filters = {
            'description': "partial",
        }
        
        result = apply_filters(mock_query, filters, filter_config)
        
        assert mock_query.filter.called
        assert result == mock_query

    def test_apply_filters_exact_int(self):
        """Test exact integer match filter type."""
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        
        mock_column = MagicMock()
        
        filter_config = {
            'height': (mock_column, 'exact_int'),
        }
        filters = {
            'height': 42,
        }
        
        result = apply_filters(mock_query, filters, filter_config)
        
        assert mock_query.filter.called
        assert result == mock_query

    def test_apply_filters_exact_date(self):
        """Test exact date match filter type."""
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        
        mock_column = MagicMock()
        
        filter_config = {
            'start_date': (mock_column, 'exact_date'),
        }
        filters = {
            'start_date': date(2025, 1, 15),
        }
        
        result = apply_filters(mock_query, filters, filter_config)
        
        assert mock_query.filter.called
        assert result == mock_query

    def test_apply_filters_multiple_filters(self):
        """Test applying multiple filters at once."""
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        
        mock_name_col = MagicMock()
        mock_status_col = MagicMock()
        
        filter_config = {
            'name': (mock_name_col, 'exact'),
            'status': (mock_status_col, 'exact'),
        }
        filters = {
            'name': "Device1",
            'status': "active",
        }
        
        result = apply_filters(mock_query, filters, filter_config)
        
        # filter() should be called twice
        assert mock_query.filter.call_count == 2
        assert result == mock_query


# ============================================================
# Tests for _restrict_to_locations function
# ============================================================

class TestRestrictToLocations:
    """Tests for the _restrict_to_locations helper function."""

    def test_returns_query_unchanged_when_allowed_ids_is_none(self):
        """Test that query is unchanged when allowed_location_ids is None."""
        mock_query = MagicMock()
        mock_column = MagicMock()
        
        result = _restrict_to_locations(mock_query, mock_column, None)
        
        # Query should be returned unchanged
        assert result == mock_query
        mock_query.filter.assert_not_called()

    def test_applies_filter_when_allowed_ids_provided(self):
        """Test that IN filter is applied when allowed_location_ids is provided."""
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_column = MagicMock()
        
        allowed_ids = {1, 2, 3}
        
        result = _restrict_to_locations(mock_query, mock_column, allowed_ids)
        
        # filter() should be called
        mock_query.filter.assert_called_once()
        assert result == mock_query

    def test_applies_filter_with_empty_set(self):
        """Test behavior with empty set of allowed IDs."""
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_column = MagicMock()
        
        allowed_ids = set()  # Empty set
        
        result = _restrict_to_locations(mock_query, mock_column, allowed_ids)
        
        # filter() should still be called (will match nothing)
        mock_query.filter.assert_called_once()
        assert result == mock_query


# ============================================================
# Tests for ENTITY_LIST_HANDLERS mapping
# ============================================================

class TestEntityListHandlers:
    """Tests for the ENTITY_LIST_HANDLERS mapping."""

    def test_all_listing_types_have_handlers(self):
        """Test that all ListingType enum values have handlers."""
        for listing_type in ListingType:
            assert listing_type in ENTITY_LIST_HANDLERS, \
                f"Missing handler for {listing_type}"

    def test_handlers_are_callable(self):
        """Test that all handlers are callable functions."""
        for listing_type, handler in ENTITY_LIST_HANDLERS.items():
            assert callable(handler), \
                f"Handler for {listing_type} is not callable"

    def test_handler_mapping_contents(self):
        """Test specific handler mappings exist."""
        expected_mappings = [
            ListingType.locations,
            ListingType.buildings,
            ListingType.wings,
            ListingType.floors,
            ListingType.racks,
            ListingType.devices,
            ListingType.device_types,
            ListingType.makes,
            ListingType.models,
            ListingType.datacenters,
            ListingType.asset_owner,
            ListingType.applications,
        ]
        
        for listing_type in expected_mappings:
            assert listing_type in ENTITY_LIST_HANDLERS


# ============================================================
# Tests for list_* functions with mocked DB
# ============================================================

class TestListLocations:
    """Tests for list_locations function."""

    @pytest.fixture
    def mock_db(self):
        """Create a mock database session."""
        return MagicMock()

    def test_list_locations_returns_tuple(self, mock_db):
        """Test that list_locations returns (total, data) tuple."""
        from app.helpers.listing_helper import list_locations
        
        # Setup mock query chain
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.group_by.return_value = mock_query
        mock_query.subquery.return_value = MagicMock()
        mock_query.outerjoin.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.add_columns.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.count.return_value = 0
        mock_query.all.return_value = []
        
        result = list_locations(mock_db, offset=0, page_size=10)
        
        assert isinstance(result, tuple)
        assert len(result) == 2
        total, data = result
        assert isinstance(total, int)
        assert isinstance(data, list)

    def test_list_locations_with_filters(self, mock_db):
        """Test list_locations with filter parameters."""
        from app.helpers.listing_helper import list_locations
        
        # Setup mock query chain
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.group_by.return_value = mock_query
        mock_query.subquery.return_value = MagicMock()
        mock_query.outerjoin.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.add_columns.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.count.return_value = 0
        mock_query.all.return_value = []
        
        result = list_locations(
            mock_db,
            offset=0,
            page_size=10,
            location_name="NYC",
            location_description="Data Center"
        )
        
        assert isinstance(result, tuple)
        # filter() should have been called for the filters
        assert mock_query.filter.called


class TestListBuildings:
    """Tests for list_buildings function."""

    @pytest.fixture
    def mock_db(self):
        return MagicMock()

    def test_list_buildings_returns_tuple(self, mock_db):
        """Test that list_buildings returns (total, data) tuple."""
        from app.helpers.listing_helper import list_buildings
        
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.group_by.return_value = mock_query
        mock_query.subquery.return_value = MagicMock()
        mock_query.join.return_value = mock_query
        mock_query.outerjoin.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.add_columns.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.count.return_value = 0
        mock_query.all.return_value = []
        
        result = list_buildings(mock_db, offset=0, page_size=10)
        
        assert isinstance(result, tuple)
        assert len(result) == 2


class TestListRacks:
    """Tests for list_racks function."""

    @pytest.fixture
    def mock_db(self):
        return MagicMock()

    def test_list_racks_returns_tuple(self, mock_db):
        """Test that list_racks returns (total, data) tuple."""
        from app.helpers.listing_helper import list_racks
        
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.group_by.return_value = mock_query
        mock_query.subquery.return_value = MagicMock()
        mock_query.join.return_value = mock_query
        mock_query.outerjoin.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.add_columns.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.count.return_value = 0
        mock_query.all.return_value = []
        
        result = list_racks(mock_db, offset=0, page_size=10)
        
        assert isinstance(result, tuple)
        assert len(result) == 2


class TestListDevices:
    """Tests for list_devices function."""

    @pytest.fixture
    def mock_db(self):
        return MagicMock()

    def test_list_devices_returns_tuple(self, mock_db):
        """Test that list_devices returns (total, data) tuple."""
        from app.helpers.listing_helper import list_devices
        
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.join.return_value = mock_query
        mock_query.outerjoin.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.add_columns.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.count.return_value = 0
        mock_query.all.return_value = []
        
        result = list_devices(mock_db, offset=0, page_size=10)
        
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_list_devices_with_date_filters(self, mock_db):
        """Test list_devices with date filter parameters."""
        from app.helpers.listing_helper import list_devices
        
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.join.return_value = mock_query
        mock_query.outerjoin.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.add_columns.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.count.return_value = 0
        mock_query.all.return_value = []
        
        result = list_devices(
            mock_db,
            offset=0,
            page_size=10,
            warranty_start_date=date(2025, 1, 1),
            warranty_end_date=date(2026, 1, 1),
        )
        
        assert isinstance(result, tuple)


class TestListDeviceTypes:
    """Tests for list_device_types function."""

    @pytest.fixture
    def mock_db(self):
        return MagicMock()

    def test_list_device_types_returns_tuple(self, mock_db):
        """Test that list_device_types returns (total, data) tuple."""
        from app.helpers.listing_helper import list_device_types
        
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.group_by.return_value = mock_query
        mock_query.subquery.return_value = MagicMock()
        mock_query.join.return_value = mock_query
        mock_query.outerjoin.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.add_columns.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.count.return_value = 0
        mock_query.all.return_value = []
        
        result = list_device_types(mock_db, offset=0, page_size=10)
        
        assert isinstance(result, tuple)
        assert len(result) == 2


class TestListMakes:
    """Tests for list_makes function."""

    @pytest.fixture
    def mock_db(self):
        return MagicMock()

    def test_list_makes_returns_tuple(self, mock_db):
        """Test that list_makes returns (total, data) tuple."""
        from app.helpers.listing_helper import list_makes
        
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.group_by.return_value = mock_query
        mock_query.subquery.return_value = MagicMock()
        mock_query.outerjoin.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.add_columns.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.count.return_value = 0
        mock_query.all.return_value = []
        
        result = list_makes(mock_db, offset=0, page_size=10)
        
        assert isinstance(result, tuple)
        assert len(result) == 2


class TestListModels:
    """Tests for list_models function."""

    @pytest.fixture
    def mock_db(self):
        return MagicMock()

    def test_list_models_returns_tuple(self, mock_db):
        """Test that list_models returns (total, data) tuple."""
        from app.helpers.listing_helper import list_models
        
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.join.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.add_columns.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.count.return_value = 0
        mock_query.all.return_value = []
        
        result = list_models(mock_db, offset=0, page_size=10)
        
        assert isinstance(result, tuple)
        assert len(result) == 2


class TestListDatacenters:
    """Tests for list_datacenters function."""

    @pytest.fixture
    def mock_db(self):
        return MagicMock()

    def test_list_datacenters_returns_tuple(self, mock_db):
        """Test that list_datacenters returns (total, data) tuple."""
        from app.helpers.listing_helper import list_datacenters
        
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.group_by.return_value = mock_query
        mock_query.subquery.return_value = MagicMock()
        mock_query.join.return_value = mock_query
        mock_query.outerjoin.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.add_columns.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.count.return_value = 0
        mock_query.all.return_value = []
        
        result = list_datacenters(mock_db, offset=0, page_size=10)
        
        assert isinstance(result, tuple)
        assert len(result) == 2


class TestListWings:
    """Tests for list_wings function."""

    @pytest.fixture
    def mock_db(self):
        return MagicMock()

    def test_list_wings_returns_tuple(self, mock_db):
        """Test that list_wings returns (total, data) tuple."""
        from app.helpers.listing_helper import list_wings
        
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.group_by.return_value = mock_query
        mock_query.subquery.return_value = MagicMock()
        mock_query.join.return_value = mock_query
        mock_query.outerjoin.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.add_columns.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.count.return_value = 0
        mock_query.all.return_value = []
        
        result = list_wings(mock_db, offset=0, page_size=10)
        
        assert isinstance(result, tuple)
        assert len(result) == 2


class TestListFloors:
    """Tests for list_floors function."""

    @pytest.fixture
    def mock_db(self):
        return MagicMock()

    def test_list_floors_returns_tuple(self, mock_db):
        """Test that list_floors returns (total, data) tuple."""
        from app.helpers.listing_helper import list_floors
        
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.group_by.return_value = mock_query
        mock_query.subquery.return_value = MagicMock()
        mock_query.join.return_value = mock_query
        mock_query.outerjoin.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.add_columns.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.count.return_value = 0
        mock_query.all.return_value = []
        
        result = list_floors(mock_db, offset=0, page_size=10)
        
        assert isinstance(result, tuple)
        assert len(result) == 2


class TestListAssetOwners:
    """Tests for list_asset_owners function."""

    @pytest.fixture
    def mock_db(self):
        return MagicMock()

    def test_list_asset_owners_returns_tuple(self, mock_db):
        """Test that list_asset_owners returns (total, data) tuple."""
        from app.helpers.listing_helper import list_asset_owners
        
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.group_by.return_value = mock_query
        mock_query.subquery.return_value = MagicMock()
        mock_query.outerjoin.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.add_columns.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.count.return_value = 0
        mock_query.all.return_value = []
        
        result = list_asset_owners(mock_db, offset=0, page_size=10)
        
        assert isinstance(result, tuple)
        assert len(result) == 2


class TestListApplications:
    """Tests for list_applications function."""

    @pytest.fixture
    def mock_db(self):
        return MagicMock()

    def test_list_applications_returns_tuple(self, mock_db):
        """Test that list_applications returns (total, data) tuple."""
        from app.helpers.listing_helper import list_applications
        
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.group_by.return_value = mock_query
        mock_query.subquery.return_value = MagicMock()
        mock_query.outerjoin.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.add_columns.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.count.return_value = 0
        mock_query.all.return_value = []
        
        result = list_applications(mock_db, offset=0, page_size=10)
        
        assert isinstance(result, tuple)
        assert len(result) == 2

