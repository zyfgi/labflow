"""Retrieval engine shared by the global Search API and the AI assistant.

Permission scopes live in app/permissions/projects.py (the single source);
nothing in this package re-implements them.
"""

from app.services.retrieval.types import RetrievalHit, RetrievalPlan  # noqa: F401
