"""LLM coaching notes via the Claude API.

We feed Claude (a) the structured stats we trust and (b) a small set of
sampled frames around each event, and ask for actionable coaching feedback.

Prompt caching is used on the (large, mostly-stable) system prompt so that
generating per-player narratives after the team report is cheap.
"""

from __future__ import annotations

import base64
import io
import json
from dataclasses import dataclass
from typing import Optional

from .config import SETTINGS


COACH_SYSTEM = """You are an experienced basketball coach giving feedback to
a team that just reviewed footage of a single game. You receive:

  - Aggregate stats from a computer-vision tracker (player on-court time,
    shot attempts, shot zones, approximate makes/misses).
  - Possession data: how many possessions each player and team had, and
    average/median possession duration.
  - Rebound data: offensive vs defensive rebounds per player, attached to
    the missed shot they followed.
  - Pose-derived shooting-form metrics for shot attempts (elbow angle, knee
    bend, release height ratio, balance offset).
  - A small set of sampled frames around shot events.

Important: the stats come from heuristic tracking and may be imperfect.
Make/miss labels are approximate, possession is inferred from ball-to-player
proximity, and offensive vs defensive rebound classification depends on the
team-color clustering. Comment qualitatively when the numbers are small; do
not over-claim. When in doubt, say so.

Your output should be:
  - Concrete and actionable (drills, cues, decisions to make differently).
  - Specific to what is visible in the frames and consistent with the stats.
  - Encouraging in tone, but honest. Avoid generic advice.

Format the response as JSON matching the schema the user supplies."""


@dataclass
class CoachOutput:
    team_summary: str
    team_strengths: list[str]
    team_areas_to_improve: list[str]
    per_player: dict[str, dict]   # keyed by display_name
    raw: str


def _encode_image_jpeg(image_bgr) -> str:
    import cv2

    ok, buf = cv2.imencode(".jpg", image_bgr, [int(cv2.IMWRITE_JPEG_QUALITY), 70])
    if not ok:
        return ""
    return base64.standard_b64encode(buf.tobytes()).decode("ascii")


def _build_user_blocks(
    team_stats: list[dict],
    player_stats: list[dict],
    shot_events: list[dict],
    form_metrics: list[dict],
    possessions: list[dict],
    rebounds: list[dict],
    sample_frames_b64: list[str],
) -> list[dict]:
    schema = {
        "team_summary": "string",
        "team_strengths": ["string"],
        "team_areas_to_improve": ["string"],
        "per_player": {
            "<display_name>": {
                "summary": "string",
                "strengths": ["string"],
                "improvements": ["string"],
                "shooting_form_notes": "string",
            }
        },
    }
    payload = {
        "instructions": (
            "Write a coaching report for this team and each named player. "
            "Be specific. Reference shot zones, makes/misses, on-court time, "
            "possession time, offensive vs defensive rebounding, half-court "
            "vs transition possessions, attacking-rim direction, and any "
            "clear pose-form patterns. Match the schema exactly."
        ),
        "schema": schema,
        "team_stats": team_stats,
        "player_stats": player_stats,
        "shot_events": shot_events,
        "form_metrics": form_metrics,
        "possessions_summary": _summarize_possessions(possessions, team_stats),
        "rebounds": rebounds,
    }
    blocks: list[dict] = [{"type": "text", "text": json.dumps(payload, indent=2)}]
    for b64 in sample_frames_b64[:8]:  # cap to keep tokens reasonable
        if not b64:
            continue
        blocks.append(
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/jpeg",
                    "data": b64,
                },
            }
        )
    return blocks


