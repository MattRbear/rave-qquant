import pytest
from unittest.mock import patch
from pathlib import Path
from extract_nova_chat import safe_read_text

def test_safe_read_text_error_path():
    """Test that safe_read_text returns None when all encodings fail."""
    test_path = Path("dummy_path.txt")
    with patch("pathlib.Path.read_text", side_effect=Exception("Simulated read error")):
        result = safe_read_text(test_path)
    assert result is None
