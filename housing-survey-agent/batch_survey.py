"""Batch survey runner for multiple manufactured housing properties.

Reads a CSV of properties and runs surveys, saving results to JSON.
Can be used with text mode for testing or voice mode for live calls.
"""

import csv
import json
import sys
from pathlib import Path

from voice_agent import HousingSurveyAgent


def load_properties(csv_path: str) -> list[dict]:
    """Load property list from CSV file.

    Expected columns: name, phone, address, city, state, notes
    """
    properties = []
    with open(csv_path) as f:
        reader = csv.DictReader(f)
        for row in reader:
            properties.append(row)
    return properties


def run_batch_survey(csv_path: str, voice_id: str | None = None):
    """Run surveys for all properties in the CSV."""
    properties = load_properties(csv_path)
    print(f"Loaded {len(properties)} properties to survey\n")

    results = []
    for i, prop in enumerate(properties, 1):
        name = prop.get("name", f"Property {i}")
        print(f"\n{'='*60}")
        print(f"Property {i}/{len(properties)}: {name}")
        print(f"{'='*60}")

        agent = HousingSurveyAgent(voice_id=voice_id)
        agent.run_interactive(property_name=name)
        results.append(agent.survey_data.model_dump())

    # Save combined results
    output_path = Path("surveys_output") / "batch_results.json"
    output_path.write_text(json.dumps(results, indent=2))
    print(f"\nBatch results saved to {output_path}")


def export_to_csv(json_dir: str = "surveys_output", output_file: str = "survey_summary.csv"):
    """Export all survey JSON files to a summary CSV."""
    json_path = Path(json_dir)
    surveys = []

    for f in json_path.glob("*.json"):
        if f.name == "batch_results.json":
            continue
        data = json.loads(f.read_text())
        if "data" in data:
            row = {"survey_date": data.get("survey_date", ""), **data["data"]}
            surveys.append(row)

    if not surveys:
        print("No survey files found.")
        return

    fieldnames = list(surveys[0].keys())
    output_path = Path(output_file)
    with open(output_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(surveys)

    print(f"Exported {len(surveys)} surveys to {output_path}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python batch_survey.py survey <properties.csv>")
        print("  python batch_survey.py export [json_dir] [output.csv]")
        sys.exit(1)

    command = sys.argv[1]

    if command == "survey":
        if len(sys.argv) < 3:
            print("Please provide a CSV file path")
            sys.exit(1)
        run_batch_survey(sys.argv[2])
    elif command == "export":
        json_dir = sys.argv[2] if len(sys.argv) > 2 else "surveys_output"
        output = sys.argv[3] if len(sys.argv) > 3 else "survey_summary.csv"
        export_to_csv(json_dir, output)
    else:
        print(f"Unknown command: {command}")
