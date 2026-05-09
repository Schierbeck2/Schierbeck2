"""Top-level orchestration: run the full pipeline on a video."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable, Optional

from . import coach as coach_mod
from . import events as events_mod
from . import pose as pose_mod
from . import stats as stats_mod
from . import tracker as tracker_mod
from .clips import cut_highlights
from .config import OUTPUT_DIR
from .court import CourtCalibration
from .video import probe, read_frame


@dataclass
class AnalysisResult:
    video_path: str
    fps: float
    duration_s: float
    detections: list[dict]
    teams: dict[int, int]
    shot_events: list[dict]
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


def run(
    video_path: str | Path,
    calibration: Optional[CourtCalibration],
    name_overrides: Optional[dict[int, str]] = None,
    on_status: Callable[[str, float], None] | None = None,
) -> AnalysisResult:
    """Run the whole pipeline.

    `on_status(message, progress01)` is called with a status string and a
    rough progress in [0, 1].
    """
    def status(msg: str, p: float) -> None:
        if on_status:
            on_status(msg, p)

    info = probe(video_path)

    status("Detecting and tracking players + ball...", 0.02)
    detections = tracker_mod.run_tracking(
        video_path,
        on_progress=lambda p: status("Tracking video...", 0.02 + 0.55 * p),
    )

    status("Estimating teams from jersey colors...", 0.6)
    teams = tracker_mod.assign_teams_by_jersey_color(
        detections, frames_lookup=lambda i: read_frame(video_path, i)
    )

    status("Detecting shot attempts...", 0.66)
    shot_events = events_mod.detect_shots(
        detections, calibration, teams=teams, fps=info.fps
    )

    status("Analyzing shooting form on detected shots...", 0.75)
    form_metrics: list[pose_mod.FormMetrics] = []
    players_only = [d for d in detections if d.cls == "player"]
    by_id_frame = {(d.track_id, d.frame): d for d in players_only}
    for s in shot_events:
        if s.shooter_track_id is None:
            continue
        d = by_id_frame.get((s.shooter_track_id, s.start_frame))
        if d is None:
            continue
        fm = pose_mod.analyze_shooter_form(
            frame_lookup=lambda i: read_frame(video_path, i),
            shooter_bbox=(d.x1, d.y1, d.x2, d.y2),
            frame_index=s.start_frame,
            track_id=s.shooter_track_id,
        )
        if fm is not None:
            form_metrics.append(fm)

    status("Aggregating stats...", 0.83)
    player_stats, team_stats = stats_mod.aggregate(
        detections, shot_events, teams, fps=info.fps,
        name_overrides=name_overrides,
    )

    status("Cutting highlight clips...", 0.88)
    clips = cut_highlights(video_path, shot_events)

    status("Generating coaching notes...", 0.93)
    sample_frames = []
    for s in shot_events[:6]:
        try:
            sample_frames.append(read_frame(video_path, s.start_frame))
        except Exception:
            continue
    coach_out = coach_mod.generate_report(
        team_stats=[ts.to_dict() for ts in team_stats.values()],
        player_stats=[ps.to_dict() for ps in player_stats.values()],
        shot_events=[s.to_dict() for s in shot_events],
        form_metrics=[fm.to_dict() for fm in form_metrics],
        sample_frames_bgr=sample_frames,
    )

    status("Done.", 1.0)

    result = AnalysisResult(
        video_path=str(video_path),
        fps=info.fps,
        duration_s=info.duration_s,
        detections=tracker_mod.to_dicts(detections),
        teams={int(k): int(v) for k, v in teams.items()},
        shot_events=[s.to_dict() for s in shot_events],
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
    out_path = OUTPUT_DIR / (Path(video_path).stem + ".analysis.json")
    result.save(out_path)
    return result
