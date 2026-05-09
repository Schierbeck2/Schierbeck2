# Basketball Game Analyzer

An MVP web app that analyzes a recording of a basketball game and produces a
coaching report for the team and individual players.

The pipeline is **hybrid**: a computer-vision tracker produces objective stats
(player positions, ball motion, shot attempts, shot zones), and a vision LLM
(Anthropic's Claude) writes the coaching narrative on top of the numbers and
sampled frames.

## What it does

Given a video of a game (single fixed-ish camera view works best) you get:

- **Team coaching report** — offense/defense observations, transitions,
  spacing, turnovers.
- **Per-player feedback** — individual notes, shooting-form pose summary,
  decision-making.
- **Stats and shot chart** — FG% by zone, attempts, makes, plus a
  half-court shot chart (after a one-time 4-point court calibration).
- **Possession & rebound tracking** — per-frame ball ownership coalesced
  into possession blocks; offensive/defensive rebounds attributed to each
  missed shot.
- **Jersey-number OCR** — best-effort reading of each player's number so
  reports say "Team A #7" instead of "Player #4".
- **Basket-side detection** — once both rims are calibrated, each shot and
  possession is tagged with a left/right rim, the team's attacking rim is
  inferred from their shot distribution, and possessions are classified
  half-court vs transition.
- **Manual overrides + cheap re-runs** — the heavy CV pass (tracking, OCR,
  pose) is cached in-session, so you can fix wrong jersey numbers or team
  assignments and re-run only the cheap analytics (shots, possessions,
  rebounds, stats, coach) without re-tracking.
- **Persistent sessions** — every analysis is auto-saved to
  `data/cache/<video-stem>/`. Restart the app the next day, pick the
  session from the sidebar, and tweak overrides without re-running YOLO
  or OCR.
- **Highlight clips** — auto-cut short clips around detected shot events.

Everything runs locally. The only external service is the Claude API for the
written coaching notes.

## Quick start

```bash
cd basketball_analysis
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                # then edit .env and add ANTHROPIC_API_KEY
streamlit run app.py
```

Open the URL Streamlit prints (usually <http://localhost:8501>).

## Workflow in the app

1. **Upload** a game video (`mp4`, `mov`, `avi`).
2. **Calibrate the court** —
   - Click 4 known points on a frame (the four corners of the half-court
     you want to analyze). This drives the shot chart.
   - Click the **two rim positions** (left and right basket). This drives
     attacking-rim detection and the half-court vs transition split.
3. **Run analysis** — the tracker will run on the video. The first run
   downloads the YOLOv8n weights (~6 MB).
4. **Review** the team report, players, shot chart, possessions, and
   highlight clips.
5. **Optional — fix mistakes**: if the auto team clustering came out
   backwards or some jersey numbers are wrong, edit the override table
   in *Step 3b* and click **Re-run rollups**. Tracking and OCR are reused
   from the first pass, so this is much faster than re-running from scratch.
6. **Coming back later**: every analysis is auto-saved. Pick the session
   from the **Saved sessions** sidebar to restore the tracker output,
   calibration, and last result. From there you can edit overrides and
   re-run rollups without redoing the slow tracking pass.

Saved sessions live in `data/cache/<video-stem>/` and are git-ignored;
delete the directory (or use the **Delete** button in the sidebar) to
clear one out. The original video file is referenced by path, not copied
into the cache, so don't delete files in `data/uploads/` if you want
highlight clips to keep working after a reload.

## Why a hybrid approach?

- **Trackers** (YOLO + ByteTrack) give you reproducible, objective stats —
  positions, distances, shot attempts. They are bad at *judgement* ("the
  spacing on that possession was poor").
- **Vision LLMs** are good at judgement and bad at counting. We feed them the
  numbers we trust and a small set of sampled frames around each event so they
  can comment on form and decisions.

## Caveats / scope

This is an MVP, not a broadcast-grade analytics product. Specifically:

- Jersey-number OCR is best-effort: small/blurry numbers, occlusion, and
  shaky cameras hurt accuracy. Players whose number can't be read fall back
  to a `Player #<track_id>` label.
- Shot detection uses ball-trajectory + rim-region heuristics. Made vs.
  missed is approximate.
- Possession is inferred from ball-to-player proximity. Rapid passes inside
  a tight cluster of players will sometimes assign the wrong owner.
- Rebound classification (OREB vs DREB) depends on team-color clustering
  being right, which can fail with similar uniforms. If you see weird
  results, use the override table in *Step 3b* (the "flip teams" toggle is
  the fastest fix when the two clusters are simply swapped).
- Basket-side detection assumes a roughly fixed camera position. Heavy
  panning or sideline-to-sideline switches will move the rim positions
  away from where they were calibrated and degrade the half-court vs
  transition split.
- Best with a fixed camera. Heavy zooms / cuts / multi-cam broadcast feeds
  will degrade tracking.
- A single CPU is fine for short clips (<2 min); for full-game video a CUDA
  GPU is strongly recommended (set `DEVICE=cuda` in `.env`).

## Project layout

```
basketball_analysis/
  app.py                  # Streamlit entry point
  analyzer/
    __init__.py
    config.py             # paths, env, runtime config
    video.py              # frame iteration, sampling, writing
    tracker.py            # YOLO + ByteTrack detect + track, team-color cluster
    court.py              # 4-point homography for shot chart
    jersey.py             # EasyOCR jersey-number reading
    pose.py               # MediaPipe pose for shooting-form notes
    events.py             # shot detection heuristics
    possession.py         # per-frame ball owner + rebound attribution
    stats.py              # aggregate per-player and team stats
    clips.py              # cut highlight clips around events
    coach.py              # Claude coaching notes
    report.py             # heavy + light pipeline phases, final report
    persistence.py        # save / load / list sessions in data/cache/
    plots.py              # shot chart and overlay rendering
  data/
    uploads/  outputs/  clips/  cache/
  requirements.txt
  .env.example
  README.md
```
