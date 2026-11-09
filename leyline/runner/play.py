"""Live autonomous gameplay runner with real-time visual HUD telemetry and AI commentary."""

from __future__ import annotations

import argparse
import sys
import threading
import time

import cv2
import numpy as np

from leyline.agents.ball_guys_agent import BallGuysAgent, DropDecision
from leyline.agents.models import PlayerDecision
from leyline.agents.player import GamerAgent
from leyline.agents.reflex import SubwayReflexAgent
from leyline.agents.truck_agent import TruckDriverAgent
from leyline.audio.models import (
    CommentatorPersona,
    GameEvent,
    GameEventType,
    VoiceConfig,
)
from leyline.audio.orchestrator import CommentaryOrchestrator
from leyline.controller.direct_input import DirectInputController
from leyline.controller.models import GameAction
from leyline.controller.mouse import MouseController
from leyline.vision.calibrator import RegionCalibrator
from leyline.vision.capture import ScreenCaptureEngine
from leyline.vision.puzzle_detector import PuzzleDetector, PuzzleState
from leyline.vision.window import WindowManager


class GameRunner:
    """Orchestrates non-blocking screen perception, AI decision-making, and input execution."""

    def __init__(
        self,
        preset_name: str = "default",
        window_title: str | None = None,
        agent_type: str = "ball_guys",
        layout: str = "wasd",
        dry_run: bool = False,
        mock_mode: bool = False,
        fps: float = 3.0,
        continuous: bool = True,
        settle_time: float = 2.2,
        hover_delay: float = 0.25,
        align_tolerance: int = 10,
        enable_commentary: bool = True,
        voice: str = "en-US-ChristopherNeural",
        persona: str = "hype",
    ) -> None:
        self.preset_name = preset_name
        self.window_title = window_title
        self.agent_type = agent_type.lower()
        self.layout = layout
        self.dry_run = dry_run
        self.mock_mode = mock_mode
        self.fps = max(0.5, fps)
        self.continuous = continuous
        self.settle_time = max(0.5, settle_time)
        self.hover_delay = max(0.05, hover_delay)
        self.align_tolerance = align_tolerance
        self.enable_commentary = enable_commentary
        self.voice = voice
        self.persona = persona
        self.calibrator = RegionCalibrator()

        # Determine capture region
        self.region = None
        if window_title:
            self.region = WindowManager.get_window_region(window_title)
            if not self.region:
                print(
                    f"Warning: Window matching '{window_title}' not found. Falling back to preset."
                )

        if not self.region:
            config = self.calibrator.load_preset(preset_name)
            self.region = config.region if config else None

        self.engine = ScreenCaptureEngine(default_region=self.region, mock_mode=mock_mode)
        self.controller = DirectInputController(layout=layout, mock_mode=(dry_run or mock_mode))
        self.mouse = MouseController(mock_mode=(dry_run or mock_mode))

        # Select agent brain
        if self.agent_type == "ball_guys":
            self.agent: BallGuysAgent | TruckDriverAgent | SubwayReflexAgent | GamerAgent = (
                BallGuysAgent(mock_mode=mock_mode)
            )
        elif self.agent_type == "truck":
            self.agent = TruckDriverAgent(mock_mode=mock_mode)
        elif self.agent_type == "reflex":
            self.agent = SubwayReflexAgent()
        else:
            self.agent = GamerAgent(mock_mode=mock_mode)

        # Asynchronous Neural Voice Commentary Engine
        self.commentary: CommentaryOrchestrator | None = None
        if self.enable_commentary:
            voice_cfg = VoiceConfig(voice_name=self.voice, rate="+5%")
            self.commentary = CommentaryOrchestrator(
                voice_config=voice_cfg,
                persona=CommentatorPersona(self.persona),
                cooldown_seconds=3.0,
                mock_mode=mock_mode,
            )

        # Threading state
        self._running = False
        self._latest_decision: PlayerDecision | DropDecision | None = None
        self._decision_lock = threading.Lock()
        self._latest_frame: np.ndarray | None = None
        self._frame_lock = threading.Lock()
        self._latest_puzzle_state: PuzzleState | None = None

        # Verification telemetry
        self._puzzle_phase = "READY"
        self._align_error = 0.0
        self._settle_remaining = 0.0

    def _countdown(self) -> None:
        """Countdown timer to allow focusing on the game window."""
        if self.window_title:
            WindowManager.focus_window(self.window_title)

        if self.commentary:
            self.commentary.post_event(
                GameEvent(
                    event_type=GameEventType.GAME_START,
                    details=f"Starting autonomous run in {self.agent_type.upper()}",
                )
            )

        print("\n-----------------------------------------------------")
        print("Starting in 3 seconds! Focus on the game window now:")
        for i in range(3, 0, -1):
            print(f"  [{i}] ...")
            time.sleep(1.0)
        print("  [GO!] Autonomous AI is now playing!")
        print("-----------------------------------------------------\n")

    def _puzzle_worker(self) -> None:
        """Turn-based drop worker with aiming, visual verification, and physics settling."""
        while self._running:
            with self._frame_lock:
                frame = self._latest_frame.copy() if self._latest_frame is not None else None

            if frame is not None and self.region is not None:
                assert isinstance(self.agent, BallGuysAgent)

                # Phase 1: Board Perception & Decision
                self._puzzle_phase = "PERCEIVING"
                decision, state = self.agent.decide_drop_from_frame(frame)
                self._latest_puzzle_state = state

                with self._decision_lock:
                    self._latest_decision = decision

                # Emit commentary event based on game state
                if self.commentary:
                    active_tier = state.hanging_ball.color_name if state.hanging_ball else "Ball"
                    max_height = max(state.column_heights) if state.column_heights else 0.0
                    if max_height > 0.75:
                        ev = GameEvent(
                            event_type=GameEventType.RED_LINE_DANGER,
                            ball_tier=active_tier,
                            target_x=decision.drop_x,
                            danger_level=max_height,
                            details="Pile height dangerously near red line limit",
                        )
                    elif "Direct match" in decision.target_match:
                        ev = GameEvent(
                            event_type=GameEventType.MATCH_MERGE,
                            ball_tier=active_tier,
                            target_x=decision.drop_x,
                            danger_level=max_height,
                            details=decision.reason,
                        )
                    else:
                        ev = GameEvent(
                            event_type=GameEventType.VALLEY_DROP,
                            ball_tier=active_tier,
                            target_x=decision.drop_x,
                            danger_level=max_height,
                            details=decision.reason,
                        )
                    self.commentary.post_event(ev)

                if not self.dry_run:
                    # Phase 2: Aim (Move cursor to candidate drop position)
                    self._puzzle_phase = "AIMING"
                    self.mouse.aim_at(
                        container_region=self.region,
                        x_fraction=decision.drop_x,
                        y_offset_pixels=30,
                        container_bounds=state.container,
                    )

                    # Phase 3: Hover & Let Hanging Ball Align
                    self._puzzle_phase = "VERIFYING ALIGNMENT"
                    time.sleep(self.hover_delay)

                    # Capture fresh frame to verify dropper alignment
                    verify_frame = self.engine.grab_frame()
                    aligned, actual_f, error_px = PuzzleDetector.verify_needle_alignment(
                        verify_frame,
                        target_fraction=decision.drop_x,
                        container=state.container,
                        tolerance_pixels=self.align_tolerance,
                    )
                    self._align_error = error_px

                    # Micro-adjustment if off-target
                    if not aligned and abs(error_px) > self.align_tolerance:
                        self._puzzle_phase = "ADJUSTING"
                        self.mouse.nudge(int(error_px), 0)
                        time.sleep(0.12)

                    # Phase 4: Release Click
                    self._puzzle_phase = "DROPPING"
                    self.mouse.click("left")

                # Phase 5: Settle Phase (Balls fall, collide, and merge)
                self._puzzle_phase = "SETTLING"
                settle_start = time.time()
                while (time.time() - settle_start) < self.settle_time and self._running:
                    self._settle_remaining = max(
                        0.0, self.settle_time - (time.time() - settle_start)
                    )
                    time.sleep(0.05)

                self._settle_remaining = 0.0
            else:
                time.sleep(0.2)

    def _action_worker(self) -> None:
        """Background thread executing fast action perception without stalling vehicle physics."""
        interval = 1.0 / self.fps
        while self._running:
            loop_start = time.time()

            with self._frame_lock:
                frame = self._latest_frame.copy() if self._latest_frame is not None else None

            if frame is not None:
                if isinstance(self.agent, SubwayReflexAgent):
                    decision = self.agent.decide_action_from_frame(frame)
                elif isinstance(self.agent, TruckDriverAgent):
                    frame_bytes = self.engine.preprocess_for_agent(frame, target_size=(512, 512))
                    decision = self.agent.decide_driving_action(frame_bytes)
                elif isinstance(self.agent, GamerAgent):
                    frame_bytes = self.engine.preprocess_for_agent(frame, target_size=(512, 512))
                    decision = self.agent.decide_action(frame_bytes)
                else:
                    break

                with self._decision_lock:
                    self._latest_decision = decision

                if not self.dry_run:
                    if decision.action == GameAction.INTERACT:
                        self.controller.tap_key("e" if self.layout == "wasd" else "space")
                    elif self.continuous:
                        self.controller.set_active_action(decision.action)
                    else:
                        self.controller.execute_action(decision.action, duration=0.25)

            elapsed = time.time() - loop_start
            sleep_time = interval - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)

    def run(self) -> None:
        """Run the main render and capture loop with live OpenCV HUD."""
        window_name = f"LeyLine Live HUD - [{self.agent_type.upper()}] (Press 'q' to stop)"
        cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(window_name, 720, 520)

        if not self.mock_mode:
            self._countdown()

        if self.commentary:
            self.commentary.start()

        self._running = True
        target_worker = (
            self._puzzle_worker if self.agent_type == "ball_guys" else self._action_worker
        )
        worker_thread = threading.Thread(target=target_worker, daemon=True)
        worker_thread.start()

        print(f"Running mode: {self.agent_type.upper()} | Preset: {self.preset_name}")
        if self.commentary:
            print(f"AI Commentator Active | Voice: {self.voice} | Persona: {self.persona.upper()}")

        try:
            while True:
                loop_start = time.time()
                frame = self.engine.grab_frame()

                with self._frame_lock:
                    self._latest_frame = frame

                with self._decision_lock:
                    current_decision = self._latest_decision

                hud_frame = self._render_hud(frame, current_decision)
                cv2.imshow(window_name, hud_frame)

                key = cv2.waitKey(1) & 0xFF
                if key in (ord("q"), 27):
                    print("Stop requested by user.")
                    break

                elapsed = time.time() - loop_start
                sleep_time = (1.0 / 30.0) - elapsed
                if sleep_time > 0:
                    time.sleep(sleep_time)

        finally:
            self._running = False
            if self.commentary:
                self.commentary.stop()
            self.controller.release_all()
            self.engine.close()
            cv2.destroyAllWindows()
            print("LeyLine Runner shutdown safely.")

    def _render_hud(
        self,
        frame: np.ndarray,
        decision: PlayerDecision | DropDecision | None,
    ) -> np.ndarray:
        """Draw an informative telemetry HUD overlay on top of the captured frame."""
        hud = frame.copy()
        h, w = hud.shape[:2]

        # Ball Guys Puzzle overlays
        if self.agent_type == "ball_guys":
            state = self._latest_puzzle_state
            if state is not None:
                c = state.container
                # Draw container boundary box in cyan
                cv2.rectangle(hud, (c.left, c.top), (c.right, c.bottom), (255, 255, 0), 2)

                # Draw red dashed limit line
                cv2.line(
                    hud, (c.left, state.red_line_y), (c.right, state.red_line_y), (0, 0, 255), 2
                )

                # Highlight resting balls
                for b in state.resting_balls:
                    r = max(8, int(b.radius))
                    cv2.circle(hud, (b.x, b.y), r, (0, 255, 0), 2)
                    cv2.putText(
                        hud,
                        f"T{b.tier}",
                        (b.x - 10, b.y - r - 4),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.4,
                        (0, 255, 0),
                        1,
                    )

                # Highlight active hanging ball
                if state.hanging_ball is not None:
                    hb = state.hanging_ball
                    hr = max(8, int(hb.radius))
                    cv2.circle(hud, (hb.x, hb.y), hr, (0, 255, 255), 2)

                # Draw drop line relative to container
                if isinstance(decision, DropDecision):
                    drop_pixel_x = int(c.left + decision.drop_x * c.width)
                    cv2.line(hud, (drop_pixel_x, c.top), (drop_pixel_x, c.bottom), (0, 255, 255), 2)
                    cv2.circle(hud, (drop_pixel_x, c.top + 20), 8, (0, 255, 0), -1)

        # Top banner background
        cv2.rectangle(hud, (0, 0), (w, 85), (20, 20, 20), -1)

        mode_label = "DRY-RUN (NO CLICKS)" if self.dry_run else "LIVE AUTONOMOUS SOLVER"
        status_color = (0, 165, 255) if self.dry_run else (0, 255, 0)
        cv2.putText(
            hud,
            f"LEYLINE | Mode: {self.agent_type.upper()} | {mode_label}",
            (10, 22),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            status_color,
            2,
            cv2.LINE_AA,
        )

        if decision:
            if isinstance(decision, DropDecision):
                pct = f"{decision.drop_x * 100:.0f}%"
                lat = f"{decision.latency_ms:.0f}ms"
                phase_info = self._puzzle_phase
                if self._settle_remaining > 0:
                    phase_info = f"SETTLING ({self._settle_remaining:.1f}s)"

                cv2.putText(
                    hud,
                    f"PHASE: [{phase_info}] | TARGET: [{pct}] | Latency: {lat}",
                    (10, 50),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    (255, 255, 255),
                    2,
                    cv2.LINE_AA,
                )
                err_text = (
                    f"Err: {self._align_error:.0f}px" if abs(self._align_error) > 0 else "Aligned"
                )
                cv2.putText(
                    hud,
                    f"AIM: {decision.target_match[:35]} | {err_text}",
                    (10, 75),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    (200, 255, 200),
                    1,
                    cv2.LINE_AA,
                )
            else:
                act_str = decision.action.value
                lat = f"{decision.latency_ms:.1f}ms"
                conf = f"{decision.confidence * 100:.0f}%"
                cv2.putText(
                    hud,
                    f"ACTION: [{act_str}] | Latency: {lat} | Conf: {conf}",
                    (10, 55),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.65,
                    (255, 255, 255),
                    2,
                    cv2.LINE_AA,
                )

        # Bottom live commentary subtitle banner
        caster_line = self.commentary.current_text if self.commentary else ""
        if caster_line:
            cv2.rectangle(hud, (0, h - 45), (w, h), (10, 10, 10), -1)
            cv2.putText(
                hud,
                f"CASTER [{self.persona.upper()}]: {caster_line[:70]}",
                (10, h - 15),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.52,
                (0, 255, 255),
                1,
                cv2.LINE_AA,
            )
        elif decision:
            cv2.rectangle(hud, (0, h - 45), (w, h), (10, 10, 10), -1)
            reason_text = decision.reason[:75]
            cv2.putText(
                hud,
                f"STRATEGY: {reason_text}",
                (10, h - 15),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.55,
                (200, 255, 200),
                1,
                cv2.LINE_AA,
            )

        return hud


