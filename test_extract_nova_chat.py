import pytest
import hashlib
from extract_nova_chat import stable_hash, strip_html

def test_stable_hash():
    # Deterministic output
    text1 = "hello world"
    assert stable_hash(text1) == stable_hash(text1)

    # Different inputs yield different outputs
    text2 = "hello world 2"
    assert stable_hash(text1) != stable_hash(text2)

    # Output length is exactly 16 chars
    assert len(stable_hash(text1)) == 16
    assert len(stable_hash("")) == 16

    # Unicode behavior
    text_unicode = "hello 🤖"
    # Verify it doesn't crash and returns the expected format
    assert len(stable_hash(text_unicode)) == 16

    # Check actual hash value to guarantee stability
    # "hello world" encoded in utf-8 -> sha256 -> first 16 hex chars
    expected_hash = hashlib.sha256("hello world".encode("utf-8")).hexdigest()[:16]
    assert stable_hash("hello world") == expected_hash

def test_strip_html():
    # Simple tag removal
    assert strip_html("<b>bold</b>") == "bold"
    assert strip_html("<p>paragraph</p>") == "paragraph"

    # HTML entity unescaping
    assert strip_html("A &amp; B") == "A & B"
    assert strip_html("A &lt; B") == "A < B"
    assert strip_html("&quot;Quote&quot;") == '"Quote"'

    # Collapsing multiple spaces
    assert strip_html("  hello   world  ") == "hello world"
    assert strip_html("hello\n\nworld") == "hello world"
    assert strip_html("hello\tworld") == "hello world"

    # Combination of tags, entities, and spaces
    assert strip_html("<p>Hello &amp;   <b>World</b>!</p>") == "Hello & World !"

    # Edge cases
    assert strip_html("") == ""
    assert strip_html("No HTML here") == "No HTML here"

    # Nested and complex tags
    assert strip_html("<div><p><span>deeply nested</span></p></div>") == "deeply nested"
    assert strip_html("<a href='http://example.com?a=1&amp;b=2'>link</a>") == "link"
