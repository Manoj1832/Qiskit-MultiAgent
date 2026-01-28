"""
Quantum Resource Manager

Manages quantum computing resources including backends,
simulators, and execution environments with proper allocation
and deallocation.
"""

import asyncio
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set
from enum import Enum, auto
from queue import Queue, Empty
import weakref


class ResourceType(Enum):
    """Types of quantum resources."""
    SIMULATOR = auto()
    QUANTUM_HARDWARE = auto()
    QUANTUM_VOLUME = auto()
    QUANTUM_JOB = auto()
    BACKEND_CONNECTION = auto()


@dataclass
class QuantumResource:
    """Represents a quantum computing resource."""
    resource_id: str
    resource_type: ResourceType
    name: str
    capacity: int  # Max concurrent usage
    current_usage: int = 0
    is_available: bool = True
    properties: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    last_used: Optional[float] = None
    usage_count: int = 0


@dataclass
class ResourceAllocation:
    """Represents allocation of a quantum resource."""
    allocation_id: str
    resource_id: str
    agent_id: str
    allocated_at: float = field(default_factory=time.time)
    expires_at: Optional[float] = None
    properties: Dict[str, Any] = field(default_factory=dict)
    is_active: bool = True


class QuantumResourceManager:
    """
    Manages quantum computing resources with intelligent allocation.
    
    Features:
    - Dynamic resource allocation
    - Resource pooling and sharing
    - Automatic resource cleanup
    - Performance monitoring
    - Load balancing across backends
    """
    
    def __init__(self):
        # Resource storage
        self._resources: Dict[str, QuantumResource] = {}
        self._allocations: Dict[str, ResourceAllocation] = {}
        
        # Thread safety
        self._lock = threading.RLock()
        
        # Performance tracking
        self.metrics = {
            'total_allocations': 0,
            'active_allocations': 0,
            'failed_allocations': 0,
            'resource_utilization': {},
            'average_allocation_time': 0.0,
        }
        
        # State management
        self._running = False
        self._monitor_thread = None
        
        # Default resources
        self._initialize_default_resources()
    
    async def start(self):
        """Start resource manager and monitoring."""
        if self._running:
            raise RuntimeError("Resource manager is already running")
        
        self._running = True
        
        # Start monitoring thread
        self._monitor_thread = threading.Thread(
            target=self._monitoring_loop,
            name="ResourceMonitor",
            daemon=True
        )
        self._monitor_thread.start()
    
    async def stop(self):
        """Stop resource manager gracefully."""
        self._running = False
        
        if self._monitor_thread and self._monitor_thread.is_alive():
            self._monitor_thread.join(timeout=30.0)
        
        # Cleanup all allocations
        self.cleanup_all_allocations()
    
    def _initialize_default_resources(self):
        """Initialize default quantum resources."""
        # Add Aer simulator
        self._add_resource(QuantumResource(
            resource_id="aer_simulator_1",
            resource_type=ResourceType.SIMULATOR,
            name="Aer Simulator",
            capacity=10,  # 10 concurrent circuits
            properties={
                'backend': 'aer_simulator',
                'max_qubits': 30,
                'supports_shots': True,
                'supports_noise_models': True,
            }
        ))
        
        # Add statevector simulator
        self._add_resource(QuantumResource(
            resource_id="statevector_simulator_1",
            resource_type=ResourceType.SIMULATOR,
            name="Statevector Simulator",
            capacity=5,  # 5 concurrent circuits
            properties={
                'backend': 'statevector_simulator',
                'max_qubits': 20,
                'exact_results': True,
                'no_shots': True,
            }
        ))
        
        # Add quantum volume resources (if available)
        self._add_resource(QuantumResource(
            resource_id="quantum_volume_1",
            resource_type=ResourceType.QUANTUM_VOLUME,
            name="Quantum Volume Calculator",
            capacity=2,  # 2 concurrent calculations
            properties={
                'max_qubits': 20,
                'calculation_type': 'quantum_volume',
                'requires_calibration': False,
            }
        ))
    
    def _add_resource(self, resource: QuantumResource):
        """Add a resource to the manager."""
        with self._lock:
            self._resources[resource.resource_id] = resource
            self.metrics['resource_utilization'][resource.resource_id] = 0.0
    
    async def allocate_resource(self, agent_id: str, resource_type: ResourceType,
                             requirements: Dict[str, Any] = None,
                             timeout: Optional[float] = None) -> Optional[str]:
        """
        Allocate a quantum resource for an agent.
        
        Args:
            agent_id: ID of the requesting agent
            resource_type: Type of resource needed
            requirements: Additional requirements
            timeout: Allocation timeout
            
        Returns:
            Allocation ID if successful, None otherwise
        """
        if requirements is None:
            requirements = {}
        
        allocation_start = time.time()
        timeout = timeout or 30.0
        
        while time.time() - allocation_start < timeout:
            with self._lock:
                # Find suitable resource
                suitable_resource = self._find_suitable_resource(resource_type, requirements)
                
                if suitable_resource:
                    # Create allocation
                    allocation_id = f"alloc_{int(time.time() * 1000000)}"
                    
                    allocation = ResourceAllocation(
                        allocation_id=allocation_id,
                        resource_id=suitable_resource.resource_id,
                        agent_id=agent_id,
                        expires_at=time.time() + requirements.get('duration', 300),  # 5 min default
                        properties=requirements.copy()
                    )
                    
                    # Update resource usage
                    suitable_resource.current_usage += 1
                    suitable_resource.last_used = time.time()
                    suitable_resource.usage_count += 1
                    
                    # Store allocation
                    self._allocations[allocation_id] = allocation
                    
                    # Update metrics
                    self.metrics['total_allocations'] += 1
                    self.metrics['active_allocations'] += 1
                    
                    # Update average allocation time
                    alloc_time = time.time() - allocation_start
                    total_allocs = self.metrics['total_allocations']
                    current_avg = self.metrics['average_allocation_time']
                    self.metrics['average_allocation_time'] = (
                        (current_avg * (total_allocs - 1) + alloc_time) / total_allocs
                    )
                    
                    return allocation_id
            
            # Wait and retry
            await asyncio.sleep(0.1)
        
        self.metrics['failed_allocations'] += 1
        return None
    
    def _find_suitable_resource(self, resource_type: ResourceType,
                              requirements: Dict[str, Any]) -> Optional[QuantumResource]:
        """Find a suitable resource based on type and requirements."""
        suitable_resources = []
        
        for resource in self._resources.values():
            # Check resource type
            if resource.resource_type != resource_type:
                continue
            
            # Check availability
            if not resource.is_available or resource.current_usage >= resource.capacity:
                continue
            
            # Check specific requirements
            if self._meets_requirements(resource, requirements):
                suitable_resources.append(resource)
        
        # Select best resource (load balanced)
        if suitable_resources:
            suitable_resources.sort(key=lambda r: r.current_usage / r.capacity)
            return suitable_resources[0]
        
        return None
    
    def _meets_requirements(self, resource: QuantumResource,
                           requirements: Dict[str, Any]) -> bool:
        """Check if resource meets specific requirements."""
        # Check qubit requirement
        if 'max_qubits' in requirements:
            required_qubits = requirements['max_qubits']
            available_qubits = resource.properties.get('max_qubits', 0)
            if available_qubits < required_qubits:
                return False
        
        # Check backend requirement
        if 'backend' in requirements:
            required_backend = requirements['backend']
            available_backend = resource.properties.get('backend')
            if available_backend != required_backend:
                return False
        
        # Check other properties
        for prop, value in requirements.items():
            if prop in ['max_qubits', 'backend', 'duration']:
                continue
            
            if resource.properties.get(prop) != value:
                return False
        
        return True
    
    async def deallocate_resource(self, allocation_id: str) -> bool:
        """
        Deallocate a previously allocated resource.
        
        Args:
            allocation_id: ID of allocation to deallocate
            
        Returns:
            True if deallocated successfully
        """
        with self._lock:
            if allocation_id not in self._allocations:
                return False
            
            allocation = self._allocations[allocation_id]
            
            if not allocation.is_active:
                return False
            
            # Mark as inactive
            allocation.is_active = False
            
            # Update resource usage
            resource = self._resources.get(allocation.resource_id)
            if resource:
                resource.current_usage = max(0, resource.current_usage - 1)
            
            # Remove allocation
            del self._allocations[allocation_id]
            
            # Update metrics
            self.metrics['active_allocations'] -= 1
            
            return True
    
    def cleanup_expired_allocations(self):
        """Clean up expired allocations."""
        current_time = time.time()
        
        with self._lock:
            expired_allocations = []
            
            for allocation_id, allocation in self._allocations.items():
                if (allocation.expires_at and 
                    current_time > allocation.expires_at):
                    expired_allocations.append(allocation_id)
            
            for allocation_id in expired_allocations:
                # Update resource usage
                allocation = self._allocations[allocation_id]
                resource = self._resources.get(allocation.resource_id)
                if resource:
                    resource.current_usage = max(0, resource.current_usage - 1)
                
                # Remove allocation
                del self._allocations[allocation_id]
                self.metrics['active_allocations'] -= 1
    
    def cleanup_all_allocations(self):
        """Clean up all allocations (emergency cleanup)."""
        with self._lock:
            # Reset all resource usage
            for resource in self._resources.values():
                resource.current_usage = 0
            
            # Clear all allocations
            self._allocations.clear()
            self.metrics['active_allocations'] = 0
    
    def _monitoring_loop(self):
        """Monitor resource usage and performance."""
        while self._running:
            try:
                # Update utilization metrics
                self._update_utilization_metrics()
                
                # Cleanup expired allocations
                self.cleanup_expired_allocations()
                
                # Check for idle resources
                self._check_idle_resources()
                
                # Wait before next check
                time.sleep(5.0)
                
            except Exception as e:
                print(f"Error in resource monitoring loop: {e}")
    
    def _update_utilization_metrics(self):
        """Update resource utilization metrics."""
        current_time = time.time()
        
        for resource_id, resource in self._resources.items():
            if resource.capacity > 0:
                utilization = resource.current_usage / resource.capacity
                self.metrics['resource_utilization'][resource_id] = utilization
    
    def _check_idle_resources(self):
        """Check for resources that have been idle too long."""
        current_time = time.time()
        idle_threshold = 300.0  # 5 minutes
        
        for resource in self._resources.values():
            if (resource.last_used and 
                current_time - resource.last_used > idle_threshold):
                # Could perform resource-specific cleanup
                pass
    
    def get_resource_status(self, resource_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a specific resource."""
        with self._lock:
            resource = self._resources.get(resource_id)
            if resource:
                return {
                    'resource_id': resource.resource_id,
                    'resource_type': resource.resource_type.name,
                    'name': resource.name,
                    'capacity': resource.capacity,
                    'current_usage': resource.current_usage,
                    'is_available': resource.is_available,
                    'utilization': resource.current_usage / max(1, resource.capacity),
                    'last_used': resource.last_used,
                    'usage_count': resource.usage_count,
                    'properties': resource.properties,
                }
            return None
    
    def get_agent_allocations(self, agent_id: str) -> List[Dict[str, Any]]:
        """Get all allocations for a specific agent."""
        with self._lock:
            allocations = []
            
            for allocation in self._allocations.values():
                if allocation.agent_id == agent_id and allocation.is_active:
                    allocations.append({
                        'allocation_id': allocation.allocation_id,
                        'resource_id': allocation.resource_id,
                        'allocated_at': allocation.allocated_at,
                        'expires_at': allocation.expires_at,
                        'properties': allocation.properties,
                    })
            
            return allocations
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status."""
        resource_status = {}
        for resource_id in self._resources:
            resource_status[resource_id] = self.get_resource_status(resource_id)
        
        return {
            'is_running': self._running,
            'metrics': self.metrics,
            'resources': resource_status,
            'total_resources': len(self._resources),
            'active_allocations': len(self._allocations),
        }
    
    def add_custom_resource(self, resource: QuantumResource):
        """Add a custom resource to the manager."""
        self._add_resource(resource)
    
    def remove_resource(self, resource_id: str) -> bool:
        """Remove a resource from the manager."""
        with self._lock:
            # Check if resource has active allocations
            for allocation in self._allocations.values():
                if allocation.resource_id == resource_id and allocation.is_active:
                    return False  # Cannot remove resource with active allocations
            
            if resource_id in self._resources:
                del self._resources[resource_id]
                
                # Clean up metrics
                if resource_id in self.metrics['resource_utilization']:
                    del self.metrics['resource_utilization'][resource_id]
                
                return True
        
        return False


# Global resource manager instance
_global_resource_manager = None

def get_resource_manager() -> QuantumResourceManager:
    """Get global resource manager instance."""
    global _global_resource_manager
    if _global_resource_manager is None:
        _global_resource_manager = QuantumResourceManager()
    return _global_resource_manager