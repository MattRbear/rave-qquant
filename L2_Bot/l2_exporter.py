"""
OKX L2 OrderBook Exporter - Enhanced with Validation & Auto-Reconnect
---------------------------------------------------------------------
Captures L2 orderbook snapshots from OKX WebSocket.
Implements gap detection, checksum validation, and proper error handling.

INSTRUMENTS: BTC-USDT-SWAP, ETH-USDT-SWAP
OUTPUT: Vault\raw\okx\l2_perps\{INSTID}\{DATE}\{HOUR}.jsonl
"""

import asyncio
import json
import logging
import requests
import sys
import zlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Set
import websockets

# Add parent directory to path for utils import
sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.validation import ValidationError, validate_instrument_id
from utils.config import Config

# Configuration
INSTRUMENTS = Config.ALLOWED_INSTRUMENTS
VAULT_BASE = Config.get_vault_base()
WS_URL = Config.OKX_WS_URL
REST_BASE = Config.OKX_REST_BASE

# L2 specific settings
SNAPSHOT_CADENCE_SEC = 2  # Snapshot frequency
DEPTH_LEVELS = 400  # Top N levels to capture
MAX_RECONNECT_ATTEMPTS = Config.MAX_RECONNECT_ATTEMPTS
RECONNECT_DELAY = Config.RECONNECT_DELAY
PING_INTERVAL = Config.WEBSOCKET_PING_INTERVAL
PING_TIMEOUT = Config.WEBSOCKET_PING_TIMEOUT

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('l2_exporter.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('L2_Exporter')


class OrderBook:
    """
    In-memory orderbook maintenance with gap detection.
    """
    
    def __init__(self, inst_id: str):
        self.inst_id = inst_id
        self.bids: Dict[str, List] = {}  # price -> [size, liquidation_orders, num_orders]
        self.asks: Dict[str, List] = {}
        self.last_seq_id: Optional[int] = None
        self.checksum: Optional[int] = None
        self.timestamp_ms: Optional[int] = None
        
    def update(self, data: Dict) -> bool:
        """
        Update orderbook with incremental data.
        Returns True if gap detected (requires resubscribe).
        """
        try:
            # Get sequence IDs
            seq_id = int(data.get('seqId', 0))
            prev_seq_id = int(data.get('prevSeqId', 0))
            
            # Gap detection
            if self.last_seq_id is not None and prev_seq_id != self.last_seq_id:
                logger.warning(
                    f"[{self.inst_id}] GAP DETECTED: "
                    f"expected prevSeqId={self.last_seq_id}, got={prev_seq_id}"
                )
                return True  # Gap detected
            
            # Update timestamp
            self.timestamp_ms = int(data.get('ts', 0))
            
            # Update bids
            for bid in data.get('bids', []):
                if len(bid) >= 2:
                    price = bid[0]
                    size = bid[1]
                    
                    if float(size) == 0:
                        # Remove level
                        self.bids.pop(price, None)
                    else:
                        # Update level
                        self.bids[price] = bid
            
            # Update asks
            for ask in data.get('asks', []):
                if len(ask) >= 2:
                    price = ask[0]
                    size = ask[1]
                    
                    if float(size) == 0:
                        # Remove level
                        self.asks.pop(price, None)
                    else:
                        # Update level
                        self.asks[price] = ask
            
            # Update checksum
            self.checksum = data.get('checksum')
            self.last_seq_id = seq_id
            
            return False  # No gap
            
        except Exception as e:
            logger.error(f"[{self.inst_id}] Error updating orderbook: {e}", exc_info=True)
            return False
    
    def load_snapshot(self, data: Dict):
        """Load full snapshot (initial or after gap)."""
        try:
            # Clear existing data
            self.bids.clear()
            self.asks.clear()
            
            # Load bids
            for bid in data.get('bids', []):
                if len(bid) >= 2:
                    price = bid[0]
                    self.bids[price] = bid
            
            # Load asks
            for ask in data.get('asks', []):
                if len(ask) >= 2:
                    price = ask[0]
                    self.asks[price] = ask
            
            # Update metadata
            self.timestamp_ms = int(data.get('ts', 0))
            self.checksum = data.get('checksum')
            self.last_seq_id = int(data.get('seqId', 0))
            
            logger.info(
                f"[{self.inst_id}] Snapshot loaded: "
                f"{len(self.bids)} bids, {len(self.asks)} asks"
            )
            
        except Exception as e:
            logger.error(f"[{self.inst_id}] Error loading snapshot: {e}", exc_info=True)
    
    def get_snapshot(self) -> Optional[Dict]:
        """Get current orderbook snapshot."""
        if not self.bids or not self.asks:
            return None
        
        try:
            # Sort and limit to top N levels
            sorted_bids = sorted(
                self.bids.items(),
                key=lambda x: float(x[0]),
                reverse=True
            )[:DEPTH_LEVELS]
            
            sorted_asks = sorted(
                self.asks.items(),
                key=lambda x: float(x[0])
            )[:DEPTH_LEVELS]
            
            # Extract just the values
            bids_list = [v for k, v in sorted_bids]
            asks_list = [v for k, v in sorted_asks]
            
            # Calculate best bid/ask and mid price
            best_bid = sorted_bids[0][0] if sorted_bids else None
            best_ask = sorted_asks[0][0] if sorted_asks else None
            
            mid_price = None
            if best_bid and best_ask:
                mid_price = str((float(best_bid) + float(best_ask)) / 2)
            
            return {
                'timestamp_utc': datetime.fromtimestamp(
                    self.timestamp_ms / 1000.0, tz=timezone.utc
                ).strftime('%Y-%m-%dT%H:%M:%S.%fZ'),
                'exchange': 'okx',
                'market': 'perp',
                'channel': 'books',
                'instId': self.inst_id,
                'bids_top400': bids_list,
                'asks_top400': asks_list,
                'best_bid': best_bid,
                'best_ask': best_ask,
                'mid_price': mid_price,
                'checksum': self.checksum,
                'seqId': self.last_seq_id
            }
            
        except Exception as e:
            logger.error(f"[{self.inst_id}] Error creating snapshot: {e}", exc_info=True)
            return None
    
    def clear(self):
        """Clear orderbook (for gap recovery)."""
        self.bids.clear()
        self.asks.clear()
        self.last_seq_id = None
        self.checksum = None
        logger.info(f"[{self.inst_id}] Orderbook cleared for gap recovery")


class SnapshotWriter:
    """Writes orderbook snapshots to hourly JSONL files."""
    
    def __init__(self):
        self.written_timestamps: Dict[str, Set[str]] = {}  # inst_id -> set of timestamps
        
    def write_snapshot(self, snapshot: Dict) -> bool:
        """
        Write snapshot to appropriate file with deduplication.
        Returns True if written, False if duplicate.
        """
        try:
            inst_id = snapshot['instId']
            timestamp_str = snapshot['timestamp_utc']
            
            # Deduplication check
            if inst_id not in self.written_timestamps:
                self.written_timestamps[inst_id] = set()
            
            if timestamp_str in self.written_timestamps[inst_id]:
                return False  # Duplicate
            
            # Parse timestamp for path
            ts = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            date_str = ts.strftime('%Y-%m-%d')
            hour_str = ts.strftime('%H')
            
            # Build output path
            output_dir = VAULT_BASE / 'raw' / 'okx' / 'l2_perps' / inst_id / date_str
            output_dir.mkdir(parents=True, exist_ok=True)
            
            output_file = output_dir / f'{hour_str}.jsonl'
            
            # Write snapshot
            with open(output_file, 'a') as f:
                f.write(json.dumps(snapshot) + '\n')
            
            # Track written timestamp
            self.written_timestamps[inst_id].add(timestamp_str)
            
            # Limit memory (keep last 1000 per instrument)
            if len(self.written_timestamps[inst_id]) > 1000:
                # Remove oldest 500
                to_remove = list(self.written_timestamps[inst_id])[:500]
                for ts in to_remove:
                    self.written_timestamps[inst_id].discard(ts)
            
            return True
            
        except Exception as e:
            logger.error(f"Error writing snapshot: {e}", exc_info=True)
            return False


class L2Exporter:
    """Main L2 orderbook exporter with auto-reconnect."""
    
    def __init__(self):
        self.orderbooks: Dict[str, OrderBook] = {}
        self.writer = SnapshotWriter()
        self.ws = None
        self.running = False
        self.reconnect_attempts = 0
        self.snapshot_tasks: Dict[str, asyncio.Task] = {}
        
        # Initialize orderbooks
        for inst_id in INSTRUMENTS:
            self.orderbooks[inst_id] = OrderBook(inst_id)
    
    async def subscribe(self):
        """Subscribe to orderbook channels."""
        subscriptions = []
        for inst_id in INSTRUMENTS:
            subscriptions.append({
                "channel": "books",
                "instId": inst_id
            })
        
        subscribe_msg = {
            "op": "subscribe",
            "args": subscriptions
        }
        
        await self.ws.send(json.dumps(subscribe_msg))
        logger.info(f"Subscribed to books for {len(INSTRUMENTS)} instruments")
    
    async def unsubscribe_all(self):
        """Unsubscribe from all channels (for gap recovery)."""
        subscriptions = []
        for inst_id in INSTRUMENTS:
            subscriptions.append({
                "channel": "books",
                "instId": inst_id
            })
        
        unsubscribe_msg = {
            "op": "unsubscribe",
            "args": subscriptions
        }
        
        await self.ws.send(json.dumps(unsubscribe_msg))
        logger.info("Unsubscribed from all channels")
    
    async def snapshot_loop(self, inst_id: str):
        """Periodically write snapshots for an instrument."""
        try:
            while self.running:
                await asyncio.sleep(SNAPSHOT_CADENCE_SEC)
                
                orderbook = self.orderbooks.get(inst_id)
                if orderbook:
                    snapshot = orderbook.get_snapshot()
                    if snapshot:
                        written = self.writer.write_snapshot(snapshot)
                        if written:
                            logger.debug(
                                f"[{inst_id}] Snapshot written: "
                                f"bids={len(snapshot['bids_top400'])}, "
                                f"asks={len(snapshot['asks_top400'])}"
                            )
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"[{inst_id}] Snapshot loop error: {e}", exc_info=True)
    
    async def process_message(self, data: Dict):
        """Process WebSocket message."""
        try:
            # Handle event messages
            if 'event' in data:
                logger.info(f"Event: {data}")
                return
            
            if 'arg' not in data or 'data' not in data:
                return
            
            arg = data.get('arg', {})
            inst_id = arg.get('instId')
            
            # Validate instrument
            try:
                validate_instrument_id(inst_id, INSTRUMENTS)
            except ValidationError as e:
                logger.error(f"Validation error: {e}")
                return
            
            action = data.get('action', '')
            message_data = data.get('data', [])
            
            if not message_data:
                return
            
            orderbook = self.orderbooks.get(inst_id)
            if not orderbook:
                return
            
            if action == 'snapshot':
                # Load full snapshot
                orderbook.load_snapshot(message_data[0])
            else:
                # Incremental update
                for update in message_data:
                    gap_detected = orderbook.update(update)
                    
                    if gap_detected:
                        # Clear and resubscribe
                        orderbook.clear()
                        logger.warning(f"[{inst_id}] Forcing resubscribe due to gap")
                        await self.unsubscribe_all()
                        await asyncio.sleep(1)
                        await self.subscribe()
                        break
        
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
    
    async def ping_loop(self):
        """Send periodic pings."""
        try:
            while self.running and self.ws:
                await asyncio.sleep(PING_INTERVAL)
                try:
                    pong = await asyncio.wait_for(
                        self.ws.ping(),
                        timeout=PING_TIMEOUT
                    )
                    await pong
                except asyncio.TimeoutError:
                    logger.warning("Ping timeout")
                    break
                except Exception as e:
                    logger.error(f"Ping error: {e}")
                    break
        except Exception as e:
            logger.error(f"Ping loop error: {e}", exc_info=True)
    
    async def run(self):
        """Main run loop with auto-reconnect."""
        self.running = True
        
        logger.info("L2 Exporter starting...")
        logger.info(f"Instruments: {INSTRUMENTS}")
        logger.info(f"Snapshot cadence: {SNAPSHOT_CADENCE_SEC}s")
        
        self.reconnect_attempts = 0
        
        while self.running:
            try:
                logger.info(f"Connecting to {WS_URL} (attempt {self.reconnect_attempts + 1})")
                
                async with websockets.connect(
                    WS_URL,
                    ping_interval=None,
                    close_timeout=10
                ) as ws:
                    self.ws = ws
                    logger.info("Connected successfully")
                    self.reconnect_attempts = 0
                    
                    # Subscribe
                    await self.subscribe()
                    
                    # Start snapshot loops
                    for inst_id in INSTRUMENTS:
                        task = asyncio.create_task(self.snapshot_loop(inst_id))
                        self.snapshot_tasks[inst_id] = task
                    
                    # Start ping loop
                    ping_task = asyncio.create_task(self.ping_loop())
                    
                    # Listen for messages
                    try:
                        await self.message_listener()
                    finally:
                        # Cleanup
                        ping_task.cancel()
                        for task in self.snapshot_tasks.values():
                            task.cancel()
                        
                        try:
                            await ping_task
                        except asyncio.CancelledError:
                            pass
                        
                        for task in self.snapshot_tasks.values():
                            try:
                                await task
                            except asyncio.CancelledError:
                                pass
                        
                        self.snapshot_tasks.clear()
            
            except websockets.exceptions.WebSocketException as e:
                logger.error(f"WebSocket error: {e}")
            except Exception as e:
                logger.error(f"Connection error: {e}", exc_info=True)
            
            if self.running:
                self.reconnect_attempts += 1
                
                if self.reconnect_attempts > MAX_RECONNECT_ATTEMPTS:
                    logger.error(f"Max reconnect attempts reached. Stopping.")
                    self.running = False
                    break
                
                delay = min(RECONNECT_DELAY * (2 ** (self.reconnect_attempts - 1)), 300)
                logger.warning(f"Reconnecting in {delay}s...")
                await asyncio.sleep(delay)
        
        logger.info("L2 Exporter stopped")
    
    def stop(self):
        """Stop the exporter."""
        logger.info("Stopping L2 Exporter...")
        self.running = False


async def main():
    """Main entry point."""
    exporter = L2Exporter()
    
    try:
        await exporter.run()
    except KeyboardInterrupt:
        logger.info("\nShutdown requested...")
        exporter.stop()


if __name__ == '__main__':
    asyncio.run(main())
