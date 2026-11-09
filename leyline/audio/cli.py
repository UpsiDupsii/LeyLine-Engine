"""Command line interface for LeyLine Neural Voice Engine and Commentator."""

from __future__ import annotations

import argparse
import asyncio
import sys
import time

import edge_tts

from leyline.audio.models import CommentatorPersona, GameEvent, GameEventType, VoiceConfig
from leyline.audio.orchestrator import CommentaryOrchestrator
from leyline.audio.voice import NeuralVoiceEngine


async def list_available_voices() -> None:
    """Print high-fidelity English neural voices supported by edge-tts."""
    print("\nQuerying Microsoft Edge Neural TTS voice registry...")
    voices = await edge_tts.list_voices()
    en_voices = [v for v in voices if v["Locale"].startswith("en-")]

    print(f"\nDiscovered {len(en_voices)} English neural voices.\n")
    print(f"{'Voice ID':<35} | {'Gender':<7} | {'Locale':<10} | {'Friendly Name'}")
    print("-" * 80)
    for v in sorted(en_voices, key=lambda x: x["ShortName"]):
        friendly = (
            v.get("FriendlyName", "").replace("Microsoft ", "").replace(" Online (Natural)", "")
        )
        print(f"{v['ShortName']:<35} | {v['Gender']:<7} | {v['Locale']:<10} | {friendly}")

    print("\nRecommended for YouTube live streams:")
    for role, vid in NeuralVoiceEngine.RECOMMENDED_VOICES.items():
        print(f"  - {role:<18}: {vid}")
    print()


def run_demo(voice: str, persona: CommentatorPersona) -> None:
    """Run an interactive 3-event esports shoutcasting audio demo."""
    print(f"\nStarting LeyLine Audio Demo | Voice: {voice} | Persona: {persona.value.upper()}")
    config = VoiceConfig(voice_name=voice, rate="+5%")
    orchestrator = CommentaryOrchestrator(
        voice_config=config,
        persona=persona,
        cooldown_seconds=1.0,
    )
    orchestrator.start()

    events = [
        GameEvent(
            event_type=GameEventType.GAME_START,
            details="Starting Ball Guys broadcast run",
        ),
        GameEvent(
            event_type=GameEventType.MATCH_MERGE,
            ball_tier="Small Light Blue",
            target_x=0.29,
            danger_level=0.15,
            details="Laser-accurate drop fusing two blue balls into purple",
        ),
        GameEvent(
            event_type=GameEventType.VALLEY_DROP,
            ball_tier="Medium Purple",
            target_x=0.68,
            danger_level=0.35,
            details="Balancing open valley on right side of container",
        ),
    ]

    for ev in events:
        print(f"\n[EVENT] {ev.event_type.value.upper()} | Ball: {ev.ball_tier}")
        orchestrator.post_event(ev)
        # Wait for speech to complete
        time.sleep(2.0)
        while orchestrator.is_speaking:
            time.sleep(0.2)
        print(f'  [CASTER SAYS]: "{orchestrator.current_text}"')

    orchestrator.stop()
    print("\nDemo completed. Audio and live subtitles written to output/audio/")


def build_parser() -> argparse.ArgumentParser:
    """Build CLI parser for the audio and commentator engine."""
    parser = argparse.ArgumentParser(description="LeyLine Neural Voice Engine & Commentator CLI.")
    parser.add_argument(
        "--list-voices",
        action="store_true",
        help="List all high-fidelity English neural voices.",
    )
    parser.add_argument(
        "--speak",
        type=str,
        default=None,
        help="Synthesize and play custom speech text immediately.",
    )
    parser.add_argument(
        "--voice",
        type=str,
        default="en-US-ChristopherNeural",
        help="Voice ID (e.g. en-US-ChristopherNeural, en-US-GuyNeural). Default: 'en-US-ChristopherNeural'.",
    )
    parser.add_argument(
        "--persona",
        type=str,
        choices=["hype", "analytical", "sarcastic", "casual"],
        default="hype",
        help="Caster personality style. Default: 'hype'.",
    )
    parser.add_argument(
        "--rate",
        type=str,
        default="+5%",
        help="Speech speed rate (e.g. +5%%, +10%%, -5%%). Default: '+5%%'.",
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Run a 3-event esports shoutcasting audio demo.",
    )
    return parser


def main() -> None:
    """Entrypoint for the audio CLI."""
    parser = build_parser()
    args = parser.parse_args()

    if args.list_voices:
        asyncio.run(list_available_voices())
        sys.exit(0)

    if args.demo:
        run_demo(voice=args.voice, persona=CommentatorPersona(args.persona))
        sys.exit(0)

    if args.speak:
        config = VoiceConfig(voice_name=args.voice, rate=args.rate)
        engine = NeuralVoiceEngine(config=config)
        print(f'Synthesizing: "{args.speak}" using {args.voice}...')
        engine.speak(args.speak)
        # Wait for playback
        while engine.is_speaking():
            time.sleep(0.1)
        print("Playback finished.")
        sys.exit(0)

    parser.print_help()


if __name__ == "__main__":
    main()
