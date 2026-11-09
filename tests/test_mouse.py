"""Tests for the MouseController pointer simulator."""

from leyline.controller.mouse import MouseController
from leyline.vision.models import ScreenRegion


def test_mouse_controller_mock_mode() -> None:
    ctrl = MouseController(mock_mode=True)
    assert ctrl.set_position(100, 200) is True
    assert ctrl.position == (100, 200)
    assert ctrl.click("left") is True
    assert ctrl.click("right") is True


def test_mouse_controller_drop_at() -> None:
    ctrl = MouseController(mock_mode=True)
    # Container at left=100, top=100, width=500, height=600
    region = ScreenRegion(left=100, top=100, width=500, height=600)

    # Drop at center (0.50): 100 + 0.50 * 500 = 350
    x, y = ctrl.drop_at(region, x_fraction=0.50, y_offset_pixels=30, settle_time=0.0)
    assert x == 350
    assert y == 130

    # Drop at left boundary (0.0): clamped to 0.08 -> 100 + 0.08 * 500 = 140
    x_left, _ = ctrl.drop_at(region, x_fraction=0.0, settle_time=0.0)
    assert x_left == 140

    # Drop at right boundary (1.0): clamped to 0.92 -> 100 + 0.92 * 500 = 560
    x_right, _ = ctrl.drop_at(region, x_fraction=1.0, settle_time=0.0)
    assert x_right == 560
