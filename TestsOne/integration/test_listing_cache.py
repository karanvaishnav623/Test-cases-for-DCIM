# tests/integration/test_listing_cache.py
"""
Integration tests for listing_cache.py

Tests the cache behavior in the context of:
- API endpoint integration
- Cache key generation with real ListingType values
- Entity invalidation across multiple cache entries
- Thread safety with concurrent access
- Integration with listing router
"""

import pytest
import threading
import time
from unittest.mock import patch, MagicMock
from datetime import date

from fastapi import status
from fastapi.testclient import TestClient

from app.main import app
from app.db.session import get_db
from app.helpers.auth_helper import get_current_user
from app.helpers.rbac_helper import require_at_least_viewer
from app.helpers.listing_cache import (
    listing_cache,
    build_listing_cache_key,
    invalidate_listing_cache_for_entity,
    clear_all_listing_cache,
)
from app.helpers.listing_types import ListingType


# ============================================================
# Fixtures
# ============================================================

class DummyUser:
    def __init__(self, user_id: int = 1) -> None:
        self.id = user_id


class DummyAccessLevel:
    def __init__(self, value: str = "viewer") -> None:
        self.value = value


@pytest.fixture(autouse=True)
def clear_cache_before_each_test():
    """Clear cache before each test to ensure isolation."""
    listing_cache.invalidate_all()
    yield
    listing_cache.invalidate_all()


@pytest.fixture
def mock_cache_settings():
    """Enable cache with test-friendly settings."""
    with patch("app.helpers.listing_cache.settings") as mock_settings:
        mock_settings.LISTING_CACHE_TTL_SECONDS = 60
        mock_settings.LISTING_CACHE_MAX_ENTRIES = 100
        yield mock_settings


# ============================================================
# Tests for cache key generation with real entities
# ============================================================

class TestCacheKeyGenerationIntegration:
    """Integration tests for cache key generation with real ListingType values."""

    def test_cache_key_for_all_listing_types(self):
        """Test cache key generation works for all ListingType enum values."""
        for listing_type in ListingType:
            key = build_listing_cache_key(
                entity=listing_type,
                offset=0,
                page_size=10,
                user_id=1,
                access_level="viewer",
            )
            assert isinstance(key, str)
            assert len(key) == 64  # SHA256 hex digest

    def test_different_listing_types_produce_different_keys(self):
        """Test that different entity types produce different cache keys."""
        keys = set()
        for listing_type in ListingType:
            key = build_listing_cache_key(
                entity=listing_type,
                offset=0,
                page_size=10,
                user_id=1,
                access_level="viewer",
            )
            keys.add(key)
        
        # All keys should be unique
        assert len(keys) == len(ListingType)

    def test_cache_key_with_typical_device_filters(self):
        """Test cache key with typical device listing filters."""
        key = build_listing_cache_key(
            entity=ListingType.devices,
            offset=0,
            page_size=25,
            user_id=42,
            access_level="editor",
            location_name="NYC",
            building_name="Building A",
            rack_name="Rack-01",
            device_status="active",
            warranty_start_date=date(2024, 1, 1),
            warranty_end_date=date(2025, 12, 31),
        )
        assert isinstance(key, str)
        assert len(key) == 64

    def test_cache_key_with_typical_rack_filters(self):
        """Test cache key with typical rack listing filters."""
        key = build_listing_cache_key(
            entity=ListingType.racks,
            offset=20,
            page_size=50,
            user_id=1,
            access_level="admin",
            location_name="LA",
            datacenter_name="DC-1",
            rack_height=42,
            rack_status="active",
        )
        assert isinstance(key, str)

    def test_cache_key_consistency_across_calls(self):
        """Test that same parameters always produce same key."""
        params = {
            "entity": ListingType.buildings,
            "offset": 10,
            "page_size": 20,
            "user_id": 5,
            "access_level": "viewer",
            "location_name": "Chicago",
        }
        
        keys = [build_listing_cache_key(**params) for _ in range(10)]
        
        # All keys should be identical
        assert len(set(keys)) == 1


# ============================================================
# Tests for entity invalidation integration
# ============================================================

