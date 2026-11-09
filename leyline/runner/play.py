"""Live autonomous gameplay runner with real-time visual HUD telemetry."""

import argparse
import sys
import time

import cv2
import numpy as np

from leyline.agents.models import PlayerDecision
from leyline.agents.player import GamerAgent
from leyline.controller.keyboard import KeyboardController
from leyline.controller.models import GameAction
from leyline.vision.calibrator import RegionCalibrator
from leyline.vision.capture import ScreenCaptureEngine


class GameRunner:
    """Orchestrates screen perception, AI decision-making, and keyboard input execution."""

    def __init__(
        self,
        preset_name: str = "default",
        layout: str = "arrows",
        dry_run: bool = False,
        mock_mode: bool = False,
        fps: float = 2.0,
    ) -> None:
        self.preset_name = preset_name
        self.layout = layout
        self.dry_run = dry_run
        self.mock_mode = mock_mode
        self.fps = max(0.5, fps)
        self.calibrator = RegionCalibrator()

        config = self.calibrator.load_preset(preset_name)
        self.region = config.region if config else None

        self.engine = ScreenCaptureEngine(default_region=self.region, mock_mode=mock_mode)
        self.controller = KeyboardController(layout=layout, mock_mode=(dry_run or mock_mode))
        self.agent = GamerAgent(mock_mode=mock_mode)

    def run(self) -> None:
        """Run the main perception-decision-action loop with live OpenCV HUD."""
        window_name = f"LeyLine Agent Live HUD - [{self.preset_name}] (Press 'q' to stop)"
        cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(window_name, 720, 520)

        interval = 1.0 / self.fps
        last_decision_time = 0.0
        current_decision = None

        print(f"LeyLine Runner started for preset: '{self.preset_name}'")
        print(f"Controller layout: {self.layout} | Dry-run: {self.dry_run}")
        print("Focus on the game window. Press 'q' or ESC in HUD to exit.")

        try:
            while True:
                loop_start = time.time()
                frame = self.engine.grab_frame()

                # Trigger decision if interval has elapsed
                now = time.time()
                if now - last_decision_time >= interval:
                    frame_bytes = self.engine.preprocess_for_agent(frame, target_size=(512, 512))
                    current_decision = self.agent.decide_action(frame_bytes)
                    last_decision_time = now

                    # Execute keyboard action
                    if current_decision and current_decision.action != GameAction.NONE:
                        if not self.dry_run:
                            self.controller.tap_action(current_decision.action)

                # Render HUD
                hud_frame = self._render_hud(frame, current_decision)
                cv2.imshow(window_name, hud_frame)

                key = cv2.waitKey(1) & 0xFF
                if key in (ord("q"), 27):
                    print("Stop requested by user.")
                    break

                elapsed = time.time() - loop_start
                sleep_time = 0.03 - elapsed
                if sleep_time > 0:
                    time.sleep(sleep_time)

        finally:
            self.controller.release_all()
            self.engine.close()
            cv2.destroyAllWindows()
            print("LeyLine Runner shutdown safely. All keys released.")

    def _render_hud(self, frame: np.ndarray, decision: PlayerDecision | None) -> np.ndarray:
        """Draw an informative telemetry HUD overlay on top of the captured frame."""
        hud = frame.copy()
        h, w = hud.shape[:2]

        # Top banner background
        cv2.rectangle(hud, (0, 0), (w, 75), (20, 20, 20), -1)

        # Title and mode
        mode_label = "DRY-RUN (NO KEYSTROKES)" if self.dry_run else "LIVE CONTROL ACTIVE"
        status_color = (0, 165, 255) if self.dry_run else (0, 255, 0)
        cv2.putText(
            hud,
            f"LEYLINE AI GAMER | Preset: {self.preset_name} | {mode_label}",
            (10, 25),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            status_color,
            2,
            cv2.LINE_AA,
        )

        if decision:
            act_str = decision.action.value
            lat = f"{decision.latency_ms:.0f}ms"
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
            cv2.putText(
                hud,
                f"REASON: {decision.reason[:65]}",
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
        default="default",
        help="Calibration preset name (e.g. car_game, roblox, subway_surfers).",
    )
    parser.add_argument(
        "--layout",
        type=str,
        choices=["arrows", "wasd"],
        default="arrows",
        help="Key mapping layout. Default: 'arrows'.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run without pressing keys (useful for observing AI decisions safely).",
    )
    parser.add_argument(
        "--mock",
        action="store_true",
        help="Run in mock mode using synthetic frames and offline agent responses.",
    )
    parser.add_argument(
        "--fps",
        type=float,
        default=2.0,
        help="Agent decision rate in decisions per second. Default: 2.0.",
    )
    return parser


def main() -> None:
    """Entrypoint for the play runner."""
    parser = build_parser()
    args = parser.parse_args()

    runner = GameRunner(
        preset_name=args.preset,
        layout=args.layout,
        dry_run=args.dry_run,
        mock_mode=args.mock,
        fps=args.fps,
    )
    try:
        runner.run()
    except KeyboardInterrupt:
        print("\nTerminated by user.")
        sys.exit(0)


if __name__ == "__main__":
    main()
