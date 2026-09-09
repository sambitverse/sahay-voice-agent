import os
import base64
import json
import logging
import asyncio
from typing import Dict, List, Optional
import numpy as np
from fastapi import WebSocket, WebSocketDisconnect
from fastapi.encoders import jsonable_encoder

_CACHED_GREETING_PATH = os.path.join(os.path.dirname(__file__), "..", "audio", "cached_greeting.wav")
_CACHED_GREETING_B64: Optional[str] = None
_CACHED_GREETING_TEXT = "Namaskar. NHAA 14566 helpline re apananku swagata. Daya kari apananka samasya kuhan tu."

def get_cached_greeting_b64() -> Optional[str]:
    global _CACHED_GREETING_B64
    if _CACHED_GREETING_B64 is None and os.path.exists(_CACHED_GREETING_PATH):
        try:
            with open(_CACHED_GREETING_PATH, "rb") as f:
                _CACHED_GREETING_B64 = base64.b64encode(f.read()).decode("utf-8")
        except Exception as e:
            logger.warning(f"Failed to read cached greeting file: {e}")
    return _CACHED_GREETING_B64

from ..config import settings
from ..domain.models import DistressState, RiskAssessment, RiskLevel
from ..audio.vad import VoiceActivityDetector
from ..audio.resampler import AudioResampler
from ..providers.sarvam_provider import SarvamProvider
from ..providers.bhashini_provider import BhashiniProvider
from ..providers.hybrid_speech import HybridSpeechProvider
from ..providers.gemini_provider import GeminiProvider
from ..acoustic.extractor import StandardAcousticExtractor
from ..emotion.classifier import Wav2VecEmotionClassifier
import wave
from ..distress.fusion_engine import DistressFusionEngine
from ..trauma.controller import TraumaController
from ..trauma.state_machine import ConversationStateManager, ConversationState
from ..trauma.handoff import StructuredHandoffGenerator
from ..trauma.prank_filter import PrankFilter
from ..safety.validator import SafetyValidator
from ..language.router import LanguageRouter, DialectBridge, SupportedLanguage
from ..rag.retriever import VerifiedRAGRetriever
from ..database.supabase_client import SupabaseManager
from .dashboard_ws import broadcaster

logger = logging.getLogger(__name__)


