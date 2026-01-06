# tests/unit/test_listing_cache.py
"""
Unit tests for listing_cache.py

Tests the in-memory cache functionality including:
- Cache get/set operations
- TTL expiration
- Entity-based invalidation
- Cache key generation
"""

import time
from datetime import date
from unittest.mock import patch

import pytest

from app.helpers.listing_cache import (
    _ListingResponseCache,
    build_listing_cache_key,
    invalidate_listing_cache_for_entity,
    clear_all_listing_cache,
    listing_cache,
    _is_cache_enabled,
)
from app.helpers.listing_types import ListingType


# ============================================================
# Tests for _ListingResponseCache class
# ============================================================

class TestListingResponseCache:
    """Tests for the _ListingResponseCache class."""

    @pytest.fixture
    def cache(self):
        """Create a fresh cache instance for each test."""
        return _ListingResponseCache()

    @pytest.fixture
    def mock_cache_enabled(self):
        """Mock settings to enable cache."""
        with patch("app.helpers.listing_cache.settings") as mock_settings:
            mock_settings.LISTING_CACHE_TTL_SECONDS = 300
            mock_settings.LISTING_CACHE_MAX_ENTRIES = 100
            yield mock_settings

    @pytest.fixture
    def mock_cache_disabled(self):
        """Mock settings to disable cache."""
        with patch("app.helpers.listing_cache.settings") as mock_settings:
            mock_settings.LISTING_CACHE_TTL_SECONDS = 0
            mock_settings.LISTING_CACHE_MAX_ENTRIES = 0
            yield mock_settings

    # --- Basic get/set tests ---

    def test_set_and_get_returns_cached_value(self, cache, mock_cache_enabled):
        """Test that set stores value and get retrieves it."""
        key = "test_key"
        value = {"data": [1, 2, 3], "total": 3}

        cache.set(key, value, entity=ListingType.locations)
        result = cache.get(key)

        assert result == value
        assert result["data"] == [1, 2, 3]
        assert result["total"] == 3

    def test_get_returns_none_for_missing_key(self, cache, mock_cache_enabled):
        """Test that get returns None for non-existent key."""
        result = cache.get("nonexistent_key")
        assert result is None

    def test_get_returns_deep_copy(self, cache, mock_cache_enabled):
        """Test that get returns a deep copy, not the original."""
        key = "test_key"
        value = {"data": [1, 2, 3]}

        cache.set(key, value, entity=ListingType.locations)
        result = cache.get(key)

        # Modify the returned value
        result["data"].append(4)

        # Original cached value should be unchanged
        cached_again = cache.get(key)
        assert cached_again["data"] == [1, 2, 3]

    # --- Cache disabled tests ---

    def test_get_returns_none_when_cache_disabled(self, cache, mock_cache_disabled):
        """Test that get returns None when cache is disabled."""
        # Manually add to store to test get behavior
        cache._store["test_key"] = (time.time() + 300, {"data": "test"})
        
        result = cache.get("test_key")
        assert result is None

    def test_set_does_nothing_when_cache_disabled(self, cache, mock_cache_disabled):
        """Test that set does nothing when cache is disabled."""
        cache.set("test_key", {"data": "test"}, entity=ListingType.locations)
        
        # Store should remain empty
        assert len(cache._store) == 0

    # --- TTL expiration tests ---

    def test_get_returns_none_for_expired_entry(self, cache, mock_cache_enabled):
        """Test that expired entries return None."""
        key = "expired_key"
        
        # Manually set an expired entry
        cache._store[key] = (time.time() - 1, {"data": "old"})
        
        result = cache.get(key)
        assert result is None

    def test_expired_entry_is_evicted_on_get(self, cache, mock_cache_enabled):
        """Test that expired entries are removed from store on get."""
        key = "expired_key"
        
        # Manually set an expired entry
        cache._store[key] = (time.time() - 1, {"data": "old"})
        
        cache.get(key)
        
        # Entry should be removed
        assert key not in cache._store

    # --- Entity invalidation tests ---

    def test_invalidate_entity_removes_related_entries(self, cache, mock_cache_enabled):
        """Test that invalidate_entity removes all entries for that entity."""
        # Add entries for different entities
        cache.set("loc_1", {"id": 1}, entity=ListingType.locations)
        cache.set("loc_2", {"id": 2}, entity=ListingType.locations)
        cache.set("dev_1", {"id": 1}, entity=ListingType.devices)

        # Invalidate locations
        cache.invalidate_entity(ListingType.locations)

        # Location entries should be gone
        assert cache.get("loc_1") is None
        assert cache.get("loc_2") is None
        
        # Device entry should remain
        assert cache.get("dev_1") is not None

    def test_invalidate_entity_with_string(self, cache, mock_cache_enabled):
        """Test that invalidate_entity works with string entity names."""
        cache.set("key1", {"data": 1}, entity="locations")
        
        cache.invalidate_entity("locations")
        
        assert cache.get("key1") is None

    def test_invalidate_entity_with_none_does_nothing(self, cache, mock_cache_enabled):
        """Test that invalidate_entity with None entity does nothing."""
        cache.set("key1", {"data": 1}, entity=ListingType.locations)
        
        # This should not raise and should not clear anything
        cache.invalidate_entity(None)  # type: ignore
        
        assert cache.get("key1") is not None

    # --- Clear/invalidate all tests ---

    def test_invalidate_all_clears_everything(self, cache, mock_cache_enabled):
        """Test that invalidate_all clears all cached entries."""
        cache.set("key1", {"data": 1}, entity=ListingType.locations)
        cache.set("key2", {"data": 2}, entity=ListingType.devices)
        cache.set("key3", {"data": 3}, entity=ListingType.racks)

        cache.invalidate_all()

        assert cache.get("key1") is None
        assert cache.get("key2") is None
        assert cache.get("key3") is None
        assert len(cache._store) == 0
        assert len(cache._entity_index) == 0

    # --- Max entries / eviction tests ---

    def test_oldest_entry_evicted_when_cache_full(self, cache):
        """Test FIFO eviction when cache reaches max entries."""
        with patch("app.helpers.listing_cache.settings") as mock_settings:
            mock_settings.LISTING_CACHE_TTL_SECONDS = 300
            mock_settings.LISTING_CACHE_MAX_ENTRIES = 3  # Small limit

            cache.set("key1", {"data": 1}, entity=ListingType.locations)
            cache.set("key2", {"data": 2}, entity=ListingType.locations)
            cache.set("key3", {"data": 3}, entity=ListingType.locations)
            
            # This should evict key1 (oldest)
            cache.set("key4", {"data": 4}, entity=ListingType.locations)

            assert cache.get("key1") is None  # Evicted
            assert cache.get("key2") is not None
            assert cache.get("key3") is not None
            assert cache.get("key4") is not None

    # --- clear_prefix tests ---

    def test_clear_prefix_removes_matching_keys(self, cache, mock_cache_enabled):
        """Test that clear_prefix removes keys starting with prefix."""
        cache.set("loc_page1", {"data": 1}, entity=ListingType.locations)
        cache.set("loc_page2", {"data": 2}, entity=ListingType.locations)
        cache.set("dev_page1", {"data": 3}, entity=ListingType.devices)

        cache.clear_prefix("loc_")

        assert cache.get("loc_page1") is None
        assert cache.get("loc_page2") is None
        assert cache.get("dev_page1") is not None

    # --- _normalize_entity tests ---

    def test_normalize_entity_with_listing_type(self, cache):
        """Test _normalize_entity with ListingType enum."""
        result = cache._normalize_entity(ListingType.locations)
        assert result == "locations"

    def test_normalize_entity_with_string(self, cache):
        """Test _normalize_entity with string."""
        result = cache._normalize_entity("devices")
        assert result == "devices"

    def test_normalize_entity_with_none(self, cache):
        """Test _normalize_entity with None."""
        result = cache._normalize_entity(None)
        assert result is None


