"""Manufactured Housing Survey Voice Agent using Mistral's voice stack.

Architecture:
  Voxtral Realtime (STT) -> Mistral Large (LLM) -> Voxtral TTS (TTS)

This agent conducts phone surveys of manufactured housing communities
to collect rent and occupancy information.
"""

import base64
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from mistralai import Mistral

from survey_config import SYSTEM_PROMPT, SURVEY_QUESTIONS, PropertySurveyData
from learning import (
    load_learnings,
    save_learnings,
    evaluate_survey,
    update_learnings,
    build_learnings_prompt,
    print_learnings_summary,
)

load_dotenv()


class HousingSurveyAgent:
    """Voice agent that surveys manufactured housing properties."""

    def __init__(self, voice_id: str | None = None):
        api_key = os.environ.get("MISTRAL_API_KEY")
        if not api_key:
            raise ValueError("MISTRAL_API_KEY environment variable is required")

        self.client = Mistral(api_key=api_key)
        self.voice_id = voice_id
        self.conversation_history: list[dict] = []
        self.survey_data = PropertySurveyData()
        self.current_question_index = 0

        # Learning system
        self.learnings = load_learnings()
        self.learnings_prompt = build_learnings_prompt(self.learnings)

        # Output directories
        self.output_dir = Path("surveys_output")
        self.output_dir.mkdir(exist_ok=True)
        self.audio_dir = Path("recordings")
        self.audio_dir.mkdir(exist_ok=True)

    def transcribe_audio(self, audio_path: str) -> str:
        """Transcribe audio using Voxtral Realtime STT."""
        with open(audio_path, "rb") as f:
            audio_data = f.read()

        response = self.client.audio.transcriptions.complete(
            model="voxtral-mini-latest",
            file={
                "file_name": os.path.basename(audio_path),
                "content": audio_data,
            },
        )
        return response.text

    def transcribe_audio_stream(self, audio_path: str):
        """Stream transcription for lower latency."""
        with open(audio_path, "rb") as f:
            audio_data = f.read()

        stream = self.client.audio.transcriptions.stream(
            model="voxtral-mini-latest",
            file={
                "file_name": os.path.basename(audio_path),
                "content": audio_data,
            },
        )
        full_text = ""
        for chunk in stream:
            if hasattr(chunk, "text") and chunk.text:
                full_text += chunk.text
                print(chunk.text, end="", flush=True)
        print()
        return full_text

    def generate_response(self, user_message: str) -> str:
        """Use Mistral LLM to generate the next survey response."""
        self.conversation_history.append({"role": "user", "content": user_message})

        # Build context about what data we still need
        collected = {k: v for k, v in self.survey_data.model_dump().items() if v is not None}
        remaining_topics = [
            q["topic"]
            for q in SURVEY_QUESTIONS[self.current_question_index :]
            if q["required_data"]
        ]

        context = (
            f"\n\n[Survey Progress]\n"
            f"Data collected so far: {json.dumps(collected, indent=2)}\n"
            f"Remaining topics to cover: {remaining_topics}\n"
            f"Guide the conversation toward the next uncovered topic naturally."
        )

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT + self.learnings_prompt + context},
            *self.conversation_history,
        ]

        response = self.client.chat.complete(
            model="mistral-large-latest",
            messages=messages,
        )

        assistant_message = response.choices[0].message.content
        self.conversation_history.append({"role": "assistant", "content": assistant_message})
        return assistant_message

    def extract_survey_data(self) -> PropertySurveyData:
        """Use the LLM to extract structured survey data from the conversation."""
        conversation_text = "\n".join(
            f"{msg['role'].upper()}: {msg['content']}" for msg in self.conversation_history
        )

        extraction_prompt = f"""Analyze this phone survey conversation with a manufactured \
housing community and extract structured data.

Conversation:
{conversation_text}

Extract the following fields (use null if not mentioned):
- property_name: Name of the community
- contact_name: Name of person spoken to
- contact_title: Their title/role
- total_lots: Total number of lots (integer)
- occupied_lots: Number of occupied lots (integer)
- occupancy_rate: Occupancy percentage (decimal, e.g. 0.95)
- lot_rent_min: Minimum monthly lot rent (float)
- lot_rent_max: Maximum monthly lot rent (float)
- lot_rent_average: Average lot rent if stated (float)
- utilities_included: What utilities are included in rent
- additional_fees: Any additional fees
- water_sewer_cost: Water/sewer cost if separate
- trash_cost: Trash cost if separate
- pet_policy: Pet policy details
- age_restriction: Age restriction details
- home_sales_on_site: Whether they sell homes on-site (boolean)
- rent_increase_history: Rent increase information
- waitlist: Whether there's a waitlist (boolean)
- recent_rent_increase: Details on recent rent increases
- notes: Any other notable information

Respond with ONLY valid JSON matching the schema above."""

        response = self.client.chat.complete(
            model="mistral-large-latest",
            messages=[{"role": "user", "content": extraction_prompt}],
            response_format={"type": "json_object"},
        )

        data = json.loads(response.choices[0].message.content)
        self.survey_data = PropertySurveyData(**data)
        return self.survey_data

    def synthesize_speech(self, text: str, output_path: str | None = None) -> bytes:
        """Convert text to speech using Voxtral TTS."""
        kwargs = {
            "model": "voxtral-mini-tts-2603",
            "input": text,
            "response_format": "mp3",
        }
        if self.voice_id:
            kwargs["voice_id"] = self.voice_id

        response = self.client.audio.speech.complete(**kwargs)
        audio_bytes = base64.b64decode(response.audio_data)

        if output_path:
            Path(output_path).write_bytes(audio_bytes)

        return audio_bytes

    def save_survey_results(self, property_name: str | None = None):
        """Save survey results to JSON."""
        name = property_name or self.survey_data.property_name or "unknown_property"
        safe_name = "".join(c if c.isalnum() or c in "-_ " else "" for c in name)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{safe_name}_{timestamp}.json"

        output = {
            "survey_date": datetime.now().isoformat(),
            "property_name": name,
            "data": self.survey_data.model_dump(),
            "conversation": self.conversation_history,
        }

        output_path = self.output_dir / filename
        output_path.write_text(json.dumps(output, indent=2))
        print(f"Survey results saved to {output_path}")
        return output_path

    def run_interactive(self, property_name: str | None = None):
        """Run the survey agent in interactive text mode (for testing without audio)."""
        print("=" * 60)
        print("Manufactured Housing Survey Agent")
        print("=" * 60)
        if property_name:
            self.survey_data.property_name = property_name
            print(f"Surveying: {property_name}")
        print("Type responses as the property manager. Type 'quit' to end.\n")

        # Generate opening message
        opening = self.generate_response(
            "[Call connected. The property manager has answered the phone.]"
        )
        print(f"\nAgent: {opening}\n")

        while True:
            user_input = input("Property Manager: ").strip()
            if not user_input:
                continue
            if user_input.lower() in ("quit", "exit", "q"):
                break

            response = self.generate_response(user_input)
            print(f"\nAgent: {response}\n")

            # Check if we've covered the closing topic
            if "thank" in response.lower() and self.current_question_index >= len(
                SURVEY_QUESTIONS
            ) - 1:
                print("[Survey appears complete]")
                break

            # Advance question index based on covered topics
            self._advance_question_index()

        # Extract, evaluate, learn, and save
        print("\nExtracting survey data...")
        self.extract_survey_data()
        self.save_survey_results(property_name)
        self._learn_from_survey(property_name)
        self._print_summary()

    def run_voice(self, property_name: str | None = None):
        """Run the survey agent with full voice (STT + TTS).

        Requires a microphone and speakers. Records user audio,
        transcribes it, generates a response, and speaks it back.
        """
        try:
            import sounddevice as sd
            import numpy as np
        except ImportError:
            print("Voice mode requires 'sounddevice' and 'numpy'.")
            print("Install with: pip install sounddevice numpy")
            sys.exit(1)

        print("=" * 60)
        print("Manufactured Housing Survey Agent (Voice Mode)")
        print("=" * 60)
        if property_name:
            self.survey_data.property_name = property_name
            print(f"Surveying: {property_name}")
        print("Press Enter to start/stop recording. Type 'quit' to end.\n")

        # Generate and speak opening
        opening = self.generate_response(
            "[Call connected. The property manager has answered the phone.]"
        )
        print(f"\nAgent: {opening}")
        self._speak(opening)

        sample_rate = 16000
        recording_counter = 0

        while True:
            input("\n[Press Enter to start recording...]")
            user_check = input("(or type 'quit' to end): ").strip()
            if user_check.lower() in ("quit", "exit", "q"):
                break

            print("Recording... Press Enter to stop.")
            frames = []
            recording = True

            def audio_callback(indata, frame_count, time_info, status):
                if recording:
                    frames.append(indata.copy())

            stream = sd.InputStream(
                samplerate=sample_rate, channels=1, callback=audio_callback
            )
            stream.start()
            input()
            recording = False
            stream.stop()
            stream.close()

            if not frames:
                print("No audio recorded.")
                continue

            # Save recording
            audio_data = np.concatenate(frames)
            recording_counter += 1
            rec_path = self.audio_dir / f"recording_{recording_counter}.wav"

            import wave
            with wave.open(str(rec_path), "w") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(sample_rate)
                wf.writeframes((audio_data * 32767).astype(np.int16).tobytes())

            # Transcribe
            print("Transcribing...")
            transcript = self.transcribe_audio(str(rec_path))
            print(f"You said: {transcript}")

            # Generate and speak response
            response = self.generate_response(transcript)
            print(f"\nAgent: {response}")
            self._speak(response)

            self._advance_question_index()

        # Extract, evaluate, learn, and save
        print("\nExtracting survey data...")
        self.extract_survey_data()
        self.save_survey_results(property_name)
        self._learn_from_survey(property_name)
        self._print_summary()

    def _learn_from_survey(self, property_name: str | None = None):
        """Evaluate the survey and update learnings for future improvement."""
        print("\nEvaluating survey performance...")
        evaluation = evaluate_survey(
            self.client,
            self.conversation_history,
            self.survey_data.model_dump(),
            property_name,
        )

        outcome = evaluation.get("outcome", "unknown")
        rate = evaluation.get("completion_rate", 0)
        print(f"  Outcome: {outcome} | Completion: {rate:.0%}")

        if evaluation.get("improvement_suggestions"):
            print("  Suggestions for next time:")
            for tip in evaluation["improvement_suggestions"][:3]:
                print(f"    -> {tip}")

        self.learnings = update_learnings(self.learnings, evaluation)
        save_learnings(self.learnings)
        print(f"  Learnings updated ({self.learnings['total_surveys']} surveys total)")

    def _speak(self, text: str):
        """Synthesize and play speech."""
        try:
            import sounddevice as sd
            import numpy as np

            audio_bytes = self.synthesize_speech(text)
            # Save temp file and play
            temp_path = self.audio_dir / "temp_response.mp3"
            temp_path.write_bytes(audio_bytes)
            print("[Playing audio response...]")
            # For actual playback, you'd decode MP3 and play through sounddevice
            # This is a simplified version - in production use ffmpeg or pydub
        except Exception as e:
            print(f"[Audio playback not available: {e}]")

    def _advance_question_index(self):
        """Move to next question based on what data we've collected."""
        while self.current_question_index < len(SURVEY_QUESTIONS) - 1:
            q = SURVEY_QUESTIONS[self.current_question_index]
            if not q["required_data"]:
                self.current_question_index += 1
                continue
            # Check if any required data for this question has been discussed
            # (LLM will handle this naturally, we just track progress)
            break

    def _print_summary(self):
        """Print a summary of collected survey data."""
        print("\n" + "=" * 60)
        print("SURVEY SUMMARY")
        print("=" * 60)
        data = self.survey_data.model_dump()
        for key, value in data.items():
            if value is not None:
                label = key.replace("_", " ").title()
                print(f"  {label}: {value}")
        print("=" * 60)


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Manufactured Housing Survey Voice Agent")
    parser.add_argument("--property", "-p", help="Property name being surveyed")
    parser.add_argument(
        "--voice",
        action="store_true",
        help="Enable voice mode (requires microphone/speakers)",
    )
    parser.add_argument("--voice-id", help="Mistral voice ID for TTS")
    parser.add_argument(
        "--learnings",
        action="store_true",
        help="Show what the agent has learned from past surveys",
    )
    args = parser.parse_args()

    if args.learnings:
        learnings = load_learnings()
        print_learnings_summary(learnings)
        return

    agent = HousingSurveyAgent(voice_id=args.voice_id)

    if args.voice:
        agent.run_voice(property_name=args.property)
    else:
        agent.run_interactive(property_name=args.property)


if __name__ == "__main__":
    main()