class ClientAudioSession:
    """Manages an active real-time multimodal voice call session."""

    def __init__(self, call_id: str):
        self.call_id = call_id
        self.vad = VoiceActivityDetector()
        self.resampler = AudioResampler()
        self.speech = HybridSpeechProvider(
            sarvam_api_key=settings.SARVAM_API_KEY,
            sarvam_base_url=settings.SARVAM_BASE_URL,
            bhashini_auth_token=settings.BHASHINI_AUTH_TOKEN,
            bhashini_user_id=settings.BHASHINI_USER_ID,
            bhashini_api_key=settings.BHASHINI_API_KEY,
            bhashini_inference_url=settings.BHASHINI_INFERENCE_URL,
            primary_provider="sarvam"
        )
        self.sarvam = self.speech
        self.gemini = GeminiProvider(api_key=settings.GEMINI_API_KEY, model=settings.GEMINI_MODEL)
        self.acoustic_extractor = StandardAcousticExtractor()
        self.emotion_classifier = Wav2VecEmotionClassifier()
        self.fusion_engine = DistressFusionEngine()
        self.trauma_controller = TraumaController()
        self.state_machine = ConversationStateManager()
        self.language_router = LanguageRouter()
        self.rag_retriever = VerifiedRAGRetriever()
        self.db = SupabaseManager.get_instance()

        self.distress_state = DistressState(call_id=call_id)
        self.phone_hash = SupabaseManager.hash_phone(call_id)
        self.turn_count = 0
        self.conversation_history: List[Dict[str, str]] = []
        self.full_transcript: List[Dict[str, str]] = []

        self.audio_buffer = bytearray()
        self.caller_audio_record = bytearray()
        self.is_ai_speaking = False
        self.current_tts_task: Optional[asyncio.Task] = None
        self.turn_lock = asyncio.Lock()
        self.caller_phone: str = "+91 94371-88210"
        self.is_language_locked: bool = False

    async def init_session(self) -> None:
        """Record session in database and announce to live operator dashboard."""
        await self.db.create_call_session(
            external_call_id=self.call_id,
            phone_hash=self.phone_hash,
            telephony_provider="web_audio",
            detected_language=SupportedLanguage.ODIA.value
        )
        await broadcaster.broadcast("call_started", {
            "call_id": self.call_id,
            "phone_hash": self.phone_hash,
            "status": "initiated",
            "language": SupportedLanguage.ODIA.value
        })

    async def handle_audio_frame(self, frame_pcm: bytes, websocket: WebSocket) -> None:
        """Process incoming 16kHz PCM audio chunk from caller."""
        # AI Speech Protection (PS 26093 & Noise Isolation Mandate):
        # Do NOT allow background noise, passing horns, or sounds to interrupt the AI while speaking.
        if self.is_ai_speaking:
            return

        is_speech = self.vad.process_frame(frame_pcm)

        if is_speech:
            self.audio_buffer.extend(frame_pcm)
            self.caller_audio_record.extend(frame_pcm)
            # HARD SAFETY CAP: If caller speaks for more than 30.0s continuously, auto-commit!
            if len(self.audio_buffer) >= int(16000 * 2 * 30.0):
                logger.info(f"[Session {self.call_id}] Utterance reached 30.0s cap. Auto-committing.")
                utterance_bytes = bytes(self.audio_buffer)
                self.audio_buffer.clear()
                self.vad.reset()
                asyncio.create_task(self._process_utterance(utterance_bytes, websocket))
        else:
            # End of utterance triggered after ~260ms silence hangover
            # Require at least 250ms of recorded speech to prevent ambient clicks
            if len(self.audio_buffer) >= int(16000 * 2 * 0.25):
                # Trim trailing silence (~250ms) so STT doesn't waste time transcribing dead air
                trailing_silence_bytes = int(16000 * 2 * 0.25)
                if len(self.audio_buffer) > trailing_silence_bytes + int(16000 * 2 * 0.15):
                    utterance_bytes = bytes(self.audio_buffer[:-trailing_silence_bytes])
                else:
                    utterance_bytes = bytes(self.audio_buffer)

                self.audio_buffer.clear()
                self.vad.reset()

                # Process the completed utterance asynchronously
                asyncio.create_task(self._process_utterance(utterance_bytes, websocket))

    async def _process_utterance(self, audio_bytes: bytes, websocket: WebSocket) -> None:
        """Run full multimodal perception, fusion, reasoning, and response generation with turn serialization."""
        async with self.turn_lock:
            await self._execute_turn(audio_bytes, websocket)

    async def _execute_turn(self, audio_bytes: bytes, websocket: WebSocket) -> None:
        try:
            # 0. Fast Acoustic Horn & Siren Scanner across the utterance (hop_size=1024 for sub-2ms check)
            samples = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32)
            horn_frames = 0
            active_frames = 0
            max_horn_freq = 0.0

            if len(samples) >= 512:
                frame_size = 512
                hop_size = 1024
                hanning_w = np.hanning(frame_size)

                for i in range(0, len(samples) - frame_size + 1, hop_size):
                    chunk = samples[i:i + frame_size]
                    rms = float(np.sqrt(np.mean(chunk**2)))
                    if rms < 180.0:
                        continue  # Silence / room noise floor
                    active_frames += 1

                    mags = np.abs(np.fft.rfft(chunk * hanning_w))
                    sum_mags = float(np.sum(mags)) + 1e-6
                    max_idx = int(np.argmax(mags))
                    peak_freq = float(max_idx * (16000.0 / frame_size))
                    top2_ratio = float(np.sum(np.partition(mags, -2)[-2:])) / sum_mags
                    top4_ratio = float(np.sum(np.partition(mags, -4)[-4:])) / sum_mags

                    # True vehicle horn signature: pure resonant acoustic spike (top4 > 0.70, top2 > 0.38, sum > 1.10)
                    # Human speech formants have top4 < 0.42 and top2 < 0.25
                    if 300.0 <= peak_freq <= 4200.0 and (
                        top4_ratio > 0.70 and top2_ratio > 0.38 and (top2_ratio + top4_ratio) > 1.10
                    ):
                        horn_frames += 1
                        if peak_freq > max_horn_freq:
                            max_horn_freq = peak_freq

                # Only discard if utterance is overwhelmingly dominated by vehicle horn (> 60% horn frames)
                if active_frames >= 6 and (horn_frames / active_frames) > 0.60:
                    logger.info(f"[Session {self.call_id}] Discarding utterance: identified as pure vehicle horn ({horn_frames}/{active_frames} frames, peak={max_horn_freq:.0f}Hz)")
                    await websocket.send_json({
                        "event": "noise_ignored",
                        "message": f"Filtered vehicle horn sound ({max_horn_freq:.0f}Hz)"
                    })
                    return

            # 1. Parallel Speech Perception & Feature Extraction
            current_lang = self.language_router.get_session_language(self.call_id)
            # Default to Odia ('od-IN') for NHAA helpline unless caller selects or switches
            mapped_lang = "od-IN" if "or" in current_lang.value.lower() else current_lang.value

            stt_task = asyncio.create_task(self.sarvam.transcribe(audio_bytes, 16000, language_code=mapped_lang))
            acoustic_task = asyncio.create_task(self.acoustic_extractor.extract(audio_bytes, 16000))
            emotion_task = asyncio.create_task(self.emotion_classifier.predict_emotion(audio_bytes, 16000))

            raw_transcript, raw_detected_lang, lang_conf = await stt_task
            acoustic_signals = await acoustic_task
            emotion_signals = await emotion_task

            # If audio was ambient noise, breathing, or silence without words, notify client and keep listening
            stripped_transcript = raw_transcript.strip()
            if not stripped_transcript:
                logger.info(f"[Session {self.call_id}] Empty audio ({len(audio_bytes)} bytes) discarded. Listening for speech.")
                await websocket.send_json({
                    "event": "noise_ignored",
                    "message": "Filtered ambient background noise"
                })
                return

            # Speech confirmed! Increment valid turn count
            self.turn_count += 1
            logger.info(f"[Session {self.call_id}] Starting turn {self.turn_count} perception: '{raw_transcript}'")

            # 2. Language Routing & Dialect Normalization
            detected_lang_enum, detected_conf = self.language_router.detect_language_from_text(raw_transcript)
            active_lang = self.language_router.update_session_language(
                self.call_id, detected_lang_enum.value, detected_conf
            )

            # Broadcast real-time language detection to client and operator dashboard
            await websocket.send_json({
                "event": "language_detected",
                "language": active_lang.value,
                "confidence": detected_conf
            })

            normalized_transcript = DialectBridge.normalize_dialect(raw_transcript, active_lang.value)

            self.full_transcript.append({"role": "caller", "content": raw_transcript})
            # Non-blocking async DB write
            asyncio.create_task(self.db.save_transcript_segment(
                external_call_id=self.call_id,
                speaker="caller",
                text_content=raw_transcript,
                sequence_num=self.turn_count,
                language=active_lang.value
            ))

            # 3. Extract linguistic signals from normalized transcript
            linguistic_signals = await self.gemini.extract_linguistic_signals(normalized_transcript)

            # 4. Multimodal Distress Fusion
            self.distress_state = self.fusion_engine.fuse(
                current_state=self.distress_state,
                acoustic=acoustic_signals,
                emotion=emotion_signals,
                linguistic=linguistic_signals
            )

            # 5. Deterministic Trauma Controller Assessment & Safety Override
            assessment: RiskAssessment = self.trauma_controller.assess_and_control(
                call_id=self.call_id,
                distress_state=self.distress_state,
                latest_transcript=normalized_transcript
            )

            # 6. Conversation State Machine Transition
            conv_state = self.state_machine.transition(
                call_id=self.call_id,
                risk_level=assessment.risk_level.value,
                turn_count=self.turn_count,
                requires_escalation=assessment.requires_human_escalation
            )

            # 7. Verified RAG Context Retrieval
            rag_context = self.rag_retriever.retrieve_context(
                query=normalized_transcript,
                risk_level=assessment.risk_level.value,
                language_code=active_lang.value,
                top_k=2
            )

            # 8. SBAR Structured Handoff generation if High/Critical
            # NOTE: Only produce a formal SBAR handoff and persist escalation events
            # once the conversation has reached the ESCALATION_HANDOFF phase (Turn 6+).
            sbar_handoff = None
            if (assessment.requires_human_escalation or assessment.risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]) and conv_state == ConversationState.ESCALATION_HANDOFF:
                sbar_handoff = StructuredHandoffGenerator.generate_sbar_report(
                    call_id=self.call_id,
                    phone_hash=self.phone_hash,
                    detected_language=active_lang.value,
                    assessment=assessment,
                    distress_state=self.distress_state,
                    full_transcript=self.full_transcript,
                    acoustic_features=acoustic_signals,
                    emotion_prediction=emotion_signals
                )
                asyncio.create_task(self.db.create_escalation(
                    external_call_id=self.call_id,
                    trigger_reason=f"Triage Level: {assessment.risk_level.value} - {'; '.join(assessment.evidence[:2])}"
                ))

            # Non-blocking async DB write
            asyncio.create_task(self.db.save_risk_assessment(
                external_call_id=self.call_id,
                risk_score=assessment.risk_score,
                risk_level=assessment.risk_level.value,
                safety_flags=assessment.safety_flags.model_dump(),
                evidence_summary=assessment.evidence,
                recommended_action=assessment.recommended_action,
                requires_human_escalation=assessment.requires_human_escalation
            ))

            # 9. Send real-time telemetry to client UI immediately
            telemetry_payload = {
                "event": "assessment_update",
                "call_id": self.call_id,
                "transcript": raw_transcript,
                "normalized_transcript": normalized_transcript if normalized_transcript != raw_transcript else None,
                "language": active_lang.value,
                "phase": conv_state.value,
                "svi_score": assessment.svi_score,
                "svi_percentage": assessment.svi_percentage,
                "sub_indices": assessment.sub_indices,
                "recommended_services": assessment.recommended_services,
                "emotion": (self.distress_state.latest_emotion or emotion_signals).model_dump(mode="json"),
                "acoustic": acoustic_signals.model_dump(mode="json"),
                "risk": assessment.model_dump(mode="json"),
                "evidence": assessment.evidence,
                "safety_flags": assessment.safety_flags.model_dump(mode="json"),
                "handoff": sbar_handoff
            }
            safe_telemetry = jsonable_encoder(telemetry_payload)
            await websocket.send_json(safe_telemetry)
            asyncio.create_task(broadcaster.broadcast("call_telemetry", safe_telemetry))

            # 10. Generate Conversational Response using Gemini Flash with strict 4.0s timeout
            self.conversation_history.append({"role": "caller", "content": raw_transcript})

            system_instructions = self.state_machine.get_system_prompt_for_state(
                state=conv_state,
                language_code=active_lang.value,
                risk_level=assessment.risk_level.value,
                latest_transcript=normalized_transcript
            )

            try:
                raw_ai_response = await asyncio.wait_for(
                    self.gemini.generate_response(
                        conversation_history=self.conversation_history[-6:],
                        system_instructions=system_instructions,
                        retrieved_context=rag_context
                    ),
                    timeout=8.0
                )
            except asyncio.TimeoutError:
                logger.warning(f"[Session {self.call_id}] Gemini response timed out; using state-specific protocol.")
                raw_ai_response = self.state_machine.get_fallback_phrase(active_lang.value, conv_state, latest_transcript=normalized_transcript)
            except Exception as e:
                logger.warning(f"[Session {self.call_id}] Gemini generation exception: {e}; using fallback.")
                raw_ai_response = self.state_machine.get_fallback_phrase(active_lang.value, conv_state, latest_transcript=normalized_transcript)

            # 11. Post-generation Safety Validation
            safe_response, is_valid = SafetyValidator.validate(raw_ai_response, active_lang.value, caller_transcript=normalized_transcript)
            if not safe_response or not safe_response.strip():
                safe_response = self.state_machine.get_fallback_phrase(active_lang.value, conv_state, latest_transcript=normalized_transcript)

            self.conversation_history.append({"role": "agent", "content": safe_response})
            self.full_transcript.append({"role": "agent", "content": safe_response})

            asyncio.create_task(self.db.save_transcript_segment(
                external_call_id=self.call_id,
                speaker="agent",
                text_content=safe_response,
                sequence_num=self.turn_count,
                language=active_lang.value
            ))

            # Send agent transcript event to caller
            await websocket.send_json({
                "event": "agent_response",
                "text": safe_response,
                "risk_level": assessment.risk_level.value,
                "phase": conv_state.value
            })

            asyncio.create_task(broadcaster.broadcast("agent_response", {
                "call_id": self.call_id,
                "text": safe_response,
                "risk_level": assessment.risk_level.value
            }))

            # 12. Synthesize Outbound Audio with Sarvam TTS
            self.is_ai_speaking = True
            tts_audio = await self.sarvam.synthesize(safe_response, active_lang.value)

            if tts_audio:
                b64_audio = base64.b64encode(tts_audio).decode("utf-8")
                await websocket.send_json({
                    "event": "media",
                    "payload": b64_audio,
                    "sample_rate": 16000
                })

                # If the websocket adapter already does realtime playback pacing (e.g. ExotelAdapter),
                # the audio has completed playback by the time send_json returns!
                if hasattr(websocket, "_streaming_lock") or hasattr(websocket, "stream_sid"):
                    self.is_ai_speaking = False
                else:
                    # Dynamic safety watchdog for browser client: auto-clear speaking state after audio duration
                    approx_duration = min(4.0, max(1.0, len(tts_audio) / 32000.0))
                    async def _auto_clear_speaking():
                        await asyncio.sleep(approx_duration + 0.2)
                        self.is_ai_speaking = False
                    asyncio.create_task(_auto_clear_speaking())
            else:
                self.is_ai_speaking = False

        except Exception as e:
            logger.error(f"[Session {self.call_id}] Processing error: {e}", exc_info=True)
            self.is_ai_speaking = False
            # Spoken safety fallback in case of unexpected network glitch
            try:
                emergency_msg = "Mu apananka katha suniparuchhi. Apan ebe surakshita sthana re achhanti ki?"
                tts_err = await self.sarvam.synthesize(emergency_msg, "or-IN")
                if tts_err:
                    await websocket.send_json({
                        "event": "agent_response",
                        "text": emergency_msg,
                        "risk_level": "LOW",
                        "phase": "PROBLEM_ASSESSMENT"
                    })
                    await websocket.send_json({
                        "event": "media",
                        "payload": base64.b64encode(tts_err).decode("utf-8"),
                        "sample_rate": 16000
                    })
            except Exception:
                pass


