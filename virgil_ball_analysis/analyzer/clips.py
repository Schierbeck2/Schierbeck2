"""Cut a short clip around each detected event."""

from __future__ import annotations

from pathlib import Path

from .config import CLIPS_DIR, SETTINGS
from .events import ShotEvent
from .video import write_clip, probe


def cut_highlights(
    video_path: str | Path,
    shots: list[ShotEvent],
    out_dir: Path | None = None,
) -> list[dict]:
    """Cut a clip per shot. Returns metadata for each clip."""
    info = probe(video_path)
    out_dir = Path(out_dir) if out_dir else CLIPS_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    pad = int(SETTINGS.clip_pad_seconds * info.fps)
    results: list[dict] = []
    for i, s in enumerate(shots):
        start = max(0, s.start_frame - pad)
        end = min(info.n_frames, s.end_frame + pad)
        out_path = out_dir / f"shot_{i:03d}.mp4"
        write_clip(video_path, out_path, start, end)
        results.append(
            {
                "index": i,
                "path": str(out_path),
                "shot_event": s.to_dict(),
                "t_start": start / info.fps,
                "t_end": end / info.fps,
            }
        )
    return results
