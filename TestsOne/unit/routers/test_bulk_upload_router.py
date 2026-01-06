import io
import pytest
import pandas as pd
from unittest.mock import MagicMock, patch, AsyncMock
from fastapi import HTTPException, UploadFile
from sqlalchemy.exc import IntegrityError

from app.dcim.routers import bulk_upload_router
from app.helpers.listing_types import ListingType

class TestBulkUploadRouter:
    """Unit tests for bulk_upload_router module."""

    def test_normalize_column_name(self):
        """Positive: Normalizes column names."""
        assert bulk_upload_router.normalize_column_name("Host Name") == "host name"
        assert bulk_upload_router.normalize_column_name("  Rack_No  ") == "rack no"

    def test_check_row_uniqueness_for_bulk_duplicate(self):
        """Negative: Returns error message if duplicate found."""
        db = MagicMock()
        data = {"name": "Wing1", "location_name": "ABC", "building_name": "B1"}
        
        with patch("app.helpers.add_entity_helper.get_location_by_name"), \
             patch("app.helpers.add_entity_helper.get_building_by_name"):
            
            # Mock existing object found
            db.query.return_value.filter.return_value.filter.return_value.filter.return_value.first.return_value = MagicMock()
            
            error = bulk_upload_router.check_row_uniqueness_for_bulk("wing", data, db)
            assert error
            assert "already exists" in error

    def test_check_row_uniqueness_for_bulk_unique(self):
        """Positive: Returns None if no duplicate."""
        db = MagicMock()
        data = {"name": "Wing1", "location_name": "ABC", "building_name": "B1"}
        
        with patch("app.helpers.add_entity_helper.get_location_by_name"), \
             patch("app.helpers.add_entity_helper.get_building_by_name"):
            
            # Mock no existing object
            db.query.return_value.filter.return_value.filter.return_value.filter.return_value.first.return_value = None
            
            error = bulk_upload_router.check_row_uniqueness_for_bulk("wing", data, db)
            assert error is None


class TestCleanDataframeRow:
    """Tests for clean_dataframe_row helper."""

    def test_clean_row_basic_mapping(self):
        """Positive: Maps columns and strips strings."""
        # Columns must be normalized (lowercase) as they would be after _load_dataframe
        row = pd.Series({"host name": "  Server1  ", "ip address": "1.2.3.4"})
        result = bulk_upload_router.clean_dataframe_row(row)
        
        assert result["name"] == "Server1"
        assert result["ip"] == "1.2.3.4"

    def test_clean_row_conversions(self):
        """Positive: Converts ints and dates."""
        row = pd.Series({
            "rack height": "42", 
            "warranty start": "2023-01-01",
            "position": 10.0
        })
        result = bulk_upload_router.clean_dataframe_row(row)
        
        assert result["height"] == 42
        assert isinstance(result["height"], int)
        assert result["warranty_start_date"] == "2023-01-01"
        assert result["position"] == 10

    def test_clean_row_ignores_nan(self):
        """Positive: Ignores NaN/None values."""
        row = pd.Series({"host name": "S1", "model": float("nan"), "make": None})
        result = bulk_upload_router.clean_dataframe_row(row)
        
        assert "name" in result
        assert "model_name" not in result
        assert "make_name" not in result


class TestLoadDataframe:
    """Tests for _load_dataframe_from_bytes."""

    def test_load_valid_csv(self):
        """Positive: Loads valid CSV bytes."""
        csv_content = b"Host Name,IP Address\nServer1,1.1.1.1"
        df = bulk_upload_router._load_dataframe_from_bytes(csv_content)
        
        assert len(df) == 1
        # Check normalized columns
        assert "host name" in df.columns
        assert df.iloc[0]["host name"] == "Server1"

    def test_empty_csv_raises_error(self):
        """Negative: Raises ValueError for empty CSV."""
        with pytest.raises(ValueError, match="CSV file is empty"):
            bulk_upload_router._load_dataframe_from_bytes(b"")

    def test_no_data_rows_raises_error(self):
        """Negative: Raises ValueError if header only."""
        with pytest.raises(ValueError, match="CSV file must have at least one data row"):
            bulk_upload_router._load_dataframe_from_bytes(b"Header1,Header2\n")


