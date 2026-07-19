"""
AgentOrchestrator — future AI agent coordination layer.

Future responsibilities:
- Coordinating the resume parsing pipeline (extract skills and experience from uploaded PDFs)
- Invoking RAG retrieval against the career knowledge base to enrich predictions
- Orchestrating the AI career advisor agent workflow (Gemini API integration)

This module is intentionally empty in Phase 1. It exists as a structural seam
so that resume-parsing and RAG phases can slot in without requiring another
backend reorganisation.
"""


class AgentOrchestrator:
    """Placeholder for the AI agent orchestration layer."""

    def __init__(self) -> None:
        pass

    def run(self, *args, **kwargs):
        raise NotImplementedError("AgentOrchestrator is not yet implemented.")
