"""
Configuration Management
-----------------------
Centralized configuration management for all system components.
Handles environment-specific settings and path resolution.
"""

import os
from pathlib import Path
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class Config:
    """
    Central configuration class.
    Manages paths, API settings, and system parameters.
    """
    
    # Allowed instruments (whitelist)
    ALLOWED_INSTRUMENTS = ["BTC-USDT-SWAP", "ETH-USDT-SWAP"]
    
    # Timeframes
    TIMEFRAMES = ['1m', '5m', '15m', '1h', '4h']
    
    # API Configuration
    OKX_WS_URL = "wss://ws.okx.com:8443/ws/v5/public"
    OKX_REST_BASE = "https://www.okx.com"
    COINALYZE_BASE_URL = "https://api.coinalyze.net"
    
    # Rate Limits
    OKX_RATE_LIMIT = 100  # requests per 2 seconds
    OKX_RATE_WINDOW = 2  # seconds
    COINALYZE_RATE_LIMIT = 40  # requests per minute
    COINALYZE_RATE_WINDOW = 60  # seconds
    
    # Timeout settings (seconds)
    REQUEST_TIMEOUT = 30
    WEBSOCKET_PING_INTERVAL = 20
    WEBSOCKET_PING_TIMEOUT = 10
    RECONNECT_DELAY = 5
    MAX_RECONNECT_ATTEMPTS = 10
    
    # Storage settings
    MAX_DEDUP_CACHE_SIZE = 10000
    STATE_SAVE_INTERVAL = 100  # Save state every N records
    
    @staticmethod
    def get_vault_base() -> Path:
        """
        Get vault base path with environment variable support.
        
        Returns:
            Path to vault base directory
        """
        # Try environment variable first
        vault_env = os.getenv('RAVEQUANT_VAULT_PATH')
        if vault_env:
            vault_path = Path(vault_env)
            if vault_path.exists():
                logger.info(f"Using vault path from environment: {vault_path}")
                return vault_path
        
        # Try current directory structure
        current_dir = Path(__file__).parent.parent
        vault_candidate = current_dir / 'Rave_Quant_Vault'
        
        if vault_candidate.exists():
            logger.info(f"Using vault path from current directory: {vault_candidate}")
            return vault_candidate
        
        # Default fallback (original hardcoded path)
        default_path = Path(r"C:\Users\M.R Bear\Documents\RaveQuant\Rave_Quant_Vault")
        
        # If default doesn't exist, create in current directory
        if not default_path.exists():
            logger.warning(
                f"Default vault path doesn't exist: {default_path}. "
                f"Using current directory vault."
            )
            vault_path = current_dir / 'Rave_Quant_Vault'
            vault_path.mkdir(parents=True, exist_ok=True)
            return vault_path
        
        return default_path
    
    @staticmethod
    def get_metadata_path(inst_id: str) -> Path:
        """Get path to instrument metadata file."""
        return Config.get_vault_base() / 'meta' / 'okx' / 'instruments' / f'{inst_id}.json'
    
    @staticmethod
    def get_trades_dir(inst_id: str) -> Path:
        """Get path to trades directory."""
        return Config.get_vault_base() / 'raw' / 'okx' / 'trades_perps' / inst_id
    
    @staticmethod
    def get_l2_dir(inst_id: str) -> Path:
        """Get path to L2 directory."""
        return Config.get_vault_base() / 'raw' / 'okx' / 'l2_perps' / inst_id
    
    @staticmethod
    def get_cvd_dir(symbol: str) -> Path:
        """Get path to CVD output directory."""
        return Config.get_vault_base() / 'derived' / 'cvd' / 'okx' / symbol / '1m'
    
    @staticmethod
    def get_vwap_dir(inst_id: str) -> Path:
        """Get path to VWAP output directory."""
        return Config.get_vault_base() / 'derived' / 'vwap' / 'okx' / 'perps' / inst_id
    
    @staticmethod
    def get_wicks_dir(inst_id: str) -> Path:
        """Get path to wicks output directory."""
        return Config.get_vault_base() / 'derived' / 'wicks' / 'okx' / 'perps' / inst_id
    
    @staticmethod
    def get_volume_dir(inst_id: str) -> Path:
        """Get path to volume output directory."""
        return Config.get_vault_base() / 'derived' / 'volume' / 'okx' / 'perps' / inst_id
    
    @staticmethod
    def get_liquidity_dir(inst_id: str) -> Path:
        """Get path to liquidity buckets output directory."""
        return Config.get_vault_base() / 'derived' / 'liquidity_buckets' / 'okx' / 'perps' / inst_id
    
    @staticmethod
    def get_state_file(component: str, exchange: str, market: str, inst_id: str) -> Path:
        """
        Get path to state file.
        
        Args:
            component: Component name (e.g., 'cvd', 'vwap', 'wicks')
            exchange: Exchange name (e.g., 'okx')
            market: Market type (e.g., 'perps')
            inst_id: Instrument ID
            
        Returns:
            Path to state file
        """
        return Config.get_vault_base() / 'state' / component / exchange / market / f'{inst_id}.state.json'
    
    @staticmethod
    def ensure_directories():
        """
        Ensure all required directories exist.
        Creates directory structure if missing.
        """
        vault_base = Config.get_vault_base()
        
        # Create main directories
        directories = [
            vault_base / 'raw' / 'okx' / 'trades_perps',
            vault_base / 'raw' / 'okx' / 'l2_perps',
            vault_base / 'derived' / 'cvd' / 'okx',
            vault_base / 'derived' / 'vwap' / 'okx' / 'perps',
            vault_base / 'derived' / 'wicks' / 'okx' / 'perps',
            vault_base / 'derived' / 'volume' / 'okx' / 'perps',
            vault_base / 'derived' / 'liquidity_buckets' / 'okx' / 'perps',
            vault_base / 'state' / 'cvd' / 'okx',
            vault_base / 'state' / 'vwap' / 'okx' / 'perps',
            vault_base / 'state' / 'wicks' / 'okx' / 'perps',
            vault_base / 'state' / 'volume' / 'okx' / 'perps',
            vault_base / 'state' / 'liquidity_buckets' / 'okx' / 'perps',
            vault_base / 'meta' / 'okx' / 'instruments',
            vault_base / 'inbox' / 'coinalyze_oi',
            vault_base / 'inbox' / 'coinalyze_funding',
            vault_base / 'inbox' / 'coinalyze_liqs',
            vault_base / 'inbox' / 'coinalyze_bullbear',
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Ensured directory structure in {vault_base}")


# Initialize directories on import
try:
    Config.ensure_directories()
except Exception as e:
    logger.warning(f"Failed to initialize directories: {e}")
