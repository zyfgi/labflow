"""Shared request-schema conventions."""

from pydantic import BaseModel, ConfigDict


class StrictSchema(BaseModel):
    """Request payloads reject unknown fields instead of silently ignoring them."""

    model_config = ConfigDict(extra="forbid")
