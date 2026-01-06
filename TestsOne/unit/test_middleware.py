import pytest
import jwt
from unittest.mock import MagicMock, patch, AsyncMock
from fastapi import Request, Response
from app.core.middleware import LoggingMiddleware
from app.core import middleware

@pytest.fixture
def mock_request():
    request = MagicMock(spec=Request)
    request.url.path = "/api/test"
    request.method = "POST"
    request.headers = {"content-type": "application/json", "authorization": "Bearer token"}
    request.client.host = "127.0.0.1"
    request.query_params = {}
    request.body = AsyncMock(return_value=b'{"key": "value"}')
    request.state = MagicMock()
    return request

@pytest.fixture
def mw():
    app = MagicMock()
    return LoggingMiddleware(app)

class TestLoggingMiddleware:
    
    @pytest.mark.asyncio
    async def test_dispatch_excluded_path_health(self, mw, mock_request):
        """Positive: Skips logging for excluded /health path."""
        mock_request.url.path = "/health"
        call_next = AsyncMock(return_value=Response(status_code=200))
        
        with patch("app.core.middleware.app_logger") as mock_logger:
            response = await mw.dispatch(mock_request, call_next)
            
            # Should NOT log request or response
            # Implementation check: app_logger.debug/info not called
            assert not mock_logger.info.called
            assert not mock_logger.debug.called
            
            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_dispatch_excluded_path_static(self, mw, mock_request):
        """Positive: Skips logging for static paths."""
        mock_request.url.path = "/static/css/style.css"
        call_next = AsyncMock(return_value=Response(status_code=200))
        
        with patch("app.core.middleware.app_logger") as mock_logger:
            await mw.dispatch(mock_request, call_next)
            assert not mock_logger.info.called

    @pytest.mark.asyncio
    async def test_dispatch_logging_success(self, mw, mock_request):
        """Positive: Logs request and response for normal paths."""
        mock_request.url.path = "/api/users"
        call_next = AsyncMock(return_value=Response(status_code=201))
        
        with patch("app.core.middleware.app_logger") as mock_logger, \
             patch("app.core.middleware.settings") as mock_settings:
            
            mock_settings.ENVIRONMENT = "prod"
            await mw.dispatch(mock_request, call_next)
            
            # Verify logging calls
            # 1. log_request -> API Request
            # 2. log_response -> API Response
            assert mock_logger.info.call_count >= 2 
            
            # Check for "API Request" in calls
            calls = [c[0][0] for c in mock_logger.info.call_args_list]
            assert "API Request" in calls
            assert "API Response" in calls

    def test_sanitize_headers(self, mw):
        """Positive: Redacts sensitive headers."""
        headers = {
            "content-type": "application/json",
            "authorization": "Bearer secret",
            "cookie": "session=123",
            "x-api-key": "secret-key",
            "x-auth-token": "token"
        }
        sanitized = mw._sanitize_headers(headers)
        
        assert sanitized["content-type"] == "application/json"
        assert sanitized["authorization"] == "<redacted>"
        assert sanitized["cookie"] == "<redacted>"
        assert sanitized["x-api-key"] == "<redacted>"
        assert sanitized["x-auth-token"] == "<redacted>"

    def test_extract_user_from_jwt_valid(self, mw, mock_request):
        """Positive: Extracts user info from valid JWT."""
        mock_request.headers = {"authorization": "Bearer valid_token"}
        
        payload = {"sub": "123", "username": "testuser", "roles": ["admin"]}
        
        with patch("jwt.decode", return_value=payload):
            user_ctx = mw._extract_user_from_jwt(mock_request)
            
            assert user_ctx["user_id"] == "123"
            assert user_ctx["username"] == "testuser"
            assert user_ctx["roles"] == ["admin"]

    def test_extract_user_from_jwt_expired(self, mw, mock_request):
        """Negative: Returns error for expired token."""
        mock_request.headers = {"authorization": "Bearer expired_token"}
        
        with patch("jwt.decode", side_effect=jwt.ExpiredSignatureError):
            user_ctx = mw._extract_user_from_jwt(mock_request)
            assert user_ctx == {"error": "expired"}

    def test_extract_user_from_jwt_invalid(self, mw, mock_request):
        """Negative: Returns error for invalid token."""
        mock_request.headers = {"authorization": "Bearer bad_token"}
        
        with patch("jwt.decode", side_effect=jwt.InvalidTokenError):
            user_ctx = mw._extract_user_from_jwt(mock_request)
            assert user_ctx == {"error": "invalid"}

    def test_extract_user_from_jwt_no_header(self, mw, mock_request):
        """Negative: Returns None if no header."""
        mock_request.headers = {}
        assert mw._extract_user_from_jwt(mock_request) is None

    @pytest.mark.asyncio
    async def test_extract_body_success(self, mw, mock_request):
        """Positive: Extracts body text."""
        body_text = await mw._extract_body(mock_request)
        assert body_text == '{"key": "value"}'

    @pytest.mark.asyncio
    async def test_extract_body_too_large(self, mw, mock_request):
        """Negative: Truncates large body."""
        # Mock body > 10KB
        large_body = b"x" * (mw.MAX_BODY_LOG_BYTES + 1)
        mock_request.body = AsyncMock(return_value=large_body)
        
        body_text = await mw._extract_body(mock_request)
        assert "body too large" in body_text

    def test_should_log_body(self, mw, mock_request):
        """Positive: True for POST/PUT with JSON."""
        mock_request.method = "POST"
        mock_request.headers = {"content-type": "application/json"}
        assert mw._should_log_body(mock_request) is True

    def test_should_log_body_get(self, mw, mock_request):
        """Negative: False for GET."""
        mock_request.method = "GET"
        assert mw._should_log_body(mock_request) is False

    def test_should_log_body_multipart(self, mw, mock_request):
        """Negative: False for multipart."""
        mock_request.method = "POST"
        mock_request.headers = {"content-type": "multipart/form-data"}
        assert mw._should_log_body(mock_request) is False

    @pytest.mark.asyncio
    async def test_dispatch_exception_handling(self, mw, mock_request):
        """Negative: Logs exception and re-raises."""
        mock_request.url.path = "/api/error"
        call_next = AsyncMock(side_effect=ValueError("Boom"))
        
        with patch("app.core.middleware.app_logger") as mock_logger:
            with pytest.raises(ValueError):
                await mw.dispatch(mock_request, call_next)
            
            mock_logger.exception.assert_called_once()
            assert "Request failed" in mock_logger.exception.call_args[0][0]
