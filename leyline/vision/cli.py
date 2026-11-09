"""Command-line interface for the LeyLine Vision and Screen Perception engine."""

import argparse
import sys

from leyline.vision.calibrator import RegionCalibrator
from leyline.vision.capture import ScreenCaptureEngine
from leyline.vision.models import ScreenRegion


def build_parser() -> argparse.ArgumentParser:
    """Construct argument parser for the vision CLI."""
    parser = argparse.ArgumentParser(
        description="LeyLine Vision Engine: screen capture, region calibration, and live stream preview."
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--calibrate",
        action="store_true",
        help="Launch interactive screen region calibration window.",
    )
    group.add_argument(
        "--preview",
        action="store_true",
        help="Run live preview stream of a calibrated preset.",
    )
    group.add_argument(
        "--list-presets",
        action="store_true",
        help="List all saved calibration presets.",
    )
    group.add_argument(
        "--monitors",
        action="store_true",
        help="Display all detected system monitors and their dimensions.",
    )
    group.add_argument(
        "--manual",
        action="store_true",
        help="Save a preset manually via explicit coordinates (--top, --left, --width, --height).",
    )

    parser.add_argument(
        "--preset",
        type=str,
        default="default",
        help="Name of the game preset (e.g. subway_surfers, roblox, contra). Default: 'default'.",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=4.0,
        help="Countdown seconds before screen capture to allow switching to game tab. Default: 4.0.",
    )
    parser.add_argument(
        "--fps",
        type=float,
        default=10.0,
        help="Target preview FPS or capture rate. Default: 10.0.",
    )
    parser.add_argument("--top", type=int, help="Top coordinate for manual preset save.")
    parser.add_argument("--left", type=int, help="Left coordinate for manual preset save.")
    parser.add_argument("--width", type=int, help="Width for manual preset save.")
    parser.add_argument("--height", type=int, help="Height for manual preset save.")

    return parser


def main() -> None:
    """Execute vision CLI commands."""
    parser = build_parser()
    args = parser.parse_args()

    calibrator = RegionCalibrator()

    if args.monitors:
        with ScreenCaptureEngine() as engine:
            monitors = engine.get_monitors()
            print("Detected Monitors:")
            for idx, m in enumerate(monitors):
                label = "Virtual All" if idx == 0 else f"Monitor {idx}"
                print(
                    f"  [{label}] Left: {m['left']}, Top: {m['top']}, "
                    f"Width: {m['width']}, Height: {m['height']}"
                )
        return

    if args.list_presets:
        presets = calibrator.list_presets()
        if not presets:
            print("No presets found in config/regions/.")
        else:
            print("Saved Calibration Presets:")
            for p in presets:
                config = calibrator.load_preset(p)
                if config:
                    r = config.region
                    print(
                        f"  - {p}: left={r.left}, top={r.top}, width={r.width}, height={r.height}"
                    )
        return

    if args.manual:
        if None in (args.top, args.left, args.width, args.height):
            print(
                "Error: --manual requires --top, --left, --width, and --height.",
                file=sys.stderr,
            )
            sys.exit(1)
        region = ScreenRegion(
            top=args.top,
            left=args.left,
            width=args.width,
            height=args.height,
        )
        saved = calibrator.save_preset(preset_name=args.preset, region=region, target_fps=args.fps)
        print(
            f"Saved manual preset '{saved.preset_name}' (region: {saved.region.width}x{saved.region.height})."
        )
        return

    if args.calibrate:
        print(f"Starting interactive calibration for preset '{args.preset}'...")
        result = calibrator.calibrate_interactive(
            preset_name=args.preset,
            target_fps=args.fps,
            delay=args.delay,
        )
        if result:
            print(
                f"Successfully calibrated and saved preset '{result.preset_name}': "
                f"Left={result.region.left}, Top={result.region.top}, "
                f"Width={result.region.width}, Height={result.region.height}"
            )
        else:
            print("Calibration cancelled or invalid selection.")
        return

    if args.preview:
        try:
            print(f"Launching live preview for preset '{args.preset}' at {args.fps} FPS...")
            print("Press 'q' or ESC in the preview window to stop.")
            calibrator.live_preview(preset_name=args.preset, fps=args.fps)
        except FileNotFoundError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main()
