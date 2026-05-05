import pytest
from pathlib import Path
from extract_nova_chat import (
    stable_hash,
    strip_html,
    detect_file_format,
    match_topics,
    format_record,
)

def test_stable_hash():
    # Check length
    res1 = stable_hash("hello")
    assert len(res1) == 16

    # Check stable output
    res2 = stable_hash("hello")
    assert res1 == res2

    # Check different output
    res3 = stable_hash("world")
    assert res1 != res3

def test_strip_html():
    # Stripping simple tags
    assert strip_html("<p>Hello</p>") == "Hello"

    # Unescaping HTML entities
    assert strip_html("Hello &amp; World") == "Hello & World"

    # Nested tags and consecutive whitespaces
    assert strip_html("<div>  <p>  Nested   <b>Tags</b> </p> </div>") == "Nested Tags"

def test_detect_file_format():
    assert detect_file_format(Path("file.json")) == "json"
    assert detect_file_format(Path("data.jsonl")) == "jsonl"
    assert detect_file_format(Path("notes.txt")) == "plaintext"
    assert detect_file_format(Path("README.md")) == "plaintext"
    assert detect_file_format(Path("index.html")) == "html"
    assert detect_file_format(Path("page.htm")) == "html"
    assert detect_file_format(Path("document.pdf")) == "unknown"

def test_match_topics():
    # Match keyword 'trade' (in 'trading' topic) and 'nova' (in 'nova' topic)
    topics, score = match_topics("I trade with nova.")
    assert "trading" in topics
    assert "nova" in topics
    # 'trade' -> 1 match, 'nova' -> 1 match
    assert pytest.approx(score) == 0.2

    # Case insensitivity and multiple matches
    topics, score = match_topics("Trade TRADE trade")
    assert "trading" in topics
    assert pytest.approx(score) == 0.3

    # No match
    topics, score = match_topics("Random irrelevant text.")
    assert len(topics) == 0
    assert score == 0.0

def test_format_record():
    filepath = Path("/root/data/chat.json")
    input_root = Path("/root/data")

    # Extracting from string
    rec1 = format_record("Hello string", filepath, input_root, "json", 0)
    assert rec1['text'] == "Hello string"
    assert rec1['source_file'] == "chat.json"
    assert rec1['detected_format'] == "json"
    assert rec1['message_index'] == 0

    # Extracting from dict and mapping roles correctly
    data2 = {"content": "Hello dict", "role": "user", "timestamp": "2023-01-01", "conversation_id": "conv123"}
    rec2 = format_record(data2, filepath, input_root, "json", 1)
    assert rec2['text'] == "Hello dict"
    assert rec2['role'] == "user"
    assert rec2['timestamp'] == "2023-01-01"
    assert rec2['conversation_id'] == "conv123"

    # Author fallback for role
    data3 = {"message": "Hello author", "author": "assistant", "date": "2023-01-02", "thread_id": "thread456"}
    rec3 = format_record(data3, filepath, input_root, "json", 2)
    assert rec3['text'] == "Hello author"
    assert rec3['role'] == "assistant"
    assert rec3['timestamp'] == "2023-01-02"
    assert rec3['conversation_id'] == "thread456"
