"""
Multi-Agent Coordinator

Coordinates multiple quantum agents with proper task distribution,
resource management, and conflict resolution.
"""

import asyncio
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set
from queue import Queue, Empty, PriorityQueue
from enum import Enum, auto

from .agent import QuantumAgent, AgentConfig, QuantumTask
from ..utils.circuit_locker import CircuitLocker, get_circuit_locker


class TaskPriority(Enum):
    """Priority levels for quantum tasks."""
    LOW = auto()
    NORMAL = auto()
    HIGH = auto()
    CRITICAL = auto()
    URGENT = auto()


@dataclass
class CoordinatorMetrics:
    """Metrics for coordinator performance."""
    total_tasks_submitted: int = 0
    total_tasks_completed: int = 0
    total_tasks_failed: int = 0
    average_execution_time: float = 0.0
    agent_utilization: Dict[str, float] = field(default_factory=dict)
    resource_conflicts: int = 0
    deadlocks_resolved: int = 0


class MultiAgentCoordinator:
    """
    Coordinates multiple quantum agents with intelligent task distribution.
    
    Features:
    - Dynamic load balancing
    - Priority-based task scheduling
    - Resource conflict detection
    - Automatic failover
    - Performance monitoring
    """
    
    def __init__(self, agents: List[QuantumAgent]):
        self.agents = {agent.agent_id: agent for agent in agents}
        self.circuit_locker = get_circuit_locker()
        
        # Task queues
        self._task_queue = PriorityQueue()
        self._completed_tasks = Queue()
        self._failed_tasks = Queue()
        
        # State management
        self._running = False
        self._coordinator_thread = None
        self._monitor_thread = None
        
        # Performance tracking
        self.metrics = CoordinatorMetrics()
        self._task_times: Dict[str, float] = {}
        
        # Load balancing
        self._agent_loads: Dict[str, int] = {
            agent_id: 0 for agent_id in self.agents.keys()
        }
        self._agent_capabilities: Dict[str, Set[str]] = {}
        
    async def start(self):
        """Start the coordinator and all agents."""
        if self._running:
            raise RuntimeError("Coordinator is already running")
        
        self._running = True
        
        # Start all agents
        for agent in self.agents.values():
            await agent.start()
        
        # Start coordinator thread
        self._coordinator_thread = threading.Thread(
            target=self._coordination_loop,
            name="Coordinator",
            daemon=True
        )
        self._coordinator_thread.start()
        
        # Start monitoring thread
        self._monitor_thread = threading.Thread(
            target=self._monitoring_loop,
            name="Coordinator-Monitor",
            daemon=True
        )
        self._monitor_thread.start()
    
    async def stop(self):
        """Stop the coordinator and all agents gracefully."""
        self._running = False
        
        # Stop all agents
        for agent in self.agents.values():
            await agent.stop()
        
        # Wait for threads to finish
        if self._coordinator_thread and self._coordinator_thread.is_alive():
            self._coordinator_thread.join(timeout=30.0)
        
        if self._monitor_thread and self._monitor_thread.is_alive():
            self._monitor_thread.join(timeout=30.0)
    
    def submit_task(self, circuit, priority: TaskPriority = TaskPriority.NORMAL,
                   timeout: Optional[float] = None, 
                   agent_id: Optional[str] = None) -> str:
        """
        Submit a quantum task for execution.
        
        Args:
            circuit: Quantum circuit to execute
            priority: Task priority
            timeout: Task timeout
            agent_id: Specific agent to use (optional)
            
        Returns:
            Task ID for tracking
        """
        task_id = str(uuid.uuid4())
        
        # Select best agent
        selected_agent_id = self._select_agent(agent_id, circuit, priority)
        
        # Create task
        task = QuantumTask(
            task_id=task_id,
            circuit=circuit,
            parameters={
                'priority': priority.name,
                'timeout': timeout,
                'submitted_at': time.time(),
            },
            priority=priority.value,
            callback=self._task_callback
        )
        
        # Submit to queue with priority
        self._task_queue.put((priority.value * -1, time.time(), task))
        
        # Update metrics
        self.metrics.total_tasks_submitted += 1
        self._task_times[task_id] = time.time()
        
        return task_id
    
    def _select_agent(self, preferred_agent: Optional[str], circuit, 
                     priority: TaskPriority) -> str:
        """Select best agent for task based on load and capabilities."""
        if preferred_agent and preferred_agent in self.agents:
            return preferred_agent
        
        # Get available agents
        available_agents = []
        for agent_id, agent in self.agents.items():
            if self._can_agent_handle_circuit(agent, circuit):
                available_agents.append((agent_id, self._agent_loads[agent_id]))
        
        if not available_agents:
            raise RuntimeError("No available agents can handle this circuit")
        
        # Select agent with lowest load (load balancing)
        available_agents.sort(key=lambda x: x[1])
        return available_agents[0][0]
    
    def _can_agent_handle_circuit(self, agent: QuantumAgent, circuit) -> bool:
        """Check if agent can handle the circuit."""
        # Check qubit count
        if circuit.num_qubits > agent.config.num_qubits:
            return False
        
        # Check memory constraints
        estimated_size = len(circuit) * 8 * circuit.num_qubits
        if agent._memory_usage + estimated_size > agent.config.memory_limit:
            return False
        
        # Check circuit complexity (simplified)
        if circuit.depth() > 100:  # Arbitrary depth limit
            return False
        
        return True
    
    def _coordination_loop(self):
        """Main coordination loop for task distribution."""
        while self._running:
            try:
                # Get next task
                try:
                    priority, timestamp, task = self._task_queue.get(timeout=1.0)
                except Empty:
                    continue
                
                # Submit task to selected agent
                success = self._submit_to_agent(task)
                
                if not success:
                    # Re-queue task with lower priority
                    self._task_queue.put((priority + 1, time.time(), task))
                    self.metrics.resource_conflicts += 1
                
                self._task_queue.task_done()
                
            except Exception as e:
                print(f"Error in coordination loop: {e}")
    
    def _submit_to_agent(self, task: QuantumTask) -> bool:
        """Submit task to agent with error handling."""
        # Try multiple agents if first fails
        for agent_id in self.agents.keys():
            agent = self.agents[agent_id]
            
            try:
                success = agent.submit_task(task)
                if success:
                    self._agent_loads[agent_id] += 1
                    return True
            except Exception as e:
                print(f"Failed to submit to agent {agent_id}: {e}")
                continue
        
        return False
    
    def _monitoring_loop(self):
        """Monitor agent performance and system health."""
        while self._running:
            try:
                # Check for deadlocks
                self.circuit_locker.cleanup_expired_locks()
                
                # Update agent utilizations
                total_tasks = 0
                for agent_id, agent in self.agents.items():
                    metrics = agent.get_metrics()
                    utilization = metrics['queue_size'] / max(1, agent.config.max_circuits)
                    self.metrics.agent_utilization[agent_id] = utilization
                    total_tasks += metrics['tasks_completed']
                
                # Update coordinator metrics
                self._update_coordinator_metrics()
                
                # Sleep before next check
                time.sleep(5.0)
                
            except Exception as e:
                print(f"Error in monitoring loop: {e}")
    
    def _task_callback(self, result: Dict[str, Any]):
        """Callback for task completion."""
        task_id = result['task_id']
        agent_id = result['agent_id']
        
        # Update agent load
        if agent_id in self._agent_loads:
            self._agent_loads[agent_id] = max(0, self._agent_loads[agent_id] - 1)
        
        # Record task completion time
        if task_id in self._task_times:
            execution_time = time.time() - self._task_times[task_id]
            del self._task_times[task_id]
            
            # Update average execution time
            completed_tasks = self.metrics.total_tasks_completed
            current_avg = self.metrics.average_execution_time
            new_avg = ((current_avg * completed_tasks) + execution_time) / (completed_tasks + 1)
            self.metrics.average_execution_time = new_avg
        
        # Update metrics based on result
        if result['success']:
            self.metrics.total_tasks_completed += 1
            self._completed_tasks.put(result)
        else:
            self.metrics.total_tasks_failed += 1
            self._failed_tasks.put(result)
    
    def _update_coordinator_metrics(self):
        """Update coordinator performance metrics."""
        # Calculate success rate
        total = (self.metrics.total_tasks_completed + 
                 self.metrics.total_tasks_failed)
        if total > 0:
            success_rate = self.metrics.total_tasks_completed / total
            # Could log or alert if success_rate is low
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status."""
        agent_status = {}
        for agent_id, agent in self.agents.items():
            agent_status[agent_id] = agent.get_metrics()
        
        return {
            'coordinator': {
                'is_running': self._running,
                'metrics': self.metrics.__dict__,
                'queue_size': self._task_queue.qsize(),
                'agent_loads': self._agent_loads,
            },
            'agents': agent_status,
            'circuit_locker': {
                'active_locks': len(self.circuit_locker._locks),
                'agent_operations': len(self.circuit_locker._agent_operations),
            }
        }
    
    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get status of specific task."""
        # Check completed tasks
        completed_tasks = list(self._completed_tasks.queue)
        for task in completed_tasks:
            if task['task_id'] == task_id:
                return {'status': 'completed', 'result': task}
        
        # Check failed tasks
        failed_tasks = list(self._failed_tasks.queue)
        for task in failed_tasks:
            if task['task_id'] == task_id:
                return {'status': 'failed', 'result': task}
        
        # Check if task is still pending
        if task_id in self._task_times:
            return {'status': 'pending', 'submitted_at': self._task_times[task_id]}
        
        return None
    
    def rebalance_load(self):
        """Rebalance load across agents."""
        # Find most and least loaded agents
        if not self._agent_loads:
            return
        
        max_load = max(self._agent_loads.values())
        min_load = min(self._agent_loads.values())
        
        if max_load - min_load > 5:  # Threshold for rebalancing
            print(f"Load imbalance detected: max={max_load}, min={min_load}")
            # Could implement task migration here
    
    def optimize_agent_distribution(self, circuits: List[Any]) -> Dict[str, List[Any]]:
        """Optimize circuit distribution across agents."""
        agent_assignments = {agent_id: [] for agent_id in self.agents.keys()}
        
        for circuit in circuits:
            best_agent = self._select_agent(None, circuit, TaskPriority.NORMAL)
            agent_assignments[best_agent].append(circuit)
        
        return agent_assignments