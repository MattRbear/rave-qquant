import pytest
from pathlib import Path
from unittest.mock import patch
from extract_nova_chat import safe_read_text

def test_safe_read_text_error_path():
    """Test safe_read_text when all encodings raise an Exception."""
    with patch.object(Path, 'read_text', side_effect=Exception("Mocked read error")):
        filepath = Path("dummy.txt")
        result = safe_read_text(filepath)
        assert result is None

def test_safe_read_text_success(tmp_path):
    """Test safe_read_text successfully reading a file."""
    test_file = tmp_path / "test.txt"
    test_file.write_text("Hello, World!", encoding='utf-8')

    result = safe_read_text(test_file)
    assert result == "Hello, World!"

def test_safe_read_text_fallback_encoding(tmp_path):
    """Test safe_read_text successfully falling back to another encoding."""
    test_file = tmp_path / "test.txt"
    # Write some non-utf-8 text
    test_file.write_bytes(b'\xff\xfeH\x00e\x00l\x00l\x00o\x00') # utf-16

    result = safe_read_text(test_file)
    assert result is not None

def test_safe_read_text_fallback_via_mock():
    """Test safe_read_text successfully falling back to another encoding via mock."""
    filepath = Path("dummy.txt")

    # Create a side_effect function that fails on the first call (utf-8) and succeeds on the second (utf-16)
    call_count = 0
    def mock_read_text(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise UnicodeDecodeError('utf-8', b'', 0, 1, 'mocked')
        return "fallback success"

    with patch.object(Path, 'read_text', side_effect=mock_read_text):
        result = safe_read_text(filepath)
        assert result == "fallback success"
        assert call_count == 2
