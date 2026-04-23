import os
from unittest.mock import patch
from config.validation import validate_environment

def test_validate_environment_success():
    """Test when all required variables are present."""
    with patch.dict(os.environ, {"COINALYZE_API_KEY": "dummy_key"}):
        is_valid, messages = validate_environment()
        assert is_valid is True
        assert len(messages) == 0

def test_validate_environment_missing_key():
    """Test when a required variable is missing."""
    with patch.dict(os.environ, {}, clear=True):
        is_valid, messages = validate_environment()
        assert is_valid is False
        assert len(messages) == 1
        assert "COINALYZE_API_KEY" in messages[0]
