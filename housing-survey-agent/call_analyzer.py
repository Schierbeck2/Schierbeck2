"""Analyze real human survey calls to train the agent.

Takes recorded calls (MP3/WAV from Google Voice or other sources),
transcribes them, extracts survey data and conversation strategies,
and feeds the learnings into the agent's learning system.

This lets the agent learn from your assistant's real calls before
it ever makes its own.

Usage:
  # Analyze a single call recording
  python call_analyzer.py recording.mp3 --property "Sunset MHP"

  # Analyze a folder of recordings
  python call_analyzer.py ./recordings/ --batch

  # Show what the agent has learned from analyzed calls
  python call_analyzer.py --summary
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from mistralai import Mistral

from learning import (
    load_learnings,
    save_learnings,
    evaluate_survey,
    update_learnings,
    build_learnings_prompt,
    print_learnings_summary,
)
from survey_config import PropertySurveyData

load_dotenv()

ANALYZED_DIR = Path("learnings") / "analyzed_calls"


def get_client() -> Mistral:
    api_key = os.environ.get("MISTRAL_API_KEY")
    if not api_key:
        raise ValueError("MISTRAL_API_KEY environment variable required")
    return Mistral(api_key=api_key)


def transcribe_call(client: Mistral, audio_path: str) -> str:
    """Transcribe a call recording using Voxtral STT."""
    path = Path(audio_path)
    print(f"  Transcribing {path.name} ({path.stat().st_size / 1024:.0f} KB)...")

    with open(audio_path, "rb") as f:
        audio_data = f.read()

    response = client.audio.transcriptions.complete(
        model="voxtral-mini-latest",
        file={
            "file_name": path.name,
            "content": audio_data,
        },
    )
    return response.text


def identify_speakers(client: Mistral, transcript: str) -> list[dict]:
    """Use the LLM to separate a raw transcript into speaker turns.

    Google Voice recordings are single-channel, so the raw transcript
    is a wall of text. The LLM identifies who is speaking based on
    context (the surveyor asks questions, the property manager answers).
    """
    response = client.chat.complete(
        model="mistral-large-latest",
        messages=[{
            "role": "user",
            "content": f"""This is a transcript of a phone survey call between a surveyor \
and a manufactured housing community manager. The transcript has no speaker labels.

Separate this into a conversation with speaker labels. The surveyor is the one asking \
questions about lot rent, occupancy, utilities, etc. The property manager is answering.

Transcript:
{transcript}

Respond with JSON:
{{
  "conversation": [
    {{"role": "surveyor", "content": "what they said"}},
    {{"role": "property_manager", "content": "what they said"}},
    ...
  ],
  "confidence": "high" | "medium" | "low",
  "notes": "any issues with the transcript"
}}

Respond with ONLY the JSON.""",
        }],
        response_format={"type": "json_object"},
    )

    result = json.loads(response.choices[0].message.content)
    return result


def extract_data_from_call(client: Mistral, conversation: list[dict]) -> dict:
    """Extract structured survey data from the analyzed conversation."""
    conv_text = "\n".join(
        f"{m['role'].upper()}: {m['content']}" for m in conversation
    )

    response = client.chat.complete(
        model="mistral-large-latest",
        messages=[{
            "role": "user",
            "content": f"""Extract survey data from this manufactured housing community \
phone call. This is a real call between a human surveyor and a property manager.

Conversation:
{conv_text}

Extract these fields (null if not mentioned):
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


