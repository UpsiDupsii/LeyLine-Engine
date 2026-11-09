"""Tests for the real-time Subway Surfers reflex agent."""

import numpy as np

from leyline.agents.reflex import SubwayReflexAgent
from leyline.controller.models import GameAction


def test_reflex_empty_frame() -> None:
    agent = SubwayReflexAgent()
    # Create plain black frame (no edges/obstacles)
    clean_frame = np.zeros((400, 300, 3), dtype=np.uint8)
    decision = agent.decide_action_from_frame(clean_frame)

    assert decision.action == GameAction.NONE
    assert decision.confidence == 0.95
    assert decision.latency_ms >= 0.0


def test_reflex_obstacle_in_center_lane() -> None:
    agent = SubwayReflexAgent(sensitivity=3.0)
    agent.current_lane = 1  # Center lane

    frame = np.zeros((400, 300, 3), dtype=np.uint8)
    # Draw high-contrast obstacle (textured block) in the center corridor (X: 100 to 200, Y: 200 to 320)
    frame[200:320, 100:200, :] = 255
    # Add alternating noise to produce Canny edges
    frame[200:320:2, 100:200, :] = 0

    decision = agent.decide_action_from_frame(frame)
    # Should swerve left or right to evade the center obstacle
    assert decision.action in (GameAction.LEFT, GameAction.RIGHT)
    assert agent.current_lane in (0, 2)


def test_reflex_small_frame_fallback() -> None:
    agent = SubwayReflexAgent()
    tiny_frame = np.zeros((10, 10, 3), dtype=np.uint8)
    decision = agent.decide_action_from_frame(tiny_frame)
    assert decision.action == GameAction.NONE
