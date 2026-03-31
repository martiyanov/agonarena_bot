"""Lock management utilities for duel operations with TTL support."""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class DuelLockManager:
    """Manages per-duel and per-user locks with TTL for race condition prevention.
    
    This class provides:
    - Per-user locks for duel creation (prevents double creation)
    - Per-duel locks for turn processing and round completion (prevents parallel operations)
    - Automatic cleanup of expired locks
    - Timeout support with graceful degradation
    """
    
    def __init__(self, default_timeout: float = 30.0, lock_ttl: float = 300.0):
        """Initialize the lock manager.
        
        Args:
            default_timeout: Default timeout for acquiring locks (seconds)
            lock_ttl: Time-to-live for locks after release (cleanup threshold) (seconds)
        """
        self._user_locks: Dict[int, asyncio.Lock] = {}
        self._duel_locks: Dict[int, asyncio.Lock] = {}
        self._lock_last_used: Dict[int, float] = {}
        self._default_timeout = default_timeout
        self._lock_ttl = lock_ttl
        self._cleanup_task: Optional[asyncio.Task] = None
        self._lock = asyncio.Lock()  # Protects internal state
    
    async def _cleanup_loop(self) -> None:
        """Background task to clean up expired locks."""
        while True:
            try:
                await asyncio.sleep(60)  # Run cleanup every minute
                await self._cleanup_expired()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[DuelLockManager] Cleanup error: {e}")
    
    async def _cleanup_expired(self) -> None:
        """Remove locks that haven't been used for longer than TTL."""
        now = time.time()
        async with self._lock:
            # Clean up user locks
            expired_users = [
                user_id for user_id, last_used in self._lock_last_used.items()
                if user_id in self._user_locks and now - last_used > self._lock_ttl
            ]
            for user_id in expired_users:
                if user_id in self._user_locks:
                    # Only remove if lock is not currently held
                    if not self._user_locks[user_id].locked():
                        del self._user_locks[user_id]
                        logger.debug(f"[DuelLockManager] Cleaned up user lock: {user_id}")
            
            # Clean up duel locks
            expired_duels = [
                duel_id for duel_id in list(self._duel_locks.keys())
                if duel_id not in self._lock_last_used or now - self._lock_last_used.get(duel_id, 0) > self._lock_ttl
            ]
            for duel_id in expired_duels:
                if duel_id in self._duel_locks:
                    if not self._duel_locks[duel_id].locked():
                        del self._duel_locks[duel_id]
                        logger.debug(f"[DuelLockManager] Cleaned up duel lock: {duel_id}")
    
    def start_cleanup(self) -> None:
        """Start the background cleanup task."""
        if self._cleanup_task is None or self._cleanup_task.done():
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())
            logger.info("[DuelLockManager] Cleanup task started")
    
    def stop_cleanup(self) -> None:
        """Stop the background cleanup task."""
        if self._cleanup_task and not self._cleanup_task.done():
            self._cleanup_task.cancel()
            logger.info("[DuelLockManager] Cleanup task stopped")
    
    async def acquire_user_lock(
        self, 
        user_id: int, 
        timeout: Optional[float] = None
    ) -> bool:
        """Acquire a per-user lock for duel creation.
        
        Args:
            user_id: The user ID to lock
            timeout: Timeout in seconds (uses default if not specified)
            
        Returns:
            True if lock acquired, False if timeout
        """
        timeout = timeout or self._default_timeout
        
        # First, ensure lock exists atomically
        async with self._lock:
            if user_id not in self._user_locks:
                self._user_locks[user_id] = asyncio.Lock()
        
        # Now try to acquire the lock with timeout
        lock = self._user_locks[user_id]
        try:
            await asyncio.wait_for(lock.acquire(), timeout=timeout)
            self._lock_last_used[user_id] = time.time()
            logger.debug(f"[DuelLockManager] Acquired user lock: {user_id}")
            return True
        except asyncio.TimeoutError:
            logger.warning(f"[DuelLockManager] Timeout acquiring user lock: {user_id}")
            return False
    
    def release_user_lock(self, user_id: int) -> None:
        """Release a per-user lock.
        
        Args:
            user_id: The user ID to unlock
        """
        if user_id in self._user_locks:
            try:
                if self._user_locks[user_id].locked():
                    self._user_locks[user_id].release()
                    logger.debug(f"[DuelLockManager] Released user lock: {user_id}")
            except RuntimeError:
                # Lock was not held
                pass
    
    async def acquire_duel_lock(
        self, 
        duel_id: int, 
        timeout: Optional[float] = None
    ) -> bool:
        """Acquire a per-duel lock for turn/round operations.
        
        Args:
            duel_id: The duel ID to lock
            timeout: Timeout in seconds (uses default if not specified)
            
        Returns:
            True if lock acquired, False if timeout
        """
        timeout = timeout or self._default_timeout
        
        # First, ensure lock exists atomically
        async with self._lock:
            if duel_id not in self._duel_locks:
                self._duel_locks[duel_id] = asyncio.Lock()
        
        # Now try to acquire the lock with timeout
        lock = self._duel_locks[duel_id]
        try:
            await asyncio.wait_for(lock.acquire(), timeout=timeout)
            self._lock_last_used[duel_id] = time.time()
            logger.debug(f"[DuelLockManager] Acquired duel lock: {duel_id}")
            return True
        except asyncio.TimeoutError:
            logger.warning(f"[DuelLockManager] Timeout acquiring duel lock: {duel_id}")
            return False
    
    def release_duel_lock(self, duel_id: int) -> None:
        """Release a per-duel lock.
        
        Args:
            duel_id: The duel ID to unlock
        """
        if duel_id in self._duel_locks:
            try:
                if self._duel_locks[duel_id].locked():
                    self._duel_locks[duel_id].release()
                    logger.debug(f"[DuelLockManager] Released duel lock: {duel_id}")
            except RuntimeError:
                # Lock was not held
                pass
    
    def is_user_locked(self, user_id: int) -> bool:
        """Check if a user is currently locked.
        
        Args:
            user_id: The user ID to check
            
        Returns:
            True if locked
        """
        return user_id in self._user_locks and self._user_locks[user_id].locked()
    
    def is_duel_locked(self, duel_id: int) -> bool:
        """Check if a duel is currently locked.
        
        Args:
            duel_id: The duel ID to check
            
        Returns:
            True if locked
        """
        return duel_id in self._duel_locks and self._duel_locks[duel_id].locked()


# Global lock manager instance
duel_lock_manager = DuelLockManager(default_timeout=30.0, lock_ttl=300.0)
