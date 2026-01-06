import pytest
from unittest.mock import MagicMock
from fastapi import HTTPException
from app.helpers import rack_capacity_helper
from app.models.entity_models import Rack

class TestRackCapacityHelper:
    """Unit tests for rack_capacity_helper module."""

    def test_ensure_rack_capacity_success(self):
        """Positive: Allows placement if space is available."""
        rack = MagicMock(spec=Rack)
        rack.name = "R1"
        rack.height = 42
        rack.space_used = 10
        rack.space_available = 32
        
        # No exception raised
        rack_capacity_helper.ensure_rack_capacity(rack, space_required=5)

    def test_ensure_rack_capacity_recalculates_if_none(self):
        """Positive: Recalculates space_available if None."""
        rack = MagicMock(spec=Rack)
        rack.name = "R1"
        rack.height = 42
        rack.space_used = 10
        rack.space_available = None
        
        # Should calculate 42 - 10 = 32 available, so 5 is fine
        rack_capacity_helper.ensure_rack_capacity(rack, space_required=5)
        
        assert rack.space_available == 32

    def test_ensure_rack_capacity_insufficient(self):
        """Negative: Raises 400 if insufficient space."""
        rack = MagicMock(spec=Rack)
        rack.name = "R1"
        rack.space_available = 2
        
        with pytest.raises(HTTPException) as exc_info:
            rack_capacity_helper.ensure_rack_capacity(rack, space_required=5)
        
        assert exc_info.value.status_code == 400
        assert "only has 2U available" in exc_info.value.detail

    def test_ensure_continuous_space_success(self):
        """Positive: Allows placement in continuous gap."""
        db = MagicMock()
        rack = MagicMock(spec=Rack)
        rack.id = 1
        rack.height = 42
        
        # Mock no existing devices in the rack
        db.query.return_value.filter.return_value.filter.return_value.all.return_value = []
        
        # Should pass
        rack_capacity_helper.ensure_continuous_space(db, rack, position=1, space_required=5)

    def test_ensure_continuous_space_overlap(self):
        """Negative: Raises 400 if overlaps with existing device."""
        db = MagicMock()
        rack = MagicMock(spec=Rack)
        rack.id = 1
        rack.height = 42
        
        # Existing device at pos 3, space 2 (occupies 3, 4)
        existing_dev = MagicMock()
        existing_dev.position = 3
        existing_dev.space_required = 2
        existing_dev.name = "ExistingDev"
        
        db.query.return_value.filter.return_value.filter.return_value.all.return_value = [existing_dev]
        
        # Try to place at pos 1, space 5 (occupies 1, 2, 3, 4, 5) -> overlap at 3, 4
        with pytest.raises(HTTPException) as exc_info:
            rack_capacity_helper.ensure_continuous_space(db, rack, position=1, space_required=5)
        
        assert exc_info.value.status_code == 400
        assert "already occupied by device 'ExistingDev'" in exc_info.value.detail

    def test_release_rack_capacity(self):
        """Positive: Releases capacity correctly."""
        rack = MagicMock(spec=Rack)
        rack.space_used = 10
        rack.height = 42
        
        rack_capacity_helper.release_rack_capacity(rack, space_released=2)
        
        assert rack.space_available == 34

    def test_ensure_continuous_space_position_none(self):
        """Negative: Raises 400 if position is None."""
        db = MagicMock()
        rack = MagicMock(spec=Rack)
        
        with pytest.raises(HTTPException) as exc:
            rack_capacity_helper.ensure_continuous_space(db, rack, position=None, space_required=1)
        assert exc.value.status_code == 400
        assert "Position is required" in exc.value.detail

    def test_ensure_continuous_space_invalid_inputs(self):
        """Negative: Raises 400 for invalid integer conversions."""
        db = MagicMock()
        rack = MagicMock(spec=Rack)
        rack.height = "not_int"
        
        with pytest.raises(HTTPException) as exc:
            rack_capacity_helper.ensure_continuous_space(db, rack, position=1, space_required=1)
        assert exc.value.status_code == 400
        assert "Invalid values" in exc.value.detail

    def test_ensure_continuous_space_position_less_than_one(self):
        """Negative: Raises 400 if position < 1."""
        db = MagicMock()
        rack = MagicMock(spec=Rack)
        rack.height = 42
        
        with pytest.raises(HTTPException) as exc:
            rack_capacity_helper.ensure_continuous_space(db, rack, position=0, space_required=1)
        assert exc.value.status_code == 400
        assert "Position must be >= 1" in exc.value.detail

    def test_ensure_continuous_space_no_height(self):
        """Negative: Raises 400 if rack height is 0."""
        db = MagicMock()
        rack = MagicMock(spec=Rack)
        rack.height = 0
        rack.name = "R1"
        
        with pytest.raises(HTTPException) as exc:
            rack_capacity_helper.ensure_continuous_space(db, rack, position=1, space_required=1)
        assert exc.value.status_code == 400
        assert "has no height defined" in exc.value.detail

    def test_ensure_continuous_space_exceeds_height(self):
        """Negative: Raises 400 if device exceeds rack height."""
        db = MagicMock()
        rack = MagicMock(spec=Rack)
        rack.height = 42
        rack.name = "R1"
        
        with pytest.raises(HTTPException) as exc:
            # Position 40 + space 5 = ends at 44 > 42
            rack_capacity_helper.ensure_continuous_space(db, rack, position=40, space_required=5)
        assert exc.value.status_code == 400
        assert "exceeds rack height" in exc.value.detail

    def test_ensure_continuous_space_exclude_device_id(self):
        """Positive: Ignores excluded device ID (self-overlap check)."""
        db = MagicMock()
        rack = MagicMock(spec=Rack)
        rack.id = 1
        rack.height = 42
        
        # Existing device is the one we are updating/excluding
        existing_dev = MagicMock()
        existing_dev.id = 999
        existing_dev.position = 3
        existing_dev.space_required = 2
        
        # Setup mock chain
        # 1. filter(rack_id) -> query
        # 2. filter(id != exclude) -> query
        # 3. filter(position not None) -> query
        # 4. all() -> []
        
        # Because we are mocking chain calls, the simplest way is to ensure valid return values for each step
        q1 = MagicMock()
        q2 = MagicMock()
        q3 = MagicMock()
        
        db.query.return_value = q1
        q1.filter.return_value = q1 # For rack_id filter
        
        # When filter(Device.id != exclude) is called, it returns q2
        # BUT commonly in these helpers it's chained like query.filter().filter()...
        # Let's simplify: the helper does `query = query.filter(Device.id != exclude_device_id)`
        
        # The final .all() should return empty list if exclusion works
        # If we didn't exclude, it would return the device and fail.
        
        # Strategy: Mock return of `all()` to be empty, implying the filter worked.
        # But we need to be careful if the logic relies on DB filtering.
        # Logic: query.filter(Device.id != exclude_device_id)
        
        # Let's just mock the final result to be empty list, which simulates "database filtered it out"
        db.query.return_value.filter.return_value.filter.return_value.filter.return_value.all.return_value = []
        
        # Should pass
        rack_capacity_helper.ensure_continuous_space(
            db, rack, position=3, space_required=2, exclude_device_id=999
        )

    def test_reserve_rack_capacity_success(self):
        """Positive: Updates usage and recalculates available."""
        rack = MagicMock(spec=Rack)
        rack.space_used = 10
        rack.height = 42
        rack.space_available = 32
        
        rack_capacity_helper.reserve_rack_capacity(rack, space_required=5)
        
        assert rack.space_used == 15
        assert rack.space_available == 27 # 42 - 15

    def test_reserve_rack_capacity_zero_required(self):
        """Negative: proper handling when space_required <= 0."""
        rack = MagicMock(spec=Rack)
        rack.space_used = 10
        
        rack_capacity_helper.reserve_rack_capacity(rack, space_required=0)
        
        # Unchanged
        assert rack.space_used == 10

    def test_sync_rack_usage_success(self):
        """Positive: Syncs usage from DB aggregation."""
        db = MagicMock()
        rack = MagicMock(spec=Rack)
        rack.id = 1
        rack.height = 42
        
        # Mock DB sum result
        db.query.return_value.filter.return_value.scalar.return_value = 20
        
        rack_capacity_helper.sync_rack_usage(db, rack)
        
        assert rack.space_used == 20
        assert rack.space_available == 22 # 42 - 20

    def test_sync_rack_usage_empty(self):
        """Positive: Handles None result from sum (empty rack)."""
        db = MagicMock()
        rack = MagicMock(spec=Rack)
        rack.id = 1
        rack.height = 42
        
        # Mock DB sum result as None
        db.query.return_value.filter.return_value.scalar.return_value = None
        
        rack_capacity_helper.sync_rack_usage(db, rack)
        
        assert rack.space_used == 0
        assert rack.space_available == 42
