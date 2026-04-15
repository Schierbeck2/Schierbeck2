"""End-to-end orchestrator for manufactured housing surveys.

Usage:
  "I'm appraising property 1234"
  ->  Find all MH communities within 10 miles / same county
  ->  Filter out recently surveyed properties
  ->  Queue calls in sequence
  ->  For each: dial, survey, review, save to DB
  ->  Report results

This ties together: database, twilio_caller, call_server,
call_reviewer, and learning.
"""

import json
import os
import time
from datetime import datetime, timedelta

from dotenv import load_dotenv
from mistralai import Mistral

from database import (
    find_survey_targets,
    get_property_by_id,
    get_recent_surveys,
    save_survey_to_db,
    ensure_rent_table,
    COL_PROPERTY_ID,
    COL_NAME,
    COL_PHONE,
    COL_COUNTY,
    COL_STATE,
)
from twilio_caller import initiate_call, wait_for_call_completion, get_call_recordings
from call_reviewer import review_call
from learning import (
    load_learnings,
    save_learnings,
    evaluate_survey,
    update_learnings,
)
from survey_config import PropertySurveyData

load_dotenv()

# How recently a property must have been surveyed to skip it
SKIP_IF_SURVEYED_WITHIN_DAYS = 180


def run_survey_campaign(
    subject_property_id: int,
    radius_miles: float = 10.0,
    include_county: bool = True,
    skip_recently_surveyed: bool = True,
    webhook_base_url: str | None = None,
    dry_run: bool = False,
):
    """Run a full survey campaign for a subject property.

    1. Look up the subject property
    2. Find all nearby MH communities
    3. Filter out recently surveyed ones
    4. Call each one, survey, review, save
    5. Update learnings
    6. Print final report
    """
    webhook_url = webhook_base_url or os.environ.get(
        "WEBHOOK_BASE_URL", "http://localhost:8000"
    )
    client = Mistral(api_key=os.environ.get("MISTRAL_API_KEY", ""))

    # 1. Look up subject property
    subject = get_property_by_id(subject_property_id)
    if not subject:
        print(f"Error: Property {subject_property_id} not found in database")
        return

    print("=" * 60)
    print("MANUFACTURED HOUSING SURVEY CAMPAIGN")
    print("=" * 60)
    print(f"Subject Property: {subject.get(COL_NAME)}")
    print(f"Location: {subject.get(COL_COUNTY)} County, {subject.get(COL_STATE)}")
    print(f"Search radius: {radius_miles} miles")
    print(f"Include full county: {include_county}")
    print()

    # 2. Find targets
    print("Finding survey targets...")
    targets = find_survey_targets(
        subject_property_id, radius_miles, include_county
    )
    print(f"Found {len(targets)} nearby MH communities")

    # 3. Filter recently surveyed
    if skip_recently_surveyed:
        cutoff = datetime.now() - timedelta(days=SKIP_IF_SURVEYED_WITHIN_DAYS)
        filtered = []
        for prop in targets:
            pid = prop[COL_PROPERTY_ID]
            recent = get_recent_surveys(pid, limit=1)
            if recent:
                last_date = recent[0].get("survey_date")
                if last_date and last_date > cutoff:
                    print(f"  Skipping {prop.get(COL_NAME)} (surveyed {last_date.date()})")
                    continue
            filtered.append(prop)
        targets = filtered
        print(f"{len(targets)} properties need surveying")

    # Filter out properties with no phone number
    no_phone = [p for p in targets if not p.get(COL_PHONE)]
    targets = [p for p in targets if p.get(COL_PHONE)]
    if no_phone:
        print(f"  {len(no_phone)} properties skipped (no phone number)")

    print(f"\nReady to call {len(targets)} properties")
    print()

    if not targets:
        print("No properties to survey.")
        return

    if dry_run:
        print("DRY RUN - would call these properties:")
        for i, prop in enumerate(targets, 1):
            print(f"  {i}. {prop.get(COL_NAME)} - {prop.get(COL_PHONE)}")
        return

    # Ensure rent table exists
    ensure_rent_table()

    # 4. Call each property
    results = []
    learnings = load_learnings()

    for i, prop in enumerate(targets, 1):
        pid = prop[COL_PROPERTY_ID]
        name = prop.get(COL_NAME, f"Property {pid}")
        phone = prop[COL_PHONE]

        print(f"\n[{i}/{len(targets)}] Calling {name} at {phone}...")

        try:
            # Initiate the call
            call_sid = initiate_call(
                to_number=phone,
                webhook_base_url=webhook_url,
                property_id=pid,
                property_name=name,
            )
            print(f"  Call SID: {call_sid}")

            # Wait for call to complete
            call_result = wait_for_call_completion(call_sid)
            status = call_result.get("status", "unknown")
            duration = call_result.get("duration", 0)
            print(f"  Status: {status} | Duration: {duration}s")

            if status != "completed":
                results.append({
                    "property_id": pid,
                    "property_name": name,
                    "status": status,
                    "duration": duration,
                    "saved": False,
                })
                continue

            # Get session data from the call server
            import urllib.request
            session_url = f"{webhook_url}/session/{call_sid}"
            resp = urllib.request.urlopen(session_url)
            session = json.loads(resp.read())

            conversation = session.get("conversation", [])
            if not conversation:
                print("  No conversation recorded")
                results.append({
                    "property_id": pid,
                    "property_name": name,
                    "status": "no_conversation",
                    "saved": False,
                })
                continue

            # Extract survey data
            survey_data = extract_survey_data(client, conversation)

            # Get recording URL
            recordings = get_call_recordings(call_sid)
            recording_url = recordings[0]["url"] if recordings else None

            # 5. Review the call
            print("  Reviewing call quality...")
            review = review_call(client, conversation, survey_data)
            print(f"  Quality: {review.quality_score:.0%} | "
                  f"Completeness: {review.data_completeness:.0%} | "
                  f"Decision: {review.recommendation}")

            if review.flags:
                for flag in review.flags[:3]:
                    print(f"    ! {flag}")

            # Save to database
            call_meta = {
                "recording_url": recording_url,
                "duration_seconds": duration,
                "quality_score": review.quality_score,
                "auto_approved": review.auto_approved,
            }

            if review.recommendation != "discard":
                survey_id = save_survey_to_db(pid, survey_data, conversation, call_meta)
                print(f"  Saved to database (survey_id: {survey_id}, "
                      f"auto_approved: {review.auto_approved})")
                saved = True
            else:
                print("  Discarded (insufficient data quality)")
                saved = False

            # Update learnings
            evaluation = evaluate_survey(client, conversation, survey_data, name)
            learnings = update_learnings(learnings, evaluation)

            results.append({
                "property_id": pid,
                "property_name": name,
                "status": "completed",
                "duration": duration,
                "quality_score": review.quality_score,
                "completeness": review.data_completeness,
                "recommendation": review.recommendation,
                "auto_approved": review.auto_approved,
                "saved": saved,
                "lot_rent": survey_data.get("lot_rent_min"),
                "occupancy_rate": survey_data.get("occupancy_rate"),
            })

            # Brief pause between calls
            if i < len(targets):
                time.sleep(3)

        except Exception as e:
            print(f"  Error: {e}")
            results.append({
                "property_id": pid,
                "property_name": name,
                "status": "error",
                "error": str(e),
                "saved": False,
            })

    # Save learnings
    save_learnings(learnings)

    # 6. Final report
    print_campaign_report(subject, targets, results)

    return results


