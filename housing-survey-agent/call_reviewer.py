"""Automated call quality review.

After each call completes, the reviewer evaluates:
- Data completeness (did we get rent + occupancy?)
- Data plausibility (are the numbers realistic?)
- Conversation quality (was the respondent cooperative?)
- Red flags (suspicious answers, hostility, confusion)

Calls are auto-approved if they pass all checks. Flagged calls
get queued for human review before data is saved to the database.
"""

import json

from mistralai import Mistral

from survey_config import PropertySurveyData


# Thresholds
MIN_FIELDS_FOR_AUTO_APPROVE = 4  # Must have at least this many data fields
MIN_QUALITY_SCORE = 0.6  # 0-1 scale
PLAUSIBLE_LOT_RENT_RANGE = (100, 2500)  # Monthly, USD
PLAUSIBLE_LOT_COUNT_RANGE = (5, 2000)
PLAUSIBLE_OCCUPANCY_RANGE = (0.3, 1.0)


class CallReview:
    """Result of an automated call review."""

    def __init__(self):
        self.auto_approved: bool = False
        self.quality_score: float = 0.0
        self.data_completeness: float = 0.0
        self.flags: list[str] = []
        self.plausibility_issues: list[str] = []
        self.summary: str = ""
        self.recommendation: str = ""  # "approve", "review", "discard"

    def to_dict(self) -> dict:
        return {
            "auto_approved": self.auto_approved,
            "quality_score": self.quality_score,
            "data_completeness": self.data_completeness,
            "flags": self.flags,
            "plausibility_issues": self.plausibility_issues,
            "summary": self.summary,
            "recommendation": self.recommendation,
        }


def check_data_completeness(survey_data: dict) -> tuple[float, list[str]]:
    """Check how complete the survey data is."""
    critical_fields = ["lot_rent_min", "lot_rent_max", "total_lots", "occupied_lots"]
    important_fields = ["utilities_included", "pet_policy", "age_restriction"]
    nice_to_have = ["additional_fees", "home_sales_on_site", "waitlist",
                     "recent_rent_increase"]

    flags = []
    score = 0.0
    total_weight = 0.0

    # Critical fields (weight 3 each)
    for field in critical_fields:
        total_weight += 3
        if survey_data.get(field) is not None:
            score += 3
        else:
            flags.append(f"Missing critical field: {field}")

    # Important fields (weight 2 each)
    for field in important_fields:
        total_weight += 2
        if survey_data.get(field) is not None:
            score += 2

    # Nice to have (weight 1 each)
    for field in nice_to_have:
        total_weight += 1
        if survey_data.get(field) is not None:
            score += 1

    completeness = score / total_weight if total_weight > 0 else 0
    return completeness, flags


def check_data_plausibility(survey_data: dict) -> list[str]:
    """Check if the collected data makes sense."""
    issues = []

    # Lot rent range
    rent_min = survey_data.get("lot_rent_min")
    rent_max = survey_data.get("lot_rent_max")
    if rent_min is not None:
        if rent_min < PLAUSIBLE_LOT_RENT_RANGE[0]:
            issues.append(f"Lot rent min ${rent_min} seems too low")
        if rent_min > PLAUSIBLE_LOT_RENT_RANGE[1]:
            issues.append(f"Lot rent min ${rent_min} seems too high")
    if rent_max is not None:
        if rent_max > PLAUSIBLE_LOT_RENT_RANGE[1]:
            issues.append(f"Lot rent max ${rent_max} seems too high")
    if rent_min and rent_max and rent_min > rent_max:
        issues.append(f"Lot rent min (${rent_min}) > max (${rent_max})")

    # Lot count
    total = survey_data.get("total_lots")
    occupied = survey_data.get("occupied_lots")
    if total is not None:
        if total < PLAUSIBLE_LOT_COUNT_RANGE[0]:
            issues.append(f"Total lots ({total}) seems too low")
        if total > PLAUSIBLE_LOT_COUNT_RANGE[1]:
            issues.append(f"Total lots ({total}) seems too high")
    if occupied is not None and total is not None:
        if occupied > total:
            issues.append(f"Occupied lots ({occupied}) > total lots ({total})")

    # Occupancy rate
    rate = survey_data.get("occupancy_rate")
    if rate is not None:
        if rate < PLAUSIBLE_OCCUPANCY_RANGE[0]:
            issues.append(f"Occupancy rate ({rate:.0%}) seems unusually low")
        if rate > 1.0:
            issues.append(f"Occupancy rate ({rate:.0%}) > 100%")

    return issues


