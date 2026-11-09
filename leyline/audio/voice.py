"""High-fidelity asynchronous Neural Voice Engine using Microsoft Edge Neural TTS.

Synthesizes studio-grade broadcast speech with natural prosody and pronunciation,
plays audio non-blocking via pygame mixer, and updates live subtitles for OBS streaming.
"""

from __future__ import annotations

import asyncio
import time
from pathlib import Path

import edge_tts
import pygame

from leyline.audio.models import VoiceConfig


class NeuralVoiceEngine:
    """Manages neural voice synthesis, audio playback, and live stream subtitle updates."""

    RECOMMENDED_VOICES = {
        "esports_caster": "en-US-ChristopherNeural",  # Authoritative, broadcast-quality esports caster
        "hype_streamer": "en-US-GuyNeural",  # Energetic, engaging livestream host
        "studio_expressive": "en-US-AndrewMultilingualNeural",  # Expressive, ultra-high-fidelity voice
        "female_caster": "en-US-AriaNeural",  # Dynamic, crisp female shoutcaster
        "british_caster": "en-GB-RyanNeural",  # Analytical British play-by-play caster
        "chill_gamer": "en-US-EricNeural",  # Friendly, casual streamer voice
    }

    def __init__(
        self,
        config: VoiceConfig | None = None,
        mock_mode: bool = False,
    ) -> None:
        self.config = config or VoiceConfig()
        self.mock_mode = mock_mode
        self.output_dir = Path(self.config.output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.subtitles_path = self.output_dir / "subtitles.txt"

        self._mixer_initialized = False
        if not self.mock_mode:
            self._init_mixer()

    def _init_mixer(self) -> None:
        """Safely initialize pygame audio mixer."""
        if not self._mixer_initialized:
            try:
                # 44.1kHz, 16-bit signed, 2 stereo channels
                pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=1024)
                self._mixer_initialized = True
            except Exception as exc:
                print(
                    f"Warning: Audio device initialization failed ({exc}). Running in silent mode."
                )
                self.mock_mode = True

    async def synthesize_async(
        self,
        text: str,
        output_path: Path | str,
        voice: str | None = None,
        rate: str | None = None,
        pitch: str | None = None,
    ) -> Path:
        """Asynchronously synthesize text to an audio file using edge-tts."""
        dest = Path(output_path)
        dest.parent.mkdir(parents=True, exist_ok=True)

        if self.mock_mode:
            dest.write_text("mock_audio_content", encoding="utf-8")
            return dest

        v = voice or self.config.voice_name
        r = rate or self.config.rate
        p = pitch or self.config.pitch

        communicate = edge_tts.Communicate(text=text, voice=v, rate=r, pitch=p)
        await communicate.save(str(dest))
        return dest

    def synthesize(
        self,
        text: str,
        output_path: Path | str | None = None,
        voice: str | None = None,
        rate: str | None = None,
        pitch: str | None = None,
    ) -> Path:
        """Synchronous wrapper for neural speech synthesis."""
        target_path = output_path or (self.output_dir / f"speech_{int(time.time() * 1000)}.mp3")
        try:
            return asyncio.run(
                self.synthesize_async(
                    text=text,
                    output_path=target_path,
                    voice=voice,
                    rate=rate,
                    pitch=pitch,
                )
            )
        except Exception as exc:
            print(f"Synthesis error: {exc}")
            dest = Path(target_path)
            dest.write_text("fallback_audio", encoding="utf-8")
            return dest

    def play(self, audio_path: Path | str) -> bool:
        """Play an audio file asynchronously without blocking the perception loop."""
        if self.mock_mode or not self._mixer_initialized:
            return True

        target = Path(audio_path)
        if not target.exists():
            return False

        try:
            pygame.mixer.music.load(str(target))
            pygame.mixer.music.play()
            return True
        except Exception as exc:
            print(f"Playback error: {exc}")
            return False

    def is_speaking(self) -> bool:
        """Check whether audio is currently playing."""
        if self.mock_mode or not self._mixer_initialized:
            return False
        try:
            return bool(pygame.mixer.music.get_busy())
        except Exception:
            return False

    def stop(self) -> None:
        """Stop current audio playback immediately."""
        if self._mixer_initialized and not self.mock_mode:
            try:
                pygame.mixer.music.stop()
            except Exception:
                pass
        self.clear_subtitles()

    def update_subtitles(self, text: str) -> None:
        """Update live text file for OBS Studio Text (GDI+) overlay."""
        try:
            self.subtitles_path.write_text(text.strip(), encoding="utf-8")
        except Exception:
            pass

    def clear_subtitles(self) -> None:
        """Clear OBS live stream subtitle text."""
        try:
            self.subtitles_path.write_text("", encoding="utf-8")
        except Exception:
            pass

    def speak(
        self,
        text: str,
        voice: str | None = None,
        update_obs: bool = True,
    ) -> Path | None:
        """Synthesize text, update OBS subtitles, and begin non-blocking playback."""
        if not text or not text.strip():
            return None

        # Format audio filename
        timestamp = int(time.time() * 1000)
        output_file = self.output_dir / f"commentary_{timestamp}.mp3"
        latest_file = self.output_dir / "commentary_latest.mp3"

        if update_obs:
            self.update_subtitles(text)

        audio_file = self.synthesize(text=text, output_path=output_file, voice=voice)

        # Copy to latest stream audio link
        if audio_file.exists() and not self.mock_mode:
            try:
                import shutil

                shutil.copyfile(audio_file, latest_file)
            except Exception:
                pass

        self.play(audio_file)
        return audio_file
