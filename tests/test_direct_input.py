"""Tests for the DirectInput hardware scan code controller."""

from leyline.controller.direct_input import DirectInputController
from leyline.controller.models import ActionCommand, GameAction


def test_direct_input_wasd_resolution() -> None:
    ctrl = DirectInputController(layout="wasd", mock_mode=True)
    assert ctrl._resolve_action_keys(GameAction.FORWARD) == ["w"]
    assert ctrl._resolve_action_keys(GameAction.FORWARD_LEFT) == ["w", "a"]
    assert ctrl._resolve_action_keys(GameAction.FORWARD_RIGHT) == ["w", "d"]
    assert ctrl._resolve_action_keys(GameAction.REVERSE) == ["s"]
    assert ctrl._resolve_action_keys(GameAction.INTERACT) == ["e"]
    assert ctrl._resolve_action_keys(GameAction.NONE) == []


def test_direct_input_arrows_resolution() -> None:
    ctrl = DirectInputController(layout="arrows", mock_mode=True)
    assert ctrl._resolve_action_keys(GameAction.FORWARD) == ["up"]
    assert ctrl._resolve_action_keys(GameAction.FORWARD_LEFT) == ["up", "left"]
    assert ctrl._resolve_action_keys(GameAction.FORWARD_RIGHT) == ["up", "right"]
    assert ctrl._resolve_action_keys(GameAction.REVERSE) == ["down"]
    assert ctrl._resolve_action_keys(GameAction.INTERACT) == ["space"]


def test_direct_input_execute_action() -> None:
    ctrl = DirectInputController(layout="wasd", mock_mode=True)
    assert ctrl.active_keys == set()

    # Execute forward-left maneuver
    success = ctrl.execute_action(GameAction.FORWARD_LEFT, duration=0.01)
    assert success is True
    # Keys should be released after execution
    assert ctrl.active_keys == set()

    # ActionCommand execution
    cmd = ActionCommand(action=GameAction.FORWARD, duration=0.01)
    success_cmd = ctrl.execute_action(cmd)
    assert success_cmd is True


def test_direct_input_release_all() -> None:
    ctrl = DirectInputController(layout="wasd", mock_mode=True)
    ctrl.press_keys(["w", "d"])
    assert ctrl.active_keys == {"w", "d"}

    ctrl.release_all()
    assert ctrl.active_keys == set()
