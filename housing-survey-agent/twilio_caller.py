"""Twilio integration for automated outbound survey calls.

Flow:
1. Agent initiates outbound call to a property via Twilio
2. Twilio connects and hits our webhook server for call instructions
3. Each turn: play TTS audio -> record property manager response
4. Webhook server downloads recording, transcribes, generates next response
5. Loop until survey is complete or call ends
6. Recording URL and metadata saved with survey results
"""

import os
import time
from dataclasses import dataclass, field

from dotenv import load_dotenv
from twilio.rest import Client

load_dotenv()


@dataclass
class CallResult:
    """Result of a completed or attempted call."""
    call_sid: str
    property_id: int
    property_name: str
    phone_number: str
    status: str  # completed, no-answer, busy, failed, canceled
    duration_seconds: int = 0
    recording_url: str | None = None
    error: str | None = None


def get_twilio_client() -> Client:
    """Create a Twilio client from environment variables."""
    account_sid = os.environ.get("TWILIO_ACCOUNT_SID")
    auth_token = os.environ.get("TWILIO_AUTH_TOKEN")
    if not account_sid or not auth_token:
        raise ValueError(
            "TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN environment variables required"
        )
    return Client(account_sid, auth_token)


def get_from_number() -> str:
    """Get the Twilio phone number to call from."""
    number = os.environ.get("TWILIO_PHONE_NUMBER")
    if not number:
        raise ValueError("TWILIO_PHONE_NUMBER environment variable required")
    return number


def initiate_call(
    to_number: str,
    webhook_base_url: str,
    property_id: int,
    property_name: str = "",
) -> str:
    """Place an outbound call via Twilio.

    The webhook_base_url is where your call_server.py is running.
    Twilio will POST to {webhook_base_url}/call/start when the
    call connects.

    Returns the call SID for tracking.
    """
    client = get_twilio_client()

    call = client.calls.create(
        to=to_number,
        from_=get_from_number(),
        url=f"{webhook_base_url}/call/start?property_id={property_id}"
            f"&property_name={property_name}",
        status_callback=f"{webhook_base_url}/call/status",
        status_callback_event=["initiated", "ringing", "answered", "completed"],
        status_callback_method="POST",
        record=True,
        recording_status_callback=f"{webhook_base_url}/call/recording",
        recording_status_callback_method="POST",
        timeout=30,  # seconds to wait for answer
        machine_detection="Enable",  # detect voicemail
        machine_detection_timeout=5,
    )

    return call.sid


def get_call_status(call_sid: str) -> dict:
    """Check the current status of a call."""
    client = get_twilio_client()
    call = client.calls(call_sid).fetch()
    return {
        "sid": call.sid,
        "status": call.status,
        "duration": call.duration,
        "direction": call.direction,
        "answered_by": call.answered_by,
        "start_time": str(call.start_time) if call.start_time else None,
        "end_time": str(call.end_time) if call.end_time else None,
    }


def wait_for_call_completion(call_sid: str, poll_interval: float = 5.0,
                              max_wait: float = 600.0) -> dict:
    """Poll until a call completes. Returns final call status."""
    client = get_twilio_client()
    elapsed = 0.0

    while elapsed < max_wait:
        call = client.calls(call_sid).fetch()
        if call.status in ("completed", "busy", "no-answer", "canceled", "failed"):
            return {
                "sid": call.sid,
                "status": call.status,
                "duration": int(call.duration) if call.duration else 0,
                "answered_by": call.answered_by,
            }
        time.sleep(poll_interval)
        elapsed += poll_interval

    return {"sid": call_sid, "status": "timeout", "duration": 0}


def get_call_recordings(call_sid: str) -> list[dict]:
    """Get recording URLs for a completed call."""
    client = get_twilio_client()
    recordings = client.calls(call_sid).recordings.list()
    return [
        {
            "sid": r.sid,
            "duration": int(r.duration) if r.duration else 0,
            "url": f"https://api.twilio.com{r.uri.replace('.json', '.mp3')}",
        }
        for r in recordings
    ]


def hangup_call(call_sid: str):
    """Hang up an active call."""
    client = get_twilio_client()
    client.calls(call_sid).update(status="completed")