def analyze_strategies(client: Mistral, conversation: list[dict],
                       survey_data: dict, property_name: str) -> dict:
    """Deep analysis of what the human surveyor did well and poorly.

    This is the key function - it learns the human's techniques so
    the agent can replicate them.
    """
    conv_text = "\n".join(
        f"{m['role'].upper()}: {m['content']}" for m in conversation
    )

    data_fields = [
        "total_lots", "occupied_lots", "occupancy_rate",
        "lot_rent_min", "lot_rent_max", "lot_rent_average",
        "utilities_included", "additional_fees", "pet_policy",
        "age_restriction", "home_sales_on_site", "waitlist",
        "recent_rent_increase",
    ]
    filled = sum(1 for f in data_fields if survey_data.get(f) is not None)
    completion_rate = filled / len(data_fields)

    response = client.chat.complete(
        model="mistral-large-latest",
        messages=[{
            "role": "user",
            "content": f"""You are analyzing a REAL phone survey call made by an experienced \
human surveyor to a manufactured housing community. Your goal is to extract the surveyor's \
techniques so an AI agent can learn from them.

Property: {property_name}
Data completion: {completion_rate:.0%} ({filled}/{len(data_fields)} fields)

Conversation:
{conv_text}

Analyze the surveyor's approach and respond with JSON. Score each strategy 1-10 \
based on how directly it contributed to getting useful information. Be generous \
with scores for real human techniques that actually worked - these are proven in \
the field.

{{
  "completion_rate": {completion_rate},
  "outcome": "success" | "partial" | "refused",
  "effective_strategies": [
    {{
      "strategy": "Specific technique the surveyor used, in enough detail to replicate",
      "effectiveness_score": 1-10,
      "context": "Why it worked in this call"
    }}
  ],
  "failed_strategies": [
    {{
      "strategy": "What didn't work or caused friction",
      "severity_score": 1-10,
      "context": "Why it failed"
    }}
  ],
  "objection_responses": [
    {{
      "objection": "What the property manager pushed back on",
      "response": "How the surveyor handled it (exact phrasing if possible)",
      "effective": true/false,
      "effectiveness_score": 1-10
    }}
  ],
  "improvement_suggestions": [
    {{
      "tip": "What the surveyor could have done better",
      "priority_score": 1-10
    }}
  ],
  "opening_technique": "How did they introduce themselves and the purpose?",
  "transition_techniques": [
    "How did they move between topics naturally?"
  ],
  "rapport_building": [
    "Any rapport-building moments (small talk, empathy, humor)?"
  ],
  "closing_technique": "How did they end the call?",
  "topic_order_feedback": {{
    "lot_rent": "easy" | "moderate" | "difficult" | "refused" | "not_asked",
    "occupancy": "easy" | "moderate" | "difficult" | "refused" | "not_asked",
    "utilities": "easy" | "moderate" | "difficult" | "refused" | "not_asked",
    "fees": "easy" | "moderate" | "difficult" | "refused" | "not_asked",
    "pet_policy": "easy" | "moderate" | "difficult" | "refused" | "not_asked",
    "age_restriction": "easy" | "moderate" | "difficult" | "refused" | "not_asked",
    "home_sales": "easy" | "moderate" | "difficult" | "refused" | "not_asked",
    "rent_increases": "easy" | "moderate" | "difficult" | "refused" | "not_asked",
    "waitlist": "easy" | "moderate" | "difficult" | "refused" | "not_asked"
  }},
  "actual_topic_order": [
    "The order topics were actually covered in this call"
  ],
  "respondent_personality": "friendly" | "busy" | "suspicious" | "guarded" | "helpful",
  "call_duration_assessment": "too_short" | "right_length" | "too_long",
  "overall_assessment": "1-2 sentence summary of the surveyor's performance"
}}

Respond with ONLY the JSON.""",
        }],
        response_format={"type": "json_object"},
    )
    result = json.loads(response.choices[0].message.content)
    result["property_name"] = property_name
    result["survey_date"] = datetime.now().isoformat()
    result["source"] = "human_call_recording"
    return result


def analyze_recording(audio_path: str, property_name: str | None = None) -> dict:
    """Full pipeline: transcribe -> identify speakers -> extract data -> analyze.

    Returns a complete analysis with survey data and learnings.
    """
    client = get_client()
    path = Path(audio_path)
    name = property_name or path.stem

    print(f"\nAnalyzing: {path.name}")
    print(f"Property: {name}")
    print("-" * 40)

    # 1. Transcribe
    transcript = transcribe_call(client, audio_path)
    print(f"  Transcript length: {len(transcript)} chars")

    # 2. Identify speakers
    print("  Identifying speakers...")
    speaker_result = identify_speakers(client, transcript)
    conversation = speaker_result.get("conversation", [])
    confidence = speaker_result.get("confidence", "unknown")
    print(f"  Speaker ID confidence: {confidence}")
    print(f"  Turns identified: {len(conversation)}")

    # Map to standard role names for the learning system
    standardized = []
    for turn in conversation:
        role = turn["role"]
        if role in ("surveyor", "assistant", "agent"):
            standardized.append({"role": "assistant", "content": turn["content"]})
        else:
            standardized.append({"role": "user", "content": turn["content"]})

    # 3. Extract survey data
    print("  Extracting survey data...")
    survey_data = extract_data_from_call(client, conversation)

    # 4. Analyze strategies
    print("  Analyzing strategies...")
    evaluation = analyze_strategies(client, conversation, survey_data, name)

    # 5. Update learnings
    learnings = load_learnings()
    learnings = update_learnings(learnings, evaluation)
    save_learnings(learnings)

    # 6. Save full analysis
    ANALYZED_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_name = "".join(c if c.isalnum() or c in "-_ " else "" for c in name)
    analysis = {
        "audio_file": str(path),
        "property_name": name,
        "analyzed_at": datetime.now().isoformat(),
        "source": "human_call_recording",
        "transcript": transcript,
        "speaker_confidence": confidence,
        "conversation": conversation,
        "survey_data": survey_data,
        "evaluation": evaluation,
    }
    output_path = ANALYZED_DIR / f"{safe_name}_{timestamp}.json"
    output_path.write_text(json.dumps(analysis, indent=2))

    # Print summary
    _print_analysis_summary(evaluation, survey_data)

    return analysis


