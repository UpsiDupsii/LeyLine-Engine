"""Tests for the GamerAgent decision engine."""

from leyline.agents.models import PlayerDecision
from leyline.agents.player import GamerAgent
from leyline.controller.models import GameAction


def test_player_decision_model() -> None:
    decision = PlayerDecision(
        action=GameAction.LEFT,
        confidence=0.92,
        reason="Dodge oncoming barrier",
        latency_ms=350.5,
    )
    assert decision.action == GameAction.LEFT
    assert decision.confidence == 0.92
    assert decision.latency_ms == 350.5
    assert "barrier" in decision.reason


def test_agent_mock_mode() -> None:
    agent = GamerAgent(mock_mode=True)
    decision = agent.decide_action(b"fake_jpeg_bytes")
    assert decision.action == GameAction.NONE
    assert decision.confidence == 1.0
    assert len(agent.history) == 1


def test_parse_valid_json_response() -> None:
    agent = GamerAgent(mock_mode=True)
    raw_json = '{"action": "RIGHT", "confidence": 0.88, "reason": "Lane clear on right"}'
    decision = agent._parse_response(raw_json, latency_ms=210.0)
    assert decision.action == GameAction.RIGHT
    assert decision.confidence == 0.88
    assert decision.reason == "Lane clear on right"
    assert decision.latency_ms == 210.0


def test_parse_markdown_wrapped_json() -> None:
    agent = GamerAgent(mock_mode=True)
    raw_markdown = (
        '```json\n{"action": "SPACE", "confidence": 0.95, "reason": "Jump over obstacle"}\n```'
    )
    decision = agent._parse_response(raw_markdown, latency_ms=180.0)
    assert decision.action == GameAction.SPACE
    assert decision.confidence == 0.95


def test_parse_fallback_keywords() -> None:
    agent = GamerAgent(mock_mode=True)
    freeform = "I recommend moving to the LEFT because an obstacle is ahead."
    decision = agent._parse_response(freeform, latency_ms=300.0)
    assert decision.action == GameAction.LEFT
    assert decision.confidence == 0.6


def test_parse_invalid_format() -> None:
    agent = GamerAgent(mock_mode=True)
    garbage = "Random text with no instructions."
    decision = agent._parse_response(garbage, latency_ms=250.0)
    assert decision.action == GameAction.NONE
    assert decision.confidence == 0.0
