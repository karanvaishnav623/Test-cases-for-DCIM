import os
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path
from pydantic import ValidationError
from app.core import config
from app.core.config import Settings, get_settings, load_environment, get_env_load_state

class TestLoadEnvironment:
    """Tests for load_environment function."""

    @patch("app.core.config.load_dotenv")
    @patch("app.core.config.Path.exists")
    @patch.dict(os.environ, {"APP_ENV": "dev"}, clear=True)
    def test_load_environment_dev(self, mock_exists, mock_load_dotenv):
        """Positive: Loads .env.dev for dev environment."""
        mock_exists.return_value = True
        
        # Reset globals
        config._loaded_env_file = None
        config._env_load_warning = None
        
        load_environment()
        
        mock_load_dotenv.assert_called()
        call_args = mock_load_dotenv.call_args
        # Check that it tried to load .env.dev (checking end of path string)
        assert str(call_args[0][0]).endswith(".env.dev")
        assert config._loaded_env_file is not None
        assert ".env.dev" in config._loaded_env_file

    @patch("app.core.config.load_dotenv")
    @patch("app.core.config.Path.exists")
    @patch.dict(os.environ, {"APP_ENV": "test"}, clear=True)
    def test_load_environment_test(self, mock_exists, mock_load_dotenv):
        """Positive: Loads .env.test for test environment."""
        mock_exists.return_value = True
        
        config._loaded_env_file = None
        load_environment()
        
        assert str(mock_load_dotenv.call_args[0][0]).endswith(".env.test")

    @patch("app.core.config.load_dotenv")
    @patch("app.core.config.Path.exists")
    @patch.dict(os.environ, {"APP_ENV": "prod"}, clear=True)
    def test_load_environment_missing_file(self, mock_exists, mock_load_dotenv):
        """Positive: Handles missing env file gracefully (sets warning)."""
        mock_exists.return_value = False
        
        config._loaded_env_file = None
        config._env_load_warning = None
        
        load_environment()
        
        mock_load_dotenv.assert_not_called()
        assert config._loaded_env_file is None
        assert config._env_load_warning is not None
        assert "not found" in config._env_load_warning

class TestSettings:
    """Tests for Settings class initialization and logic."""

    @patch.dict(os.environ, {}, clear=True)
    def test_settings_defaults(self):
        """Positive: Verify default settings."""
        settings = Settings()
        assert settings.ENVIRONMENT == "dev"
        assert settings.LOG_LEVEL == "DEBUG"
        assert settings.JWT_ALGORITHM == "HS256"
        assert settings.ACCESS_TOKEN_EXPIRE_SECONDS == 900

    @patch.dict(os.environ, {"APP_ENV": "prod"}, clear=True)
    def test_settings_prod_log_level(self):
        """Positive: LOG_LEVEL is INFO in prod environment."""
        settings = Settings(ENVIRONMENT="prod")
        assert settings.ENVIRONMENT == "prod"
        assert settings.LOG_LEVEL == "INFO"

    def test_settings_device_image_url_autoconfig(self):
        """Positive: Auto-configures DEVICE_IMAGE_BASE_URL in dev/uat."""
        # Default behavior: /images/ -> http://127.0.0.1:8000/images/
        settings = Settings(ENVIRONMENT="dev", DEVICE_IMAGE_BASE_URL="/images/")
        assert settings.DEVICE_IMAGE_BASE_URL == "http://127.0.0.1:8000/images/"

    def test_settings_device_image_url_no_autoconfig_if_custom(self):
        """Positive: Does not overwrite custom DEVICE_IMAGE_BASE_URL."""
        settings = Settings(ENVIRONMENT="dev", DEVICE_IMAGE_BASE_URL="http://cdn.example.com/")
        assert settings.DEVICE_IMAGE_BASE_URL == "http://cdn.example.com/"

    def test_settings_invalid_environment(self):
        """Negative: Raises ValidationError for invalid environment value."""
        with pytest.raises(ValidationError) as exc:
            Settings(ENVIRONMENT="invalid_env")
        assert "Input should be 'dev', 'uat' or 'prod'" in str(exc.value)

    def test_settings_invalid_type(self):
        """Negative: Raises ValidationError for invalid type (e.g. SMTP_PORT not int)."""
        with pytest.raises(ValidationError) as exc:
            Settings(SMTP_PORT="not_an_int")
        assert "Input should be a valid integer" in str(exc.value)


class TestGetSettingsAndProxy:
    """Tests for get_settings singleton and proxy."""

    def test_get_settings_singleton(self):
        """Positive: get_settings returns the same instance."""
        # Reset global settings
        config._settings = None
        
        s1 = get_settings()
        s2 = get_settings()
        
        assert s1 is s2
        assert isinstance(s1, Settings)

    def test_settings_proxy_access(self):
        """Positive: Proxy delegates attribute access."""
        # Reset global settings
        config._settings = None
        
        # Access through proxy
        assert config.settings.JWT_ALGORITHM == "HS256"
        
        # Verify it initialized the singleton
        assert config._settings is not None


class TestEnvLoadState:
    """Tests for get_env_load_state."""

    def test_get_env_load_state(self):
        """Positive: Returns dictionary with load state."""
        config._loaded_env_file = "/path/to/.env.test"
        config._env_load_warning = "Some warning"
        
        state = get_env_load_state()
        
        assert state["env_file"] == "/path/to/.env.test"
        assert state["warning"] == "Some warning"
