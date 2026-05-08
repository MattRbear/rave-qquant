import pytest
import re
from unittest.mock import patch
import extract_nova_chat
from extract_nova_chat import match_topics

# Dummy topics for robust testing against future config changes
DUMMY_TOPICS = {
    'trading': ['trade', 'trading', 'trader'],
    'nova': ['nova', 'ai'],
    'personal_life': ['dog']
}

# Pre-compile the regexes as done in the main file
DUMMY_TOPIC_PATTERNS = {}
for topic, keywords in DUMMY_TOPICS.items():
    patterns = []
    for kw in keywords:
        escaped = re.escape(kw)
        if ' ' in kw:
            patterns.append(escaped)
        else:
            patterns.append(rf'\b{escaped}\b')
    DUMMY_TOPIC_PATTERNS[topic] = re.compile('|'.join(patterns), re.IGNORECASE)


@pytest.fixture(autouse=True)
def mock_topic_patterns():
    """Mock the global TOPIC_PATTERNS to use our deterministic dummy data."""
    with patch.dict(extract_nova_chat.TOPIC_PATTERNS, DUMMY_TOPIC_PATTERNS, clear=True):
        yield


def test_match_topics_empty_or_irrelevant():
    """Test text with no relevant topics."""
    assert match_topics("") == (set(), 0.0)
    assert match_topics("hello world") == (set(), 0.0)
    assert match_topics("just a random conversation") == (set(), 0.0)

def test_match_topics_single_match():
    """Test single occurrences of a topic."""
    matched, score = match_topics("I like to trade")
    assert matched == {'trading'}
    assert pytest.approx(score) == 0.1

def test_match_topics_word_boundaries():
    """Ensure partial word matches inside other words do not count."""
    # "trademark" contains "trade"
    assert match_topics("trademark")[0] == set()
    # "dogmatic" contains "dog"
    assert match_topics("dogmatic")[0] == set()

def test_match_topics_case_insensitivity():
    """Test case insensitivity."""
    matched, score = match_topics("TRADING is fun")
    assert matched == {'trading'}
    assert pytest.approx(score) == 0.1

    matched, score = match_topics("Hello NoVa")
    assert matched == {'nova'}
    assert pytest.approx(score) == 0.1

def test_match_topics_multiple_same_topic():
    """Test multiple occurrences of the same topic keywords."""
    # "trade" and "trader" and "trading" are all keywords for 'trading'
    matched, score = match_topics("trade trader trading")
    assert matched == {'trading'}
    assert pytest.approx(score) == 0.3

def test_match_topics_multiple_topics():
    """Test string containing keywords from different topics."""
    # "nova" matches 'nova', "trading" matches 'trading'
    matched, score = match_topics("nova likes trading")
    assert matched == {'nova', 'trading'}
    assert pytest.approx(score) == 0.2
