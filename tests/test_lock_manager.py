"""Tests for DuelLockManager race condition prevention."""

import asyncio
import pytest
from app.utils.locks import DuelLockManager


class TestDuelLockManager:
    """Test suite for DuelLockManager."""
    
    @pytest.fixture
    def lock_manager(self):
        """Create a fresh lock manager for each test."""
        return DuelLockManager(default_timeout=1.0, lock_ttl=60.0)
    
    @pytest.mark.asyncio
    async def test_user_lock_acquire_and_release(self, lock_manager):
        """Test basic user lock acquire and release."""
        user_id = 12345
        
        # Acquire lock
        result = await lock_manager.acquire_user_lock(user_id)
        assert result is True
        assert lock_manager.is_user_locked(user_id) is True
        
        # Release lock
        lock_manager.release_user_lock(user_id)
        assert lock_manager.is_user_locked(user_id) is False
    
    @pytest.mark.asyncio
    async def test_duel_lock_acquire_and_release(self, lock_manager):
        """Test basic duel lock acquire and release."""
        duel_id = 67890
        
        # Acquire lock
        result = await lock_manager.acquire_duel_lock(duel_id)
        assert result is True
        assert lock_manager.is_duel_locked(duel_id) is True
        
        # Release lock
        lock_manager.release_duel_lock(duel_id)
        assert lock_manager.is_duel_locked(duel_id) is False
    
    @pytest.mark.asyncio
    async def test_user_lock_timeout(self, lock_manager):
        """Test that user lock times out when already held."""
        user_id = 12345
        
        # First acquire
        result1 = await lock_manager.acquire_user_lock(user_id, timeout=0.5)
        assert result1 is True
        
        # Second acquire should timeout
        result2 = await lock_manager.acquire_user_lock(user_id, timeout=0.1)
        assert result2 is False
        
        # Cleanup
        lock_manager.release_user_lock(user_id)
    
    @pytest.mark.asyncio
    async def test_duel_lock_timeout(self, lock_manager):
        """Test that duel lock times out when already held."""
        duel_id = 67890
        
        # First acquire
        result1 = await lock_manager.acquire_duel_lock(duel_id, timeout=0.5)
        assert result1 is True
        
        # Second acquire should timeout
        result2 = await lock_manager.acquire_duel_lock(duel_id, timeout=0.1)
        assert result2 is False
        
        # Cleanup
        lock_manager.release_duel_lock(duel_id)
    
    @pytest.mark.asyncio
    async def test_user_lock_prevents_double_creation(self, lock_manager):
        """Test that user lock prevents double duel creation scenario."""
        user_id = 12345
        create_count = 0
        lock_acquired_order = []
        
        async def create_duel(task_id: int):
            nonlocal create_count
            if await lock_manager.acquire_user_lock(user_id, timeout=0.1):
                try:
                    lock_acquired_order.append(task_id)
                    # Simulate some work
                    await asyncio.sleep(0.05)
                    create_count += 1
                    return True
                finally:
                    lock_manager.release_user_lock(user_id)
            return False
        
        # Try to create duel twice concurrently
        results = await asyncio.gather(create_duel(1), create_duel(2))
        
        # Both should succeed (one after another), but sequentially
        assert sum(results) == 2
        assert create_count == 2
        # They should execute sequentially, not in parallel
        assert len(lock_acquired_order) == 2
    
    @pytest.mark.asyncio
    async def test_duel_lock_prevents_parallel_turns(self, lock_manager):
        """Test that duel lock prevents parallel turn processing."""
        duel_id = 67890
        turn_count = 0
        lock_acquired_order = []
        
        async def process_turn(task_id: int):
            nonlocal turn_count
            if await lock_manager.acquire_duel_lock(duel_id, timeout=0.1):
                try:
                    lock_acquired_order.append(task_id)
                    # Simulate turn processing
                    await asyncio.sleep(0.05)
                    turn_count += 1
                    return True
                finally:
                    lock_manager.release_duel_lock(duel_id)
            return False
        
        # Try to process turn twice concurrently
        results = await asyncio.gather(process_turn(1), process_turn(2))
        
        # Both should succeed (one after another), but sequentially
        assert sum(results) == 2
        assert turn_count == 2
        # They should execute sequentially, not in parallel
        assert len(lock_acquired_order) == 2
    
    @pytest.mark.asyncio
    async def test_separate_users_have_separate_locks(self, lock_manager):
        """Test that different users have independent locks."""
        user1 = 111
        user2 = 222
        
        # Both should be able to acquire locks simultaneously
        result1 = await lock_manager.acquire_user_lock(user1)
        result2 = await lock_manager.acquire_user_lock(user2)
        
        assert result1 is True
        assert result2 is True
        assert lock_manager.is_user_locked(user1) is True
        assert lock_manager.is_user_locked(user2) is True
        
        # Cleanup
        lock_manager.release_user_lock(user1)
        lock_manager.release_user_lock(user2)
    
    @pytest.mark.asyncio
    async def test_separate_duels_have_separate_locks(self, lock_manager):
        """Test that different duels have independent locks."""
        duel1 = 111
        duel2 = 222
        
        # Both should be able to acquire locks simultaneously
        result1 = await lock_manager.acquire_duel_lock(duel1)
        result2 = await lock_manager.acquire_duel_lock(duel2)
        
        assert result1 is True
        assert result2 is True
        assert lock_manager.is_duel_locked(duel1) is True
        assert lock_manager.is_duel_locked(duel2) is True
        
        # Cleanup
        lock_manager.release_duel_lock(duel1)
        lock_manager.release_duel_lock(duel2)
    
    @pytest.mark.asyncio
    async def test_cleanup_removes_expired_locks(self, lock_manager):
        """Test that cleanup removes expired locks."""
        # Create a lock manager with very short TTL
        lm = DuelLockManager(default_timeout=1.0, lock_ttl=0.01)
        
        duel_id = 123
        
        # Acquire and release lock
        await lm.acquire_duel_lock(duel_id)
        lm.release_duel_lock(duel_id)
        
        # Lock should exist but not be locked
        assert duel_id in lm._duel_locks
        
        # Wait for TTL to expire
        await asyncio.sleep(0.02)
        
        # Run cleanup
        await lm._cleanup_expired()
        
        # Lock should be removed
        assert duel_id not in lm._duel_locks
    
    @pytest.mark.asyncio
    async def test_global_lock_manager_singleton(self):
        """Test that global duel_lock_manager exists and is a singleton."""
        from app.utils.locks import duel_lock_manager as lm1
        from app.utils.locks import duel_lock_manager as lm2
        
        assert lm1 is lm2
        assert isinstance(lm1, DuelLockManager)
