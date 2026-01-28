"""
Circuit Locker for Thread-Safe Quantum Circuit Operations

Provides atomic operations and prevents race conditions when multiple
agents modify quantum circuits simultaneously.
"""

import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Dict, Set, Optional, Any
import weakref
import uuid


@dataclass
class CircuitLock:
    """Represents a lock on a quantum circuit."""
    circuit_id: str
    agent_id: str
    acquired_at: float = field(default_factory=time.time)
    expires_at: Optional[float] = None
    lock_type: str = "exclusive"  # exclusive, shared
    operations: Set[str] = field(default_factory=set)


class CircuitLocker:
    """
    Thread-safe circuit locking mechanism to prevent race conditions.
    
    Features:
    - Exclusive and shared locks
    - Lock expiration to prevent deadlocks
    - Deadlock detection and resolution
    - Lock promotion/demotion
    """
    
    def __init__(self, default_timeout: float = 30.0):
        self._locks: Dict[str, CircuitLock] = {}
        self._lock = threading.RLock()
        self._default_timeout = default_timeout
        self._agent_operations: Dict[str, Set[str]] = {}
        
        # Deadlock detection
        self._deadlock_check_interval = 5.0
        self._last_deadlock_check = time.time()
        self._max_lock_duration = 60.0  # Maximum lock duration before forced release
    
    @contextmanager
    def acquire_lock(self, circuit_id: str, agent_id: str, 
                   lock_type: str = "exclusive", 
                   timeout: Optional[float] = None):
        """
        Context manager for acquiring circuit lock.
        
        Args:
            circuit_id: ID of circuit to lock
            agent_id: ID of agent requesting lock
            lock_type: Type of lock (exclusive/shared)
            timeout: Lock timeout in seconds
            
        Yields:
            CircuitLock if lock acquired successfully
            
        Raises:
            TimeoutError: If lock cannot be acquired
            ValueError: If invalid parameters provided
        """
        if timeout is None:
            timeout = self._default_timeout
        
        circuit_lock = self._acquire_lock(circuit_id, agent_id, lock_type, timeout)
        
        try:
            yield circuit_lock
        finally:
            self._release_lock(circuit_id, agent_id)
    
    def _acquire_lock(self, circuit_id: str, agent_id: str, 
                     lock_type: str, timeout: float) -> CircuitLock:
        """Acquire lock with deadlock detection."""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            with self._lock:
                # Check for existing lock
                existing_lock = self._locks.get(circuit_id)
                
                # Check if lock is compatible
                if self._is_lock_compatible(existing_lock, lock_type, agent_id):
                    # Create new lock
                    new_lock = CircuitLock(
                        circuit_id=circuit_id,
                        agent_id=agent_id,
                        lock_type=lock_type,
                        expires_at=time.time() + self._default_timeout
                    )
                    
                    self._locks[circuit_id] = new_lock
                    
                    # Track agent operations
                    if agent_id not in self._agent_operations:
                        self._agent_operations[agent_id] = set()
                    self._agent_operations[agent_id].add(circuit_id)
                    
                    return new_lock
                
                # Check for deadlock
                if self._detect_deadlock(agent_id):
                    self._resolve_deadlock(agent_id)
                
                # Wait before retrying
                time.sleep(0.01)
        
        raise TimeoutError(f"Could not acquire lock for circuit {circuit_id}")
    
    def _is_lock_compatible(self, existing_lock: Optional[CircuitLock], 
                          requested_type: str, agent_id: str) -> bool:
        """Check if lock request is compatible with existing lock."""
        if existing_lock is None:
            return True
        
        # Same agent can always acquire
        if existing_lock.agent_id == agent_id:
            return True
        
        # Check if lock has expired
        if existing_lock.expires_at and time.time() > existing_lock.expires_at:
            return True
        
        # Exclusive and shared lock compatibility
        if existing_lock.lock_type == "exclusive" and requested_type == "exclusive":
            return False
        
        if existing_lock.lock_type == "exclusive" and requested_type == "shared":
            return False
        
        if existing_lock.lock_type == "shared" and requested_type == "exclusive":
            return False
        
        return True
    
    def _detect_deadlock(self, agent_id: str) -> bool:
        """Detect if agent is involved in a deadlock."""
        # Simple deadlock detection: check circular dependencies
        agent_locks = self._agent_operations.get(agent_id, set())
        
        # If agent is waiting for locks held by others who are waiting for this agent
        for circuit_id in agent_locks:
            lock = self._locks.get(circuit_id)
            if lock and lock.agent_id != agent_id:
                # Check if other agent is waiting for this agent's locks
                other_agent_locks = self._agent_operations.get(lock.agent_id, set())
                for other_circuit_id in other_agent_locks:
                    other_lock = self._locks.get(other_circuit_id)
                    if other_lock and other_lock.agent_id == agent_id:
                        return True  # Deadlock detected
        
        return False
    
    def _resolve_deadlock(self, agent_id: str):
        """Resolve deadlock by releasing agent's locks."""
        print(f"Resolving deadlock for agent {agent_id}")
        
        with self._lock:
            # Release all locks held by this agent
            agent_circuits = list(self._agent_operations.get(agent_id, set()))
            for circuit_id in agent_circuits:
                if circuit_id in self._locks:
                    del self._locks[circuit_id]
            
            # Clear agent operations
            self._agent_operations[agent_id] = set()
    
    def _release_lock(self, circuit_id: str, agent_id: str):
        """Release lock on circuit."""
        with self._lock:
            if circuit_id in self._locks:
                lock = self._locks[circuit_id]
                if lock.agent_id == agent_id:
                    del self._locks[circuit_id]
            
            # Update agent operations
            if agent_id in self._agent_operations:
                self._agent_operations[agent_id].discard(circuit_id)
    
    def cleanup_expired_locks(self):
        """Clean up expired locks to prevent resource leaks."""
        current_time = time.time()
        
        with self._lock:
            expired_locks = []
            for circuit_id, lock in self._locks.items():
                if (lock.expires_at and current_time > lock.expires_at) or \
                   (current_time - lock.acquired_at > self._max_lock_duration):
                    expired_locks.append(circuit_id)
            
            for circuit_id in expired_locks:
                del self._locks[circuit_id]
                agent_id = self._locks[circuit_id].agent_id if circuit_id in self._locks else None
                
                if agent_id and agent_id in self._agent_operations:
                    self._agent_operations[agent_id].discard(circuit_id)
    
    def get_lock_status(self, circuit_id: str) -> Optional[Dict[str, Any]]:
        """Get status of lock on specific circuit."""
        with self._lock:
            lock = self._locks.get(circuit_id)
            if lock:
                return {
                    'agent_id': lock.agent_id,
                    'lock_type': lock.lock_type,
                    'acquired_at': lock.acquired_at,
                    'expires_at': lock.expires_at,
                    'operations': list(lock.operations),
                }
            return None
    
    def get_agent_status(self, agent_id: str) -> Dict[str, Any]:
        """Get status of agent's locks and operations."""
        with self._lock:
            agent_locks = []
            agent_operations = self._agent_operations.get(agent_id, set())
            
            for circuit_id in agent_operations:
                lock = self._locks.get(circuit_id)
                if lock:
                    agent_locks.append({
                        'circuit_id': circuit_id,
                        'lock_type': lock.lock_type,
                        'acquired_at': lock.acquired_at,
                    })
            
            return {
                'agent_id': agent_id,
                'locked_circuits': agent_locks,
                'total_locks': len(agent_locks),
                'active_operations': len(agent_operations),
            }
    
    def force_release_all_locks(self, agent_id: str):
        """Force release all locks for an agent (emergency cleanup)."""
        with self._lock:
            if agent_id in self._agent_operations:
                circuit_ids = list(self._agent_operations[agent_id])
                for circuit_id in circuit_ids:
                    if circuit_id in self._locks:
                        del self._locks[circuit_id]
                
                self._agent_operations[agent_id] = set()


# Global circuit locker instance
_global_circuit_locker = None

def get_circuit_locker() -> CircuitLocker:
    """Get global circuit locker instance."""
    global _global_circuit_locker
    if _global_circuit_locker is None:
        _global_circuit_locker = CircuitLocker()
    return _global_circuit_locker


@contextmanager
def atomic_circuit_operation(circuit_id: str, agent_id: str, 
                          operation_type: str = "exclusive"):
    """
    Context manager for atomic circuit operations.
    
    Usage:
        with atomic_circuit_operation("circuit_123", "agent_1"):
            # Perform circuit modifications
            modify_circuit()
    """
    locker = get_circuit_locker()
    
    with locker.acquire_lock(circuit_id, agent_id, operation_type) as lock:
        # Add operation to lock
        lock.operations.add(operation_type)
        yield lock