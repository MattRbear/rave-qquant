import pytest
from pathlib import Path
from extract_nova_chat import detect_file_format

def test_detect_file_format_json():
    assert detect_file_format(Path("file.json")) == "json"
    assert detect_file_format(Path("path/to/file.json")) == "json"
    assert detect_file_format(Path("file.JSON")) == "json"

def test_detect_file_format_jsonl():
    assert detect_file_format(Path("file.jsonl")) == "jsonl"
    assert detect_file_format(Path("file.JSONL")) == "jsonl"

def test_detect_file_format_plaintext():
    assert detect_file_format(Path("file.txt")) == "plaintext"
    assert detect_file_format(Path("file.md")) == "plaintext"
    assert detect_file_format(Path("file.TXT")) == "plaintext"
    assert detect_file_format(Path("file.Md")) == "plaintext"

def test_detect_file_format_html():
    assert detect_file_format(Path("file.html")) == "html"
    assert detect_file_format(Path("file.htm")) == "html"
    assert detect_file_format(Path("file.HTML")) == "html"

def test_detect_file_format_unknown():
    assert detect_file_format(Path("file.pdf")) == "unknown"
    assert detect_file_format(Path("file.csv")) == "unknown"
    assert detect_file_format(Path("file.jpg")) == "unknown"
    assert detect_file_format(Path("file_without_extension")) == "unknown"
