"""
Input Validation Utilities
--------------------------
Provides comprehensive validation for all data inputs across the system.
Prevents injection attacks, data corruption, and invalid state.
"""

import re
from decimal import Decimal, InvalidOperation
from datetime import datetime
from typing import Any, Optional, List, Dict
import logging

logger = logging.getLogger(__name__)


class ValidationError(Exception):
    """Custom exception for validation failures."""
    pass


def validate_instrument_id(inst_id: str, allowed_instruments: List[str]) -> str:
    """
    Validate instrument ID against whitelist.
    
    Args:
        inst_id: Instrument ID to validate
        allowed_instruments: List of allowed instrument IDs
        
    Returns:
        Validated instrument ID
        
    Raises:
        ValidationError: If instrument ID is invalid
    """
    if not inst_id:
        raise ValidationError("Instrument ID cannot be empty")
    
    if not isinstance(inst_id, str):
        raise ValidationError(f"Instrument ID must be string, got {type(inst_id)}")
    
    # Check against whitelist
    if inst_id not in allowed_instruments:
        raise ValidationError(
            f"Invalid instrument ID: {inst_id}. "
            f"Allowed: {', '.join(allowed_instruments)}"
        )
    
    # Additional format validation (should match pattern like BTC-USDT-SWAP)
    pattern = r'^[A-Z]{3,10}-[A-Z]{3,10}-[A-Z]{3,10}$'
    if not re.match(pattern, inst_id):
        raise ValidationError(
            f"Instrument ID format invalid: {inst_id}. "
            f"Expected pattern: XXX-XXX-XXX"
        )
    
    return inst_id


def validate_timestamp(timestamp: str) -> str:
    """
    Validate ISO 8601 timestamp format.
    
    Args:
        timestamp: Timestamp string to validate
        
    Returns:
        Validated timestamp string
        
    Raises:
        ValidationError: If timestamp is invalid
    """
    if not timestamp:
        raise ValidationError("Timestamp cannot be empty")
    
    if not isinstance(timestamp, str):
        raise ValidationError(f"Timestamp must be string, got {type(timestamp)}")
    
    # Try to parse as ISO format
    try:
        # Support both 'Z' suffix and '+00:00' format
        dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        
        # Verify it's in reasonable range (not too far in past or future)
        now = datetime.now(dt.tzinfo)
        min_date = datetime(2020, 1, 1, tzinfo=dt.tzinfo)
        max_date = datetime(2030, 12, 31, tzinfo=dt.tzinfo)
        
        if dt < min_date or dt > max_date:
            raise ValidationError(
                f"Timestamp out of reasonable range: {timestamp}. "
                f"Must be between 2020-01-01 and 2030-12-31"
            )
        
        return timestamp
        
    except (ValueError, AttributeError) as e:
        raise ValidationError(f"Invalid timestamp format: {timestamp}. Error: {e}")


def validate_price(price: str, min_value: Decimal = Decimal('0')) -> str:
    """
    Validate price value.
    
    Args:
        price: Price string to validate
        min_value: Minimum allowed price (default: 0)
        
    Returns:
        Validated price string
        
    Raises:
        ValidationError: If price is invalid
    """
    if not price:
        raise ValidationError("Price cannot be empty")
    
    if not isinstance(price, str):
        raise ValidationError(f"Price must be string, got {type(price)}")
    
    try:
        price_decimal = Decimal(price)
        
        # Check if price is positive and greater than minimum
        if price_decimal <= min_value:
            raise ValidationError(
                f"Price must be greater than {min_value}, got {price}"
            )
        
        # Check for reasonable upper bound (prevent overflow)
        max_price = Decimal('10000000000')  # 10 billion
        if price_decimal > max_price:
            raise ValidationError(
                f"Price exceeds maximum allowed value: {price}"
            )
        
        return price
        
    except (InvalidOperation, ValueError) as e:
        raise ValidationError(f"Invalid price format: {price}. Error: {e}")


def validate_quantity(quantity: str, min_value: Decimal = Decimal('0')) -> str:
    """
    Validate quantity/size value.
    
    Args:
        quantity: Quantity string to validate
        min_value: Minimum allowed quantity (default: 0)
        
    Returns:
        Validated quantity string
        
    Raises:
        ValidationError: If quantity is invalid
    """
    if not quantity:
        raise ValidationError("Quantity cannot be empty")
    
    if not isinstance(quantity, str):
        raise ValidationError(f"Quantity must be string, got {type(quantity)}")
    
    try:
        qty_decimal = Decimal(quantity)
        
        # Check if quantity is positive and greater than minimum
        if qty_decimal <= min_value:
            raise ValidationError(
                f"Quantity must be greater than {min_value}, got {quantity}"
            )
        
        # Check for reasonable upper bound
        max_qty = Decimal('1000000000')  # 1 billion
        if qty_decimal > max_qty:
            raise ValidationError(
                f"Quantity exceeds maximum allowed value: {quantity}"
            )
        
        return quantity
        
    except (InvalidOperation, ValueError) as e:
        raise ValidationError(f"Invalid quantity format: {quantity}. Error: {e}")


def validate_side(side: str) -> str:
    """
    Validate trade side.
    
    Args:
        side: Side string to validate (should be 'buy' or 'sell')
        
    Returns:
        Validated side string (lowercase)
        
    Raises:
        ValidationError: If side is invalid
    """
    if not side:
        raise ValidationError("Side cannot be empty")
    
    if not isinstance(side, str):
        raise ValidationError(f"Side must be string, got {type(side)}")
    
    side_lower = side.lower()
    
    if side_lower not in ['buy', 'sell']:
        raise ValidationError(
            f"Invalid side: {side}. Must be 'buy' or 'sell'"
        )
    
    return side_lower


def validate_trade_id(trade_id: str) -> str:
    """
    Validate trade ID.
    
    Args:
        trade_id: Trade ID to validate
        
    Returns:
        Validated trade ID
        
    Raises:
        ValidationError: If trade ID is invalid
    """
    if not trade_id:
        raise ValidationError("Trade ID cannot be empty")
    
    if not isinstance(trade_id, str):
        raise ValidationError(f"Trade ID must be string, got {type(trade_id)}")
    
    # Check for reasonable length and format (should be numeric or alphanumeric)
    if len(trade_id) > 50:
        raise ValidationError(f"Trade ID too long: {len(trade_id)} characters")
    
    # Allow alphanumeric and hyphens
    if not re.match(r'^[a-zA-Z0-9\-]+$', trade_id):
        raise ValidationError(
            f"Trade ID contains invalid characters: {trade_id}"
        )
    
    return trade_id
