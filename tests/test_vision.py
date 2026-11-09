"""Tests for LeyLine vision and screen perception engine."""

from pathlib import Path
from unittest.mock import patch

import numpy as np
import pytest
from pydantic import ValidationError

from leyline.vision.calibrator import RegionCalibrator
from leyline.vision.capture import ScreenCaptureEngine
from leyline.vision.models import CalibrationConfig, ScreenRegion


def test_screen_region_model() -> None:
    region = ScreenRegion(top=100, left=200, width=800, height=600)
    assert region.top == 100
    assert region.left == 200
    assert region.width == 800
    assert region.height == 600

    mss_dict = region.to_mss_dict()
    assert mss_dict == {"top": 100, "left": 200, "width": 800, "height": 600}

    roi_tuple = region.to_roi_tuple()
    assert roi_tuple == (200, 100, 800, 600)


def test_screen_region_validation_errors() -> None:
    # Negative top / left should fail
    with pytest.raises(ValidationError):
        ScreenRegion(top=-1, left=0, width=100, height=100)

    # Zero or negative width / height should fail
    with pytest.raises(ValidationError):
        ScreenRegion(top=0, left=0, width=0, height=100)


def test_calibration_config_model() -> None:
    region = ScreenRegion(top=50, left=50, width=400, height=300)
    config = CalibrationConfig(
        preset_name="test_game",
        region=region,
        target_fps=5.0,
        downscale_width=256,
        downscale_height=256,
    )

    data = config.to_dict()
    assert data["preset_name"] == "test_game"
    assert data["target_fps"] == 5.0
    assert data["region"]["width"] == 400


def test_preset_persistence(tmp_path: Path) -> None:
    calibrator = RegionCalibrator(config_dir=tmp_path)
    assert calibrator.list_presets() == []

    region = ScreenRegion(top=10, left=20, width=640, height=480)
    saved = calibrator.save_preset(preset_name="subway_runner", region=region, target_fps=3.0)
    assert saved.preset_name == "subway_runner"

    presets = calibrator.list_presets()
    assert "subway_runner" in presets

    loaded = calibrator.load_preset("subway_runner")
    assert loaded is not None
    assert loaded.region.width == 640
    assert loaded.region.height == 480
    assert loaded.target_fps == 3.0

    # Non-existent preset returns None
    assert calibrator.load_preset("unknown_game") is None


def test_frame_preprocessing() -> None:
    # Create synthetic test frame (800x600 BGR)
    dummy_frame = np.zeros((600, 800, 3), dtype=np.uint8)
    dummy_frame[:, :, 0] = 255  # Blue channel

    jpeg_bytes = ScreenCaptureEngine.preprocess_for_agent(
        dummy_frame, target_size=(256, 256), image_format=".jpg", quality=85
    )
    assert isinstance(jpeg_bytes, bytes)
    # Check JPEG magic header
    assert jpeg_bytes[:2] == b"\xff\xd8"

    png_bytes = ScreenCaptureEngine.preprocess_for_agent(
        dummy_frame, target_size=(128, 128), image_format=".png"
    )
    assert isinstance(png_bytes, bytes)
    # Check PNG magic header
    assert png_bytes[:4] == b"\x89PNG"

    b64_str = ScreenCaptureEngine.encode_base64(jpeg_bytes)
    assert isinstance(b64_str, str)
    assert len(b64_str) > 0


def test_screen_capture_mock_mode() -> None:
    with ScreenCaptureEngine(mock_mode=True) as engine:
        monitors = engine.get_monitors()
        assert len(monitors) > 0

        test_region = ScreenRegion(top=0, left=0, width=200, height=150)
        frame = engine.grab_frame(region=test_region)
        assert isinstance(frame, np.ndarray)
        assert frame.shape == (150, 200, 3)


def test_screen_capture_with_mocked_mss() -> None:
    # Test grab_frame pipeline with mocked underlying screenshot
    fake_screenshot = np.zeros((100, 100, 4), dtype=np.uint8)  # BGRA
    fake_screenshot[:, :, 2] = 255  # Red channel

    with ScreenCaptureEngine() as engine:
        with patch.object(engine._sct, "grab", return_value=fake_screenshot):
            test_region = ScreenRegion(top=0, left=0, width=100, height=100)
            frame = engine.grab_frame(region=test_region)
            assert isinstance(frame, np.ndarray)
            assert frame.shape == (100, 100, 3)


def test_screen_capture_failure_raises_runtime_error() -> None:
    with ScreenCaptureEngine(mock_mode=False) as engine:
        with patch.object(engine._sct, "grab", side_effect=Exception("Display disconnected")):
            test_region = ScreenRegion(top=0, left=0, width=100, height=100)
            with pytest.raises(RuntimeError, match="Screen capture failed"):
                engine.grab_frame(region=test_region)
