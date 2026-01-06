import time
from unittest.mock import patch, MagicMock
import pytest
from app.helpers.summary_cache import (
    _SummaryCache,
    get_cached_location_summary,
    set_cached_location_summary,
    invalidate_location_summary_cache,
)


class TestSummaryCache:
    """Unit tests for _SummaryCache class."""

    def test_get_returns_none_when_cache_empty(self):
        """Negative: Cache miss when no data is set."""
        cache = _SummaryCache()
        result = cache.get()
        assert result is None

    def test_get_returns_cached_data_when_valid(self):
        """Positive: Cache hit when data exists and not expired."""
        cache = _SummaryCache()
        test_payload = {"total_locations": 2, "results": [{"id": 1, "name": "Loc1"}]}
        
        with patch("app.helpers.summary_cache.settings") as mock_settings:
            mock_settings.SUMMARY_CACHE_TTL_SECONDS = 60
            cache.set(test_payload)
            result = cache.get()
            
            assert result is not None
            assert result["total_locations"] == 2
            assert result["results"][0]["id"] == 1
            # Verify deepcopy - modifying result shouldn't affect original
            result["total_locations"] = 999
            assert cache._payload["total_locations"] == 2

    def test_get_returns_none_when_expired(self):
        """Negative: Cache miss when TTL has expired."""
        cache = _SummaryCache()
        test_payload = {"total_locations": 1, "results": []}
        
        with patch("app.helpers.summary_cache.settings") as mock_settings:
            mock_settings.SUMMARY_CACHE_TTL_SECONDS = 1
            cache.set(test_payload)
            
            # Wait for expiration
            time.sleep(1.1)
            
            result = cache.get()
            assert result is None

    def test_get_returns_none_when_ttl_disabled(self):
        """Negative: Cache disabled when TTL is 0 or negative."""
        cache = _SummaryCache()
        test_payload = {"total_locations": 1, "results": []}
        
        with patch("app.helpers.summary_cache.settings") as mock_settings:
            mock_settings.SUMMARY_CACHE_TTL_SECONDS = 0
            cache.set(test_payload)
            result = cache.get()
            assert result is None

    def test_set_stores_data_when_ttl_enabled(self):
        """Positive: Set cache when TTL is positive."""
        cache = _SummaryCache()
        test_payload = {"total_locations": 3, "results": [{"id": 1}]}
        
        with patch("app.helpers.summary_cache.settings") as mock_settings:
            mock_settings.SUMMARY_CACHE_TTL_SECONDS = 30
            cache.set(test_payload)
            
            assert cache._payload is not None
            assert cache._payload["total_locations"] == 3
            assert cache._expires_at > time.time()

    def test_set_does_nothing_when_ttl_disabled(self):
        """Negative: Set does nothing when TTL is 0 or negative."""
        cache = _SummaryCache()
        test_payload = {"total_locations": 1, "results": []}
        
        with patch("app.helpers.summary_cache.settings") as mock_settings:
            mock_settings.SUMMARY_CACHE_TTL_SECONDS = 0
            cache.set(test_payload)
            
            assert cache._payload is None
            assert cache._expires_at == 0.0

    def test_set_deepcopies_payload(self):
        """Positive: Set creates deep copy, original can be modified safely."""
        cache = _SummaryCache()
        original_payload = {"total_locations": 1, "results": [{"id": 1}]}
        
        with patch("app.helpers.summary_cache.settings") as mock_settings:
            mock_settings.SUMMARY_CACHE_TTL_SECONDS = 60
            cache.set(original_payload)
            
            # Modify original
            original_payload["total_locations"] = 999
            original_payload["results"][0]["id"] = 999
            
            # Cached version should be unchanged
            assert cache._payload["total_locations"] == 1
            assert cache._payload["results"][0]["id"] == 1

    def test_clear_removes_cached_data(self):
        """Positive: Clear removes all cached data."""
        cache = _SummaryCache()
        test_payload = {"total_locations": 1, "results": []}
        
        with patch("app.helpers.summary_cache.settings") as mock_settings:
            mock_settings.SUMMARY_CACHE_TTL_SECONDS = 60
            cache.set(test_payload)
            assert cache._payload is not None
            
            cache.clear()
            assert cache._payload is None
            assert cache._expires_at == 0.0


class TestSummaryCacheWrappers:
    """Unit tests for public wrapper functions."""

    def test_get_cached_location_summary_returns_cached_data(self):
        """Positive: Wrapper returns cached data when available."""
        test_payload = {"total_locations": 2, "results": [{"id": 1}]}
        
        with patch("app.helpers.summary_cache.settings") as mock_settings:
            mock_settings.SUMMARY_CACHE_TTL_SECONDS = 60
            set_cached_location_summary(test_payload)
            result = get_cached_location_summary()
            
            assert result is not None
            assert result["total_locations"] == 2

    def test_get_cached_location_summary_returns_none_when_empty(self):
        """Negative: Wrapper returns None when cache is empty."""
        invalidate_location_summary_cache()
        result = get_cached_location_summary()
        assert result is None

    def test_set_cached_location_summary_stores_data(self):
        """Positive: Wrapper stores data in cache."""
        test_payload = {"total_locations": 1, "results": []}
        
        with patch("app.helpers.summary_cache.settings") as mock_settings:
            mock_settings.SUMMARY_CACHE_TTL_SECONDS = 60
            set_cached_location_summary(test_payload)
            result = get_cached_location_summary()
            
            assert result is not None
            assert result["total_locations"] == 1

    def test_invalidate_location_summary_cache_clears_data(self):
        """Positive: Invalidate clears the cache."""
        test_payload = {"total_locations": 1, "results": []}
        
        with patch("app.helpers.summary_cache.settings") as mock_settings:
            mock_settings.SUMMARY_CACHE_TTL_SECONDS = 60
            set_cached_location_summary(test_payload)
            assert get_cached_location_summary() is not None
            
            invalidate_location_summary_cache()
            assert get_cached_location_summary() is None

