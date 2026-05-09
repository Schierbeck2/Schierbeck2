"""Shooting-form pose analysis using MediaPipe Pose.

For each shot event we crop the shooter at the release frame, run pose, and
compute a few simple form metrics:

  - elbow_angle: angle at the shooting elbow (proxy for arm bend)
  - knee_angle: angle at the front knee (proxy for leg drive)
  - release_height_ratio: wrist y relative to head y (higher = better)
  - balance_offset_px: horizontal offset of head over hips (smaller = better)

These are descriptive, not prescriptive. The LLM coach turns them into notes.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Callable, Optional

import numpy as np


@dataclass
class FormMetrics:
    track_id: Optional[int]
    frame: int
    elbow_angle_deg: Optional[float]
    knee_angle_deg: Optional[float]
    release_height_ratio: Optional[float]
    balance_offset_px: Optional[float]

    def to_dict(self) -> dict:
        return asdict(self)


def _angle(a: np.ndarray, b: np.ndarray, c: np.ndarray) -> float:
    """Angle at b formed by a-b-c, in degrees."""
    ba = a - b
    bc = c - b
    cos = float(np.dot(ba, bc) / (np.linalg.norm(ba) * np.linalg.norm(bc) + 1e-9))
    cos = max(-1.0, min(1.0, cos))
    return float(np.degrees(np.arccos(cos)))


def analyze_shooter_form(
    frame_lookup: Callable[[int], np.ndarray],
    shooter_bbox: tuple[float, float, float, float],
    frame_index: int,
    track_id: Optional[int],
) -> Optional[FormMetrics]:
    """Run MediaPipe Pose on the cropped shooter and return form metrics."""
    try:
        import mediapipe as mp
    except ImportError:
        return None

    try:
        frame = frame_lookup(frame_index)
    except Exception:
        return None
    h, w = frame.shape[:2]
    x1, y1, x2, y2 = (int(max(0, v)) for v in shooter_bbox)
    x2 = min(w, x2); y2 = min(h, y2)
    if x2 <= x1 or y2 <= y1:
        return None
    crop = frame[y1:y2, x1:x2]

    mp_pose = mp.solutions.pose
    with mp_pose.Pose(
        static_image_mode=True, model_complexity=1, enable_segmentation=False
    ) as pose:
        # MediaPipe wants RGB.
        import cv2

        results = pose.process(cv2.cvtColor(crop, cv2.COLOR_BGR2RGB))
    if not results.pose_landmarks:
        return FormMetrics(track_id, frame_index, None, None, None, None)

    lm = results.pose_landmarks.landmark

    # Convert to absolute pixels in the crop.
    def pt(idx: int) -> np.ndarray:
        p = lm[idx]
        return np.array([p.x * (x2 - x1), p.y * (y2 - y1)])

    # MediaPipe indices (subset).
    R_SHOULDER, R_ELBOW, R_WRIST = 12, 14, 16
    L_SHOULDER, L_ELBOW, L_WRIST = 11, 13, 15
    R_HIP, R_KNEE, R_ANKLE = 24, 26, 28
    L_HIP, L_KNEE, L_ANKLE = 23, 25, 27
    NOSE = 0

    # Pick the dominant arm = whichever wrist is highest (smallest y) at release.
    if pt(R_WRIST)[1] < pt(L_WRIST)[1]:
        s, e, w_pt = pt(R_SHOULDER), pt(R_ELBOW), pt(R_WRIST)
    else:
        s, e, w_pt = pt(L_SHOULDER), pt(L_ELBOW), pt(L_WRIST)
    elbow_angle = _angle(s, e, w_pt)

    # Front knee = lower knee in y (closer to the ground).
    rk_pt, lk_pt = pt(R_KNEE), pt(L_KNEE)
    if rk_pt[1] > lk_pt[1]:
        h_pt, k_pt, a_pt = pt(R_HIP), rk_pt, pt(R_ANKLE)
    else:
        h_pt, k_pt, a_pt = pt(L_HIP), lk_pt, pt(L_ANKLE)
    knee_angle = _angle(h_pt, k_pt, a_pt)

    head_y = pt(NOSE)[1]
    wrist_y = w_pt[1]
    body_h = (pt(L_ANKLE)[1] + pt(R_ANKLE)[1]) / 2.0 - head_y
    release_height_ratio = (
        float((head_y - wrist_y) / body_h) if body_h > 1 else None
    )

    hips_x = (pt(L_HIP)[0] + pt(R_HIP)[0]) / 2.0
    head_x = pt(NOSE)[0]
    balance_offset_px = float(abs(head_x - hips_x))

    return FormMetrics(
        track_id=track_id,
        frame=frame_index,
        elbow_angle_deg=elbow_angle,
        knee_angle_deg=knee_angle,
        release_height_ratio=release_height_ratio,
        balance_offset_px=balance_offset_px,
    )
