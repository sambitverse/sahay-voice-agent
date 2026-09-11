import os
import json
import base64
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database import recordings_db


@pytest.fixture(autouse=True)
def setup_db():
    recordings_db.init_db()


def test_exotel_call_stores_recording_as_mobile_number():
    """Verify that a real-time Exotel call with audio persists its recording as caller's mobile number."""
    client = TestClient(app)
    call_id = "live_call_session_77"
    test_phone = "+91 94371-55555"
    expected_mobile = "+919437155555"

    with client.websocket_connect(f"/ws/exotel/{call_id}") as ws:
        start_payload = {
            "event": "start",
            "stream_sid": "stream_test_123",
            "start": {
                "stream_sid": "stream_test_123",
                "call_sid": call_id,
                "from": test_phone,
                "media_format": {
                    "encoding": "audio/x-mulaw",
                    "sample_rate": 8000,
                    "channels": 1
                }
            }
        }
        ws.send_text(json.dumps(start_payload))

        # Send actual 8kHz audio media frames
        dummy_audio = b"\x00\x7f" * 1600  # 3200 bytes = 0.2 sec
        b64_audio = base64.b64encode(dummy_audio).decode("utf-8")
        media_payload = {
            "event": "media",
            "stream_sid": "stream_test_123",
            "media": {
                "payload": b64_audio
            }
        }
        ws.send_text(json.dumps(media_payload))

        # Send stop event to end call
        ws.send_text(json.dumps({"event": "stop", "stream_sid": "stream_test_123"}))

    # Recording must be stored under their mobile number
    records = recordings_db.get_recordings(phone=test_phone)
    call_ids = [r["call_id"] for r in records]
    assert expected_mobile in call_ids, f"Expected {expected_mobile} in recordings_db, found {call_ids}"

    matched = next(r for r in records if r["call_id"] == expected_mobile)
    assert matched["caller_phone"] == test_phone
    assert matched["caller_name"] == test_phone
    assert matched["recording_url"] == f"/api/v1/recordings/{expected_mobile}.wav"
    assert os.path.exists(matched["file_path"])

    # Clean up generated test wav file and db row
    if os.path.exists(matched["file_path"]):
        try:
            os.remove(matched["file_path"])
        except Exception:
            pass
    recordings_db.delete_recording(expected_mobile)


def test_exotel_call_without_audio_does_not_store_recording():
    """Verify that an Exotel call with zero caller audio frames does NOT store any recording."""
    client = TestClient(app)
    call_id = "empty_call_888"
    silent_phone = "+91 98610-99999"
    expected_mobile = "+919861099999"

    with client.websocket_connect(f"/ws/exotel/{call_id}") as ws:
        start_payload = {
            "event": "start",
            "stream_sid": "stream_empty_123",
            "start": {
                "stream_sid": "stream_empty_123",
                "call_sid": call_id,
                "from": silent_phone,
                "media_format": {
                    "encoding": "audio/x-mulaw",
                    "sample_rate": 8000,
                    "channels": 1
                }
            }
        }
        ws.send_text(json.dumps(start_payload))
        # End call immediately with zero audio media frames sent
        ws.send_text(json.dumps({"event": "stop", "stream_sid": "stream_empty_123"}))

    # No recording should be stored because no real-time caller audio was captured
    records = recordings_db.get_recordings(phone=silent_phone)
    call_ids = [r["call_id"] for r in records]
    assert expected_mobile not in call_ids