class TestProcessRowError:
    """Tests for _process_row_error."""

    def test_integrity_error_handling(self):
        """Positive: Formats integrity error correctly."""
        db = MagicMock()
        # Mock IntegrityError with .orig attribute
        orig_exc = Exception("Duplicate entry 'Key' for key 'PRIMARY'")
        exc = IntegrityError("statement", "params", orig_exc)
        
        row_result = {"status": "pending"}
        
        aborted, pending = bulk_upload_router._process_row_error(exc, row_result, db, skip_errors=True, pending_commit=5)
        
        assert db.rollback.called
        assert pending == 0
        assert not aborted # skip_errors=True
        assert row_result["status"] == "error"
        assert "Duplicate data" in row_result["error"]

    def test_generic_exception_handling(self):
        """Positive: Handles generic exceptions."""
        db = MagicMock()
        exc = ValueError("Invalid value")
        row_result = {}
        
        # skip_errors=False -> should abort
        aborted, pending = bulk_upload_router._process_row_error(exc, row_result, db, skip_errors=False, pending_commit=1)
        
        assert aborted is True
        assert row_result["error"] == "Invalid value"


@pytest.mark.asyncio
class TestBulkUploadEndpoint:
    """Tests for bulk_upload_entities endpoint."""

    async def test_bulk_upload_success(self):
        """Positive: Successful upload with report email."""
        access_level = MagicMock()
        current_user = MagicMock(email="test@example.com")
        db = MagicMock()
        background_tasks = MagicMock()
        
        file_content = b"Host Name,IP\nServer1,1.1.1.1"
        upload_file = MagicMock(spec=UploadFile)
        upload_file.filename = "test.csv"
        upload_file.read = AsyncMock(return_value=file_content)
        
        with patch("app.dcim.routers.bulk_upload_router.ENTITY_CREATE_HANDLERS"), \
             patch("app.dcim.routers.bulk_upload_router.ENTITY_CREATE_SCHEMAS"), \
             patch("app.dcim.routers.bulk_upload_router.log_create"), \
             patch("app.dcim.routers.bulk_upload_router.send_bulk_upload_report"):
            
            # Use the enum from the router module
            response = await bulk_upload_router.bulk_upload_entities(
                background_tasks=background_tasks,
                file=upload_file,
                entity_type=bulk_upload_router.BulkUploadEntityType.devices,
                skip_errors=False,
                access_level=access_level,
                current_user=current_user
            )
            
            assert response["entity"] == "devices"
            assert "job_id" in response
            
            background_tasks.add_task.assert_called_once()
            task_name = background_tasks.add_task.call_args[0][0].__name__
            assert task_name == "_process_bulk_upload_job"

    async def test_bulk_upload_file_read_error(self):
        """Negative: Handles file read error."""
        upload_file = MagicMock(spec=UploadFile)
        upload_file.filename = "test.csv"
        # Since reading happens in the endpoint (await file.read()), we mock it to fail
        # BUT wait, file.read() is awaited in the endpoint BEFORE background task.
        # So we mock file.read to raise exception
        upload_file.read = AsyncMock(return_value=b"") # Empty read first checks empty
        
        # Test empty file check
        with pytest.raises(HTTPException) as exc:
            await bulk_upload_router.bulk_upload_entities(
                background_tasks=MagicMock(),
                file=upload_file,
                entity_type=bulk_upload_router.BulkUploadEntityType.devices,
                access_level=MagicMock(),
                current_user=MagicMock()
            )
        assert exc.value.status_code == 400
        assert "is empty" in exc.value.detail

# =============================================================================
# Migrated Coverage Tests (Helpers & Process Logic)
# =============================================================================

