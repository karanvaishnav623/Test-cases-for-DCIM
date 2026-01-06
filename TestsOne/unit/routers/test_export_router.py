import pytest
from unittest.mock import MagicMock, patch, call
from app.dcim.routers import export_router
from app.helpers.listing_types import ListingType

class TestExportRouter:
    """Unit tests for export_router module."""

    def test_normalize_empty_to_none(self):
        """Positive: Normalizes empty strings to None."""
        assert export_router._normalize_empty_to_none("") is None
        assert export_router._normalize_empty_to_none("   ") is None
        assert export_router._normalize_empty_to_none("val") == "val"
        assert export_router._normalize_empty_to_none(None) is None

    def test_parse_optional_int(self):
        """Positive: Parses int strings or returns None."""
        assert export_router._parse_optional_int("123") == 123
        assert export_router._parse_optional_int("") is None
        assert export_router._parse_optional_int("abc") is None

    def test_export_stream_generates_csv(self):
        """Positive: Generates CSV chunks from handler data (using real pandas)."""
        entity = ListingType.devices
        handler_mock = MagicMock()
        
        # Mock handler returning one page of data then empty (end of stream)
        records = [{"id": 1, "name": "Dev1"}, {"id": 2, "name": "Dev2"}]
        handler_mock.side_effect = [
            (2, records), # First call
            (2, [])       # Second call (empty)
        ]
        
        # We don't patch _get_pandas, so it uses real pandas
        generator = export_router._export_stream(entity, handler_mock, {})
        
        chunk = next(generator)
        # Verify content exists in CSV format
        assert "id,name" in chunk
        assert "1,Dev1" in chunk
        assert "2,Dev2" in chunk
        
        # Should be end of stream
        with pytest.raises(StopIteration):
            next(generator)

    def test_resolve_headers_dynamic(self):
        """Positive: dynamic headers are resolved correctly."""
        entity = ListingType.devices # No pre-configured headers
        row = {"name": "D1", "id": 1, "extra": "val"}
        
        headers = export_router._resolve_headers(entity, row)
        assert "extra" in headers
        assert "name" in headers

    def test_prepare_export_row_device_types(self):
        """Positive: Flattens device type structure."""
        entity = ListingType.device_types
        record = {
            "id": 1, 
            "name": "DT1", 
            "model": {"id": 10, "name": "M1", "height": 2},
            "models_count": 5
        }
        
        row = export_router._prepare_export_row(entity, record)
        assert row["model_name"] == "M1"
        assert row["model_height"] == 2
        assert row["model_height"] == 2

    def test_parse_optional_date(self):
        """Positive/Negative: Parses date strings or returns None."""
        from datetime import date
        assert export_router._parse_optional_date("2023-10-27") == date(2023, 10, 27)
        assert export_router._parse_optional_date("") is None
        assert export_router._parse_optional_date("invalid-date") is None
        assert export_router._parse_optional_date(None) is None
        # Existing date object should be returned as is
        d = date(2023, 1, 1)
        assert export_router._parse_optional_date(d) == d

    def test_get_listing_handler(self):
        """Positive: Returns handler for valid entity."""
        # We need to mock ENTITY_LIST_HANDLERS within the function's scope logic
        # But since it does a local import, we can try patching where it imports from.
        # However, testing that it returns *something* for a known type is good enough.
        # Let's mock the dict in the module if possible, or just check return value.
        
        # Real import check
        handler = export_router._get_listing_handler(ListingType.devices)
        assert handler is not None
        
        handler = export_router._get_listing_handler(ListingType.locations)
        assert handler is not None

    def test_prepare_export_row_models(self):
        """Positive: Flattens model structure."""
        entity = ListingType.models
        record = {
            "id": 10,
            "name": "M1",
            "description": "Desc",
            "make_name": "Dell",
            "device_type": {"id": 5, "name": "Server", "height": 2},
            "height": 2
        }
        row = export_router._prepare_export_row(entity, record)
        assert row["device_type_name"] == "Server"
        assert row["device_type_height"] == 2
        assert row["make_name"] == "Dell"

    def test_resolve_headers_configured(self):
        """Positive: Uses configured headers for specific entities."""
        entity = ListingType.models
        # Models has configured headers in ENTITY_EXPORT_HEADERS
        row = {"id": 1, "name": "M1", "extra": "val"}
        headers = export_router._resolve_headers(entity, row)
        # Should start with configured headers
        expected_start = export_router.ENTITY_EXPORT_HEADERS[ListingType.models]
        assert headers[:len(expected_start)] == expected_start
        # dynamic keys appended
        assert "extra" in headers

    def test_export_stream_empty(self):
        """Positive: Generates header-only CSV when no records found."""
        entity = ListingType.models
        handler_mock = MagicMock()
        handler_mock.return_value = (0, [])
        
        generator = export_router._export_stream(entity, handler_mock, {})
        
        # Should yield headers only
        chunk = next(generator)
        assert "id,name,description" in chunk
        
        with pytest.raises(StopIteration):
            next(generator)

    def test_export_endpoint_success(self):
        """Positive: Endpoint returns StreamingResponse."""
        with patch("app.dcim.routers.export_router._get_listing_handler") as mock_get_handler, \
             patch("app.dcim.routers.export_router._export_stream") as mock_stream, \
             patch("app.dcim.routers.export_router.get_allowed_location_ids") as mock_get_locs:
            
            mock_handler = MagicMock()
            mock_get_handler.return_value = mock_handler
            mock_stream.return_value = iter(["csv_data"])
            mock_get_locs.return_value = {1, 2} # Mock allowed locations
            
            # AccessLevel, db, user mocks
            mock_db = MagicMock()
            mock_user = MagicMock()
            mock_access = 5 # AccessLevel.admin (int)
            
            # calling the endpoint function directly
            response = export_router.export_dcim_entities(
                entity=ListingType.devices,
                access_level=mock_access,
                db=mock_db,
                current_user=mock_user,
                # Explicitly pass None for all Query params to avoid default value being a Query object
                location_name=None, location_description=None,
                building_name=None, building_status=None, building_description=None,
                wing_name=None, floor_name=None,
                rack_name=None, rack_status=None, rack_height=None, rack_description=None,
                device_name="test-device", # This one we want to test
                device_status=None, device_position=None, device_face=None, device_description=None,
                serial_number=None, ip_address=None, po_number=None, asset_user=None, asset_owner=None,
                applications_mapped_name=None,
                warranty_start_date=None, warranty_end_date=None,
                amc_start_date=None, amc_end_date=None,
                device_type=None, device_type_description=None,
                make_name=None, make_description=None,
                model_name=None, model_description=None, model_height=None,
                datacenter_name=None, datacenter_description=None
            )
            
            assert isinstance(response, export_router.StreamingResponse)
            # Verify stream called with correct args
            mock_stream.assert_called_once()
            args, _ = mock_stream.call_args
            assert args[0] == ListingType.devices
            assert args[1] == mock_handler
            # Check kwargs in args[2] include mocked db and filter
            assert args[2]["db"] == mock_db
            assert args[2]["allowed_location_ids"] == {1, 2} # Verified mocked value passed
            assert args[2]["device_name"] == "test-device"

    def test_export_endpoint_unsupported_entity(self):
        """Negative: Raises 400 for entity with no handler."""
        with patch("app.dcim.routers.export_router._get_listing_handler") as mock_get_handler:
            mock_get_handler.return_value = None
            
            try:
                export_router.export_dcim_entities(
                    entity=ListingType.devices, # Even if valid type, if handler returns None
                    db=MagicMock(),
                    current_user=MagicMock(),
                    access_level=5
                )
                assert False, "Should raise HTTPException"
            except export_router.HTTPException as e:
                assert e.status_code == 400
                assert "not supported" in e.detail
