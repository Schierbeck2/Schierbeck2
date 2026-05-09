"""Roll up tracker output + shot events into team and per-player stats."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, asdict, field
from typing import Optional

from .events import ShotEvent
from .tracker import Detection


@dataclass
class PlayerStats:
    track_id: int
    team: Optional[int]
    display_name: str
    frames_seen: int = 0
    seconds_on_court: float = 0.0
    shots_attempted: int = 0
    shots_made: int = 0
    shots_by_zone: dict[str, dict[str, int]] = field(
        default_factory=lambda: defaultdict(lambda: {"att": 0, "make": 0})
    )

    @property
    def fg_pct(self) -> Optional[float]:
        if self.shots_attempted == 0:
            return None
        return self.shots_made / self.shots_attempted

    def to_dict(self) -> dict:
        d = asdict(self)
        d["fg_pct"] = self.fg_pct
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

    @property
    def fg_pct(self) -> Optional[float]:
        if self.shots_attempted == 0:
            return None
        return self.shots_made / self.shots_attempted

    def to_dict(self) -> dict:
        d = asdict(self)
        d["fg_pct"] = self.fg_pct
        d["shots_by_zone"] = {z: dict(v) for z, v in self.shots_by_zone.items()}
        return d


def aggregate(
    detections: list[Detection],
    shots: list[ShotEvent],
    teams: dict[int, int],
    fps: float,
    name_overrides: dict[int, str] | None = None,
) -> tuple[dict[int, PlayerStats], dict[int, TeamStats]]:
    name_overrides = name_overrides or {}
    players: dict[int, PlayerStats] = {}

    # On-court time per player.
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
            frames_seen=count,
            seconds_on_court=count / fps if fps else 0.0,
        )

    # Shooting.
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

    # Roll up to teams.
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
        for zone, zb in ps.shots_by_zone.items():
            tzb = ts.shots_by_zone[zone]
            tzb["att"] += zb["att"]
            tzb["make"] += zb["make"]

    return players, by_team
