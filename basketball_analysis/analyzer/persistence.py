"""On-disk persistence for analysis sessions.

Each session lives in `data/cache/<video-stem>/` and contains:

  - `heavy.pkl`        — pickled HeavyCache (detections, OCR readings,
                         pose-form metrics, auto team clustering).
  - `calibration.pkl`  — pickled court + basket calibration plus the raw
                         pixel coordinates the user typed.
  - `result.json`      — JSON of the most recent AnalysisResult.
  - `session.json`     — small metadata blob (timestamp, counts) used by
                         the session list so we don't have to unpickle the
                         heavy cache to render the UI.

Pickle is only used for objects we wrote ourselves (numpy arrays inside
the homography, our dataclasses). We never load pickles from outside the
cache directory.
"""

from __future__ import annotations

import json
import pickle
import shutil
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any, Optional

from .config import CACHE_DIR


SESSION_VERSION = 1
HEAVY_PKL = "heavy.pkl"
CALIB_PKL = "calibration.pkl"
META_JSON = "session.json"
RESULT_JSON = "result.json"


def session_dir(video_path: str | Path) -> Path:
    name = Path(video_path).stem
    d = CACHE_DIR / name
    d.mkdir(parents=True, exist_ok=True)
    return d


def session_dir_by_name(name: str) -> Path:
    return CACHE_DIR / name


def has_session(video_path: str | Path) -> bool:
    d = session_dir(video_path)
    return (d / HEAVY_PKL).exists() and (d / META_JSON).exists()


def save_session(
    *,
    video_path: str | Path,
    heavy_cache,
    court_calibration,
    basket_calibration,
    calibration_points,
    rim_points,
    result,
) -> Path:
    d = session_dir(video_path)

    with (d / HEAVY_PKL).open("wb") as f:
        pickle.dump(heavy_cache, f, protocol=pickle.HIGHEST_PROTOCOL)

    with (d / CALIB_PKL).open("wb") as f:
        pickle.dump(
            {
                "court": court_calibration,
                "basket": basket_calibration,
                "calibration_points": calibration_points,
                "rim_points": rim_points,
            },
            f,
            protocol=pickle.HIGHEST_PROTOCOL,
        )

    if result is not None:
        with (d / RESULT_JSON).open("w") as f:
            json.dump(asdict(result), f, indent=2, default=str)

    meta: dict[str, Any] = {
        "version": SESSION_VERSION,
        "video_path": str(video_path),
        "saved_at": time.time(),
        "n_shots": len(getattr(result, "shot_events", [])) if result else 0,
        "n_possessions": len(getattr(result, "possessions", [])) if result else 0,
        "n_rebounds": len(getattr(result, "rebounds", [])) if result else 0,
        "duration_s": getattr(result, "duration_s", None) if result else None,
    }
    with (d / META_JSON).open("w") as f:
        json.dump(meta, f, indent=2, default=str)
    return d


def load_session(name: str) -> dict:
    """Restore a session by name. Returns a dict ready to push into session
    state. Caller is responsible for placing the values onto its UI state."""
    d = session_dir_by_name(name)
    if not (d / HEAVY_PKL).exists():
        raise FileNotFoundError(f"No heavy cache for session {name!r}")

    with (d / HEAVY_PKL).open("rb") as f:
        heavy_cache = pickle.load(f)

    calib_path = d / CALIB_PKL
    calib_blob: dict[str, Any] = {}
    if calib_path.exists():
        with calib_path.open("rb") as f:
            calib_blob = pickle.load(f) or {}

    meta: dict[str, Any] = {}
    if (d / META_JSON).exists():
        with (d / META_JSON).open() as f:
            meta = json.load(f)

    result = None
    result_path = d / RESULT_JSON
    if result_path.exists():
        with result_path.open() as f:
            result_dict = json.load(f)
        result = _hydrate_result(result_dict)

    return {
        "name": name,
        "heavy_cache": heavy_cache,
        "court_calibration": calib_blob.get("court"),
        "basket_calibration": calib_blob.get("basket"),
        "calibration_points": calib_blob.get("calibration_points") or [],
        "rim_points": calib_blob.get("rim_points") or [(0, 0), (0, 0)],
        "result": result,
        "meta": meta,
    }


def _hydrate_result(d: dict):
    """JSON-loaded keys are strings; AnalysisResult uses int keys."""
    from .report import AnalysisResult

    def to_int_keys(m):
        if not isinstance(m, dict):
            return m
        return {int(k): v for k, v in m.items()}

    return AnalysisResult(
        video_path=d["video_path"],
        fps=d["fps"],
        duration_s=d["duration_s"],
        detections=d.get("detections", []),
        teams=to_int_keys(d.get("teams", {})),
        jersey_numbers=to_int_keys(d.get("jersey_numbers", {})),
        shot_events=d.get("shot_events", []),
        possessions=d.get("possessions", []),
        rebounds=d.get("rebounds", []),
        form_metrics=d.get("form_metrics", []),
        player_stats=to_int_keys(d.get("player_stats", {})),
        team_stats=to_int_keys(d.get("team_stats", {})),
        clips=d.get("clips", []),
        coach=d.get("coach", {}),
    )


def list_sessions() -> list[dict]:
    """Return metadata for every saved session, newest first."""
    out: list[dict] = []
    if not CACHE_DIR.exists():
        return out
    for child in CACHE_DIR.iterdir():
        if not child.is_dir():
            continue
        meta_path = child / META_JSON
        if not meta_path.exists():
            continue
        try:
            with meta_path.open() as f:
                meta = json.load(f)
        except Exception:
            continue
        meta["name"] = child.name
        meta["dir"] = str(child)
        meta["video_exists"] = Path(meta.get("video_path", "")).exists()
        out.append(meta)
    return sorted(out, key=lambda m: m.get("saved_at", 0), reverse=True)


def delete_session(name: str) -> None:
    d = session_dir_by_name(name)
    if d.is_dir():
        shutil.rmtree(d)
