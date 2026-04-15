"""Learning system for the housing survey agent.

After each survey, the agent evaluates what worked and what didn't,
then stores those learnings. Before future surveys, it loads past
learnings to improve its approach.

Strategies are scored by effectiveness and ranked competitively.
New strategies must outperform existing ones to earn a spot in the
top 20. This ensures the agent keeps its best learnings, not just
the most recent.

Tracks:
- Completion rate (how many data fields were collected)
- Ranked effective strategies (scored 1-10 by impact)
- Ranked failed strategies (scored 1-10 by severity)
- Common objections and successful responses
- Timing patterns (when people are more receptive)
"""

import json
from datetime import datetime
from pathlib import Path

from mistralai import Mistral

MAX_EFFECTIVE_STRATEGIES = 20
MAX_FAILED_STRATEGIES = 20
MAX_OBJECTION_RESPONSES = 15
MAX_GENERAL_TIPS = 15

LEARNINGS_DIR = Path("learnings")
LEARNINGS_FILE = LEARNINGS_DIR / "survey_learnings.json"


def _ensure_dir():
    LEARNINGS_DIR.mkdir(exist_ok=True)


def load_learnings() -> dict:
    """Load accumulated learnings from disk."""
    _ensure_dir()
    if LEARNINGS_FILE.exists():
        return json.loads(LEARNINGS_FILE.read_text())
    return {
        "total_surveys": 0,
        "avg_completion_rate": 0.0,
        "effective_strategies": [],
        "failed_strategies": [],
        "objection_responses": [],
        "topic_difficulty_ranking": {},
        "general_tips": [],
    }


def save_learnings(learnings: dict):
    """Persist learnings to disk."""
    _ensure_dir()
    LEARNINGS_FILE.write_text(json.dumps(learnings, indent=2))


def evaluate_survey(
    client: Mistral,
    conversation: list[dict],
    survey_data: dict,
    property_name: str | None = None,
) -> dict:
    """Use the LLM to evaluate a completed survey and extract learnings.

    Returns a structured evaluation with success/failure analysis.
    """
    # Calculate completion rate
    data_fields = [
        "total_lots", "occupied_lots", "occupancy_rate",
        "lot_rent_min", "lot_rent_max", "lot_rent_average",
        "utilities_included", "additional_fees", "pet_policy",
        "age_restriction", "home_sales_on_site", "waitlist",
        "recent_rent_increase",
    ]
    filled = sum(1 for f in data_fields if survey_data.get(f) is not None)
    completion_rate = filled / len(data_fields)

    conversation_text = "\n".join(
        f"{msg['role'].upper()}: {msg['content']}" for msg in conversation
    )

    eval_prompt = f"""You are analyzing a completed phone survey of a manufactured housing \
community to help improve future surveys.

Property: {property_name or "Unknown"}
Data completion rate: {completion_rate:.0%} ({filled}/{len(data_fields)} fields collected)

Conversation transcript:
{conversation_text}

Collected data:
{json.dumps(survey_data, indent=2)}

Analyze this survey and respond with JSON. IMPORTANT: For each strategy, include an \
"effectiveness_score" from 1-10 that measures how much impact it had on getting useful \
data. Be rigorous - a 10 means the strategy directly unlocked critical information, \
a 1 means it was barely helpful. For failed strategies, score severity 1-10 (10 = caused \
the person to hang up, 1 = minor awkwardness).

{{
  "completion_rate": {completion_rate},
  "outcome": "success" | "partial" | "refused",
  "effective_strategies": [
    {{
      "strategy": "description of what worked",
      "effectiveness_score": 1-10,
      "context": "brief note on why it worked"
    }}
  ],
  "failed_strategies": [
    {{
      "strategy": "description of what failed",
      "severity_score": 1-10,
      "context": "brief note on why it failed"
    }}
  ],
  "objection_responses": [
    {{
      "objection": "what the person said",
      "response": "how the agent handled it",
      "effective": true/false,
      "effectiveness_score": 1-10
    }}
  ],
  "improvement_suggestions": [
    {{
      "tip": "concrete suggestion for next time",
      "priority_score": 1-10
    }}
  ],
  "topic_order_feedback": {{
    "lot_rent": "easy" | "moderate" | "difficult" | "refused",
    "occupancy": "easy" | "moderate" | "difficult" | "refused",
    "utilities": "easy" | "moderate" | "difficult" | "refused",
    "fees": "easy" | "moderate" | "difficult" | "refused",
    "pet_policy": "easy" | "moderate" | "difficult" | "refused",
    "age_restriction": "easy" | "moderate" | "difficult" | "refused",
    "home_sales": "easy" | "moderate" | "difficult" | "refused",
    "rent_increases": "easy" | "moderate" | "difficult" | "refused",
    "waitlist": "easy" | "moderate" | "difficult" | "refused"
  }},
  "respondent_personality": "friendly" | "busy" | "suspicious" | "guarded" | "helpful",
  "call_duration_assessment": "too_short" | "right_length" | "too_long"
}}

Respond with ONLY the JSON."""

    response = client.chat.complete(
        model="mistral-large-latest",
        messages=[{"role": "user", "content": eval_prompt}],
        response_format={"type": "json_object"},
    )

    evaluation = json.loads(response.choices[0].message.content)
    evaluation["property_name"] = property_name
    evaluation["survey_date"] = datetime.now().isoformat()
    return evaluation


