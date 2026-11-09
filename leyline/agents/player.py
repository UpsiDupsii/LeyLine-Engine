"""Gamer Agent: Real-time visual perception and action planning using Multimodal Gemini."""

import json
import re
import socket
import time
from typing import Any

import requests

from leyline.agents.models import PlayerDecision
from leyline.config import GEMINI_API_KEY
from leyline.controller.models import GameAction


class GamerAgent:
    """Multimodal vision gamer agent that plans tactical gameplay actions."""

    SYSTEM_PROMPT = (
        "You are an elite AI gamer playing a real-time game. "
        "Analyze the provided screenshot of the game. Detect obstacles, road boundaries, "
        "and threats. Choose the best immediate action from: "
        "['LEFT', 'RIGHT', 'UP', 'DOWN', 'SPACE', 'NONE']. "
        "Respond ONLY with a JSON object in this format:\n"
        '{"action": "LEFT", "reason": "Avoid oncoming obstacle on right lane", "confidence": 0.95}'
    )

    def __init__(
        self,
        api_key: str = GEMINI_API_KEY,
        model_name: str = "gemini-2.5-flash",
        mock_mode: bool = False,
        timeout: float = 3.0,
    ) -> None:
        self.api_key = api_key
        self.model_name = model_name
        self.mock_mode = mock_mode
        self.timeout = timeout
        self.history: list[PlayerDecision] = []

    def _force_ipv4_if_needed(self) -> None:
        """Ensure socket address resolution prioritizes IPv4 to prevent connection reset errors."""
        try:
            orig_getaddrinfo = socket.getaddrinfo

            def ipv4_getaddrinfo(*args: Any, **kwargs: Any) -> list[Any]:
                res = orig_getaddrinfo(*args, **kwargs)
                v4 = [r for r in res if r[0] == socket.AF_INET]
                return v4 if v4 else res

            socket.getaddrinfo = ipv4_getaddrinfo
        except Exception:
            pass

    def decide_action(self, frame_bytes: bytes, base64_frame: str | None = None) -> PlayerDecision:
        """Analyze a game frame and return the recommended action.

        Args:
            frame_bytes: Raw JPEG/PNG image bytes.
            base64_frame: Optional precomputed base64 string of the frame.

        Returns:
            PlayerDecision: Tactical action, reasoning, confidence, and latency.
        """
        start_time = time.time()

        if self.mock_mode or not self.api_key:
            elapsed_ms = (time.time() - start_time) * 1000
            decision = PlayerDecision(
                action=GameAction.NONE,
                confidence=1.0,
                reason="Mock mode active or API key unset",
                latency_ms=elapsed_ms,
            )
            self.history.append(decision)
            return decision

        self._force_ipv4_if_needed()

        import base64

        b64_data = base64_frame or base64.b64encode(frame_bytes).decode("utf-8")

        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{self.model_name}:generateContent?key={self.api_key}"
        )
        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": self.SYSTEM_PROMPT},
                        {
                            "inline_data": {
                                "mime_type": "image/jpeg",
                                "data": b64_data,
                            }
                        },
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0.1,
                "response_mime_type": "application/json",
            },
        }

        try:
            resp = requests.post(url, json=payload, timeout=self.timeout)
            elapsed_ms = (time.time() - start_time) * 1000

            if resp.status_code == 200:
                data = resp.json()
                raw_text = (
                    data.get("candidates", [{}])[0]
                    .get("content", {})
                    .get("parts", [{}])[0]
                    .get("text", "")
                )
                return self._parse_response(raw_text, elapsed_ms)

            # Non-200 status code fallback
            return PlayerDecision(
                action=GameAction.NONE,
                confidence=0.0,
                reason=f"API returned status {resp.status_code}",
                latency_ms=elapsed_ms,
            )

        except Exception as exc:
            elapsed_ms = (time.time() - start_time) * 1000
            return PlayerDecision(
                action=GameAction.NONE,
                confidence=0.0,
                reason=f"Inference error: {exc}",
                latency_ms=elapsed_ms,
            )

    def _parse_response(self, text: str, latency_ms: float) -> PlayerDecision:
        """Parse the JSON response into a PlayerDecision model."""
        clean_text = text.strip()
        # Handle markdown code fences if present
        if clean_text.startswith("```"):
            clean_text = re.sub(r"^```(?:json)?\n?", "", clean_text)
            clean_text = re.sub(r"\n?```$", "", clean_text)

        try:
            data = json.loads(clean_text)
            raw_action = str(data.get("action", "NONE")).upper().strip()

            try:
                action = GameAction(raw_action)
            except ValueError:
                action = GameAction.NONE

            confidence = float(data.get("confidence", 0.9))
            reason = str(data.get("reason", "Tactical maneuver"))

            decision = PlayerDecision(
                action=action,
                confidence=max(0.0, min(1.0, confidence)),
                reason=reason,
                latency_ms=latency_ms,
            )
            self.history.append(decision)
            return decision

        except json.JSONDecodeError:
            # Fallback search for action keywords
            for act in (
                GameAction.LEFT,
                GameAction.RIGHT,
                GameAction.UP,
                GameAction.DOWN,
                GameAction.SPACE,
            ):
                if act.value in clean_text.upper():
                    decision = PlayerDecision(
                        action=act,
                        confidence=0.6,
                        reason=clean_text[:60],
                        latency_ms=latency_ms,
                    )
                    self.history.append(decision)
                    return decision

            decision = PlayerDecision(
                action=GameAction.NONE,
                confidence=0.0,
                reason="Failed to parse response format",
                latency_ms=latency_ms,
            )
            self.history.append(decision)
            return decision
