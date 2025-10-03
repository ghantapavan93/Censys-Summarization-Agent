"""Rate limiting using token bucket algorithm."""

import time
from typing import Dict
from threading import Lock

class TokenBucket:
    """Token bucket for rate limiting."""
    
    def __init__(self, capacity: int, refill_per_sec: float):
        """Initialize token bucket.
        
        Args:
            capacity: Maximum number of tokens
            refill_per_sec: Tokens added per second
        """
        self.capacity = capacity
        self.tokens = float(capacity)  # Start with full bucket
        self.refill_per_sec = refill_per_sec
        self.last_update = time.monotonic()
        self._lock = Lock()
    
    def allow(self, tokens: int = 1) -> bool:
        """Check if request is allowed.
        
        Args:
            tokens: Number of tokens to consume
            
        Returns:
            True if request allowed, False if rate limited
        """
        with self._lock:
            now = time.monotonic()
            
            # Add tokens based on elapsed time
            elapsed = now - self.last_update
            self.last_update = now
            
            # Add tokens, but don't exceed capacity
            self.tokens = min(
                self.capacity, 
                self.tokens + elapsed * self.refill_per_sec
            )
            
            # Check if we have enough tokens
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            
            return False
    
    def get_info(self) -> Dict[str, float]:
        """Get current bucket information.
        
        Returns:
            Dictionary with bucket stats
        """
        with self._lock:
            return {
                "capacity": self.capacity,
                "current_tokens": round(self.tokens, 2),
                "refill_per_sec": self.refill_per_sec,
                "utilization_pct": round((1 - self.tokens / self.capacity) * 100, 1)
            }

class RateLimiter:
    """Global rate limiter managing multiple token buckets."""
    
    def __init__(self):
        self._buckets: Dict[str, TokenBucket] = {}
        self._lock = Lock()
    
    def is_allowed(self, key: str, capacity: int, refill_per_sec: float, tokens: int = 1) -> bool:
        """Check if request is allowed for given key.
        
        Args:
            key: Unique identifier (e.g., IP address)
            capacity: Bucket capacity
            refill_per_sec: Refill rate
            tokens: Tokens to consume
            
        Returns:
            True if allowed, False if rate limited
        """
        with self._lock:
            if key not in self._buckets:
                self._buckets[key] = TokenBucket(capacity, refill_per_sec)
            
            bucket = self._buckets[key]
        
        return bucket.allow(tokens)
    
    def get_bucket_info(self, key: str) -> Dict[str, float]:
        """Get information about a specific bucket.
        
        Args:
            key: Bucket identifier
            
        Returns:
            Bucket information or empty dict if not found
        """
        with self._lock:
            if key in self._buckets:
                return self._buckets[key].get_info()
            return {}
    
    def cleanup_expired(self, max_idle_time: int = 3600) -> int:
        """Clean up buckets that haven't been used recently.
        
        Args:
            max_idle_time: Max idle time in seconds
            
        Returns:
            Number of buckets cleaned up
        """
        # Simple cleanup - in production you'd track last access time
        # For now, just return 0 (no cleanup)
        return 0

# Global rate limiter instance
_global_limiter = RateLimiter()

def limiter(key: str, capacity: int, refill_per_sec: float) -> bool:
    """Simple rate limiting function.
    
    Args:
        key: Unique identifier for the client
        capacity: Maximum requests in bucket
        refill_per_sec: Rate at which bucket refills
        
    Returns:
        True if request allowed, False if rate limited
    """
    return _global_limiter.is_allowed(key, capacity, refill_per_sec)

def get_limiter_info(key: str) -> Dict[str, float]:
    """Get rate limiter info for a key.
    
    Args:
        key: Client identifier
        
    Returns:
        Rate limiter statistics
    """
    return _global_limiter.get_bucket_info(key)