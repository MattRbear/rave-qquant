"""
Rate Limiter Utilities
----------------------
Provides rate limiting functionality for API calls and WebSocket connections.
Prevents API rate limit violations and ensures system stability.
"""

import time
import threading
from typing import Optional, Callable, Any
from collections import deque
import logging

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    Token bucket rate limiter implementation.
    Thread-safe rate limiting for API calls.
    """
    
    def __init__(self, max_calls: int, time_window: float):
        """
        Initialize rate limiter.
        
        Args:
            max_calls: Maximum number of calls allowed in time window
            time_window: Time window in seconds
        """
        self.max_calls = max_calls
        self.time_window = time_window
        self.calls = deque()
        self.lock = threading.RLock()
        
    def acquire(self, blocking: bool = True, timeout: Optional[float] = None) -> bool:
        """
        Acquire permission to make a call.
        
        Args:
            blocking: If True, wait until permission granted
            timeout: Maximum time to wait (None = wait forever)
            
        Returns:
            True if permission granted, False otherwise
        """
        start_time = time.time()
        
        with self.lock:
            while True:
                # Clean up old calls outside the window
                current_time = time.time()
                while self.calls and current_time - self.calls[0] >= self.time_window:
                    self.calls.popleft()
                
                # Check if we can make a call
                if len(self.calls) < self.max_calls:
                    self.calls.append(current_time)
                    return True
                
                # If non-blocking, return immediately
                if not blocking:
                    return False
                
                # Check timeout
                if timeout is not None:
                    elapsed = time.time() - start_time
                    if elapsed >= timeout:
                        return False
                
                # Wait a bit before retrying
                sleep_time = self.calls[0] + self.time_window - current_time
                sleep_time = min(sleep_time, 0.1)  # Don't sleep too long
                time.sleep(sleep_time)
    
    def wait_time(self) -> float:
        """
        Get time to wait before next call can be made.
        
        Returns:
            Time in seconds (0 if call can be made immediately)
        """
        with self.lock:
            current_time = time.time()
            
            # Clean up old calls
            while self.calls and current_time - self.calls[0] >= self.time_window:
                self.calls.popleft()
            
            # Check if we can make a call
            if len(self.calls) < self.max_calls:
                return 0.0
            
            # Calculate wait time
            return self.calls[0] + self.time_window - current_time
    
    def get_usage(self) -> tuple[int, int]:
        """
        Get current usage.
        
        Returns:
            Tuple of (current_calls, max_calls)
        """
        with self.lock:
            current_time = time.time()
            
            # Clean up old calls
            while self.calls and current_time - self.calls[0] >= self.time_window:
                self.calls.popleft()
            
            return (len(self.calls), self.max_calls)


class SlidingWindowRateLimiter:
    """
    Sliding window rate limiter with better precision than token bucket.
    Useful for strict API rate limits.
    """
    
    def __init__(self, max_calls: int, time_window: float, min_interval: float = 0.0):
        """
        Initialize sliding window rate limiter.
        
        Args:
            max_calls: Maximum number of calls in time window
            time_window: Time window in seconds
            min_interval: Minimum time between consecutive calls (optional)
        """
        self.max_calls = max_calls
        self.time_window = time_window
        self.min_interval = min_interval
        self.call_times = deque()
        self.last_call_time = 0.0
        self.lock = threading.RLock()
        
    def acquire(self, blocking: bool = True, timeout: Optional[float] = None) -> bool:
        """
        Acquire permission to make a call.
        
        Args:
            blocking: If True, wait until permission granted
            timeout: Maximum time to wait (None = wait forever)
            
        Returns:
            True if permission granted, False otherwise
        """
        start_time = time.time()
        
        with self.lock:
            while True:
                current_time = time.time()
                
                # Remove calls outside the window
                cutoff_time = current_time - self.time_window
                while self.call_times and self.call_times[0] <= cutoff_time:
                    self.call_times.popleft()
                
                # Check minimum interval
                time_since_last = current_time - self.last_call_time
                if self.min_interval > 0 and time_since_last < self.min_interval:
                    wait_time = self.min_interval - time_since_last
                    
                    if not blocking:
                        return False
                    
                    if timeout is not None and time.time() - start_time + wait_time > timeout:
                        return False
                    
                    time.sleep(wait_time)
                    current_time = time.time()
                
                # Check if we can make a call
                if len(self.call_times) < self.max_calls:
                    self.call_times.append(current_time)
                    self.last_call_time = current_time
                    return True
                
                # If non-blocking, return immediately
                if not blocking:
                    return False
                
                # Check timeout
                if timeout is not None:
                    elapsed = time.time() - start_time
                    if elapsed >= timeout:
                        return False
                
                # Calculate wait time
                oldest_call = self.call_times[0]
                wait_time = oldest_call + self.time_window - current_time
                wait_time = max(0, min(wait_time, 0.1))  # Between 0 and 0.1 seconds
                
                if wait_time > 0:
                    time.sleep(wait_time)


def retry_with_backoff(
    func: Callable,
    max_retries: int = 3,
    initial_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    exceptions: tuple = (Exception,),
    logger_func: Optional[Callable] = None
) -> Any:
    """
    Retry a function with exponential backoff.
    
    Args:
        func: Function to retry
        max_retries: Maximum number of retry attempts
        initial_delay: Initial delay in seconds
        max_delay: Maximum delay in seconds
        exponential_base: Base for exponential backoff
        exceptions: Tuple of exceptions to catch and retry
        logger_func: Optional logging function
        
    Returns:
        Result of function call
        
    Raises:
        Last exception if all retries fail
    """
    delay = initial_delay
    last_exception = None
    
    for attempt in range(max_retries + 1):
        try:
            return func()
        except exceptions as e:
            last_exception = e
            
            if attempt >= max_retries:
                if logger_func:
                    logger_func(f"All {max_retries} retries failed: {e}")
                raise
            
            if logger_func:
                logger_func(
                    f"Attempt {attempt + 1}/{max_retries + 1} failed: {e}. "
                    f"Retrying in {delay:.2f}s..."
                )
            
            time.sleep(delay)
            
            # Exponential backoff with max cap
            delay = min(delay * exponential_base, max_delay)
    
    # Should never reach here, but just in case
    if last_exception:
        raise last_exception
