"""Roll up tracker output + shot/possession/rebound events into stats."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, asdict, field
from typing import Optional

from .events import ShotEvent
from .possession import Possession, Rebound
from .tracker import Detection


@dataclass
class PlayerStats:
    track_id: int
    team: Optional[int]
    display_name: str
    jersey_number: Optional[str] = None
    frames_seen: int = 0
    seconds_on_court: float = 0.0
    shots_attempted: int = 0
    shots_made: int = 0
    shots_by_zone: dict[str, dict[str, int]] = field(
        default_factory=lambda: defaultdict(lambda: {"att": 0, "make": 0})
    )
    possessions: int = 0
    possession_time_s: float = 0.0
    offensive_rebounds: int = 0
    defensive_rebounds: int = 0

    @property
    def fg_pct(self) -> Optional[float]:
        if self.shots_attempted == 0:
            return None
        return self.shots_made / self.shots_attempted

    @property
    def total_rebounds(self) -> int:
        return self.offensive_rebounds + self.defensive_rebounds

    def to_dict(self) -> dict:
        d = asdict(self)
        d["fg_pct"] = self.fg_pct
        d["total_rebounds"] = self.total_rebounds
        d["shots_by_zone"] = {z: dict(v) for z, v in self.shots_by_zone.items()}
        return d


@dataclass
class TeamStats:
    team_id: int
    players: list[int]
    shots_attempted: int = 0
    shots_made: int = 0
    shots_by_zone: dict[str, dict[str, int]] = field(
        default_factory=lambda: defaultdict(lambda: {"att": 0, "make": 0})
    )
    possessions: int = 0
    possession_time_s: float = 0.0
    offensive_rebounds: int = 0
    defensive_rebounds: int = 0
    attacking_rim: Optional[str] = None  # "left" | "right" | None
    half_court_possessions: int = 0
    transition_possessions: int = 0
    wrong_rim_shots: int = 0  # debug signal: shots aimed at the OTHER team's rim

    @property
    def fg_pct(self) -> Optional[float]:
        if self.shots_attempted == 0:
            return None
        return self.shots_made / self.shots_attempted

    @property
    def total_rebounds(self) -> int:
        return self.offensive_rebounds + self.defensive_rebounds

    def to_dict(self) -> dict:
        d = asdict(self)
        d["fg_pct"] = self.fg_pct
        d["total_rebounds"] = self.total_rebounds
        d["shots_by_zone"] = {z: dict(v) for z, v in self.shots_by_zone.items()}
        return d


def aggregate(
    detections: list[Detection],
    shots: list[ShotEvent],
    teams: dict[int, int],
    fps: float,
    name_overrides: dict[int, str] | None = None,
    jersey_numbers: dict[int, str | None] | None = None,
    possessions: list[Possession] | None = None,
    rebounds: list[Rebound] | None = None,
) -> tuple[dict[int, PlayerStats], dict[int, TeamStats]]:
    name_overrides = name_overrides or {}
    jersey_numbers = jersey_numbers or {}
    possessions = possessions or []
    rebounds = rebounds or []
    players: dict[int, PlayerStats] = {}

    seen: dict[int, int] = defaultdict(int)
    for d in detections:
        if d.cls != "player":
            continue
        seen[d.track_id] += 1
    for tid, count in seen.items():
        players[tid] = PlayerStats(
            track_id=tid,
            team=teams.get(tid),
            display_name=name_overrides.get(tid, f"Player #{tid}"),
            jersey_number=jersey_numbers.get(tid),
            frames_seen=count,
            seconds_on_court=count / fps if fps else 0.0,
        )

    for s in shots:
        if s.shooter_track_id is None:
            continue
        ps = players.get(s.shooter_track_id)
        if ps is None:
            ps = PlayerStats(
                track_id=s.shooter_track_id,
                team=s.shooter_team,
                display_name=name_overrides.get(
                    s.shooter_track_id, f"Player #{s.shooter_track_id}"
                ),
                jersey_number=jersey_numbers.get(s.shooter_track_id),
            )
            players[s.shooter_track_id] = ps
        ps.shots_attempted += 1
        if s.made:
            ps.shots_made += 1
        if s.zone:
            zb = ps.shots_by_zone[s.zone]
            zb["att"] += 1
            if s.made:
                zb["make"] += 1

    for p in possessions:
        if p.track_id is None:
            continue
        ps = players.get(p.track_id)
        if ps is None:
            ps = PlayerStats(
                track_id=p.track_id,
                team=p.team,
                display_name=name_overrides.get(p.track_id, f"Player #{p.track_id}"),
                jersey_number=jersey_numbers.get(p.track_id),
            )
            players[p.track_id] = ps
        ps.possessions += 1
        ps.possession_time_s += p.duration_s

    for r in rebounds:
        if r.rebounder_track_id is None or r.kind == "unknown":
            continue
        ps = players.get(r.rebounder_track_id)
        if ps is None:
            continue
        if r.kind == "offensive":
            ps.offensive_rebounds += 1
        elif r.kind == "defensive":
            ps.defensive_rebounds += 1

    by_team: dict[int, TeamStats] = {}
    for ps in players.values():
        if ps.team is None:
            continue
        ts = by_team.get(ps.team)
        if ts is None:
            ts = TeamStats(team_id=ps.team, players=[])
            by_team[ps.team] = ts
        ts.players.append(ps.track_id)
        ts.shots_attempted += ps.shots_attempted
        ts.shots_made += ps.shots_made
        ts.possessions += ps.possessions
        ts.possession_time_s += ps.possession_time_s
        ts.offensive_rebounds += ps.offensive_rebounds
        ts.defensive_rebounds += ps.defensive_rebounds
        for zone, zb in ps.shots_by_zone.items():
            tzb = ts.shots_by_zone[zone]
            tzb["att"] += zb["att"]
            tzb["make"] += zb["make"]

    # Per-team attacking rim: majority of that team's shots' attacking_rim.
    rim_votes: dict[int, dict[str, int]] = defaultdict(lambda: {"left": 0, "right": 0})
    for s in shots:
        if s.shooter_team is None or s.attacking_rim not in ("left", "right"):
            continue
        rim_votes[s.shooter_team][s.attacking_rim] += 1
    for team_id, votes in rim_votes.items():
        if team_id not in by_team:
            continue
        if votes["left"] == 0 and votes["right"] == 0:
            continue
        by_team[team_id].attacking_rim = (
            "left" if votes["left"] >= votes["right"] else "right"
        )

    # Wrong-rim shots = shots whose attacking_rim disagrees with the team's
    # majority. Useful as a sanity check on team-color clustering.
    for s in shots:
        if s.shooter_team is None or s.attacking_rim is None:
            continue
        ts = by_team.get(s.shooter_team)
        if ts is None or ts.attacking_rim is None:
            continue
        if s.attacking_rim != ts.attacking_rim:
            ts.wrong_rim_shots += 1

    # Half-court vs transition: a possession is "half-court" if it both
    # starts and ends on the team's attacking rim's half. If it starts on
    # the opposite half and ends on the attacking half, it's "transition".
    for p in possessions:
        if p.team is None:
            continue
        ts = by_team.get(p.team)
        if ts is None or ts.attacking_rim is None:
            continue
        attacking = ts.attacking_rim
        if p.start_rim == attacking and p.end_rim == attacking:
            ts.half_court_possessions += 1
        elif p.start_rim and p.end_rim and p.start_rim != attacking and p.end_rim == attacking:
            ts.transition_possessions += 1

    return players, by_team


def validate_team_mapping(team_stats: dict[int, TeamStats]) -> dict:
    """Sanity-check the team-cluster + attacking-rim assignment.

    Returns:
      both_teams_same_rim: True if every team that has a known attacking_rim
        has the *same* one. This is the canonical "team labels are
        swapped" failure: with two teams on a court the inferred attacking
        rims should be opposite. If they're equal, the safest guess is
        that the team-color clustering came out backwards.
      high_wrong_rim_team_ids: teams where >=4 shots were attributed and
        more than 40% of those shots point at the OTHER rim. This means
        either the shot detection is mis-attributing shooters or the
        team mapping is noisy enough that it can't be trusted; surfaced
        as a warning, not auto-fixed.
    """
    rims = {ts.team_id: ts.attacking_rim for ts in team_stats.values() if ts.attacking_rim}
    both_same = len(rims) >= 2 and len(set(rims.values())) == 1

    high_wrong: list[int] = []
    for ts in team_stats.values():
        if ts.shots_attempted >= 4 and (ts.wrong_rim_shots / ts.shots_attempted) > 0.4:
            high_wrong.append(ts.team_id)

    return {
        "both_teams_same_rim": bool(both_same),
        "high_wrong_rim_team_ids": high_wrong,
    }
