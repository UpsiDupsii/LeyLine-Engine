"""Ball Guys and Suika physics puzzle computer vision perception module.

Detects container bounds, the hanging active ball, resting balls, color tiers,
and performs deterministic matching, valley leveling, and dropper alignment verification.
"""

from __future__ import annotations

import cv2
import numpy as np
from pydantic import BaseModel, Field


class ContainerBounds(BaseModel):
    """Bounding box coordinates of the puzzle container cup within the captured frame."""

    left: int = Field(ge=0, description="Left wall pixel X")
    top: int = Field(ge=0, description="Top edge pixel Y")
    right: int = Field(ge=0, description="Right wall pixel X")
    bottom: int = Field(ge=0, description="Bottom floor pixel Y")
    width: int = Field(ge=1, description="Container inner width in pixels")
    height: int = Field(ge=1, description="Container inner height in pixels")


class BallInfo(BaseModel):
    """Detection metadata for a single puzzle ball."""

    x: int = Field(description="Center X pixel coordinate in frame")
    y: int = Field(description="Center Y pixel coordinate in frame")
    radius: float = Field(ge=0.0, description="Estimated ball radius in pixels")
    tier: int = Field(default=1, ge=1, le=11, description="Ball evolution tier (1 = smallest)")
    color_name: str = Field(default="Unknown", description="Human-readable color and size tier")
    bgr: tuple[int, int, int] = Field(default=(0, 0, 0), description="Representative BGR color")
    fraction_x: float = Field(
        ge=0.0, le=1.0, description="Horizontal position relative to container (0.0 to 1.0)"
    )
    fraction_y: float = Field(
        ge=0.0, le=1.0, description="Vertical position relative to container (0.0=top, 1.0=bottom)"
    )


class PuzzleState(BaseModel):
    """Complete perception state of the Ball Guys puzzle board."""

    container: ContainerBounds
    hanging_ball: BallInfo | None = None
    resting_balls: list[BallInfo] = Field(default_factory=list)
    red_line_y: int = Field(default=0, description="Pixel Y of the red dashed overflow limit")
    column_heights: list[float] = Field(
        default_factory=list,
        description="Normalized pile heights across vertical container columns",
    )


def classify_ball_color(bgr: np.ndarray | tuple[int, int, int], radius: float) -> tuple[int, str]:
    """Classify ball evolution tier and descriptor based on BGR color and radius.

    Progression in Ball Guys / Suika puzzles:
    Tier 1: Small Light Blue
    Tier 2: Medium Purple
    Tier 3: Orange / Yellow
    Tier 4: Green
    Tier 5: Large Red / Watermelon
    """
    b, g, r = int(bgr[0]), int(bgr[1]), int(bgr[2])
    hsv = cv2.cvtColor(np.uint8([[[b, g, r]]]), cv2.COLOR_BGR2HSV)[0][0]
    h, s, _v = int(hsv[0]), int(hsv[1]), int(hsv[2])

    if b > 175 and r > 90 and g < 75:
        return (2, "Medium Purple")
    elif (b > 160 and g > 100) or (h >= 95 and h <= 125):
        return (1, "Small Light Blue")
    elif (h < 15 or h > 165) and s > 80:
        return (5, "Large Red")
    elif 15 <= h < 40 and s > 80:
        return (3, "Orange/Yellow")
    elif 40 <= h < 90 and s > 60:
        return (4, "Medium Green")
    elif radius > 45:
        return (3, "Large Ball")
    elif radius > 25:
        return (2, "Medium Ball")
    else:
        return (1, "Small Ball")


