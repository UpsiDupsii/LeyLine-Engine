# LeyLine-Engine

[![CI](https://github.com/UpsiDupsii/LeyLine-Engine/actions/workflows/ci.yml/badge.svg)](https://github.com/UpsiDupsii/LeyLine-Engine/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

LeyLine is an autonomous dual-agent AI gaming platform designed to play video games (Ball Guys / Suika merge puzzles, Roblox, vehicle simulators, Subway Surfers, NES classics) while running a dynamic, real-time AI live commentator powered by Google Gemini and Microsoft Edge Neural TTS. Built specifically for YouTube Live and OBS streaming.

---

## Key Features

- Ball Guys / Suika Merge Solver: Physics-aware puzzle solver that analyzes hanging balls and resting container piles, calculates optimal horizontal drop coordinates (`drop_x`), and positions cursor clicks to trigger cascading merges. Features deterministic Computer Vision color/tier matching, valley leveling, and pre-drop alignment verification.
- Dynamic AI Esports Shoutcaster: Asynchronous live commentator analyzing game plays, drop accuracy, merge cascades, and red line danger. Features customizable broadcast personas (`hype`, `analytical`, `sarcastic`, `casual`).
- Studio-Grade Neural Voice Engine: Microsoft Edge Neural TTS deep learning voices (`en-US-ChristopherNeural`, `en-US-GuyNeural`, `en-US-AndrewMultilingualNeural`) with natural human-like prosody, inflection, and pronunciation.
- YouTube Live & Monetization Ready: 100% compliant with YouTube Partner Program / AdSense guidelines (original real-time gameplay analysis, natural deep neural voices, and anti-repetition phrasing).
- OBS Studio Streaming Pipeline: Outputs broadcast audio directly and writes real-time stream subtitles to `output/audio/subtitles.txt` for live OBS text overlays.
- DirectInput & Hardware Mouse Controllers: Kernel-level mouse positioning, clicks, and keyboard scan codes via Windows SendInput for 100% browser canvas compatibility.
- Real-Time Telemetry HUD: OpenCV display window rendering captured game frames, drop trajectory guide lines, detected container bounds and ball tiers, alignment verification status, live caster subtitles, and tactical reasoning.
- Screen Perception Engine: Sub-millisecond screen frame grabber and interactive ROI calibrator using mss and OpenCV.
- Non-Blocking Architecture: Decoupled perception-action loop and commentary synthesis ensures zero gameplay lag.

---

## Architecture

```mermaid
flowchart TD
    subgraph Target ["Game Environment"]
        Screen["Game Screen (Ball Guys / Browser / Roblox)"]
        Inputs["Windows Hardware Mouse & Keyboard Inputs"]
    end

    subgraph Core ["LeyLine Perception"]
        Capture["High-speed Screen Capture (mss / OpenCV)"]
    end

    subgraph Agents ["Dual-Agent System"]
        BallGuysAgent["Ball Guys / Suika Solver\n- Hanging ball identification\n- Pile density & merge matching\n- Alignment verification & drop"]
        CommentatorAgent["Commentator Agent (Gemini / Edge TTS)\n- Event analysis (merges, valleys, danger)\n- Persona-based play-by-play (Hype/Analyst)"]
    end

    subgraph Output ["Audio & Stream Output"]
        TTS["Neural TTS Engine (edge-tts / 24kHz)"]
        OBS["OBS Studio\n- Desktop Audio Source\n- Live Subtitles (output/audio/subtitles.txt)"]
    end

    Screen --> Capture
    Capture -->|Downsampled container frames| BallGuysAgent
    BallGuysAgent -->|Mouse Move & Click at drop_x| Inputs
    Inputs --> Screen
    BallGuysAgent -.->|Telemetry & Game Events| CommentatorAgent
    CommentatorAgent -->|Punchy broadcast script| TTS
    TTS -->|Non-blocking Audio Playback| OBS
    TTS -->|Live Subtitle Overlay| OBS
```

---

## Quickstart & Environment Setup

### 1. Prerequisites
- Python 3.10 or higher
- A Google Gemini API Key (Google AI Studio: https://aistudio.google.com/)

### 2. Virtual Environment Setup

```bash
# Clone the repository
git clone https://github.com/UpsiDupsii/LeyLine-Engine.git
cd LeyLine-Engine

# Create virtual environment (if not already present)
python -m venv .venv

# Activate in PowerShell (Windows):
.venv\Scripts\Activate.ps1

# Activate in Command Prompt (cmd.exe):
# .venv\Scripts\activate.bat
```

### 3. Install Dependencies

With `.venv` active, install dependencies:

```bash
pip install -r requirements-dev.txt
```

### 4. Configure Secrets

Copy `.env.example` to `.env` and insert your API keys:

```bash
cp .env.example .env
```

Edit `.env`:
```env
GEMINI_API_KEY=your_gemini_api_key_here
GROQ_API_KEY=your_groq_api_key_here
```

---

## AI Neural Voice Commentary & YouTube Live Streaming

### Why LeyLine Commentary is YouTube Monetization Friendly
- **Original Content:** The commentary is uniquely generated in real-time based on live game board states, pile geometry, and physics events.
- **Natural Neural Voices:** Uses Microsoft Edge Neural TTS voices (`en-US-ChristopherNeural`, `en-US-GuyNeural`, `en-US-AndrewMultilingualNeural`) trained on human speech, with realistic inflection, natural breathing pauses, and accurate pronunciation.
- **Anti-Repetition Cache:** Procedural and AI phrase banks actively rotate templates to prevent repetitive or robotic phrases.

### Available Broadcaster Personas
- `hype`: Energetic esports shoutcaster delivering exciting play-by-play calls.
- `analytical`: Tactical grandmaster discussing physics, angles, and merge probabilities.
- `sarcastic`: Witty, humorous caster reacting to close calls and dramatic drops.
- `casual`: Laid-back, conversational streamer vibe.

### Testing Voices in Terminal
```bash
# List all 47 English neural voices
python -m leyline.audio --list-voices

# Test speech with esports voice
python -m leyline.audio --speak "What an incredible drop! Laser precision right into the pocket!" --voice en-US-ChristopherNeural

# Run an interactive 3-event esports shoutcaster demo
python -m leyline.audio --demo --persona hype
```

### Connecting to OBS Studio for Live Streaming
1. **Audio Layer:** In OBS Studio, ensure **Desktop Audio** is enabled. LeyLine plays high-fidelity neural audio through the system default device.
2. **Live Subtitle Overlay:**
   - In OBS Studio, add a new **Source** -> **Text (GDI+)**.
   - Check the box **Read from file**.
   - Browse and select `output/audio/subtitles.txt`.
   - Customize font, color, and outline as desired. As the AI speaks, subtitles will automatically update live on your stream.

---

## Playing "Ball Guys" with Live AI Commentary (Step-by-Step)

Ball Guys is a physics drop puzzle (similar to the Watermelon / Suika game). Dropping identical balls together merges them into larger balls (Small Blue -> Medium Purple -> Larger Balls up to King Ball). The goal is to maximize mergers while keeping the pile below the red dashed game-over line.

### Step 1: Open Ball Guys in Your Browser
Open Ball Guys in Chrome or your browser. Position the browser window so the blue container is visible on your screen.

### Step 2: Calibrate the Container Box (Optional if Using Full Window)
Tell LeyLine where the container is located:
```bash
python -m leyline.vision --calibrate --preset ball_guys --delay 4
```
- During the 4-second countdown, switch to your Ball Guys browser window.
- When the screen freezes, click and drag a rectangle around the container (or select your browser window; the built-in Computer Vision detector will automatically find the blue container borders inside the captured region).
- Press `ENTER` to save the preset.

### Step 3: Run the Autonomous Puzzle Solver with AI Commentary
```bash
python -m leyline.runner --preset ball_guys --agent ball_guys --settle-time 2.2 --voice en-US-ChristopherNeural --persona hype
```
- A 3-second countdown will display: `[3]... [2]... [1]... [GO!]`. Focus on the Ball Guys window.
- The 5-Phase Autonomous Loop:
  1. Perceive: High-speed CV identifies the top active ball, container bounds, red dashed line, and resting balls.
  2. Aim: Moves the mouse cursor to the optimal drop coordinate (matching identical ball colors or leveling valleys).
  3. Hover & Verify Alignment: Waits for the in-game dropper needle to glide to the mouse, captures a fresh verification snapshot, verifies that the needle is centered over the target, and micro-adjusts if off-target.
  4. Release: Clicks the left mouse button to release the ball.
  5. Settle: Waits for balls to drop, roll, bounce, and merge before taking the next turn.
- While the agent plays, the AI Commentator analyzes the drops, merges, and close calls, shouting out live commentary and updating subtitles on screen.
- Press `q` or `ESC` in the HUD window to stop at any time.

---

## Development & CI

```bash
# Run test suite
python -m pytest tests/

# Check linting
python -m ruff check .

# Check formatting
python -m ruff format --check .

# Auto-fix formatting
python -m ruff format .
```

---

## Roadmap

- [x] Initial project scaffolding & CI setup with Ruff
- [x] Screen region capture & visual calibration tool with countdown delay
- [x] DirectInput hardware scan code keyboard controller (SendInput)
- [x] Hardware mouse controller for click-to-drop puzzle games
- [x] Ball Guys / Suika merge puzzle solver agent
- [x] Autonomous truck / vehicle driver agent with sustained throttle
- [x] Subway Surfers fast reflex lane agent (sub-3ms)
- [x] Real-time live HUD overlay runner with drop line visualizations (OpenCV)
- [x] Asynchronous Commentator agent with edge-tts neural voice streaming
- [x] OBS Studio audio and live subtitle integration
- [ ] OBS virtual camera routing for YouTube Live
- [ ] Game-specific presets (Ball Guys, Truck Simulator, Subway Surfers, Roblox)

---

## License

MIT License. See [LICENSE](LICENSE) for details.
