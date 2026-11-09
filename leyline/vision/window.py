"""Window detection and bounding box extraction for target game applications."""

from typing import Any

import pygetwindow as gw

from leyline.vision.models import ScreenRegion


class WindowManager:
    """Discovers, focuses, and extracts screen coordinates for specific application windows."""

    @staticmethod
    def list_open_windows() -> list[str]:
        """Return a sorted list of unique titles of all visible, non-empty windows."""
        try:
            titles = [w.title.strip() for w in gw.getAllWindows() if w.title and w.title.strip()]
            return sorted(set(titles))
        except Exception:
            return []

    @staticmethod
    def find_window(query: str) -> Any:
        """Find the first window whose title contains the query string (case-insensitive)."""
        clean_query = query.strip().lower()
        try:
            for w in gw.getAllWindows():
                if w.title and clean_query in w.title.lower():
                    return w
        except Exception:
            pass
        return None

    @staticmethod
    def get_window_region(query: str) -> ScreenRegion | None:
        """Get the ScreenRegion bounding box for a window matching the query."""
        win = WindowManager.find_window(query)
        if not win or win.width <= 0 or win.height <= 0:
            return None

        # Ensure coordinates are within non-negative display space
        left = max(0, int(win.left))
        top = max(0, int(win.top))
        width = int(win.width)
        height = int(win.height)

        return ScreenRegion(top=top, left=left, width=width, height=height)

    @staticmethod
    def focus_window(query: str) -> bool:
        """Bring the target window to the foreground and activate it."""
        win = WindowManager.find_window(query)
        if not win:
            return False
        try:
            if win.isMinimized:
                win.restore()
            win.activate()
            return True
        except Exception:
            return False
