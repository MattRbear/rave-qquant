import pytest
from extract_nova_chat import stable_hash

def test_stable_hash_consistency():
    """Ensure the same input string produces the same hash consistently."""
    text = "test_string_123"
    assert stable_hash(text) == stable_hash(text)

def test_stable_hash_length():
    """Ensure the output hash is always 16 characters long."""
    text1 = "short"
    text2 = "this_is_a_much_longer_string_that_should_still_produce_16_chars"
    assert len(stable_hash(text1)) == 16
    assert len(stable_hash(text2)) == 16

def test_stable_hash_empty_string():
    """Ensure an empty string produces a valid 16-character hash."""
    result = stable_hash("")
    assert isinstance(result, str)
    assert len(result) == 16

def test_stable_hash_different_inputs():
    """Ensure different inputs produce different hashes (up to 16 char prefix)."""
    assert stable_hash("text1") != stable_hash("text2")

def test_stable_hash_unicode():
    """Ensure hashing works correctly with non-ASCII unicode characters."""
    text = "hello world 😊🌍 testing"
    assert len(stable_hash(text)) == 16
    assert stable_hash(text) == stable_hash(text)
    assert stable_hash("hello world 😊🌍 testing") != stable_hash("hello world 🌍😊 testing")

def test_stable_hash_invalid_surrogates():
    """Ensure invalid surrogate characters do not raise a UnicodeEncodeError."""
    # This string contains a lone surrogate which is invalid in strictly encoded UTF-8
    invalid_text = "test \ud800 string"
    try:
        result = stable_hash(invalid_text)
        assert len(result) == 16
    except UnicodeEncodeError:
        pytest.fail("stable_hash raised UnicodeEncodeError with invalid surrogate characters.")
