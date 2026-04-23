import os
import pytest
from unittest.mock import patch
from config.validation import validate_environment

def test_validate_environment_all_present():
    """Test when all required environment variables are present."""
    with patch.dict(os.environ, {"COINALYZE_API_KEY": "dummy_key"}, clear=True):
        is_valid, messages = validate_environment()
        assert is_valid is True
        assert len(messages) == 0

def test_validate_environment_missing_required():
    """Test when required environment variables are missing."""
    with patch.dict(os.environ, {}, clear=True):
        is_valid, messages = validate_environment()
        assert is_valid is False
        assert len(messages) == 1
        assert "Missing required environment variable: COINALYZE_API_KEY" in messages[0]

def test_validate_environment_empty_required():
    """Test when required environment variable exists but is empty."""
    with patch.dict(os.environ, {"COINALYZE_API_KEY": ""}, clear=True):
        is_valid, messages = validate_environment()
        assert is_valid is False
        assert len(messages) == 1
        assert "Missing required environment variable: COINALYZE_API_KEY" in messages[0]
