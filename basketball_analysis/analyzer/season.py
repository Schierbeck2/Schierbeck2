"""Multi-game (season-level) rollups.

We anchor every saved session to a "canonical" roster — by default the
most recent session — and use the same Jaccard-by-jersey-number matching
as `diff.py` to relabel each older session's teams. Players are matched
within each canonical team by jersey number.

The result is a long-format DataFrame with one row per
(session, scope, team, jersey, metric, value). Streamlit can pivot it
into trend lines (`st.line_chart`) or tables.
"""

from __future__ import annotations

from typing import Any, Iterable, Optional

import pandas as pd

from . import persistence
from .diff import (
    PLAYER_METRICS,
    TEAM_METRICS,
    _resolve,
    match_teams,
)


def _player_for_team(player_stats: dict, team_player_ids: Iterable[Any]) -> dict[str, dict]:
    """Map jersey -> player dict for the players on a given team."""
    out: dict[str, dict] = {}
    for pid in team_player_ids or []:
        try:
            ps = _resolve(player_stats, int(pid))
        except (TypeError, ValueError):
            ps = None
        if not ps:
            continue
        j = ps.get("jersey_number")
        if not j:
            continue
        existing = out.get(str(j))
        if existing is None or ps.get("seconds_on_court", 0) > existing.get("seconds_on_court", 0):
            out[str(j)] = ps
    return out


def load_all_loaded_sessions() -> list[dict]:
    """Load every persisted session that has a result file. Returns a list
    of dicts: {name, meta, result}."""
    out: list[dict] = []
    for s in persistence.list_sessions():
        try:
            bundle = persistence.load_session(s["name"])
        except Exception:
            continue
        result = bundle.get("result")
        if result is None:
            continue
        out.append({"name": s["name"], "meta": s, "result": result})
    return out


def build_long_dataframe(
    sessions: list[dict],
    anchor_name: Optional[str] = None,
) -> pd.DataFrame:
    """Build a long-format frame across `sessions`.

    `anchor_name` selects the canonical roster used to relabel teams; if
    None, the most-recent session in `sessions` is used.
    """
    if not sessions:
        return pd.DataFrame(
            columns=["session", "saved_at", "team", "scope", "jersey", "metric", "value"]
        )

    anchor = None
    if anchor_name:
        for s in sessions:
            if s["name"] == anchor_name:
                anchor = s
                break
    if anchor is None:
        anchor = max(sessions, key=lambda s: s["meta"].get("saved_at") or 0)

    rows: list[dict] = []
    for s in sessions:
        result = s["result"]
        # Match this session's teams to the anchor's teams.
        team_map = match_teams(
            anchor["result"].team_stats, anchor["result"].player_stats,
            result.team_stats, result.player_stats,
        )
        # team_map maps current_team_id -> anchor_team_id.
        for sess_tid, anchor_tid in team_map.items():
            ts = _resolve(result.team_stats, sess_tid)
            if ts is None:
                continue
            canonical_label = chr(ord("A") + int(anchor_tid))
            base = {
                "session": s["name"],
                "saved_at": s["meta"].get("saved_at"),
                "team": canonical_label,
            }
            for metric, _ in TEAM_METRICS:
                rows.append({
                    **base,
                    "scope": "team",
                    "jersey": None,
                    "metric": metric,
                    "value": ts.get(metric),
                })
            by_jersey = _player_for_team(result.player_stats, ts.get("players", []))
            for jersey, ps in by_jersey.items():
                for metric, _ in PLAYER_METRICS:
                    rows.append({
                        **base,
                        "scope": "player",
                        "jersey": jersey,
                        "metric": metric,
                        "value": ps.get(metric),
                    })

    df = pd.DataFrame(rows)
    if not df.empty and "saved_at" in df.columns:
        df = df.sort_values("saved_at")
    return df


def team_trend(df: pd.DataFrame, metric: str) -> pd.DataFrame:
    """Pivot a team metric into a wide DataFrame indexed by saved_at,
    with one column per team. Suitable for `st.line_chart`."""
    if df.empty:
        return pd.DataFrame()
    sub = df[(df["scope"] == "team") & (df["metric"] == metric)].copy()
    if sub.empty:
        return pd.DataFrame()
    sub["saved_at"] = pd.to_datetime(sub["saved_at"], unit="s", errors="coerce")
    return sub.pivot_table(
        index="saved_at", columns="team", values="value", aggfunc="first"
    ).sort_index()


def player_trend(df: pd.DataFrame, team: str, jersey: str, metric: str) -> pd.DataFrame:
    """One column for the player; rows per saved_at."""
    if df.empty:
        return pd.DataFrame()
    sub = df[
        (df["scope"] == "player")
        & (df["team"] == team)
        & (df["jersey"] == jersey)
        & (df["metric"] == metric)
    ].copy()
    if sub.empty:
        return pd.DataFrame()
    sub["saved_at"] = pd.to_datetime(sub["saved_at"], unit="s", errors="coerce")
    sub = sub.sort_values("saved_at")
    return sub.set_index("saved_at")[["value"]].rename(columns={"value": metric})


def season_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Per-team season averages across the long DataFrame's metrics."""
    if df.empty:
        return pd.DataFrame()
    team_part = df[df["scope"] == "team"].copy()
    if team_part.empty:
        return pd.DataFrame()
    return (
        team_part
        .groupby(["team", "metric"], dropna=False)["value"]
        .agg(["mean", "min", "max", "count"])
        .reset_index()
    )