def analyze_batch(directory: str, property_names: dict | None = None):
    """Analyze all audio files in a directory.

    property_names is an optional dict mapping filename -> property name.
    If not provided, the filename (without extension) is used.
    """
    audio_dir = Path(directory)
    audio_files = []
    for ext in ("*.mp3", "*.wav", "*.m4a", "*.ogg", "*.flac"):
        audio_files.extend(audio_dir.glob(ext))

    if not audio_files:
        print(f"No audio files found in {directory}")
        return

    audio_files.sort()
    print(f"Found {len(audio_files)} recordings to analyze\n")

    names = property_names or {}
    for i, path in enumerate(audio_files, 1):
        print(f"\n{'='*60}")
        print(f"[{i}/{len(audio_files)}]")
        name = names.get(path.name, path.stem)
        try:
            analyze_recording(str(path), property_name=name)
        except Exception as e:
            print(f"  Error analyzing {path.name}: {e}")

    # Final summary
    learnings = load_learnings()
    print(f"\n\n{'='*60}")
    print(f"BATCH ANALYSIS COMPLETE")
    print(f"{'='*60}")
    print_learnings_summary(learnings)


def _print_analysis_summary(evaluation: dict, survey_data: dict):
    """Print a summary of a single call analysis."""
    print(f"\n  Results:")
    print(f"    Outcome: {evaluation.get('outcome', '?')}")
    print(f"    Completion: {evaluation.get('completion_rate', 0):.0%}")
    print(f"    Respondent: {evaluation.get('respondent_personality', '?')}")

    if evaluation.get("effective_strategies"):
        print(f"    Top strategies learned:")
        for s in evaluation["effective_strategies"][:3]:
            score = s.get("effectiveness_score", "?")
            print(f"      [{score}/10] {s.get('strategy', s)}")

    if evaluation.get("opening_technique"):
        print(f"    Opening: {evaluation['opening_technique']}")

    if evaluation.get("actual_topic_order"):
        order = evaluation["actual_topic_order"]
        print(f"    Topic order: {' -> '.join(order[:6])}")

    # Key data points collected
    rent = survey_data.get("lot_rent_min") or survey_data.get("lot_rent_max")
    lots = survey_data.get("total_lots")
    occ = survey_data.get("occupancy_rate")
    if rent:
        print(f"    Lot rent: ${rent}")
    if lots:
        print(f"    Total lots: {lots}")
    if occ:
        print(f"    Occupancy: {occ:.0%}")


# ---------------------------------------------------------------------------
# Google Voice helpers
# ---------------------------------------------------------------------------

def list_google_voice_tips():
    """Print instructions for recording and exporting Google Voice calls."""
    print("""
RECORDING CALLS ON GOOGLE VOICE
================================

1. ENABLE CALL RECORDING:
   - Open Google Voice (voice.google.com)
   - Settings (gear icon) -> Calls
   - Turn on "Incoming call options"

2. RECORD A CALL:
   - During any call, press 4 on the keypad
   - Both parties hear "This call is now being recorded"
   - Press 4 again to stop recording
   - NOTE: Your assistant should let the property manager know
     the call may be recorded for quality purposes at the start

3. FIND RECORDINGS:
   - Recordings appear in the Google Voice inbox (Voicemail tab)
   - Each recording shows the phone number and timestamp

4. DOWNLOAD RECORDINGS:
   - Click on the recording in Google Voice
   - Click the three-dot menu -> Download
   - Saves as MP3

5. BATCH EXPORT:
   - Use Google Takeout (takeout.google.com)
   - Select "Google Voice" -> include "Calls"
   - Export all recordings at once as a ZIP

6. FEED TO THE ANALYZER:
   # Single recording
   python call_analyzer.py recording.mp3 --property "Pine Valley Estates"

   # Folder of recordings
   python call_analyzer.py ./google_voice_exports/ --batch

TIPS:
   - Name the downloaded files after the property for easier tracking
   - Record both successful and unsuccessful calls - the agent
     learns from failures too
   - Even partial calls are useful (someone who hangs up teaches
     the agent what NOT to do)
""")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Analyze real survey calls to train the agent"
    )
    parser.add_argument(
        "path", nargs="?",
        help="Audio file or directory of recordings to analyze",
    )
    parser.add_argument(
        "--property", "-p",
        help="Property name for the recording",
    )
    parser.add_argument(
        "--batch", "-b", action="store_true",
        help="Analyze all audio files in the directory",
    )
    parser.add_argument(
        "--summary", action="store_true",
        help="Show what the agent has learned from analyzed calls",
    )
    parser.add_argument(
        "--google-voice-help", action="store_true",
        help="Show instructions for recording/exporting Google Voice calls",
    )
    args = parser.parse_args()

    if args.google_voice_help:
        list_google_voice_tips()
        return

    if args.summary:
        learnings = load_learnings()
        print_learnings_summary(learnings)
        return

    if not args.path:
        parser.print_help()
        return

    if args.batch or Path(args.path).is_dir():
        analyze_batch(args.path)
    else:
        analyze_recording(args.path, property_name=args.property)


if __name__ == "__main__":
    main()
