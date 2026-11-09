"""Data models and enums for game controllers and keyboard actions."""

from enum import Enum

from pydantic import BaseModel, Field


class GameAction(str, Enum):
    """Supported gameplay control actions."""

    LEFT = "LEFT"
    RIGHT = "RIGHT"
    UP = "UP"
    DOWN = "DOWN"
    SPACE = "SPACE"
    NONE = "NONE"


class ActionCommand(BaseModel):
    """Specification of an action to execute on the virtual controller."""

    action: GameAction = Field(default=GameAction.NONE, description="Target game action")
    duration: float = Field(
        default=0.08, ge=0.01, le=2.0, description="Key press duration in seconds"
    )
    cooldown: float = Field(default=0.05, ge=0.0, description="Minimum cooldown before next action")
