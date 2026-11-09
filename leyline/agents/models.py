"""Data models for AI agents in LeyLine."""

import time

from pydantic import BaseModel, Field

from leyline.controller.models import GameAction


class PlayerDecision(BaseModel):
    """Tactical gameplay decision returned by the gamer agent."""

    action: GameAction = Field(default=GameAction.NONE, description="Recommended key action")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Confidence score")
    reason: str = Field(default="", description="Tactical reasoning for this action")
    latency_ms: float = Field(default=0.0, ge=0.0, description="Roundtrip inference latency in ms")
    timestamp: float = Field(default_factory=time.time, description="Unix timestamp of decision")
