"""Ball Guys and Suika merge puzzle solver agent powered by Multimodal AI and Computer Vision."""

from __future__ import annotations

import base64
import json
import re
import socket
import time
from typing import Any

import cv2
import numpy as np
import requests
from pydantic import BaseModel, Field

from leyline.config import GEMINI_API_KEY, GROQ_API_KEY
from leyline.vision.puzzle_detector import PuzzleDetector, PuzzleState


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
        "3. Choose the optimal horizontal drop position (drop_x) between 0.12 (left) and 0.88 (right).\n\n"
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
        model_name: str = "gemini-3-flash-preview",
        mock_mode: bool = False,
        timeout: float = 3.5,
    ) -> None:
        self.api_key = api_key
        self.groq_api_key = GROQ_API_KEY
        self.model_name = model_name
        self.mock_mode = mock_mode
        self.timeout = timeout
        self.history: list[DropDecision] = []
        self.latest_state: PuzzleState | None = None

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

    def decide_drop_from_frame(
        self,
        frame: np.ndarray,
    ) -> tuple[DropDecision, PuzzleState]:
        """Analyze uncompressed BGR frame using Computer Vision and optional Multimodal AI."""
        start_time = time.time()

        # Step 1: Deterministic Computer Vision puzzle perception
        state = PuzzleDetector.detect_puzzle_state(frame)
        self.latest_state = state
        cv_x, cv_target, cv_reason, cv_conf = PuzzleDetector.find_best_drop_target(state)

        # In mock mode or if no API key, return the fast deterministic CV decision
        if self.mock_mode or not self.api_key:
            elapsed_ms = (time.time() - start_time) * 1000.0
            decision = DropDecision(
                drop_x=cv_x,
                target_match=cv_target,
                reason=f"[CV Engine] {cv_reason}",
                confidence=cv_conf,
                latency_ms=elapsed_ms,
            )
            self.history.append(decision)
            return decision, state

        # Step 2: Query Cloud Multimodal AI for high-level strategy
        self._force_ipv4()
        encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 80]
        _, enc_img = cv2.imencode(".jpg", frame, encode_param)
        b64_data = base64.b64encode(enc_img.tobytes()).decode("utf-8")

        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{self.model_name}:generateContent?key={self.api_key}"
        )

        active_desc = (
            state.hanging_ball.color_name if state.hanging_ball else "Unknown top hanging ball"
        )
        context_hint = (
            f"\nVision context: Active hanging ball: {active_desc}. "
            f"Detected resting balls: {len(state.resting_balls)}. "
            f"CV recommended drop_x: {cv_x:.2f} ({cv_target})."
        )

        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": self.SYSTEM_PROMPT + context_hint},
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
                decision = self._parse_json(raw_text, elapsed_ms)
                return decision, state

            # If API non-200, fallback to CV target matching
            decision = DropDecision(
                drop_x=cv_x,
                target_match=cv_target,
                reason=f"[CV Fallback (HTTP {resp.status_code})] {cv_reason}",
                confidence=cv_conf * 0.9,
                latency_ms=elapsed_ms,
            )
            self.history.append(decision)
            return decision, state

        except Exception as exc:
            elapsed_ms = (time.time() - start_time) * 1000.0
            # Fallback to CV target matching on network errors
            decision = DropDecision(
                drop_x=cv_x,
                target_match=cv_target,
                reason=f"[CV Fallback ({type(exc).__name__})] {cv_reason}",
                confidence=cv_conf * 0.85,
                latency_ms=elapsed_ms,
            )
            self.history.append(decision)
            return decision, state

    def decide_drop(
        self,
        frame_bytes: bytes,
        base64_frame: str | None = None,
    ) -> DropDecision:
        """Legacy compatibility wrapper for frame bytes input."""
        np_arr = np.frombuffer(frame_bytes, np.uint8)
        frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        if frame is None:
            decision = DropDecision(
                drop_x=0.5,
                target_match="Center container drop",
                reason="Decoding error fallback",
                confidence=0.5,
                latency_ms=0.0,
            )
            self.history.append(decision)
            return decision

        decision, _ = self.decide_drop_from_frame(frame)
        return decision

    def _parse_json(self, raw_text: str, latency_ms: float) -> DropDecision:
        clean = raw_text.strip()
        if clean.startswith("```"):
            clean = re.sub(r"^```(?:json)?\n?", "", clean)
            clean = re.sub(r"\n?```$", "", clean)

        try:
            parsed = json.loads(clean)
            raw_x = float(parsed.get("drop_x", 0.5))
            drop_x = max(0.12, min(0.88, raw_x))
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
