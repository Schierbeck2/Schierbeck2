"""Runtime configuration: paths and environment-driven knobs."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass


PKG_DIR = Path(__file__).resolve().parent
ROOT_DIR = PKG_DIR.parent
DATA_DIR = ROOT_DIR / "data"
UPLOAD_DIR = DATA_DIR / "uploads"
OUTPUT_DIR = DATA_DIR / "outputs"
CLIPS_DIR = DATA_DIR / "clips"
CACHE_DIR = DATA_DIR / "cache"

for d in (UPLOAD_DIR, OUTPUT_DIR, CLIPS_DIR, CACHE_DIR):
    d.mkdir(parents=True, exist_ok=True)


@dataclass(frozen=True)
class Settings:
    anthropic_api_key: str | None = os.getenv("ANTHROPIC_API_KEY")
    coach_model: str = os.getenv("COACH_MODEL", "claude-sonnet-4-6")
    yolo_model: str = os.getenv("YOLO_MODEL", "yolov8n.pt")
    device: str = os.getenv("DEVICE", "cpu")
    # Frame sampling for the tracker. 1 = every frame, 2 = every other, etc.
    frame_stride: int = int(os.getenv("FRAME_STRIDE", "2"))
    # How many frames a track must persist before we trust it.
    min_track_len: int = int(os.getenv("MIN_TRACK_LEN", "8"))
    # Seconds of video around each detected event to keep as a highlight clip.
    clip_pad_seconds: float = float(os.getenv("CLIP_PAD_SECONDS", "2.5"))


SETTINGS = Settings()