import pandas as pd
from unittest.mock import MagicMock, patch, ANY
from app.dcim.routers import bulk_upload_router
from app.dcim.routers.bulk_upload_router import BulkUploadEntityType
from app.helpers.listing_types import ListingType

def test_load_dataframe_simple():
    csv_bytes = b"name,status\nd1,active"
    df = bulk_upload_router._load_dataframe_from_bytes(csv_bytes)
    assert len(df) == 1
    assert "name" in df.columns
    assert df.iloc[0]["name"] == "d1"

def test_load_dataframe_encoding():
    # Test normalization
    csv_bytes = b"Device Name, Status \nd1, active"
    df = bulk_upload_router._load_dataframe_from_bytes(csv_bytes)
    assert "device name" in df.columns
    assert df.iloc[0]["device name"] == "d1"

def test_clean_dataframe_row():
    # Test type conversion and stripping
    row = pd.Series({"name": " d1 ", "position": " 42 ", "warranty start date": "2023-01-01"})
    cleaned = bulk_upload_router.clean_dataframe_row(row, apply_mapping=True)
    assert cleaned["name"] == "d1"
    assert cleaned["position"] == 42
    assert cleaned["warranty_start_date"] == "2023-01-01"

def test_clean_dataframe_row_mapping():
    # Test CSV column mapping
    # "host name" -> "name"
    row = pd.Series({"host name": "h1"})
    cleaned = bulk_upload_router.clean_dataframe_row(row, apply_mapping=True)
    assert cleaned["name"] == "h1"

def test_process_single_entity_rows_success():
    db = MagicMock()
    # Minimal valid CSV content for a device
    file_bytes = b"name,status\nd1,active"
    
    # Mock Schema
    mock_schema = MagicMock()
    # Mock validation result object
    mock_validated = MagicMock()
    mock_validated.model_dump.return_value = {"name": "d1", "status": "active"}
    mock_schema.return_value = mock_validated
    
    # Mock Handler
    mock_handler = MagicMock()
    mock_handler.return_value = {"id": 1, "name": "d1"}
    
    # Mock log_create to avoid DB/Audit issues
    with patch.dict(bulk_upload_router.ENTITY_CREATE_SCHEMAS, {ListingType.devices: mock_schema}),          patch.dict(bulk_upload_router.ENTITY_CREATE_HANDLERS, {ListingType.devices: mock_handler}),          patch("app.dcim.routers.bulk_upload_router.log_create") as mock_log:
         
         summary, results = bulk_upload_router._process_single_entity_rows(
             db, file_bytes, skip_errors=False, current_user=None, audit_context=None, entity=ListingType.devices
         )
         
         assert summary["success"] == 1
         assert summary["errors"] == 0
         assert results[0]["status"] == "success"
         assert results[0]["data"]["id"] == 1
         
         mock_handler.assert_called_once()
         db.commit.assert_called()

def test_process_single_entity_rows_validation_error():
    db = MagicMock()
    file_bytes = b"name\nd1"
    
    mock_schema = MagicMock(side_effect=ValueError("Invalid data"))
    
    with patch.dict(bulk_upload_router.ENTITY_CREATE_SCHEMAS, {ListingType.devices: mock_schema}),          patch.dict(bulk_upload_router.ENTITY_CREATE_HANDLERS, {ListingType.devices: MagicMock()}):
         
         summary, results = bulk_upload_router._process_single_entity_rows(
             db, file_bytes, skip_errors=True, current_user=None, audit_context=None, entity=ListingType.devices
         )
         
         assert summary["success"] == 0
         assert summary["errors"] == 1
         assert results[0]["status"] == "error"
         assert "Validation error" in results[0]["error"]

