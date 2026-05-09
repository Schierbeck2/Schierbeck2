"""Video I/O helpers: probe metadata, iterate frames, save clips and frames."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

import cv2
import numpy as np


@dataclass(frozen=True)
class VideoInfo:
    path: Path
    width: int
    height: int
    fps: float
    n_frames: int

    @property
    def duration_s(self) -> float:
        return self.n_frames / self.fps if self.fps else 0.0


def probe(path: str | Path) -> VideoInfo:
    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        raise FileNotFoundError(f"Cannot open video: {path}")
    info = VideoInfo(
        path=Path(path),
        width=int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
        height=int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
        fps=float(cap.get(cv2.CAP_PROP_FPS) or 30.0),
        n_frames=int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0),
    )
    cap.release()
    return info


def iter_frames(path: str | Path, stride: int = 1) -> Iterator[tuple[int, np.ndarray]]:
    """Yield (frame_index, BGR frame) pairs, sampled every `stride` frames."""
    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        raise FileNotFoundError(f"Cannot open video: {path}")
    idx = 0
    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            if stride <= 1 or idx % stride == 0:
                yield idx, frame
            idx += 1
    finally:
        cap.release()


def read_frame(path: str | Path, frame_index: int) -> np.ndarray:
    """Read a single frame by index. Useful for the calibration step."""
    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        raise FileNotFoundError(f"Cannot open video: {path}")
    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
    ok, frame = cap.read()
    cap.release()
    if not ok:
        raise RuntimeError(f"Cannot read frame {frame_index} from {path}")
    return frame


def write_clip(
    src_path: str | Path,
    dst_path: str | Path,
    start_frame: int,
    end_frame: int,
) -> Path:
    """Copy frames [start_frame, end_frame) from src to dst as an mp4."""
    src = cv2.VideoCapture(str(src_path))
    if not src.isOpened():
        raise FileNotFoundError(f"Cannot open video: {src_path}")
    fps = src.get(cv2.CAP_PROP_FPS) or 30.0
    width = int(src.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(src.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    dst = cv2.VideoWriter(str(dst_path), fourcc, fps, (width, height))

    src.set(cv2.CAP_PROP_POS_FRAMES, max(0, start_frame))
    written = 0
    target = max(1, end_frame - start_frame)
    while written < target:
        ok, frame = src.read()
        if not ok:
            break
        dst.write(frame)
        written += 1
    src.release()
    dst.release()
    return Path(dst_path)