class PuzzleDetector:
    """High-accuracy deterministic computer vision detector for Ball Guys."""

    @staticmethod
    def detect_container(frame: np.ndarray) -> ContainerBounds:
        """Detect container boundaries automatically from frame or default to center."""
        h, w = frame.shape[:2]

        # Container walls are blue-gray borders: B ~ 105-145, G ~ 70-105, R ~ 25-60
        wall_mask = cv2.inRange(frame, np.array([105, 75, 25]), np.array([145, 105, 60]))
        col_sums = np.sum(wall_mask > 0, axis=0)
        wall_cols = np.where(col_sums > max(40, int(h * 0.2)))[0]

        if len(wall_cols) >= 2 and (wall_cols[-1] - wall_cols[0]) > int(w * 0.15):
            c_left = int(wall_cols[0])
            c_right = int(wall_cols[-1])
        else:
            # Fallback to full frame or center
            c_left = int(w * 0.1)
            c_right = int(w * 0.9)

        c_width = max(10, c_right - c_left)

        # Detect bottom floor
        row_sums = np.sum(wall_mask[:, c_left:c_right] > 0, axis=1)
        wall_rows = np.where(row_sums > int(c_width * 0.35))[0]
        c_bottom = int(wall_rows[-1]) if len(wall_rows) > 0 else int(h * 0.85)

        # Detect top edge / red dashed limit line
        red_mask = (
            (frame[:, c_left:c_right, 2] > 150)
            & (frame[:, c_left:c_right, 1] < 70)
            & (frame[:, c_left:c_right, 0] < 70)
        )
        red_row_sums = np.sum(red_mask, axis=1)
        red_rows = np.where(red_row_sums > 12)[0]

        if len(red_rows) > 0:
            c_top = max(0, int(red_rows[0]) - 48)
        else:
            c_top = max(0, int(c_bottom - c_width * 1.15))

        c_height = max(10, c_bottom - c_top)
        return ContainerBounds(
            left=c_left,
            top=c_top,
            right=c_right,
            bottom=c_bottom,
            width=c_width,
            height=c_height,
        )

    @classmethod
    def detect_puzzle_state(cls, frame: np.ndarray) -> PuzzleState:
        """Extract full puzzle state including container, active ball, and resting balls."""
        container = cls.detect_container(frame)

        c_left, c_top = container.left, container.top
        c_right, c_bottom = container.right, container.bottom
        c_width, c_height = container.width, container.height

        # Container ROI
        roi = frame[c_top:c_bottom, c_left:c_right]
        if roi.size == 0:
            return PuzzleState(container=container)

        # Safe background sampling: sample center interior
        sample_y1, sample_y2 = int(c_height * 0.35), int(c_height * 0.45)
        sample_x1, sample_x2 = int(c_width * 0.25), int(c_width * 0.35)
        if sample_y2 > sample_y1 and sample_x2 > sample_x1:
            bg_color = np.median(roi[sample_y1:sample_y2, sample_x1:sample_x2], axis=(0, 1)).astype(
                np.int32
            )
        else:
            bg_color = np.array([78, 52, 52], dtype=np.int32)

        diff = np.linalg.norm(roi.astype(np.int32) - bg_color, axis=2)

        # Mask container borders out
        pad_x = max(6, int(c_width * 0.04))
        diff[:, :pad_x] = 0
        diff[:, -pad_x:] = 0
        diff[-pad_x:, :] = 0

        # Mask red dashed line out
        is_red = (roi[:, :, 2] > 150) & (roi[:, :, 1] < 70) & (roi[:, :, 0] < 70)
        diff[is_red] = 0

        red_row_sums = np.sum(is_red, axis=1)
        red_rows = np.where(red_row_sums > 10)[0]
        red_line_y = int(red_rows[0]) if len(red_rows) > 0 else int(c_height * 0.18)

        # 1. Hanging active ball at top
        hanging_ball: BallInfo | None = None
        top_strip = roi[0 : max(30, red_line_y), :]
        top_diff = diff[0 : max(30, red_line_y), :]
        top_fg = (top_diff > 35).astype(np.uint8) * 255
        top_contours, _ = cv2.findContours(top_fg, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        for cnt in top_contours:
            bx, by, bw, bh = cv2.boundingRect(cnt)
            if bw >= 10:
                cx = bx + bw // 2
                cy = by + bh // 2
                sampled_bgr = top_strip[min(cy, top_strip.shape[0] - 1), cx]
                radius = max(bw, bh) / 2.0
                tier, color_name = classify_ball_color(sampled_bgr, radius)
                frac_x = max(0.0, min(1.0, cx / float(c_width)))
                frac_y = max(0.0, min(1.0, cy / float(c_height)))
                hanging_ball = BallInfo(
                    x=c_left + cx,
                    y=c_top + cy,
                    radius=radius,
                    tier=tier,
                    color_name=color_name,
                    bgr=(int(sampled_bgr[0]), int(sampled_bgr[1]), int(sampled_bgr[2])),
                    fraction_x=frac_x,
                    fraction_y=frac_y,
                )
                break

        # 2. Resting balls in container floor
        resting_balls: list[BallInfo] = []
        floor_start_y = red_line_y + 12
        if floor_start_y < c_height:
            floor_diff = diff[floor_start_y:, :]
            floor_fg = (floor_diff > 35).astype(np.uint8) * 255
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
            floor_fg = cv2.morphologyEx(floor_fg, cv2.MORPH_OPEN, kernel)
            floor_fg = cv2.morphologyEx(floor_fg, cv2.MORPH_CLOSE, kernel)

            floor_contours, _ = cv2.findContours(
                floor_fg, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
            )
            for cnt in floor_contours:
                area = cv2.contourArea(cnt)
                if area < 100:
                    continue

                bx, by, bw, bh = cv2.boundingRect(cnt)
                if bh > 40 and bw < 10:
                    continue

                cx = bx + bw // 2
                cy = floor_start_y + by + bh // 2
                radius = max(bw, bh) / 2.0
                sampled_bgr = roi[min(cy, roi.shape[0] - 1), min(cx, roi.shape[1] - 1)]
                tier, color_name = classify_ball_color(sampled_bgr, radius)
                frac_x = max(0.0, min(1.0, cx / float(c_width)))
                frac_y = max(0.0, min(1.0, cy / float(c_height)))

                ball = BallInfo(
                    x=c_left + cx,
                    y=c_top + cy,
                    radius=radius,
                    tier=tier,
                    color_name=color_name,
                    bgr=(int(sampled_bgr[0]), int(sampled_bgr[1]), int(sampled_bgr[2])),
                    fraction_x=frac_x,
                    fraction_y=frac_y,
                )
                resting_balls.append(ball)

        # 3. Compute pile heights across 5 vertical columns
        columns = [0.15, 0.32, 0.50, 0.68, 0.85]
        col_heights = [0.0] * len(columns)
        for rb in resting_balls:
            closest_idx = min(range(len(columns)), key=lambda i: abs(columns[i] - rb.fraction_x))
            height_from_floor = 1.0 - rb.fraction_y
            col_heights[closest_idx] = max(col_heights[closest_idx], height_from_floor)

        return PuzzleState(
            container=container,
            hanging_ball=hanging_ball,
            resting_balls=resting_balls,
            red_line_y=c_top + red_line_y,
            column_heights=col_heights,
        )

    @classmethod
    def find_best_drop_target(cls, state: PuzzleState) -> tuple[float, str, str, float]:
        """Compute the optimal horizontal drop fraction using matching priority and valley leveling.

        Returns:
            tuple[float, str, str, float]: (drop_fraction, target_match, reason, confidence)
        """
        min_safe_x = 0.12
        max_safe_x = 0.88

        # Strategy 1: Direct match with identical tier resting ball
        if state.hanging_ball is not None:
            active_tier = state.hanging_ball.tier
            matching_balls = [b for b in state.resting_balls if b.tier == active_tier]

            if matching_balls:
                best_match = min(matching_balls, key=lambda b: b.fraction_y)
                target_x = max(min_safe_x, min(max_safe_x, best_match.fraction_x))
                desc = f"Direct match on {best_match.color_name} at X={target_x:.2f} (Tier {active_tier})"
                reason = (
                    f"Drop directly above matching {state.hanging_ball.color_name} to trigger merge"
                )
                return (target_x, desc, reason, 0.95)

        # Strategy 2: If no direct match, drop into the lowest valley column
        columns = [0.16, 0.33, 0.50, 0.67, 0.84]
        if state.column_heights and len(state.column_heights) == len(columns):
            min_height_idx = int(np.argmin(state.column_heights))
            target_x = columns[min_height_idx]
            min_height = state.column_heights[min_height_idx]
            desc = f"Valley leveling in Column {min_height_idx + 1} at X={target_x:.2f}"
            reason = f"No direct tier match; leveling lowest valley (height: {min_height:.2f}) to prevent pile peak"
            return (target_x, desc, reason, 0.85)

        # Strategy 3: Safe center balance fallback
        return (0.50, "Center container fallback", "Even center distribution drop", 0.70)

    @classmethod
    def verify_needle_alignment(
        cls,
        frame: np.ndarray,
        target_fraction: float,
        container: ContainerBounds,
        tolerance_pixels: int = 8,
    ) -> tuple[bool, float, float]:
        """Verify if the hanging ball or dropper needle is currently aligned with the target drop position.

        Args:
            frame: Fresh visual screenshot from screen capture.
            target_fraction: Intended horizontal fraction (0.0 to 1.0).
            container: Bounding box of the container.
            tolerance_pixels: Allowed pixel discrepancy.

        Returns:
            tuple[bool, float, float]: (is_aligned, current_fraction, error_pixels)
        """
        c_left, c_top = container.left, container.top
        c_right = container.right
        c_width = container.width

        target_px = c_left + int(target_fraction * c_width)

        strip_bottom = min(frame.shape[0], c_top + 65)
        strip = frame[max(0, c_top - 20) : strip_bottom, c_left:c_right]
        if strip.size == 0:
            return (True, target_fraction, 0.0)

        bg_color = np.median(strip[:, :10], axis=(0, 1)).astype(np.int32)
        diff = np.linalg.norm(strip.astype(np.int32) - bg_color, axis=2)
        mask = (diff > 40).astype(np.uint8) * 255

        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        valid_candidates = []
        for cnt in contours:
            bx, by, bw, bh = cv2.boundingRect(cnt)
            if bw >= 8 or bh >= 15:
                center_x = bx + bw // 2
                abs_x = c_left + center_x
                valid_candidates.append(abs_x)

        if not valid_candidates:
            return (True, target_fraction, 0.0)

        actual_px = min(valid_candidates, key=lambda x: abs(x - target_px))
        actual_fraction = max(0.0, min(1.0, (actual_px - c_left) / float(c_width)))
        error_pixels = float(target_px - actual_px)

        is_aligned = abs(error_pixels) <= tolerance_pixels
        return (is_aligned, actual_fraction, error_pixels)