# ============================================================
# Tests for build_listing_cache_key function
# ============================================================

class TestBuildListingCacheKey:
    """Tests for the build_listing_cache_key function."""

    def test_basic_cache_key_generation(self):
        """Test basic cache key generation."""
        key = build_listing_cache_key(
            entity=ListingType.locations,
            offset=0,
            page_size=10,
            user_id=1,
            access_level="admin",
        )

        assert isinstance(key, str)
        assert len(key) == 64  # SHA256 hex digest length

    def test_same_params_produce_same_key(self):
        """Test that identical parameters produce identical keys."""
        params = {
            "entity": ListingType.locations,
            "offset": 0,
            "page_size": 10,
            "user_id": 1,
            "access_level": "viewer",
        }

        key1 = build_listing_cache_key(**params)
        key2 = build_listing_cache_key(**params)

        assert key1 == key2

    def test_different_params_produce_different_keys(self):
        """Test that different parameters produce different keys."""
        key1 = build_listing_cache_key(
            entity=ListingType.locations,
            offset=0,
            page_size=10,
            user_id=1,
            access_level="admin",
        )
        key2 = build_listing_cache_key(
            entity=ListingType.devices,  # Different entity
            offset=0,
            page_size=10,
            user_id=1,
            access_level="admin",
        )

        assert key1 != key2

    def test_different_offset_produces_different_key(self):
        """Test that different offset produces different key."""
        key1 = build_listing_cache_key(
            entity=ListingType.locations,
            offset=0,
            page_size=10,
            user_id=None,
            access_level=None,
        )
        key2 = build_listing_cache_key(
            entity=ListingType.locations,
            offset=10,  # Different offset
            page_size=10,
            user_id=None,
            access_level=None,
        )

        assert key1 != key2

    def test_none_values_excluded_from_key(self):
        """Test that None values are excluded from cache key."""
        key1 = build_listing_cache_key(
            entity=ListingType.locations,
            offset=0,
            page_size=10,
            user_id=None,
            access_level=None,
        )
        key2 = build_listing_cache_key(
            entity=ListingType.locations,
            offset=0,
            page_size=10,
            user_id=None,
            access_level=None,
            some_filter=None,  # Extra None filter
        )

        # Keys should be the same since None values are excluded
        assert key1 == key2

    def test_empty_string_excluded_from_key(self):
        """Test that empty strings are excluded from cache key."""
        key1 = build_listing_cache_key(
            entity=ListingType.locations,
            offset=0,
            page_size=10,
            user_id=None,
            access_level=None,
        )
        key2 = build_listing_cache_key(
            entity=ListingType.locations,
            offset=0,
            page_size=10,
            user_id=None,
            access_level=None,
            location_name="",  # Empty string filter
        )

        assert key1 == key2

    def test_filters_included_in_key(self):
        """Test that filter parameters are included in cache key."""
        key1 = build_listing_cache_key(
            entity=ListingType.devices,
            offset=0,
            page_size=10,
            user_id=1,
            access_level="viewer",
            location_name="NYC",
        )
        key2 = build_listing_cache_key(
            entity=ListingType.devices,
            offset=0,
            page_size=10,
            user_id=1,
            access_level="viewer",
            location_name="LA",  # Different filter value
        )

        assert key1 != key2

    def test_date_objects_converted_to_isoformat(self):
        """Test that date objects are properly converted in cache key."""
        test_date = date(2025, 1, 15)
        
        key = build_listing_cache_key(
            entity=ListingType.devices,
            offset=0,
            page_size=10,
            user_id=None,
            access_level=None,
            warranty_start_date=test_date,
        )

        # Should not raise and should produce valid key
        assert isinstance(key, str)
        assert len(key) == 64

    def test_filter_order_does_not_affect_key(self):
        """Test that filter order doesn't affect the cache key (sorted)."""
        key1 = build_listing_cache_key(
            entity=ListingType.devices,
            offset=0,
            page_size=10,
            user_id=None,
            access_level=None,
            filter_a="value_a",
            filter_b="value_b",
        )
        key2 = build_listing_cache_key(
            entity=ListingType.devices,
            offset=0,
            page_size=10,
            user_id=None,
            access_level=None,
            filter_b="value_b",  # Different order
            filter_a="value_a",
        )

        assert key1 == key2


