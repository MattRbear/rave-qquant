"""
Coinalyze Data Bot - Adversarial Market Intelligence
Fetches: OI, Liquidations, Funding, Bull/Bear Ratio
Targets: BTC, ETH only
Storage: Append-only vault/inbox architecture
"""

import os
import time
import json
import requests
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

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
    Coinalyze market data fetcher.
    Tracks OI, liquidations, funding, and bull/bear ratio for BTC & ETH.
    """
    
    # API Configuration
    BASE_URL = "https://api.coinalyze.net"
    RATE_LIMIT = 40  # calls per minute
    RATE_WINDOW = 60  # seconds
    
    # Symbols - using aggregated perpetual contracts
    # Format: {COIN}USDT_PERP.A (A = aggregated across exchanges)
    SYMBOLS = {
        'BTC': 'BTCUSDT_PERP.A',
        'ETH': 'ETHUSDT_PERP.A'
    }
    
    # Data intervals
    INTERVAL_1MIN = "1min"
    INTERVAL_5MIN = "5min"
    
    def __init__(self, api_key: str, vault_base_path: str = r"C:\Users\M.R Bear\Documents\RaveQuant\Rave_Quant_Vault"):
        """
        Initialize Coinalyze bot.
        
        Args:
            api_key: Coinalyze API key
            vault_base_path: Base path for vault storage (default: centralized RaveQuant vault)
        """
        self.api_key = api_key
        self.vault_base = Path(vault_base_path)
        
        # Create inbox directories
        self.inbox_paths = {
            'oi': self.vault_base / 'inbox' / 'coinalyze_oi',
            'funding': self.vault_base / 'inbox' / 'coinalyze_funding',
            'liqs': self.vault_base / 'inbox' / 'coinalyze_liqs',
            'bullbear': self.vault_base / 'inbox' / 'coinalyze_bullbear'
        }
        
        for path in self.inbox_paths.values():
            path.mkdir(parents=True, exist_ok=True)
        
        # Rate limiting
        self.request_times: List[float] = []
        
        # Health tracking
        self.stats = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'rate_limit_hits': 0,
            'last_fetch_time': None
        }
    
    def _enforce_rate_limit(self):
        """Enforce 40 requests per minute rate limit."""
        current_time = time.time()
        
        # Remove requests outside the window
        self.request_times = [t for t in self.request_times 
                              if current_time - t < self.RATE_WINDOW]
        
        # Check if at limit
        if len(self.request_times) >= self.RATE_LIMIT:
            sleep_time = self.RATE_WINDOW - (current_time - self.request_times[0])
            if sleep_time > 0:
                logger.warning(f"Rate limit reached. Sleeping {sleep_time:.2f}s")
                self.stats['rate_limit_hits'] += 1
                time.sleep(sleep_time + 0.1)  # Add buffer
        
        self.request_times.append(current_time)
    
    def _make_request(self, endpoint: str, params: Dict) -> Optional[Dict]:
        """
        Make API request with rate limiting and error handling.
        
        Args:
            endpoint: API endpoint (e.g., '/open-interest-history')
            params: Query parameters
            
        Returns:
            JSON response or None on failure
        """
        self._enforce_rate_limit()
        
        # Add API key to params
        params['api_key'] = self.api_key
        
        url = f"{self.BASE_URL}{endpoint}"
        
        try:
            self.stats['total_requests'] += 1
            response = requests.get(url, params=params, timeout=30)
            
            if response.status_code == 200:
                self.stats['successful_requests'] += 1
                return response.json()
            elif response.status_code == 429:
                # Rate limit hit despite our checks
                retry_after = response.headers.get('Retry-After', 60)
                logger.error(f"API rate limit hit. Retry after {retry_after}s")
                self.stats['failed_requests'] += 1
                time.sleep(int(retry_after))
                return None
            else:
                logger.error(f"API error {response.status_code}: {response.text}")
                self.stats['failed_requests'] += 1
                return None
                
        except Exception as e:
            logger.error(f"Request failed: {e}")
            self.stats['failed_requests'] += 1
            return None
    
    def _save_to_inbox(self, data_type: str, symbol: str, data: List[Dict]):
        """
        Save data to appropriate inbox folder (append-only).
        
        Args:
            data_type: 'oi', 'funding', 'liqs', or 'bullbear'
            symbol: Asset symbol (BTC or ETH)
            data: List of data points
        """
        if not data:
            return
        
        inbox_path = self.inbox_paths[data_type]
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{symbol}_{data_type}_{timestamp}.jsonl"
        filepath = inbox_path / filename
        
        # Write as JSON Lines (one JSON object per line)
        with open(filepath, 'a') as f:
            for item in data:
                f.write(json.dumps(item) + '\n')
        
        logger.info(f"Saved {len(data)} {data_type} records for {symbol} to {filename}")
    
    def fetch_open_interest(self, symbol: str, interval: str = "1min", 
                           lookback_minutes: int = 60) -> Optional[List[Dict]]:
        """
        Fetch Open Interest history.
        
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
        
        response = self._make_request('/open-interest-history', params)
        
        if response:
            # Extract data from response
            for item in response:
                if item['symbol'] == symbol_code:
                    history = item.get('history', [])
                    self._save_to_inbox('oi', symbol, history)
                    return history
        
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
        """Get bot statistics."""
        return {
            **self.stats,
            'rate_limit_usage': f"{len(self.request_times)}/{self.RATE_LIMIT} per minute"
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
