import os
import re
import wave
import uuid
import datetime
import json
import base64
import logging
import asyncio
from typing import Optional
from fastapi import WebSocket, WebSocketDisconnect
from ..audio.resampler import AudioResampler
from ..database.supabase_client import SupabaseManager
from .client_ws import (
    ClientAudioSession,
    get_cached_greeting_b64,
    _CACHED_GREETING_TEXT,
)
from .dashboard_ws import broadcaster

logger = logging.getLogger(__name__)


class ExotelWebSocketAdapter:
    """
    Adapter that translates between internal ClientAudioSession events
    and the Exotel Voicebot WebSocket protocol (8kHz slin16 PCM).
    """

    def __init__(self, raw_ws: WebSocket, stream_sid: str = "", session: Optional["ClientAudioSession"] = None):
        self.raw_ws = raw_ws
        self.stream_sid = stream_sid
        self.session = session
        self.resampler = AudioResampler()
        self.is_closed = False
        self.is_streaming_adapter = True
        self._interrupted = False
        self._streaming_lock = asyncio.Lock()

    async def send_json(self, data: dict):
        if self.is_closed:
            return

        event = data.get("event")

        # 1. Outbound Audio Media Event -> Convert to Exotel Voicebot format
        if event == "media":
            payload_b64 = data.get("payload", "")
            if not payload_b64 or not self.stream_sid:
                return

            self._interrupted = False

            try:
                pcm_bytes = base64.b64decode(payload_b64)
                # Strip WAV header if present (44-byte RIFF header)
                if pcm_bytes.startswith(b"RIFF") and len(pcm_bytes) > 44:
                    pcm_bytes = pcm_bytes[44:]

                sample_rate = data.get("sample_rate", 16000)
                if sample_rate == 16000:
                    pcm_8k = self.resampler.resample_16k_to_8k(pcm_bytes)
                else:
                    pcm_8k = pcm_bytes

                # Pad to multiple of 320 bytes (Exotel requirement: multiple of 320 bytes)
                rem = len(pcm_8k) % 320
                if rem != 0:
                    pcm_8k += b"\x00" * (320 - rem)

                # Chunk into 3200-byte packets (200ms of audio at 8kHz 16-bit mono)
                chunk_size = 3200
                total_len = len(pcm_8k)

                async with self._streaming_lock:
                    for i in range(0, total_len, chunk_size):
                        if self.is_closed or self._interrupted:
                            break
                        chunk = pcm_8k[i:i + chunk_size]
                        if not chunk:
                            break
                        chunk_rem = len(chunk) % 320
                        if chunk_rem != 0:
                            chunk += b"\x00" * (320 - chunk_rem)

                        b64_chunk = base64.b64encode(chunk).decode("utf-8")
                        exotel_msg = {
                            "event": "media",
                            "stream_sid": self.stream_sid,
                            "media": {
                                "payload": b64_chunk
                            }
                        }
                        await self.raw_ws.send_json(exotel_msg)
                        # Pacing: 3200 bytes = 200ms; sleep 170ms to keep audio smooth without underrun
                        await asyncio.sleep(0.17)

                # Pacing completed: allow 0.2s for final network buffer, then clear speaking state
                await asyncio.sleep(0.2)
                if self.session and not self._interrupted:
                    self.session.is_ai_speaking = False
                    self.session.turn_in_progress = False

            except Exception as e:
                logger.error(f"[ExotelAdapter] Error streaming audio chunk to Exotel: {e}")
                if self.session:
                    self.session.is_ai_speaking = False
                    self.session.turn_in_progress = False

        # 2. Interruption / Clear Audio Buffer Event
        elif event in ("clear", "clear_buffer", "barge_in"):
            self._interrupted = True
            if self.session:
                self.session.is_ai_speaking = False
                self.session.turn_in_progress = False
            if self.stream_sid:
                try:
                    await self.raw_ws.send_json({
                        "event": "clear",
                        "stream_sid": self.stream_sid
                    })
                except Exception as e:
                    logger.warning(f"[ExotelAdapter] Error sending clear event: {e}")

        # 3. Telemetry & Agent Response -> Broadcast to Operator Dashboard
        else:
            try:
                if event == "agent_response":
                    await broadcaster.broadcast("agent_response", data)
                elif event == "assessment_update":
                    await broadcaster.broadcast("call_telemetry", data)
            except Exception as e:
                logger.warning(f"[ExotelAdapter] Broadcast warning: {e}")


