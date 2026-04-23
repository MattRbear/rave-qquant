"""
extract_nova_chat.py

Incrementally extracts and filters chat history from massive datasets.
Outputs multiple chunked JSON files with topic-filtered conversations.

Author: Claude
Python: 3.12+
Platform: Windows
"""

import json
import re
import hashlib
import argparse
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any, Iterator, Set
from collections import defaultdict
from datetime import datetime
import html


# ============================================================================
# CONFIGURATION
# ============================================================================

TOPICS = {
    'trading': [
        'trade', 'trading', 'trader', 'trades', 'traded',
        'market', 'markets', 'price', 'chart', 'candle',
        'buy', 'sell', 'long', 'short', 'position',
        'entry', 'exit', 'stop', 'loss', 'profit',
        'vwap', 'cvd', 'volume', 'liquidity', 'orderbook',
        'wick', 'support', 'resistance', 'breakout'
    ],
    'stocks': [
        'stock', 'stocks', 'equity', 'equities',
        'option', 'options', 'spy', 'qqq',
        'share', 'shares', 'ticker', 'nasdaq', 'nyse'
    ],
    'osrs': [
        'osrs', 'runescape', 'old school runescape',
        'runelite', 'gp', 'gold', 'grinding', 'quest'
    ],
    'bot_ideas': [
        'bot', 'bots', 'automation', 'automated', 'automate',
        'script', 'algorithm', 'algo', 'system', 'strategy'
    ],
    'career': [
        'career', 'job', 'work', 'employment', 'resume',
        'interview', 'salary', 'promotion', 'boss', 'manager',
        'factory', 'shift', 'wage', 'income'
    ],
    'tkl': [
        'tkl', 'guitar case', 'manufacturing', 'factory work'
    ],
    'friends': [
        'friend', 'friends', 'friendship', 'buddy', 'homie',
        'bestie', 'pal', 'mate'
    ],
    'pc': [
        'pc', 'computer', 'gpu', 'cpu', 'ram', 'windows',
        'driver', 'hardware', 'gaming rig', 'desktop',
        'laptop', 'monitor', 'keyboard', 'mouse'
    ],
    'ravebear': [
        'ravebear', 'rave bear', 'mr bear', 'm.r bear',
        'astral bear', 'bearish', 'bean'  # bean is his dog
    ],
    'raving': [
        'rave', 'raving', 'raver', 'festival', 'edm',
        'dubstep', 'bass', 'lost lands', 'dj', 'concert'
    ],
    'music': [
        'music', 'song', 'album', 'artist', 'track',
        'listen', 'spotify', 'playlist', 'beat', 'sound'
    ],
    'depression': [
        'depress', 'depression', 'depressed', 'sad', 'sadness',
        'lonely', 'loneliness', 'hopeless', 'anxiety', 'anxious',
        'mental health', 'therapy', 'therapist', 'medication'
    ],
    'adhd': [
        'adhd', 'add', 'attention', 'focus', 'focused', 'focusing',
        'distract', 'distracted', 'concentration', 'hyperfocus',
        'stimulant', 'adderall', 'vyvanse', 'ritalin'
    ],
    'goals': [
        'goal', 'goals', 'target', 'objective', 'aim',
        'plan', 'dream', 'ambition', 'mission', 'vision',
        'achieve', 'accomplish', 'milestone'
    ],
    'strats': [
        'strat', 'strategy', 'strategies', 'strategic',
        'tactic', 'tactics', 'tactical', 'approach',
        'method', 'methodology', 'framework', 'playbook'
    ],
    'nova': [
        'nova', 'claude', 'ai', 'assistant', 'chatbot',
        'llm', 'model', 'gpt', 'anthropic'
    ],
    'personal_life': [
        'mom', 'mother', 'dad', 'father', 'family',
        'home', 'house', 'apartment', 'sleep', 'tired',
        'exhausted', 'eat', 'food', 'hungry', 'shower',
        'bean', 'dog', 'pet', 'girlfriend', 'relationship'
    ]
}

# Compile regex patterns for word boundaries
TOPIC_PATTERNS = {}
for topic, keywords in TOPICS.items():
    # Build regex with word boundaries for accurate matching
    patterns = []
    for kw in keywords:
        # Escape special regex chars, then wrap in word boundary
        escaped = re.escape(kw)
        # Use word boundary \b for single words, flexible for multi-word
        if ' ' in kw:
            patterns.append(escaped)
        else:
            patterns.append(rf'\b{escaped}\b')
    TOPIC_PATTERNS[topic] = re.compile('|'.join(patterns), re.IGNORECASE)


