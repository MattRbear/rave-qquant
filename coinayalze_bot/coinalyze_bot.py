"""
Coinalyze Data Bot - Adversarial Market Intelligence (Enhanced)
---------------------------------------------------------------
Fetches: OI, Liquidations, Funding, Bull/Bear Ratio
Targets: BTC, ETH only
Storage: Append-only vault/inbox architecture

ENHANCEMENTS:
- Improved rate limiting with SlidingWindowRateLimiter
- Retry logic with exponential backoff
- Input validation on API responses
- Better error handling and recovery
- Timeout handling for all requests
"""

import os
import time
import json
import requests
import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

# Add parent directory to path for utils import
sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.validation import ValidationError, validate_positive_int
from utils.rate_limiter import SlidingWindowRateLimiter, retry_with_backoff
from utils.config import Config

# Logging configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('coinalyze_bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('Coinalyze_Bot')


class CoinalyzeBot:
    """
    Coinalyze market data fetcher with enhanced error handling.
    Tracks OI, liquidations, funding, and bull/bear ratio for BTC & ETH.
    """
    
    # API Configuration
    BASE_URL = Config.COINALYZE_BASE_URL
    
    # Symbols - using aggregated perpetual contracts
    # Format: {COIN}USDT_PERP.A (A = aggregated across exchanges)
    SYMBOLS = {
        'BTC': 'BTCUSDT_PERP.A',
        'ETH': 'ETHUSDT_PERP.A'
    }
    
    # Data intervals
    INTERVAL_1MIN = "1min"
    INTERVAL_5MIN = "5min"
    
    def __init__(self, api_key: str, vault_base_path: Optional[str] = None):
        """
        Initialize Coinalyze bot.
        
        Args:
            api_key: Coinalyze API key
            vault_base_path: Base path for vault storage (optional, uses config default)
        """
        if not api_key:
            raise ValueError("API key cannot be empty")
        
        self.api_key = api_key
        
        # Use config path if not specified
        if vault_base_path:
            self.vault_base = Path(vault_base_path)
        else:
            self.vault_base = Config.get_vault_base()
        
        # Create inbox directories
        self.inbox_paths = {
            'oi': self.vault_base / 'inbox' / 'coinalyze_oi',
            'funding': self.vault_base / 'inbox' / 'coinalyze_funding',
            'liqs': self.vault_base / 'inbox' / 'coinalyze_liqs',
            'bullbear': self.vault_base / 'inbox' / 'coinalyze_bullbear'
        }
        
        for path in self.inbox_paths.values():
            path.mkdir(parents=True, exist_ok=True)
        
        # Enhanced rate limiting with sliding window
        self.rate_limiter = SlidingWindowRateLimiter(
            max_calls=Config.COINALYZE_RATE_LIMIT,
            time_window=Config.COINALYZE_RATE_WINDOW,
            min_interval=1.0  # At least 1 second between calls
        )
        
        # Health tracking
        self.stats = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'rate_limit_hits': 0,
            'validation_errors': 0,
            'network_errors': 0,
            'last_fetch_time': None
        }
    
    def _make_request(self, endpoint: str, params: Dict) -> Optional[Dict]:
        """
        Make API request with rate limiting, retries, and error handling.
        
        Args:
            endpoint: API endpoint (e.g., '/open-interest-history')
            params: Query parameters
            
        Returns:
            JSON response or None on failure
        """
        # Acquire rate limit permission (blocking)
        if not self.rate_limiter.acquire(blocking=True, timeout=60):
            logger.error("Failed to acquire rate limit permission within 60s")
            self.stats['rate_limit_hits'] += 1
            return None
        
        # Add API key to params
        params['api_key'] = self.api_key
        
        url = f"{self.BASE_URL}{endpoint}"
        
        def make_single_request():
            self.stats['total_requests'] += 1
            response = requests.get(url, params=params, timeout=Config.REQUEST_TIMEOUT)
            response.raise_for_status()
            return response.json()
        
        try:
            # Use retry logic with exponential backoff
            data = retry_with_backoff(
                make_single_request,
                max_retries=3,
                initial_delay=1.0,
                max_delay=30.0,
                exceptions=(requests.RequestException,),
                logger_func=logger.warning
            )
            
            # Validate response
            if not isinstance(data, (list, dict)):
                logger.error(f"Invalid response type: {type(data)}")
                self.stats['validation_errors'] += 1
                return None
            
            self.stats['successful_requests'] += 1
            return data
            
        except requests.Timeout:
            logger.error(f"Request timeout after {Config.REQUEST_TIMEOUT}s: {endpoint}")
            self.stats['failed_requests'] += 1
            self.stats['network_errors'] += 1
            return None
            
        except requests.HTTPError as e:
            if e.response is not None and e.response.status_code == 429:
                # Rate limit hit despite our checks
                retry_after = e.response.headers.get('Retry-After', 60)
                logger.error(f"API rate limit hit. Retry after {retry_after}s")
                self.stats['rate_limit_hits'] += 1
                time.sleep(int(retry_after))
            else:
                logger.error(f"HTTP error: {e}")
            
            self.stats['failed_requests'] += 1
            return None
            
        except requests.RequestException as e:
            logger.error(f"Network error: {e}")
            self.stats['failed_requests'] += 1
            self.stats['network_errors'] += 1
            return None
            
        except Exception as e:
            logger.error(f"Unexpected error in request: {e}", exc_info=True)
            self.stats['failed_requests'] += 1
            return None
    
    def _save_to_inbox(self, data_type: str, symbol: str, data: List[Dict]):
        """
        Save data to appropriate inbox folder (append-only) with validation.
        
        Args:
            data_type: 'oi', 'funding', 'liqs', or 'bullbear'
            symbol: Asset symbol (BTC or ETH)
            data: List of data points
        """
        if not data:
            return
        
        # Validate data_type
        if data_type not in self.inbox_paths:
            logger.error(f"Invalid data_type: {data_type}")
            return
        
        # Validate symbol
        if symbol not in ['BTC', 'ETH']:
            logger.error(f"Invalid symbol: {symbol}")
            return
        
        inbox_path = self.inbox_paths[data_type]
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{symbol}_{data_type}_{timestamp}.jsonl"
        filepath = inbox_path / filename
        
        try:
            # Write as JSON Lines (one JSON object per line)
            with open(filepath, 'a') as f:
                for item in data:
                    # Basic validation
                    if not isinstance(item, dict):
                        logger.warning(f"Skipping non-dict item: {item}")
                        continue
                    
                    f.write(json.dumps(item) + '\n')
            
            logger.info(f"Saved {len(data)} {data_type} records for {symbol} to {filename}")
            
        except IOError as e:
            logger.error(f"Failed to write to {filepath}: {e}")
        except Exception as e:
            logger.error(f"Error saving data: {e}", exc_info=True)
    
    def fetch_open_interest(self, symbol: str, interval: str = "1min", 
                           lookback_minutes: int = 60) -> Optional[List[Dict]]:
        """
        Fetch Open Interest history with validation.
        
        Args:
            symbol: 'BTC' or 'ETH'
            interval: Time interval (default: 1min)
            lookback_minutes: How far back to fetch
        """
        # Validate inputs
        if symbol not in self.SYMBOLS:
            logger.error(f"Invalid symbol: {symbol}. Allowed: {list(self.SYMBOLS.keys())}")
            return None
        
        try:
            validate_positive_int(lookback_minutes, "lookback_minutes")
        except ValidationError as e:
            logger.error(f"Validation error: {e}")
            return None
        
        symbol_code = self.SYMBOLS[symbol]
        
        now = int(time.time())
        from_ts = now - (lookback_minutes * 60)
        
        params = {
            'symbols': symbol_code,
            'interval': interval,
            'from': from_ts,
            'to': now,
            'convert_to_usd': 'true'
        }
        
        response = self._make_request('/open-interest-history', params)
        
        if response:
            try:
                # Validate response structure
                if not isinstance(response, list):
                    logger.error(f"Expected list response, got {type(response)}")
                    return None
                
                # Extract data from response
                for item in response:
                    if not isinstance(item, dict):
                        logger.warning(f"Skipping invalid item: {item}")
                        continue
                    
                    if item.get('symbol') == symbol_code:
                        history = item.get('history', [])
                        
                        if not isinstance(history, list):
                            logger.error(f"Invalid history type: {type(history)}")
                            return None
                        
                        self._save_to_inbox('oi', symbol, history)
                        return history
                
                logger.warning(f"No data found for symbol {symbol_code}")
                return None
                
            except Exception as e:
                logger.error(f"Error processing response: {e}", exc_info=True)
                return None
        
        return None
    
    def fetch_liquidations(self, symbol: str, interval: str = "1min",
                          lookback_minutes: int = 60) -> Optional[List[Dict]]:
        """
        Fetch Liquidation history.
        
        Args:
            symbol: 'BTC' or 'ETH'
            interval: Time interval (default: 1min)
            lookback_minutes: How far back to fetch
        """
        symbol_code = self.SYMBOLS.get(symbol)
        if not symbol_code:
            logger.error(f"Invalid symbol: {symbol}")
            return None
        
        now = int(time.time())
        from_ts = now - (lookback_minutes * 60)
        
        params = {
            'symbols': symbol_code,
            'interval': interval,
            'from': from_ts,
            'to': now,
            'convert_to_usd': 'true'
        }
        
        response = self._make_request('/liquidation-history', params)
        
        if response:
            for item in response:
                if item['symbol'] == symbol_code:
                    history = item.get('history', [])
                    self._save_to_inbox('liqs', symbol, history)
                    return history
        
        return None
    
    def fetch_funding_rate(self, symbol: str, interval: str = "1min",
                          lookback_minutes: int = 60) -> Optional[List[Dict]]:
        """
        Fetch Funding Rate history.
        
        Args:
            symbol: 'BTC' or 'ETH'
            interval: Time interval (default: 1min)
            lookback_minutes: How far back to fetch
        """
        symbol_code = self.SYMBOLS.get(symbol)
        if not symbol_code:
            logger.error(f"Invalid symbol: {symbol}")
            return None
        
        now = int(time.time())
        from_ts = now - (lookback_minutes * 60)
        
        params = {
            'symbols': symbol_code,
            'interval': interval,
            'from': from_ts,
            'to': now
        }
        
        response = self._make_request('/funding-rate-history', params)
        
        if response:
            for item in response:
                if item['symbol'] == symbol_code:
                    history = item.get('history', [])
                    self._save_to_inbox('funding', symbol, history)
                    return history
        
        return None
    
    def fetch_bull_bear_ratio(self, symbol: str, interval: str = "1min",
                             lookback_minutes: int = 60) -> Optional[List[Dict]]:
        """
        Fetch Long/Short Ratio (Bull/Bear) history.
        
        Args:
            symbol: 'BTC' or 'ETH'
            interval: Time interval (default: 1min)
            lookback_minutes: How far back to fetch
        """
        symbol_code = self.SYMBOLS.get(symbol)
        if not symbol_code:
            logger.error(f"Invalid symbol: {symbol}")
            return None
        
        now = int(time.time())
        from_ts = now - (lookback_minutes * 60)
        
        params = {
            'symbols': symbol_code,
            'interval': interval,
            'from': from_ts,
            'to': now
        }
        
        response = self._make_request('/long-short-ratio-history', params)
        
        if response:
            for item in response:
                if item['symbol'] == symbol_code:
                    history = item.get('history', [])
                    self._save_to_inbox('bullbear', symbol, history)
                    return history
        
        return None
    
    def fetch_all_data(self, lookback_minutes: int = 60):
        """
        Fetch all data types for all symbols.
        
        Args:
            lookback_minutes: How far back to fetch (default: 60 min)
        """
        logger.info(f"Fetching all data (lookback: {lookback_minutes} min)")
        
        for symbol in ['BTC', 'ETH']:
            logger.info(f"\n{'='*60}")
            logger.info(f"Fetching data for {symbol}")
            logger.info(f"{'='*60}")
            
            # Open Interest (1min)
            logger.info(f"Fetching Open Interest...")
            self.fetch_open_interest(symbol, interval="1min", 
                                    lookback_minutes=lookback_minutes)
            
            # Liquidations (1min)
            logger.info(f"Fetching Liquidations...")
            self.fetch_liquidations(symbol, interval="1min",
                                   lookback_minutes=lookback_minutes)
            
            # Funding Rate (1min)
            logger.info(f"Fetching Funding Rate...")
            self.fetch_funding_rate(symbol, interval="1min",
                                   lookback_minutes=lookback_minutes)
            
            # Bull/Bear Ratio (1min)
            logger.info(f"Fetching Bull/Bear Ratio...")
            self.fetch_bull_bear_ratio(symbol, interval="1min",
                                      lookback_minutes=lookback_minutes)
        
        self.stats['last_fetch_time'] = datetime.now()
        logger.info(f"\n{'='*60}")
        logger.info("Fetch cycle complete")
        logger.info(f"{'='*60}\n")
    
    def get_stats(self) -> Dict:
        """Get bot statistics including rate limiter status."""
        usage = self.rate_limiter.get_usage()
        return {
            **self.stats,
            'rate_limit_usage': f"{usage[0]}/{usage[1]} in window"
        }
    
    def print_stats(self):
        """Print statistics."""
        stats = self.get_stats()
        print("\n" + "="*60)
        print("COINALYZE BOT STATS")
        print("="*60)
        for key, value in stats.items():
            print(f"{key}: {value}")
        print("="*60 + "\n")


