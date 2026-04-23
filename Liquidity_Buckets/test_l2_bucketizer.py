import pytest
import json
from pathlib import Path

from Liquidity_Buckets.l2_bucketizer import load_metadata

def test_load_metadata_file_not_found(tmp_path, monkeypatch):
    """Test that load_metadata raises FileNotFoundError when metadata file is missing."""
    # Mock VAULT_BASE to use our temporary directory
    monkeypatch.setattr('Liquidity_Buckets.l2_bucketizer.VAULT_BASE', tmp_path)

    with pytest.raises(FileNotFoundError, match="Metadata not found for BTC-USDT-SWAP"):
        load_metadata("BTC-USDT-SWAP")

def test_load_metadata_with_normalized(tmp_path, monkeypatch):
    """Test loading metadata when 'normalized' key is present."""
    monkeypatch.setattr('Liquidity_Buckets.l2_bucketizer.VAULT_BASE', tmp_path)

    # Setup mock file structure
    meta_dir = tmp_path / 'meta' / 'okx' / 'instruments'
    meta_dir.mkdir(parents=True)
    meta_file = meta_dir / 'BTC-USDT-SWAP.json'

    # Write mock data
    mock_data = {
        "normalized": {"ctVal": "0.01"},
        "raw": {"other": "data"}
    }
    meta_file.write_text(json.dumps(mock_data))

    # Call function and assert result
    result = load_metadata("BTC-USDT-SWAP")
    assert result == {"ctVal": "0.01"}

def test_load_metadata_with_raw_fallback(tmp_path, monkeypatch):
    """Test loading metadata falling back to 'raw' key when 'normalized' is missing."""
    monkeypatch.setattr('Liquidity_Buckets.l2_bucketizer.VAULT_BASE', tmp_path)

    # Setup mock file structure
    meta_dir = tmp_path / 'meta' / 'okx' / 'instruments'
    meta_dir.mkdir(parents=True)
    meta_file = meta_dir / 'BTC-USDT-SWAP.json'

    # Write mock data without 'normalized' key
    mock_data = {
        "raw": {"ctVal": "0.01", "other": "data"}
    }
    meta_file.write_text(json.dumps(mock_data))

    # Call function and assert result
    result = load_metadata("BTC-USDT-SWAP")
    assert result == {"ctVal": "0.01", "other": "data"}

def test_load_metadata_with_top_level_fallback(tmp_path, monkeypatch):
    """Test loading metadata falling back to top-level data when neither 'normalized' nor 'raw' is present."""
    monkeypatch.setattr('Liquidity_Buckets.l2_bucketizer.VAULT_BASE', tmp_path)

    # Setup mock file structure
    meta_dir = tmp_path / 'meta' / 'okx' / 'instruments'
    meta_dir.mkdir(parents=True)
    meta_file = meta_dir / 'BTC-USDT-SWAP.json'

    # Write mock data without 'normalized' or 'raw' keys
    mock_data = {
        "ctVal": "0.01",
        "instType": "SWAP"
    }
    meta_file.write_text(json.dumps(mock_data))

    # Call function and assert result
    result = load_metadata("BTC-USDT-SWAP")
    assert result == {"ctVal": "0.01", "instType": "SWAP"}