def test_check_row_uniqueness_for_bulk():
    db = MagicMock()
    
    with patch("app.helpers.add_entity_helper.get_location_by_name") as mock_get_loc,          patch("app.helpers.add_entity_helper.get_building_by_name") as mock_get_bld,          patch("app.helpers.add_entity_helper.get_wing_by_name") as mock_get_wing,          patch("app.helpers.add_entity_helper.get_floor_by_name") as mock_get_floor:
             
         mock_get_loc.return_value.id = 1
         mock_get_bld.return_value.id = 2
         mock_get_wing.return_value.id = 3
         mock_get_floor.return_value.id = 4
         
         # Mock Query Object
         mock_q = MagicMock()
         mock_q.filter.return_value.filter.return_value.filter.return_value.first.return_value = MagicMock()
         db.query.return_value = mock_q
         
         data = {"name": "W1", "location_name": "L1", "building_name": "B1"}
         error = bulk_upload_router.check_row_uniqueness_for_bulk("wing", data, db)
         assert error is not None
         assert "Wing with name 'W1' already exists" in error

# =============================================================================
# Migrated Orchestration Tests
# =============================================================================

def test_process_bulk_upload_job_success():
    # Mock dependencies
    mock_db = MagicMock()
    file_content = b"header1,header2\nval1,val2"
    user_id = 1
    user_email = "admin@example.com"
    job_id = "job-123"
    
    # Mock dataframes
    df_result = pd.DataFrame([{"status": "success"}])
    summary = {"success": 1, "errors": 0}
    results = [{"status": "success"}]
    
    # We need to mock SessionLocal because the function creates a new session
    with patch("app.dcim.routers.bulk_upload_router.SessionLocal", return_value=mock_db),          patch("app.dcim.routers.bulk_upload_router._process_single_entity_rows", return_value=(summary, results)),          patch("app.dcim.routers.bulk_upload_router.send_bulk_upload_report") as mock_report,          patch("app.dcim.routers.bulk_upload_router.invalidate_listing_cache_for_entity") as mock_cache,          patch("app.dcim.routers.bulk_upload_router.invalidate_location_summary_cache") as mock_summary_cache:
         
         # Mock user retrieval
         mock_db.get.return_value = MagicMock(email=user_email)

         bulk_upload_router._process_bulk_upload_job(
             job_id, file_bytes=file_content, skip_errors=False, 
             current_user_id=user_id, current_user_email=user_email,
             entity_type=BulkUploadEntityType.devices
         )
         
         # Verification
         mock_report.assert_called_once()
         call_kwargs = mock_report.call_args[1]
         assert call_kwargs["job_id"] == job_id
         assert call_kwargs["summary"] == summary

def test_process_bulk_upload_job_error():
    # Mock dependencies
    mock_db = MagicMock()
    file_content = b"header1,header2"
    user_id = 1
    user_email = "admin@example.com"
    job_id = "job-123"
    
    with patch("app.dcim.routers.bulk_upload_router.SessionLocal", return_value=mock_db),          patch("app.dcim.routers.bulk_upload_router._process_single_entity_rows", side_effect=Exception("CSV Error")),          patch("app.dcim.routers.bulk_upload_router.send_bulk_upload_report") as mock_report:
         
         # Mock user retrieval
         mock_db.get.return_value = MagicMock(email=user_email)

         bulk_upload_router._process_bulk_upload_job(
             job_id, file_bytes=file_content, skip_errors=False, 
             current_user_id=user_id, current_user_email=user_email,
             entity_type=BulkUploadEntityType.devices
         )
         
         mock_report.assert_called_once()
         call_kwargs = mock_report.call_args[1]
         assert call_kwargs["failure_reason"] == "CSV Error"
import pytest
import pandas as pd
from unittest.mock import MagicMock, patch, ANY
from app.dcim.routers import bulk_upload_router
from app.helpers.listing_types import ListingType

# =============================================================================
# Helper Function Tests (_extract_entity_data_from_row)
# =============================================================================

