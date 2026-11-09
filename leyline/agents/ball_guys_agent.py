"""Ball Guys and Suika merge puzzle solver agent powered by Multimodal AI."""

import base64
import json
import re
import socket
import time
from typing import Any

import requests
from pydantic import BaseModel, Field

from leyline.config import GEMINI_API_KEY


class DropDecision(BaseModel):
    """Decision output for dropping a puzzle ball into the container."""

    drop_x: float = Field(
        ge=0.0, le=1.0, description="Horizontal drop fraction from 0.0 (left) to 1.0 (right)"
    )
    target_match: str = Field(default="", description="Target ball or region identified for merge")
    reason: str = Field(default="", description="Strategic reasoning for chosen drop position")
    confidence: float = Field(default=0.9, ge=0.0, le=1.0, description="Confidence score")
    latency_ms: float = Field(default=0.0, ge=0.0, description="Inference latency in milliseconds")


class BallGuysAgent:
    """Strategic AI solver for Ball Guys and Suika physics-based merge drop games."""

    SYSTEM_PROMPT = (
        "You are an expert AI player playing 'Ball Guys' (a Suika / Watermelon physics merge puzzle game).\n"
        "Game Rules:\n"
        "- Identical balls of matching color, face, and size merge into the next larger tier ball when they touch.\n"
        "- Progression: Small Light Blue -> Medium Purple -> Larger Tier Balls up to King Ball.\n"
        "- Game over if balls overflow past the red dashed line at the top of the container.\n\n"
        "Your Task:\n"
        "1. Identify the current ball hanging at the top center.\n"
        "2. Examine the balls resting inside the blue container below.\n"
        "3. Choose the optimal horizontal drop position (drop_x) between 0.08 (far left) and 0.92 (far right).\n\n"
        "Merge Strategy:\n"
        "- TOP PRIORITY: Drop directly above an identical ball of the same color/size to merge them.\n"
        "- SECOND PRIORITY: Drop next to a matching ball in a valley where physics will roll them together.\n"
        "- PILE CONTROL: Keep the pile flat and balanced. Avoid stacking a high peak in the center.\n\n"
        "Respond ONLY with a valid JSON in this exact schema:\n"
        '{"drop_x": 0.25, "target_match": "Small blue ball on bottom left", "reason": "Drop to trigger merge with blue ball", "confidence": 0.95}'
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
        self.history: list[DropDecision] = []

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

    def decide_drop(
        self,
        frame_bytes: bytes,
        base64_frame: str | None = None,
    ) -> DropDecision:
        """Analyze the container snapshot and determine the best horizontal drop position."""
        start_time = time.time()

        if self.mock_mode or not self.api_key:
            elapsed_ms = (time.time() - start_time) * 1000.0
            decision = DropDecision(
                drop_x=0.5,
                target_match="Center container drop",
                reason="Default center drop in simulation mode",
                confidence=1.0,
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

            # API fallback: drop in alternating valleys
            drop_x = 0.3 if len(self.history) % 2 == 0 else 0.7
            decision = DropDecision(
                drop_x=drop_x,
                target_match="Valley balance fallback",
                reason=f"API status {resp.status_code}; balancing pile",
                confidence=0.5,
                latency_ms=elapsed_ms,
            )
            self.history.append(decision)
            return decision

        except Exception as exc:
            elapsed_ms = (time.time() - start_time) * 1000.0
            drop_x = 0.35 if len(self.history) % 2 == 0 else 0.65
            decision = DropDecision(
                drop_x=drop_x,
                target_match="Offline balance fallback",
                reason=f"Inference error ({exc}); alternating drop",
                confidence=0.5,
                latency_ms=elapsed_ms,
            )
            self.history.append(decision)
            return decision

    def _parse_json(self, raw_text: str, latency_ms: float) -> DropDecision:
        clean = raw_text.strip()
        if clean.startswith("```"):
            clean = re.sub(r"^```(?:json)?\n?", "", clean)
            clean = re.sub(r"\n?```$", "", clean)

        try:
            parsed = json.loads(clean)
            raw_x = float(parsed.get("drop_x", 0.5))
            # Clamp within container walls
            drop_x = max(0.08, min(0.92, raw_x))
            target = str(parsed.get("target_match", "Open slot"))
            reason = str(parsed.get("reason", "Merging matching balls"))
            conf = float(parsed.get("confidence", 0.9))

            decision = DropDecision(
                drop_x=drop_x,
                target_match=target,
                reason=reason,
                confidence=max(0.0, min(1.0, conf)),
                latency_ms=latency_ms,
            )
            self.history.append(decision)
            return decision

        except (json.JSONDecodeError, ValueError):
            decision = DropDecision(
                drop_x=0.5,
                target_match="Center drop",
                reason="Parsed freeform; dropping in center",
                confidence=0.6,
                latency_ms=latency_ms,
            )
            self.history.append(decision)
            return decision
