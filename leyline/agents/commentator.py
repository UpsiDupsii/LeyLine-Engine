"""Dynamic esports shoutcaster commentator agent for live video game streams.

Generates broadcast-quality play-by-play and color commentary with customizable
caster personas (Hype, Analytical, Sarcastic, Casual) and non-repetition caching.
"""

from __future__ import annotations

import random

import requests

from leyline.audio.models import CommentatorPersona, GameEvent, GameEventType
from leyline.config import GEMINI_API_KEY, GROQ_API_KEY


class CommentatorAgent:
    """Generates punchy, human-like live commentary scripts for video game streaming."""

    # Rich contextual phrase banks per persona and event type
    PHRASE_BANKS: dict[CommentatorPersona, dict[GameEventType, list[str]]] = {
        CommentatorPersona.HYPE: {
            GameEventType.MATCH_MERGE: [
                "Boom! Clean connection right down the middle, fusing that {tier} instantly!",
                "Look at the accuracy on that drop! Two {tier}s meet, and that is a textbook merge!",
                "Surgical precision! Dropping right onto the matching ball, what a sensational play!",
                "That is how you execute! Dropped with pinpoint timing, and the physics take care of the rest!",
                "Absolute laser focus! An instant combination that completely clears room in the pocket!",
                "Bang! Direct hit on the {tier}! The momentum is building fast right now!",
            ],
            GameEventType.VALLEY_DROP: [
                "Smart tactical placement! Finding the lowest valley on the floor to stabilize the pile!",
                "Playing the long game! Dropping that {tier} cleanly into the pocket to balance the board!",
                "Look at the board vision! Setting up the next sequence by leveling out the terrain!",
                "Controlled drop into the open valley! That keeps the center flat and prevents an early stack!",
            ],
            GameEventType.RED_LINE_DANGER: [
                "Warning lights are flashing! We are dangerously close to the red line limit!",
                "Heart in mouth moment right there! The balls are rocking right on the edge of the red zone!",
                "Living right on the razor edge! One bad bounce could overflow the entire container!",
                "High pressure situation! The stack is climbing and the margin for error is razor thin!",
            ],
            GameEventType.CHAIN_REACTION: [
                "Oh baby, what a sequence! An explosive chain reaction rolling through the entire container!",
                "The domino effect! Balls colliding and cascading into higher tier merges across the board!",
                "Unbelievable combo! The board completely opens up as consecutive merges trigger!",
            ],
            GameEventType.GAME_START: [
                "Welcome in, chat! The autonomous gaming engine is live, locked in, and ready to dominate!",
                "We are live on stream! Clean board, zero mistakes, let us see how high we can push this run!",
            ],
            GameEventType.GAME_OVER: [
                "Tough break! The physics just barely spilled over the line. We run it right back, chat!",
                "GG! What an incredible run, but that stack finally caught up to us. Let us reset and go again!",
            ],
            GameEventType.IDLE_BANTER: [
                "Checking the geometry here, watching every bounce as the physics settle down.",
                "Chat, the patience on display here is remarkable. Every single pixel matters.",
            ],
        },
        CommentatorPersona.ANALYTICAL: {
            GameEventType.MATCH_MERGE: [
                "Optimal play chosen. Direct vertical trajectory onto the identical {tier} maximizes merge probability.",
                "Notice the angle of approach. Aligning directly over the matching center of mass guarantees a merge.",
                "Mathematically sound drop. Eliminating the {tier} consolidates volume and lowers overall pile height.",
                "Clean physics resolution. By dropping directly on target, rolling deviation is minimized.",
            ],
            GameEventType.VALLEY_DROP: [
                "Leveling maneuver executed. Distributing weight to Column {col} to minimize peak board variance.",
                "Notice how the algorithm selects the column with minimum relative height to maintain equilibrium.",
                "Defensive placement. Avoiding the central peak keeps the system well beneath the critical threshold.",
            ],
            GameEventType.RED_LINE_DANGER: [
                "Warning: Peak elevation has exceeded 80 percent of container capacity. High overflow risk.",
                "Critical threshold approaching. The current fill factor requires aggressive consolidation merges.",
            ],
            GameEventType.CHAIN_REACTION: [
                "Cascading kinetic resolution. The secondary collision induced an immediate secondary tier promotion.",
                "Compounding efficiency. Two consecutive merges reduced total board volume by nearly thirty percent.",
            ],
            GameEventType.GAME_START: [
                "Initializing solver perception. Beginning baseline container scan and telemetry tracking.",
            ],
            GameEventType.GAME_OVER: [
                "Terminal state reached due to boundary overflow. Analyzing telemetry for next iteration.",
            ],
            GameEventType.IDLE_BANTER: [
                "Allowing damping oscillations to settle before sampling the next frame state.",
            ],
        },
        CommentatorPersona.SARCASTIC: {
            GameEventType.MATCH_MERGE: [
                "Well, would you look at that, it actually hit the right ball for once. Color me impressed.",
                "A blindfolded pigeon could have made that merge, but hey, points on the board.",
                "Look at Einstein over here, matching blue with blue. Truly ground-breaking stuff.",
            ],
            GameEventType.VALLEY_DROP: [
                "Tossing that ball into the corner and hoping for the best. Solid life strategy.",
                "Not the flashiest move, but at least we are not throwing the game away just yet.",
            ],
            GameEventType.RED_LINE_DANGER: [
                "Chat, start preparing your Fs in the chat, because this red line is looking hungry.",
                "Sweating bullets right now. One millimeter higher and we are packing our bags.",
            ],
            GameEventType.CHAIN_REACTION: [
                "Okay, I take back ten percent of what I said. That combo was actually pretty slick.",
            ],
            GameEventType.GAME_START: [
                "Here we go again, folks. Grab your popcorn and let us see how long we survive this time.",
            ],
            GameEventType.GAME_OVER: [
                "And there it is. Down in flames. Beautiful catastrophe.",
            ],
            GameEventType.IDLE_BANTER: [
                "Still waiting on these balls to stop bouncing around like they own the place.",
            ],
        },
        CommentatorPersona.CASUAL: {
            GameEventType.MATCH_MERGE: [
                "Nice and smooth. Good little merge right there to keep the momentum going.",
                "There we go, clean connection on the {tier}. That feels great.",
                "Solid drop. Just taking what the board gives us and keeping it tidy.",
            ],
            GameEventType.VALLEY_DROP: [
                "Dropping it in the low spot for now. Keeps everything nice and even.",
                "Just tucking that one into the open slot. No need to force anything crazy.",
            ],
            GameEventType.RED_LINE_DANGER: [
                "Whoa, that is getting pretty high up there. Definitely need a couple merges soon.",
                "A little close for comfort right now, but we are hanging in there.",
            ],
            GameEventType.CHAIN_REACTION: [
                "Oh sweet, double merge! Love to see that happen out of nowhere.",
            ],
            GameEventType.GAME_START: [
                "Hey everyone, chilling with some puzzle games today. Let us get some good runs going.",
            ],
            GameEventType.GAME_OVER: [
                "Ah, tough bounce at the end there. Good run though, let us restart.",
            ],
            GameEventType.IDLE_BANTER: [
                "Just letting everything settle into place before making the next move.",
            ],
        },
    }

    def __init__(
        self,
        persona: CommentatorPersona = CommentatorPersona.HYPE,
        api_key: str = GEMINI_API_KEY,
        groq_api_key: str = GROQ_API_KEY,
        enable_llm: bool = True,
        mock_mode: bool = False,
    ) -> None:
        self.persona = persona
        self.api_key = api_key
        self.groq_api_key = groq_api_key
        self.enable_llm = enable_llm
        self.mock_mode = mock_mode
        self.recent_history: list[str] = []
        self.max_history = 10

    def generate_commentary(self, event: GameEvent) -> str:
        """Generate a punchy, contextual 1-sentence live commentary line."""
        # 1. Attempt Cloud LLM generation if enabled
        if self.enable_llm and not self.mock_mode:
            cloud_line = self._generate_via_cloud(event)
            if cloud_line:
                self._record_history(cloud_line)
                return cloud_line

        # 2. High-speed procedural caster generation with anti-repetition filter
        line = self._generate_procedural(event)
        self._record_history(line)
        return line

    def _generate_procedural(self, event: GameEvent) -> str:
        """Generate a fresh phrase from the curated caster banks without repeating recent lines."""
        persona_banks = self.PHRASE_BANKS.get(
            self.persona, self.PHRASE_BANKS[CommentatorPersona.HYPE]
        )
        candidates = persona_banks.get(
            event.event_type,
            persona_banks.get(GameEventType.MATCH_MERGE, ["Clean play executed on stream!"]),
        )

        # Filter out phrases used in the last N cycles
        fresh_candidates = [c for c in candidates if c not in self.recent_history]
        chosen_template = random.choice(fresh_candidates if fresh_candidates else candidates)

        # Format template with event variables
        col_num = int(event.target_x * 5) + 1
        formatted = chosen_template.format(
            tier=event.ball_tier,
            col=col_num,
            x=f"{event.target_x:.2f}",
        )
        return formatted

    def _generate_via_cloud(self, event: GameEvent) -> str | None:
        """Attempt to call Gemini API for contextual broadcast lines."""
        if not self.api_key:
            return None

        prompt = (
            f"You are a live YouTube esports shoutcaster with a {self.persona.value.upper()} persona.\n"
            f"Current Play: Event: {event.event_type.value}, Ball Tier: {event.ball_tier}, "
            f"Drop Position: {event.target_x:.2f}, Danger Level: {event.danger_level:.2f}. "
            f"Details: {event.details}.\n"
            "Deliver ONE punchy, natural, broadcast-ready commentary sentence (15-25 words). "
            "Speak like a real human caster on a live YouTube gaming stream. Do not use emojis."
        )

        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"gemini-3-flash-preview:generateContent?key={self.api_key}"
        )
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.8, "maxOutputTokens": 60},
        }

        try:
            resp = requests.post(url, json=payload, timeout=2.5)
            if resp.status_code == 200:
                data = resp.json()
                text = (
                    data.get("candidates", [{}])[0]
                    .get("content", {})
                    .get("parts", [{}])[0]
                    .get("text", "")
                    .strip()
                )
                if text and len(text) > 5:
                    return text.replace('"', "").replace("\n", " ")
        except Exception:
            pass

        return None

    def _record_history(self, line: str) -> None:
        self.recent_history.append(line)
        if len(self.recent_history) > self.max_history:
            self.recent_history.pop(0)

    def set_persona(self, persona: CommentatorPersona) -> None:
        """Switch caster personality on the fly."""
        self.persona = persona
