"""High-speed screen capture and frame preprocessing engine."""

import base64
from typing import Any

import cv2
import mss
import numpy as np

from leyline.vision.models import ScreenRegion


class ScreenCaptureEngine:
    """Fast screen capture using mss and OpenCV for agent visual perception."""

    def __init__(
        self,
        default_region: ScreenRegion | None = None,
        mock_mode: bool = False,
    ) -> None:
        self.default_region = default_region
        self.mock_mode = mock_mode
        mss_cls = getattr(mss, "MSS", mss.mss)
        self._sct = mss_cls()

    def __enter__(self) -> "ScreenCaptureEngine":
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.close()

    def close(self) -> None:
        """Release underlying screen capture resources."""
        if hasattr(self, "_sct") and self._sct is not None:
            self._sct.close()

    def get_monitors(self) -> list[dict[str, int]]:
        """List all available monitors detected on the host system."""
        return list(self._sct.monitors)

    def grab_frame(self, region: ScreenRegion | None = None) -> np.ndarray:
        """Capture a single frame from the specified or default screen region.

        Args:
            region: Optional bounding box to capture. Uses default_region if None.

        Returns:
            np.ndarray: BGR image array compatible with OpenCV.
        """
        active_region = region or self.default_region
        if active_region:
            monitor_dict = active_region.to_mss_dict()
        else:
            # Monitor 1 is typically the primary display; monitor 0 is all displays combined
            monitor_dict = (
                self._sct.monitors[1] if len(self._sct.monitors) > 1 else self._sct.monitors[0]
            )

        if self.mock_mode:
            width = monitor_dict.get("width", 512)
            height = monitor_dict.get("height", 512)
            mock_frame = np.zeros((height, width, 3), dtype=np.uint8)
            cv2.putText(
                mock_frame,
                "MOCK CAPTURE FRAME",
                (30, max(30, height // 2)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (0, 255, 0),
                2,
                cv2.LINE_AA,
            )
            return mock_frame

        try:
            screenshot = self._sct.grab(monitor_dict)
            frame = np.array(screenshot)
            return cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
        except Exception as exc:
            raise RuntimeError(
                f"Screen capture failed: {exc}. Ensure your session has interactive desktop "
                "access and the screen is unlocked, or enable mock_mode=True for headless testing."
            ) from exc

    @staticmethod
    def preprocess_for_agent(
        frame: np.ndarray,
        target_size: tuple[int, int] = (512, 512),
        image_format: str = ".jpg",
        quality: int = 80,
    ) -> bytes:
        """Downscale frame and compress to image bytes optimized for LLM multimodal APIs.

        Args:
            frame: Input BGR image array.
            target_size: (width, height) to downscale the frame.
            image_format: Image encoding extension (e.g., '.jpg', '.png').
            quality: Compression quality (1-100) for JPEG encoding.

        Returns:
            bytes: Compressed image bytes.
        """
        resized = cv2.resize(frame, target_size, interpolation=cv2.INTER_AREA)
        encode_params: list[int] = []
        if image_format.lower() in (".jpg", ".jpeg"):
            encode_params = [int(cv2.IMWRITE_JPEG_QUALITY), quality]
        elif image_format.lower() == ".png":
            encode_params = [int(cv2.IMWRITE_PNG_COMPRESSION), 4]

        success, buffer = cv2.imencode(image_format, resized, encode_params)
        if not success:
            raise RuntimeError("Failed to encode frame to image buffer")

        return buffer.tobytes()

    @staticmethod
    def encode_base64(frame_bytes: bytes) -> str:
        """Encode raw image bytes into a base64 string."""
        return base64.b64encode(frame_bytes).decode("utf-8")
