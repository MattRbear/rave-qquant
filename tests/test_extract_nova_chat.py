import pytest
from pathlib import Path
from unittest.mock import patch
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from extract_nova_chat import safe_read_text

def test_safe_read_text_success(tmp_path):
    """Test successful reading with default utf-8 encoding."""
    test_file = tmp_path / "test.txt"
    test_file.write_text("hello world", encoding="utf-8")

    result = safe_read_text(test_file)
    assert result == "hello world"

@patch('extract_nova_chat.Path.read_text')
def test_safe_read_text_fallback_encoding(mock_read_text):
    """Test that it falls back to other encodings if the first one raises an exception."""
    # Raise Exception for the first two encodings, then succeed on the third
    mock_read_text.side_effect = [
        Exception("Failed utf-8"),
        Exception("Failed utf-16"),
        "hello world fallback"
    ]

    dummy_path = Path("dummy.txt")
    result = safe_read_text(dummy_path)

    assert result == "hello world fallback"
    assert mock_read_text.call_count == 3
    # Check the encodings that were called
    mock_read_text.assert_any_call(encoding='utf-8', errors='replace')
    mock_read_text.assert_any_call(encoding='utf-16', errors='replace')
    mock_read_text.assert_any_call(encoding='latin-1', errors='replace')

@patch('extract_nova_chat.Path.read_text')
def test_safe_read_text_all_encodings_fail(mock_read_text, caplog):
    """Test when all encodings fail to read the file."""
    # Mock read_text to always raise an exception
    mock_read_text.side_effect = Exception("Mocked read error")

    dummy_path = Path("dummy.txt")
    result = safe_read_text(dummy_path)

    assert result is None
    # Verify it tried all 4 encodings ('utf-8', 'utf-16', 'latin-1', 'cp1252')
    assert mock_read_text.call_count == 4

    # Verify the warning was logged
    assert "Could not read file with any encoding" in caplog.text


from extract_nova_chat import strip_html

def test_strip_html_normal():
    """Test normal HTML stripping."""
    assert strip_html("<p>Hello <b>world</b>!</p>") == "Hello world !"

def test_strip_html_edge_case():
    """Test edge cases where unescaped angle brackets cause text to be stripped."""
    # This intentionally documents the current exact behavior mentioned in memory.
    # HTML unescape makes &lt; into < and &gt; into >
    # Then the regex <[^>]+> strips everything in between
    text = "Math: 5 &lt; 10 and 10 &gt; 5"
    # unescaped: Math: 5 < 10 and 10 > 5
    # regex matches "< 10 and 10 >" and removes it
    assert strip_html(text) == "Math: 5 5"
