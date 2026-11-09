"""Interactive screen region calibration and preview tool."""

import json
import time
from pathlib import Path

import cv2

from leyline.vision.capture import ScreenCaptureEngine
from leyline.vision.models import CalibrationConfig, ScreenRegion

DEFAULT_CONFIG_DIR = Path("config/regions")


class RegionCalibrator:
    """Manages game region presets, interactive ROI selection, and live visual preview."""

    def __init__(self, config_dir: Path | str = DEFAULT_CONFIG_DIR) -> None:
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(parents=True, exist_ok=True)

    def _get_preset_path(self, preset_name: str) -> Path:
        sanitized = preset_name.strip().lower().replace(" ", "_")
        return self.config_dir / f"{sanitized}.json"

    def list_presets(self) -> list[str]:
        """List all saved calibration preset names."""
        if not self.config_dir.exists():
            return []
        return [p.stem for p in self.config_dir.glob("*.json")]

    def save_preset(
        self,
        preset_name: str,
        region: ScreenRegion,
        target_fps: float = 2.0,
        downscale_width: int = 512,
        downscale_height: int = 512,
    ) -> CalibrationConfig:
        """Persist a calibrated region preset to a JSON file."""
        config = CalibrationConfig(
            preset_name=preset_name,
            region=region,
            target_fps=target_fps,
            downscale_width=downscale_width,
            downscale_height=downscale_height,
        )
        file_path = self._get_preset_path(preset_name)
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(config.to_dict(), f, indent=2)
        return config

    def load_preset(self, preset_name: str) -> CalibrationConfig | None:
        """Load a calibration preset from disk by name."""
        file_path = self._get_preset_path(preset_name)
        if not file_path.exists():
            return None
        with open(file_path, encoding="utf-8") as f:
            data = json.load(f)
        return CalibrationConfig(**data)

    def calibrate_interactive(
        self,
        preset_name: str = "default",
        target_fps: float = 2.0,
    ) -> CalibrationConfig | None:
        """Launch an interactive window to select the game region on screen.

        Instructions:
            - Click and drag a rectangle over the target game area.
            - Press ENTER or SPACE to confirm the selection.
            - Press 'c' to cancel without saving.
        """
        engine = ScreenCaptureEngine()
        full_frame = engine.grab_frame()
        engine.close()

        window_name = "LeyLine Region Selector (Drag box, press ENTER to confirm, C to cancel)"
        cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)

        # Show prompt banner on top of full screen capture
        display_frame = full_frame.copy()
        cv2.putText(
            display_frame,
            "DRAG TO SELECT GAME REGION -> PRESS ENTER TO SAVE -> PRESS 'C' TO CANCEL",
            (50, 50),
            cv2.FONT_HERSHEY_SIMPLEX,
            1.0,
            (0, 255, 0),
            2,
            cv2.LINE_AA,
        )

        # ROI format from cv2.selectROI is (left, top, width, height)
        roi = cv2.selectROI(window_name, display_frame, showCrosshair=True, fromCenter=False)
        cv2.destroyWindow(window_name)

        left, top, width, height = roi
        if width <= 0 or height <= 0:
            return None

        region = ScreenRegion(top=int(top), left=int(left), width=int(width), height=int(height))
        return self.save_preset(preset_name=preset_name, region=region, target_fps=target_fps)

    def live_preview(self, preset_name: str = "default", fps: float = 10.0) -> None:
        """Display a live preview stream of the calibrated region with FPS telemetry.

        Press 'q' or ESC in the preview window to exit.
        """
        config = self.load_preset(preset_name)
        if not config:
            raise FileNotFoundError(f"Preset '{preset_name}' not found. Run calibration first.")

        engine = ScreenCaptureEngine(default_region=config.region)
        window_name = f"LeyLine Preview - [{config.preset_name}] (Press 'q' to exit)"
        cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)

        frame_delay = 1.0 / max(fps, 1.0)
        prev_time = time.time()
        measured_fps = 0.0

        try:
            while True:
                start_loop = time.time()
                frame = engine.grab_frame()

                now = time.time()
                dt = now - prev_time
                if dt > 0:
                    measured_fps = 0.9 * measured_fps + 0.1 * (1.0 / dt)
                prev_time = now

                # Telemetry overlay
                info_text = (
                    f"Preset: {config.preset_name} | "
                    f"Res: {frame.shape[1]}x{frame.shape[0]} | "
                    f"FPS: {measured_fps:.1f}"
                )
                cv2.putText(
                    frame,
                    info_text,
                    (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (0, 255, 255),
                    2,
                    cv2.LINE_AA,
                )

                cv2.imshow(window_name, frame)

                # Process key event
                key = cv2.waitKey(1) & 0xFF
                if key in (ord("q"), 27):  # 'q' or ESC
                    break

                elapsed = time.time() - start_loop
                sleep_time = frame_delay - elapsed
                if sleep_time > 0:
                    time.sleep(sleep_time)
        finally:
            engine.close()
            cv2.destroyAllWindows()
