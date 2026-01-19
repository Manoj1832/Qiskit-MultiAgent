"""Tests for observability modules."""

import pytest
import tempfile
from pathlib import Path
from swe_agent_system.observability.tracing import (
    ExecutionTrace,
    ExecutionTracer,
    MetricsCollector,
    TraceEvent,
)


class TestTraceEvent:
    """Tests for TraceEvent dataclass."""
    
    def test_trace_event_creation(self):
        """Should create trace event."""
        event = TraceEvent(
            timestamp="2024-01-01T00:00:00",
            event_type="agent_started",
            agent="planner",
            data={"step": 1},
            duration_ms=100.0,
        )
        
        assert event.event_type == "agent_started"
        assert event.agent == "planner"
        assert event.duration_ms == 100.0


class TestExecutionTrace:
    """Tests for ExecutionTrace class."""
    
    def test_add_event(self):
        """Should add events to trace."""
        trace = ExecutionTrace(
            issue_id="123",
            started_at="2024-01-01T00:00:00",
        )
        
        trace.add_event("test_event", {"key": "value"}, agent="test")
        
        assert len(trace.events) == 1
        assert trace.events[0].event_type == "test_event"
    
    def test_complete(self):
        """Should mark trace as complete."""
        trace = ExecutionTrace(
            issue_id="123",
            started_at="2024-01-01T00:00:00",
        )
        
        trace.complete("success")
        
        assert trace.status == "success"
        assert trace.completed_at is not None
    
    def test_to_dict(self):
        """Should convert trace to dictionary."""
        trace = ExecutionTrace(
            issue_id="123",
            started_at="2024-01-01T00:00:00",
        )
        trace.add_event("event1", {"data": 1})
        
        data = trace.to_dict()
        
        assert data["issue_id"] == "123"
        assert len(data["events"]) == 1
    
    def test_save(self):
        """Should save trace to file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            trace = ExecutionTrace(
                issue_id="123",
                started_at="2024-01-01T00:00:00",
            )
            trace.add_event("test", {})
            
            path = trace.save(Path(tmpdir))
            
            assert path.exists()
            assert "trace_123" in path.name


class TestExecutionTracer:
    """Tests for ExecutionTracer class."""
    
    def test_start_trace(self):
        """Should start new trace."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tracer = ExecutionTracer(tmpdir)
            trace = tracer.start_trace("issue_456")
            
            assert trace.issue_id == "issue_456"
            assert tracer.current_trace is not None
    
    def test_add_event(self):
        """Should add event to current trace."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tracer = ExecutionTracer(tmpdir)
            tracer.start_trace("issue_789")
            tracer.add_event("my_event", {"info": "data"})
            
            assert len(tracer.current_trace.events) == 1
    
    def test_complete_trace(self):
        """Should complete and save trace."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tracer = ExecutionTracer(tmpdir)
            tracer.start_trace("issue_complete")
            tracer.add_event("event", {})
            
            path = tracer.complete_trace("success")
            
            assert path is not None
            assert path.exists()
            assert tracer.current_trace is None


class TestMetricsCollector:
    """Tests for MetricsCollector class."""
    
    def test_record_metric(self):
        """Should record metric values."""
        collector = MetricsCollector()
        collector.record("tokens", 1000)
        collector.record("tokens", 2000)
        
        assert len(collector.metrics["tokens"]) == 2
    
    def test_get_summary(self):
        """Should calculate summary statistics."""
        collector = MetricsCollector()
        collector.record("duration", 10)
        collector.record("duration", 20)
        collector.record("duration", 30)
        
        summary = collector.get_summary()
        
        assert summary["duration"]["count"] == 3
        assert summary["duration"]["sum"] == 60
        assert summary["duration"]["mean"] == 20
        assert summary["duration"]["min"] == 10
        assert summary["duration"]["max"] == 30
    
    def test_empty_summary(self):
        """Should handle empty metrics."""
        collector = MetricsCollector()
        summary = collector.get_summary()
        
        assert summary == {}
