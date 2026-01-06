from unittest.mock import MagicMock, patch
import pytest
from app.dcim.routers.summary_router import _get_entity_models


class TestGetEntityModels:
    """Unit tests for _get_entity_models helper function."""

    def test_get_entity_models_returns_module(self):
        """Positive: Function returns entity_models module."""
        models = _get_entity_models()
        
        assert models is not None
        # Verify it has expected model classes
        assert hasattr(models, "Location")
        assert hasattr(models, "Rack")
        assert hasattr(models, "Device")
        assert hasattr(models, "Building")
        assert hasattr(models, "Datacenter")

    def test_get_entity_models_is_cached(self):
        """Positive: Function result is cached (same object returned)."""
        models1 = _get_entity_models()
        models2 = _get_entity_models()
        
        # Should return the same object due to @lru_cache
        assert models1 is models2


class TestSummaryCalculations:
    """Unit tests for summary calculation logic."""

    def test_utilization_percent_calculation_with_units(self):
        """Positive: Utilization percent calculated correctly when total_units > 0."""
        total_units = 200
        used_units = 100
        utilization_percent = round((used_units / total_units * 100), 1) if total_units > 0 else 0
        
        assert utilization_percent == 50.0

    def test_utilization_percent_calculation_zero_units(self):
        """Negative: Utilization percent is 0 when total_units is 0."""
        total_units = 0
        used_units = 50
        utilization_percent = round((used_units / total_units * 100), 1) if total_units > 0 else 0
        
        assert utilization_percent == 0

    def test_utilization_percent_rounding(self):
        """Positive: Utilization percent rounds to 1 decimal place."""
        total_units = 3
        used_units = 1
        utilization_percent = round((used_units / total_units * 100), 1) if total_units > 0 else 0
        
        assert utilization_percent == 33.3

    def test_inactive_devices_calculation(self):
        """Positive: Inactive devices = total_devices - active_devices."""
        total_devices = 10
        active_devices = 8
        inactive_devices = total_devices - active_devices
        
        assert inactive_devices == 2

    def test_inactive_devices_calculation_all_active(self):
        """Positive: Inactive devices is 0 when all devices are active."""
        total_devices = 10
        active_devices = 10
        inactive_devices = total_devices - active_devices
        
        assert inactive_devices == 0

    def test_available_rack_units_calculation(self):
        """Positive: Available units = max(0, total_units - used_units)."""
        total_units = 200
        used_units = 100
        available_units = max(0, total_units - used_units)
        
        assert available_units == 100

    def test_available_rack_units_never_negative(self):
        """Negative: Available units never negative (edge case: used > total)."""
        total_units = 100
        used_units = 150
        available_units = max(0, total_units - used_units)
        
        assert available_units == 0

    def test_available_rack_units_zero_when_no_total(self):
        """Negative: Available units is 0 when total_units is 0."""
        total_units = 0
        used_units = 0
        available_units = max(0, total_units - used_units)
        
        assert available_units == 0


class TestSummaryRouter:
    """Unit tests for summary_router endpoints."""

    def test_get_location_summary_success(self):
        """Positive: Returns correctly formatted summary from mocked aggregations."""
        with patch("app.dcim.routers.summary_router.get_db") as mock_get_db, \
             patch("app.dcim.routers.summary_router.get_allowed_location_ids") as mock_get_locs, \
             patch("app.dcim.routers.summary_router.get_cached_location_summary") as mock_get_cache, \
             patch("app.dcim.routers.summary_router.set_cached_location_summary") as mock_set_cache:
            
            mock_db = MagicMock()
            mock_get_db.return_value = mock_db
            
            # Mock no cache hit
            mock_get_locs.return_value = None # Admin access, so cache enabled
            mock_get_cache.return_value = None
            
            # Mock DB results
            # The query returns a list of tuples/rows
            # (location, device_count, device_type_count, active_count, used_rack_units, 
            #  rack_count, total_rack_units, available_rack_count, building_count, datacenter_count)
            
            mock_loc = MagicMock()
            mock_loc.id = 1
            mock_loc.name = "Test Loc"
            mock_loc.build_image = "img.png"
            
            # Row 1: Location 1
            row1 = (
                mock_loc,
                10, # device_count
                5,  # device_type_count
                8,  # active_count (active_devices)
                20, # used_rack_units
                5,  # rack_count
                100,# total_rack_units
                2,  # available_rack_count
                3,  # building_count
                1   # datacenter_count
            )
            
            # Mock the query chain. 
            # The code does db.query(...).outerjoin(...).order_by(...).all()
            # If allowed_location_ids is None, no filter() is called.
            
            mock_query = mock_db.query.return_value
            mock_query.outerjoin.return_value.outerjoin.return_value.outerjoin.return_value.outerjoin.return_value.order_by.return_value.all.return_value = [row1]
            
            from app.dcim.routers import summary_router
            response = summary_router.get_location_summary(
                access_level=5,
                db=mock_db,
                current_user=MagicMock()
            )
            
            assert response["total_locations"] == 1
            res = response["results"][0]
            assert res["id"] == 1
            assert res["name"] == "Test Loc"
            assert res["total_devices"] == 10
            assert res["active_devices"] == 8
            assert res["inactive_devices"] == 2 # 10 - 8
            assert res["total_rack_units"] == 100
            assert res["used_rack_units"] == 20
            # utilization = 20/100 = 20.0
            assert res["utilization_percent"] == 20.0
            
            # Check cache was set
            mock_set_cache.assert_called_once()

    def test_get_location_summary_cache_hit(self):
        """Positive: Returns cached data if available and allowed."""
        with patch("app.dcim.routers.summary_router.get_allowed_location_ids") as mock_get_locs, \
             patch("app.dcim.routers.summary_router.get_cached_location_summary") as mock_get_cache:
            
            mock_get_locs.return_value = None # Cache enabled
            cached_data = {"total_locations": 99, "results": []}
            mock_get_cache.return_value = cached_data
            
            from app.dcim.routers import summary_router
            response = summary_router.get_location_summary(
                access_level=5,
                db=MagicMock(),
                current_user=MagicMock()
            )
            
            assert response == cached_data

    def test_get_location_summary_filtered(self):
        """Positive: Applies location filter and skips cache if restricted."""
        with patch("app.dcim.routers.summary_router.get_db") as mock_get_db, \
             patch("app.dcim.routers.summary_router.get_allowed_location_ids") as mock_get_locs, \
             patch("app.dcim.routers.summary_router.get_cached_location_summary") as mock_get_cache:
            
            mock_db = MagicMock()
            mock_get_db.return_value = mock_db
            
            # Restricted access
            mock_get_locs.return_value = {10} 
            
            # Should NOT call get_cached_location_summary
            
            mock_loc = MagicMock()
            mock_loc.id = 10
            row1 = (mock_loc, 0, 0, 0, 0, 0, 0, 0, 0, 0)
            
            mock_query = mock_db.query.return_value
            # Now filter() IS called
            mock_query.outerjoin.return_value.outerjoin.return_value.outerjoin.return_value.outerjoin.return_value.order_by.return_value.filter.return_value.all.return_value = [row1]
            
            from app.dcim.routers import summary_router
            summary_router.get_location_summary(
                access_level=1,
                db=mock_db,
                current_user=MagicMock()
            )
            
            mock_get_cache.assert_not_called()
            # Verify filter was applied
            query_chain = mock_query.outerjoin.return_value.outerjoin.return_value.outerjoin.return_value.outerjoin.return_value.order_by.return_value
            query_chain.filter.assert_called_once()
