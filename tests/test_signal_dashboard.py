from pathlib import Path
from unittest.mock import patch, mock_open
from Analysis.signal_dashboard import load_last_line

def test_load_last_line_file_not_found():
    # If file does not exist, return None
    with patch("pathlib.Path.exists", return_value=False):
        assert load_last_line(Path("non_existent_file.jsonl")) is None

def test_load_last_line_empty_file():
    # If file is empty, return None
    with patch("pathlib.Path.exists", return_value=True):
        m = mock_open(read_data="")
        with patch("builtins.open", m):
            assert load_last_line(Path("empty.jsonl")) is None

def test_load_last_line_success():
    # If file has lines, return the parsed last line
    data = '{"line": 1}\n{"line": 2}'
    with patch("pathlib.Path.exists", return_value=True):
        m = mock_open(read_data=data)
        with patch("builtins.open", m):
            result = load_last_line(Path("data.jsonl"))
            assert result == {"line": 2}

def test_load_last_line_exception():
    # If an exception occurs, return None
    with patch("pathlib.Path.exists", return_value=True):
        with patch("builtins.open", side_effect=PermissionError("Permission denied")):
            assert load_last_line(Path("error.jsonl")) is None
