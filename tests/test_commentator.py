"""Tests for CommentatorAgent and CommentaryOrchestrator."""

import time
from pathlib import Path

from leyline.agents.commentator import CommentatorAgent
from leyline.audio.models import (
    CommentatorPersona,
    GameEvent,
    GameEventType,
    VoiceConfig,
)
from leyline.audio.orchestrator import CommentaryOrchestrator


def test_commentator_agent_personas() -> None:
    for persona in [
        CommentatorPersona.HYPE,
        CommentatorPersona.ANALYTICAL,
        CommentatorPersona.SARCASTIC,
        CommentatorPersona.CASUAL,
    ]:
        agent = CommentatorAgent(persona=persona, mock_mode=True)
        event = GameEvent(
            event_type=GameEventType.MATCH_MERGE,
            ball_tier="Small Light Blue",
            target_x=0.25,
        )
        line = agent.generate_commentary(event)
        assert isinstance(line, str)
        assert len(line) > 10
        # Zero emoji verification
        assert all(ord(c) < 127000 for c in line)


def test_commentator_agent_non_repetition() -> None:
    agent = CommentatorAgent(persona=CommentatorPersona.HYPE, mock_mode=True)
    event = GameEvent(
        event_type=GameEventType.MATCH_MERGE,
        ball_tier="Small Light Blue",
        target_x=0.25,
    )

    generated = set()
    for _ in range(5):
        line = agent.generate_commentary(event)
        generated.add(line)

    # Should produce varied phrases from the pool
    assert len(generated) >= 2


def test_commentator_event_types() -> None:
    agent = CommentatorAgent(persona=CommentatorPersona.HYPE, mock_mode=True)
    for et in [
        GameEventType.VALLEY_DROP,
        GameEventType.RED_LINE_DANGER,
        GameEventType.CHAIN_REACTION,
        GameEventType.GAME_START,
        GameEventType.GAME_OVER,
    ]:
        ev = GameEvent(event_type=et, ball_tier="Medium Purple", target_x=0.65)
        text = agent.generate_commentary(ev)
        assert isinstance(text, str)
        assert len(text) > 5


def test_commentary_orchestrator_mock(tmp_path: Path) -> None:
    config = VoiceConfig(output_dir=tmp_path)
    orchestrator = CommentaryOrchestrator(
        voice_config=config,
        persona=CommentatorPersona.HYPE,
        cooldown_seconds=0.1,
        mock_mode=True,
    )

    orchestrator.start()
    ev = GameEvent(
        event_type=GameEventType.MATCH_MERGE,
        ball_tier="Small Light Blue",
        target_x=0.30,
    )
    posted = orchestrator.post_event(ev)
    assert posted is True

    # Allow worker thread to process
    time.sleep(0.6)
    assert len(orchestrator.current_text) > 0

    orchestrator.stop()
