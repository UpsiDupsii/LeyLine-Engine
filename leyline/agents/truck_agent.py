"""Autonomous Vehicle and Garbage Truck Driver Agent powered by Multimodal AI."""

import base64
import json
import re
import socket
import time
from typing import Any

import requests

from leyline.agents.models import PlayerDecision
from leyline.config import GEMINI_API_KEY
from leyline.controller.models import GameAction


class TruckDriverAgent:
    """Intelligent autonomous vehicle agent for objective collection, delivery, and driving games."""

    SYSTEM_PROMPT = (
        "You are an AI driver controlling a garbage truck / delivery vehicle in a video game. "
        "Your mission is to find garbage, collect items, navigate roads, and avoid crashing into walls. "
        "Analyze the game frame and choose the best immediate driving maneuver from:\n"
        "- FORWARD: Drive forward on open road\n"
        "- FORWARD_LEFT: Steer left while accelerating\n"
        "- FORWARD_RIGHT: Steer right while accelerating\n"
        "- REVERSE: Back up if facing a wall or obstacle\n"
        "- INTERACT: Press action key to pick up or dump garbage\n"
        "- BRAKE: Stop vehicle\n\n"
        "Respond ONLY with valid JSON in this exact schema:\n"
        '{"action": "FORWARD", "reason": "Clear road ahead towards garbage container", "confidence": 0.95}'
    )

    def __init__(
        self,
        api_key: str = GEMINI_API_KEY,
        model_name: str = "gemini-2.5-flash",
        mock_mode: bool = False,
        timeout: float = 3.5,
    ) -> None:
        self.api_key = api_key
        self.model_name = model_name
        self.mock_mode = mock_mode
        self.timeout = timeout
        self.history: list[PlayerDecision] = []

    def _force_ipv4(self) -> None:
        try:
            orig = socket.getaddrinfo

            def ipv4_info(*args: Any, **kwargs: Any) -> list[Any]:
                res = orig(*args, **kwargs)
                v4 = [r for r in res if r[0] == socket.AF_INET]
                return v4 if v4 else res

            socket.getaddrinfo = ipv4_info
        except Exception:
            pass

    def decide_driving_action(
        self,
        frame_bytes: bytes,
        base64_frame: str | None = None,
    ) -> PlayerDecision:
        """Analyze game screen and determine next vehicle maneuver."""
        start_time = time.time()

        if self.mock_mode or not self.api_key:
            elapsed_ms = (time.time() - start_time) * 1000.0
            decision = PlayerDecision(
                action=GameAction.FORWARD,
                confidence=1.0,
                reason="Default forward cruising in simulation mode",
                latency_ms=elapsed_ms,
            )
            self.history.append(decision)
            return decision

        self._force_ipv4()
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
            elapsed_ms = (time.time() - start_time) * 1000.0

            if resp.status_code == 200:
                data = resp.json()
                raw_text = (
                    data.get("candidates", [{}])[0]
                    .get("content", {})
                    .get("parts", [{}])[0]
                    .get("text", "")
                )
                return self._parse_json(raw_text, elapsed_ms)

            # API fallback: default to forward cruising
            return PlayerDecision(
                action=GameAction.FORWARD,
                confidence=0.5,
                reason=f"API status {resp.status_code}; continuing forward",
                latency_ms=elapsed_ms,
            )

        except Exception as exc:
            elapsed_ms = (time.time() - start_time) * 1000.0
            return PlayerDecision(
                action=GameAction.FORWARD,
                confidence=0.5,
                reason=f"Inference error ({exc}); cruising forward",
                latency_ms=elapsed_ms,
            )

    def _parse_json(self, raw_text: str, latency_ms: float) -> PlayerDecision:
        clean = raw_text.strip()
        if clean.startswith("```"):
            clean = re.sub(r"^```(?:json)?\n?", "", clean)
            clean = re.sub(r"\n?```$", "", clean)

        try:
            parsed = json.loads(clean)
            action_str = str(parsed.get("action", "FORWARD")).upper().strip()
            try:
                action = GameAction(action_str)
            except ValueError:
                action = GameAction.FORWARD

            decision = PlayerDecision(
                action=action,
                confidence=float(parsed.get("confidence", 0.9)),
                reason=str(parsed.get("reason", "Navigating vehicle")),
                latency_ms=latency_ms,
            )
            self.history.append(decision)
            return decision

        except json.JSONDecodeError:
            decision = PlayerDecision(
                action=GameAction.FORWARD,
                confidence=0.6,
                reason="Parsed freeform; continuing forward drive",
                latency_ms=latency_ms,
            )
            self.history.append(decision)
            return decision
