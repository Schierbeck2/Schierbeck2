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
2. **Calibrate the court** — click 4 known points on a frame (the four corners
   of the half-court you want to analyze). This is used for the shot chart.
3. **Run analysis** — the tracker will run on the video. The first run
   downloads the YOLOv8n weights (~6 MB).
4. **Review** the team report, per-player tabs, shot chart, and highlight clips.

## Why a hybrid approach?

- **Trackers** (YOLO + ByteTrack) give you reproducible, objective stats —
  positions, distances, shot attempts. They are bad at *judgement* ("the
  spacing on that possession was poor").
- **Vision LLMs** are good at judgement and bad at counting. We feed them the
  numbers we trust and a small set of sampled frames around each event so they
  can comment on form and decisions.

## Caveats / scope

This is an MVP, not a broadcast-grade analytics product. Specifically:

- Player IDs are stable within continuous tracking but jersey numbers are not
  read by default — you may see "Player #4" rather than a real number. You can
  rename players in the UI after analysis.
- Shot detection uses ball-trajectory + rim-region heuristics. Made vs.
  missed is approximate.
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
    tracker.py            # YOLO + ByteTrack detect + track
    court.py              # 4-point homography for shot chart
    pose.py               # MediaPipe pose for shooting-form notes
    events.py             # shot/possession/rebound heuristics
    stats.py              # aggregate per-player and team stats
    clips.py              # cut highlight clips around events
    coach.py              # Claude coaching notes
    report.py             # build the final report dict
    plots.py              # shot chart and overlay rendering
  data/
    uploads/  outputs/  clips/  cache/
  requirements.txt
  .env.example
  README.md
```
