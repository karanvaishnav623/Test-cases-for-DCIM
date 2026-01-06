# DCIM Backend Tests

This directory contains all tests for the DCIM FastAPI backend, organized by test type.

## 📁 Folder Structure

```
tests/
├── conftest.py          # Shared fixtures and configuration
├── __init__.py
├── README.md
│
├── unit/                # Unit Tests
│   ├── __init__.py
│   ├── test_auth_helper.py
│   └── test_rbac_helper.py
│
├── integration/         # Integration Tests
│   ├── __init__.py
│   ├── test_login_router.py
│   ├── test_listing_router.py
│   ├── test_details_router.py
│   ├── test_summary_router.py
│   ├── test_change_log_router.py
│   └── test_add_update_delete_routers.py
│
└── e2e/                 # End-to-End Tests
    └── __init__.py      # (Add e2e tests here)
```

## 🧪 Test Types Explained

### Unit Tests (`tests/unit/`)
- **What**: Test individual functions in isolation
- **Dependencies**: None (no DB, no HTTP, no external services)
- **Speed**: Very fast (milliseconds)
- **Example**: Testing JWT token encoding/decoding

```python
def test_build_jwt_payload_includes_roles():
    user = DummyUser(roles=[...])
    payload = auth_helper._build_jwt_payload(user)
    assert payload["roles"] == ["ADMIN"]
```

### Integration Tests (`tests/integration/`)
- **What**: Test API endpoints with mocked dependencies
- **Dependencies**: FastAPI TestClient, mocked DB
- **Speed**: Fast (seconds)
- **Example**: Testing login endpoint returns tokens

```python
def test_login_success(client):
    response = client.post("/api/dcim/login", json={...})
    assert response.status_code == 200
    assert "access_token" in response.json()
```

### End-to-End Tests (`tests/e2e/`)
- **What**: Test complete user flows with real database
- **Dependencies**: Real Oracle DB, real services
- **Speed**: Slow (seconds to minutes)
- **Example**: Full login → create device → verify in DB

```python
def test_full_device_creation_flow(real_db_client):
    # Login
    login_resp = real_db_client.post("/api/dcim/login", ...)
    token = login_resp.json()["access_token"]
    
    # Create device
    create_resp = real_db_client.post("/api/dcim/add", ...)
    
    # Verify in database
    device = db.query(Device).filter_by(name="test").first()
    assert device is not None
```

## 🚀 Running Tests

### Run All Tests
```bash
cd dcim_backend_fastapi
source venv/bin/activate
pytest tests/ -v
```

### Run by Test Type
```bash
# Unit tests only (fastest)
pytest tests/unit/ -v

# Integration tests only
pytest tests/integration/ -v

# E2E tests only (requires DB)
pytest tests/e2e/ -v
```

### Run Specific File
```bash
pytest tests/unit/test_auth_helper.py -v
```

### Run with Coverage
```bash
pytest tests/ --cov=app --cov-report=html
# Open htmlcov/index.html in browser
```

### Run by Marker
```bash
# Run only unit tests
pytest -m unit

# Skip slow tests
pytest -m "not slow"

# Run only e2e tests
pytest -m e2e
```

## 📝 Writing New Tests

### 1. Choose the Right Directory
| If testing... | Put in... |
|---------------|-----------|
| Helper function logic | `unit/` |
| API endpoint behavior | `integration/` |
| Full user workflow | `e2e/` |

### 2. Use Shared Fixtures
Import from `conftest.py`:
```python
def test_something(dummy_user, dummy_db):
    # dummy_user and dummy_db are provided by conftest.py
    pass
```

### 3. Follow Naming Convention
- Files: `test_<module_name>.py`
- Functions: `test_<what>_<expected_behavior>()`

### 4. Use Markers (Optional)
```python
import pytest

@pytest.mark.unit
def test_fast_function():
    pass

@pytest.mark.slow
def test_heavy_computation():
    pass
```

## ✅ Test Coverage Goals

| Type | Target Coverage |
|------|-----------------|
| Unit | 80%+ |
| Integration | 70%+ |
| E2E | Key flows |

## 🔧 Troubleshooting

### Tests fail with "DATABASE_URL not set"
Unit and integration tests should mock the DB. If you see this error:
1. Check if test is using `TestClient` properly
2. Ensure `dependency_overrides` is set for `get_db`

### Import errors
Make sure you're running from the `dcim_backend_fastapi` directory:
```bash
cd dcim_backend_fastapi
pytest tests/ -v
```

