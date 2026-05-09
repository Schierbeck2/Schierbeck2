"""Streamlit UI for the basketball game analyzer.

Run with:
    streamlit run app.py
"""

from __future__ import annotations

import json
from pathlib import Path

import cv2
import numpy as np
import pandas as pd
import streamlit as st

from analyzer.config import OUTPUT_DIR, SETTINGS, UPLOAD_DIR
from analyzer.court import calibrate
from analyzer.events import ShotEvent
from analyzer.plots import shot_chart
from analyzer.report import run as run_pipeline
from analyzer.video import probe, read_frame


st.set_page_config(page_title="Basketball Game Analyzer", layout="wide")

st.title("🏀 Basketball Game Analyzer")
st.caption(
    "Upload a game recording, calibrate the court, and get a coaching "
    "report with stats, a shot chart, and highlight clips."
)


# ---------- session state ----------
ss = st.session_state
ss.setdefault("video_path", None)
ss.setdefault("calibration", None)
ss.setdefault("calibration_points", [])
ss.setdefault("result", None)


# ---------- step 1: upload ----------
with st.expander("Step 1 — Upload a game video", expanded=ss.video_path is None):
    uploaded = st.file_uploader(
        "Choose a video file (mp4, mov, avi)",
        type=["mp4", "mov", "avi", "mkv"],
        accept_multiple_files=False,
    )
    if uploaded is not None:
        dst = UPLOAD_DIR / uploaded.name
        dst.write_bytes(uploaded.getbuffer())
        ss.video_path = str(dst)
        ss.result = None
        ss.calibration = None
        ss.calibration_points = []
        st.success(f"Uploaded to {dst}")
    if ss.video_path:
        st.write(f"**Active video:** `{ss.video_path}`")
        try:
            info = probe(ss.video_path)
            st.write(
                f"{info.width}×{info.height} px, {info.fps:.1f} fps, "
                f"{info.duration_s:.1f} s, {info.n_frames} frames"
            )
        except Exception as e:
            st.error(f"Could not read video: {e}")