# ============================================================================
# LOGGING
# ============================================================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def stable_hash(text: str) -> str:
    """Generate stable hash for record_id."""
    return hashlib.sha256(text.encode('utf-8', errors='replace')).hexdigest()[:16]


def strip_html(text: str) -> str:
    """Cheaply strip HTML tags."""
    # Unescape HTML entities
    text = html.unescape(text)
    # Remove tags
    text = re.sub(r'<[^>]+>', ' ', text)
    # Collapse whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def detect_file_format(filepath: Path) -> str:
    """Detect file format from extension and content."""
    ext = filepath.suffix.lower()
    
    if ext == '.json':
        return 'json'
    elif ext == '.jsonl':
        return 'jsonl'
    elif ext in ['.txt', '.md']:
        return 'plaintext'
    elif ext in ['.html', '.htm']:
        return 'html'
    else:
        return 'unknown'


def safe_read_text(filepath: Path) -> Optional[str]:
    """Safely read text file with encoding fallback."""
    encodings = ['utf-8', 'utf-16', 'latin-1', 'cp1252']
    
    for encoding in encodings:
        try:
            return filepath.read_text(encoding=encoding, errors='replace')
        except Exception:
            continue
    
    logger.warning(f"Could not read file with any encoding: {filepath}")
    return None


# ============================================================================
# TOPIC MATCHING
# ============================================================================

def match_topics(text: str) -> tuple[Set[str], float]:
    """
    Match topics in text.
    
    Returns:
        (matched_topics, match_score)
    """
    matched = set()
    score = 0.0
    
    text_lower = text.lower()
    
    for topic, pattern in TOPIC_PATTERNS.items():
        matches = pattern.findall(text_lower)
        if matches:
            matched.add(topic)
            # Score: number of matches × small weight
            score += len(matches) * 0.1
    
    return matched, score


# ============================================================================
# RECORD EXTRACTORS
# ============================================================================

def _process_json_list(data: list, filepath: Path, input_root: Path) -> Iterator[Dict[str, Any]]:
    """Helper to process a JSON list of messages."""
    for idx, item in enumerate(data):
        if isinstance(item, dict):
            yield format_record(item, filepath, input_root, 'openai_export_json', idx)
        elif isinstance(item, str):
            yield {
                'text': item,
                'source_file': str(filepath.relative_to(input_root)),
                'detected_format': 'json_array',
                'message_index': idx
            }

def _process_json_dict(data: dict, filepath: Path, input_root: Path) -> Iterator[Dict[str, Any]]:
    """Helper to process a JSON dictionary structure."""
    if 'messages' in data:
        messages = data['messages']
        conv_id = data.get('id') or data.get('conversation_id')
        for idx, msg in enumerate(messages):
            record = format_record(msg, filepath, input_root, 'openai_export_json', idx)
            if conv_id:
                record['conversation_id'] = conv_id
            yield record
    elif 'conversations' in data:
        for conv in data['conversations']:
            conv_id = conv.get('id')
            messages = conv.get('messages', [])
            for idx, msg in enumerate(messages):
                record = format_record(msg, filepath, input_root, 'openai_export_json', idx)
                if conv_id:
                    record['conversation_id'] = conv_id
                yield record
    else:
        # Fallback: extract any text-like fields
        yield format_record(data, filepath, input_root, 'json_dict', 0)

def extract_from_json(filepath: Path, input_root: Path) -> Iterator[Dict[str, Any]]:
    """Extract records from JSON file."""
    try:
        text = safe_read_text(filepath)
        if not text:
            return
        
        data = json.loads(text)
        
        # Try to detect structure
        if isinstance(data, list):
            yield from _process_json_list(data, filepath, input_root)
        elif isinstance(data, dict):
            yield from _process_json_dict(data, filepath, input_root)
    
    except json.JSONDecodeError as e:
        logger.warning(f"JSON decode error in {filepath}: {e}")
    except Exception as e:
        logger.error(f"Error processing JSON {filepath}: {e}")


