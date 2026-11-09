"""Data models and enums for game controllers and keyboard actions."""

from enum import Enum

from pydantic import BaseModel, Field


class GameAction(str, Enum):
    """Supported gameplay control actions across arcade and driving games."""

    FORWARD = "FORWARD"
    LEFT = "LEFT"
    RIGHT = "RIGHT"
    REVERSE = "REVERSE"
    FORWARD_LEFT = "FORWARD_LEFT"
    FORWARD_RIGHT = "FORWARD_RIGHT"
    UP = "UP"
    DOWN = "DOWN"
    SPACE = "SPACE"
    INTERACT = "INTERACT"
    BRAKE = "BRAKE"
    NONE = "NONE"


class ActionCommand(BaseModel):
    """Specification of an action to execute on the virtual controller."""

    action: GameAction = Field(default=GameAction.NONE, description="Target game action")
    duration: float = Field(
        default=0.25,
        ge=0.01,
        le=5.0,
        description="Key hold duration in seconds for vehicle movement",
    )
    cooldown: float = Field(default=0.02, ge=0.0, description="Minimum cooldown before next action")