# ---------- step 2: calibrate court ----------
if ss.video_path:
    with st.expander(
        "Step 2 — Calibrate the court (click 4 corners on a frame)",
        expanded=ss.calibration is None,
    ):
        st.markdown(
            "Pick a frame index and enter the **pixel coordinates** of the "
            "four corners of the half-court you want to analyze, in this "
            "order: 1) baseline + far sideline, 2) baseline + near sideline, "
            "3) half-court line + near sideline, 4) half-court line + far "
            "sideline. The displayed frame includes a pixel grid to help."
        )

        info = probe(ss.video_path)
        col1, col2 = st.columns([2, 1])
        with col1:
            frame_idx = st.slider(
                "Calibration frame",
                min_value=0,
                max_value=max(0, info.n_frames - 1),
                value=min(60, max(0, info.n_frames - 1)),
            )
            try:
                frame = read_frame(ss.video_path, frame_idx)
            except Exception as e:
                st.error(f"{e}")
                frame = None

            if frame is not None:
                # Draw a faint pixel grid for reference.
                preview = frame.copy()
                step = max(50, frame.shape[1] // 16)
                for x in range(0, preview.shape[1], step):
                    cv2.line(preview, (x, 0), (x, preview.shape[0]),
                             (0, 255, 255), 1)
                for y in range(0, preview.shape[0], step):
                    cv2.line(preview, (0, y), (preview.shape[1], y),
                             (0, 255, 255), 1)
                # Mark already-entered points.
                for i, (px, py) in enumerate(ss.calibration_points):
                    cv2.circle(preview, (int(px), int(py)), 8, (0, 0, 255), 2)
                    cv2.putText(
                        preview, str(i + 1), (int(px) + 10, int(py) + 5),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2,
                    )
                st.image(
                    cv2.cvtColor(preview, cv2.COLOR_BGR2RGB),
                    caption=f"Frame {frame_idx}",
                    use_column_width=True,
                )

        with col2:
            st.markdown("**Enter the four points (px):**")
            pts: list[tuple[float, float]] = []
            labels = [
                "1: baseline + far sideline",
                "2: baseline + near sideline",
                "3: half-court + near sideline",
                "4: half-court + far sideline",
            ]
            for i, label in enumerate(labels):
                cur = ss.calibration_points[i] if i < len(ss.calibration_points) else (0, 0)
                cx = st.number_input(f"{label} — x", value=int(cur[0]), step=1, key=f"px_{i}")
                cy = st.number_input(f"{label} — y", value=int(cur[1]), step=1, key=f"py_{i}")
                pts.append((float(cx), float(cy)))

            if st.button("Save calibration"):
                try:
                    ss.calibration = calibrate(pts)
                    ss.calibration_points = pts
                    st.success("Calibration saved.")
                except Exception as e:
                    st.error(f"Calibration failed: {e}")

            if ss.calibration is not None:
                st.success("Court is calibrated. You can re-run if needed.")


# ---------- step 3: run analysis ----------
if ss.video_path and ss.calibration is not None:
    with st.expander("Step 3 — Run analysis", expanded=ss.result is None):
        st.write(
            f"Model: `{SETTINGS.yolo_model}`  ·  Device: `{SETTINGS.device}`  "
            f"·  Frame stride: `{SETTINGS.frame_stride}`"
        )
        if not SETTINGS.anthropic_api_key:
            st.warning(
                "No `ANTHROPIC_API_KEY` set in `.env`. The app will still "
                "run the tracker and show stats, but the written coaching "
                "narrative will be a heuristic placeholder."
            )

        if st.button("Run full analysis", type="primary"):
            progress = st.progress(0.0, text="Starting...")
            def on_status(msg: str, p: float) -> None:
                progress.progress(min(1.0, max(0.0, p)), text=msg)

            try:
                ss.result = run_pipeline(
                    ss.video_path,
                    calibration=ss.calibration,
                    on_status=on_status,
                )
                st.success("Analysis complete.")
            except Exception as e:
                st.exception(e)


# ---------- step 4: review results ----------
if ss.result is not None:
    result = ss.result
    st.header("Results")

    tabs = st.tabs(
        ["Team report", "Players", "Shot chart", "Possessions", "Highlights", "Raw data"]
    )

    # --- team report
    with tabs[0]:
        c = result.coach
        st.subheader("Coach summary")
        st.write(c.get("team_summary") or "_(no summary)_")
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**Strengths**")
            for s in c.get("team_strengths") or []:
                st.markdown(f"- {s}")
        with col2:
            st.markdown("**Areas to improve**")
            for s in c.get("team_areas_to_improve") or []:
                st.markdown(f"- {s}")

        st.subheader("Team stats")
        rows = []
        for tid, ts in result.team_stats.items():
            rows.append(
                {
                    "team": chr(ord("A") + int(tid)),
                    "players": len(ts["players"]),
                    "shots_att": ts["shots_attempted"],
                    "shots_made": ts["shots_made"],
                    "fg_pct": ts.get("fg_pct"),
                    "possessions": ts.get("possessions", 0),
                    "poss_time_s": round(ts.get("possession_time_s", 0), 1),
                    "OREB": ts.get("offensive_rebounds", 0),
                    "DREB": ts.get("defensive_rebounds", 0),
                    "REB": ts.get("total_rebounds", 0),
                }
            )
        if rows:
            st.dataframe(pd.DataFrame(rows), hide_index=True)
        else:
            st.info("No team-level stats yet (need at least one detected shot).")

    # --- players
    with tabs[1]:
        rows = []
        for tid, ps in result.player_stats.items():
            rows.append(
                {
                    "track_id": tid,
                    "name": ps.get("display_name"),
                    "jersey": ps.get("jersey_number") or "?",
                    "team": (
                        chr(ord("A") + int(ps["team"]))
                        if ps.get("team") is not None else "?"
                    ),
                    "minutes": round(ps.get("seconds_on_court", 0) / 60.0, 2),
                    "shots_att": ps.get("shots_attempted", 0),
                    "shots_made": ps.get("shots_made", 0),
                    "fg_pct": ps.get("fg_pct"),
                    "poss": ps.get("possessions", 0),
                    "poss_time_s": round(ps.get("possession_time_s", 0), 1),
                    "OREB": ps.get("offensive_rebounds", 0),
                    "DREB": ps.get("defensive_rebounds", 0),
                }
            )
        if rows:
            st.dataframe(pd.DataFrame(rows), hide_index=True)
        else:
            st.info("No players detected.")

        per_player = (result.coach or {}).get("per_player", {}) or {}
        for tid, ps in result.player_stats.items():
            name = ps.get("display_name", f"Player #{tid}")
            with st.expander(name, expanded=False):
                notes = per_player.get(name, {})
                st.markdown(f"**Summary** — {notes.get('summary', '_(none)_')}")
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown("**Strengths**")
                    for s in notes.get("strengths", []) or []:
                        st.markdown(f"- {s}")
                with col2:
                    st.markdown("**Improvements**")
                    for s in notes.get("improvements", []) or []:
                        st.markdown(f"- {s}")
                form_notes = notes.get("shooting_form_notes")
                if form_notes:
                    st.markdown(f"**Shooting form** — {form_notes}")

                # Form metric rows for this player.
                fm_rows = [
                    fm for fm in result.form_metrics if fm.get("track_id") == tid
                ]
                if fm_rows:
                    st.dataframe(pd.DataFrame(fm_rows), hide_index=True)

    # --- shot chart
    with tabs[2]:
        events = [
            ShotEvent(**{k: v for k, v in e.items() if k in ShotEvent.__annotations__})
            for e in result.shot_events
        ]
        if events:
            fig = shot_chart(events, title="Half-court shot chart")
            st.pyplot(fig, clear_figure=True)
        else:
            st.info("No shots detected.")

    # --- possessions
    with tabs[3]:
        st.subheader("Possessions")
        if result.possessions:
            poss_rows = []
            name_by_tid = {
                int(tid): ps.get("display_name") for tid, ps in result.player_stats.items()
            }
            for p in result.possessions:
                poss_rows.append(
                    {
                        "t_start": round(p.get("t_start", 0), 1),
                        "duration_s": round(p.get("duration_s", 0), 2),
                        "team": (
                            chr(ord("A") + int(p["team"]))
                            if p.get("team") is not None else "?"
                        ),
                        "owner": name_by_tid.get(int(p.get("track_id") or -1), "?"),
                        "frames": p.get("n_frames"),
                    }
                )
            st.dataframe(pd.DataFrame(poss_rows), hide_index=True)
        else:
            st.info("No possessions detected.")

        st.subheader("Rebounds")
        if result.rebounds:
            reb_rows = []
            name_by_tid = {
                int(tid): ps.get("display_name") for tid, ps in result.player_stats.items()
            }
            for r in result.rebounds:
                reb_rows.append(
                    {
                        "t": round(r.get("t_seconds", 0), 1),
                        "kind": r.get("kind"),
                        "rebounder": name_by_tid.get(
                            int(r.get("rebounder_track_id") or -1), "?"
                        ),
                        "team": (
                            chr(ord("A") + int(r["rebounder_team"]))
                            if r.get("rebounder_team") is not None else "?"
                        ),
                        "shot_idx": r.get("shot_index"),
                    }
                )
            st.dataframe(pd.DataFrame(reb_rows), hide_index=True)
        else:
            st.info("No rebounds inferred (need at least one missed shot followed by a possession).")

    # --- highlights
    with tabs[4]:
        if not result.clips:
            st.info("No highlight clips were generated.")
        for clip in result.clips:
            s = clip["shot_event"]
            label = (
                f"Shot @ t={s['t_start']:.1f}s · zone={s.get('zone') or '?'} · "
                f"{'MADE' if s.get('made') else 'miss/unknown'}"
            )
            st.markdown(f"**{label}**")
            try:
                st.video(clip["path"])
            except Exception:
                st.write(clip["path"])

    # --- raw
    with tabs[5]:
        st.download_button(
            "Download analysis JSON",
            data=json.dumps(
                {
                    "video_path": result.video_path,
                    "fps": result.fps,
                    "duration_s": result.duration_s,
                    "teams": result.teams,
                    "jersey_numbers": result.jersey_numbers,
                    "shot_events": result.shot_events,
                    "possessions": result.possessions,
                    "rebounds": result.rebounds,
                    "form_metrics": result.form_metrics,
                    "player_stats": result.player_stats,
                    "team_stats": result.team_stats,
                    "clips": result.clips,
                    "coach": result.coach,
                },
                indent=2,
                default=str,
            ),
            file_name="analysis.json",
            mime="application/json",
        )
        st.json(
            {
                "n_detections": len(result.detections),
                "n_shots": len(result.shot_events),
                "n_possessions": len(result.possessions),
                "n_rebounds": len(result.rebounds),
                "n_clips": len(result.clips),
                "teams": result.teams,
            }
        )

st.markdown("---")
st.caption(
    "MVP: tracker output is heuristic (especially make/miss). Player IDs are "
    "stable within continuous tracking, not jersey numbers. See README."
)
