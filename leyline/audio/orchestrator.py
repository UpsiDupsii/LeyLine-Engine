"""Asynchronous commentary orchestrator coordinating speech synthesis and game events.

Decouples voice synthesis and audio playback from the gameplay loop so that speech
generation never causes frame drops or input lag.
"""

from __future__ import annotations

import queue
import threading
import time

from leyline.agents.commentator import CommentatorAgent
from leyline.audio.models import CommentatorPersona, GameEvent, VoiceConfig
from leyline.audio.voice import NeuralVoiceEngine


class CommentaryOrchestrator:
    """Manages an asynchronous queue of game events, voice synthesis, and broadcast audio."""

    def __init__(
        self,
        voice_config: VoiceConfig | None = None,
        persona: CommentatorPersona = CommentatorPersona.HYPE,
        cooldown_seconds: float = 3.0,
        mock_mode: bool = False,
    ) -> None:
        self.voice_config = voice_config or VoiceConfig()
        self.persona = persona
        self.cooldown_seconds = max(1.0, cooldown_seconds)
        self.mock_mode = mock_mode

        self.voice_engine = NeuralVoiceEngine(config=self.voice_config, mock_mode=mock_mode)
        self.agent = CommentatorAgent(persona=persona, mock_mode=mock_mode)

        self._queue: queue.Queue[GameEvent] = queue.Queue(maxsize=20)
        self._running = False
        self._worker_thread: threading.Thread | None = None
        self._last_speech_time = 0.0
        self._current_text = ""
        self._text_lock = threading.Lock()

    def start(self) -> None:
        """Start the background commentary worker thread."""
        if not self._running:
            self._running = True
            self._worker_thread = threading.Thread(target=self._commentary_worker, daemon=True)
            self._worker_thread.start()

    def stop(self) -> None:
        """Stop worker thread and halt audio playback."""
        self._running = False
        self.voice_engine.stop()
        if self._worker_thread and self._worker_thread.is_alive():
            self._worker_thread.join(timeout=1.0)

    def post_event(self, event: GameEvent) -> bool:
        """Push a game event to the commentary queue (non-blocking)."""
        try:
            self._queue.put_nowait(event)
            return True
        except queue.Full:
            return False

    def _commentary_worker(self) -> None:
        """Daemon worker executing event consumption, script generation, and speech."""
        while self._running:
            try:
                # Poll for an event with timeout
                event = self._queue.get(timeout=0.5)
            except queue.Empty:
                continue

            # Respect pacing cooldown and wait for any ongoing speech to finish
            now = time.time()
            time_since_speech = now - self._last_speech_time
            if time_since_speech < self.cooldown_seconds:
                sleep_needed = self.cooldown_seconds - time_since_speech
                time.sleep(sleep_needed)

            # Wait if the audio engine is actively speaking
            while self.voice_engine.is_speaking() and self._running:
                time.sleep(0.1)

            if not self._running:
                break

            # Generate commentary script
            commentary_text = self.agent.generate_commentary(event)
            with self._text_lock:
                self._current_text = commentary_text

            # Synthesize and play
            self.voice_engine.speak(commentary_text)
            self._last_speech_time = time.time()
            self._queue.task_done()

    @property
    def current_text(self) -> str:
        """Return the most recently spoken commentary line."""
        with self._text_lock:
            return self._current_text

    @property
    def is_speaking(self) -> bool:
        """Check whether the commentator is actively talking."""
        return self.voice_engine.is_speaking()