def generate_report(
    team_stats: list[dict],
    player_stats: list[dict],
    shot_events: list[dict],
    form_metrics: list[dict],
    possessions: list[dict],
    rebounds: list[dict],
    sample_frames_bgr: list,
) -> CoachOutput:
    """Call Claude to produce the coaching report."""
    if not SETTINGS.anthropic_api_key:
        return _offline_fallback(team_stats, player_stats, shot_events, rebounds)

    try:
        import anthropic
    except ImportError:
        return _offline_fallback(team_stats, player_stats, shot_events, rebounds)

    client = anthropic.Anthropic(api_key=SETTINGS.anthropic_api_key)
    sample_b64 = [_encode_image_jpeg(f) for f in sample_frames_bgr]

    msg = client.messages.create(
        model=SETTINGS.coach_model,
        max_tokens=2000,
        system=[
            {
                "type": "text",
                "text": COACH_SYSTEM,
                "cache_control": {"type": "ephemeral"},
            }
        ],
        messages=[
            {
                "role": "user",
                "content": _build_user_blocks(
                    team_stats, player_stats, shot_events,
                    form_metrics, possessions, rebounds, sample_b64,
                ),
            }
        ],
    )
    text = "".join(
        block.text for block in msg.content if getattr(block, "type", "") == "text"
    )
    return _parse(text)


def _parse(text: str) -> CoachOutput:
    try:
        # Tolerate code-fenced JSON.
        cleaned = text.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.strip("`")
            if cleaned.lower().startswith("json"):
                cleaned = cleaned[4:].strip()
        data = json.loads(cleaned)
    except Exception:
        return CoachOutput(
            team_summary=text[:1000],
            team_strengths=[],
            team_areas_to_improve=[],
            per_player={},
            raw=text,
        )
    return CoachOutput(
        team_summary=data.get("team_summary", ""),
        team_strengths=list(data.get("team_strengths", []) or []),
        team_areas_to_improve=list(data.get("team_areas_to_improve", []) or []),
        per_player=dict(data.get("per_player", {}) or {}),
        raw=text,
    )


def _summarize_possessions(
    possessions: list[dict], team_stats: list[dict] | None = None,
) -> dict:
    if not possessions:
        return {"count": 0}
    durations = [p.get("duration_s", 0.0) for p in possessions]
    by_team: dict[int, int] = {}
    for p in possessions:
        t = p.get("team")
        if t is None:
            continue
        by_team[t] = by_team.get(t, 0) + 1
    summary = {
        "count": len(possessions),
        "avg_duration_s": sum(durations) / max(1, len(durations)),
        "median_duration_s": sorted(durations)[len(durations) // 2] if durations else 0,
        "by_team": by_team,
    }
    if team_stats:
        summary["per_team_breakdown"] = [
            {
                "team": ts.get("team_id"),
                "attacking_rim": ts.get("attacking_rim"),
                "half_court_possessions": ts.get("half_court_possessions"),
                "transition_possessions": ts.get("transition_possessions"),
                "wrong_rim_shots": ts.get("wrong_rim_shots"),
            }
            for ts in team_stats
        ]
    return summary


def _offline_fallback(
    team_stats: list[dict],
    player_stats: list[dict],
    shot_events: list[dict],
    rebounds: list[dict] | None = None,
) -> CoachOutput:
    """Produce a minimal heuristic report when no API key is configured."""
    msg = (
        "No ANTHROPIC_API_KEY configured. Showing a heuristic summary based "
        "purely on the tracker output."
    )
    per_player: dict[str, dict] = {}
    for ps in player_stats:
        name = ps.get("display_name", f"Player #{ps.get('track_id')}")
        att = ps.get("shots_attempted", 0)
        made = ps.get("shots_made", 0)
        oreb = ps.get("offensive_rebounds", 0)
        dreb = ps.get("defensive_rebounds", 0)
        poss = ps.get("possessions", 0)
        per_player[name] = {
            "summary": (
                f"On-court time {ps.get('seconds_on_court', 0):.0f}s, "
                f"attempts {att}, makes {made}, possessions {poss}, "
                f"OREB {oreb}, DREB {dreb}."
            ),
            "strengths": [],
            "improvements": [],
            "shooting_form_notes": "",
        }
    return CoachOutput(
        team_summary=msg,
        team_strengths=[],
        team_areas_to_improve=[],
        per_player=per_player,
        raw="",
    )
