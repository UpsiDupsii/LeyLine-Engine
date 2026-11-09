"""Mouse controller for pointer positioning and click-to-drop puzzle games."""

import ctypes
import os
import time

from leyline.vision.models import ScreenRegion


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

    def click(self, button: str = "left", hold_duration: float = 0.05) -> bool:
        """Execute a mouse click at the current position."""
        if self.mock_mode or not self._user32:
            return True

        # Windows mouse event flags
        # MOUSEEVENTF_LEFTDOWN = 0x0002, MOUSEEVENTF_LEFTUP = 0x0004
        # MOUSEEVENTF_RIGHTDOWN = 0x0008, MOUSEEVENTF_RIGHTUP = 0x0010
        down_flag = 0x0002 if button == "left" else 0x0008
        up_flag = 0x0004 if button == "left" else 0x0010

        try:
            self._user32.mouse_event(down_flag, 0, 0, 0, 0)
            time.sleep(hold_duration)
            self._user32.mouse_event(up_flag, 0, 0, 0, 0)
            return True
        except Exception:
            return False

    def drop_at(
        self,
        container_region: ScreenRegion,
        x_fraction: float,
        y_offset_pixels: int = 40,
        settle_time: float = 0.15,
    ) -> tuple[int, int]:
        """Position cursor at horizontal fraction across container and trigger drop click.

        Args:
            container_region: Bounding box of the game container cup.
            x_fraction: Float from 0.0 (left wall) to 1.0 (right wall).
            y_offset_pixels: Vertical distance below top of container to click.
            settle_time: Delay to let browser pointer catch up before clicking.

        Returns:
            tuple[int, int]: Screen coordinates (x, y) where drop was triggered.
        """
        # Clamp fraction within safe container walls (0.08 to 0.92) to avoid wall clipping
        safe_fraction = max(0.08, min(0.92, x_fraction))
        screen_x = int(container_region.left + safe_fraction * container_region.width)
        screen_y = int(container_region.top + y_offset_pixels)

        # Move cursor to drop line
        self.set_position(screen_x, screen_y)
        time.sleep(settle_time)

        # Click to drop the ball
        self.click("left")
        return (screen_x, screen_y)

    @property
    def position(self) -> tuple[int, int]:
        return self._last_position
