"""DirectInput hardware scan code controller for Windows games and browser canvas."""

import ctypes
import os
import time
from ctypes import wintypes

from leyline.controller.models import ActionCommand, GameAction

# Win32 Constants
INPUT_KEYBOARD = 1
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_SCANCODE = 0x0008
KEYEVENTF_EXTENDEDKEY = 0x0001

# Hardware Scan Codes (DirectInput)
SCAN_CODES: dict[str, tuple[int, bool]] = {
    # Key: (scancode, is_extended)
    "w": (0x11, False),
    "a": (0x1E, False),
    "s": (0x1F, False),
    "d": (0x20, False),
    "e": (0x12, False),
    "space": (0x39, False),
    "up": (0x48, True),
    "left": (0x4B, True),
    "right": (0x4D, True),
    "down": (0x50, True),
}


class KeyBdInput(ctypes.Structure):
    _fields_ = [
        ("wVk", wintypes.WORD),
        ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.c_void_p),
    ]


class HardwareInput(ctypes.Structure):
    _fields_ = [
        ("uMsg", wintypes.DWORD),
        ("wParamL", wintypes.WORD),
        ("wParamH", wintypes.WORD),
    ]


class MouseInput(ctypes.Structure):
    _fields_ = [
        ("dx", wintypes.LONG),
        ("dy", wintypes.LONG),
        ("mouseData", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.c_void_p),
    ]


class Input_I(ctypes.Union):
    _fields_ = [
        ("ki", KeyBdInput),
        ("mi", MouseInput),
        ("hi", HardwareInput),
    ]


class Input(ctypes.Structure):
    _fields_ = [
        ("type", wintypes.DWORD),
        ("ii", Input_I),
    ]


class DirectInputController:
    """Simulates real hardware keyboard scan codes for Unity, Roblox, and browser games."""

    def __init__(self, layout: str = "wasd", mock_mode: bool = False) -> None:
        self.layout = layout.lower()
        self.mock_mode = mock_mode or os.name != "nt"
        self._pressed_keys: set[str] = set()
        self._user32 = ctypes.windll.user32 if os.name == "nt" else None

    def _send_key_event(self, key_name: str, key_up: bool = False) -> bool:
        if self.mock_mode or not self._user32:
            return True

        key_info = SCAN_CODES.get(key_name.lower())
        if not key_info:
            return False

        scan_code, is_extended = key_info
        flags = KEYEVENTF_SCANCODE
        if is_extended:
            flags |= KEYEVENTF_EXTENDEDKEY
        if key_up:
            flags |= KEYEVENTF_KEYUP

        inp = Input(
            type=INPUT_KEYBOARD,
            ii=Input_I(
                ki=KeyBdInput(
                    wVk=0,
                    wScan=scan_code,
                    dwFlags=flags,
                    time=0,
                    dwExtraInfo=None,
                )
            ),
        )
        self._user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(inp))
        return True

    def _resolve_action_keys(self, action: GameAction | str) -> list[str]:
        act = action if isinstance(action, GameAction) else GameAction(action.upper())

        # Map to wasd or arrows
        if self.layout == "wasd":
            mapping: dict[GameAction, list[str]] = {
                GameAction.FORWARD: ["w"],
                GameAction.UP: ["w"],
                GameAction.LEFT: ["a"],
                GameAction.RIGHT: ["d"],
                GameAction.REVERSE: ["s"],
                GameAction.DOWN: ["s"],
                GameAction.FORWARD_LEFT: ["w", "a"],
                GameAction.FORWARD_RIGHT: ["w", "d"],
                GameAction.SPACE: ["space"],
                GameAction.INTERACT: ["e"],
                GameAction.BRAKE: ["s"],
                GameAction.NONE: [],
            }
        else:
            mapping = {
                GameAction.FORWARD: ["up"],
                GameAction.UP: ["up"],
                GameAction.LEFT: ["left"],
                GameAction.RIGHT: ["right"],
                GameAction.REVERSE: ["down"],
                GameAction.DOWN: ["down"],
                GameAction.FORWARD_LEFT: ["up", "left"],
                GameAction.FORWARD_RIGHT: ["up", "right"],
                GameAction.SPACE: ["space"],
                GameAction.INTERACT: ["space"],
                GameAction.BRAKE: ["down"],
                GameAction.NONE: [],
            }

        return mapping.get(act, [])

    def press_keys(self, keys: list[str]) -> None:
        """Hold down multiple keys simultaneously."""
        for k in keys:
            self._send_key_event(k, key_up=False)
            self._pressed_keys.add(k)

    def release_keys(self, keys: list[str]) -> None:
        """Release specified keys."""
        for k in keys:
            self._send_key_event(k, key_up=True)
            self._pressed_keys.discard(k)

    def execute_action(
        self,
        command: ActionCommand | GameAction | str,
        duration: float | None = None,
    ) -> bool:
        """Execute a sustained vehicular maneuver (e.g. forward + turn).

        Args:
            command: ActionCommand, GameAction, or action string.
            duration: Key hold duration in seconds. Overrides command duration if set.

        Returns:
            bool: True if action was executed.
        """
        if isinstance(command, ActionCommand):
            action = command.action
            hold_time = duration if duration is not None else command.duration
        else:
            action = command if isinstance(command, GameAction) else GameAction(command.upper())
            hold_time = duration if duration is not None else 0.25

        keys = self._resolve_action_keys(action)
        if not keys:
            return False

        # Release any old keys not needed for this action
        for k in list(self._pressed_keys):
            if k not in keys:
                self._send_key_event(k, key_up=True)
                self._pressed_keys.discard(k)

        # Press keys and hold for duration
        self.press_keys(keys)
        time.sleep(hold_time)
        self.release_keys(keys)
        return True

    def release_all(self) -> None:
        """Emergency release for all currently held keys."""
        for k in list(self._pressed_keys):
            self._send_key_event(k, key_up=True)
        self._pressed_keys.clear()

    @property
    def active_keys(self) -> set[str]:
        return set(self._pressed_keys)
