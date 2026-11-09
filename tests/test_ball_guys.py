"""Tests for the BallGuysAgent puzzle solver brain."""

from leyline.agents.ball_guys_agent import BallGuysAgent, DropDecision


def test_ball_guys_agent_mock_mode() -> None:
    agent = BallGuysAgent(mock_mode=True)
    decision = agent.decide_drop(b"fake_jpeg_bytes")
    assert isinstance(decision, DropDecision)
    assert decision.drop_x == 0.5
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
    # Beyond left wall (< 0.08)
    decision_left = agent._parse_json('{"drop_x": -0.5}', latency_ms=100.0)
    assert decision_left.drop_x == 0.08

    # Beyond right wall (> 0.92)
    decision_right = agent._parse_json('{"drop_x": 1.5}', latency_ms=100.0)
    assert decision_right.drop_x == 0.92


def test_ball_guys_parse_fallback() -> None:
    agent = BallGuysAgent(mock_mode=True)
    decision = agent._parse_json("Not a valid json response", latency_ms=200.0)
    assert decision.drop_x == 0.5
