"""
Agent Communication System

Provides inter-agent communication with message passing,
broadcasting, and coordination protocols.
"""

import asyncio
import json
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Callable, Set
from queue import Queue, Empty
from enum import Enum, auto


class MessageType(Enum):
    """Types of inter-agent messages."""
    TASK_ASSIGNMENT = auto()
    TASK_UPDATE = auto()
    RESOURCE_REQUEST = auto()
    RESOURCE_RESPONSE = auto()
    COORDINATION_REQUEST = auto()
    COORDINATION_RESPONSE = auto()
    STATUS_UPDATE = auto()
    ERROR_NOTIFICATION = auto()
    HEARTBEAT = auto()
    TERMINATION = auto()


@dataclass
class AgentMessage:
    """Message passed between quantum agents."""
    message_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    sender_id: str = ""
    recipient_id: Optional[str] = None  # None for broadcast
    message_type: MessageType = MessageType.STATUS_UPDATE
    payload: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    priority: int = 0  # Higher numbers = higher priority
    requires_ack: bool = False
    reply_to: Optional[str] = None
    ttl: Optional[float] = None  # Time to live
    attempts: int = field(default_factory=lambda: 0)
    max_attempts: int = 3


class MessageQueue:
    """Thread-safe message queue with priority handling."""
    
    def __init__(self, max_size: int = 1000):
        self._queue = Queue(maxsize=max_size)
        self._lock = threading.RLock()
        self._subscribers: Dict[str, Set[str]] = {}  # message_type -> set of agents
    
    def put(self, message: AgentMessage) -> bool:
        """Add message to queue with priority handling."""
        try:
            self._queue.put(message, timeout=1.0)
            return True
        except (Full, TimeoutError):
            return False
    
    def get(self, timeout: float = 1.0) -> Optional[AgentMessage]:
        """Get next message from queue."""
        try:
            return self._queue.get(timeout=timeout)
        except Empty:
            return None
    
    def subscribe(self, agent_id: str, message_types: List[MessageType]):
        """Subscribe agent to specific message types."""
        with self._lock:
            for msg_type in message_types:
                if msg_type not in self._subscribers:
                    self._subscribers[msg_type] = set()
                self._subscribers[msg_type].add(agent_id)
    
    def unsubscribe(self, agent_id: str, message_types: List[MessageType]):
        """Unsubscribe agent from message types."""
        with self._lock:
            for msg_type in message_types:
                if msg_type in self._subscribers:
                    self._subscribers[msg_type].discard(agent_id)
    
    def get_subscribers(self, message_type: MessageType) -> Set[str]:
        """Get all subscribers for a message type."""
        with self._lock:
            return self._subscribers.get(message_type, set()).copy()


