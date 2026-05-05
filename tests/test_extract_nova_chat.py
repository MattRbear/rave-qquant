import pytest
from pathlib import Path
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from extract_nova_chat import detect_file_format

def test_detect_file_format_json():
    assert detect_file_format(Path("data/test.json")) == "json"
    assert detect_file_format(Path("TEST.JSON")) == "json"

def test_detect_file_format_jsonl():
    assert detect_file_format(Path("data/test.jsonl")) == "jsonl"
    assert detect_file_format(Path("TEST.JSONL")) == "jsonl"

def test_detect_file_format_plaintext():
    assert detect_file_format(Path("doc.txt")) == "plaintext"
    assert detect_file_format(Path("readme.md")) == "plaintext"
    assert detect_file_format(Path("DOC.TXT")) == "plaintext"
    assert detect_file_format(Path("README.MD")) == "plaintext"

def test_detect_file_format_html():
    assert detect_file_format(Path("page.html")) == "html"
    assert detect_file_format(Path("index.htm")) == "html"
    assert detect_file_format(Path("PAGE.HTML")) == "html"

def test_detect_file_format_unknown():
    assert detect_file_format(Path("data.csv")) == "unknown"
    assert detect_file_format(Path("archive.zip")) == "unknown"
    assert detect_file_format(Path("no_extension_file")) == "unknown"
    assert detect_file_format(Path(".hidden")) == "unknown"
