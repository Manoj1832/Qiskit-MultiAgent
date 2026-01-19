"""
Execution tracing for reproducibility and debugging.
"""

import json
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass
class TraceEvent:
    """A single trace event in the execution."""
    timestamp: str
    event_type: str
    agent: str | None
    data: dict[str, Any]
    duration_ms: float | None = None


@dataclass
class ExecutionTrace:
    """Complete execution trace for an issue resolution."""
    issue_id: str
    started_at: str
    events: list[TraceEvent] = field(default_factory=list)
    completed_at: str | None = None
    status: str = "running"
    total_tokens: int = 0
    
    def add_event(
        self,
        event_type: str,
        data: dict[str, Any],
        agent: str | None = None,
        duration_ms: float | None = None,
    ) -> None:
        """Add an event to the trace."""
        event = TraceEvent(
            timestamp=datetime.utcnow().isoformat(),
            event_type=event_type,
            agent=agent,
            data=data,
            duration_ms=duration_ms,
        )
        self.events.append(event)
    
    def complete(self, status: str = "success") -> None:
        """Mark the trace as complete."""
        self.completed_at = datetime.utcnow().isoformat()
        self.status = status
    
    def to_dict(self) -> dict[str, Any]:
        """Convert trace to dictionary."""
        return {
            "issue_id": self.issue_id,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "status": self.status,
            "total_tokens": self.total_tokens,
            "events": [asdict(e) for e in self.events],
        }
    
    def save(self, output_dir: Path) -> Path:
        """Save trace to JSON file."""
        output_dir.mkdir(parents=True, exist_ok=True)
        filename = f"trace_{self.issue_id}_{int(time.time())}.json"
        output_path = output_dir / filename
        with open(output_path, "w") as f:
            json.dump(self.to_dict(), f, indent=2)
        return output_path


class ExecutionTracer:
    """Manages execution tracing for the system."""
    
    def __init__(self, output_dir: Path | str = "traces"):
        self.output_dir = Path(output_dir)
        self.current_trace: ExecutionTrace | None = None
    
    def start_trace(self, issue_id: str) -> ExecutionTrace:
        """Start a new execution trace."""
        self.current_trace = ExecutionTrace(
            issue_id=issue_id,
            started_at=datetime.utcnow().isoformat(),
        )
        return self.current_trace
    
    def add_event(
        self,
        event_type: str,
        data: dict[str, Any],
        agent: str | None = None,
        duration_ms: float | None = None,
    ) -> None:
        """Add an event to the current trace."""
        if self.current_trace:
            self.current_trace.add_event(event_type, data, agent, duration_ms)
    
    def complete_trace(self, status: str = "success") -> Path | None:
        """Complete and save the current trace."""
        if self.current_trace:
            self.current_trace.complete(status)
            path = self.current_trace.save(self.output_dir)
            self.current_trace = None
            return path
        return None


class MetricsCollector:
    """Collects and aggregates system metrics."""
    
    def __init__(self):
        self.metrics: dict[str, list[float]] = {}
    
    def record(self, metric_name: str, value: float) -> None:
        """Record a metric value."""
        if metric_name not in self.metrics:
            self.metrics[metric_name] = []
        self.metrics[metric_name].append(value)
    
    def get_summary(self) -> dict[str, dict[str, float]]:
        """Get summary statistics for all metrics."""
        summary = {}
        for name, values in self.metrics.items():
            if values:
                summary[name] = {
                    "count": len(values),
                    "sum": sum(values),
                    "mean": sum(values) / len(values),
                    "min": min(values),
                    "max": max(values),
                }
        return summary
