import pytest
from extract_nova_chat import match_topics

def test_match_topics_empty_text():
    """Test that empty text returns no topics and 0 score."""
    topics, score = match_topics("")
    assert topics == set()
    assert score == 0.0

def test_match_topics_no_match():
    """Test text with no matching keywords."""
    topics, score = match_topics("Hello world, this is a random text with no keywords.")
    assert topics == set()
    assert score == 0.0

def test_match_topics_single_match():
    """Test text with a single matching keyword."""
    # 'trade' is in the 'trading' topic
    topics, score = match_topics("I want to make a trade today.")
    assert topics == {'trading'}
    assert score == pytest.approx(0.1)

def test_match_topics_multiple_occurrences():
    """Test text with multiple occurrences of keywords in the same topic."""
    # 'trade' and 'market' are in 'trading'
    topics, score = match_topics("The market is good for a trade, another trade.")
    assert topics == {'trading'}
    # 3 matches: 'market', 'trade', 'trade'
    assert score == pytest.approx(0.3)

def test_match_topics_multiple_topics():
    """Test text matching multiple different topics."""
    # 'stock' -> stocks, 'buy' -> trading, 'dog' -> personal_life
    text = "I want to buy some stock for my dog."
    topics, score = match_topics(text)
    assert topics == {'stocks', 'trading', 'personal_life'}
    # 3 matches: 'buy' (1), 'stock' (1), 'dog' (1)
    assert score == pytest.approx(0.3)

def test_match_topics_case_insensitivity():
    """Test that matching is case-insensitive."""
    # 'TrAdE' -> 'trade'
    topics, score = match_topics("Let's do a TrAdE.")
    assert topics == {'trading'}
    assert score == pytest.approx(0.1)

def test_match_topics_word_boundaries():
    """Test that word boundaries are respected."""
    # 'trade' should not match 'trademark'
    topics, score = match_topics("This is my trademark.")
    assert topics == set()
    assert score == 0.0

    # 'bot' should not match 'bottle'
    topics, score = match_topics("A bottle of water.")
    assert topics == set()
    assert score == 0.0

    # 'bot' should match 'bot'
    topics, score = match_topics("This is a bot.")
    assert topics == {'bot_ideas'}
    assert score == pytest.approx(0.1)

def test_match_topics_multi_word_phrases():
    """Test multi-word keywords."""
    # 'old school runescape' is in 'osrs'
    topics, score = match_topics("I love playing old school runescape all day.")
    assert topics == {'osrs'}
    assert score == pytest.approx(0.1)