class TestExtractEntityData:
    
    def test_extract_wings(self):
        """Positive: Correctly extracts Wing data."""
        row_data = {
            "name": "W1", 
            "location_name": "L1", 
            "building_name": "B1",
            "description": "Desc"
        }
        raw_row = {"Wing Name": "W1", "Location": "L1"}
        config = {"name_key": "wing_name", "fallback_key": "name"}
        
        result = bulk_upload_router._extract_entity_data_from_row(
            row_data, raw_row, config, ListingType.wings
        )
        assert result["name"] == "W1"
        assert result["location_name"] == "L1"
        assert result["building_name"] == "B1"

    def test_extract_floors(self):
        """Positive: Correctly extracts Floor data."""
        row_data = {"floor_name": "F1", "wing_name": "W1"}
        raw_row = {}
        config = {"name_key": "floor_name"}
        
        result = bulk_upload_router._extract_entity_data_from_row(
            row_data, raw_row, config, ListingType.floors
        )
        assert result["name"] == "F1"
        assert result["wing_name"] == "W1"

    def test_extract_datacenters(self):
        """Positive: Correctly extracts Datacenter data."""
        row_data = {"datacenter_name": "DC1", "floor_name": "F1"}
        raw_row = {}
        config = {"name_key": "datacenter_name"}
        
        result = bulk_upload_router._extract_entity_data_from_row(
            row_data, raw_row, config, ListingType.datacenters
        )
        assert result["name"] == "DC1"
        assert result["floor_name"] == "F1"

    def test_extract_applications_with_fallback(self):
        """Positive: Correctly extracts Application data with fallback."""
        row_data = {"application_name": "App1", "asset_owner_name": "Owner1"}
        raw_row = {}
        config = {"name_key": "name", "fallback_key": "application_name"}
        
        result = bulk_upload_router._extract_entity_data_from_row(
            row_data, raw_row, config, ListingType.applications
        )
        assert result["name"] == "App1"
        assert result["asset_owner_name"] == "Owner1"

    def test_extract_model_complex_lookup(self):
        """Positive: Model extraction uses make/device type from various columns."""
        row_data = {"name": "M1", "height": 42}
        raw_row = {
            "Model Name": "M1", 
            "Manufacturer": "Dell",
            "Asset Type": "Server"
        }
        config = {"name_key": "model_name"}
        
        result = bulk_upload_router._extract_entity_data_from_row(
            row_data, raw_row, config, ListingType.models
        )
        assert result["name"] == "M1"
        assert result["make_name"] == "Dell"
        assert result["devicetype_name"] == "Server"
        assert result["height"] == 42

    def test_extract_model_fallback_data(self):
        """Positive: Model extraction falls back to row_data if raw_row missing."""
        row_data = {
            "name": "M2", 
            "make_name": "HP", 
            "devicetype_name": "Switch",
            "model_height": "2"
        }
        raw_row = {}
        config = {"name_key": "model_name"}
        
        result = bulk_upload_router._extract_entity_data_from_row(
            row_data, raw_row, config, ListingType.models
        )
        assert result["name"] == "M2"
        assert result["make_name"] == "HP"
        assert result["devicetype_name"] == "Switch"
        assert result["height"] == 2


# =============================================================================
# Helper Function Tests (_create_error_csv)
# =============================================================================

