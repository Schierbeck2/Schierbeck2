"""Player and ball detection + multi-object tracking.

We use Ultralytics YOLOv8 with its built-in ByteTrack tracker. From the COCO
classes we keep two: `person` (class 0, players + refs) and `sports ball`
(class 32). Refs are filtered out later by team color clustering.

Output is a flat list of `Detection` rows, one per (frame, track_id).
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Callable, Iterable

import numpy as np

from .config import SETTINGS
from .video import probe


PERSON_CLS = 0
BALL_CLS = 32


@dataclass
class Detection:
    frame: int
    t_seconds: float
    track_id: int
    cls: str  # "player" or "ball"
    x1: float
    y1: float
    x2: float
    y2: float
    conf: float

    @property
    def cx(self) -> float:
        return (self.x1 + self.x2) / 2.0

    @property
    def cy(self) -> float:
        return (self.y1 + self.y2) / 2.0

    @property
    def foot_x(self) -> float:
        return self.cx

    @property
    def foot_y(self) -> float:
        # bottom of bbox is roughly where the player stands
        return self.y2


def run_tracking(
    video_path: str | Path,
    on_progress: Callable[[float], None] | None = None,
) -> list[Detection]:
    """Run detection + tracking across the whole video.

    `on_progress` is called with a value in [0,1] periodically.
    """
    # Imported lazily so the rest of the app can be imported without these
    # heavy deps installed.
    from ultralytics import YOLO

    info = probe(video_path)
    model = YOLO(SETTINGS.yolo_model)

    results: Iterable = model.track(
        source=str(video_path),
        stream=True,
        tracker="bytetrack.yaml",
        classes=[PERSON_CLS, BALL_CLS],
        persist=True,
        verbose=False,
        device=SETTINGS.device,
        vid_stride=SETTINGS.frame_stride,
    )

    detections: list[Detection] = []
    last_progress = 0.0
    stride = max(1, SETTINGS.frame_stride)
    frame_idx = -stride
    for r in results:
        frame_idx += stride
        t = frame_idx / info.fps if info.fps else 0.0
        if r.boxes is None or r.boxes.id is None:
            continue
        ids = r.boxes.id.cpu().numpy().astype(int)
        cls_arr = r.boxes.cls.cpu().numpy().astype(int)
        conf_arr = r.boxes.conf.cpu().numpy()
        xyxy = r.boxes.xyxy.cpu().numpy()
        for tid, c, conf, box in zip(ids, cls_arr, conf_arr, xyxy):
            label = "ball" if c == BALL_CLS else "player"
            x1, y1, x2, y2 = (float(v) for v in box)
            detections.append(
                Detection(
                    frame=frame_idx,
                    t_seconds=float(t),
                    track_id=int(tid),
                    cls=label,
                    x1=x1, y1=y1, x2=x2, y2=y2,
                    conf=float(conf),
                )
            )
        if on_progress and info.n_frames:
            p = min(1.0, frame_idx / info.n_frames)
            if p - last_progress > 0.01:
                on_progress(p)
                last_progress = p

    return _drop_short_tracks(detections, SETTINGS.min_track_len)


def _drop_short_tracks(dets: list[Detection], min_len: int) -> list[Detection]:
    counts: dict[tuple[str, int], int] = {}
    for d in dets:
        counts[(d.cls, d.track_id)] = counts.get((d.cls, d.track_id), 0) + 1
    return [d for d in dets if counts[(d.cls, d.track_id)] >= min_len]


def to_dicts(dets: list[Detection]) -> list[dict]:
    return [asdict(d) for d in dets]


def detections_by_frame(
    dets: list[Detection],
) -> dict[int, list[Detection]]:
    out: dict[int, list[Detection]] = {}
    for d in dets:
        out.setdefault(d.frame, []).append(d)
    return out


def split_by_class(
    dets: list[Detection],
) -> tuple[list[Detection], list[Detection]]:
    players = [d for d in dets if d.cls == "player"]
    balls = [d for d in dets if d.cls == "ball"]
    return players, balls


def player_track_ids(dets: list[Detection]) -> list[int]:
    return sorted({d.track_id for d in dets if d.cls == "player"})


def assign_teams_by_jersey_color(
    dets: list[Detection],
    frames_lookup: Callable[[int], np.ndarray],
    sample_per_track: int = 6,
) -> dict[int, int]:
    """Cluster player tracks into 2 teams by mean jersey color.

    For each player track we sample up to `sample_per_track` boxes, take the
    middle third of the box (torso area), average HSV, then run a tiny k-means
    with k=2. Returns {track_id: team_index in {0, 1}}.

    Refs and outliers may slip in; this is best-effort, suitable for an MVP.
    """
    import cv2

    by_track: dict[int, list[Detection]] = {}
    for d in dets:
        if d.cls != "player":
            continue
        by_track.setdefault(d.track_id, []).append(d)

    feats: dict[int, np.ndarray] = {}
    for tid, group in by_track.items():
        # Spread the samples across the track.
        if len(group) > sample_per_track:
            step = len(group) // sample_per_track
            sample = group[::step][:sample_per_track]
        else:
            sample = group
        colors = []
        for d in sample:
            try:
                frame = frames_lookup(d.frame)
            except Exception:
                continue
            x1, y1, x2, y2 = (int(max(0, v)) for v in (d.x1, d.y1, d.x2, d.y2))
            if x2 <= x1 or y2 <= y1:
                continue
            crop = frame[y1:y2, x1:x2]
            if crop.size == 0:
                continue
            h = crop.shape[0]
            torso = crop[h // 4 : h * 2 // 3]
            if torso.size == 0:
                continue
            hsv = cv2.cvtColor(torso, cv2.COLOR_BGR2HSV)
            colors.append(hsv.reshape(-1, 3).mean(axis=0))
        if colors:
            feats[tid] = np.mean(np.stack(colors, axis=0), axis=0)

    if len(feats) < 2:
        return {tid: 0 for tid in feats}

    X = np.stack(list(feats.values()), axis=0).astype(np.float32)
    # OpenCV k-means; deterministic-ish via fixed seed via attempts.
    Z = X.copy()
    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.5)
    _, labels, _ = cv2.kmeans(Z, 2, None, criteria, 5, cv2.KMEANS_PP_CENTERS)
    labels = labels.flatten().astype(int)
    return {tid: int(lbl) for tid, lbl in zip(feats.keys(), labels)}