def _ranked_insert(existing: list, new_entries: list, max_size: int, score_key: str) -> list:
    """Insert new entries into a ranked list, keeping only the top N by score.

    New entries compete against existing ones. If a new entry scores higher
    than the weakest existing entry, it displaces it. If the list isn't full
    yet, it's added unconditionally.
    """
    combined = existing + new_entries
    # Sort descending by score, so the best are first
    combined.sort(key=lambda x: x.get(score_key, 0), reverse=True)
    return combined[:max_size]


def update_learnings(learnings: dict, evaluation: dict) -> dict:
    """Merge a new evaluation into the accumulated learnings.

    Uses competitive ranking: new strategies only survive if they
    score higher than existing ones. The agent keeps its best
    learnings across all surveys, not just the most recent.
    """
    learnings["total_surveys"] += 1
    n = learnings["total_surveys"]

    # Running average of completion rate
    prev_avg = learnings["avg_completion_rate"]
    new_rate = evaluation.get("completion_rate", 0)
    learnings["avg_completion_rate"] = prev_avg + (new_rate - prev_avg) / n

    survey_context = evaluation.get("property_name", "unknown")
    survey_completion = evaluation.get("completion_rate", 0)

    # --- Effective strategies: ranked by effectiveness_score ---
    new_effective = []
    for s in evaluation.get("effective_strategies", []):
        # Handle both old format (plain string) and new format (dict with score)
        if isinstance(s, str):
            entry = {
                "strategy": s,
                "effectiveness_score": 5,
                "from_survey": survey_context,
                "survey_completion": survey_completion,
            }
        else:
            entry = {
                "strategy": s.get("strategy", str(s)),
                "effectiveness_score": s.get("effectiveness_score", 5),
                "context": s.get("context", ""),
                "from_survey": survey_context,
                "survey_completion": survey_completion,
            }
        new_effective.append(entry)

    learnings["effective_strategies"] = _ranked_insert(
        learnings["effective_strategies"],
        new_effective,
        MAX_EFFECTIVE_STRATEGIES,
        "effectiveness_score",
    )

    # --- Failed strategies: ranked by severity_score (worst failures kept) ---
    new_failed = []
    for s in evaluation.get("failed_strategies", []):
        if isinstance(s, str):
            entry = {
                "strategy": s,
                "severity_score": 5,
                "from_survey": survey_context,
            }
        else:
            entry = {
                "strategy": s.get("strategy", str(s)),
                "severity_score": s.get("severity_score", 5),
                "context": s.get("context", ""),
                "from_survey": survey_context,
            }
        new_failed.append(entry)

    learnings["failed_strategies"] = _ranked_insert(
        learnings["failed_strategies"],
        new_failed,
        MAX_FAILED_STRATEGIES,
        "severity_score",
    )

    # --- Objection responses: keep only effective ones, ranked by score ---
    new_objections = []
    for obj in evaluation.get("objection_responses", []):
        if obj.get("effective", False):
            obj["from_survey"] = survey_context
            obj.setdefault("effectiveness_score", 5)
            new_objections.append(obj)

    learnings["objection_responses"] = _ranked_insert(
        learnings["objection_responses"],
        new_objections,
        MAX_OBJECTION_RESPONSES,
        "effectiveness_score",
    )

    # --- Topic difficulty: running average over time ---
    topic_feedback = evaluation.get("topic_order_feedback", {})
    difficulty_scores = {"easy": 1, "moderate": 2, "difficult": 3, "refused": 4}
    for topic, difficulty in topic_feedback.items():
        score = difficulty_scores.get(difficulty, 2)
        if topic not in learnings["topic_difficulty_ranking"]:
            learnings["topic_difficulty_ranking"][topic] = {
                "total_score": 0, "count": 0, "avg": 0
            }
        entry = learnings["topic_difficulty_ranking"][topic]
        entry["total_score"] += score
        entry["count"] += 1
        entry["avg"] = entry["total_score"] / entry["count"]

    # --- General tips: ranked by priority_score ---
    new_tips = []
    for tip in evaluation.get("improvement_suggestions", []):
        if isinstance(tip, str):
            new_tips.append({"tip": tip, "priority_score": 5, "from_survey": survey_context})
        else:
            new_tips.append({
                "tip": tip.get("tip", str(tip)),
                "priority_score": tip.get("priority_score", 5),
                "from_survey": survey_context,
            })

    learnings["general_tips"] = _ranked_insert(
        learnings["general_tips"],
        new_tips,
        MAX_GENERAL_TIPS,
        "priority_score",
    )

    # Save individual evaluation
    eval_dir = LEARNINGS_DIR / "evaluations"
    eval_dir.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    eval_path = eval_dir / f"eval_{timestamp}.json"
    eval_path.write_text(json.dumps(evaluation, indent=2))

    return learnings