def extract_survey_data(client: Mistral, conversation: list[dict]) -> dict:
    """Extract structured survey data from a conversation."""
    conversation_text = "\n".join(
        f"{m['role'].upper()}: {m['content']}" for m in conversation
    )

    response = client.chat.complete(
        model="mistral-large-latest",
        messages=[{
            "role": "user",
            "content": f"""Extract survey data from this conversation.

{conversation_text}

Respond with JSON containing these fields (null if not mentioned):
property_name, contact_name, contact_title,
total_lots (int), occupied_lots (int), occupancy_rate (decimal),
lot_rent_min (float), lot_rent_max (float), lot_rent_average (float),
utilities_included, additional_fees, water_sewer_cost, trash_cost,
pet_policy, age_restriction, home_sales_on_site (bool),
rent_increase_history, recent_rent_increase, waitlist (bool), notes

Respond with ONLY valid JSON.""",
        }],
        response_format={"type": "json_object"},
    )
    return json.loads(response.choices[0].message.content)


def print_campaign_report(subject: dict, targets: list, results: list):
    """Print a summary report of the campaign."""
    print("\n" + "=" * 60)
    print("CAMPAIGN REPORT")
    print("=" * 60)
    print(f"Subject: {subject.get(COL_NAME)}")
    print(f"Properties targeted: {len(targets)}")
    print()

    completed = [r for r in results if r["status"] == "completed"]
    saved = [r for r in results if r.get("saved")]
    auto_approved = [r for r in results if r.get("auto_approved")]
    needs_review = [r for r in saved if not r.get("auto_approved")]
    no_answer = [r for r in results if r["status"] in ("no-answer", "busy")]
    errors = [r for r in results if r["status"] == "error"]

    print(f"Calls completed:    {len(completed)}/{len(targets)}")
    print(f"Data saved:         {len(saved)}")
    print(f"  Auto-approved:    {len(auto_approved)}")
    print(f"  Needs review:     {len(needs_review)}")
    print(f"No answer/busy:     {len(no_answer)}")
    print(f"Errors:             {len(errors)}")

    if completed:
        avg_quality = sum(r.get("quality_score", 0) for r in completed) / len(completed)
        avg_completeness = sum(r.get("completeness", 0) for r in completed) / len(completed)
        print(f"\nAvg quality score:  {avg_quality:.0%}")
        print(f"Avg completeness:   {avg_completeness:.0%}")

    # Rent summary
    rents = [r["lot_rent"] for r in completed if r.get("lot_rent")]
    if rents:
        print(f"\nLot Rent Summary:")
        print(f"  Low:     ${min(rents):,.0f}")
        print(f"  High:    ${max(rents):,.0f}")
        print(f"  Average: ${sum(rents)/len(rents):,.0f}")

    # Properties needing follow-up
    if no_answer:
        print(f"\nNeed callback ({len(no_answer)}):")
        for r in no_answer:
            print(f"  - {r['property_name']} ({r['status']})")

    if needs_review:
        print(f"\nNeed manual review ({len(needs_review)}):")
        for r in needs_review:
            print(f"  - {r['property_name']} "
                  f"(quality: {r.get('quality_score', 0):.0%})")

    print("=" * 60)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Run a manufactured housing survey campaign"
    )
    parser.add_argument(
        "--subject-property", "-s", type=int, required=True,
        help="Property ID of the property you're appraising",
    )
    parser.add_argument(
        "--radius", "-r", type=float, default=10.0,
        help="Search radius in miles (default: 10)",
    )
    parser.add_argument(
        "--no-county", action="store_true",
        help="Don't include full county, only radius search",
    )
    parser.add_argument(
        "--webhook-url", "-w",
        help="Base URL of the call server (default: http://localhost:8000)",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="List properties that would be called without calling them",
    )
    args = parser.parse_args()

    run_survey_campaign(
        subject_property_id=args.subject_property,
        radius_miles=args.radius,
        include_county=not args.no_county,
        webhook_base_url=args.webhook_url,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    main()
