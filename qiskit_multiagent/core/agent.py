"""
Quantum Agent Base Class

Provides thread-safe quantum agent functionality with proper resource management
and error handling for multi-agent quantum environments.
"""

import asyncio
import threading
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Callable
from queue import Queue, Empty
import uuid

from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister
from qiskit.primitives import Sampler
from qiskit_aer import AerSimulator
import numpy as np


@dataclass
class AgentConfig:
    """Configuration for quantum agent."""
    agent_id: str
    num_qubits: int = 4
    max_circuits: int = 100
    timeout: float = 30.0
    memory_limit: int = 1024 * 1024 * 100  # 100MB
    backend: str = "aer_simulator"


@dataclass
class QuantumTask:
    """Represents a quantum computation task."""
    task_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    circuit: Optional[QuantumCircuit] = None
    parameters: Dict[str, Any] = field(default_factory=dict)
    priority: int = 0
    created_at: float = field(default_factory=time.time)
    callback: Optional[Callable] = None


class QuantumAgent(ABC):
    """
    Base class for quantum agents with thread-safe operations
    and proper resource management.
    """
    
    def __init__(self, config: AgentConfig):
        self.config = config
        self.agent_id = config.agent_id
        
        # Thread safety
        self._lock = threading.RLock()
        self._task_queue = Queue(maxsize=config.max_circuits)
        self._running = False
        self._executor_thread = None
        
        # Resource tracking
        self._memory_usage = 0
        self._circuit_count = 0
        self._last_activity = time.time()
        
        # Quantum resources
        self._backend = self._initialize_backend()
        self._sampler = Sampler(self._backend)
        
        # Performance metrics
        self.metrics = {
            'tasks_completed': 0,
            'tasks_failed': 0,
            'total_execution_time': 0.0,
            'average_circuit_depth': 0.0,
        }
        
    def _initialize_backend(self):
        """Initialize quantum backend with proper configuration."""
        if self.config.backend == "aer_simulator":
            backend = AerSimulator()
        else:
            # Add support for other backends
            from qiskit.providers.ibmq import IBMQ
            backend = IBMQ.get_provider().get_backend(self.config.backend)
        
        # Configure backend for optimal performance
        if hasattr(backend, 'configuration'):
            backend_config = backend.configuration()
            if hasattr(backend_config, 'max_shots'):
                backend.set_options(max_shots=1024)
        
        return backend
    
    async def start(self):
        """Start the agent's main execution loop."""
        with self._lock:
            if self._running:
                raise RuntimeError(f"Agent {self.agent_id} is already running")
            
            self._running = True
            self._executor_thread = threading.Thread(
                target=self._execution_loop,
                name=f"QuantumAgent-{self.agent_id}",
                daemon=True
            )
            self._executor_thread.start()
    
    async def stop(self):
        """Stop the agent gracefully."""
        with self._lock:
            self._running = False
            
        if self._executor_thread and self._executor_thread.is_alive():
            self._executor_thread.join(timeout=self.config.timeout)
    
    def submit_task(self, task: QuantumTask) -> bool:
        """
        Submit a task to the agent's queue.
        
        Args:
            task: QuantumTask to execute
            
        Returns:
            True if task was submitted successfully
        """
        try:
            if self._check_memory_usage(task.circuit):
                self._task_queue.put(task, timeout=1.0)
                return True
            else:
                raise MemoryError("Insufficient memory for task")
        except (Full, asyncio.TimeoutError):
            return False
    
    def _check_memory_usage(self, circuit: Optional[QuantumCircuit]) -> bool:
        """Check if circuit can be accommodated within memory limits."""
        if circuit is None:
            return True
        
        # Estimate memory usage based on circuit size
        estimated_size = len(circuit) * 8 * self.config.num_qubits  # Rough estimate
        return (self._memory_usage + estimated_size) < self.config.memory_limit
    
    def _execution_loop(self):
        """Main execution loop for the agent."""
        while self._running:
            try:
                # Get task with timeout
                task = self._task_queue.get(timeout=1.0)
                
                if task is None:  # Poison pill
                    break
                
                # Execute task with error handling
                result = self._execute_task_safely(task)
                
                # Update metrics
                self._update_metrics(task, result)
                
                # Call callback if provided
                if task.callback:
                    task.callback(result)
                
                self._task_queue.task_done()
                
            except Empty:
                continue
            except Exception as e:
                # Log error but continue running
                print(f"Error in agent {self.agent_id}: {e}")
                self.metrics['tasks_failed'] += 1
    
    def _execute_task_safely(self, task: QuantumTask) -> Dict[str, Any]:
        """Execute task with comprehensive error handling."""
        start_time = time.time()
        
        try:
            # Validate circuit
            if task.circuit is None:
                raise ValueError("Task circuit is None")
            
            # Check circuit size
            if task.circuit.num_qubits > self.config.num_qubits:
                raise ValueError(f"Circuit exceeds agent's qubit limit: {task.circuit.num_qubits}")
            
            # Execute quantum circuit
            result = self._execute_quantum_task(task)
            
            # Update resource tracking
            self._update_resource_usage(task.circuit, start_time)
            
            return {
                'success': True,
                'result': result,
                'execution_time': time.time() - start_time,
                'agent_id': self.agent_id,
                'task_id': task.task_id,
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'execution_time': time.time() - start_time,
                'agent_id': self.agent_id,
                'task_id': task.task_id,
            }
    
    def _execute_quantum_task(self, task: QuantumTask) -> Dict[str, Any]:
        """Execute the quantum computation."""
        # This is where the actual quantum computation happens
        # Override in subclasses for specific quantum algorithms
        
        circuit = task.circuit
        
        # Add measurement if not present
        if not any(isinstance(op, type) and op.name == 'measure' 
                  for op in circuit.data):
            creg = ClassicalRegister(circuit.num_qubits, 'c')
            if not any(isinstance(reg, ClassicalRegister) for reg in circuit.cregs):
                circuit.add_register(creg)
            circuit.measure_all()
        
        # Execute with proper error handling
        try:
            job = self._sampler.run(circuit, shots=1024)
            result = job.result()
            
            # Process results
            counts = result.get_counts()
            
            # Calculate success probability (example metric)
            success_prob = counts.get('0' * circuit.num_qubits, 0) / sum(counts.values())
            
            return {
                'counts': counts,
                'success_probability': success_prob,
                'circuit_depth': circuit.depth(),
                'gate_count': len(circuit),
            }
            
        except Exception as e:
            raise RuntimeError(f"Quantum execution failed: {e}")
    
    def _update_resource_usage(self, circuit: QuantumCircuit, start_time: float):
        """Update resource usage tracking."""
        with self._lock:
            # Update memory usage (simplified)
            circuit_size = len(circuit) * 8 * self.config.num_qubits
            self._memory_usage += circuit_size
            self._circuit_count += 1
            self._last_activity = time.time()
            
            # Clean up old circuits to prevent memory leaks
            if self._circuit_count > self.config.max_circuits:
                self._cleanup_old_circuits()
    
    def _cleanup_old_circuits(self):
        """Clean up old circuits to prevent memory leaks."""
        # Simplified cleanup - in real implementation, 
        # this would remove oldest circuits
        self._memory_usage = max(0, self._memory_usage * 0.8)
        self._circuit_count = int(self._circuit_count * 0.8)
    
    def _update_metrics(self, task: QuantumTask, result: Dict[str, Any]):
        """Update performance metrics."""
        with self._lock:
            self.metrics['tasks_completed'] += 1 if result['success'] else 0
            self.metrics['total_execution_time'] += result['execution_time']
            
            if result['success'] and 'result' in result:
                circuit_depth = result['result'].get('circuit_depth', 0)
                if circuit_depth > 0:
                    total_depth = (self.metrics['average_circuit_depth'] * 
                                 (self.metrics['tasks_completed'] - 1) + circuit_depth)
                    self.metrics['average_circuit_depth'] = (total_depth / 
                                                          self.metrics['tasks_completed'])
    
    @abstractmethod
    async def process_quantum_data(self, data: Any) -> Any:
        """Process quantum-specific data. Override in subclasses."""
        pass
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get current performance metrics."""
        with self._lock:
            return {
                **self.metrics,
                'memory_usage': self._memory_usage,
                'circuit_count': self._circuit_count,
                'last_activity': self._last_activity,
                'queue_size': self._task_queue.qsize(),
                'is_running': self._running,
            }
    
    def __repr__(self) -> str:
        return f"QuantumAgent(id={self.agent_id}, running={self._running})"