"""AI assistant service package.

Read-only assistant: question → local permission-scoped retrieval → minimal
context → external OpenAI-compatible API → answer + local source links.
The LLM never touches the database and never gains extra permissions.
"""
