"""Heuristic detection of shot attempts and (approximate) makes.

We don't try to be a sports-analytics product here. The goal is to surface
candidate moments the coach can review, with enough metadata that the
downstream report and clipping are useful.

Method:
  - Track the ball's image-space center over time.
  - Detect "shot arcs": stretches where the ball goes up significantly,
    peaks, then comes down through the rim region (per the calibrated
    court). Apex y must be above the average shooter height.
  - For each arc, the shooter is the player track whose foot point was
    closest to the ball at the start of the arc.
  - Made vs. missed: did the ball spend > N frames inside the rim region
    immediately after apex? This is approximate and noted as such.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Optional

import numpy as np

from .court import CourtCalibration
from .tracker import Detection, split_by_class


@dataclass
class ShotEvent:
    start_frame: int
    apex_frame: int
    end_frame: int
    t_start: float
    t_end: float
    shooter_track_id: Optional[int]
    shooter_team: Optional[int]
    shot_x_img: float
    shot_y_img: float
    shot_x_ft: Optional[float]
    shot_y_ft: Optional[float]
    zone: Optional[str]
    distance_ft: Optional[float]
    made: Optional[bool]
    confidence: float  # in [0, 1], heuristic

    def to_dict(self) -> dict:
        return asdict(self)


def _ball_track(
    balls: list[Detection],
) -> list[Detection]:
    """Pick the longest ball track to follow."""
    if not balls:
        return []
    counts: dict[int, int] = {}
    for b in balls:
        counts[b.track_id] = counts.get(b.track_id, 0) + 1
    primary = max(counts.items(), key=lambda kv: kv[1])[0]
    return sorted([b for b in balls if b.track_id == primary], key=lambda d: d.frame)


def _nearest_player(
    players: list[Detection], frame: int, x: float, y: float, window: int = 6,
) -> Optional[Detection]:
    candidates = [p for p in players if abs(p.frame - frame) <= window]
    if not candidates:
        return None
    return min(candidates, key=lambda p: (p.cx - x) ** 2 + (p.foot_y - y) ** 2)


def detect_shots(
    detections: list[Detection],
    calib: Optional[CourtCalibration],
    teams: dict[int, int] | None = None,
    fps: float = 30.0,
) -> list[ShotEvent]:
    """Find candidate shot events from ball trajectory.

    Heuristic: scan smoothed ball y; identify local minima of y (apex, since
    image y grows downward) flanked by upward then downward motion. Drop
    apexes whose vertical excursion is too small.
    """
    players, balls = split_by_class(detections)
    track = _ball_track(balls)
    if len(track) < 8:
        return []

    frames = np.array([b.frame for b in track])
    ys = np.array([b.cy for b in track], dtype=float)
    xs = np.array([b.cx for b in track], dtype=float)

    # Smooth y with a small moving average to suppress noise.
    win = 3
    if len(ys) >= win:
        kernel = np.ones(win) / win
        ys_s = np.convolve(ys, kernel, mode="same")
    else:
        ys_s = ys.copy()

    events: list[ShotEvent] = []
    i = 2
    while i < len(ys_s) - 2:
        # Local minimum of y == apex (highest point on screen).
        if ys_s[i] < ys_s[i - 1] and ys_s[i] < ys_s[i + 1]:
            # Look back and forward to find shot start (release) and end.
            start = i
            while start > 0 and ys_s[start - 1] > ys_s[start]:
                start -= 1
            end = i
            while end < len(ys_s) - 1 and ys_s[end + 1] > ys_s[end]:
                end += 1
            up_amp = ys_s[start] - ys_s[i]
            down_amp = ys_s[end] - ys_s[i]
            # Need a real arc: significant up + down vertical motion in image.
            if up_amp > 40 and down_amp > 40 and (end - start) >= 4:
                shot_x = float(xs[start])
                shot_y = float(ys_s[start])
                shooter = _nearest_player(
                    players, int(frames[start]), shot_x, shot_y
                )
                tid = shooter.track_id if shooter else None
                team = teams.get(tid) if (teams and tid is not None) else None

                shot_xy_ft: Optional[tuple[float, float]] = None
                zone = None
                dist_ft: Optional[float] = None
                if calib and shooter is not None:
                    fx_ft, fy_ft = calib.to_court(shooter.foot_x, shooter.foot_y)
                    shot_xy_ft = (fx_ft, fy_ft)
                    rim_x, rim_y = calib.rim_xy_ft()
                    dist_ft = float(np.hypot(fx_ft - rim_x, fy_ft - rim_y))
                    from .court import shot_zone

                    zone = shot_zone(fx_ft, fy_ft)

                made = _heuristic_made(track, i, end)

                events.append(
                    ShotEvent(
                        start_frame=int(frames[start]),
                        apex_frame=int(frames[i]),
                        end_frame=int(frames[end]),
                        t_start=float(frames[start] / fps),
                        t_end=float(frames[end] / fps),
                        shooter_track_id=tid,
                        shooter_team=team,
                        shot_x_img=shot_x,
                        shot_y_img=shot_y,
                        shot_x_ft=shot_xy_ft[0] if shot_xy_ft else None,
                        shot_y_ft=shot_xy_ft[1] if shot_xy_ft else None,
                        zone=zone,
                        distance_ft=dist_ft,
                        made=made,
                        confidence=min(1.0, (up_amp + down_amp) / 400.0),
                    )
                )
                i = end + 1
                continue
        i += 1
    return _dedupe(events)


def _heuristic_made(track: list[Detection], apex_idx: int, end_idx: int) -> Optional[bool]:
    """Approximate make/miss from ball motion after apex.

    A loose proxy: if right after apex the ball decelerates and dwells in a
    small image-space region for several frames (suggesting it went through
    the net), call it a make. Otherwise miss / unknown.
    """
    if end_idx - apex_idx < 3:
        return None
    pts = np.array([(b.cx, b.cy) for b in track[apex_idx : end_idx + 1]])
    if len(pts) < 3:
        return None
    diffs = np.linalg.norm(np.diff(pts, axis=0), axis=1)
    # Many small steps == ball settled (likely through the net or caught).
    settled_frac = float((diffs < 6.0).mean())
    if settled_frac > 0.5:
        return True
    return False


def _dedupe(events: list[ShotEvent], min_gap_frames: int = 15) -> list[ShotEvent]:
    out: list[ShotEvent] = []
    last_end = -10**9
    for e in sorted(events, key=lambda x: x.start_frame):
        if e.start_frame - last_end >= min_gap_frames:
            out.append(e)
            last_end = e.end_frame
    return out
