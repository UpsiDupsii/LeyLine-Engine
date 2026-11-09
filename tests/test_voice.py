"""Tests for the NeuralVoiceEngine and audio models."""

from pathlib import Path

from leyline.audio.models import (
    GameEvent,
    GameEventType,
    VoiceConfig,
)
from leyline.audio.voice import NeuralVoiceEngine


def test_voice_config_defaults() -> None:
    config = VoiceConfig()
    assert "ChristopherNeural" in config.voice_name
    assert config.rate == "+5%"
    assert config.output_dir == Path("output/audio")


def test_neural_voice_engine_mock_mode(tmp_path: Path) -> None:
    config = VoiceConfig(output_dir=tmp_path)
    engine = NeuralVoiceEngine(config=config, mock_mode=True)
    assert engine.is_speaking() is False

    # Mock synthesize
    audio_file = engine.synthesize("Hello world", output_path=tmp_path / "test.mp3")
    assert audio_file.exists()

    # Subtitle updates
    engine.update_subtitles("Test subtitle text")
    assert engine.subtitles_path.read_text(encoding="utf-8") == "Test subtitle text"

    engine.clear_subtitles()
    assert engine.subtitles_path.read_text(encoding="utf-8") == ""


def test_game_event_model() -> None:
    event = GameEvent(
        event_type=GameEventType.MATCH_MERGE,
        ball_tier="Small Light Blue",
        target_x=0.29,
        danger_level=0.2,
        details="Fusing two blue balls",
    )
    assert event.event_type == GameEventType.MATCH_MERGE
    assert event.ball_tier == "Small Light Blue"
    assert event.target_x == 0.29


def test_voice_engine_speak_mock(tmp_path: Path) -> None:
    config = VoiceConfig(output_dir=tmp_path)
    engine = NeuralVoiceEngine(config=config, mock_mode=True)
    result = engine.speak("What a play!", update_obs=True)
    assert result is not None
    assert result.exists()
    assert engine.subtitles_path.read_text(encoding="utf-8") == "What a play!"
