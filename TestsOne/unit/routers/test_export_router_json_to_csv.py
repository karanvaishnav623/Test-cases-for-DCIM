import pytest
import json
from unittest.mock import MagicMock
from fastapi import HTTPException
from app.dcim.routers import export_router_json_to_csv
from app.dcim.routers.export_router_json_to_csv import ExportRequest

class TestExportRouterJsonToCsv:
    """Unit tests for export_router_json_to_csv module."""

    def test_flatten_dict(self):
        """Positive: Nested dicts are flattened with separator."""
        nested = {
            "a": 1,
            "b": {"c": 2},
            "d": {"e": {"f": 3}},
            "g": [1, 2] # List should be stringified
        }
        flat = export_router_json_to_csv._flatten_dict(nested)
        
        assert flat["a"] == 1
        assert flat["b_c"] == 2
        assert flat["d_e_f"] == 3
        # Lists are converted to str
        assert flat["g"] == "[1, 2]"

    def test_json_to_csv_conversion(self):
        """Positive: Converts list of dicts to CSV string."""
        data = [
            {"id": 1, "name": "A", "meta": {"type": "x"}},
            {"id": 2, "name": "B", "meta": {"type": "y"}}
        ]
        
        csv_out = export_router_json_to_csv._json_to_csv(data)
        
        lines = csv_out.strip().split('\n')
        # Header + 2 rows = 3 lines
        assert len(lines) == 3
        
        header = lines[0]
        assert "id" in header
        assert "meta_type" in header
        
        assert "1,A,x" in lines[1] or "1,x,A" in lines[1] # Order depends on dict iteration but normally insertion order in Py3.7+

    def test_json_to_csv_empty(self):
        """Positive: Empty input returns empty string."""
        assert export_router_json_to_csv._json_to_csv([]) == ""

    def test_export_dcim_entities_success(self):
        """Positive: Valid request returns CSV content with headers."""
        req = ExportRequest(
            data=[{"col1": "val1"}],
            filename="test_file"
        )
        
        response = export_router_json_to_csv.export_dcim_entities(req)
        
        assert response.media_type == "text/csv"
        # Check disposition header
        assert 'filename="test_file.csv"' in response.headers["content-disposition"]
        # Body should contain csv
        assert b"col1" in response.body
        assert b"val1" in response.body

    def test_export_dcim_entities_no_data(self):
        """Negative: Raises 400 if data is empty."""
        req = ExportRequest(data=[])
        
        with pytest.raises(HTTPException) as exc:
            export_router_json_to_csv.export_dcim_entities(req)
        assert exc.value.status_code == 400

    def test_export_dcim_entities_error(self):
        """Negative: Handling of internal errors (e.g. during CSV conversion)."""
        req = ExportRequest(data=[{"a": 1}])
        
        # Mock _json_to_csv to raise exception
        original_func = export_router_json_to_csv._json_to_csv
        try:
            export_router_json_to_csv._json_to_csv = MagicMock(side_effect=Exception("Pandas boom"))
            
            with pytest.raises(HTTPException) as exc:
                export_router_json_to_csv.export_dcim_entities(req)
            assert exc.value.status_code == 500
            assert "Pandas boom" in exc.value.detail
        finally:
            export_router_json_to_csv._json_to_csv = original_func
