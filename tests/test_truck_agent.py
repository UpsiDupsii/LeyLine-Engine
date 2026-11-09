"""Tests for the TruckDriverAgent autonomous vehicle brain."""

from leyline.agents.truck_agent import TruckDriverAgent
from leyline.controller.models import GameAction


def test_truck_agent_mock_mode() -> None:
    agent = TruckDriverAgent(mock_mode=True)
    decision = agent.decide_driving_action(b"fake_jpeg_bytes")
    assert decision.action == GameAction.FORWARD
    assert decision.confidence == 1.0
    assert len(agent.history) == 1


def test_truck_agent_parse_json() -> None:
    agent = TruckDriverAgent(mock_mode=True)
    raw_json = (
        '{"action": "FORWARD_LEFT", "confidence": 0.92, "reason": "Steering towards garbage bin"}'
    )
    decision = agent._parse_json(raw_json, latency_ms=190.0)
    assert decision.action == GameAction.FORWARD_LEFT
    assert decision.confidence == 0.92
    assert "garbage" in decision.reason
    assert decision.latency_ms == 190.0


def test_truck_agent_parse_interact_action() -> None:
    agent = TruckDriverAgent(mock_mode=True)
    raw_json = '{"action": "INTERACT", "confidence": 0.98, "reason": "Dumping garbage at depot"}'
    decision = agent._parse_json(raw_json, latency_ms=150.0)
    assert decision.action == GameAction.INTERACT


def test_truck_agent_parse_fallback() -> None:
    agent = TruckDriverAgent(mock_mode=True)
    malformed = "Non-json text from model"
    decision = agent._parse_json(malformed, latency_ms=200.0)
    assert decision.action == GameAction.FORWARD
