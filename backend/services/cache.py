"""SQLite-based caching system for API responses."""

import hashlib
import json
import sqlite3
import os
from contextlib import contextmanager
from typing import Dict, Any, Optional
from datetime import datetime

class Cache:
    """SQLite-based cache for storing API responses."""
    
    def __init__(self, path: str):
        """Initialize cache with SQLite database.
        
        Args:
            path: Path to SQLite database file
        """
        self.path = path
        
        # Create directory if needed
        os.makedirs(os.path.dirname(path), exist_ok=True) if os.path.dirname(path) else None
        
        # Initialize database schema
        self._init_db()
    
    def _init_db(self):
        """Initialize database schema."""
        with self._db() as con:
            con.execute("""
                CREATE TABLE IF NOT EXISTS kv (
                    k TEXT PRIMARY KEY,
                    v TEXT NOT NULL,
                    ts DATETIME DEFAULT CURRENT_TIMESTAMP,
                    access_count INTEGER DEFAULT 1
                )
            """)
            
            # Create index for timestamp-based cleanup
            con.execute("""
                CREATE INDEX IF NOT EXISTS idx_kv_ts ON kv(ts)
            """)
            
            con.commit()
    
    @contextmanager
    def _db(self):
        """Database connection context manager."""
        con = sqlite3.connect(self.path)
        try:
            yield con
        finally:
            con.close()
    
    @staticmethod
    def key_from_dict(data: Dict[str, Any]) -> str:
        """Generate cache key from dictionary.
        
        Args:
            data: Dictionary to hash
            
        Returns:
            SHA-256 hash of the dictionary
        """
        # Create deterministic JSON representation
        json_str = json.dumps(data, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(json_str.encode("utf-8")).hexdigest()
    
    def get(self, key: str) -> Optional[Dict[str, Any]]:
        """Get value from cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found
        """
        with self._db() as con:
            # Update access count and get value
            con.execute(
                "UPDATE kv SET access_count = access_count + 1 WHERE k = ?",
                (key,)
            )
            
            row = con.execute("SELECT v FROM kv WHERE k = ?", (key,)).fetchone()
            con.commit()
            
            if row:
                return json.loads(row[0])
            return None
    
    def set(self, key: str, value: Dict[str, Any]) -> None:
        """Set value in cache.
        
        Args:
            key: Cache key
            value: Value to cache
        """
        with self._db() as con:
            json_value = json.dumps(value)
            con.execute(
                "REPLACE INTO kv (k, v, ts, access_count) VALUES (?, ?, CURRENT_TIMESTAMP, 1)",
                (key, json_value)
            )
            con.commit()
    
    def delete(self, key: str) -> bool:
        """Delete key from cache.
        
        Args:
            key: Cache key to delete
            
        Returns:
            True if key was deleted, False if not found
        """
        with self._db() as con:
            cursor = con.execute("DELETE FROM kv WHERE k = ?", (key,))
            con.commit()
            return cursor.rowcount > 0
    
    def clear(self) -> int:
        """Clear all cache entries.
        
        Returns:
            Number of entries cleared
        """
        with self._db() as con:
            cursor = con.execute("DELETE FROM kv")
            con.commit()
            return cursor.rowcount
    
    def stats(self) -> Dict[str, Any]:
        """Get cache statistics.
        
        Returns:
            Dictionary with cache stats
        """
        with self._db() as con:
            row = con.execute("""
                SELECT 
                    COUNT(*) as total_entries,
                    SUM(access_count) as total_accesses,
                    AVG(access_count) as avg_accesses_per_entry,
                    MAX(ts) as latest_entry
                FROM kv
            """).fetchone()
            
            if row:
                return {
                    "total_entries": row[0],
                    "total_accesses": row[1] or 0,
                    "avg_accesses_per_entry": round(row[2] or 0, 2),
                    "latest_entry": row[3]
                }
            return {
                "total_entries": 0,
                "total_accesses": 0,
                "avg_accesses_per_entry": 0,
                "latest_entry": None
            }