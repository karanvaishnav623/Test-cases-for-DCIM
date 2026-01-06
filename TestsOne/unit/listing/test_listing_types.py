# tests/unit/test_listing_types.py
"""
Unit tests for listing_types.py

Tests the ListingType enum:
- All expected values exist
- String inheritance works correctly
- Enum behavior (iteration, comparison, etc.)
"""

import pytest

from app.helpers.listing_types import ListingType


class TestListingTypeEnum:
    """Unit tests for the ListingType enum."""

    # --- Existence tests ---

    def test_racks_exists(self):
        """Test racks enum value exists."""
        assert ListingType.racks.value == "racks"

    def test_devices_exists(self):
        """Test devices enum value exists."""
        assert ListingType.devices.value == "devices"

    def test_device_types_exists(self):
        """Test device_types enum value exists."""
        assert ListingType.device_types.value == "device_types"

    def test_locations_exists(self):
        """Test locations enum value exists."""
        assert ListingType.locations.value == "locations"

    def test_buildings_exists(self):
        """Test buildings enum value exists."""
        assert ListingType.buildings.value == "buildings"

    def test_wings_exists(self):
        """Test wings enum value exists."""
        assert ListingType.wings.value == "wings"

    def test_floors_exists(self):
        """Test floors enum value exists."""
        assert ListingType.floors.value == "floors"

    def test_datacenters_exists(self):
        """Test datacenters enum value exists."""
        assert ListingType.datacenters.value == "datacenters"

    def test_asset_owner_exists(self):
        """Test asset_owner enum value exists."""
        assert ListingType.asset_owner.value == "asset_owner"

    def test_makes_exists(self):
        """Test makes enum value exists."""
        assert ListingType.makes.value == "makes"

    def test_models_exists(self):
        """Test models enum value exists."""
        assert ListingType.models.value == "models"

    def test_applications_exists(self):
        """Test applications enum value exists."""
        assert ListingType.applications.value == "applications"

    # --- Count test ---

    def test_enum_has_expected_count(self):
        """Test enum has exactly 12 values."""
        assert len(ListingType) == 12

    # --- String inheritance tests ---

    def test_is_string_subclass(self):
        """Test ListingType inherits from str."""
        assert issubclass(ListingType, str)

    def test_enum_value_is_string(self):
        """Test enum values are strings."""
        for listing_type in ListingType:
            assert isinstance(listing_type.value, str)

    def test_enum_can_be_used_as_string(self):
        """Test enum can be used directly as string."""
        # Because ListingType inherits from str, the enum itself acts as a string
        assert ListingType.devices == "devices"
        assert ListingType.racks == "racks"

    def test_string_comparison(self):
        """Test enum can be compared to strings."""
        assert ListingType.locations == "locations"
        assert ListingType.buildings != "locations"

    def test_string_concatenation(self):
        """Test enum can be concatenated with strings."""
        result = "entity_" + ListingType.devices
        assert result == "entity_devices"

    def test_string_formatting(self):
        """Test enum works in string formatting with .value."""
        result = f"Listing {ListingType.racks.value}"
        assert result == "Listing racks"
        
        # Direct f-string uses enum repr
        result_direct = f"Listing {ListingType.racks}"
        assert "racks" in result_direct

    # --- Enum behavior tests ---

    def test_enum_iteration(self):
        """Test enum can be iterated."""
        values = [lt.value for lt in ListingType]
        assert "racks" in values
        assert "devices" in values
        assert "locations" in values

    def test_enum_membership(self):
        """Test membership check works."""
        assert ListingType.racks in ListingType
        assert ListingType.devices in ListingType

    def test_enum_lookup_by_value(self):
        """Test enum can be looked up by value."""
        assert ListingType("racks") == ListingType.racks
        assert ListingType("devices") == ListingType.devices

    def test_enum_lookup_by_name(self):
        """Test enum can be looked up by name."""
        assert ListingType["racks"] == ListingType.racks
        assert ListingType["devices"] == ListingType.devices

    def test_invalid_value_raises_error(self):
        """Test invalid value raises ValueError."""
        with pytest.raises(ValueError):
            ListingType("invalid_type")

    def test_invalid_name_raises_error(self):
        """Test invalid name raises KeyError."""
        with pytest.raises(KeyError):
            ListingType["invalid_name"]

    # --- Name and value consistency ---

    def test_name_equals_value(self):
        """Test that enum name equals its value for all members."""
        for listing_type in ListingType:
            assert listing_type.name == listing_type.value

    # --- All expected values test ---

    def test_all_expected_values_present(self):
        """Test all expected entity types are present."""
        expected_values = {
            "racks",
            "devices",
            "device_types",
            "locations",
            "buildings",
            "wings",
            "floors",
            "datacenters",
            "asset_owner",
            "makes",
            "models",
            "applications",
        }
        actual_values = {lt.value for lt in ListingType}
        assert actual_values == expected_values

    # --- Uniqueness test ---

    def test_all_values_unique(self):
        """Test all enum values are unique."""
        values = [lt.value for lt in ListingType]
        assert len(values) == len(set(values))

    def test_all_names_unique(self):
        """Test all enum names are unique."""
        names = [lt.name for lt in ListingType]
        assert len(names) == len(set(names))

