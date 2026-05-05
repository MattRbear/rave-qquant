import pytest
from extract_nova_chat import strip_html

def test_strip_html_plain_text():
    """Test that plain text without HTML is unchanged."""
    assert strip_html("Hello world") == "Hello world"
    assert strip_html("Just a normal sentence.") == "Just a normal sentence."

def test_strip_html_simple_tags():
    """Test that simple HTML tags are removed and replaced with spaces."""
    assert strip_html("<p>Hello</p>") == "Hello"
    assert strip_html("<b>Bold</b> and <i>italic</i>") == "Bold and italic"
    assert strip_html("<div><span>Nested</span></div>") == "Nested"

def test_strip_html_attributes():
    """Test that HTML tags with attributes are removed."""
    assert strip_html('<a href="https://example.com">Link</a>') == "Link"
    assert strip_html('<div class="container" id="main">Content</div>') == "Content"
    assert strip_html('<img src="image.jpg" alt="An image" />') == ""

def test_strip_html_entities():
    """Test that HTML entities are unescaped correctly."""
    assert strip_html("Jack &amp; Jill") == "Jack & Jill"
    # Note: Due to the regex `<[^>]+>`, if entities unescape to < and >, they might be treated as tags and stripped.
    # So "5 < 10 > 2" will become "5 2" because "< 10 >" is stripped.
    assert strip_html("5 &lt; 10 &gt; 2") == "5 2"
    assert strip_html("Quote: &quot;Hello&quot; or &apos;World&apos;") == 'Quote: "Hello" or \'World\''
    assert strip_html("Caf&eacute;") == "Café"

def test_strip_html_whitespace_collapse():
    """Test that multiple spaces and newlines are collapsed to a single space."""
    assert strip_html("Too    many     spaces") == "Too many spaces"
    assert strip_html("New\n\nlines\nand\ttabs") == "New lines and tabs"
    assert strip_html("<p>  Spaced   <b>  out  </b>   content  </p>") == "Spaced out content"

def test_strip_html_complex_mixed():
    """Test a complex mix of tags, entities, and whitespace."""
    html_input = '''
    <div class="article">
        <h1>Title with &amp; entity</h1>
        <p>
            Some <strong>bold</strong> text and a <a href="#">link</a>.
            <br />
            New line     with spaces.
        </p>
    </div>
    '''
    # The regex replaces tags with a space, so "</a>." becomes " ."
    expected = "Title with & entity Some bold text and a link . New line with spaces."
    assert strip_html(html_input) == expected

def test_strip_html_edge_cases():
    """Test various edge cases like empty strings, only tags, invalid HTML, etc."""
    # Empty string
    assert strip_html("") == ""
    # Only tags
    assert strip_html("<br><hr>") == ""
    # Only spaces
    assert strip_html("   \t\n  ") == ""
    # Tags with spaces inside
    assert strip_html("< p > Hello </ p >") == "Hello"
    # Unclosed tags
    assert strip_html("Unclosed <tag") == "Unclosed <tag"
    assert strip_html("No start tag > here") == "No start tag > here"

def test_strip_html_script_style_tags():
    """Test that script and style contents are not stripped by this simple function.
    Note: The current implementation ONLY strips tags, not their content.
    This test verifies current behavior, even if it's considered 'cheap' stripping.
    """
    assert strip_html("<script>alert('Hello');</script>") == "alert('Hello');"
    assert strip_html("<style>body { color: red; }</style>") == "body { color: red; }"
