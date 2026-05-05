from extract_nova_chat import stable_hash

def test_stable_hash():
    """Test that stable_hash generates correct deterministic hashes."""

    # Deterministic output for known input
    hash1 = stable_hash("hello world")
    assert hash1 == stable_hash("hello world")

    # Length is exactly 16 chars
    assert len(hash1) == 16

    # Different inputs yield different hashes
    assert hash1 != stable_hash("Hello world")

    # Empty string
    empty_hash = stable_hash("")
    assert len(empty_hash) == 16
    assert empty_hash == stable_hash("")

def test_stable_hash_unicode():
    """Test that stable_hash handles unicode characters correctly."""

    # Unicode characters
    hash_unicode = stable_hash("こんにちは世界")
    assert len(hash_unicode) == 16
    assert hash_unicode == stable_hash("こんにちは世界")

    # Emoji
    hash_emoji = stable_hash("hello 🌍")
    assert len(hash_emoji) == 16
    assert hash_emoji == stable_hash("hello 🌍")

    # Unicode and ASCII difference
    assert stable_hash("cafe") != stable_hash("café")

def test_stable_hash_invalid_surrogates():
    """Test that stable_hash gracefully handles strings with invalid surrogates using errors='replace'."""

    # Invalid surrogate pair which can cause errors during utf-8 encoding without errors='replace'
    # Python 3 strings are unicode. We use a surrogate sequence.
    invalid_string = "hello \ud800 world"

    # Should not raise UnicodeEncodeError
    hash_invalid = stable_hash(invalid_string)
    assert len(hash_invalid) == 16
    assert hash_invalid == stable_hash(invalid_string)
