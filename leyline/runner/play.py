"""Live autonomous gameplay runner with real-time visual HUD telemetry."""

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
from leyline.controller.direct_input import DirectInputController
from leyline.controller.models import GameAction
from leyline.controller.mouse import MouseController
from leyline.vision.calibrator import RegionCalibrator
from leyline.vision.capture import ScreenCaptureEngine
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
        settle_time: float = 2.0,
    ) -> None:
        self.preset_name = preset_name
        self.window_title = window_title
        self.agent_type = agent_type.lower()
        self.layout = layout
        self.dry_run = dry_run
        self.mock_mode = mock_mode
        self.fps = max(0.5, fps)
        self.continuous = continuous
        self.settle_time = settle_time
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

        # Threading state
        self._running = False
        self._latest_decision: PlayerDecision | DropDecision | None = None
        self._decision_lock = threading.Lock()
        self._latest_frame: np.ndarray | None = None
        self._frame_lock = threading.Lock()

    def _countdown(self) -> None:
        """Countdown timer to allow focusing on the game window."""
        if self.window_title:
            WindowManager.focus_window(self.window_title)

        print("\n-----------------------------------------------------")
        print("Starting in 3 seconds! Focus on the game window now:")
        for i in range(3, 0, -1):
            print(f"  [{i}] ...")
            time.sleep(1.0)
        print("  [GO!] Autonomous AI is now playing!")
        print("-----------------------------------------------------\n")

    def _puzzle_worker(self) -> None:
        """Turn-based drop worker for Ball Guys / Suika merge puzzle games."""
        while self._running:
            with self._frame_lock:
                frame = self._latest_frame.copy() if self._latest_frame is not None else None

            if frame is not None and self.region is not None:
                frame_bytes = self.engine.preprocess_for_agent(frame, target_size=(512, 512))
                assert isinstance(self.agent, BallGuysAgent)
                decision = self.agent.decide_drop(frame_bytes)

                with self._decision_lock:
                    self._latest_decision = decision

                # Execute mouse movement and drop click
                if not self.dry_run:
                    self.mouse.drop_at(
                        container_region=self.region,
                        x_fraction=decision.drop_x,
                        y_offset_pixels=40,
                    )

                # Wait for physics: balls drop, roll, bounce, and merge
                time.sleep(self.settle_time)
            else:
                time.sleep(0.5)

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

        self._running = True
        target_worker = (
            self._puzzle_worker if self.agent_type == "ball_guys" else self._action_worker
        )
        worker_thread = threading.Thread(target=target_worker, daemon=True)
        worker_thread.start()

        print(f"Running mode: {self.agent_type.upper()} | Preset: {self.preset_name}")

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

        # Draw drop line for Ball Guys
        if self.agent_type == "ball_guys" and isinstance(decision, DropDecision):
            drop_pixel_x = int(decision.drop_x * w)
            cv2.line(hud, (drop_pixel_x, 0), (drop_pixel_x, h), (0, 255, 255), 2)
            cv2.circle(hud, (drop_pixel_x, 40), 12, (0, 255, 0), -1)

        # Top banner background
        cv2.rectangle(hud, (0, 0), (w, 75), (20, 20, 20), -1)

        mode_label = "DRY-RUN (NO CLICKS)" if self.dry_run else "LIVE AUTONOMOUS SOLVER"
        status_color = (0, 165, 255) if self.dry_run else (0, 255, 0)
        cv2.putText(
            hud,
            f"LEYLINE | Mode: {self.agent_type.upper()} | {mode_label}",
            (10, 25),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            status_color,
            2,
            cv2.LINE_AA,
        )

        if decision:
            if isinstance(decision, DropDecision):
                pct = f"{decision.drop_x * 100:.0f}%"
                lat = f"{decision.latency_ms:.0f}ms"
                cv2.putText(
                    hud,
                    f"DROP POSITION: [{pct} of container] | Latency: {lat}",
                    (10, 55),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.65,
                    (255, 255, 255),
                    2,
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

            # Bottom reasoning box
            cv2.rectangle(hud, (0, h - 45), (w, h), (10, 10, 10), -1)
            reason_text = decision.reason[:65]
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
        default=2.0,
        help="Seconds to wait between drops for physics and ball merges to settle in Ball Guys. Default: 2.0s.",
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
    )
    try:
        runner.run()
    except KeyboardInterrupt:
        print("\nTerminated by user.")
        sys.exit(0)


if __name__ == "__main__":
    main()
