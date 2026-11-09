# LeyLine-Engine

[![CI](https://github.com/UpsiDupsii/LeyLine-Engine/actions/workflows/ci.yml/badge.svg)](https://github.com/UpsiDupsii/LeyLine-Engine/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

LeyLine is an autonomous dual-agent AI gaming platform designed to play video games (Ball Guys / Suika merge puzzles, Roblox, vehicle simulators, Subway Surfers, NES classics) while running a dynamic, real-time AI live commentator powered by Google Gemini. Built with live streaming in mind (YouTube Live / OBS).

---

## Key Features

- Ball Guys / Suika Merge Solver: Physics-aware puzzle solver that analyzes hanging balls and resting container piles, calculates optimal horizontal drop coordinates (`drop_x`), and positions cursor clicks to trigger cascading merges.
- Autonomous Vehicle & Truck Agent: Tactical driving AI with continuous hardware throttle and obstacle avoidance.
- DirectInput & Hardware Mouse Controllers: Kernel-level mouse positioning, clicks, and keyboard scan codes via Windows SendInput for 100% browser canvas compatibility.
- Real-Time Telemetry HUD: OpenCV display window rendering captured game frames, drop trajectory guide lines, latency metrics, and tactical reasoning.
- Screen Perception Engine: Sub-millisecond screen frame grabber and interactive ROI calibrator using mss and OpenCV.
- Non-Blocking Architecture: Decoupled vision-action loop and commentary synthesis ensures zero steering lag.
- Realistic Neural TTS: Natural esports voice output powered by edge-tts.
- Stream-Ready: Designed to output video and audio layers directly compatible with OBS Studio for YouTube Live streams.

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
        BallGuysAgent["Ball Guys / Suika Solver\n- Hanging ball identification\n- Pile density & merge matching\n- Drop coordinate calculation"]
        CommentatorAgent["Commentator Agent (Gemini / Groq)\n- Event analysis\n- Persona-based play-by-play"]
    end

    subgraph Output ["Audio & Stream Output"]
        TTS["Neural TTS Engine (edge-tts)"]
        StreamAudio["Virtual Audio / OBS Stream"]
    end

    Screen --> Capture
    Capture -->|Downsampled container frames| BallGuysAgent
    BallGuysAgent -->|Mouse Move & Click at drop_x| Inputs
    Inputs --> Screen
    Capture -.->|Highlight snapshots| CommentatorAgent
    BallGuysAgent -.->|Merge telemetry| CommentatorAgent
    CommentatorAgent -->|Punchy commentary| TTS
    TTS --> StreamAudio
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

## Playing "Ball Guys" Merge Puzzle (Step-by-Step)

Ball Guys is a physics drop puzzle (similar to the Watermelon / Suika game). Dropping identical balls together merges them into larger balls (Small Blue -> Medium Purple -> King Ball). The goal is to maximize mergers while keeping the pile below the red dashed game-over line.

### Step 1: Open Ball Guys in Your Browser
Open Ball Guys in Chrome or your browser. Position the browser window so the blue container is visible on your screen.

### Step 2: Calibrate the Container Box
Tell LeyLine where the blue container is located:
```bash
python -m leyline.vision --calibrate --preset ball_guys --delay 4
```
- During the 4-second countdown, switch to your Ball Guys browser window.
- When the screen freezes, click and drag a rectangle strictly around the **blue container cup** (from the left wall to the right wall, including the red dashed line at the top).
- Press `ENTER` to save the preset.

### Step 3: Run the Autonomous Puzzle Solver
```bash
python -m leyline.runner --preset ball_guys --agent ball_guys --settle-time 2.0
```
- A 3-second countdown will display: `[3]... [2]... [1]... [GO!]`. Focus on the Ball Guys window.
- The AI will evaluate the current hanging ball and resting pile, calculate the optimal drop position `drop_x`, move the mouse, click to release the ball, wait for physics to settle, and repeat.
- The HUD window will display the vertical yellow drop guide line, the target merge match, and latency telemetry.
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
- [ ] Commentator agent with edge-tts live voice streaming
- [ ] OBS virtual camera & audio routing for YouTube Live
- [ ] Game-specific presets (Ball Guys, Truck Simulator, Subway Surfers, Roblox)

---

## License

MIT License. See [LICENSE](LICENSE) for details.
