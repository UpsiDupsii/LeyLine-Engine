"""Fast real-time Computer Vision reflex engine for high-speed runner games like Subway Surfers."""

import time

import cv2
import numpy as np

from leyline.agents.models import PlayerDecision
from leyline.controller.models import GameAction


class SubwayReflexAgent:
    """Sub-millisecond reflex agent for 3-lane endless runners (Subway Surfers).

    Divides the playing canvas into 3 vertical corridors (Left, Center, Right)
    and scans collision zones in real time using edge and texture variance.
    """

    def __init__(self, sensitivity: float = 25.0) -> None:
        self.sensitivity = sensitivity
        self.current_lane = 1  # 0: Left, 1: Center, 2: Right
        self.history: list[PlayerDecision] = []
        self._last_action_time = 0.0

    def decide_action_from_frame(self, frame: np.ndarray) -> PlayerDecision:
        """Scan the 3 gameplay lanes and choose the optimal immediate dodge action.

        Args:
            frame: Raw BGR frame of the calibrated game window.

        Returns:
            PlayerDecision: Immediate tactical decision with 0-5ms latency.
        """
        start_time = time.time()
        h, w = frame.shape[:2]

        if h < 50 or w < 50:
            return PlayerDecision(
                action=GameAction.NONE,
                confidence=0.0,
                reason="Frame too small for lane analysis",
                latency_ms=0.0,
            )

        # Region of interest: middle 40% to 80% vertically (danger horizon)
        roi_top = int(h * 0.45)
        roi_bottom = int(h * 0.85)
        danger_zone = frame[roi_top:roi_bottom, :]

        # Convert to grayscale and apply Gaussian blur
        gray = cv2.cvtColor(danger_zone, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        edges = cv2.Canny(blurred, 50, 150)

        # Split into 3 vertical lane corridors
        lane_w = w // 3
        lane_edges = [
            edges[:, 0:lane_w],  # Left lane
            edges[:, lane_w : 2 * lane_w],  # Center lane
            edges[:, 2 * lane_w : w],  # Right lane
        ]

        # Calculate obstacle intensity density per lane
        lane_threats = [float(np.mean(corridor)) for corridor in lane_edges]

        # Determine if current lane is obstructed
        current_threat = lane_threats[self.current_lane]
        chosen_action = GameAction.NONE
        reason = "Lane clear, maintaining course"
        now = time.time()

        # Enforce minimum cooldown between dodge maneuvers (150ms)
        can_maneuver = (now - self._last_action_time) > 0.18

        if can_maneuver and current_threat > self.sensitivity:
            # Current lane is blocked; find the best alternate lane
            left_clear = (
                self.current_lane > 0 and lane_threats[self.current_lane - 1] < self.sensitivity
            )
            right_clear = (
                self.current_lane < 2 and lane_threats[self.current_lane + 1] < self.sensitivity
            )

            if left_clear and right_clear:
                # Choose lane with lower threat
                if lane_threats[self.current_lane - 1] <= lane_threats[self.current_lane + 1]:
                    chosen_action = GameAction.LEFT
                    self.current_lane -= 1
                    reason = "Evading obstacle: switched to left lane"
                else:
                    chosen_action = GameAction.RIGHT
                    self.current_lane += 1
                    reason = "Evading obstacle: switched to right lane"
            elif left_clear:
                chosen_action = GameAction.LEFT
                self.current_lane -= 1
                reason = "Evading obstacle: swerving LEFT"
            elif right_clear:
                chosen_action = GameAction.RIGHT
                self.current_lane += 1
                reason = "Evading obstacle: swerving RIGHT"
            else:
                # Both lanes blocked or walls on both sides -> Jump!
                chosen_action = GameAction.UP
                reason = "All lanes contested: emergency JUMP"

            self._last_action_time = now

        latency_ms = (time.time() - start_time) * 1000.0
        decision = PlayerDecision(
            action=chosen_action,
            confidence=0.95,
            reason=reason,
            latency_ms=latency_ms,
        )
        self.history.append(decision)
        return decision