def extract_from_jsonl(filepath: Path, input_root: Path) -> Iterator[Dict[str, Any]]:
    """Extract records from JSONL file (line-by-line JSON)."""
    try:
        with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
            for idx, line in enumerate(f):
                line = line.strip()
                if not line:
                    continue
                
                try:
                    data = json.loads(line)
                    yield format_record(data, filepath, input_root, 'jsonl', idx)
                except json.JSONDecodeError:
                    # Skip malformed lines
                    continue
    
    except Exception as e:
        logger.error(f"Error processing JSONL {filepath}: {e}")


def _process_structured_plaintext(splits: list[str], filepath: Path, input_root: Path) -> Iterator[Dict[str, Any]]:
    """Helper to process structured plaintext messages."""
    idx = 0
    for i in range(1, len(splits), 2):
        if i+1 < len(splits):
            role = splits[i].lower()
            content = splits[i+1].strip()

            if content:
                yield {
                    'text': content,
                    'source_file': str(filepath.relative_to(input_root)),
                    'detected_format': 'plaintext_structured',
                    'message_index': idx,
                    'role': role if role in ['user', 'assistant', 'system'] else 'unknown'
                }
                idx += 1

def extract_from_plaintext(filepath: Path, input_root: Path) -> Iterator[Dict[str, Any]]:
    """Extract records from plaintext file."""
    try:
        text = safe_read_text(filepath)
        if not text:
            return
        
        # Try to detect message boundaries
        # Common patterns: "User:", "Assistant:", "Human:", "AI:", etc.
        message_pattern = re.compile(
            r'^(User|Assistant|Human|AI|System|You|Me):\s*',
            re.MULTILINE | re.IGNORECASE
        )
        
        splits = message_pattern.split(text)
        
        if len(splits) > 3:
            yield from _process_structured_plaintext(splits, filepath, input_root)
        else:
            # Treat entire file as one record
            yield {
                'text': text,
                'source_file': str(filepath.relative_to(input_root)),
                'detected_format': 'plaintext',
                'message_index': 0,
                'role': 'unknown'
            }
    
    except Exception as e:
        logger.error(f"Error processing plaintext {filepath}: {e}")


def extract_from_html(filepath: Path, input_root: Path) -> Iterator[Dict[str, Any]]:
    """Extract records from HTML file."""
    try:
        text = safe_read_text(filepath)
        if not text:
            return
        
        # Strip HTML
        clean_text = strip_html(text)
        
        if clean_text:
            yield {
                'text': clean_text,
                'source_file': str(filepath.relative_to(input_root)),
                'detected_format': 'html',
                'message_index': 0,
                'role': 'unknown'
            }
    
    except Exception as e:
        logger.error(f"Error processing HTML {filepath}: {e}")


def format_record(data: Any, filepath: Path, input_root: Path, format_type: str, index: int) -> Dict[str, Any]:
    """Format a record from various data structures."""
    record = {
        'source_file': str(filepath.relative_to(input_root)),
        'detected_format': format_type,
        'message_index': index,
        'conversation_id': None,
        'role': 'unknown',
        'timestamp': None,
        'text': ''
    }
    
    if isinstance(data, str):
        record['text'] = data
        return record
    
    if not isinstance(data, dict):
        record['text'] = str(data)
        return record
    
    # Extract fields from dict
    # Text content
    for field in ['text', 'content', 'message', 'body', 'text_content']:
        if field in data:
            record['text'] = str(data[field])
            break
    
    # Role
    if 'role' in data:
        role = str(data['role']).lower()
        if role in ['user', 'assistant', 'system']:
            record['role'] = role
    elif 'author' in data:
        author = str(data['author']).lower()
        if author in ['user', 'assistant', 'system']:
            record['role'] = author
    
    # Timestamp
    for field in ['timestamp', 'created_at', 'date', 'time']:
        if field in data:
            record['timestamp'] = str(data[field])
            break
    
    # Conversation ID
    for field in ['conversation_id', 'conv_id', 'thread_id', 'chat_id']:
        if field in data:
            record['conversation_id'] = str(data[field])
            break
    
    return record


# ============================================================================
# CHUNKED OUTPUT WRITER
# ============================================================================