class TestCreateErrorCSV:
    
    def test_create_error_csv_basic(self):
        """Positive: Creates CSV bytes from error results."""
        results = [
            {
                "row": 2, 
                "status": "error", 
                "error": "Bad Data", 
                "original_row": {"Name": "X", "IP": "1.1"}
            },
            {
                "row": 3, 
                "status": "success"
            }
        ]
        
        csv_bytes = bulk_upload_router._create_error_csv(results, "job-1")
        assert csv_bytes is not None
        
        # Parse back to check content
        df = pd.read_csv(pd.io.common.BytesIO(csv_bytes))
        assert len(df) == 1
        assert "Error Message" in df.columns
        assert df.iloc[0]["Error Message"] == "Bad Data"
        assert df.iloc[0]["Name"] == "X"

    def test_create_error_csv_multi_entity_errors(self):
        """Positive: Combines errors for same row from multiple entities."""
        results = [
            {
                "row": 2, 
                "status": "error", 
                "error": "Wing Error", 
                "original_row": {"Name": "X"}
            },
            {
                "row": 2, 
                "status": "error", 
                "error": "Floor Error", 
                "original_row": {"Name": "X"}
            }
        ]
        
        csv_bytes = bulk_upload_router._create_error_csv(results, "job-1")
        df = pd.read_csv(pd.io.common.BytesIO(csv_bytes))
        
        assert len(df) == 1
        assert "Wing Error" in df.iloc[0]["Error Message"]
        assert "Floor Error" in df.iloc[0]["Error Message"]

    def test_create_error_csv_no_errors(self):
        """Positive: Returns None if no errors."""
        results = [{"row": 2, "status": "success"}]
        assert bulk_upload_router._create_error_csv(results, "job-1") is None


# =============================================================================
# Multi Entity Processing Tests
# =============================================================================

class TestProcessMultiEntityRows:
    
    def test_process_multi_entity_wfd_success(self):
        """Positive: Successfully processes Wings, Floors, DCs."""
        db = MagicMock()
        file_bytes = b"Wing Name,Floor Name,Datacenter Name\nW1,F1,DC1"
        
        # Mock handlers for all types
        mock_wing_handler = MagicMock(return_value={"id": 1, "name": "W1"})
        mock_floor_handler = MagicMock(return_value={"id": 2, "name": "F1"})
        mock_dc_handler = MagicMock(return_value={"id": 3, "name": "DC1"})
        
        handlers = {
            ListingType.wings: mock_wing_handler,
            ListingType.floors: mock_floor_handler,
            ListingType.datacenters: mock_dc_handler
        }
        
        # Mock schemas to pass validation
        mock_schema = MagicMock()
        mock_schema.return_value.model_dump.return_value = {}
        schemas = {
            ListingType.wings: mock_schema,
            ListingType.floors: mock_schema,
            ListingType.datacenters: mock_schema
        }
        
        with patch.dict(bulk_upload_router.ENTITY_CREATE_HANDLERS, handlers), \
             patch.dict(bulk_upload_router.ENTITY_CREATE_SCHEMAS, schemas), \
             patch("app.dcim.routers.bulk_upload_router.log_create"), \
             patch("app.dcim.routers.bulk_upload_router.check_row_uniqueness_for_bulk", return_value=None):
             
             summary, results = bulk_upload_router._process_multi_entity_rows(
                 db, file_bytes, False, None, None, "entity_wfd"
             )
             
             assert summary["success"][ListingType.wings.value] == 1
             assert summary["success"][ListingType.floors.value] == 1
             assert summary["success"][ListingType.datacenters.value] == 1
             
             # Should have called all handlers
             mock_wing_handler.assert_called()
             mock_floor_handler.assert_called()
             mock_dc_handler.assert_called()

    def test_process_multi_entity_missing_fields(self):
        """Negative: Skips if required fields missing."""
        db = MagicMock()
        # Missing Datacenter Name
        file_bytes = b"Wing Name,Floor Name\nW1,F1"
        
        # Schema for DC requires "name"
        dc_schema = MagicMock()
        field_mock = MagicMock()
        field_mock.is_required.return_value = True
        dc_schema.model_fields = {"name": field_mock}
        
        schemas = {
            ListingType.wings: MagicMock(), # Mock generic schema for others
            ListingType.floors: MagicMock(),
            ListingType.datacenters: dc_schema
        }
        
        # Handlers
        handlers = {
            ListingType.wings: MagicMock(return_value={"id": 1}),
            ListingType.floors: MagicMock(return_value={"id": 2}),
            ListingType.datacenters: MagicMock()
        }
        
        with patch.dict(bulk_upload_router.ENTITY_CREATE_HANDLERS, handlers), \
             patch.dict(bulk_upload_router.ENTITY_CREATE_SCHEMAS, schemas), \
             patch("app.dcim.routers.bulk_upload_router.log_create"):
             
             summary, results = bulk_upload_router._process_multi_entity_rows(
                 db, file_bytes, False, None, None, "entity_wfd"
             )
             
             # Wings/Floors might succeed (depends on their schemas), DC should fail/skip
             # But wait, missing_fields check happens inside loop.
             # In our mock above, generic schemas have no required fields, so W/F pass.
             # DC fails.
             
             assert summary["success"][ListingType.datacenters.value] == 0
             # Check results for skipped DC
             dc_errors = [r for r in results if r["entity_type"] == "datacenters"]
             assert len(dc_errors) == 1
             assert dc_errors[0]["status"] == "skipped"
             assert "Missing required fields" in dc_errors[0]["error"]

    def test_process_multi_entity_aborts_on_error(self):
        """Negative: aborts if processing error and skip_errors=False."""
        db = MagicMock()
        file_bytes = b"Wing Name\nW1"
        
        # Wing handler raises exception
        mock_wing_handler = MagicMock(side_effect=Exception("DB Error"))
        
        with patch.dict(bulk_upload_router.ENTITY_CREATE_HANDLERS, {ListingType.wings: mock_wing_handler}), \
             patch.dict(bulk_upload_router.ENTITY_CREATE_SCHEMAS, {ListingType.wings: MagicMock()}):
             
             summary, results = bulk_upload_router._process_multi_entity_rows(
                 db, file_bytes, False, None, None, "entity_wfd"
             )
             
             assert summary["aborted"] is True
             assert summary["errors"][ListingType.wings.value] == 1
             assert db.rollback.called
