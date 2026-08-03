"""Pipeline package — integration façade over Sprint modules."""

from backend.pipeline.orchestrator import OmniPipeline, get_or_create_session

__all__ = ["OmniPipeline", "get_or_create_session"]
