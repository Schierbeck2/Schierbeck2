"""Frame-level ball possession + rebound detection.

Possession heuristic
--------------------
For each frame where both the ball and at least one player are detected,
the ball "belongs to" the closest player whose expanded bounding box
contains the ball center, using image-space distance to break ties.
Frames with no nearby player are flagged "in flight" (typical during a
shot) and contribute to the previous owner if the ball returns to them
quickly.

Possession runs are coalesced into `Possession` blocks. A change of team
between consecutive blocks is a turnover-or-rebound; we let the rebound
detector sort that out by aligning to detected shots.

Rebound heuristic
-----------------
For each shot event that we believe was a miss:
  - find the next possession that begins after the shot's end frame,
  - if that possession's owner is on the *shooting* team -> offensive
    rebound, otherwise -> defensive rebound.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Optional

import numpy as np

from .events import ShotEvent
from .tracker import Detection, detections_by_frame, split_by_class


@dataclass
class Possession:
    start_frame: int
    end_frame: int
    t_start: float
    t_end: float
    track_id: Optional[int]
    team: Optional[int]
    n_frames: int

    @property
    def duration_s(self) -> float:
        return self.t_end - self.t_start

    def to_dict(self) -> dict:
        d = asdict(self)
        d["duration_s"] = self.duration_s
        return d


@dataclass
class Rebound:
    shot_index: int
    frame: int
    t_seconds: float
    rebounder_track_id: Optional[int]
    rebounder_team: Optional[int]
    kind: str  # "offensive" | "defensive" | "unknown"

    def to_dict(self) -> dict:
        return asdict(self)


def _expanded_contains(d: Detection, x: float, y: float, pad: float = 0.3) -> bool:
    w = d.x2 - d.x1
    h = d.y2 - d.y1
    return (
        d.x1 - pad * w <= x <= d.x2 + pad * w
        and d.y1 - pad * h <= y <= d.y2 + pad * h
    )


def _distance(d: Detection, x: float, y: float) -> float:
    return float(np.hypot(d.cx - x, d.cy - y))


def per_frame_owner(
    detections: list[Detection],
) -> dict[int, Optional[int]]:
    """Return {frame: track_id_of_ball_owner_or_None}."""
    by_frame = detections_by_frame(detections)
    owners: dict[int, Optional[int]] = {}
    for frame, dets in by_frame.items():
        balls = [d for d in dets if d.cls == "ball"]
        players = [d for d in dets if d.cls == "player"]
        if not balls or not players:
            owners[frame] = None
            continue
        ball = max(balls, key=lambda b: b.conf)
        candidates = [p for p in players if _expanded_contains(p, ball.cx, ball.cy)]
        if not candidates:
            owners[frame] = None
            continue
        owner = min(candidates, key=lambda p: _distance(p, ball.cx, ball.cy))
        owners[frame] = owner.track_id
    return owners


def compute_possessions(
    owner_per_frame: dict[int, Optional[int]],
    teams: dict[int, int],
    fps: float,
    min_run_frames: int = 4,
    bridge_gap_frames: int = 6,
) -> list[Possession]:
    """Coalesce per-frame ownership into Possession blocks.

    `min_run_frames` filters jitter; `bridge_gap_frames` lets short None
    stretches (e.g. a dribble where the ball detection drops) keep the
    same owner instead of cutting the possession.
    """
    if not owner_per_frame:
        return []
    frames = sorted(owner_per_frame.keys())
    runs: list[tuple[int, int, Optional[int]]] = []  # (start, end, owner)
    cur_owner: Optional[int] = None
    cur_start: int = frames[0]
    last_seen_owner_frame = frames[0]
    for f in frames:
        owner = owner_per_frame[f]
        if owner == cur_owner:
            if owner is not None:
                last_seen_owner_frame = f
            continue
        # Bridge short Nones: if owner is None but we expect to come back...
        if owner is None and cur_owner is not None and f - last_seen_owner_frame <= bridge_gap_frames:
            continue
        # Switching: close the previous run.
        runs.append((cur_start, f - 1, cur_owner))
        cur_owner = owner
        cur_start = f
        if owner is not None:
            last_seen_owner_frame = f
    runs.append((cur_start, frames[-1], cur_owner))

    out: list[Possession] = []
    for start, end, owner in runs:
        if owner is None:
            continue
        if (end - start + 1) < min_run_frames:
            continue
        out.append(
            Possession(
                start_frame=start,
                end_frame=end,
                t_start=start / fps if fps else 0.0,
                t_end=end / fps if fps else 0.0,
                track_id=owner,
                team=teams.get(owner),
                n_frames=end - start + 1,
            )
        )
    return out


def detect_rebounds(
    shots: list[ShotEvent],
    possessions: list[Possession],
    teams: dict[int, int],
) -> list[Rebound]:
    rebounds: list[Rebound] = []
    for i, s in enumerate(shots):
        if s.made:
            continue  # made baskets don't generate a rebound
        # First possession that starts after the shot's end frame.
        nxt = next((p for p in possessions if p.start_frame > s.end_frame), None)
        if nxt is None:
            continue
        kind = "unknown"
        if s.shooter_team is not None and nxt.team is not None:
            kind = "offensive" if nxt.team == s.shooter_team else "defensive"
        rebounds.append(
            Rebound(
                shot_index=i,
                frame=nxt.start_frame,
                t_seconds=nxt.t_start,
                rebounder_track_id=nxt.track_id,
                rebounder_team=nxt.team,
                kind=kind,
            )
        )
    return rebounds
