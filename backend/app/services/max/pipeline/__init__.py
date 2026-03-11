"""
MAX Pipeline — Unified task pipeline for multi-step autonomous work.
Breaks high-level tasks into ordered subtasks routed to desks.
"""
from .task_pipeline import TaskPipeline, pipeline_engine

__all__ = ["TaskPipeline", "pipeline_engine"]