class TestEntityInvalidationIntegration:
    """Integration tests for entity-based cache invalidation."""

    def test_invalidate_locations_clears_location_entries(self, mock_cache_settings):
        """Test invalidating locations clears all location cache entries."""
        # Add multiple location entries
        listing_cache.set("loc_key_1", {"data": 1}, entity=ListingType.locations)
        listing_cache.set("loc_key_2", {"data": 2}, entity=ListingType.locations)
        listing_cache.set("loc_key_3", {"data": 3}, entity=ListingType.locations)
        
        # Add entries for other entities
        listing_cache.set("dev_key_1", {"data": 4}, entity=ListingType.devices)
        listing_cache.set("rack_key_1", {"data": 5}, entity=ListingType.racks)
        
        # Invalidate locations
        invalidate_listing_cache_for_entity(ListingType.locations)
        
        # Location entries should be gone
        assert listing_cache.get("loc_key_1") is None
        assert listing_cache.get("loc_key_2") is None
        assert listing_cache.get("loc_key_3") is None
        
        # Other entities should remain
        assert listing_cache.get("dev_key_1") is not None
        assert listing_cache.get("rack_key_1") is not None

    def test_invalidate_devices_clears_device_entries(self, mock_cache_settings):
        """Test invalidating devices clears all device cache entries."""
        listing_cache.set("dev_1", {"id": 1}, entity=ListingType.devices)
        listing_cache.set("dev_2", {"id": 2}, entity=ListingType.devices)
        listing_cache.set("loc_1", {"id": 1}, entity=ListingType.locations)
        
        invalidate_listing_cache_for_entity(ListingType.devices)
        
        assert listing_cache.get("dev_1") is None
        assert listing_cache.get("dev_2") is None
        assert listing_cache.get("loc_1") is not None

    def test_invalidate_all_entity_types(self, mock_cache_settings):
        """Test invalidating each entity type works correctly."""
        # Add one entry for each entity type
        for listing_type in ListingType:
            key = f"test_{listing_type.value}"
            listing_cache.set(key, {"type": listing_type.value}, entity=listing_type)
        
        # Verify all entries exist
        for listing_type in ListingType:
            key = f"test_{listing_type.value}"
            assert listing_cache.get(key) is not None
        
        # Invalidate each type one by one
        for listing_type in ListingType:
            invalidate_listing_cache_for_entity(listing_type)
            key = f"test_{listing_type.value}"
            assert listing_cache.get(key) is None

    def test_clear_all_cache_removes_everything(self, mock_cache_settings):
        """Test clear_all_listing_cache removes all entries."""
        # Add entries for multiple entities
        listing_cache.set("key1", {"data": 1}, entity=ListingType.locations)
        listing_cache.set("key2", {"data": 2}, entity=ListingType.devices)
        listing_cache.set("key3", {"data": 3}, entity=ListingType.racks)
        listing_cache.set("key4", {"data": 4}, entity=ListingType.buildings)
        
        clear_all_listing_cache()
        
        assert listing_cache.get("key1") is None
        assert listing_cache.get("key2") is None
        assert listing_cache.get("key3") is None
        assert listing_cache.get("key4") is None


# ============================================================
# Tests for thread safety
# ============================================================

class TestCacheThreadSafety:
    """Integration tests for cache thread safety."""

    def test_concurrent_reads_and_writes(self, mock_cache_settings):
        """Test cache handles concurrent reads and writes correctly."""
        results = {"errors": [], "reads": 0, "writes": 0}
        
        def writer_thread(thread_id):
            try:
                for i in range(50):
                    key = f"thread_{thread_id}_key_{i}"
                    listing_cache.set(key, {"thread": thread_id, "i": i}, entity=ListingType.devices)
                    results["writes"] += 1
            except Exception as e:
                results["errors"].append(f"Writer {thread_id}: {e}")
        
        def reader_thread(thread_id):
            try:
                for i in range(50):
                    key = f"thread_0_key_{i}"
                    listing_cache.get(key)
                    results["reads"] += 1
            except Exception as e:
                results["errors"].append(f"Reader {thread_id}: {e}")
        
        threads = []
        # Create writer threads
        for i in range(3):
            t = threading.Thread(target=writer_thread, args=(i,))
            threads.append(t)
        
        # Create reader threads
        for i in range(3):
            t = threading.Thread(target=reader_thread, args=(i,))
            threads.append(t)
        
        # Start all threads
        for t in threads:
            t.start()
        
        # Wait for completion
        for t in threads:
            t.join()
        
        # No errors should have occurred
        assert len(results["errors"]) == 0, f"Errors: {results['errors']}"

    def test_concurrent_invalidation(self, mock_cache_settings):
        """Test cache handles concurrent invalidation correctly."""
        errors = []
        
        def populate_cache():
            for i in range(20):
                listing_cache.set(f"key_{i}", {"i": i}, entity=ListingType.locations)
        
        def invalidate_thread():
            try:
                for _ in range(10):
                    invalidate_listing_cache_for_entity(ListingType.locations)
                    time.sleep(0.001)
            except Exception as e:
                errors.append(str(e))
        
        def write_thread():
            try:
                for i in range(20):
                    listing_cache.set(f"new_key_{i}", {"i": i}, entity=ListingType.locations)
            except Exception as e:
                errors.append(str(e))
        
        populate_cache()
        
        threads = [
            threading.Thread(target=invalidate_thread),
            threading.Thread(target=invalidate_thread),
            threading.Thread(target=write_thread),
            threading.Thread(target=write_thread),
        ]
        
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        assert len(errors) == 0, f"Errors: {errors}"


# ============================================================
# Tests for cache behavior with API-like scenarios
# ============================================================

