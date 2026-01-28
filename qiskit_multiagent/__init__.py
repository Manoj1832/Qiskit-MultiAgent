"""
Qiskit Multi-Agent System

A comprehensive framework for multi-agent quantum computing with Qiskit.
Provides coordination, communication, and resource management for quantum agents.
"""

__version__ = "1.0.0"
__author__ = "Manoj1832"

from .core.agent import QuantumAgent
from .core.coordinator import MultiAgentCoordinator
from .core.communication import AgentCommunication
from .core.resource_manager import QuantumResourceManager
from .utils.circuit_locker import CircuitLocker
from .utils.error_handler import QuantumErrorHandler

__all__ = [
    "QuantumAgent",
    "MultiAgentCoordinator", 
    "AgentCommunication",
    "QuantumResourceManager",
    "CircuitLocker",
    "QuantumErrorHandler",
]