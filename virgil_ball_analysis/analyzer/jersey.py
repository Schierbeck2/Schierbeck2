"""Jersey-number OCR.

For each player track we sample frames, crop the torso/back area, and run
EasyOCR. We keep digit-only outputs in [0, 99] and pick the per-track winner
by confidence-weighted majority vote.

EasyOCR is imported lazily; if it isn't installed the module returns no
numbers and the rest of the pipeline still works (players keep their
"Player #<track_id>" names).
"""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass
from typing import Callable, Optional

import numpy as np

from .tracker import Detection


JERSEY_RE = re.compile(r"^\d{1,2}$")


@dataclass
class JerseyReading:
    track_id: int
    number: Optional[str]
    confidence: float
    n_supporting_frames: int


def _torso_crop(frame: np.ndarray, bbox: tuple[float, float, float, float]) -> Optional[np.ndarray]:
    """Take the upper-middle section of the player bbox where the number lives."""
    h, w = frame.shape[:2]
    x1, y1, x2, y2 = (int(max(0, v)) for v in bbox)
    x2 = min(w, x2); y2 = min(h, y2)
    if x2 - x1 < 20 or y2 - y1 < 40:
        return None
    bh = y2 - y1
    # Numbers usually sit between ~15% and ~55% of player height.
    ty1 = y1 + int(0.15 * bh)
    ty2 = y1 + int(0.55 * bh)
    crop = frame[ty1:ty2, x1:x2]
    if crop.size == 0:
        return None
    return crop


def read_jersey_numbers(
    detections: list[Detection],
    frame_lookup: Callable[[int], np.ndarray],
    samples_per_track: int = 8,
    min_confidence: float = 0.4,
) -> dict[int, JerseyReading]:
    """Return {track_id: JerseyReading}. Tracks with no read get number=None."""
    try:
        import easyocr
    except ImportError:
        return {}

    reader = easyocr.Reader(["en"], gpu=False, verbose=False)

    by_track: dict[int, list[Detection]] = defaultdict(list)
    for d in detections:
        if d.cls != "player":
            continue
        by_track[d.track_id].append(d)

    out: dict[int, JerseyReading] = {}
    for tid, group in by_track.items():
        # Spread samples across the track and prefer mid-resolution frames
        # (largest bbox tends to mean the player is closer to the camera).
        group_sorted = sorted(
            group, key=lambda d: (d.x2 - d.x1) * (d.y2 - d.y1), reverse=True
        )[: samples_per_track * 2]
        if len(group_sorted) > samples_per_track:
            step = len(group_sorted) // samples_per_track
            sample = group_sorted[::step][:samples_per_track]
        else:
            sample = group_sorted

        votes: dict[str, float] = defaultdict(float)
        supporting: dict[str, int] = defaultdict(int)
        for d in sample:
            try:
                frame = frame_lookup(d.frame)
            except Exception:
                continue
            crop = _torso_crop(frame, (d.x1, d.y1, d.x2, d.y2))
            if crop is None:
                continue
            try:
                results = reader.readtext(crop, allowlist="0123456789", detail=1)
            except Exception:
                continue
            for _bbox, text, conf in results:
                cleaned = text.strip()
                if not JERSEY_RE.match(cleaned):
                    continue
                n = int(cleaned)
                if n < 0 or n > 99:
                    continue
                if conf < min_confidence:
                    continue
                votes[cleaned] += float(conf)
                supporting[cleaned] += 1

        if not votes:
            out[tid] = JerseyReading(tid, None, 0.0, 0)
            continue

        winner, score = max(votes.items(), key=lambda kv: kv[1])
        out[tid] = JerseyReading(
            track_id=tid,
            number=winner,
            confidence=score / max(1, sum(supporting.values())),
            n_supporting_frames=supporting[winner],
        )
    return out


def jersey_display_names(
    track_ids: list[int],
    readings: dict[int, JerseyReading],
    teams: dict[int, int] | None = None,
) -> dict[int, str]:
    """Map track_ids to display names like 'Team A #7' or 'Player #4'.

    Disambiguates duplicate jersey numbers by appending a suffix.
    """
    teams = teams or {}
    used: dict[tuple[int | None, str], int] = defaultdict(int)
    names: dict[int, str] = {}
    for tid in track_ids:
        r = readings.get(tid)
        team = teams.get(tid)
        team_label = "?" if team is None else chr(ord("A") + team)
        if r and r.number:
            key = (team, r.number)
            used[key] += 1
            suffix = "" if used[key] == 1 else f" ({used[key]})"
            names[tid] = f"Team {team_label} #{r.number}{suffix}"
        else:
            names[tid] = f"Team {team_label} · Player #{tid}"
    return names