def load_api_key() -> Optional[str]:
    """Load API key from environment or env file."""
    # Try environment variable first
    api_key = os.getenv('COINALYZE_API_KEY')
    
    if not api_key:
        # Try loading from env file
        env_file = Path(__file__).parent.parent.parent.parent / 'OneDrive' / 'Desktop' / 'all env.txt'
        if env_file.exists():
            with open(env_file, 'r') as f:
                for line in f:
                    if line.startswith('COINALYZE_API_KEY='):
                        api_key = line.split('=')[1].strip()
                        break
    
    return api_key


if __name__ == "__main__":
    print("\n" + "="*60)
    print("COINALYZE DATA BOT - ADVERSARIAL INTELLIGENCE")
    print("="*60)
    print("Tracking: OI, Liquidations, Funding, Bull/Bear")
    print("Symbols: BTC, ETH")
    print("Interval: 1min")
    print("="*60 + "\n")
    
    # Load API key
    api_key = load_api_key()
    if not api_key:
        logger.error("COINALYZE_API_KEY not found!")
        logger.error("Set environment variable or add to all env.txt")
        exit(1)
    
    # Initialize bot
    bot = CoinalyzeBot(api_key=api_key)
    
    # Fetch mode
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == '--once':
        # Single fetch
        logger.info("Running single fetch...")
        bot.fetch_all_data(lookback_minutes=60)
        bot.print_stats()
    else:
        # Continuous mode
        logger.info("Running continuous mode (Ctrl+C to stop)")
        logger.info("Fetch interval: 1 minute\n")
        
        try:
            while True:
                bot.fetch_all_data(lookback_minutes=5)  # Only fetch last 5min to avoid duplicates
                bot.print_stats()
                
                logger.info("Sleeping 60 seconds until next fetch...")
                time.sleep(60)
                
        except KeyboardInterrupt:
            logger.info("\n\nShutdown requested...")
            bot.print_stats()
            logger.info("Bot stopped.\n")
