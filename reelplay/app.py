"""Streamlit UI for Reelplay, the basketball game analyzer.

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

from analyzer import diff as diff_mod
from analyzer import persistence
from analyzer import season as season_mod
from analyzer.config import OUTPUT_DIR, SETTINGS, UPLOAD_DIR
from analyzer.court import BasketCalibration, calibrate
from analyzer.events import ShotEvent
from analyzer.plots import shot_chart
from analyzer.report import recompute as recompute_pipeline
from analyzer.report import run as run_pipeline
from analyzer.video import probe, read_frame


st.set_page_config(page_title="Reelplay", layout="wide")

st.title("🏀 Reelplay")
st.caption(
    "Upload a game recording, calibrate the court, and get a coaching "
    "report with stats, a shot chart, and highlight clips."
)


# ---------- session state ----------
ss = st.session_state
ss.setdefault("video_path", None)
ss.setdefault("calibration", None)
ss.setdefault("calibration_points", [])
ss.setdefault("basket_calibration", None)
ss.setdefault("rim_points", [(0, 0), (0, 0)])  # left rim, right rim (px)
ss.setdefault("result", None)
ss.setdefault("heavy_cache", None)
ss.setdefault("override_editor_df", None)


def _persist_current_session() -> None:
    """Save the current session bundle to disk (best-effort)."""
    if not ss.video_path or ss.heavy_cache is None:
        return
    try:
        persistence.save_session(
            video_path=ss.video_path,
            heavy_cache=ss.heavy_cache,
            court_calibration=ss.calibration,
            basket_calibration=ss.basket_calibration,
            calibration_points=ss.calibration_points,
            rim_points=ss.rim_points,
            result=ss.result,
        )
    except Exception as e:
        st.warning(f"Could not save session: {e}")


def _load_session_into_state(name: str) -> None:
    bundle = persistence.load_session(name)
    ss.video_path = bundle["meta"].get("video_path") or ss.video_path
    ss.heavy_cache = bundle["heavy_cache"]
    ss.calibration = bundle["court_calibration"]
    ss.basket_calibration = bundle["basket_calibration"]
    ss.calibration_points = bundle["calibration_points"]
    ss.rim_points = bundle["rim_points"] or [(0, 0), (0, 0)]
    ss.result = bundle["result"]
    ss.override_editor_df = None


# ---------- sidebar: saved sessions + bundle import/export ----------
with st.sidebar:
    st.header("Saved sessions")
    sessions = persistence.list_sessions()
    if not sessions:
        st.caption("No saved sessions yet. Upload a video and run an analysis to create one.")
    else:
        labels = []
        for s in sessions:
            ts = s.get("saved_at")
            when = ""
            if ts:
                from datetime import datetime
                when = datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M")
            labels.append(
                f"{s['name']} — {s.get('n_shots', 0)} shots · {when}"
            )
        choice = st.selectbox(
            "Pick one to load",
            options=list(range(len(sessions))),
            format_func=lambda i: labels[i],
            key="saved_session_choice",
        )
        sel = sessions[choice]
        if not sel.get("video_exists", True):
            st.caption(
                f"⚠️ Original video not found at `{sel.get('video_path')}`. "
                "Tracker results will still load; highlight clips may be missing."
            )
        col_a, col_b = st.columns(2)
        if col_a.button("Load", key="btn_load_session"):
            try:
                _load_session_into_state(sel["name"])
                st.success(f"Loaded session: {sel['name']}")
                st.rerun()
            except Exception as e:
                st.exception(e)
        if col_b.button("Delete", key="btn_delete_session"):
            persistence.delete_session(sel["name"])
            st.warning(f"Deleted session: {sel['name']}")
            st.rerun()

        st.divider()
        st.subheader("Share")
        include_video = st.checkbox(
            "Include video file (larger, but recipient gets highlight clips too)",
            value=False,
            key="bundle_include_video",
        )
        try:
            bundle_bytes = persistence.export_bundle_bytes(
                sel["name"], include_video=include_video
            )
            st.download_button(
                "Export bundle (.zip)",
                data=bundle_bytes,
                file_name=f"{sel['name']}.bball.zip",
                mime="application/zip",
                key="btn_export_bundle",
            )
            st.caption(f"Bundle size: {len(bundle_bytes) / 1024:.1f} KB")
        except Exception as e:
            st.warning(f"Cannot prepare bundle: {e}")

    st.divider()
    st.subheader("Import session")
    incoming = st.file_uploader(
        "Drop a .bball.zip from a teammate",
        type=["zip"],
        accept_multiple_files=False,
        key="bundle_uploader",
    )
    if incoming is not None and st.button("Import", key="btn_import_bundle"):
        try:
            new_name = persistence.import_bundle(incoming.getvalue())
            st.success(f"Imported as `{new_name}`. Pick it from the list above.")
            st.rerun()
        except Exception as e:
            st.exception(e)


# ---------- season trends (visible when 2+ saved sessions exist) ----------
_n_saved = len(persistence.list_sessions())
if _n_saved >= 2:
    with st.expander(
        f"Season trends — {_n_saved} games saved",
        expanded=False,
    ):
        st.caption(
            "Trends across every saved session. Teams are matched between "
            "games by jersey-number overlap; players by jersey number."
        )
        season_sessions = season_mod.load_all_loaded_sessions()
        if len(season_sessions) < 2:
            st.info("Need at least two sessions with saved analysis results.")
        else:
            anchor_choice = st.selectbox(
                "Roster anchor",
                options=[s["name"] for s in season_sessions],
                index=0,
                help=(
                    "The session whose team-A / team-B labeling everything "
                    "else is mapped to. Defaults to the most recent."
                ),
                key="season_anchor",
            )
            df_long = season_mod.build_long_dataframe(
                season_sessions, anchor_name=anchor_choice
            )

            tab_team, tab_player, tab_summary = st.tabs(
                ["Team trends", "Player trends", "Season summary"]
            )

            with tab_team:
                team_metric_options = [m for m, _ in diff_mod.TEAM_METRICS]
                tm = st.selectbox(
                    "Team metric",
                    team_metric_options,
                    index=team_metric_options.index("fg_pct") if "fg_pct" in team_metric_options else 0,
                    key="season_team_metric",
                )
                wide = season_mod.team_trend(df_long, tm)
                if wide.empty:
                    st.info("No data for this metric.")
                else:
                    st.line_chart(wide)

            with tab_player:
                # Pick a team, then a jersey, then a metric.
                player_subset = df_long[df_long["scope"] == "player"]
                if player_subset.empty:
                    st.info(
                        "No player-level rows. This usually means jersey OCR "
                        "didn't produce numbers in either game."
                    )
                else:
                    teams_avail = sorted(player_subset["team"].dropna().unique().tolist())
                    team_pick = st.selectbox(
                        "Team", teams_avail, key="season_player_team"
                    )
                    jerseys_avail = sorted(
                        player_subset[player_subset["team"] == team_pick]["jersey"].dropna().unique().tolist(),
                        key=lambda x: int(x) if str(x).isdigit() else 99,
                    )
                    if not jerseys_avail:
                        st.info("No players with readable jerseys for this team.")
                    else:
                        jersey_pick = st.selectbox(
                            "Jersey #", jerseys_avail, key="season_player_jersey"
                        )
                        player_metric_options = [m for m, _ in diff_mod.PLAYER_METRICS]
                        pm = st.selectbox(
                            "Player metric",
                            player_metric_options,
                            index=player_metric_options.index("fg_pct") if "fg_pct" in player_metric_options else 0,
                            key="season_player_metric",
                        )
                        wide_p = season_mod.player_trend(
                            df_long, team_pick, jersey_pick, pm
                        )
                        if wide_p.empty:
                            st.info("No data for that combination.")
                        else:
                            st.line_chart(wide_p)

            with tab_summary:
                summary = season_mod.season_summary(df_long)
                if summary.empty:
                    st.info("No team-level data available.")
                else:
                    st.dataframe(summary, hide_index=True)


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
        already_had_session = persistence.has_session(dst)
        ss.video_path = str(dst)
        ss.result = None
        ss.calibration = None
        ss.calibration_points = []
        ss.basket_calibration = None
        ss.rim_points = [(0, 0), (0, 0)]
        ss.heavy_cache = None
        ss.override_editor_df = None
        st.success(f"Uploaded to {dst}")
        if already_had_session:
            st.info(
                f"A saved session already exists for `{dst.stem}`. Use "
                "**Restore saved session for this video** below, or pick "
                "it from the sidebar."
            )

    if ss.video_path and persistence.has_session(ss.video_path) and ss.heavy_cache is None:
        if st.button(
            "Restore saved session for this video",
            type="secondary",
            key="btn_restore_for_video",
        ):
            try:
                _load_session_into_state(Path(ss.video_path).stem)
                st.success("Restored.")
                st.rerun()
            except Exception as e:
                st.exception(e)

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
                # Mark rim points.
                rim_colors = [(255, 100, 0), (0, 165, 255)]  # left=blue-ish, right=orange
                rim_labels = ["L", "R"]
                for i, (rpx, rpy) in enumerate(ss.rim_points):
                    if rpx == 0 and rpy == 0:
                        continue
                    cv2.circle(preview, (int(rpx), int(rpy)), 10, rim_colors[i], 2)
                    cv2.putText(
                        preview, rim_labels[i], (int(rpx) + 12, int(rpy) + 5),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, rim_colors[i], 2,
                    )
                st.image(
                    cv2.cvtColor(preview, cv2.COLOR_BGR2RGB),
                    caption=f"Frame {frame_idx}",
                    use_column_width=True,
                )

        with col2:
            st.markdown("**Half-court corners (px):**")
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

            st.markdown("**Rim positions (px):**")
            st.caption(
                "Click-coordinates of the **two baskets** in the same frame. "
                "These let the app tell which basket each team is attacking."
            )
            rim_pts: list[tuple[float, float]] = []
            for i, label in enumerate(["Left rim", "Right rim"]):
                cur = ss.rim_points[i]
                rx = st.number_input(f"{label} — x", value=int(cur[0]), step=1, key=f"rim_x_{i}")
                ry = st.number_input(f"{label} — y", value=int(cur[1]), step=1, key=f"rim_y_{i}")
                rim_pts.append((float(rx), float(ry)))

            if st.button("Save calibration"):
                try:
                    ss.calibration = calibrate(pts)
                    ss.calibration_points = pts
                    ss.rim_points = rim_pts
                    if any(rx != 0 or ry != 0 for rx, ry in rim_pts):
                        ss.basket_calibration = BasketCalibration(
                            left_rim_xy=rim_pts[0],
                            right_rim_xy=rim_pts[1],
                        )
                    else:
                        ss.basket_calibration = None
                    st.success("Calibration saved.")
                except Exception as e:
                    st.error(f"Calibration failed: {e}")

            if ss.calibration is not None:
                st.success("Court is calibrated. You can re-run if needed.")
            if ss.basket_calibration is not None:
                st.success("Both baskets calibrated.")
            else:
                st.info(
                    "Rim positions not set yet. The app will still run; "
                    "it just won't be able to label which basket each team "
                    "is attacking or split possessions into half-court vs "
                    "transition."
                )


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
                heavy, result = run_pipeline(
                    ss.video_path,
                    calibration=ss.calibration,
                    basket_calibration=ss.basket_calibration,
                    on_status=on_status,
                )
                ss.heavy_cache = heavy
                ss.result = result
                ss.override_editor_df = None  # rebuild from new tracks
                _persist_current_session()
                st.success("Analysis complete and saved.")
            except Exception as e:
                st.exception(e)


# ---------- step 3b: edit overrides + recompute ----------
if ss.heavy_cache is not None and ss.result is not None:
    with st.expander("Step 3b — Edit overrides and re-run analytics", expanded=False):
        st.markdown(
            "Fix any wrong jersey numbers or team assignments below, then "
            "click **Re-run rollups**. The expensive tracking + OCR + pose "
            "pass is reused; only the cheap analytics (shots, possessions, "
            "rebounds, stats, coach) are recomputed."
        )

        if ss.override_editor_df is None:
            rows = []
            for tid, ps in sorted(ss.result.player_stats.items()):
                rows.append(
                    {
                        "track_id": int(tid),
                        "name": ps.get("display_name") or f"Player #{tid}",
                        "jersey": ps.get("jersey_number") or "",
                        "team": (
                            chr(ord("A") + int(ps["team"]))
                            if ps.get("team") is not None else "?"
                        ),
                        "minutes": round(ps.get("seconds_on_court", 0) / 60.0, 2),
                        "shots_att": ps.get("shots_attempted", 0),
                    }
                )
            ss.override_editor_df = pd.DataFrame(rows)

        edited = st.data_editor(
            ss.override_editor_df,
            hide_index=True,
            column_config={
                "track_id": st.column_config.NumberColumn(disabled=True),
                "name": st.column_config.TextColumn(disabled=True),
                "jersey": st.column_config.TextColumn(
                    help="Player's jersey number (e.g. '7'). Leave blank to clear."
                ),
                "team": st.column_config.SelectboxColumn(
                    options=["A", "B", "?"],
                    help="A or B; ? to leave unassigned.",
                ),
                "minutes": st.column_config.NumberColumn(disabled=True),
                "shots_att": st.column_config.NumberColumn(disabled=True),
            },
            num_rows="fixed",
            key="override_editor",
        )

        col_a, col_b = st.columns(2)
        skip_coach = col_a.checkbox(
            "Skip coach narrative (faster, no API call)", value=False
        )
        skip_clips = col_b.checkbox(
            "Skip cutting highlight clips", value=False
        )
        flip_teams = st.checkbox(
            "Flip team A ↔ B (use this if the team-color clustering came out backwards)",
            value=False,
        )

        if st.button("Re-run rollups", type="primary"):
            jersey_overrides: dict[int, str | None] = {}
            team_overrides: dict[int, int] = {}
            unassigned: list[int] = []
            for _, row in edited.iterrows():
                tid = int(row["track_id"])
                j = str(row["jersey"]).strip() if row["jersey"] is not None else ""
                jersey_overrides[tid] = j if j else None
                t = str(row["team"]).strip()
                if t in ("A", "B"):
                    team_idx = 0 if t == "A" else 1
                    if flip_teams:
                        team_idx = 1 - team_idx
                    team_overrides[tid] = team_idx
                else:
                    unassigned.append(tid)

            # Apply team-flip to any tracks we didn't explicitly override
            # but were auto-clustered.
            if flip_teams:
                for tid, auto_team in ss.heavy_cache.auto_teams.items():
                    if tid in team_overrides:
                        continue
                    if tid in unassigned:
                        continue
                    team_overrides[tid] = 1 - int(auto_team)

            progress = st.progress(0.0, text="Recomputing...")
            def on_status(msg: str, p: float) -> None:
                progress.progress(min(1.0, max(0.0, p)), text=msg)

            try:
                ss.result = recompute_pipeline(
                    ss.heavy_cache,
                    court_calibration=ss.calibration,
                    basket_calibration=ss.basket_calibration,
                    team_overrides=team_overrides,
                    jersey_overrides=jersey_overrides,
                    skip_coach=skip_coach,
                    skip_clips=skip_clips,
                    on_status=on_status,
                )
                ss.override_editor_df = None
                _persist_current_session()
                st.success("Re-run complete and saved.")
            except Exception as e:
                st.exception(e)


# ---------- step 4: review results ----------
if ss.result is not None:
    result = ss.result
    st.header("Results")

    tabs = st.tabs(
        ["Team report", "Players", "Shot chart", "Possessions",
         "Highlights", "Compare", "Raw data"]
    )

    # --- team report
    with tabs[0]:
        validation = getattr(result, "validation", {}) or {}
        if validation.get("auto_fix_applied"):
            st.info(
                "Auto-fix applied: both teams' shots originally pointed at "
                "the same rim, which usually means the team-color clustering "
                "came out swapped. Team A↔B labels have been flipped. Use the "
                "**Step 3b** override editor if you'd rather override this."
            )
        if validation.get("both_teams_same_rim"):
            st.warning(
                "Sanity check: both teams still have the same `attacking_rim`. "
                "The auto-fix could not resolve this (probably because the "
                "team mapping was overridden manually). Verify in the override "
                "table that the right players are on each team."
            )
        wrong_team_ids = validation.get("high_wrong_rim_team_ids") or []
        if wrong_team_ids:
            labels = ", ".join(chr(ord("A") + int(t)) for t in wrong_team_ids)
            st.warning(
                f"Team(s) {labels}: more than 40% of their detected shots "
                "point at the *other* basket. Either shot detection is "
                "mis-attributing shooters, or this team's mapping is noisy. "
                "Use Step 3b to inspect."
            )

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
                    "attacks": ts.get("attacking_rim") or "?",
                    "players": len(ts["players"]),
                    "shots_att": ts["shots_attempted"],
                    "shots_made": ts["shots_made"],
                    "fg_pct": ts.get("fg_pct"),
                    "wrong_rim_shots": ts.get("wrong_rim_shots", 0),
                    "possessions": ts.get("possessions", 0),
                    "half_court": ts.get("half_court_possessions", 0),
                    "transition": ts.get("transition_possessions", 0),
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
                        "start_rim": p.get("start_rim") or "?",
                        "end_rim": p.get("end_rim") or "?",
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

    # --- compare
    with tabs[5]:
        st.subheader("Compare with a previous game")
        all_sessions = persistence.list_sessions()
        # Exclude whatever session matches the current loaded video.
        current_stem = Path(result.video_path).stem
        candidates = [s for s in all_sessions if s.get("name") != current_stem]
        if not candidates:
            st.info(
                "Save at least one other session (or import a teammate's bundle) "
                "to enable comparison."
            )
        else:
            labels = []
            for s in candidates:
                ts = s.get("saved_at")
                when = ""
                if ts:
                    from datetime import datetime
                    when = datetime.fromtimestamp(ts).strftime("%Y-%m-%d")
                labels.append(f"{s['name']} ({when})")
            idx = st.selectbox(
                "Previous game",
                options=list(range(len(candidates))),
                format_func=lambda i: labels[i],
                key="compare_prev_choice",
            )
            prev_meta = candidates[idx]
            if st.button("Run comparison", key="btn_run_compare"):
                try:
                    prev_bundle = persistence.load_session(prev_meta["name"])
                    prev_result = prev_bundle.get("result")
                    if prev_result is None:
                        st.warning(
                            "That session has no saved analysis result yet. "
                            "Open it once and re-run rollups, then try again."
                        )
                    else:
                        out = diff_mod.compute_diff(prev_result, result)
                        st.session_state["compare_output"] = {
                            "prev_name": prev_meta["name"],
                            "out": out,
                        }
                except Exception as e:
                    st.exception(e)

            cmp_state = st.session_state.get("compare_output")
            if cmp_state and cmp_state.get("prev_name") == prev_meta["name"]:
                out = cmp_state["out"]
                team_match = out.get("team_match", {})
                if not team_match:
                    st.warning(
                        "No teams could be matched between the two games. "
                        "Make sure both have at least some readable jersey "
                        "numbers."
                    )

                st.markdown("**Team-level changes**")
                team_rows = out.get("teams") or []
                if team_rows:
                    df = pd.DataFrame(team_rows)
                    df = df.pivot_table(
                        index=["team", "metric"],
                        values=["prev", "curr", "delta"],
                        aggfunc="first",
                    ).reset_index()
                    st.dataframe(df, hide_index=True)
                else:
                    st.info("No team metrics available.")

                st.markdown("**Per-player changes (matched by jersey number)**")
                player_rows = out.get("players") or []
                if player_rows:
                    pdf = pd.DataFrame(player_rows)
                    st.dataframe(pdf, hide_index=True)
                else:
                    st.info(
                        "No players could be matched. Either jersey OCR was "
                        "weak in one of the games or the rosters don't overlap."
                    )

    # --- raw
    with tabs[6]:
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
