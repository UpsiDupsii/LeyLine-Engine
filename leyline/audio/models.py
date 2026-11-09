"""Data models for audio synthesis and commentator events."""

from __future__ import annotations

from enum import Enum
from pathlib import Path

from pydantic import BaseModel, Field


class CommentatorPersona(str, Enum):
    """Broadcaster personality profiles for commentary style."""

    HYPE = "hype"
    ANALYTICAL = "analytical"
    SARCASTIC = "sarcastic"
    CASUAL = "casual"


class GameEventType(str, Enum):
    """Categorized gameplay occurrences triggering commentary."""

    MATCH_MERGE = "match_merge"
    VALLEY_DROP = "valley_drop"
    RED_LINE_DANGER = "red_line_danger"
    CHAIN_REACTION = "chain_reaction"
    GAME_START = "game_start"
    GAME_OVER = "game_over"
    IDLE_BANTER = "idle_banter"


class GameEvent(BaseModel):
    """Structured telemetry event emitted by the gamer runner to the commentator."""

    event_type: GameEventType = Field(default=GameEventType.MATCH_MERGE)
    ball_tier: str = Field(default="Small Light Blue", description="Active or target ball tier")
    target_x: float = Field(default=0.5, ge=0.0, le=1.0, description="Horizontal drop fraction")
    danger_level: float = Field(
        default=0.0, ge=0.0, le=1.0, description="Proximity to red limit line (0=safe, 1=overflow)"
    )
    details: str = Field(default="", description="Contextual description of the play")


class VoiceConfig(BaseModel):
    """Configuration for Microsoft Edge Neural TTS voice synthesis."""

    voice_name: str = Field(
        default="en-US-ChristopherNeural",
        description="High-fidelity neural voice identifier",
    )
    rate: str = Field(
        default="+5%", description="Speech rate adjustment (e.g. +5% for energetic pacing)"
    )
    pitch: str = Field(default="+0Hz", description="Speech pitch adjustment")
    volume: str = Field(default="+0%", description="Speech volume adjustment")
    output_dir: Path = Field(
        default=Path("output/audio"),
        description="Destination directory for audio outputs and live subtitles",
    )


class CommentarySnippet(BaseModel):
    """Synthesized commentary line with timing and text metadata."""

    text: str = Field(description="Transcribed broadcast commentary script")
    audio_path: str = Field(description="Absolute path to the synthesized audio file")
    duration_seconds: float = Field(ge=0.0, description="Duration of speech in seconds")
    timestamp: float = Field(description="Epoch timestamp when commentary was generated")
    persona: CommentatorPersona = Field(default=CommentatorPersona.HYPE)
