"""Compare two saved sessions to show how a team progressed game-to-game.

Teams are matched between sessions by greedy Jaccard similarity over their
players' jersey numbers — a team whose roster carries the most overlapping
numbers is the same team. Players are then matched within each matched
team by jersey number.

We avoid trying to align tracker IDs across games because they're
per-video and not stable. If neither side has reliable jersey reads the
match falls back to team-id equality (so "team A" → "team A").
"""

from __future__ import annotations

from typing import Any, Iterable, Optional


# (metric_name, higher_is_worse). higher_is_worse just helps the UI label
# the delta if it wants to flag regressions.
TEAM_METRICS: list[tuple[str, bool]] = [
    ("shots_attempted", False),
    ("shots_made", False),
    ("fg_pct", False),
    ("possessions", False),
    ("half_court_possessions", False),
    ("transition_possessions", False),
    ("possession_time_s", False),
    ("offensive_rebounds", False),
    ("defensive_rebounds", False),
    ("total_rebounds", False),
    ("wrong_rim_shots", True),
]

PLAYER_METRICS: list[tuple[str, bool]] = [
    ("seconds_on_court", False),
    ("shots_attempted", False),
    ("shots_made", False),
    ("fg_pct", False),
    ("possessions", False),
    ("possession_time_s", False),
    ("offensive_rebounds", False),
    ("defensive_rebounds", False),
    ("total_rebounds", False),
]


def _delta(curr: Any, prev: Any) -> Optional[float]:
    if curr is None or prev is None:
        return None
    try:
        return float(curr) - float(prev)
    except (TypeError, ValueError):
        return None


def _resolve(d: dict, key: int) -> Optional[dict]:
    """Player/team dicts can come in with int or str keys depending on whether
    they were JSON-loaded. Try both."""
    if d is None:
        return None
    if key in d:
        return d[key]
    s = str(key)
    if s in d:
        return d[s]
    return None


def _team_rosters(team_stats: dict, player_stats: dict) -> dict[int, set[str]]:
    out: dict[int, set[str]] = {}
    for tid, ts in team_stats.items():
        jerseys: set[str] = set()
        for pid in ts.get("players", []) or []:
            try:
                ps = _resolve(player_stats, int(pid))
            except (TypeError, ValueError):
                ps = None
            if ps and ps.get("jersey_number"):
                jerseys.add(str(ps["jersey_number"]))
        out[int(tid)] = jerseys
    return out


def match_teams(prev_team_stats: dict, prev_player_stats: dict,
                curr_team_stats: dict, curr_player_stats: dict) -> dict[int, int]:
    """Greedy bipartite match by jersey-number Jaccard. Returns
    {curr_team_id: prev_team_id}."""
    prev_rost = _team_rosters(prev_team_stats, prev_player_stats)
    curr_rost = _team_rosters(curr_team_stats, curr_player_stats)
    pairs: list[tuple[float, int, int]] = []
    for ct, cset in curr_rost.items():
        for pt, pset in prev_rost.items():
            union = len(cset | pset)
            jac = len(cset & pset) / union if union else 0.0
            pairs.append((jac, ct, pt))
    pairs.sort(reverse=True)

    matched: dict[int, int] = {}
    used_p: set[int] = set()
    used_c: set[int] = set()
    for jac, ct, pt in pairs:
        if jac == 0 or ct in used_c or pt in used_p:
            continue
        matched[ct] = pt
        used_c.add(ct)
        used_p.add(pt)

    # Fallback: align unmatched teams by id-equality if both sides still have
    # them free. Better than nothing when nobody had readable numbers.
    for ct in curr_rost:
        if ct in used_c:
            continue
        if ct in prev_rost and ct not in used_p:
            matched[ct] = ct
            used_c.add(ct)
            used_p.add(ct)
    return matched


def diff_teams(prev_result: Any, curr_result: Any) -> list[dict]:
    matches = match_teams(
        prev_result.team_stats, prev_result.player_stats,
        curr_result.team_stats, curr_result.player_stats,
    )
    rows: list[dict] = []
    for curr_tid, prev_tid in matches.items():
        ct = _resolve(curr_result.team_stats, curr_tid)
        pt = _resolve(prev_result.team_stats, prev_tid)
        if ct is None or pt is None:
            continue
        team_label = chr(ord("A") + int(curr_tid))
        for metric, _ in TEAM_METRICS:
            rows.append({
                "team": team_label,
                "metric": metric,
                "prev": pt.get(metric),
                "curr": ct.get(metric),
                "delta": _delta(ct.get(metric), pt.get(metric)),
            })
    return rows


def _players_by_jersey(
    player_stats: dict, team_player_ids: Iterable[Any]
) -> dict[str, dict]:
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


def diff_players(prev_result: Any, curr_result: Any) -> list[dict]:
    matches = match_teams(
        prev_result.team_stats, prev_result.player_stats,
        curr_result.team_stats, curr_result.player_stats,
    )
    rows: list[dict] = []
    for curr_tid, prev_tid in matches.items():
        ct = _resolve(curr_result.team_stats, curr_tid)
        pt = _resolve(prev_result.team_stats, prev_tid)
        if ct is None or pt is None:
            continue
        team_label = chr(ord("A") + int(curr_tid))
        prev_by = _players_by_jersey(prev_result.player_stats, pt.get("players", []))
        curr_by = _players_by_jersey(curr_result.player_stats, ct.get("players", []))
        common = sorted(
            set(prev_by) & set(curr_by),
            key=lambda x: int(x) if x.isdigit() else 99,
        )
        for jersey in common:
            ps_prev = prev_by[jersey]
            ps_curr = curr_by[jersey]
            for metric, _ in PLAYER_METRICS:
                rows.append({
                    "team": team_label,
                    "jersey": jersey,
                    "metric": metric,
                    "prev": ps_prev.get(metric),
                    "curr": ps_curr.get(metric),
                    "delta": _delta(ps_curr.get(metric), ps_prev.get(metric)),
                })
    return rows


def compute_diff(prev_result: Any, curr_result: Any) -> dict:
    return {
        "teams": diff_teams(prev_result, curr_result),
        "players": diff_players(prev_result, curr_result),
        "team_match": match_teams(
            prev_result.team_stats, prev_result.player_stats,
            curr_result.team_stats, curr_result.player_stats,
        ),
    }
