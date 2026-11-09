# LeyLine-Engine

[![CI](https://github.com/UpsiDupsii/LeyLine-Engine/actions/workflows/ci.yml/badge.svg)](https://github.com/UpsiDupsii/LeyLine-Engine/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

LeyLine is an autonomous dual-agent AI gaming platform designed to play video games (Roblox, garbage truck simulators, open-world car games, Subway Surfers, NES classics) while running a dynamic, real-time AI live commentator powered by Google Gemini. Built with live streaming in mind (YouTube Live / OBS).

---

## Key Features

- Autonomous Vehicle & Truck Agent: Tactical driving AI that steers, accelerates with sustained throttle pulses, explores roads, and collects targets (garbage, coins, delivery points).
- DirectInput Hardware Controller: Kernel-level keyboard scan code simulation via Windows SendInput, guaranteeing 100% responsiveness in Chromium WebGL, Unity, and desktop games.
- Real-Time Telemetry HUD: OpenCV display window rendering captured game frames, AI steering decisions, latency metrics, and tactical reasoning.
- Screen Perception Engine: Sub-millisecond screen frame grabber and interactive ROI calibrator using mss and OpenCV.
- Non-Blocking Architecture: Decoupled vision-action loop and commentary synthesis ensures zero steering lag.
- Realistic Neural TTS: Natural esports voice output powered by edge-tts.
- Stream-Ready: Designed to output video and audio layers directly compatible with OBS Studio for YouTube Live streams.

---

## Architecture

```mermaid
flowchart TD
    subgraph Target ["Game Environment"]
        Screen["Game Screen (Browser / Truck Simulator / Roblox)"]
        DirectInput["Windows DirectInput Hardware Scan Codes"]
    end

    subgraph Core ["LeyLine Perception"]
        Capture["High-speed Screen Capture (mss / OpenCV)"]
    end

    subgraph Agents ["Dual-Agent System"]
        TruckAgent["Truck / Driving Agent\n- Navigation & obstacle scan\n- Sustained throttle & steering"]
        CommentatorAgent["Commentator Agent (Gemini / Groq)\n- Event analysis\n- Persona-based play-by-play"]
    end

    subgraph Output ["Audio & Stream Output"]
        TTS["Neural TTS Engine (edge-tts)"]
        StreamAudio["Virtual Audio / OBS Stream"]
    end

    Screen --> Capture
    Capture -->|Downsampled frames| TruckAgent
    TruckAgent -->|Hardware Scan Codes (W/A/S/D)| DirectInput
    DirectInput --> Screen
    Capture -.->|Highlight snapshots| CommentatorAgent
    TruckAgent -.->|Driving telemetry| CommentatorAgent
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

## Playing Garbage Truck & Driving Games (Step-by-Step)

Truck driving and delivery games are optimal for AI navigation because vehicles have realistic physics, sustained acceleration, and tactical objectives (collecting garbage, delivering to depot, upgrading).

### Step 1: Open Your Truck Game
Open your garbage truck or car game in Chrome or your desktop browser. Start the level so your truck is on the road.

### Step 2: Calibrate the Game Region
Tell LeyLine where your game window is located on screen:
```bash
python -m leyline.vision --calibrate --preset truck_game --delay 4
```
- You will see a 4-second countdown in your terminal. Switch to your game window.
- When the snapshot freezes on screen, click and drag a box around the gameplay area.
- Press `ENTER` to save the preset.

### Step 3: Run the Autonomous Truck Driver
Launch the autonomous driver with hardware DirectInput:
```bash
python -m leyline.runner --preset truck_game --agent truck --layout wasd --fps 2.5 --hold-time 0.4
```
- A 3-second start countdown will run in the terminal. Click into your game window.
- The AI driver will perceive the road, hold `W` to accelerate, use `A`/`D` to steer towards garbage, reverse (`S`) if facing an obstacle, and press `E` to interact.
- Press `q` or `ESC` in the LeyLine HUD window at any time to immediately stop and release all keys.

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
- [x] Autonomous truck / vehicle driver agent with sustained throttle
- [x] Subway Surfers fast reflex lane agent (sub-3ms)
- [x] Real-time live HUD overlay runner (OpenCV)
- [ ] Commentator agent with edge-tts live voice streaming
- [ ] OBS virtual camera & audio routing for YouTube Live
- [ ] Game-specific presets (Truck Simulator, Subway Surfers, Contra, Roblox)

---

## License

MIT License. See [LICENSE](LICENSE) for details.
