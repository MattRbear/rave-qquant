import pytest
import re
from unittest.mock import patch
from extract_nova_chat import match_topics, strip_html

# Dummy patterns for testing match_topics
DUMMY_TOPIC_PATTERNS = {
    'music': re.compile(r'\bmusic\b|\bsong\b', re.IGNORECASE),
    'gaming': re.compile(r'\bgaming rig\b|\bpc\b', re.IGNORECASE),
    'career': re.compile(r'\bjob\b|\bcareer\b', re.IGNORECASE)
}

@patch('extract_nova_chat.TOPIC_PATTERNS', DUMMY_TOPIC_PATTERNS)
def test_match_topics_happy_path():
    text = "I love listening to music while working on my gaming rig."
    topics, score = match_topics(text)
    assert topics == {'music', 'gaming'}
    # music (1) + gaming rig (1) = 2 matches. 2 * 0.1 = 0.2
    assert score == pytest.approx(0.2)

@patch('extract_nova_chat.TOPIC_PATTERNS', DUMMY_TOPIC_PATTERNS)
def test_match_topics_no_match():
    text = "I am eating a sandwich."
    topics, score = match_topics(text)
    assert topics == set()
    assert score == 0.0

@patch('extract_nova_chat.TOPIC_PATTERNS', DUMMY_TOPIC_PATTERNS)
def test_match_topics_case_insensitive():
    text = "Music is great, especially when getting a new JoB."
    topics, score = match_topics(text)
    assert topics == {'music', 'career'}
    # music (1) + job (1) = 2 matches. 2 * 0.1 = 0.2
    assert score == pytest.approx(0.2)

@patch('extract_nova_chat.TOPIC_PATTERNS', DUMMY_TOPIC_PATTERNS)
def test_match_topics_word_boundaries():
    # 'musician' contains 'music' but should not match due to \b
    # 'jobless' contains 'job' but should not match
    text = "The musician was jobless."
    topics, score = match_topics(text)
    assert topics == set()
    assert score == 0.0

@patch('extract_nova_chat.TOPIC_PATTERNS', DUMMY_TOPIC_PATTERNS)
def test_match_topics_multiple_matches_same_topic():
    text = "Music music song song"
    topics, score = match_topics(text)
    assert topics == {'music'}
    # 4 matches * 0.1 = 0.4
    assert score == pytest.approx(0.4)

def test_strip_html_basic():
    text = "<p>Hello <b>World</b></p>"
    assert strip_html(text) == "Hello World"

def test_strip_html_entities():
    text = "AT&amp;T &lt; Verizon"
    # Unescapes to "AT&T < Verizon"
    # Then strips tags (no valid tags here, but < is tricky)
    # Actually, in the current implementation, `< Verizon` is not a closed tag,
    # so `r'<[^>]+>'` won't match it.
    assert strip_html(text) == "AT&T < Verizon"

def test_strip_html_edge_case_unescaped_brackets():
    # Testing the documented flaw in strip_html where unescaped angle brackets
    # act like a tag and delete content.
    # Text: "I love <this> so much"
    text = "I love &lt;this&gt; so much"
    # Unescapes to "I love <this> so much"
    # The `<this>` matches `<[^>]+>`, so it is replaced by ' '
    # Result: "I love so much"
    assert strip_html(text) == "I love so much"

def test_strip_html_whitespace_collapse():
    text = "<div>  Hello   \n\t World  </div>"
    assert strip_html(text) == "Hello World"
