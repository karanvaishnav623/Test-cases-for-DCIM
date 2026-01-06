import pytest
from unittest.mock import MagicMock, patch
from app.dcim.routers import hierarchy_router

class TestHierarchyRouter:
    """Unit tests for hierarchy_router module."""

    def test_get_hierarchy_success(self):
        """Positive: Returns nested hierarchy structure."""
        db = MagicMock()
        
        # Mock nested objects
        loc = MagicMock()
        loc.id = 1
        loc.name = "Loc1"
        
        bldg = MagicMock()
        bldg.id = 2
        bldg.name = "Bldg1"
        
        wing = MagicMock()
        wing.id = 3
        wing.name = "Wing1"
        
        floor = MagicMock()
        floor.id = 4
        floor.name = "Floor1"
        
        dc = MagicMock()
        dc.id = 5
        dc.name = "DC1"
        
        rack = MagicMock()
        rack.id = 6
        rack.name = "Rack1"
        
        device = MagicMock()
        device.id = 7
        device.name = "Dev1"
        
        # Link them
        rack.devices = [device]
        dc.racks = [rack]
        floor.datacenters = [dc]
        wing.floors = [floor]
        bldg.wings = [wing]
        loc.buildings = [bldg]
        
        # Mock DB execute
        db.execute.return_value.scalars.return_value.all.return_value = [loc]
        
        result = hierarchy_router.get_hierarchy(
            access_level=MagicMock(),
            db=db,
            current_user=MagicMock()
        )
        
        assert len(result) == 1
        loc_res = result[0]
        assert loc_res["name"] == "Loc1"
        assert loc_res["type"] == "Location"
        
        bldg_res = loc_res["children"][0]
        assert bldg_res["name"] == "Bldg1"
        
        # Verify deep nesting
        dev_res = bldg_res["children"][0]["children"][0]["children"][0]["children"][0]["children"][0]
        assert dev_res["name"] == "Dev1"
        assert dev_res["type"] == "Device"