# ============================================================
# Tests for module-level helper functions
# ============================================================

class TestModuleFunctions:
    """Tests for module-level helper functions."""

    def test_invalidate_listing_cache_for_entity(self):
        """Test the invalidate_listing_cache_for_entity helper."""
        with patch("app.helpers.listing_cache.settings") as mock_settings:
            mock_settings.LISTING_CACHE_TTL_SECONDS = 300
            mock_settings.LISTING_CACHE_MAX_ENTRIES = 100

            # Add some entries
            listing_cache.set("test_key", {"data": 1}, entity=ListingType.locations)
            
            # Invalidate
            invalidate_listing_cache_for_entity(ListingType.locations)
            
            # Should be cleared
            assert listing_cache.get("test_key") is None

    def test_clear_all_listing_cache(self):
        """Test the clear_all_listing_cache helper."""
        with patch("app.helpers.listing_cache.settings") as mock_settings:
            mock_settings.LISTING_CACHE_TTL_SECONDS = 300
            mock_settings.LISTING_CACHE_MAX_ENTRIES = 100

            # Add some entries
            listing_cache.set("key1", {"data": 1}, entity=ListingType.locations)
            listing_cache.set("key2", {"data": 2}, entity=ListingType.devices)
            
            # Clear all
            clear_all_listing_cache()
            
            # All should be cleared
            assert listing_cache.get("key1") is None
            assert listing_cache.get("key2") is None

    def test_is_cache_enabled(self):
        """Test _is_cache_enabled logic."""
        with patch("app.helpers.listing_cache.settings") as mock_settings:
            # Case 1: Both > 0 -> Enabled
            mock_settings.LISTING_CACHE_TTL_SECONDS = 300
            mock_settings.LISTING_CACHE_MAX_ENTRIES = 100
            assert _is_cache_enabled() is True
            
            # Case 2: TTL = 0 -> Disabled
            mock_settings.LISTING_CACHE_TTL_SECONDS = 0
            mock_settings.LISTING_CACHE_MAX_ENTRIES = 100
            assert _is_cache_enabled() is False
            
            # Case 3: Max Entries = 0 -> Disabled
            mock_settings.LISTING_CACHE_TTL_SECONDS = 300
            mock_settings.LISTING_CACHE_MAX_ENTRIES = 0
            assert _is_cache_enabled() is False

    def test_clear_prefix_negative_no_match(self):
        """Test that clear_prefix does nothing if no keys match."""
        with patch("app.helpers.listing_cache.settings") as mock_settings:
             mock_settings.LISTING_CACHE_TTL_SECONDS = 300
             mock_settings.LISTING_CACHE_MAX_ENTRIES = 100
             
             # Setup: add key that doesn't match prefix
             listing_cache.set("keep_me", {"val": 1}, entity="misc")
             
             # Action: Clear unrelated prefix
             listing_cache.clear_prefix("delete_")
             
             # Assert: Key remains
             assert listing_cache.get("keep_me") is not None