async def handle_exotel_websocket(websocket: WebSocket, call_id: str):
    """
    Handles Exotel Voicebot bidirectional audio over WebSockets.
    Translates 8kHz PSTN carrier audio <-> 16kHz internal AI processing pipeline.
    """
    await websocket.accept()
    logger.info(f"[ExotelWS] Connected Exotel Voicebot telephony call: {call_id}")

    session = ClientAudioSession(call_id)
    await session.init_session()
    resampler = AudioResampler()
    adapter = ExotelWebSocketAdapter(websocket, session=session)

    is_ulaw = False

    try:
        while True:
            message = await websocket.receive()

            if "text" in message and message["text"]:
                data = json.loads(message["text"])
                event = data.get("event")

                # Exotel Media Event containing 8kHz audio from caller
                if event == "media":
                    payload_b64 = data.get("media", {}).get("payload", "")
                    if payload_b64:
                        raw_8k = base64.b64decode(payload_b64)
                        if is_ulaw:
                            pcm_8k = resampler.ulaw_to_linear_pcm(raw_8k)
                        else:
                            pcm_8k = raw_8k

                        # Resample to 16kHz linear PCM for AI perception
                        pcm_16k = resampler.resample_8k_to_16k(pcm_8k)
                        session.caller_audio_record.extend(pcm_16k)
                        await session.handle_audio_frame(pcm_16k, adapter)

                elif event == "start":
                    start_info = data.get("start", {})
                    stream_sid = data.get("stream_sid") or start_info.get("stream_sid", "")
                    adapter.stream_sid = stream_sid

                    media_format = start_info.get("media_format", {})
                    bit_rate = media_format.get("bit_rate", "")
                    encoding = media_format.get("encoding", "").lower()
                    if bit_rate == "64kbps" or "mulaw" in encoding:
                        is_ulaw = True

                    caller_phone = start_info.get("from") or start_info.get("From") or call_id
                    session.caller_phone = caller_phone
                    session.phone_hash = SupabaseManager.hash_phone(caller_phone)

                    actual_call_id = start_info.get("call_sid") or start_info.get("CallSid")
                    if actual_call_id and actual_call_id != "live_call":
                        session.call_id = actual_call_id

                    logger.info(
                        f"[ExotelWS] Call Stream started: stream_sid={stream_sid}, "
                        f"caller={caller_phone}, call_id={session.call_id}, is_ulaw={is_ulaw}"
                    )

                    # Trigger initial Odia voice greeting immediately at connection
                    cached_b64 = get_cached_greeting_b64()
                    if cached_b64:
                        session.is_ai_speaking = True
                        await broadcaster.broadcast("agent_response", {
                            "call_id": call_id,
                            "text": _CACHED_GREETING_TEXT,
                            "risk_level": "LOW",
                            "phase": "GREETING"
                        })
                        # Stream greeting audio to caller phone
                        asyncio.create_task(adapter.send_json({
                            "event": "media",
                            "payload": cached_b64,
                            "sample_rate": 16000
                        }))
                    else:
                        try:
                            greeting_audio = await session.sarvam.synthesize(_CACHED_GREETING_TEXT, "or-IN")
                            if greeting_audio:
                                session.is_ai_speaking = True
                                b64_greet = base64.b64encode(greeting_audio).decode("utf-8")
                                await broadcaster.broadcast("agent_response", {
                                    "call_id": call_id,
                                    "text": _CACHED_GREETING_TEXT,
                                    "risk_level": "LOW",
                                    "phase": "GREETING"
                                })
                                asyncio.create_task(adapter.send_json({
                                    "event": "media",
                                    "payload": b64_greet,
                                    "sample_rate": 16000
                                }))
                        except Exception as e:
                            logger.error(f"[ExotelWS] Error synthesizing initial greeting: {e}")

                elif event == "dtmf":
                    digit = data.get("dtmf", {}).get("digit")
                    logger.info(f"[ExotelWS] Caller DTMF pressed: {digit}")

                elif event == "stop":
                    logger.info(f"[ExotelWS] Call Stream ended: {call_id}")
                    break

            elif "bytes" in message and message["bytes"]:
                raw_8k = message["bytes"]
                if is_ulaw:
                    pcm_8k = resampler.ulaw_to_linear_pcm(raw_8k)
                else:
                    pcm_8k = raw_8k
                pcm_16k = resampler.resample_8k_to_16k(pcm_8k)
                await session.handle_audio_frame(pcm_16k, adapter)

    except WebSocketDisconnect:
        logger.info(f"[ExotelWS] Exotel carrier disconnected call: {call_id}")
    except Exception as e:
        logger.error(f"[ExotelWS] Telephony stream error on {call_id}: {e}", exc_info=True)
    finally:
        adapter.is_closed = True

        caller_num = getattr(session, "caller_phone", None) or call_id
        duration_s = len(session.caller_audio_record) / 32000.0 if len(session.caller_audio_record) > 0 else 0.0
        user_texts = [t["content"] for t in session.full_transcript if t.get("role") in ("caller", "user")]
        summary = user_texts[0] if user_texts else f"Telephony Helpline Call ({duration_s:.0f}s)"
        risk_lvl = session.distress_state.current_level.value if hasattr(session.distress_state, "current_level") else "HIGH"
        tkt_ref = f"TKT-{datetime.datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:4].upper()}"

        # Standardize mobile number format for storage and filename
        raw_phone = str(caller_num).strip()
        phone_digits = re.sub(r"\D", "", raw_phone)
        if phone_digits:
            clean_mobile = f"+91{phone_digits[-10:]}" if len(phone_digits) >= 10 and not raw_phone.startswith("+") else raw_phone
            file_mobile = re.sub(r"[^\d+]", "", raw_phone) or phone_digits
        else:
            clean_mobile = raw_phone
            file_mobile = re.sub(r"[^\w+]", "", raw_phone) or call_id

        rec_dir = os.path.join(os.path.dirname(__file__), "..", "static", "recordings")
        os.makedirs(rec_dir, exist_ok=True)
        rec_filename = f"{file_mobile}.wav"
        wav_path = os.path.join(rec_dir, rec_filename)
        recording_url = f"/api/v1/recordings/{rec_filename}"

        # ONLY add real-time call recordings with captured caller audio
        if len(session.caller_audio_record) > 0:
            try:
                with wave.open(wav_path, "wb") as wf:
                    wf.setnchannels(1)
                    wf.setsampwidth(2)
                    wf.setframerate(16000)
                    wf.writeframes(bytes(session.caller_audio_record))
                logger.info(f"[ExotelWS] Saved real-time telephony audio recording to {wav_path} ({len(session.caller_audio_record)} bytes)")
            except Exception as e:
                logger.warning(f"[ExotelWS] Could not write telephony audio recording file: {e}")

            # Store in database as their mobile number
            try:
                from app.database import recordings_db
                lang_val = session.language_router.get_session_language(call_id).value
                rec_entry = recordings_db.save_recording(
                    call_id=file_mobile,
                    caller_name=clean_mobile,
                    caller_phone=clean_mobile,
                    duration_seconds=round(duration_s, 1),
                    file_path=wav_path,
                    recording_url=recording_url,
                    risk_level=risk_lvl,
                    summary=summary,
                    language=lang_val
                )
                await broadcaster.broadcast("recording_saved", rec_entry)
                logger.info(f"[ExotelWS] Stored real-time call recording in database as mobile number: {clean_mobile} -> {wav_path}")
            except Exception as dbe:
                logger.error(f"[ExotelWS] Failed to save Exotel recording to recordings_db: {dbe}")

            # Register Grievance Record in Database for Caller Dashboard
            try:
                complaint = session.db.register_complaint(
                    call_id=file_mobile,
                    ticket_id=tkt_ref,
                    summary=summary,
                    risk_level=risk_lvl,
                    caller_number=clean_mobile,
                    language=session.language_router.get_session_language(call_id).value,
                    recording_url=recording_url
                )
                await broadcaster.broadcast("complaint_registered", complaint)
                logger.info(f"[ExotelWS] Registered telephony complaint {tkt_ref} for {clean_mobile}")
            except Exception as e:
                logger.warning(f"[ExotelWS] Could not register complaint: {e}")

        await session.db.update_call_status(call_id, "completed")
        await broadcaster.broadcast("call_ended", {"call_id": call_id})
        logger.info(f"[ExotelWS] Cleaned up Exotel call: {call_id}")
