"""Top-level orchestration: run the full pipeline on a video.

The pipeline is split into two phases:

  1. **Heavy** (`run_heavy`): YOLO tracking, team-color clustering, jersey
     OCR, MediaPipe pose. These are expensive. Their outputs are bundled in
     a `HeavyCache` so the user can edit overrides afterward and re-run the
     cheap analytics without redoing the slow CV work.
  2. **Light** (`recompute`): shot detection, possessions, rebounds, stats,
     clip cutting, coach call. Takes the `HeavyCache` plus optional manual
     overrides for jersey numbers and team assignments and a basket
     calibration, and produces the final `AnalysisResult`.

`run` calls both in sequence for the first analysis pass.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Callable, Optional

from . import coach as coach_mod
from . import events as events_mod
from . import jersey as jersey_mod
from . import pose as pose_mod
from . import possession as possession_mod
from . import stats as stats_mod
from . import tracker as tracker_mod
from .clips import cut_highlights
from .config import OUTPUT_DIR
from .court import BasketCalibration, CourtCalibration
from .video import probe, read_frame


@dataclass
class HeavyCache:
    """Outputs of the expensive CV phase, suitable for re-running analytics
    after manual overrides."""

    video_path: str
    fps: float
    duration_s: float
    detections: list[tracker_mod.Detection]
    auto_teams: dict[int, int]
    jersey_readings: dict[int, jersey_mod.JerseyReading]
    form_metrics_by_shot_start: dict[int, pose_mod.FormMetrics] = field(
        default_factory=dict
    )


@dataclass
class AnalysisResult:
    video_path: str
    fps: float
    duration_s: float
    detections: list[dict]
    teams: dict[int, int]
    jersey_numbers: dict[int, dict]
    shot_events: list[dict]
    possessions: list[dict]
    rebounds: list[dict]
    form_metrics: list[dict]
    player_stats: dict[int, dict]
    team_stats: dict[int, dict]
    clips: list[dict]
    coach: dict

    def save(self, path: Path) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w") as f:
            json.dump(asdict(self), f, indent=2, default=str)
        return path


def run_heavy(
    video_path: str | Path,
    on_status: Callable[[str, float], None] | None = None,
) -> HeavyCache:
    """Run YOLO tracking, jersey OCR, and form-pose for shooter releases."""
    def status(msg: str, p: float) -> None:
        if on_status:
            on_status(msg, p)

    info = probe(video_path)
    frame_lookup = lambda i: read_frame(video_path, i)

    status("Detecting and tracking players + ball...", 0.02)
    detections = tracker_mod.run_tracking(
        video_path,
        on_progress=lambda p: status("Tracking video...", 0.02 + 0.55 * p),
    )

    status("Estimating teams from jersey colors...", 0.6)
    teams = tracker_mod.assign_teams_by_jersey_color(
        detections, frames_lookup=frame_lookup
    )

    status("Reading jersey numbers...", 0.7)
    jersey_readings = jersey_mod.read_jersey_numbers(detections, frame_lookup)

    # Pre-compute form metrics for the shooter at the release frame of every
    # candidate shot. We use a no-calibration first pass for shot detection
    # purely to find candidate (shooter, frame) pairs; the real shot list is
    # produced during the light phase, but the (shooter, frame)→FormMetrics
    # cache covers any superset because shot apexes are stable.
    status("Analyzing shooting form on candidate releases...", 0.85)
    candidate_shots = events_mod.detect_shots(
        detections, calib=None, teams=teams, fps=info.fps,
    )
    players_only = [d for d in detections if d.cls == "player"]
    by_id_frame = {(d.track_id, d.frame): d for d in players_only}
    form_cache: dict[int, pose_mod.FormMetrics] = {}
    for s in candidate_shots:
        if s.shooter_track_id is None:
            continue
        d = by_id_frame.get((s.shooter_track_id, s.start_frame))
        if d is None:
            continue
        fm = pose_mod.analyze_shooter_form(
            frame_lookup=frame_lookup,
            shooter_bbox=(d.x1, d.y1, d.x2, d.y2),
            frame_index=s.start_frame,
            track_id=s.shooter_track_id,
        )
        if fm is not None:
            form_cache[s.start_frame] = fm

    return HeavyCache(
        video_path=str(video_path),
        fps=info.fps,
        duration_s=info.duration_s,
        detections=detections,
        auto_teams=teams,
        jersey_readings=jersey_readings,
        form_metrics_by_shot_start=form_cache,
    )


def recompute(
    cache: HeavyCache,
    court_calibration: Optional[CourtCalibration],
    basket_calibration: Optional[BasketCalibration],
    *,
    team_overrides: Optional[dict[int, int]] = None,
    jersey_overrides: Optional[dict[int, str | None]] = None,
    name_overrides: Optional[dict[int, str]] = None,
    on_status: Callable[[str, float], None] | None = None,
    skip_coach: bool = False,
    skip_clips: bool = False,
) -> AnalysisResult:
    """Re-run all the cheap analytics on top of a cached heavy pass.

    `team_overrides` maps track_id → team_index, replacing the auto-cluster.
    `jersey_overrides` maps track_id → number string (or None to clear).
    `name_overrides` maps track_id → display name to use verbatim.
    """
    def status(msg: str, p: float) -> None:
        if on_status:
            on_status(msg, p)

    teams = dict(cache.auto_teams)
    if team_overrides:
        teams.update(team_overrides)

    jersey_numbers: dict[int, str | None] = {
        tid: r.number for tid, r in cache.jersey_readings.items()
    }
    if jersey_overrides:
        for tid, number in jersey_overrides.items():
            jersey_numbers[tid] = number  # may be None to clear

    track_ids = tracker_mod.player_track_ids(cache.detections)
    auto_names = jersey_mod.jersey_display_names(
        track_ids,
        {
            tid: jersey_mod.JerseyReading(
                track_id=tid,
                number=jersey_numbers.get(tid),
                confidence=0.0,
                n_supporting_frames=0,
            )
            for tid in track_ids
        },
        teams,
    )
    merged_names: dict[int, str] = dict(auto_names)
    if name_overrides:
        merged_names.update(name_overrides)

    status("Detecting shot attempts...", 0.1)
    shot_events = events_mod.detect_shots(
        cache.detections,
        court_calibration,
        teams=teams,
        fps=cache.fps,
        basket_calib=basket_calibration,
    )

    status("Computing possessions...", 0.3)
    owners = possession_mod.per_frame_owner(cache.detections)
    ball_xy = possession_mod.ball_xy_per_frame(cache.detections)
    possessions = possession_mod.compute_possessions(
        owners,
        teams,
        fps=cache.fps,
        basket_calib=basket_calibration,
        ball_xy=ball_xy,
    )

    status("Detecting rebounds...", 0.45)
    rebounds = possession_mod.detect_rebounds(shot_events, possessions, teams)

    status("Looking up shooting-form metrics...", 0.55)
    form_metrics: list[pose_mod.FormMetrics] = []
    for s in shot_events:
        fm = cache.form_metrics_by_shot_start.get(s.start_frame)
        if fm is not None:
            form_metrics.append(fm)

    status("Aggregating stats...", 0.65)
    player_stats, team_stats = stats_mod.aggregate(
        cache.detections, shot_events, teams, fps=cache.fps,
        name_overrides=merged_names,
        jersey_numbers=jersey_numbers,
        possessions=possessions,
        rebounds=rebounds,
    )

    if skip_clips:
        status("Skipping highlight clips.", 0.75)
        clips: list[dict] = []
    else:
        status("Cutting highlight clips...", 0.75)
        clips = cut_highlights(cache.video_path, shot_events)

    if skip_coach:
        status("Skipping coach narrative.", 0.9)
        coach_out = coach_mod.CoachOutput(
            team_summary="(coach narrative skipped)",
            team_strengths=[],
            team_areas_to_improve=[],
            per_player={},
            raw="",
        )
    else:
        status("Generating coaching notes...", 0.9)
        sample_frames = []
        for s in shot_events[:6]:
            try:
                sample_frames.append(read_frame(cache.video_path, s.start_frame))
            except Exception:
                continue
        coach_out = coach_mod.generate_report(
            team_stats=[ts.to_dict() for ts in team_stats.values()],
            player_stats=[ps.to_dict() for ps in player_stats.values()],
            shot_events=[s.to_dict() for s in shot_events],
            form_metrics=[fm.to_dict() for fm in form_metrics],
            possessions=[p.to_dict() for p in possessions],
            rebounds=[r.to_dict() for r in rebounds],
            sample_frames_bgr=sample_frames,
        )

    status("Done.", 1.0)

    result = AnalysisResult(
        video_path=str(cache.video_path),
        fps=cache.fps,
        duration_s=cache.duration_s,
        detections=tracker_mod.to_dicts(cache.detections),
        teams={int(k): int(v) for k, v in teams.items()},
        jersey_numbers={
            int(tid): {
                "number": r.number,
                "confidence": r.confidence,
                "n_supporting_frames": r.n_supporting_frames,
            }
            for tid, r in cache.jersey_readings.items()
        },
        shot_events=[s.to_dict() for s in shot_events],
        possessions=[p.to_dict() for p in possessions],
        rebounds=[r.to_dict() for r in rebounds],
        form_metrics=[fm.to_dict() for fm in form_metrics],
        player_stats={int(tid): ps.to_dict() for tid, ps in player_stats.items()},
        team_stats={int(t): ts.to_dict() for t, ts in team_stats.items()},
        clips=clips,
        coach={
            "team_summary": coach_out.team_summary,
            "team_strengths": coach_out.team_strengths,
            "team_areas_to_improve": coach_out.team_areas_to_improve,
            "per_player": coach_out.per_player,
            "raw": coach_out.raw,
        },
    )
    out_path = OUTPUT_DIR / (Path(cache.video_path).stem + ".analysis.json")
    result.save(out_path)
    return result


def run(
    video_path: str | Path,
    calibration: Optional[CourtCalibration],
    basket_calibration: Optional[BasketCalibration] = None,
    name_overrides: Optional[dict[int, str]] = None,
    on_status: Callable[[str, float], None] | None = None,
) -> tuple[HeavyCache, AnalysisResult]:
    """End-to-end: heavy phase + light phase. Returns both so the caller can
    cache the heavy outputs for later re-runs."""

    def status_heavy(msg: str, p: float) -> None:
        if on_status:
            on_status(msg, p * 0.85)

    def status_light(msg: str, p: float) -> None:
        if on_status:
            on_status(msg, 0.85 + p * 0.15)

    cache = run_heavy(video_path, on_status=status_heavy)
    result = recompute(
        cache,
        court_calibration=calibration,
        basket_calibration=basket_calibration,
        name_overrides=name_overrides,
        on_status=status_light,
    )
    return cache, result
