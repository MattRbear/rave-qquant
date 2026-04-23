import pytest
from unittest.mock import patch, mock_open
from pathlib import Path
import json

from Analysis.signal_dashboard import load_last_line

def test_load_last_line_not_exists():
    """Test when the file does not exist."""
    filepath = Path("nonexistent.jsonl")
    with patch.object(Path, 'exists', return_value=False):
        result = load_last_line(filepath)
        assert result is None

def test_load_last_line_success():
    """Test successful loading of the last line."""
    filepath = Path("dummy.jsonl")
    file_content = '{"key1": "value1"}\n{"key2": "value2"}\n'

    with patch.object(Path, 'exists', return_value=True):
        with patch('builtins.open', mock_open(read_data=file_content)):
            result = load_last_line(filepath)
            assert result == {"key2": "value2"}

def test_load_last_line_empty_file():
    """Test loading from an empty file."""
    filepath = Path("dummy.jsonl")

    with patch.object(Path, 'exists', return_value=True):
        with patch('builtins.open', mock_open(read_data="")):
            result = load_last_line(filepath)
            assert result is None

def test_load_last_line_invalid_json():
    """Test loading when the last line is invalid JSON."""
    filepath = Path("dummy.jsonl")
    file_content = '{"key1": "value1"}\ninvalid json\n'

    with patch.object(Path, 'exists', return_value=True):
        with patch('builtins.open', mock_open(read_data=file_content)):
            result = load_last_line(filepath)
            assert result is None

def test_load_last_line_generic_exception():
    """Test that load_last_line handles generic exceptions during file read."""
    filepath = Path("dummy.jsonl")

    with patch.object(Path, 'exists', return_value=True):
        with patch('builtins.open', side_effect=Exception("Simulated read error")):
            result = load_last_line(filepath)
            assert result is None