import pytest
from unittest.mock import MagicMock, patch
from fastapi import HTTPException
from app.dcim.routers.bulk_upload_router import check_row_uniqueness_for_bulk
from app.models.entity_models import Wing, Floor, Datacenter, ApplicationMapped, Rack, Model

class TestBulkUploadUniqueness:
    """Tests for check_row_uniqueness_for_bulk."""

    def test_check_wing_uniqueness_conflict(self):
        db = MagicMock()
        data = {"name": "W1", "location_name": "L1", "building_name": "B1"}
        
        # Mock lookups
        with patch("app.helpers.add_entity_helper.get_location_by_name") as mock_loc, \
             patch("app.helpers.add_entity_helper.get_building_by_name") as mock_bld:
            
            mock_loc.return_value = MagicMock(id=10)
            mock_bld.return_value = MagicMock(id=20)
            
            # Mock existing wing query
            db.query.return_value.filter.return_value.filter.return_value.filter.return_value.first.return_value = MagicMock(id=1)
            
            error = check_row_uniqueness_for_bulk("wing", data, db)
            assert error is not None
            assert "already exists" in error

    def test_check_floor_uniqueness_conflict(self):
        db = MagicMock()
        data = {"name": "F1", "location_name": "L1", "building_name": "B1", "wing_name": "W1"}
        
        with patch("app.helpers.add_entity_helper.get_location_by_name") as mock_loc, \
             patch("app.helpers.add_entity_helper.get_building_by_name") as mock_bld, \
             patch("app.helpers.add_entity_helper.get_wing_by_name_scoped") as mock_wing:
            
            mock_loc.return_value = MagicMock(id=10)
            mock_bld.return_value = MagicMock(id=20)
            mock_wing.return_value = MagicMock(id=30)
            
            db.query.return_value.filter.return_value.filter.return_value.filter.return_value.filter.return_value.first.return_value = MagicMock(id=1)
            
            error = check_row_uniqueness_for_bulk("floor", data, db)
            assert error is not None
            assert "Floor with name" in error

    def test_check_floor_missing_dependency(self):
        """Test returns None if Wing doesn't exist yet (cannot be duplicate)."""
        db = MagicMock()
        data = {"name": "F1", "location_name": "L1", "building_name": "B1", "wing_name": "W1"}
        
        with patch("app.helpers.add_entity_helper.get_location_by_name"), \
             patch("app.helpers.add_entity_helper.get_building_by_name"), \
             patch("app.helpers.add_entity_helper.get_wing_by_name_scoped") as mock_wing:
            
            mock_wing.side_effect = HTTPException(status_code=404)
            
            error = check_row_uniqueness_for_bulk("floor", data, db)
            assert error is None

    def test_check_datacenter_uniqueness_conflict(self):
        db = MagicMock()
        data = {"name": "DC1", "location_name": "L1", "building_name": "B1", "wing_name": "W1", "floor_name": "F1"}
        
        with patch("app.helpers.add_entity_helper.get_location_by_name"), \
             patch("app.helpers.add_entity_helper.get_building_by_name"), \
             patch("app.helpers.add_entity_helper.get_wing_by_name_scoped") as mock_wing, \
             patch("app.helpers.add_entity_helper.get_floor_by_name_scoped") as mock_floor:
            
            mock_wing.return_value = MagicMock(id=30)
            mock_floor.return_value = MagicMock(id=40)
            
            # Massive chain for existing check
            q = db.query.return_value
            for _ in range(6): q = q.filter.return_value
            q.first.return_value = MagicMock(id=1)
            
            error = check_row_uniqueness_for_bulk("datacenter", data, db)
            assert error is not None
            assert "Datacenter with name" in error

    def test_check_application_uniqueness(self):
        db = MagicMock()
        data = {"name": "App1", "asset_owner_name": "Owner1"}
        
        with patch("app.helpers.add_entity_helper.get_asset_owner_by_name") as mock_ao:
             mock_ao.return_value = MagicMock(id=10)
             
             db.query.return_value.filter.return_value.filter.return_value.first.return_value = MagicMock(id=1)
             
             error = check_row_uniqueness_for_bulk("application", data, db)
             assert error is not None
             assert "Application with name" in error

    def test_check_rack_uniqueness_conflict(self):
        db = MagicMock()
        data = {
            "name": "R1", "location_name": "L1", "building_name": "B1", 
            "wing_name": "W1", "floor_name": "F1", "datacenter_name": "DC1"
        }
        
        with patch("app.helpers.add_entity_helper.get_location_by_name"), \
             patch("app.helpers.add_entity_helper.get_building_by_name"), \
             patch("app.helpers.add_entity_helper.get_wing_by_name_scoped") as mock_wing, \
             patch("app.helpers.add_entity_helper.get_floor_by_name_scoped") as mock_floor, \
             patch("app.helpers.add_entity_helper.get_datacenter_by_name_scoped") as mock_dc:
             
             mock_wing.return_value = MagicMock(id=30)
             mock_floor.return_value = MagicMock(id=40)
             mock_dc.return_value = MagicMock(id=50)
             
             q = db.query.return_value
             for _ in range(7): q = q.filter.return_value
             q.first.return_value = MagicMock(id=1)
             
             error = check_row_uniqueness_for_bulk("rack", data, db)
             assert error is not None
             assert "Rack with name" in error

    def test_check_model_uniqueness_conflict(self):
        db = MagicMock()
        data = {"name": "M1", "make_name": "Make1", "devicetype_name": "DT1"}
        
        with patch("app.helpers.add_entity_helper.get_or_create_make") as mock_make, \
             patch("app.helpers.add_entity_helper.get_or_create_device_type") as mock_dt:
             
             mock_make.return_value = MagicMock(id=10)
             mock_dt.return_value = MagicMock(id=20)
             
             db.query.return_value.filter.return_value.filter.return_value.filter.return_value.first.return_value = MagicMock(id=1)
             
             error = check_row_uniqueness_for_bulk("model", data, db)
             assert error is not None
             assert "Model with name" in error
