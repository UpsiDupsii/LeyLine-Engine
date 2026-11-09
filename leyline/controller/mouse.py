"""Mouse controller for pointer positioning and click-to-drop puzzle games."""

from __future__ import annotations

import ctypes
import os
import time
from typing import TYPE_CHECKING

from leyline.vision.models import ScreenRegion

if TYPE_CHECKING:
    from leyline.vision.puzzle_detector import ContainerBounds


class MouseController:
    """Controls mouse movement and clicks via Windows user32 SendInput or pynput."""

    def __init__(self, mock_mode: bool = False) -> None:
        self.mock_mode = mock_mode or os.name != "nt"
        self._user32 = ctypes.windll.user32 if (os.name == "nt" and not mock_mode) else None
        self._last_position: tuple[int, int] = (0, 0)

    def set_position(self, x: int, y: int) -> bool:
        """Move cursor immediately to target screen coordinates."""
        self._last_position = (x, y)
        if self.mock_mode or not self._user32:
            return True
        try:
            self._user32.SetCursorPos(int(x), int(y))
            return True
        except Exception:
            return False

    def nudge(self, delta_x: int, delta_y: int = 0) -> bool:
        """Micro-adjust cursor position by delta screen pixels."""
        cur_x, cur_y = self._last_position
        return self.set_position(cur_x + delta_x, cur_y + delta_y)

    def click(self, button: str = "left", hold_duration: float = 0.05) -> bool:
        """Execute a mouse click at the current position."""
        if self.mock_mode or not self._user32:
            return True

        # Windows mouse event flags
        down_flag = 0x0002 if button == "left" else 0x0008
        up_flag = 0x0004 if button == "left" else 0x0010

        try:
            self._user32.mouse_event(down_flag, 0, 0, 0, 0)
            time.sleep(hold_duration)
            self._user32.mouse_event(up_flag, 0, 0, 0, 0)
            return True
        except Exception:
            return False

    def aim_at(
        self,
        container_region: ScreenRegion,
        x_fraction: float,
        y_offset_pixels: int = 40,
        container_bounds: ContainerBounds | None = None,
    ) -> tuple[int, int]:
        """Position cursor over the intended drop coordinate without clicking.

        Args:
            container_region: Bounding box of the overall screen capture area.
            x_fraction: Float from 0.0 (left wall) to 1.0 (right wall).
            y_offset_pixels: Vertical distance below container top.
            container_bounds: Optional inner container bounds detected by CV.

        Returns:
            tuple[int, int]: Computed screen coordinates (screen_x, screen_y).
        """
        safe_fraction = max(0.08, min(0.92, x_fraction))
        if container_bounds is not None:
            container_screen_left = container_region.left + container_bounds.left
            container_screen_width = container_bounds.width
            screen_x = int(container_screen_left + safe_fraction * container_screen_width)
            screen_y = int(container_region.top + container_bounds.top + y_offset_pixels)
        else:
            screen_x = int(container_region.left + safe_fraction * container_region.width)
            screen_y = int(container_region.top + y_offset_pixels)

        self.set_position(screen_x, screen_y)
        return (screen_x, screen_y)

    def drop_at(
        self,
        container_region: ScreenRegion,
        x_fraction: float,
        y_offset_pixels: int = 40,
        settle_time: float = 0.15,
        container_bounds: ContainerBounds | None = None,
    ) -> tuple[int, int]:
        """Position cursor at horizontal fraction across container and trigger drop click.

        Args:
            container_region: Bounding box of the game container cup.
            x_fraction: Float from 0.0 (left wall) to 1.0 (right wall).
            y_offset_pixels: Vertical distance below top of container to click.
            settle_time: Delay to let browser pointer catch up before clicking.
            container_bounds: Optional inner container bounds detected by CV.

        Returns:
            tuple[int, int]: Screen coordinates (x, y) where drop was triggered.
        """
        coords = self.aim_at(
            container_region=container_region,
            x_fraction=x_fraction,
            y_offset_pixels=y_offset_pixels,
            container_bounds=container_bounds,
        )
        time.sleep(settle_time)
        self.click("left")
        return coords

    @property
    def position(self) -> tuple[int, int]:
        return self._last_position