class ChunkedWriter:
    """Writes records to multiple chunked JSON files."""
    
    def __init__(self, output_dir: Path, max_chars: int):
        self.output_dir = output_dir
        self.max_chars = max_chars
        self.chunk_index = 1
        self.current_file = None
        self.current_size = 0
        self.current_records = []
        self.chunk_files = []
        
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def add_record(self, record: Dict[str, Any]):
        """Add a record, starting new chunk if needed."""
        # Generate record_id
        record_id_input = f"{record['source_file']}_{record.get('message_index', 0)}"
        record['record_id'] = stable_hash(record_id_input)
        
        # Estimate size (conservative)
        record_json = json.dumps(record, ensure_ascii=False)
        record_size = len(record_json) + 10  # +10 for comma, brackets, newlines
        
        # Check if need new chunk
        if self.current_size + record_size > self.max_chars:
            self._flush_chunk()
        
        self.current_records.append(record)
        self.current_size += record_size
    
    def _flush_chunk(self):
        """Write current chunk to file."""
        if not self.current_records:
            return
        
        filename = f"nova_chat_{self.chunk_index:04d}.json"
        filepath = self.output_dir / filename
        temp_filepath = self.output_dir / f"{filename}.tmp"
        
        try:
            # Write to temp file
            with open(temp_filepath, 'w', encoding='utf-8') as f:
                json.dump(self.current_records, f, ensure_ascii=False, indent=2)
            
            # Rename to final
            temp_filepath.rename(filepath)
            
            # Track chunk metadata
            self.chunk_files.append({
                'filename': filename,
                'record_count': len(self.current_records),
                'char_size': self.current_size
            })
            
            logger.info(f"Wrote chunk {self.chunk_index}: {len(self.current_records)} records, {self.current_size:,} chars")
            
            # Reset for next chunk
            self.chunk_index += 1
            self.current_records = []
            self.current_size = 0
        
        except Exception as e:
            logger.error(f"Error writing chunk {self.chunk_index}: {e}")
            # Clean up temp file
            if temp_filepath.exists():
                temp_filepath.unlink()
    
    def close(self):
        """Flush remaining records and close."""
        self._flush_chunk()
        return self.chunk_files


# ============================================================================
# MAIN PROCESSOR
# ============================================================================

def _process_record(record: Dict[str, Any], writer: ChunkedWriter, stats: Dict[str, Any]):
    """Helper to process a single record, filter it by topics, and update stats."""
    text = record.get('text', '')

    if not text or len(text) < 10:
        stats['total_records_dropped'] += 1
        return

    # Match topics
    topics, score = match_topics(text)

    if topics and score > 0:
        # Keep this record
        record['topics'] = sorted(list(topics))
        record['match_score'] = round(score, 2)

        writer.add_record(record)
        stats['total_records_kept'] += 1

        # Update topic counts
        for topic in topics:
            stats['topic_counts'][topic] += 1
    else:
        stats['total_records_dropped'] += 1


def process_dataset(input_dir: Path, output_dir: Path, max_chars: int):
    """Main processing pipeline."""
    logger.info(f"Starting extraction from: {input_dir}")
    logger.info(f"Output directory: {output_dir}")
    logger.info(f"Max chars per chunk: {max_chars:,}")
    
    # Initialize
    writer = ChunkedWriter(output_dir, max_chars)
    
    stats = {
        'total_files_scanned': 0,
        'total_records_kept': 0,
        'total_records_dropped': 0,
        'topic_counts': defaultdict(int),
        'failed_files': []
    }
    
    # Scan all files
    all_files = []
    for ext in ['*.json', '*.jsonl', '*.txt', '*.md', '*.html', '*.htm']:
        all_files.extend(input_dir.rglob(ext))
    
    logger.info(f"Found {len(all_files)} files to process")
    
    # Process each file
    for file_idx, filepath in enumerate(all_files, 1):
        stats['total_files_scanned'] += 1
        
        if file_idx % 10 == 0:
            logger.info(f"Progress: {file_idx}/{len(all_files)} files, {stats['total_records_kept']} records kept")
        
        try:
            # Detect format and extract records
            file_format = detect_file_format(filepath)
            
            if file_format == 'json':
                records = extract_from_json(filepath, input_dir)
            elif file_format == 'jsonl':
                records = extract_from_jsonl(filepath, input_dir)
            elif file_format == 'plaintext':
                records = extract_from_plaintext(filepath, input_dir)
            elif file_format == 'html':
                records = extract_from_html(filepath, input_dir)
            else:
                records = extract_from_plaintext(filepath, input_dir)  # Fallback
            
            # Filter and write records
            for record in records:
                _process_record(record, writer, stats)
        
        except Exception as e:
            logger.error(f"Failed to process {filepath}: {e}")
            stats['failed_files'].append({
                'file': str(filepath),
                'error': str(e)
            })
    
    # Close writer
    chunk_files = writer.close()
    
    # Write manifest
    manifest = {
        'extraction_date': datetime.now().isoformat(),
        'input_directory': str(input_dir),
        'output_directory': str(output_dir),
        'total_files_scanned': stats['total_files_scanned'],
        'total_records_kept': stats['total_records_kept'],
        'total_records_dropped': stats['total_records_dropped'],
        'topic_counts': dict(stats['topic_counts']),
        'output_chunks': chunk_files,
        'failed_files': stats['failed_files']
    }
    
    manifest_path = output_dir / 'manifest.json'
    with open(manifest_path, 'w', encoding='utf-8') as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    
    logger.info("=" * 60)
    logger.info("EXTRACTION COMPLETE")
    logger.info(f"Files scanned: {stats['total_files_scanned']}")
    logger.info(f"Records kept: {stats['total_records_kept']}")
    logger.info(f"Records dropped: {stats['total_records_dropped']}")
    logger.info(f"Output chunks: {len(chunk_files)}")
    logger.info(f"Manifest written: {manifest_path}")
    logger.info("=" * 60)


