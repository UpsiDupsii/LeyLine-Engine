"""Tests for the BallGuysAgent puzzle solver brain and Computer Vision puzzle detector."""

import numpy as np

from leyline.agents.ball_guys_agent import BallGuysAgent, DropDecision
from leyline.vision.puzzle_detector import (
    BallInfo,
    ContainerBounds,
    PuzzleDetector,
    PuzzleState,
    classify_ball_color,
)


def test_ball_guys_agent_mock_mode() -> None:
    agent = BallGuysAgent(mock_mode=True)
    decision = agent.decide_drop(b"fake_jpeg_bytes")
    assert isinstance(decision, DropDecision)
    assert 0.0 <= decision.drop_x <= 1.0
    assert len(agent.history) == 1


def test_ball_guys_parse_valid_json() -> None:
    agent = BallGuysAgent(mock_mode=True)
    raw_json = (
        '{"drop_x": 0.25, "target_match": "Small blue ball on left", '
        '"reason": "Trigger merge with matching blue ball", "confidence": 0.95}'
    )
    decision = agent._parse_json(raw_json, latency_ms=180.0)
    assert decision.drop_x == 0.25
    assert decision.target_match == "Small blue ball on left"
    assert "merge" in decision.reason
    assert decision.confidence == 0.95
    assert decision.latency_ms == 180.0


def test_ball_guys_clamp_boundaries() -> None:
    agent = BallGuysAgent(mock_mode=True)
    # Beyond left wall (< 0.12)
    decision_left = agent._parse_json('{"drop_x": -0.5}', latency_ms=100.0)
    assert decision_left.drop_x == 0.12

    # Beyond right wall (> 0.88)
    decision_right = agent._parse_json('{"drop_x": 1.5}', latency_ms=100.0)
    assert decision_right.drop_x == 0.88


def test_ball_guys_parse_fallback() -> None:
    agent = BallGuysAgent(mock_mode=True)
    decision = agent._parse_json("Not a valid json response", latency_ms=200.0)
    assert decision.drop_x == 0.5


def test_classify_ball_color() -> None:
    # Purple: high B and R, low G
    tier_purple, name_purple = classify_ball_color((240, 20, 140), radius=30)
    assert tier_purple == 2
    assert "Purple" in name_purple

    # Light Blue: high B and G
    tier_blue, name_blue = classify_ball_color((235, 160, 85), radius=15)
    assert tier_blue == 1
    assert "Blue" in name_blue


def test_find_best_drop_target_direct_match() -> None:
    container = ContainerBounds(left=100, top=50, right=300, bottom=350, width=200, height=300)
    # Active hanging ball is Tier 1 (Light Blue)
    hanging = BallInfo(
        x=200,
        y=70,
        radius=12.0,
        tier=1,
        color_name="Small Light Blue",
        fraction_x=0.5,
        fraction_y=0.06,
    )
    # Resting ball is Tier 1 at fraction_x=0.28
    resting_match = BallInfo(
        x=156,
        y=320,
        radius=12.0,
        tier=1,
        color_name="Small Light Blue",
        fraction_x=0.28,
        fraction_y=0.90,
    )
    state = PuzzleState(
        container=container,
        hanging_ball=hanging,
        resting_balls=[resting_match],
        red_line_y=110,
        column_heights=[0.0, 0.1, 0.0, 0.0, 0.0],
    )

    drop_x, target, reason, conf = PuzzleDetector.find_best_drop_target(state)
    assert abs(drop_x - 0.28) < 0.01
    assert "Direct match" in target
    assert "merge" in reason
    assert conf >= 0.90


def test_find_best_drop_target_valley_leveling() -> None:
    container = ContainerBounds(left=100, top=50, right=300, bottom=350, width=200, height=300)
    # Active hanging ball is Tier 2 (Purple)
    hanging = BallInfo(
        x=200,
        y=70,
        radius=25.0,
        tier=2,
        color_name="Medium Purple",
        fraction_x=0.5,
        fraction_y=0.06,
    )
    # Resting balls are all Tier 1 (no tier 2 match)
    # Columns: [0.16, 0.33, 0.50, 0.67, 0.84]
    # Column 1 has 0 height (lowest valley)
    state = PuzzleState(
        container=container,
        hanging_ball=hanging,
        resting_balls=[],
        red_line_y=110,
        column_heights=[0.0, 0.35, 0.50, 0.20, 0.40],
    )

    drop_x, target, reason, conf = PuzzleDetector.find_best_drop_target(state)
    assert abs(drop_x - 0.16) < 0.01
    assert "Valley" in target
    assert "leveling" in reason


def test_verify_needle_alignment() -> None:
    container = ContainerBounds(left=0, top=0, right=200, bottom=200, width=200, height=200)
    # Create synthetic frame with needle centered at x=100
    frame = np.full((200, 200, 3), 50, dtype=np.uint8)
    # Draw needle/ball at x=100
    frame[5:35, 96:104] = 220

    # Target fraction 0.50 corresponds to x=100
    aligned, actual_f, err = PuzzleDetector.verify_needle_alignment(
        frame, target_fraction=0.50, container=container, tolerance_pixels=6
    )
    assert aligned is True
    assert abs(err) <= 6.0


def test_ball_guys_decide_from_frame() -> None:
    agent = BallGuysAgent(mock_mode=True)
    frame = np.full((300, 300, 3), 60, dtype=np.uint8)
    decision, state = agent.decide_drop_from_frame(frame)
    assert isinstance(decision, DropDecision)
    assert isinstance(state, PuzzleState)
    assert 0.12 <= decision.drop_x <= 0.88