def ai_review(client: Mistral, conversation: list[dict],
              survey_data: dict) -> dict:
    """Use the LLM to evaluate conversation quality and flag concerns."""
    conversation_text = "\n".join(
        f"{m['role'].upper()}: {m['content']}" for m in conversation
    )

    prompt = f"""You are a quality reviewer for automated phone surveys of manufactured \
housing communities. Review this call and provide an assessment.

Conversation:
{conversation_text}

Extracted data:
{json.dumps(survey_data, indent=2)}

Evaluate and respond with JSON:
{{
  "quality_score": 0.0-1.0,  // Overall call quality
  "respondent_cooperative": true/false,
  "data_seems_reliable": true/false,
  "red_flags": [
    // Any concerns: "respondent seemed confused about lot count",
    // "answers contradicted each other", "may have been giving
    // made-up numbers", "respondent was hostile", etc.
  ],
  "data_corrections": {{
    // If you notice the extraction got something wrong based on
    // the conversation, suggest corrections:
    // "lot_rent_min": 450  // they said $450 not $45
  }},
  "summary": "Brief 1-2 sentence assessment of the call"
}}

Respond with ONLY the JSON."""

    response = client.chat.complete(
        model="mistral-large-latest",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
    )
    return json.loads(response.choices[0].message.content)


def review_call(client: Mistral, conversation: list[dict],
                survey_data: dict) -> CallReview:
    """Run the full review pipeline on a completed call.

    Returns a CallReview with auto_approved=True if the call
    passes all checks, or flags/recommendation if it needs
    human review.
    """
    review = CallReview()

    # 1. Data completeness
    completeness, completeness_flags = check_data_completeness(survey_data)
    review.data_completeness = completeness
    review.flags.extend(completeness_flags)

    # 2. Data plausibility
    plausibility_issues = check_data_plausibility(survey_data)
    review.plausibility_issues = plausibility_issues
    review.flags.extend(plausibility_issues)

    # 3. AI review
    ai_result = ai_review(client, conversation, survey_data)
    review.quality_score = ai_result.get("quality_score", 0)
    review.summary = ai_result.get("summary", "")

    if ai_result.get("red_flags"):
        review.flags.extend(ai_result["red_flags"])

    if not ai_result.get("data_seems_reliable", True):
        review.flags.append("AI reviewer: data may not be reliable")

    if not ai_result.get("respondent_cooperative", True):
        review.flags.append("AI reviewer: respondent was not cooperative")

    # Apply any corrections the AI suggested
    corrections = ai_result.get("data_corrections", {})
    if corrections:
        review.flags.append(f"AI suggested corrections: {json.dumps(corrections)}")

    # 4. Decision
    filled_count = sum(
        1 for v in survey_data.values() if v is not None
    )
    has_enough_data = filled_count >= MIN_FIELDS_FOR_AUTO_APPROVE
    has_good_quality = review.quality_score >= MIN_QUALITY_SCORE
    has_no_plausibility_issues = len(plausibility_issues) == 0
    has_no_red_flags = not ai_result.get("red_flags")

    if has_enough_data and has_good_quality and has_no_plausibility_issues and has_no_red_flags:
        review.auto_approved = True
        review.recommendation = "approve"
    elif not has_enough_data or review.quality_score < 0.3:
        review.recommendation = "discard"
    else:
        review.recommendation = "review"

    return review
