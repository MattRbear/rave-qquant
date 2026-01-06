"""
OKX Trades Exporter - PERPS Only
---------------------------------
Captures raw perpetual swap trades from OKX WebSocket.
Writes append-only JSONL with full contract metadata.

INSTRUMENTS: BTC-USDT-SWAP, ETH-USDT-SWAP ONLY
OUTPUT: Vault\raw\okx\trades_perps\{INSTID}\{DATE}.jsonl
"""

import asyncio
import json
import logging
import requests
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Set
import websockets

# Configuration
INSTRUMENTS = ["BTC-USDT-SWAP", "ETH-USDT-SWAP"]
VAULT_BASE = Path(r"C:\Users\M.R Bear\Documents\RaveQuant\Rave_Quant_Vault")
WS_URL = "wss://ws.okx.com:8443/ws/v5/public"
REST_BASE = "https://www.okx.com"

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('trades_exporter.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('Trades_Exporter')


class InstrumentMetadata:
    """Manages instrument contract metadata."""
    
    def __init__(self):
        self.metadata: Dict[str, Dict] = {}
    
    def fetch_metadata(self, inst_id: str) -> bool:
        """Fetch and cache instrument metadata from OKX REST API."""
        try:
            url = f"{REST_BASE}/api/v5/public/instruments"
            params = {
                'instType': 'SWAP',
                'instId': inst_id
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            if data.get('code') != '0':
                logger.error(f"[{inst_id}] API error: {data}")
                return False
            
            instruments = data.get('data', [])
            if not instruments:
                logger.error(f"[{inst_id}] No instrument data returned")
                return False
            
            raw_data = instruments[0]
            
            # Validate required fields
            required_fields = ['ctVal', 'ctMult', 'ctType']
            missing = [f for f in required_fields if f not in raw_data]
            
            if missing:
                logger.error(f"BUILD_FAIL: [{inst_id}] Missing required metadata fields: {missing}")
                logger.error(f"Available fields: {list(raw_data.keys())}")
                return False
            
            # Build normalized metadata
            normalized = {
                'ctVal': str(raw_data['ctVal']),
                'ctMult': str(raw_data['ctMult']),
                'ctType': str(raw_data['ctType']),
                'tickSz': str(raw_data.get('tickSz', '')),
                'lotSz': str(raw_data.get('lotSz', ''))
            }
            
            # Store full metadata with normalized block
            self.metadata[inst_id] = {
                'instId': inst_id,
                'raw': raw_data,
                'normalized': normalized
            }
            
            # Save to vault
            meta_dir = VAULT_BASE / 'meta' / 'okx' / 'instruments'
            meta_dir.mkdir(parents=True, exist_ok=True)
            
            meta_file = meta_dir / f"{inst_id}.json"
            with open(meta_file, 'w') as f:
                json.dump(self.metadata[inst_id], f, indent=2)
            
            logger.info(f"[{inst_id}] Metadata fetched and saved: ctVal={normalized['ctVal']}, ctMult={normalized['ctMult']}")
            return True
            
        except Exception as e:
            logger.error(f"[{inst_id}] Metadata fetch failed: {e}", exc_info=True)
            return False
    
    def get_contract_params(self, inst_id: str) -> Dict[str, str]:
        """Get contract conversion parameters."""
        if inst_id not in self.metadata:
            logger.error(f"BUILD_FAIL: No metadata for {inst_id}")
            raise ValueError(f"Missing metadata for {inst_id}")
        
        return self.metadata[inst_id]['normalized']



class TradesWriter:
    """Writes trades to daily-rotated JSONL files with deduplication."""
    
    def __init__(self, metadata_manager: InstrumentMetadata):
        self.metadata = metadata_manager
        self.seen_trades: Dict[str, Set[str]] = {}  # inst_id -> set of trade_ids
        self.trades_written = 0
        self.trades_skipped = 0
    
    def _get_output_path(self, inst_id: str, timestamp_utc: datetime) -> Path:
        """Get output file path for trade."""
        date_str = timestamp_utc.strftime('%Y-%m-%d')
        
        output_dir = VAULT_BASE / 'raw' / 'okx' / 'trades_perps' / inst_id
        output_dir.mkdir(parents=True, exist_ok=True)
        
        return output_dir / f"{date_str}.jsonl"
    
    def _make_dedup_key(self, exchange: str, inst_id: str, trade_id: str) -> str:
        """Create deduplication key."""
        return f"{exchange}:{inst_id}:{trade_id}"
    
    def write_trade(self, inst_id: str, trade_data: Dict) -> bool:
        """
        Write trade to JSONL file with deduplication.
        Returns True if written, False if duplicate.
        """
        try:
            # Validate instrument
            if inst_id not in INSTRUMENTS:
                logger.error(f"BUILD_FAIL: Invalid instId: {inst_id} (allowed: {INSTRUMENTS})")
                raise ValueError(f"Invalid instId: {inst_id}")
            
            # Parse timestamp (event time from OKX)
            ts_ms = int(trade_data.get('ts', 0))
            if not ts_ms:
                logger.error(f"[{inst_id}] Missing timestamp")
                return False
            
            timestamp_utc = datetime.fromtimestamp(ts_ms / 1000.0, tz=timezone.utc)
            timestamp_str = timestamp_utc.strftime('%Y-%m-%dT%H:%M:%S.%fZ')
            
            # Extract trade fields
            trade_id = str(trade_data.get('tradeId', ''))
            if not trade_id:
                logger.error(f"[{inst_id}] Missing trade_id")
                return False
            
            # Deduplication check
            dedup_key = self._make_dedup_key('okx', inst_id, trade_id)
            
            if inst_id not in self.seen_trades:
                self.seen_trades[inst_id] = set()
            
            if dedup_key in self.seen_trades[inst_id]:
                self.trades_skipped += 1
                return False  # Duplicate
            
            # Get contract metadata
            try:
                contract_params = self.metadata.get_contract_params(inst_id)
            except ValueError as e:
                logger.error(str(e))
                return False
            
            # Derive canonical symbol (BTC-USDT-SWAP -> BTC/USDT)
            symbol_canon = inst_id.replace('-USDT-SWAP', '/USDT')
            
            # Build trade record
            trade_record = {
                'timestamp_utc': timestamp_str,
                'exchange': 'okx',
                'market': 'perp',
                'instId': inst_id,
                'symbol_canon': symbol_canon,
                'trade_id': trade_id,
                'side': str(trade_data.get('side', '')),
                'price': str(trade_data.get('px', '')),
                'qty_contracts': str(trade_data.get('sz', '')),
                'ctVal': contract_params['ctVal'],
                'ctMult': contract_params['ctMult'],
                'ctType': contract_params['ctType']
            }
            
            # Validate required fields
            required = ['timestamp_utc', 'instId', 'trade_id', 'side', 'price', 'qty_contracts']
            missing = [f for f in required if not trade_record.get(f)]
            
            if missing:
                logger.error(f"BUILD_FAIL: [{inst_id}] Missing required fields: {missing}")
                return False
            
            # Write to JSONL
            output_path = self._get_output_path(inst_id, timestamp_utc)
            
            with open(output_path, 'a') as f:
                f.write(json.dumps(trade_record) + '\n')
            
            # Track written trade
            self.seen_trades[inst_id].add(dedup_key)
            self.trades_written += 1
            
            # Limit memory (keep last 10k per instrument)
            if len(self.seen_trades[inst_id]) > 10000:
                # Remove oldest 5k
                to_remove = list(self.seen_trades[inst_id])[:5000]
                for key in to_remove:
                    self.seen_trades[inst_id].discard(key)
            
            return True
            
        except Exception as e:
            logger.error(f"[{inst_id}] Trade write failed: {e}", exc_info=True)
            return False



class TradesExporter:
    """Main trades exporter."""
    
    def __init__(self):
        self.metadata = InstrumentMetadata()
        self.writer = None  # Initialize after metadata fetch
        self.ws = None
        self.running = False
    
    async def subscribe(self):
        """Subscribe to trades channels."""
        subscriptions = []
        for inst_id in INSTRUMENTS:
            subscriptions.append({
                "channel": "trades",
                "instId": inst_id
            })
        
        subscribe_msg = {
            "op": "subscribe",
            "args": subscriptions
        }
        
        await self.ws.send(json.dumps(subscribe_msg))
        logger.info(f"Subscribed to trades for {len(INSTRUMENTS)} instruments")
    
    def validate_message(self, data: Dict) -> bool:
        """Validate required fields are present."""
        if 'arg' not in data or 'data' not in data:
            return True  # Event message
        
        message_data = data.get('data', [])
        if not message_data:
            return True
        
        first_item = message_data[0]
        
        # REQUIRED fields
        required = ['ts', 'tradeId', 'px', 'sz', 'side']
        missing = [f for f in required if f not in first_item]
        
        if missing:
            logger.error(f"BUILD_FAIL: Missing required trade fields: {missing}")
            logger.error(f"Full message: {json.dumps(data, indent=2)}")
            return False
        
        return True
    
    async def process_message(self, data: Dict):
        """Process WebSocket message."""
        try:
            # Handle event messages
            if 'event' in data:
                logger.info(f"Event: {data}")
                return
            
            # Validate message structure
            if not self.validate_message(data):
                logger.error("Stopping due to schema validation failure")
                self.running = False
                return
            
            if 'arg' not in data or 'data' not in data:
                return
            
            arg = data.get('arg', {})
            inst_id = arg.get('instId')
            
            # Validate instrument
            if inst_id not in INSTRUMENTS:
                logger.error(f"BUILD_FAIL: Unexpected instId: {inst_id} (allowed: {INSTRUMENTS})")
                self.running = False
                return
            
            message_data = data.get('data', [])
            
            for trade_data in message_data:
                self.writer.write_trade(inst_id, trade_data)
        
        except Exception as e:
            logger.error(f"Error processing message: {e}", exc_info=True)
    
    async def message_listener(self):
        """Listen to WebSocket messages."""
        try:
            async for message in self.ws:
                if message == "pong":
                    continue
                
                try:
                    data = json.loads(message)
                    await self.process_message(data)
                except json.JSONDecodeError:
                    logger.error(f"Failed to decode message: {message}")
        
        except websockets.exceptions.ConnectionClosed:
            logger.warning("WebSocket connection closed")
        except Exception as e:
            logger.error(f"Error in message listener: {e}", exc_info=True)
    
    async def run(self):
        """Main run loop with auto-reconnect."""
        self.running = True
        
        logger.info("Trades Exporter starting...")
        logger.info(f"Instruments: {INSTRUMENTS}")
        
        # Fetch instrument metadata
        logger.info("Fetching instrument metadata...")
        for inst_id in INSTRUMENTS:
            success = self.metadata.fetch_metadata(inst_id)
            if not success:
                logger.error(f"BUILD_FAIL: Failed to fetch metadata for {inst_id}")
                return
        
        # Initialize writer after metadata loaded
        self.writer = TradesWriter(self.metadata)
        logger.info("Metadata loaded successfully")
        
        while self.running:
            try:
                logger.info(f"Connecting to {WS_URL}")
                async with websockets.connect(WS_URL) as ws:
                    self.ws = ws
                    logger.info("Connected successfully")
                    
                    # Subscribe to trades
                    await self.subscribe()
                    
                    # Listen for messages
                    await self.message_listener()
            
            except Exception as e:
                logger.error(f"Connection error: {e}", exc_info=True)
            
            if self.running:
                logger.warning("Reconnecting in 5s...")
                await asyncio.sleep(5)
        
        logger.info("Trades Exporter stopped")
        logger.info(f"Stats: {self.writer.trades_written} written, {self.writer.trades_skipped} skipped (duplicates)")
    
    def stop(self):
        """Stop the exporter."""
        logger.info("Stopping Trades Exporter...")
        self.running = False


async def main():
    """Main entry point."""
    exporter = TradesExporter()
    
    try:
        await exporter.run()
    except KeyboardInterrupt:
        logger.info("\nShutdown requested...")
        exporter.stop()


if __name__ == '__main__':
    asyncio.run(main())
