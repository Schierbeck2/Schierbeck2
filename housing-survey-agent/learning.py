"""Learning system for the housing survey agent.

After each survey, the agent evaluates what worked and what didn't,
then stores those learnings. Before future surveys, it loads past
learnings to improve its approach.

Tracks:
- Completion rate (how many data fields were collected)
- Effective phrases and conversation strategies
- Common objections and successful responses
- Timing patterns (when people are more receptive)
"""

import json
from datetime import datetime
from pathlib import Path

from mistralai import Mistral


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
        "best_opening_lines": [],
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

Analyze this survey and respond with JSON containing:
{{
  "completion_rate": {completion_rate},
  "outcome": "success" | "partial" | "refused",
  "effective_strategies": [
    // List specific phrases or approaches that worked well
    // e.g. "Asking about utilities right after lot rent created a natural flow"
  ],
  "failed_strategies": [
    // Approaches that didn't work or caused friction
    // e.g. "Asking about rent increases too early made them defensive"
  ],
  "objection_responses": [
    // Any objections encountered and how they were handled
    {{
      "objection": "what the person said",
      "response": "how the agent handled it",
      "effective": true/false
    }}
  ],
  "best_moments": [
    // Specific exchanges that went particularly well
  ],
  "improvement_suggestions": [
    // Concrete suggestions for next time
  ],
  "topic_order_feedback": {{
    // For each topic, was the ordering effective?
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


def update_learnings(learnings: dict, evaluation: dict) -> dict:
    """Merge a new evaluation into the accumulated learnings."""
    learnings["total_surveys"] += 1
    n = learnings["total_surveys"]

    # Running average of completion rate
    prev_avg = learnings["avg_completion_rate"]
    new_rate = evaluation.get("completion_rate", 0)
    learnings["avg_completion_rate"] = prev_avg + (new_rate - prev_avg) / n

    # Append effective strategies (keep top 20 most recent)
    for strategy in evaluation.get("effective_strategies", []):
        entry = {"strategy": strategy, "from_survey": evaluation.get("property_name")}
        learnings["effective_strategies"].append(entry)
    learnings["effective_strategies"] = learnings["effective_strategies"][-20:]

    # Append failed strategies (keep top 20)
    for strategy in evaluation.get("failed_strategies", []):
        entry = {"strategy": strategy, "from_survey": evaluation.get("property_name")}
        learnings["failed_strategies"].append(entry)
    learnings["failed_strategies"] = learnings["failed_strategies"][-20:]

    # Append objection responses (keep top 15)
    for obj in evaluation.get("objection_responses", []):
        learnings["objection_responses"].append(obj)
    learnings["objection_responses"] = learnings["objection_responses"][-15:]

    # Track topic difficulty over time
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

    # Append improvement suggestions as general tips (keep top 15)
    for tip in evaluation.get("improvement_suggestions", []):
        learnings["general_tips"].append(tip)
    learnings["general_tips"] = learnings["general_tips"][-15:]

    # Save individual evaluation too
    eval_dir = LEARNINGS_DIR / "evaluations"
    eval_dir.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    eval_path = eval_dir / f"eval_{timestamp}.json"
    eval_path.write_text(json.dumps(evaluation, indent=2))

    return learnings


def build_learnings_prompt(learnings: dict) -> str:
    """Build a prompt section that injects past learnings into the system prompt.

    This is what makes the agent smarter over time.
    """
    if learnings["total_surveys"] == 0:
        return ""

    sections = []
    sections.append(
        f"\n\n[LEARNINGS FROM {learnings['total_surveys']} PAST SURVEYS]"
        f"\nAverage data completion rate: {learnings['avg_completion_rate']:.0%}"
    )

    # What works
    if learnings["effective_strategies"]:
        strategies = [s["strategy"] for s in learnings["effective_strategies"][-8:]]
        sections.append(
            "\nStrategies that have worked well:\n"
            + "\n".join(f"- {s}" for s in strategies)
        )

    # What to avoid
    if learnings["failed_strategies"]:
        fails = [s["strategy"] for s in learnings["failed_strategies"][-5:]]
        sections.append(
            "\nApproaches to AVOID (these caused problems):\n"
            + "\n".join(f"- {s}" for s in fails)
        )

    # Objection handling
    effective_objections = [
        o for o in learnings["objection_responses"] if o.get("effective")
    ]
    if effective_objections:
        sections.append("\nSuccessful objection handling examples:")
        for o in effective_objections[-5:]:
            sections.append(
                f'- When they said: "{o["objection"]}" '
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

    # General tips
    if learnings["general_tips"]:
        tips = learnings["general_tips"][-5:]
        sections.append(
            "\nTips from past experience:\n"
            + "\n".join(f"- {t}" for t in tips)
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
        print("\nTop effective strategies:")
        for s in learnings["effective_strategies"][-5:]:
            print(f"  + {s['strategy']}")

    if learnings["failed_strategies"]:
        print("\nStrategies to avoid:")
        for s in learnings["failed_strategies"][-5:]:
            print(f"  - {s['strategy']}")

    if learnings["topic_difficulty_ranking"]:
        print("\nTopic difficulty (1=easy, 4=refused):")
        ranked = sorted(
            learnings["topic_difficulty_ranking"].items(),
            key=lambda x: x[1]["avg"],
        )
        for topic, data in ranked:
            print(f"  {topic}: {data['avg']:.1f} (n={data['count']})")

    if learnings["general_tips"]:
        print("\nRecent tips:")
        for tip in learnings["general_tips"][-5:]:
            print(f"  * {tip}")

    print("=" * 60)
