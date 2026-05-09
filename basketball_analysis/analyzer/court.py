"""Map image-space points onto a half-court coordinate system.

The user clicks 4 known points on a frame; we treat those as the 4 corners of
the half court (in this order, looking at the half from sideline view):

  0: top-left corner (baseline + far sideline)
  1: top-right corner (baseline + near sideline)
  2: bottom-right corner (half-court line + near sideline)
  3: bottom-left corner (half-court line + far sideline)

We compute a homography to a fixed half-court template and use that to
project foot points (image px) onto court feet.

Half court is 50 ft wide x 47 ft long. We work in feet.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


HALF_COURT_W_FT = 50.0   # sideline to sideline
HALF_COURT_L_FT = 47.0   # baseline to half-court
RIM_FROM_BASELINE_FT = 5.25  # rim center is ~5'3" from baseline


@dataclass
class CourtCalibration:
    image_points: list[tuple[float, float]]  # 4 clicked points (px)
    H: np.ndarray  # 3x3 image -> court (feet) homography

    def to_court(self, x: float, y: float) -> tuple[float, float]:
        v = np.array([x, y, 1.0])
        w = self.H @ v
        return float(w[0] / w[2]), float(w[1] / w[2])

    def rim_xy_ft(self) -> tuple[float, float]:
        return (HALF_COURT_W_FT / 2.0, RIM_FROM_BASELINE_FT)


def calibrate(image_points: list[tuple[float, float]]) -> CourtCalibration:
    if len(image_points) != 4:
        raise ValueError("Need exactly 4 image points to calibrate the court.")
    src = np.array(image_points, dtype=np.float32)
    # Court template (feet): same ordering as image_points.
    dst = np.array(
        [
            [0.0, 0.0],                          # baseline + far sideline
            [HALF_COURT_W_FT, 0.0],              # baseline + near sideline
            [HALF_COURT_W_FT, HALF_COURT_L_FT],  # half-court + near sideline
            [0.0, HALF_COURT_L_FT],              # half-court + far sideline
        ],
        dtype=np.float32,
    )
    import cv2
    H, _ = cv2.findHomography(src, dst, method=0)
    if H is None:
        raise RuntimeError("Homography solve failed; pick 4 non-collinear points.")
    return CourtCalibration(image_points=image_points, H=H)


def shot_zone(x_ft: float, y_ft: float) -> str:
    """Classify a shot location in court feet into a coarse zone.

    Origin at far-sideline baseline corner; x along baseline (0..50),
    y from baseline toward half (0..47). Rim at (25, 5.25).
    """
    rim_x, rim_y = HALF_COURT_W_FT / 2.0, RIM_FROM_BASELINE_FT
    dx, dy = x_ft - rim_x, y_ft - rim_y
    dist = float(np.hypot(dx, dy))
    if dist <= 4.0:
        return "rim"
    if dist <= 14.0:
        return "paint"
    # 3-pt arc: 23'9" at top, 22' on the corners. Use 22.5' as a simple cut.
    if dist >= 22.5:
        return "three"
    return "midrange"
