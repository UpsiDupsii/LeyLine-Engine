"""Keyboard controller simulation for autonomous game inputs using pynput."""

import time
from typing import Any

from pynput.keyboard import Controller as PynputController
from pynput.keyboard import Key

from leyline.controller.models import ActionCommand, GameAction

KEY_MAPPINGS: dict[str, dict[GameAction, Any]] = {
    "arrows": {
        GameAction.LEFT: Key.left,
        GameAction.RIGHT: Key.right,
        GameAction.UP: Key.up,
        GameAction.DOWN: Key.down,
        GameAction.SPACE: Key.space,
        GameAction.NONE: None,
    },
    "wasd": {
        GameAction.LEFT: "a",
        GameAction.RIGHT: "d",
        GameAction.UP: "w",
        GameAction.DOWN: "s",
        GameAction.SPACE: Key.space,
        GameAction.NONE: None,
    },
}


class KeyboardController:
    """Low-latency virtual keyboard controller with safety limits and layout profiles."""

    def __init__(self, layout: str = "arrows", mock_mode: bool = False) -> None:
        self.layout = layout.lower()
        self.mock_mode = mock_mode
        self._keyboard = None if mock_mode else PynputController()
        self._pressed_keys: set[Any] = set()
        self._last_action_time: float = 0.0

        if self.layout not in KEY_MAPPINGS:
            raise ValueError(
                f"Unsupported layout '{layout}'. Choose from: {list(KEY_MAPPINGS.keys())}"
            )
        self.mapping = KEY_MAPPINGS[self.layout]

    def _resolve_key(self, action: GameAction | str) -> Any:
        if isinstance(action, str):
            try:
                action_enum = GameAction(action.upper())
            except ValueError:
                return None
        else:
            action_enum = action

        return self.mapping.get(action_enum)

    def press(self, action: GameAction | str) -> bool:
        """Hold down the key corresponding to the action."""
        key = self._resolve_key(action)
        if key is None:
            return False

        if not self.mock_mode and self._keyboard is not None:
            self._keyboard.press(key)
        self._pressed_keys.add(key)
        return True

    def release(self, action: GameAction | str) -> bool:
        """Release the key corresponding to the action."""
        key = self._resolve_key(action)
        if key is None or key not in self._pressed_keys:
            return False

        if not self.mock_mode and self._keyboard is not None:
            self._keyboard.release(key)
        self._pressed_keys.discard(key)
        return True

    def tap_action(self, command: ActionCommand | GameAction | str) -> bool:
        """Press and release a key with precise hold duration.

        Args:
            command: ActionCommand instance, GameAction enum, or action string.

        Returns:
            bool: True if key was tapped, False if action was NONE or invalid.
        """
        if isinstance(command, ActionCommand):
            action = command.action
            duration = command.duration
            cooldown = command.cooldown
        else:
            action = command if isinstance(command, GameAction) else GameAction(command.upper())
            duration = 0.08
            cooldown = 0.02

        now = time.time()
        if now - self._last_action_time < cooldown:
            return False

        key = self._resolve_key(action)
        if key is None:
            return False

        if not self.mock_mode and self._keyboard is not None:
            self._keyboard.press(key)
            self._pressed_keys.add(key)
            time.sleep(duration)
            self._keyboard.release(key)
            self._pressed_keys.discard(key)
        else:
            time.sleep(min(duration, 0.01))

        self._last_action_time = time.time()
        return True

    def release_all(self) -> None:
        """Emergency safety method to release all currently pressed keys."""
        if not self.mock_mode and self._keyboard is not None:
            for key in list(self._pressed_keys):
                try:
                    self._keyboard.release(key)
                except Exception:
                    pass
        self._pressed_keys.clear()

    @property
    def active_keys(self) -> set[Any]:
        """Return the set of keys currently pressed down."""
        return set(self._pressed_keys)
