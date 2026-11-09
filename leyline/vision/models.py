"""Data models for screen perception and calibration."""

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field


class ScreenRegion(BaseModel):
    """Bounding box coordinates for screen capture."""

    top: int = Field(ge=0, description="Top Y coordinate in pixels")
    left: int = Field(ge=0, description="Left X coordinate in pixels")
    width: int = Field(gt=0, description="Width in pixels")
    height: int = Field(gt=0, description="Height in pixels")

    def to_mss_dict(self) -> dict[str, int]:
        """Convert region to the dictionary format expected by mss."""
        return {
            "top": self.top,
            "left": self.left,
            "width": self.width,
            "height": self.height,
        }

    def to_roi_tuple(self) -> tuple[int, int, int, int]:
        """Convert to (left, top, width, height) tuple for OpenCV ROI."""
        return (self.left, self.top, self.width, self.height)


class CalibrationConfig(BaseModel):
    """Configuration settings for a game capture region preset."""

    preset_name: str = Field(default="default", description="Preset identifier")
    region: ScreenRegion = Field(description="Bounding box for the capture region")
    target_fps: float = Field(default=2.0, gt=0, description="Target capture frames per second")
    downscale_width: int = Field(default=512, gt=0, description="Downscaled frame width for model")
    downscale_height: int = Field(
        default=512, gt=0, description="Downscaled frame height for model"
    )
    updated_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO 8601 timestamp of last calibration",
    )

    def to_dict(self) -> dict[str, Any]:
        """Serialize configuration to a dictionary."""
        return self.model_dump()