# ============================================================================
# SELF-TEST MODE
# ============================================================================

def run_self_test():
    """Run a quick self-test on synthetic data."""
    logger.info("Running self-test...")
    
    # Create temp directories
    test_input = Path("test_input_temp")
    test_output = Path("test_output_temp")
    
    test_input.mkdir(exist_ok=True)
    test_output.mkdir(exist_ok=True)
    
    try:
        # Create test data
        test_data = [
            {"role": "user", "content": "I want to learn about trading stocks and options"},
            {"role": "assistant", "content": "I can help you with that!"},
            {"role": "user", "content": "My depression is getting worse and I need goals"},
            {"role": "assistant", "content": "Let's talk about achievable goals"},
            {"role": "user", "content": "This is irrelevant noise that should be filtered"},
            {"role": "user", "content": "Tell me about OSRS bots and automation strategies"},
        ]
        
        # Write test file
        test_file = test_input / "test.jsonl"
        with open(test_file, 'w') as f:
            for item in test_data:
                f.write(json.dumps(item) + '\n')
        
        # Run extraction with small chunk size
        process_dataset(test_input, test_output, max_chars=500)
        
        # Verify output
        output_files = list(test_output.glob("nova_chat_*.json"))
        manifest = test_output / "manifest.json"
        
        assert len(output_files) > 0, "No output files created"
        assert manifest.exists(), "Manifest not created"
        
        # Load and verify
        with open(manifest) as f:
            manifest_data = json.load(f)
        
        assert manifest_data['total_records_kept'] >= 4, f"Expected 4+ records, got {manifest_data['total_records_kept']}"
        assert manifest_data['total_records_dropped'] >= 1, f"Expected 1+ dropped, got {manifest_data['total_records_dropped']}"
        
        logger.info("✓ Self-test PASSED")
        logger.info(f"  Output files: {len(output_files)}")
        logger.info(f"  Records kept: {manifest_data['total_records_kept']}")
        logger.info(f"  Records dropped: {manifest_data['total_records_dropped']}")
        
    finally:
        # Cleanup
        import shutil
        if test_input.exists():
            shutil.rmtree(test_input)
        if test_output.exists():
            shutil.rmtree(test_output)


# ============================================================================
# CLI
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description='Extract and filter chat history by topics'
    )
    parser.add_argument(
        '--input',
        type=str,
        required=True,
        help='Input directory containing chat files'
    )
    parser.add_argument(
        '--output',
        type=str,
        required=True,
        help='Output directory for filtered chunks'
    )
    parser.add_argument(
        '--max-chars',
        type=int,
        default=4_950_000,
        help='Maximum characters per output file (default: 4,950,000)'
    )
    parser.add_argument(
        '--self-test',
        action='store_true',
        help='Run self-test mode on synthetic data'
    )
    
    args = parser.parse_args()
    
    if args.self_test:
        run_self_test()
        return
    
    # Validate paths
    input_dir = Path(args.input)
    output_dir = Path(args.output)
    
    if not input_dir.exists():
        logger.error(f"Input directory does not exist: {input_dir}")
        return
    
    # Run extraction
    process_dataset(input_dir, output_dir, args.max_chars)


if __name__ == '__main__':
    main()
