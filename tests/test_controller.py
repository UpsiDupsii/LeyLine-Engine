"""Tests for the virtual keyboard controller."""

import pytest
from pydantic import ValidationError

from leyline.controller.keyboard import KeyboardController
from leyline.controller.models import ActionCommand, GameAction


def test_action_command_model() -> None:
    cmd = ActionCommand(action=GameAction.LEFT, duration=0.1, cooldown=0.05)
    assert cmd.action == GameAction.LEFT
    assert cmd.duration == 0.1
    assert cmd.cooldown == 0.05

    # Duration boundary tests
    with pytest.raises(ValidationError):
        ActionCommand(duration=0.001)

    with pytest.raises(ValidationError):
        ActionCommand(duration=5.0)


def test_controller_initialization() -> None:
    ctrl_arrows = KeyboardController(layout="arrows", mock_mode=True)
    assert ctrl_arrows.layout == "arrows"
    assert ctrl_arrows.mock_mode is True

    ctrl_wasd = KeyboardController(layout="wasd", mock_mode=True)
    assert ctrl_wasd.layout == "wasd"

    with pytest.raises(ValueError, match="Unsupported layout"):
        KeyboardController(layout="invalid_layout", mock_mode=True)


def test_key_resolution() -> None:
    ctrl = KeyboardController(layout="arrows", mock_mode=True)
    assert ctrl._resolve_key(GameAction.LEFT) is not None
    assert ctrl._resolve_key("RIGHT") is not None
    assert ctrl._resolve_key(GameAction.NONE) is None
    assert ctrl._resolve_key("INVALID") is None


def test_press_and_release_in_mock_mode() -> None:
    ctrl = KeyboardController(layout="arrows", mock_mode=True)
    assert ctrl.active_keys == set()

    # Press LEFT
    success = ctrl.press(GameAction.LEFT)
    assert success is True
    assert len(ctrl.active_keys) == 1

    # Release LEFT
    success_rel = ctrl.release(GameAction.LEFT)
    assert success_rel is True
    assert ctrl.active_keys == set()

    # Releasing when not pressed returns False
    assert ctrl.release(GameAction.LEFT) is False

    # NONE returns False
    assert ctrl.press(GameAction.NONE) is False


def test_tap_action() -> None:
    ctrl = KeyboardController(layout="arrows", mock_mode=True)
    # Tapping NONE should return False
    assert ctrl.tap_action(GameAction.NONE) is False

    # Tapping valid action should return True
    assert ctrl.tap_action(GameAction.RIGHT) is True


def test_release_all() -> None:
    ctrl = KeyboardController(layout="arrows", mock_mode=True)
    ctrl.press(GameAction.UP)
    ctrl.press(GameAction.SPACE)
    assert len(ctrl.active_keys) == 2

    ctrl.release_all()
    assert ctrl.active_keys == set()