class AgentCommunication:
    """
    Handles communication between quantum agents.
    
    Features:
    - Asynchronous message passing
    - Priority-based routing
    - Message filtering and subscriptions
    - Automatic acknowledgments
    - Broadcast and unicast support
    - Dead letter queue for failed messages
    """
    
    def __init__(self, heartbeat_interval: float = 5.0):
        self.heartbeat_interval = heartbeat_interval
        
        # Message handling
        self.message_queue = MessageQueue()
        self.dead_letter_queue: Queue[AgentMessage] = Queue()
        
        # Agent registry
        self._agents: Dict[str, Any] = {}  # agent_id -> agent reference
        self._agent_status: Dict[str, Dict[str, Any]] = {}
        
        # State management
        self._running = False
        self._communication_thread = None
        self._heartbeat_thread = None
        
        # Statistics
        self.stats = {
            'messages_sent': 0,
            'messages_received': 0,
            'messages_delivered': 0,
            'messages_failed': 0,
            'active_agents': 0,
        }
    
    async def start(self):
        """Start the communication system."""
        if self._running:
            raise RuntimeError("Communication system is already running")
        
        self._running = True
        
        # Start communication thread
        self._communication_thread = threading.Thread(
            target=self._communication_loop,
            name="Communication",
            daemon=True
        )
        self._communication_thread.start()
        
        # Start heartbeat thread
        self._heartbeat_thread = threading.Thread(
            target=self._heartbeat_loop,
            name="Heartbeat",
            daemon=True
        )
        self._heartbeat_thread.start()
    
    async def stop(self):
        """Stop the communication system."""
        self._running = False
        
        # Wait for threads to finish
        if self._communication_thread and self._communication_thread.is_alive():
            self._communication_thread.join(timeout=30.0)
        
        if self._heartbeat_thread and self._heartbeat_thread.is_alive():
            self._heartbeat_thread.join(timeout=30.0)
        
        # Send termination message to all agents
        await self.broadcast_message(MessageType.TERMINATION, {'reason': 'system_shutdown'})
    
    def register_agent(self, agent_id: str, agent_reference: Any, 
                     message_types: List[MessageType]):
        """Register an agent with the communication system."""
        self._agents[agent_id] = agent_reference
        self._agent_status[agent_id] = {
            'registered_at': time.time(),
            'last_heartbeat': time.time(),
            'status': 'active',
            'messages_received': 0,
            'messages_sent': 0,
        }
        
        # Subscribe agent to message types
        self.message_queue.subscribe(agent_id, message_types)
        
        self.stats['active_agents'] = len(self._agents)
    
    def unregister_agent(self, agent_id: str):
        """Unregister an agent."""
        if agent_id in self._agents:
            del self._agents[agent_id]
        
        if agent_id in self._agent_status:
            del self._agent_status[agent_id]
        
        self.stats['active_agents'] = len(self._agents)
    
    async def send_message(self, sender_id: str, recipient_id: str,
                         message_type: MessageType, payload: Dict[str, Any],
                         priority: int = 0, requires_ack: bool = False) -> str:
        """Send a unicast message to a specific agent."""
        message = AgentMessage(
            sender_id=sender_id,
            recipient_id=recipient_id,
            message_type=message_type,
            payload=payload,
            priority=priority,
            requires_ack=requires_ack
        )
        
        success = self.message_queue.put(message)
        if success:
            self.stats['messages_sent'] += 1
            self._update_agent_status(sender_id, 'messages_sent', 1)
        
        return message.message_id if success else None
    
    async def broadcast_message(self, sender_id: str, message_type: MessageType,
                             payload: Dict[str, Any], priority: int = 0,
                             exclude_self: bool = True) -> str:
        """Broadcast a message to all agents."""
        message = AgentMessage(
            sender_id=sender_id,
            message_type=message_type,
            payload=payload,
            priority=priority
        )
        
        # Don't send to self if requested
        if exclude_self and sender_id in self._agents:
            self.message_queue.subscribe(sender_id, [])  # Temporarily unsubscribe
        
        success = self.message_queue.put(message)
        
        # Restore subscription
        if exclude_self and sender_id in self._agents:
            self.message_queue.subscribe(sender_id, [message_type])
        
        if success:
            self.stats['messages_sent'] += 1
            self._update_agent_status(sender_id, 'messages_sent', 1)
        
        return message.message_id if success else None
    
    async def send_coordination_request(self, requester_id: str,
                                    requested_operation: str,
                                    parameters: Dict[str, Any]) -> Optional[str]:
        """Send a coordination request and wait for responses."""
        # Send request
        message_id = await self.send_message(
            requester_id, None, MessageType.COORDINATION_REQUEST,
            {
                'operation': requested_operation,
                'parameters': parameters,
                'requester_id': requester_id,
                'timestamp': time.time(),
            },
            priority=10  # High priority for coordination
        )
        
        if not message_id:
            return None
        
        # Wait for responses (simplified - in practice would use futures)
        await asyncio.sleep(0.1)  # Brief wait
        
        return message_id
    
    def _communication_loop(self):
        """Main communication loop for message processing."""
        while self._running:
            try:
                message = self.message_queue.get(timeout=1.0)
                if message is None:
                    continue
                
                # Process message
                success = self._process_message(message)
                
                if success:
                    self.stats['messages_delivered'] += 1
                else:
                    self.stats['messages_failed'] += 1
                    self.dead_letter_queue.put(message)
                
            except Empty:
                continue
            except Exception as e:
                print(f"Error in communication loop: {e}")
    
    def _process_message(self, message: AgentMessage) -> bool:
        """Process a single message."""
        # Check TTL
        if message.ttl and time.time() > message.ttl:
            return False
        
        # Check message attempts
        if message.attempts >= message.max_attempts:
            return False
        
        message.attempts += 1
        
        # Determine recipients
        if message.recipient_id:
            # Unicast message
            recipients = [message.recipient_id]
        else:
            # Broadcast message
            recipients = self.message_queue.get_subscribers(message.message_type)
        
        # Deliver to recipients
        delivered = False
        for recipient_id in recipients:
            if recipient_id in self._agents:
                try:
                    agent = self._agents[recipient_id]
                    
                    # Call agent's message handler
                    if hasattr(agent, 'handle_message'):
                        agent.handle_message(message)
                        delivered = True
                        self._update_agent_status(recipient_id, 'messages_received', 1)
                    
                except Exception as e:
                    print(f"Failed to deliver message to {recipient_id}: {e}")
        
        return delivered
    
    def _heartbeat_loop(self):
        """Send periodic heartbeat messages."""
        while self._running:
            try:
                # Send heartbeat broadcast
                for agent_id in self._agents:
                    self._update_agent_status(agent_id, 'last_heartbeat', time.time())
                
                # Check for inactive agents
                current_time = time.time()
                inactive_threshold = self.heartbeat_interval * 3
                
                inactive_agents = []
                for agent_id, status in self._agent_status.items():
                    if current_time - status['last_heartbeat'] > inactive_threshold:
                        inactive_agents.append(agent_id)
                
                # Mark inactive agents
                for agent_id in inactive_agents:
                    self._agent_status[agent_id]['status'] = 'inactive'
                    print(f"Agent {agent_id} marked as inactive")
                
                # Wait before next heartbeat
                time.sleep(self.heartbeat_interval)
                
            except Exception as e:
                print(f"Error in heartbeat loop: {e}")
    
    def _update_agent_status(self, agent_id: str, field: str, value: Any):
        """Update status information for an agent."""
        if agent_id in self._agent_status:
            self._agent_status[agent_id][field] = value
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status."""
        return {
            'is_running': self._running,
            'statistics': self.stats,
            'agent_status': self._agent_status.copy(),
            'queue_size': self.message_queue._queue.qsize(),
            'dead_letter_queue_size': self.dead_letter_queue.qsize(),
        }
    
    def get_agent_status(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Get status of specific agent."""
        return self._agent_status.get(agent_id)
    
    def send_heartbeat(self, agent_id: str):
        """Send heartbeat message for an agent."""
        # Update agent's last heartbeat
        self._update_agent_status(agent_id, 'last_heartbeat', time.time())
        
        # Mark as active if was inactive
        if self._agent_status.get(agent_id, {}).get('status') == 'inactive':
            self._agent_status[agent_id]['status'] = 'active'
            print(f"Agent {agent_id} reactivated")


# Global communication instance
_global_communication = None

def get_communication_system() -> AgentCommunication:
    """Get global communication system instance."""
    global _global_communication
    if _global_communication is None:
        _global_communication = AgentCommunication()
    return _global_communication