"""Configuration loader for LeyLine Engine."""

import os
from pathlib import Path

from dotenv import load_dotenv

# Load .env if present
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")

VISION_FPS: float = float(os.getenv("VISION_FPS", "2.0"))
COMMENTARY_INTERVAL_SEC: float = float(os.getenv("COMMENTARY_INTERVAL_SEC", "3.0"))
VOICE_NAME: str = os.getenv("VOICE_NAME", "en-US-ChristopherNeural")
DEBUG_MODE: bool = os.getenv("DEBUG_MODE", "false").lower() in ("true", "1", "yes")