def build_learnings_prompt(learnings: dict) -> str:
    """Build a prompt section that injects past learnings into the system prompt.

    Strategies are presented in ranked order (best first) so the LLM
    prioritizes the highest-impact approaches.
    """
    if learnings["total_surveys"] == 0:
        return ""

    sections = []
    sections.append(
        f"\n\n[LEARNINGS FROM {learnings['total_surveys']} PAST SURVEYS]"
        f"\nAverage data completion rate: {learnings['avg_completion_rate']:.0%}"
    )

    # Top effective strategies (already sorted by score, show top 8)
    if learnings["effective_strategies"]:
        top = learnings["effective_strategies"][:8]
        lines = []
        for s in top:
            score = s.get("effectiveness_score", "?")
            lines.append(f"- [{score}/10] {s['strategy']}")
        sections.append(
            "\nProven strategies (ranked by effectiveness):\n" + "\n".join(lines)
        )

    # Top failures to avoid (already sorted by severity, show top 5)
    if learnings["failed_strategies"]:
        top = learnings["failed_strategies"][:5]
        lines = []
        for s in top:
            score = s.get("severity_score", "?")
            lines.append(f"- [severity {score}/10] {s['strategy']}")
        sections.append(
            "\nApproaches to AVOID (ranked by how badly they backfired):\n"
            + "\n".join(lines)
        )

    # Best objection responses (already sorted by score)
    if learnings["objection_responses"]:
        sections.append("\nBest objection handling responses (ranked):")
        for o in learnings["objection_responses"][:5]:
            score = o.get("effectiveness_score", "?")
            sections.append(
                f'- [{score}/10] When they said: "{o["objection"]}" '
                f'-> Respond with: "{o["response"]}"'
            )

    # Topic ordering by difficulty
    if learnings["topic_difficulty_ranking"]:
        ranked = sorted(
            learnings["topic_difficulty_ranking"].items(),
            key=lambda x: x[1]["avg"],
        )
        easy_first = [t[0] for t in ranked]
        sections.append(
            "\nRecommended topic order (easiest first): "
            + " -> ".join(easy_first)
        )

    # Top tips (already sorted by priority)
    if learnings["general_tips"]:
        top = learnings["general_tips"][:5]
        lines = []
        for t in top:
            tip_text = t.get("tip", t) if isinstance(t, dict) else t
            score = t.get("priority_score", "?") if isinstance(t, dict) else "?"
            lines.append(f"- [{score}/10] {tip_text}")
        sections.append(
            "\nTop tips from past experience (ranked by priority):\n"
            + "\n".join(lines)
        )

    return "\n".join(sections)


def print_learnings_summary(learnings: dict):
    """Print a human-readable summary of accumulated learnings."""
    print("\n" + "=" * 60)
    print("AGENT LEARNING SUMMARY")
    print("=" * 60)
    print(f"Total surveys completed: {learnings['total_surveys']}")
    print(f"Average completion rate: {learnings['avg_completion_rate']:.0%}")

    if learnings["effective_strategies"]:
        print(f"\nTop effective strategies ({len(learnings['effective_strategies'])} stored):")
        for s in learnings["effective_strategies"][:10]:
            score = s.get("effectiveness_score", "?")
            source = s.get("from_survey", "?")
            print(f"  [{score}/10] {s['strategy']}  (from: {source})")

    if learnings["failed_strategies"]:
        print(f"\nStrategies to avoid ({len(learnings['failed_strategies'])} stored):")
        for s in learnings["failed_strategies"][:10]:
            score = s.get("severity_score", "?")
            print(f"  [severity {score}/10] {s['strategy']}")

    if learnings["topic_difficulty_ranking"]:
        print("\nTopic difficulty (1=easy, 4=refused):")
        ranked = sorted(
            learnings["topic_difficulty_ranking"].items(),
            key=lambda x: x[1]["avg"],
        )
        for topic, data in ranked:
            print(f"  {topic}: {data['avg']:.1f} (n={data['count']})")

    if learnings["objection_responses"]:
        print(f"\nBest objection responses ({len(learnings['objection_responses'])} stored):")
        for o in learnings["objection_responses"][:5]:
            score = o.get("effectiveness_score", "?")
            print(f'  [{score}/10] "{o["objection"]}" -> "{o["response"]}"')

    if learnings["general_tips"]:
        print(f"\nTop tips ({len(learnings['general_tips'])} stored):")
        for tip in learnings["general_tips"][:5]:
            if isinstance(tip, dict):
                score = tip.get("priority_score", "?")
                print(f"  [{score}/10] {tip.get('tip', tip)}")
            else:
                print(f"  * {tip}")

    # Show the score threshold to beat
    if learnings["effective_strategies"]:
        weakest = learnings["effective_strategies"][-1]
        print(f"\nMin score to enter top strategies: "
              f"{weakest.get('effectiveness_score', '?')}/10")

    print("=" * 60)
