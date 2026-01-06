import pytest
from unittest.mock import MagicMock, patch
from app.db.session import get_db

def test_get_db():
    # Mock SessionLocal
    mock_session = MagicMock()
    with patch("app.db.session.SessionLocal", return_value=mock_session):
        gen = get_db()
        db = next(gen)
        assert db == mock_session
        
        # Verify close is called
        try:
            next(gen)
        except StopIteration:
            pass
        mock_session.close.assert_called_once()