def build_parser() -> argparse.ArgumentParser:
    """Build CLI parser for the play runner."""
    parser = argparse.ArgumentParser(
        description="LeyLine Autonomous Gamer Runner: real-time visual perception and input control."
    )
    parser.add_argument(
        "--preset",
        type=str,
        default="ball_guys",
        help="Calibration preset name (e.g. ball_guys, truck_game, subway_surfers). Default: 'ball_guys'.",
    )
    parser.add_argument(
        "--window",
        type=str,
        default=None,
        help="Target window title pattern (e.g. 'Chrome', 'Ball Guys', 'Roblox').",
    )
    parser.add_argument(
        "--agent",
        type=str,
        choices=["ball_guys", "truck", "reflex", "gemini"],
        default="ball_guys",
        help="Agent brain: 'ball_guys' (Suika merge puzzle solver), 'truck' (vehicle navigation), 'reflex' (sub-3ms lane runner), or 'gemini' (standard VLM). Default: 'ball_guys'.",
    )
    parser.add_argument(
        "--layout",
        type=str,
        choices=["wasd", "arrows"],
        default="wasd",
        help="Key mapping layout. Default: 'wasd'.",
    )
    parser.add_argument(
        "--settle-time",
        type=float,
        default=2.2,
        help="Seconds to wait between drops for physics and ball merges to settle in Ball Guys. Default: 2.2s.",
    )
    parser.add_argument(
        "--hover-delay",
        type=float,
        default=0.25,
        help="Delay in seconds to let in-game dropper glide to mouse position before verification check. Default: 0.25s.",
    )
    parser.add_argument(
        "--align-tolerance",
        type=int,
        default=10,
        help="Pixel discrepancy tolerance when verifying dropper needle alignment. Default: 10 pixels.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run without clicking or pressing keys (useful for observing AI decisions safely).",
    )
    parser.add_argument(
        "--mock",
        action="store_true",
        help="Run in mock mode using synthetic frames and offline agent responses.",
    )
    parser.add_argument(
        "--fps",
        type=float,
        default=3.0,
        help="Inference query rate in decisions per second for action games. Default: 3.0.",
    )
    parser.add_argument(
        "--no-commentary",
        action="store_true",
        help="Disable asynchronous neural voice commentary.",
    )
    parser.add_argument(
        "--voice",
        type=str,
        default="en-US-ChristopherNeural",
        help="Voice ID for commentary (e.g. en-US-ChristopherNeural, en-US-GuyNeural). Default: 'en-US-ChristopherNeural'.",
    )
    parser.add_argument(
        "--persona",
        type=str,
        choices=["hype", "analytical", "sarcastic", "casual"],
        default="hype",
        help="Commentator personality style. Default: 'hype'.",
    )
    return parser


def main() -> None:
    """Entrypoint for the play runner."""
    parser = build_parser()
    args = parser.parse_args()

    runner = GameRunner(
        preset_name=args.preset,
        window_title=args.window,
        agent_type=args.agent,
        layout=args.layout,
        dry_run=args.dry_run,
        mock_mode=args.mock,
        fps=args.fps,
        settle_time=args.settle_time,
        hover_delay=args.hover_delay,
        align_tolerance=args.align_tolerance,
        enable_commentary=(not args.no_commentary),
        voice=args.voice,
        persona=args.persona,
    )
    try:
        runner.run()
    except KeyboardInterrupt:
        print("\nTerminated by user.")
        sys.exit(0)


if __name__ == "__main__":
    main()
