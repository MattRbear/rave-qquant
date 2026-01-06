# Nova Chat Extractor

Incrementally processes massive chat history datasets (~800M+ characters) and extracts topic-filtered conversations into chunked JSON files.

## Features

- **Memory-efficient streaming**: Processes files incrementally, never loads entire dataset into RAM
- **Multi-format support**: Handles .json, .jsonl, .txt, .md, .html files
- **Topic filtering**: Extracts only conversations related to specific topics
- **Chunked output**: Produces multiple valid JSON files, each ≤5MB
- **Deterministic**: Same input always produces same output
- **Robust error handling**: Gracefully handles encoding issues and malformed files
- **Progress tracking**: Logs progress and generates detailed manifest

## Requirements

- Python 3.12+
- Windows (PowerShell)
- Standard library only (no external dependencies)

## Installation

No installation needed. Just ensure Python 3.12+ is installed:

```powershell
python --version
```

## Usage

### Basic Extraction

```powershell
python extract_nova_chat.py --input "C:\Users\M.R Bear\Desktop\chat" --output "C:\Users\M.R Bear\Documents\NOVA-Chat"
```

### Custom Chunk Size

```powershell
python extract_nova_chat.py --input "C:\Users\M.R Bear\Desktop\chat" --output "C:\Users\M.R Bear\Documents\NOVA-Chat" --max-chars 3000000
```

### Self-Test Mode

Verify the script works on synthetic data before processing your real dataset:

```powershell
python extract_nova_chat.py --self-test
```

This creates temporary test data, processes it, verifies output, and cleans up.

## Filtered Topics

The script extracts conversations related to:

- **Trading**: Market analysis, strategies, technical analysis
- **Stocks**: Equities, options, tickers
- **OSRS**: Old School RuneScape
- **Bot Ideas**: Automation, algorithms, systems
- **Career**: Job, work, employment
- **TKL**: Guitar case manufacturing
- **Friends**: Social connections
- **PC**: Computer hardware, gaming rigs
- **RaveBear**: User's identity/brand
- **Raving**: EDM festivals, concerts
- **Music**: Songs, artists, playlists
- **Depression**: Mental health, therapy
- **ADHD**: Focus, attention, medication
- **Goals**: Targets, milestones, ambitions
- **Strats**: Strategies, tactics, frameworks
- **Nova**: AI assistants, Claude, LLMs
- **Personal Life**: Family, home, relationships

## Output Structure

### Chunked Files

```
C:\Users\M.R Bear\Documents\NOVA-Chat\
├── nova_chat_0001.json    (≤5MB, valid JSON array)
├── nova_chat_0002.json    (≤5MB, valid JSON array)
├── nova_chat_0003.json    (≤5MB, valid JSON array)
└── manifest.json          (metadata and statistics)
```

### Record Format

Each record in the JSON files contains:

```json
{
  "record_id": "a1b2c3d4e5f6g7h8",
  "source_file": "chat/2023/conversation_123.json",
  "detected_format": "openai_export_json",
  "conversation_id": "conv_abc123",
  "message_index": 5,
  "role": "user",
  "timestamp": "2023-05-15T14:30:00Z",
  "text": "I want to discuss trading strategies...",
  "topics": ["trading", "strats", "goals"],
  "match_score": 1.5
}
```

### Manifest Format

```json
{
  "extraction_date": "2025-12-15T12:00:00",
  "input_directory": "C:\\Users\\M.R Bear\\Desktop\\chat",
  "output_directory": "C:\\Users\\M.R Bear\\Documents\\NOVA-Chat",
  "total_files_scanned": 1250,
  "total_records_kept": 45000,
  "total_records_dropped": 155000,
  "topic_counts": {
    "trading": 12000,
    "goals": 8000,
    "depression": 5000
  },
  "output_chunks": [
    {
      "filename": "nova_chat_0001.json",
      "record_count": 450,
      "char_size": 4950000
    }
  ],
  "failed_files": []
}
```

## Performance

- **Memory usage**: ~50-100MB (constant, regardless of dataset size)
- **Speed**: ~1-5 minutes per 100MB of input (depends on CPU)
- **Disk I/O**: Sequential reads, atomic writes

## Troubleshooting

### "No output files created"

- Check that input directory exists
- Verify input files contain text matching topics
- Run with `--self-test` to verify script works

### "Encoding errors"

Script automatically tries multiple encodings (UTF-8, UTF-16, Latin-1, CP1252) and uses `errors='replace'` as fallback.

### "Out of memory"

This should never happen due to streaming architecture. If it does, reduce `--max-chars` value.

## Customization

### Add/Remove Topics

Edit the `TOPICS` dictionary in `extract_nova_chat.py`:

```python
TOPICS = {
    'my_topic': ['keyword1', 'keyword2', 'keyword3']
}
```

### Adjust Match Threshold

Modify the topic matching condition in `process_dataset()`:

```python
if topics and score > 0.5:  # Increase threshold
    # Keep record
```

## Quick Start

1. **Run self-test first:**
```powershell
python extract_nova_chat.py --self-test
```

2. **If self-test passes, run on real data:**
```powershell
python extract_nova_chat.py --input "C:\Users\M.R Bear\Desktop\chat" --output "C:\Users\M.R Bear\Documents\NOVA-Chat"
```

3. **Check results:**
```powershell
cd "C:\Users\M.R Bear\Documents\NOVA-Chat"
dir
type manifest.json
```

## License

MIT License - Free to use and modify

## Notes

- Processing ~800MB may take 5-15 minutes
- Watch the console for progress updates
- Manifest shows exactly what was kept/dropped
- All output files are valid standalone JSON
- Can be interrupted and rerun (idempotent)
