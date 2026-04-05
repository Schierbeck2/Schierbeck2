"""FastAPI webhook server that handles Twilio call flow.

Twilio calls this server at each turn of the conversation.
The flow per turn:
  1. /call/start    - Call connects, play the opening TTS audio
  2. /call/respond  - Receive recorded speech, transcribe, generate
                      next response, play it back, record again
  3. /call/status   - Track call lifecycle events
  4. /call/recording - Receive final recording URL

The server maintains per-call conversation state in memory.
For production, use Redis or a database for state.
"""

import base64
import json
import os
import tempfile
import urllib.request
from datetime import datetime

from dotenv import load_dotenv
from fastapi import FastAPI, Form, Query, Request, Response
from mistralai import Mistral

from learning import build_learnings_prompt, load_learnings
from survey_config import SYSTEM_PROMPT, PropertySurveyData

load_dotenv()

app = FastAPI(title="Housing Survey Call Server")

# In-memory call state (use Redis in production)
call_sessions: dict[str, dict] = {}

# Mistral client (shared across requests)
mistral_client = Mistral(api_key=os.environ.get("MISTRAL_API_KEY", ""))

# Load learnings once at startup
learnings = load_learnings()
learnings_prompt = build_learnings_prompt(learnings)


def twiml_say_and_record(audio_url: str, call_sid: str) -> str:
    """Generate TwiML that plays audio then records the response."""
    webhook_base = os.environ.get("WEBHOOK_BASE_URL", "http://localhost:8000")
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Play>{audio_url}</Play>
    <Record
        action="{webhook_base}/call/respond?call_sid={call_sid}"
        method="POST"
        maxLength="60"
        timeout="5"
        playBeep="false"
        trim="trim-silence"
    />
    <Say>I didn't catch that. Thank you for your time, goodbye.</Say>
    <Hangup/>
</Response>"""


def twiml_closing(audio_url: str) -> str:
    """Generate TwiML that plays closing audio and hangs up."""
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Play>{audio_url}</Play>
    <Pause length="1"/>
    <Hangup/>
</Response>"""


def twiml_voicemail_hangup() -> str:
    """Hang up if we detect a voicemail machine."""
    return """<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Hangup/>
</Response>"""


def synthesize_to_url(text: str, call_sid: str, turn: int) -> str:
    """Synthesize speech and save to a temp file served by the app.

    Returns a URL path that Twilio can fetch.
    """
    response = mistral_client.audio.speech.complete(
        model="voxtral-mini-tts-2603",
        input=text,
        response_format="mp3",
    )
    audio_bytes = base64.b64decode(response.audio_data)

    # Save to temp directory served as static files
    audio_dir = os.path.join(tempfile.gettempdir(), "survey_audio")
    os.makedirs(audio_dir, exist_ok=True)
    filename = f"{call_sid}_turn_{turn}.mp3"
    filepath = os.path.join(audio_dir, filename)

    with open(filepath, "wb") as f:
        f.write(audio_bytes)

    webhook_base = os.environ.get("WEBHOOK_BASE_URL", "http://localhost:8000")
    return f"{webhook_base}/audio/{filename}"


def transcribe_recording(recording_url: str) -> str:
    """Download a Twilio recording and transcribe with Voxtral."""
    # Download the recording
    response = urllib.request.urlopen(recording_url)
    audio_data = response.read()

    result = mistral_client.audio.transcriptions.complete(
        model="voxtral-mini-latest",
        file={
            "file_name": "recording.wav",
            "content": audio_data,
        },
    )
    return result.text


def generate_agent_response(session: dict, user_message: str) -> str:
    """Generate the agent's next response using the LLM."""
    session["conversation"].append({"role": "user", "content": user_message})

    # Build context
    collected = {
        k: v for k, v in session.get("survey_data", {}).items() if v is not None
    }

    context = (
        f"\n\n[Survey Progress]\n"
        f"Data collected so far: {json.dumps(collected, indent=2)}\n"
        f"Turn {session['turn']} of conversation.\n"
        f"Guide the conversation toward uncovered topics naturally."
    )

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT + learnings_prompt + context},
        *session["conversation"],
    ]

    response = mistral_client.chat.complete(
        model="mistral-large-latest",
        messages=messages,
    )

    assistant_message = response.choices[0].message.content
    session["conversation"].append({"role": "assistant", "content": assistant_message})
    return assistant_message


def check_survey_complete(session: dict) -> bool:
    """Ask the LLM if we've collected enough data to wrap up."""
    if session["turn"] < 4:
        return False

    conversation_text = "\n".join(
        f"{m['role']}: {m['content']}" for m in session["conversation"]
    )

    response = mistral_client.chat.complete(
        model="mistral-large-latest",
        messages=[{
            "role": "user",
            "content": f"""Based on this survey conversation, have we collected enough
data to be useful? We need at minimum: lot rent and either occupancy or total lots.

Conversation:
{conversation_text}

Respond with ONLY "yes" or "no".""",
        }],
    )
    return response.choices[0].message.content.strip().lower() == "yes"


# --------------------------------------------------------------------------
# Static file serving for TTS audio
# --------------------------------------------------------------------------

from fastapi.responses import FileResponse


@app.get("/audio/{filename}")
async def serve_audio(filename: str):
    """Serve synthesized TTS audio files to Twilio."""
    audio_dir = os.path.join(tempfile.gettempdir(), "survey_audio")
    filepath = os.path.join(audio_dir, filename)
    if os.path.exists(filepath):
        return FileResponse(filepath, media_type="audio/mpeg")
    return Response(status_code=404)


# --------------------------------------------------------------------------
# Twilio webhook endpoints
# --------------------------------------------------------------------------

