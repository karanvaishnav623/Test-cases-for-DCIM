"""
=============================================================================
UNIT TESTS - location_scope.py
=============================================================================
"""
import pytest
from unittest.mock import MagicMock
from fastapi import HTTPException
from app.helpers.location_scope import get_allowed_location_ids
from app.helpers.rbac_helper import AccessLevel


# =============================================================================
# TEST CLASS: get_allowed_location_ids
# =============================================================================
class TestGetAllowedLocationIds:
    """Tests for the get_allowed_location_ids function"""

    def test_admin_access_returns_none(self):
        """
        GIVEN: AccessLevel.admin
        WHEN: get_allowed_location_ids is called
        THEN: Returns None (indicating full access)
        NOTE: current_user can be None for admins as per logic
        """
        result = get_allowed_location_ids(current_user=None, access_level=AccessLevel.admin)
        assert result is None

    def test_standard_user_with_locations(self):
        """
        GIVEN: AccessLevel.viewer/editor and a user with locations
        WHEN: get_allowed_location_ids is called
        THEN: Returns set of location IDs
        """
        mock_access1 = MagicMock()
        mock_access1.location_id = 101
        
        mock_access2 = MagicMock()
        mock_access2.location_id = 202

        mock_user = MagicMock()
        mock_user.location_accesses = [mock_access1, mock_access2]

        result = get_allowed_location_ids(current_user=mock_user, access_level=AccessLevel.viewer)
        
        assert isinstance(result, set)
        assert result == {101, 202}

    def test_missing_user_raises_401(self):
        """
        GIVEN: Non-admin access level but current_user is None
        WHEN: get_allowed_location_ids is called
        THEN: Raises 401 Unauthorized
        """
        with pytest.raises(HTTPException) as exc:
            get_allowed_location_ids(current_user=None, access_level=AccessLevel.viewer)
        
        assert exc.value.status_code == 401
        assert "Unable to determine current user" in exc.value.detail

    def test_user_with_no_locations_raises_403(self):
        """
        GIVEN: User logic returns empty list of accesses
        WHEN: get_allowed_location_ids is called
        THEN: Raises 403 Forbidden
        """
        mock_user = MagicMock()
        mock_user.location_accesses = []

        with pytest.raises(HTTPException) as exc:
            get_allowed_location_ids(current_user=mock_user, access_level=AccessLevel.editor)
        
        assert exc.value.status_code == 403
        assert "No locations are assigned" in exc.value.detail

    def test_user_missing_attribute_handled_gracefully(self):
        """
        GIVEN: User object doesn't even have 'location_accesses' attribute
        WHEN: get_allowed_location_ids is called
        THEN: Treated as empty -> Raises 403
        """
        mock_user = MagicMock()
        del mock_user.location_accesses  # Ensure it doesn't exist

        with pytest.raises(HTTPException) as exc:
            get_allowed_location_ids(current_user=mock_user, access_level=AccessLevel.viewer)
        
        assert exc.value.status_code == 403

    def test_none_location_ids_are_filtered(self):
        """
        GIVEN: location_accesses has an entry with location_id=None
        WHEN: get_allowed_location_ids is called
        THEN: That entry is ignored
        """
        mock_access_valid = MagicMock()
        mock_access_valid.location_id = 101
        
        mock_access_none = MagicMock()
        mock_access_none.location_id = None  # Invalid

        mock_user = MagicMock()
        mock_user.location_accesses = [mock_access_valid, mock_access_none]

        result = get_allowed_location_ids(current_user=mock_user, access_level=AccessLevel.viewer)
        
        assert result == {101}

    def test_all_none_location_ids_raises_403(self):
        """
        GIVEN: location_accesses ONLY has entries with location_id=None
        WHEN: get_allowed_location_ids is called
        THEN: Resulting set is empty -> Raises 403
        """
        mock_access_none = MagicMock()
        mock_access_none.location_id = None

        mock_user = MagicMock()
        mock_user.location_accesses = [mock_access_none]

        with pytest.raises(HTTPException) as exc:
            get_allowed_location_ids(current_user=mock_user, access_level=AccessLevel.viewer)
        
        assert exc.value.status_code == 403