async def handle_client_websocket(websocket: WebSocket, call_id: str):
    """FastAPI WebSocket endpoint handler for /ws/client/{call_id}."""
    await websocket.accept()
    logger.info(f"[WebSocket] Connected client session: {call_id}")

    session = ClientAudioSession(call_id)
    phone_param = websocket.query_params.get("phone")
    if phone_param:
        session.caller_phone = phone_param
        session.phone_hash = SupabaseManager.hash_phone(phone_param)
    await session.init_session()

    try:
        # Send connected event
        await websocket.send_json({
            "event": "connected",
            "call_id": call_id,
            "message": "Connected to NHAA (14566) Voice Triage Gateway"
        })

        # Play initial voice greeting instantly at Second 0 (pre-cached audio)
        cached_b64 = get_cached_greeting_b64()
        if cached_b64:
            session.is_ai_speaking = True
            await websocket.send_json({
                "event": "agent_response",
                "text": _CACHED_GREETING_TEXT,
                "risk_level": "LOW",
                "phase": "GREETING"
            })
            await websocket.send_json({
                "event": "media",
                "payload": cached_b64,
                "sample_rate": 16000
            })
            # Safety watchdog for initial cached greeting
            cached_bytes = base64.b64decode(cached_b64)
            approx_dur = min(3.5, max(1.5, len(cached_bytes) / 32000.0))
            async def _auto_clear_cached_greeting():
                await asyncio.sleep(approx_dur + 0.2)
                session.is_ai_speaking = False
            asyncio.create_task(_auto_clear_cached_greeting())
        else:
            try:
                greeting_audio = await session.sarvam.synthesize(_CACHED_GREETING_TEXT, "or-IN")
                if greeting_audio:
                    b64_greeting = base64.b64encode(greeting_audio).decode("utf-8")
                    session.is_ai_speaking = True
                    await websocket.send_json({
                        "event": "agent_response",
                        "text": _CACHED_GREETING_TEXT,
                        "risk_level": "LOW",
                        "phase": "GREETING"
                    })
                    await websocket.send_json({
                        "event": "media",
                        "payload": b64_greeting,
                        "sample_rate": 16000
                    })
                    approx_dur = min(3.5, max(1.5, len(greeting_audio) / 32000.0))
                    async def _auto_clear_synth_greeting():
                        await asyncio.sleep(approx_dur + 0.2)
                        session.is_ai_speaking = False
                    asyncio.create_task(_auto_clear_synth_greeting())
            except Exception as e:
                logger.warning(f"[WebSocket] Initial greeting synthesis warning: {e}")

        while True:
            message = await websocket.receive()

            # Handle Binary PCM Audio
            if "bytes" in message and message["bytes"]:
                await session.handle_audio_frame(message["bytes"], websocket)

            # Handle JSON Events
            elif "text" in message and message["text"]:
                data = json.loads(message["text"])
                event = data.get("event")

                if event == "media":
                    payload_b64 = data.get("payload", "")
                    if payload_b64:
                        pcm_bytes = base64.b64decode(payload_b64)
                        await session.handle_audio_frame(pcm_bytes, websocket)

                elif event == "utterance":
                    payload_b64 = data.get("payload", "")
                    if payload_b64:
                        pcm_bytes = base64.b64decode(payload_b64)
                        session.caller_audio_record.extend(pcm_bytes)
                        logger.info(f"[WebSocket] Processing complete caller utterance: {len(pcm_bytes)} bytes")
                        session.is_ai_speaking = False
                        asyncio.create_task(session._process_utterance(pcm_bytes, websocket))

                elif event == "barge_in":
                    logger.info(f"[WebSocket] Client confirmed human barge-in on session: {call_id}")
                    session.is_ai_speaking = False
                    if session.current_tts_task and not session.current_tts_task.done():
                        session.current_tts_task.cancel()

                elif event == "ai_speaking_ended":
                    session.is_ai_speaking = False

                elif event == "set_language":
                    lang = data.get("language", "or-IN")
                    if lang and lang.lower() in ("auto", "unknown", "auto-detect"):
                        session.is_language_locked = False
                        logger.info(f"[WebSocket] Set auto language detection for session: {call_id}")
                    else:
                        active_l = session.language_router.set_session_language(call_id, lang)
                        session.is_language_locked = True
                        logger.info(f"[WebSocket] User selected language: {active_l.value} for session: {call_id}")
                        await websocket.send_json({
                            "event": "language_updated",
                            "language": active_l.value
                        })

                elif event in ("stop", "commit"):
                    logger.info(f"[WebSocket] Client requested {event} for {call_id}")
                    if len(session.audio_buffer) >= int(16000 * 2 * 0.4):
                        utterance_bytes = bytes(session.audio_buffer)
                        session.audio_buffer.clear()
                        session.vad.reset()
                        await session._process_utterance(utterance_bytes, websocket)
                    if event == "stop":
                        break

    except WebSocketDisconnect:
        logger.info(f"[WebSocket] Client disconnected: {call_id}")
    except Exception as e:
        logger.error(f"[WebSocket] Error on {call_id}: {e}")
    finally:
        # 1. Save caller audio recording if audio frames were captured
        if len(session.caller_audio_record) > 0:
            try:
                rec_dir = os.path.join(os.path.dirname(__file__), "..", "static", "recordings")
                os.makedirs(rec_dir, exist_ok=True)
                wav_path = os.path.join(rec_dir, f"{call_id}.wav")
                with wave.open(wav_path, "wb") as wf:
                    wf.setnchannels(1)
                    wf.setsampwidth(2)
                    wf.setframerate(16000)
                    wf.writeframes(bytes(session.caller_audio_record))
                logger.info(f"[Session {call_id}] Saved caller audio recording to {wav_path} ({len(session.caller_audio_record)} bytes)")
            except Exception as e:
                logger.warning(f"[Session {call_id}] Could not write audio recording file: {e}")

        # 2. Precautionary Prank & Spam Filter
        duration_s = len(session.caller_audio_record) / 32000.0
        user_texts = [t["content"] for t in session.full_transcript if t.get("role") in ("caller", "user")]
        prank_res = PrankFilter.evaluate(
            call_id=call_id,
            transcripts=user_texts,
            risk_score=session.distress_state.current_score,
            duration_seconds=duration_s,
            safety_flags=session.distress_state.safety_flags.__dict__ if hasattr(session.distress_state, "safety_flags") else None
        )

        caller_num = getattr(session, "caller_phone", None) or "+91 94371-88210"

        if prank_res.is_legitimate and prank_res.ticket_id:
            summary = user_texts[0] if user_texts else "Citizen Emergency Triage Session"
            complaint = session.db.register_complaint(
                call_id=call_id,
                ticket_id=prank_res.ticket_id,
                summary=summary,
                risk_level=session.distress_state.current_level.value,
                caller_number=caller_num,
                language=session.language_router.get_session_language(call_id).value,
                recording_url=f"/api/v1/recordings/{call_id}.wav"
            )
            await broadcaster.broadcast("complaint_registered", complaint)
            logger.info(f"[Session {call_id}] Registered genuine citizen complaint: {prank_res.ticket_id} for {caller_num}")
        else:
            logger.info(f"[Session {call_id}] Prank/Spam filtered out: {prank_res.reason}")

        await session.db.update_call_status(call_id, "completed")
        await broadcaster.broadcast("call_ended", {"call_id": call_id})
        logger.info(f"[WebSocket] Cleaned up session: {call_id}")