class TestCacheAPIScenarios:
    """Integration tests simulating API usage patterns."""

    def test_pagination_caching_scenario(self, mock_cache_settings):
        """Test caching works correctly for paginated requests."""
        # Simulate caching paginated results
        for page in range(5):
            offset = page * 10
            key = build_listing_cache_key(
                entity=ListingType.devices,
                offset=offset,
                page_size=10,
                user_id=1,
                access_level="viewer",
            )
            listing_cache.set(
                key,
                {"page": page, "results": list(range(offset, offset + 10))},
                entity=ListingType.devices,
            )
        
        # Verify each page is cached separately
        for page in range(5):
            offset = page * 10
            key = build_listing_cache_key(
                entity=ListingType.devices,
                offset=offset,
                page_size=10,
                user_id=1,
                access_level="viewer",
            )
            cached = listing_cache.get(key)
            assert cached is not None
            assert cached["page"] == page

    def test_filter_variation_caching(self, mock_cache_settings):
        """Test that different filters produce separate cache entries."""
        # Same entity, different filters
        filters_variations = [
            {"location_name": "NYC"},
            {"location_name": "LA"},
            {"location_name": "NYC", "building_name": "A"},
            {"rack_status": "active"},
            {},  # No filters
        ]
        
        keys = []
        for filters in filters_variations:
            key = build_listing_cache_key(
                entity=ListingType.racks,
                offset=0,
                page_size=10,
                user_id=1,
                access_level="viewer",
                **filters,
            )
            keys.append(key)
            listing_cache.set(key, {"filters": filters}, entity=ListingType.racks)
        
        # All keys should be unique
        assert len(set(keys)) == len(filters_variations)
        
        # All entries should be retrievable
        for key in keys:
            assert listing_cache.get(key) is not None

    def test_user_specific_caching(self, mock_cache_settings):
        """Test that different users get separate cache entries."""
        user_ids = [1, 2, 3, 100]
        
        for user_id in user_ids:
            key = build_listing_cache_key(
                entity=ListingType.locations,
                offset=0,
                page_size=10,
                user_id=user_id,
                access_level="viewer",
            )
            listing_cache.set(key, {"user_id": user_id}, entity=ListingType.locations)
        
        # Verify each user has separate cache
        for user_id in user_ids:
            key = build_listing_cache_key(
                entity=ListingType.locations,
                offset=0,
                page_size=10,
                user_id=user_id,
                access_level="viewer",
            )
            cached = listing_cache.get(key)
            assert cached is not None
            assert cached["user_id"] == user_id

    def test_access_level_specific_caching(self, mock_cache_settings):
        """Test that different access levels get separate cache entries."""
        access_levels = ["viewer", "editor", "admin"]
        
        for level in access_levels:
            key = build_listing_cache_key(
                entity=ListingType.devices,
                offset=0,
                page_size=10,
                user_id=1,
                access_level=level,
            )
            listing_cache.set(key, {"access_level": level}, entity=ListingType.devices)
        
        # Verify each access level has separate cache
        for level in access_levels:
            key = build_listing_cache_key(
                entity=ListingType.devices,
                offset=0,
                page_size=10,
                user_id=1,
                access_level=level,
            )
            cached = listing_cache.get(key)
            assert cached is not None
            assert cached["access_level"] == level

    def test_cache_invalidation_after_entity_modification(self, mock_cache_settings):
        """Test cache is properly invalidated when entity is modified."""
        # Simulate: User lists devices, cache is populated
        key = build_listing_cache_key(
            entity=ListingType.devices,
            offset=0,
            page_size=10,
            user_id=1,
            access_level="viewer",
        )
        listing_cache.set(key, {"devices": ["dev1", "dev2"]}, entity=ListingType.devices)
        
        # Verify cache hit
        assert listing_cache.get(key) is not None
        
        # Simulate: Device is added/updated/deleted -> invalidate cache
        invalidate_listing_cache_for_entity(ListingType.devices)
        
        # Cache should be cleared
        assert listing_cache.get(key) is None


# ============================================================
# Tests for cache with disabled settings
# ============================================================

class TestCacheDisabledBehavior:
    """Integration tests for cache behavior when disabled."""

    def test_cache_disabled_returns_none(self):
        """Test that cache returns None when disabled."""
        with patch("app.helpers.listing_cache.settings") as mock_settings:
            mock_settings.LISTING_CACHE_TTL_SECONDS = 0
            mock_settings.LISTING_CACHE_MAX_ENTRIES = 0
            
            # Try to set
            listing_cache.set("test_key", {"data": 1}, entity=ListingType.devices)
            
            # Should return None
            result = listing_cache.get("test_key")
            assert result is None

    def test_cache_disabled_with_zero_ttl(self):
        """Test cache disabled when TTL is 0."""
        with patch("app.helpers.listing_cache.settings") as mock_settings:
            mock_settings.LISTING_CACHE_TTL_SECONDS = 0
            mock_settings.LISTING_CACHE_MAX_ENTRIES = 100
            
            listing_cache.set("key", {"data": 1}, entity=ListingType.locations)
            assert listing_cache.get("key") is None

    def test_cache_disabled_with_zero_max_entries(self):
        """Test cache disabled when max entries is 0."""
        with patch("app.helpers.listing_cache.settings") as mock_settings:
            mock_settings.LISTING_CACHE_TTL_SECONDS = 300
            mock_settings.LISTING_CACHE_MAX_ENTRIES = 0
            
            listing_cache.set("key", {"data": 1}, entity=ListingType.locations)
            assert listing_cache.get("key") is None

