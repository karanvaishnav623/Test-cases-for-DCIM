import pytest
from unittest.mock import MagicMock, patch, ANY
from fastapi import HTTPException
from app.dcim.routers import overview_router
from app.dcim.routers.overview_router import EntityType

class TestOverviewRouter:
    """Unit tests for overview_router module."""

    @patch("app.dcim.routers.overview_router.get_db")
    def test_get_entity_overview_location_success(self, mock_get_db):
        """Positive: Retrieve location overview successfully."""
        mock_db = MagicMock()
        mock_get_db.return_value = mock_db
        
        # Mock entity
        mock_loc = MagicMock()
        mock_loc.id = 1
        mock_loc.name = "Test Loc"
        mock_loc.build_image = None
        mock_loc.buildings = [MagicMock()]
        mock_loc.wings = []
        mock_loc.floors = []
        mock_loc.datacenters = []
        mock_loc.racks = []
        mock_loc.devices = []
        
        # Mock DB execute result
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_loc
        mock_db.execute.return_value = mock_result
        
        # Call endpoint
        response = overview_router.get_entity_overview(
            entity_name="Test Loc",
            entity_type=EntityType.location,
            location=None, building=None, wing=None, floor=None, datacenter=None, # Explicitly pass None
            db=mock_db,
            current_user=MagicMock(),
            access_level=5
        )
        
        assert response["name"] == "Test Loc"
        assert response["type"] == "Location"
        assert response["counts"]["buildings"] == 1
        assert "device_stats" in response

    def test_get_entity_overview_rack_success(self):
        """Positive: Retrieve rack overview (special handling)."""
        mock_db = MagicMock()
        
        mock_rack = MagicMock()
        mock_rack.id = 10
        mock_rack.name = "Rack 1"
        mock_rack.height = 42
        # Devices in rack
        dev1 = MagicMock()
        dev1.space_required = 2
        dev1.status = "active"
        dev1.device_type.name = "Server"
        mock_rack.devices = [dev1]
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_rack
        mock_db.execute.return_value = mock_result
        
        response = overview_router.get_entity_overview(
            entity_name="Rack 1",
            entity_type=EntityType.rack,
            location=None, building=None, wing=None, floor=None, datacenter=None, # Explicitly pass None
            db=mock_db,
            current_user=MagicMock(),
            access_level=5
        )
        
        assert response["type"] == "Rack"
        assert response["device_stats"]["total_devices"] == 1
        assert response["device_stats"]["active_devices"] == 1
        assert response["space_stats"]["used_space"] == 2
        
    def test_get_entity_overview_not_found(self):
        """Negative: Entity not found raises 404."""
        mock_db = MagicMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result
        
        with pytest.raises(HTTPException) as exc:
            overview_router.get_entity_overview(
                entity_name="Missing",
                entity_type=EntityType.location,
                location=None, building=None, wing=None, floor=None, datacenter=None, # Explicitly pass None
                db=mock_db,
                current_user=MagicMock(),
                access_level=5
            )
        assert exc.value.status_code == 404

    def test_get_entity_overview_multiple_found(self):
        """Negative: Multiple entities found raises 400."""
        from sqlalchemy.exc import MultipleResultsFound
        
        mock_db = MagicMock()
        mock_db.execute.side_effect = MultipleResultsFound
        
        with pytest.raises(HTTPException) as exc:
            overview_router.get_entity_overview(
                entity_name="Duplicate",
                entity_type=EntityType.building,
                location=None, building=None, wing=None, floor=None, datacenter=None, # Explicitly pass None
                db=mock_db,
                current_user=MagicMock(),
                access_level=5
            )
        assert exc.value.status_code == 400
        assert "Multiple Building entities" in exc.value.detail

    def test_apply_hierarchy_filters(self):
        """Positive: Hierarchy filters modify query."""
        mock_query = MagicMock()
        mock_model = MagicMock()
        
        # Test applying location filter
        overview_router.apply_hierarchy_filters(
            mock_query, mock_model, location="Loc1", 
            building=None, wing=None, floor=None, datacenter=None
        )
        # Should join location and filter by name
        mock_query.join.assert_called()
        mock_query.join.return_value.where.assert_called()

    def test_stats_helpers(self):
        """Positive: Verify calculation logic."""
        dev1 = MagicMock()
        dev1.space_required = 4
        dev1.status = "active"
        dev1.device_type.name = "TypeA"
        
        dev2 = MagicMock()
        dev2.space_required = 2
        dev2.status = "inactive"
        dev2.device_type = None # Test none safety
        
        devices = [dev1, dev2]
        
        # Space stats
        space = overview_router.calculate_space_stats(devices, 42)
        assert space["used_space"] == 6
        assert space["available_space"] == 36
        
        # Device stats
        stats = overview_router.calculate_device_stats(devices)
        assert stats["total_devices"] == 2
        assert stats["active_devices"] == 1
        
        # Breakdown
        breakdown = overview_router.get_device_type_breakdown(devices)
        assert len(breakdown) == 2
        names = [x["device_type"] for x in breakdown]
        assert "TypeA" in names
        assert "Unknown" in names