@app.post("/call/start")
async def call_start(
    CallSid: str = Form(""),
    AnsweredBy: str = Form(""),
    property_id: int = Query(0),
    property_name: str = Query(""),
):
    """Called when Twilio connects the outbound call."""

    # Hang up on voicemail
    if AnsweredBy in ("machine_start", "machine_end_beep", "machine_end_silence", "fax"):
        call_sessions[CallSid] = {
            "status": "voicemail",
            "property_id": property_id,
            "property_name": property_name,
        }
        return Response(content=twiml_voicemail_hangup(), media_type="application/xml")

    # Initialize session
    session = {
        "property_id": property_id,
        "property_name": property_name,
        "conversation": [],
        "survey_data": {},
        "turn": 0,
        "started_at": datetime.now().isoformat(),
        "status": "in_progress",
    }
    call_sessions[CallSid] = session

    # Generate opening line
    opening = generate_agent_response(
        session,
        "[Call connected. The property manager has answered the phone.]",
    )
    session["turn"] = 1

    # Synthesize and play
    audio_url = synthesize_to_url(opening, CallSid, 0)
    twiml = twiml_say_and_record(audio_url, CallSid)

    return Response(content=twiml, media_type="application/xml")


@app.post("/call/respond")
async def call_respond(
    CallSid: str = Form(""),
    RecordingUrl: str = Form(""),
    RecordingSid: str = Form(""),
    RecordingDuration: str = Form("0"),
    call_sid: str = Query(""),
):
    """Called after each recording. Transcribe, respond, record again."""
    sid = call_sid or CallSid
    session = call_sessions.get(sid)

    if not session:
        return Response(
            content=twiml_closing(
                synthesize_to_url("Thank you, goodbye.", sid, 999)
            ),
            media_type="application/xml",
        )

    # Handle empty recording (silence / no response)
    if int(RecordingDuration) < 1:
        session["silence_count"] = session.get("silence_count", 0) + 1
        if session["silence_count"] >= 2:
            closing = "I'm sorry, I can't hear you. I'll try calling back later. Thank you."
            audio_url = synthesize_to_url(closing, sid, session["turn"])
            session["status"] = "no_response"
            return Response(
                content=twiml_closing(audio_url), media_type="application/xml"
            )
        prompt = "Are you still there? I was asking about your community."
        audio_url = synthesize_to_url(prompt, sid, session["turn"])
        return Response(
            content=twiml_say_and_record(audio_url, sid),
            media_type="application/xml",
        )

    session["silence_count"] = 0

    # Transcribe the recording
    transcript = transcribe_recording(RecordingUrl)

    # Check if the person wants to end the call
    end_phrases = ["goodbye", "not interested", "don't call", "stop calling",
                    "take me off", "no thank you", "hang up"]
    if any(phrase in transcript.lower() for phrase in end_phrases):
        closing = "I understand. Thank you for your time. Have a great day."
        audio_url = synthesize_to_url(closing, sid, session["turn"])
        session["status"] = "ended_by_respondent"
        return Response(
            content=twiml_closing(audio_url), media_type="application/xml"
        )

    # Generate response
    response_text = generate_agent_response(session, transcript)
    session["turn"] += 1

    # Check if survey is complete
    if check_survey_complete(session) or session["turn"] > 15:
        # Generate a natural closing
        closing = generate_agent_response(
            session,
            "[The survey is complete. Wrap up and thank them warmly.]",
        )
        audio_url = synthesize_to_url(closing, sid, session["turn"])
        session["status"] = "completed"
        return Response(
            content=twiml_closing(audio_url), media_type="application/xml"
        )

    # Continue conversation
    audio_url = synthesize_to_url(response_text, sid, session["turn"])
    return Response(
        content=twiml_say_and_record(audio_url, sid), media_type="application/xml"
    )


@app.post("/call/status")
async def call_status(
    CallSid: str = Form(""),
    CallStatus: str = Form(""),
    CallDuration: str = Form("0"),
    AnsweredBy: str = Form(""),
):
    """Track call lifecycle events from Twilio."""
    session = call_sessions.get(CallSid, {})
    session["last_status"] = CallStatus
    session["duration_seconds"] = int(CallDuration) if CallDuration else 0
    session["answered_by"] = AnsweredBy

    if CallStatus in ("completed", "busy", "no-answer", "canceled", "failed"):
        session["ended_at"] = datetime.now().isoformat()
        session.setdefault("status", CallStatus)

    return Response(status_code=200)


@app.post("/call/recording")
async def call_recording(
    CallSid: str = Form(""),
    RecordingUrl: str = Form(""),
    RecordingSid: str = Form(""),
    RecordingDuration: str = Form("0"),
):
    """Receive the final call recording URL from Twilio."""
    session = call_sessions.get(CallSid, {})
    session["recording_url"] = RecordingUrl
    session["recording_sid"] = RecordingSid
    return Response(status_code=200)


# --------------------------------------------------------------------------
# API endpoints for the orchestrator
# --------------------------------------------------------------------------

@app.get("/session/{call_sid}")
async def get_session(call_sid: str):
    """Get the current state of a call session."""
    session = call_sessions.get(call_sid)
    if not session:
        return {"error": "Session not found"}
    return session


@app.get("/sessions")
async def list_sessions():
    """List all call sessions."""
    return {
        sid: {
            "property_name": s.get("property_name"),
            "status": s.get("status"),
            "turn": s.get("turn", 0),
            "duration": s.get("duration_seconds", 0),
        }
        for sid, s in call_sessions.items()
    }


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", "8000"))
    print(f"Starting call server on port {port}")
    print("Make sure WEBHOOK_BASE_URL is set to your public URL (e.g. ngrok)")
    uvicorn.run(app, host="0.0.0.0", port=port)
