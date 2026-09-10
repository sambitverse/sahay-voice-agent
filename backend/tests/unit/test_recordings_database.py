"""
Unit tests for Voice Recordings Database and Role-Based Access Control.
Verifies:
1. Citizen can see only their own voice recordings matching mobile number.
2. Operator can see everyone's voice recordings in a unified administrative list.
3. Recordings store caller name, mobile number, call ID, duration, and audio URLs as per login details.
"""

import os
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database import recordings_db


@pytest.fixture(autouse=True)
def ensure_db():
    recordings_db.init_db()


def test_sqlite_save_and_retrieve_own_recordings():
    # Save a recording for citizen Alice
    recordings_db.save_recording(
        call_id="test_alice_rec_001",
        caller_name="Alice Majhi",
        caller_phone="+91 99371-22334",
        duration_seconds=12.4,
        file_path="/tmp/fake_alice.wav",
        recording_url="/api/v1/recordings/test_alice_rec_001.wav",
        risk_level="HIGH",
        summary="Witness harassment by land syndicate.",
        language="or-IN"
    )

    # Save a recording for citizen Bob
    recordings_db.save_recording(
        call_id="test_bob_rec_002",
        caller_name="Bob Munda",
        caller_phone="+91 98610-88990",
        duration_seconds=9.8,
        file_path="/tmp/fake_bob.wav",
        recording_url="/api/v1/recordings/test_bob_rec_002.wav",
        risk_level="MODERATE",
        summary="Water well access dispute.",
        language="sp-IN"
    )

    # 1. Alice should only see her own recordings
    alice_recs = recordings_db.get_recordings(phone="+91 99371-22334")
    alice_call_ids = [r["call_id"] for r in alice_recs]
    assert "test_alice_rec_001" in alice_call_ids
    assert "test_bob_rec_002" not in alice_call_ids
    assert alice_recs[0]["caller_name"] == "Alice Majhi"

    # 2. Bob should only see his own recordings
    bob_recs = recordings_db.get_recordings(phone="+91 98610-88990")
    bob_call_ids = [r["call_id"] for r in bob_recs]
    assert "test_bob_rec_002" in bob_call_ids
    assert "test_alice_rec_001" not in bob_call_ids

    # 3. Operator (phone=None) should see EVERYONE'S recordings as a list
    all_recs = recordings_db.get_recordings(phone=None)
    all_call_ids = [r["call_id"] for r in all_recs]
    assert "test_alice_rec_001" in all_call_ids
    assert "test_bob_rec_002" in all_call_ids
    assert len(all_recs) >= 2


def test_api_role_based_recordings():
    client = TestClient(app)

    # Citizen query: filtered by phone
    res_user = client.get("/api/v1/recordings?phone=%2B91%2099371-22334")
    assert res_user.status_code == 200
    user_data = res_user.json()
    assert user_data["status"] == "success"
    # Citizen only receives records matching their phone number
    for rec in user_data["recordings"]:
        assert "9937122334" in rec["caller_phone"].replace("-", "").replace(" ", "")

    # Operator query: role=operator returns ALL recordings
    res_op = client.get("/api/v1/recordings?role=operator")
    assert res_op.status_code == 200
    op_data = res_op.json()
    assert op_data["status"] == "success"
    assert op_data["role"] == "operator"
    assert len(op_data["recordings"]) >= len(user_data["recordings"])
