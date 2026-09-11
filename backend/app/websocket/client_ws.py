import os
import re
import io
import math
import wave
import struct
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

GREETINGS_TEXT: Dict[str, str] = {
    "hi-IN": "Namaskar. Rashtriya Helpline 14566 mein aapka swagat hai. Kripya apni samasya batayein.",
    "or-IN": "Namaskar. NHAA 14566 helpline re apananku swagata. Daya kari apananka samasya kuhan tu.",
    "en-IN": "Hello. Welcome to the National Helpline Against Atrocities (14566). Please tell us how we can help you.",
    "sat-IN": "Johar. NHAA 14566 helpline re sagun daram. Daya kate apanar samasya lai tabon pe.",
    "des-IN": "Namaskar. NHAA 14566 helpline re apananku swagata. Daya kari apananka samasya kuhan tu.",
    "kui-IN": "Namaskar. NHAA 14566 helpline re apananku swagata. Daya kari apananka samasya kuhan tu.",
    "kuvi-IN": "Namaskar. NHAA 14566 helpline re apananku swagata. Daya kari apananka samasya kuhan tu.",
    "unknown": "Namaskar. NHAA 14566 helpline re apananku swagata. Daya kari apananka samasya kuhan tu."
}

def is_response_language_consistent(resp: str, target_lang_code: str) -> bool:
    """Verifies that generated response is not contaminated by scripts or words of other languages."""
    if not resp or not resp.strip():
        return True
    resp_clean = resp.strip()
    lc = (target_lang_code or "or-IN").lower()

    if "hi" in lc:
        if re.search(r'[\u0b00-\u0b7f]', resp_clean):
            return False
        eng_tokens = len(re.findall(r'\b(?:i|you|are|we|help|need|call|safe|police|please|hello|welcome)\b', resp_clean.lower()))
        hi_tokens = len(re.findall(r'\b(?:main|aap|hum|hai|hain|kripya|madad|surakshit|batayein|hoon|ho|shikayat|darj|chinta|rahein)\b', resp_clean.lower()))
        has_devanagari = bool(re.search(r'[\u0900-\u0963\u0966-\u097f]', resp_clean))
        if not has_devanagari and eng_tokens >= 4 and hi_tokens == 0:
            return False
    elif "or" in lc or "od" in lc:
        if re.search(r'[\u0900-\u0963\u0966-\u097f]', resp_clean):
            return False
        eng_tokens = len(re.findall(r'\b(?:i|you|are|we|help|need|call|safe|police|please|hello|welcome)\b', resp_clean.lower()))
        or_tokens = len(re.findall(r'\b(?:mu|apan|amara|achhi|achhanti|sahajya|surakshita|kuhan|ruhantu|bujhiparuchhi|abhiboga)\b', resp_clean.lower()))
        has_odia = bool(re.search(r'[\u0b00-\u0b7f]', resp_clean))
        if not has_odia and eng_tokens >= 4 and or_tokens == 0:
            return False
    elif "en" in lc:
        if re.search(r'[\u0900-\u0963\u0966-\u097f]|[\u0b00-\u0b7f]', resp_clean):
            return False

    return True

def get_cached_greeting_b64() -> Optional[str]:
    global _CACHED_GREETING_B64
    if _CACHED_GREETING_B64 is None and os.path.exists(_CACHED_GREETING_PATH):
        try:
            with open(_CACHED_GREETING_PATH, "rb") as f:
                _CACHED_GREETING_B64 = base64.b64encode(f.read()).decode("utf-8")
        except Exception as e:
            logger.warning(f"Failed to read cached greeting file: {e}")
            sample_rate = 16000
            duration_s = max(1.0, min(len(_CACHED_GREETING_TEXT) * 0.055, 5.0))
            num_samples = int(sample_rate * duration_s)
            buf = io.BytesIO()
            with wave.open(buf, "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(sample_rate)
                for i in range(num_samples):
                    envelope = min(1.0, i / 800) * min(1.0, (num_samples - i) / 800)
                    sample = int(2500 * envelope * math.sin(2 * math.pi * 330 * (i / sample_rate)))
                    wf.writeframesraw(struct.pack("<h", sample))
            _CACHED_GREETING_B64 = base64.b64encode(buf.getvalue()).decode("utf-8")
    return _CACHED_GREETING_B64

from ..config import settings
from ..domain.models import DistressState, RiskAssessment, RiskLevel, AcousticSignals, EmotionSignals
from ..audio.vad import VoiceActivityDetector
from ..audio.resampler import AudioResampler
from ..providers.sarvam_provider import SarvamProvider
from ..providers.bhashini_provider import BhashiniProvider
from ..providers.hybrid_speech import HybridSpeechProvider
from ..providers.gemini_provider import GeminiProvider
from ..acoustic.extractor import StandardAcousticExtractor
from ..emotion.classifier import Wav2VecEmotionClassifier
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
        self.bhashini = BhashiniProvider(
            auth_token=settings.BHASHINI_AUTH_TOKEN,
            user_id=settings.BHASHINI_USER_ID,
            api_key=settings.BHASHINI_API_KEY,
            inference_url=settings.BHASHINI_INFERENCE_URL
        )
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
        self.turn_in_progress = False
        self.current_tts_task: Optional[asyncio.Task] = None
        self.turn_lock = asyncio.Lock()
        self.caller_phone: str = "+91 94371-88210"
        self.active_lang = SupportedLanguage.ODIA
        self.last_processed_text: Optional[str] = None
        self.last_turn_completed_time: float = 0.0
        self.latest_acoustic: AcousticSignals = AcousticSignals()
        self.latest_emotion: EmotionSignals = EmotionSignals()
        self.latest_transcript: str = ""
        self._vad_debug_counter: int = 0

    async def init_session(self, initial_language: Optional[str] = None) -> None:
        """Record session in database and announce to live operator dashboard."""
        if initial_language and initial_language != "auto":
            try:
                self.active_lang = self.language_router.set_session_language(self.call_id, initial_language)
            except Exception:
                self.active_lang = SupportedLanguage.ODIA
        else:
            self.active_lang = SupportedLanguage.ODIA

        await self.db.create_call_session(
            external_call_id=self.call_id,
            phone_hash=self.phone_hash,
            telephony_provider="web_audio",
            detected_language=self.active_lang.value
        )
        await broadcaster.broadcast("call_started", {
            "call_id": self.call_id,
            "phone_hash": self.phone_hash,
            "status": "initiated",
            "language": self.active_lang.value
        })

    async def handle_audio_frame(self, frame_pcm: bytes, websocket: WebSocket) -> None:
        """Process incoming 16kHz PCM audio chunk from caller."""
        if self.is_ai_speaking or self.turn_in_progress:
            return

        is_speech = self.vad.process_frame(frame_pcm)

        # Emit VAD debug telemetry every ~8 frames (160ms)
        self._vad_debug_counter += 1
        if self._vad_debug_counter % 8 == 0 and hasattr(self.vad, "last_debug") and self.vad.last_debug:
            try:
                await websocket.send_json({
                    "event": "vad_debug",
                    **self.vad.last_debug
                })
            except Exception:
                pass

        if is_speech:
            self.audio_buffer.extend(frame_pcm)
            self.caller_audio_record.extend(frame_pcm)
            if len(self.audio_buffer) >= int(16000 * 2 * 30.0):
                logger.info(f"[Session {self.call_id}] Utterance reached 30.0s cap. Auto-committing.")
                utterance_bytes = bytes(self.audio_buffer)
                self.audio_buffer.clear()
                self.vad.reset()
                asyncio.create_task(self._process_utterance(utterance_bytes, websocket))
        else:
            if len(self.audio_buffer) >= int(16000 * 2 * 0.35):
                trailing_silence_bytes = int(16000 * 2 * 0.35)
                if len(self.audio_buffer) > trailing_silence_bytes + int(16000 * 2 * 0.25):
                    utterance_bytes = bytes(self.audio_buffer[:-trailing_silence_bytes])
                else:
                    utterance_bytes = bytes(self.audio_buffer)

                self.audio_buffer.clear()
                self.vad.reset()
                asyncio.create_task(self._process_utterance(utterance_bytes, websocket))

    async def _process_utterance(self, audio_bytes: bytes, websocket: WebSocket) -> None:
        """Run full multimodal perception, fusion, reasoning, and response generation with turn serialization."""
        async with self.turn_lock:
            await self._execute_turn(audio_bytes, websocket)

    async def _process_text_utterance(self, text: str, websocket: WebSocket, language_hint: Optional[str] = None) -> None:
        """Run reasoning and response generation from direct user speech text or browser speech recognition."""
        async with self.turn_lock:
            await self._execute_turn(b"", websocket, text_override=text, language_hint=language_hint)

    async def _execute_turn(
        self,
        audio_bytes: bytes,
        websocket: WebSocket,
        text_override: Optional[str] = None,
        language_hint: Optional[str] = None
    ) -> None:
        if self.turn_in_progress:
            logger.info(f"[Session {self.call_id}] Turn already in progress; dropping duplicate input.")
            return

        self.turn_in_progress = True
        try:
            self.audio_buffer.clear()
            self.vad.reset()

            raw_transcript = ""
            raw_detected_lang = language_hint or "unknown"

            if text_override and text_override.strip():
                raw_transcript = text_override.strip()
                now = asyncio.get_event_loop().time()
                if self.last_processed_text and raw_transcript.lower() == self.last_processed_text.lower() and (now - self.last_turn_completed_time < 3.5):
                    logger.info(f"[Session {self.call_id}] Duplicate user input text dropped: '{raw_transcript}'")
                    self.turn_in_progress = False
                    return
                acoustic_signals = getattr(self, "latest_acoustic", AcousticSignals())
                emotion_signals = getattr(self, "latest_emotion", EmotionSignals())
            elif audio_bytes and len(audio_bytes) > 0:
                # Fast vehicle horn & ambient silence filter
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
                            continue
                        active_frames += 1

                        mags = np.abs(np.fft.rfft(chunk * hanning_w))
                        sum_mags = float(np.sum(mags)) + 1e-6
                        max_idx = int(np.argmax(mags))
                        peak_freq = float(max_idx * (16000.0 / frame_size))
                        top2_ratio = float(np.sum(np.partition(mags, -2)[-2:])) / sum_mags
                        top4_ratio = float(np.sum(np.partition(mags, -4)[-4:])) / sum_mags

                        if 300.0 <= peak_freq <= 4200.0 and (
                            top4_ratio > 0.70 and top2_ratio > 0.38 and (top2_ratio + top4_ratio) > 1.10
                        ):
                            horn_frames += 1
                            if peak_freq > max_horn_freq:
                                max_horn_freq = peak_freq

                    if active_frames >= 6 and (horn_frames / active_frames) > 0.60:
                        logger.info(f"[Session {self.call_id}] Discarding utterance: vehicle horn ({horn_frames}/{active_frames} frames)")
                        await websocket.send_json({
                            "event": "noise_ignored",
                            "message": f"Filtered vehicle horn sound ({max_horn_freq:.0f}Hz)"
                        })
                        self.turn_in_progress = False
                        return

                    if active_frames < 2 or len(samples) < 5500:
                        logger.info(f"[Session {self.call_id}] Discarding utterance: ambient silence ({active_frames} voiced frames)")
                        await websocket.send_json({
                            "event": "noise_ignored",
                            "message": "Filtered ambient silence"
                        })
                        self.turn_in_progress = False
                        return

                if self.turn_count == 0:
                    mapped_lang = "unknown"
                else:
                    current_lang = self.language_router.get_session_language(self.call_id)
                    mapped_lang = "od-IN" if "or" in current_lang.value.lower() else current_lang.value

                if self.speech.is_configured():
                    stt_task = asyncio.create_task(self.speech.transcribe(audio_bytes, 16000, language_code=mapped_lang))
                else:
                    stt_task = asyncio.create_task(self.gemini.transcribe_audio(audio_bytes, 16000, language_hint=mapped_lang))

                acoustic_task = asyncio.create_task(self.acoustic_extractor.extract(audio_bytes, 16000))
                emotion_task = asyncio.create_task(self.emotion_classifier.predict_emotion(audio_bytes, 16000))

                raw_transcript, raw_detected_lang, lang_conf = await stt_task
                acoustic_signals = await acoustic_task
                emotion_signals = await emotion_task
                self.latest_acoustic = acoustic_signals
                self.latest_emotion = emotion_signals

            stripped_transcript = raw_transcript.strip()
            if not stripped_transcript:
                logger.info(f"[Session {self.call_id}] Empty audio ({len(audio_bytes)} bytes) discarded.")
                await websocket.send_json({
                    "event": "noise_ignored",
                    "message": "Filtered ambient background noise"
                })
                self.turn_in_progress = False
                return

            now = asyncio.get_event_loop().time()
            if self.last_processed_text and stripped_transcript.lower() == self.last_processed_text.lower() and (now - self.last_turn_completed_time < 3.5):
                logger.info(f"[Session {self.call_id}] Duplicate audio transcript dropped: '{stripped_transcript}'")
                self.turn_in_progress = False
                return

            self.turn_count += 1
            logger.info(f"[Session {self.call_id}] Starting turn {self.turn_count} perception: '{raw_transcript}' (lang: {raw_detected_lang})")

            hint_lc = (language_hint or "").lower()
            if "hi" in hint_lc or bool(re.search(r'[\u0900-\u097f]', raw_transcript)):
                class _HindiLang:
                    value = "hi-IN"
                active_lang = _HindiLang()
            else:
                active_lang = self.language_router.resolve_language(
                    call_id=self.call_id,
                    transcript=raw_transcript,
                    stt_detected_lang=raw_detected_lang,
                    language_hint=language_hint
                )
            self.active_lang = active_lang
            self.latest_transcript = raw_transcript

            if self.turn_count == 1 and self.conversation_history:
                target_greeting = GREETINGS_TEXT.get(active_lang.value, GREETINGS_TEXT["or-IN"])
                if self.conversation_history[0].get("role") in ("agent", "model"):
                    self.conversation_history[0]["content"] = target_greeting

            normalized_transcript = DialectBridge.normalize_dialect(raw_transcript, active_lang.value)

            await websocket.send_json({
                "event": "user_transcript",
                "text": raw_transcript,
                "language": active_lang.value,
                "normalized_text": normalized_transcript if normalized_transcript != raw_transcript else None
            })

            self.full_transcript.append({"role": "caller", "content": raw_transcript})
            asyncio.create_task(self.db.save_transcript_segment(
                external_call_id=self.call_id,
                speaker="caller",
                text_content=raw_transcript,
                sequence_num=self.turn_count,
                language=active_lang.value
            ))

            linguistic_signals = await self.gemini.extract_linguistic_signals(normalized_transcript)

            self.distress_state = self.fusion_engine.fuse(
                current_state=self.distress_state,
                acoustic=acoustic_signals,
                emotion=emotion_signals,
                linguistic=linguistic_signals
            )

            assessment: RiskAssessment = self.trauma_controller.assess_and_control(
                call_id=self.call_id,
                distress_state=self.distress_state,
                latest_transcript=normalized_transcript
            )

            conv_state = self.state_machine.transition(
                call_id=self.call_id,
                risk_level=assessment.risk_level.value,
                turn_count=self.turn_count,
                requires_escalation=assessment.requires_human_escalation
            )

            rag_context = self.rag_retriever.retrieve_context(
                query=normalized_transcript,
                risk_level=assessment.risk_level.value,
                language_code=active_lang.value,
                top_k=2
            )

            sbar_handoff = None
            if assessment.requires_human_escalation or assessment.risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]:
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

            asyncio.create_task(self.db.save_risk_assessment(
                external_call_id=self.call_id,
                risk_score=assessment.risk_score,
                risk_level=assessment.risk_level.value,
                safety_flags=assessment.safety_flags.model_dump(),
                evidence_summary=assessment.evidence,
                recommended_action=assessment.recommended_action,
                requires_human_escalation=assessment.requires_human_escalation
            ))

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

            self.conversation_history.append({"role": "caller", "content": raw_transcript})

            system_instructions = self.state_machine.get_system_prompt_for_state(
                state=conv_state,
                language_code=active_lang.value,
                risk_level=assessment.risk_level.value,
                latest_transcript=normalized_transcript
            )

            lang_label = {
                "or-IN": "ODIA",
                "hi-IN": "HINDI",
                "en-IN": "ENGLISH",
                "sat-IN": "SANTALI",
                "des-IN": "DESIA",
                "kui-IN": "KUI",
                "kuvi-IN": "KUVI",
            }.get(active_lang.value, active_lang.value)

            lang_mandate = (
                f"\n\n[MANDATORY STRICT USER LANGUAGE DIRECTIVE - ZERO TOLERANCE]:\n"
                f"- The caller's language is strictly {lang_label} ({active_lang.value}).\n"
                f"- Caller's latest utterance: '{raw_transcript}'.\n"
                f"- CRITICAL REQUIREMENT: You MUST formulate your entire response STRICTLY in {lang_label}.\n"
                f"- ABSOLUTE PROHIBITION: Under NO circumstances should you respond in any other language!\n"
                f"  * If language is HINDI: do NOT speak Odia or English. Output natural, comforting spoken Hindi.\n"
                f"  * If language is ODIA: do NOT speak Hindi or English. Output natural, comforting spoken Odia.\n"
                f"  * If language is ENGLISH: do NOT speak Hindi or Odia. Output clear Indian English.\n"
                f"- FAST SPOKEN VOICE REQUIREMENT: Keep your response very brief and to the point — at most 1 to 2 short sentences (under 25 words total). Never ramble, lecture, or explain procedures at length. Ask one clear question or give one immediate instruction."
            )
            system_instructions += lang_mandate

            try:
                raw_ai_response = await asyncio.wait_for(
                    self.gemini.generate_response(
                        conversation_history=self.conversation_history[-6:],
                        system_instructions=system_instructions,
                        retrieved_context=rag_context
                    ),
                    timeout=15.0
                )
            except asyncio.TimeoutError:
                logger.warning(f"[Session {self.call_id}] Gemini response timed out; using fallback.")
                raw_ai_response = self.state_machine.get_fallback_phrase(active_lang.value, conv_state, latest_transcript=normalized_transcript)
            except Exception as e:
                logger.warning(f"[Session {self.call_id}] Gemini generation exception: {e}; using fallback.")
                raw_ai_response = self.state_machine.get_fallback_phrase(active_lang.value, conv_state, latest_transcript=normalized_transcript)

            safe_response, is_valid = SafetyValidator.validate(raw_ai_response, active_lang.value, caller_transcript=normalized_transcript)

            if not is_response_language_consistent(safe_response, active_lang.value):
                logger.warning(
                    f"[LanguageGuardrail] LLM response deviated from target language {active_lang.value}: "
                    f"'{safe_response[:60]}'. Replacing with certified fallback."
                )
                safe_response = self.state_machine.get_fallback_phrase(
                    active_lang.value, conv_state, latest_transcript=normalized_transcript
                )

            self.conversation_history.append({"role": "agent", "content": safe_response})
            self.full_transcript.append({"role": "agent", "content": safe_response})

            asyncio.create_task(self.db.save_transcript_segment(
                external_call_id=self.call_id,
                speaker="agent",
                text_content=safe_response,
                sequence_num=self.turn_count,
                language=active_lang.value
            ))

            self.last_processed_text = raw_transcript
            self.last_turn_completed_time = asyncio.get_event_loop().time()

            await websocket.send_json({
                "event": "agent_response",
                "text": safe_response,
                "language": active_lang.value,
                "risk_level": assessment.risk_level.value,
                "phase": conv_state.value
            })

            asyncio.create_task(broadcaster.broadcast("agent_response", {
                "call_id": self.call_id,
                "text": safe_response,
                "risk_level": assessment.risk_level.value
            }))

            self.is_ai_speaking = True
            if self.speech.is_configured():
                tts_audio = await self.speech.synthesize(safe_response, active_lang.value)
            else:
                tts_audio = b""

            if self.is_ai_speaking and tts_audio:
                b64_audio = base64.b64encode(tts_audio).decode("utf-8")
                await websocket.send_json({
                    "event": "media",
                    "payload": b64_audio,
                    "sample_rate": 16000
                })

                approx_duration = max(1.0, len(tts_audio) / 32000.0)
                async def _auto_clear_speaking():
                    await asyncio.sleep(approx_duration + 1.2)
                    self.is_ai_speaking = False
                    self.turn_in_progress = False
                asyncio.create_task(_auto_clear_speaking())
            else:
                self.is_ai_speaking = False
                self.turn_in_progress = False
                await websocket.send_json({
                    "event": "tts_unavailable",
                    "text": safe_response,
                    "language": active_lang.value
                })

        except Exception as e:
            logger.error(f"[Session {self.call_id}] Processing error: {e}", exc_info=True)
            self.is_ai_speaking = False
            self.turn_in_progress = False
            try:
                target_lang = getattr(self, "active_lang", SupportedLanguage.ODIA).value
                emergency_msg = self.state_machine.get_fallback_phrase(
                    target_lang,
                    ConversationState.PROBLEM_ASSESSMENT,
                    latest_transcript=getattr(self, "latest_transcript", "")
                )
                tts_err = await self.sarvam.synthesize(emergency_msg, target_lang)
                if tts_err:
                    await websocket.send_json({
                        "event": "agent_response",
                        "text": emergency_msg,
                        "risk_level": "LOW",
                        "phase": "PROBLEM_ASSESSMENT",
                        "language": target_lang
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
    initial_language = websocket.query_params.get("language")
    phone_param = websocket.query_params.get("phone")
    name_param = websocket.query_params.get("name")
    logger.info(f"[WebSocket] Connected client session: {call_id} (lang: {initial_language}, phone: {phone_param}, name: {name_param})")

    session = ClientAudioSession(call_id)
    if phone_param:
        session.caller_phone = phone_param
        session.phone_hash = SupabaseManager.hash_phone(phone_param)
    if name_param:
        session.caller_name = name_param.strip()

    await session.init_session(initial_language=initial_language)

    try:
        await websocket.send_json({
            "event": "connected",
            "call_id": call_id,
            "message": "Connected to NHAA (14566) Voice Triage Gateway",
            "language": session.active_lang.value
        })

        greeting_lang = session.active_lang.value if session.active_lang != SupportedLanguage.UNKNOWN else SupportedLanguage.ODIA.value
        greeting_text = GREETINGS_TEXT.get(greeting_lang, GREETINGS_TEXT["or-IN"])
        session.conversation_history.append({"role": "agent", "content": greeting_text})

        cached_b64 = get_cached_greeting_b64() if greeting_lang == "or-IN" else None
        if cached_b64:
            session.is_ai_speaking = True
            await websocket.send_json({
                "event": "agent_response",
                "text": greeting_text,
                "risk_level": "LOW",
                "phase": "GREETING",
                "language": greeting_lang
            })
            await websocket.send_json({
                "event": "media",
                "payload": cached_b64,
                "sample_rate": 16000
            })
            async def _auto_clear_cached_greeting():
                await asyncio.sleep(4.0)
                session.is_ai_speaking = False
                session.turn_in_progress = False
            asyncio.create_task(_auto_clear_cached_greeting())
        else:
            try:
                if session.speech.is_configured():
                    greeting_audio = await session.speech.synthesize(greeting_text, greeting_lang)
                else:
                    greeting_audio = b""
                if greeting_audio:
                    b64_greeting = base64.b64encode(greeting_audio).decode("utf-8")
                    session.is_ai_speaking = True
                    await websocket.send_json({
                        "event": "agent_response",
                        "text": greeting_text,
                        "risk_level": "LOW",
                        "phase": "GREETING",
                        "language": greeting_lang
                    })
                    await websocket.send_json({
                        "event": "media",
                        "payload": b64_greeting,
                        "sample_rate": 16000
                    })
                    approx_dur = max(2.0, len(greeting_audio) / 32000.0)
                    async def _auto_clear_live_greeting():
                        await asyncio.sleep(approx_dur + 1.2)
                        session.is_ai_speaking = False
                        session.turn_in_progress = False
                    asyncio.create_task(_auto_clear_live_greeting())
            except Exception as e:
                logger.warning(f"[WebSocket] Initial greeting synthesis warning: {e}")

        while True:
            message = await websocket.receive()

            if "bytes" in message and message["bytes"]:
                await session.handle_audio_frame(message["bytes"], websocket)

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
                    if payload_b64 and not session.is_ai_speaking and not session.turn_in_progress:
                        pcm_bytes = base64.b64decode(payload_b64)
                        session.caller_audio_record.extend(pcm_bytes)
                        logger.info(f"[WebSocket] Processing complete caller utterance: {len(pcm_bytes)} bytes")
                        asyncio.create_task(session._process_utterance(pcm_bytes, websocket))

                elif event in ("user_speech", "chat_message"):
                    user_text = data.get("text", "").strip()
                    if user_text:
                        if session.is_ai_speaking or session.turn_in_progress:
                            logger.info(f"[WebSocket] Dropping user input: AI speaking or turn in progress for {call_id}: '{user_text}'")
                            continue

                        # Echo suppression
                        is_echo = False
                        recent_agent_texts = [_CACHED_GREETING_TEXT.lower()]
                        if session.conversation_history:
                            recent_agent_texts.extend([
                                msg.get("content", "").lower()
                                for msg in session.conversation_history[-4:]
                                if msg.get("role") in ("agent", "model")
                            ])
                        u_clean = re.sub(r'[^\w\s]', '', user_text.lower()).strip()
                        u_words = [w for w in u_clean.split() if len(w) > 2]
                        if u_words:
                            for a_text in recent_agent_texts:
                                a_clean = re.sub(r'[^\w\s]', '', a_text).strip()
                                if u_clean in a_clean or a_clean in u_clean:
                                    is_echo = True
                                    break
                                matches = sum(1 for w in u_words if w in a_clean)
                                if matches / len(u_words) >= 0.40:
                                    is_echo = True
                                    break
                        if is_echo:
                            logger.info(f"[WebSocket] Suppressed acoustic echo from client microphone for {call_id}: '{user_text}'")
                            continue

                        logger.info(f"[WebSocket] User direct speech/text received for {call_id}: '{user_text}'")
                        lang_hint = data.get("language")
                        asyncio.create_task(session._process_text_utterance(user_text, websocket, lang_hint))

                elif event == "barge_in":
                    logger.info(f"[WebSocket] Client confirmed human barge-in on session: {call_id}")
                    session.is_ai_speaking = False
                    session.turn_in_progress = False
                    session.audio_buffer.clear()
                    session.vad.reset()
                    if session.current_tts_task and not session.current_tts_task.done():
                        session.current_tts_task.cancel()

                elif event == "ai_speaking_ended":
                    session.is_ai_speaking = False
                    session.turn_in_progress = False
                    session.audio_buffer.clear()
                    session.vad.reset()

                elif event == "set_language":
                    lang = data.get("language", "auto")
                    active_l = session.language_router.set_session_language(call_id, lang)
                    session.active_lang = active_l if active_l != SupportedLanguage.UNKNOWN else session.language_router.get_session_language(call_id)
                    if session.turn_count == 0 and session.conversation_history:
                        new_greet = GREETINGS_TEXT.get(session.active_lang.value, GREETINGS_TEXT["or-IN"])
                        session.conversation_history[0] = {"role": "agent", "content": new_greet}
                    logger.info(f"[WebSocket] User selected language: {lang} (active: {session.active_lang.value}) for session: {call_id}")
                    await websocket.send_json({
                        "event": "language_updated",
                        "language": lang if lang == "auto" else session.active_lang.value
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
        # Save caller audio recording if audio frames were captured
        rec_dir = os.path.join(os.path.dirname(__file__), "..", "static", "recordings")
        os.makedirs(rec_dir, exist_ok=True)
        wav_path = os.path.join(rec_dir, f"{call_id}.wav")

        if len(session.caller_audio_record) > 0:
            try:
                with wave.open(wav_path, "wb") as wf:
                    wf.setnchannels(1)
                    wf.setsampwidth(2)
                    wf.setframerate(16000)
                    wf.writeframes(bytes(session.caller_audio_record))
                logger.info(f"[Session {call_id}] Saved caller audio recording to {wav_path} ({len(session.caller_audio_record)} bytes)")
            except Exception as e:
                logger.warning(f"[Session {call_id}] Could not write audio recording file: {e}")

        # Precautionary Prank & Spam Filter
        duration_s = len(session.caller_audio_record) / 32000.0 if len(session.caller_audio_record) > 0 else 0.0
        user_texts = [t["content"] for t in session.full_transcript if t.get("role") in ("caller", "user")]
        prank_res = PrankFilter.evaluate(
            call_id=call_id,
            transcripts=user_texts,
            risk_score=session.distress_state.current_score,
            duration_seconds=duration_s,
            safety_flags=session.distress_state.safety_flags.__dict__ if hasattr(session.distress_state, "safety_flags") else None
        )

        caller_num = getattr(session, "caller_phone", None) or "+91 94371-88210"
        caller_name = getattr(session, "caller_name", None) or f"Citizen ({caller_num})"
        summary = user_texts[0] if user_texts else "Microphone Voice Stream Session"
        lang_val = session.language_router.get_session_language(call_id).value

        # Persist in SQLite Voice Recordings Database
        if os.path.exists(wav_path):
            try:
                from app.database import recordings_db
                rec_entry = recordings_db.save_recording(
                    call_id=call_id,
                    caller_name=caller_name,
                    caller_phone=caller_num,
                    duration_seconds=duration_s,
                    file_path=wav_path,
                    recording_url=f"/api/v1/recordings/{call_id}.wav",
                    risk_level=session.distress_state.current_level.value,
                    summary=summary,
                    language=lang_val
                )
                await broadcaster.broadcast("recording_saved", rec_entry)
            except Exception as dbe:
                logger.error(f"[Session {call_id}] Failed to save to recordings_db: {dbe}")

        if prank_res.is_legitimate and prank_res.ticket_id:
            complaint = session.db.register_complaint(
                call_id=call_id,
                ticket_id=prank_res.ticket_id,
                summary=summary,
                risk_level=session.distress_state.current_level.value,
                caller_number=caller_num,
                language=lang_val,
                recording_url=f"/api/v1/recordings/{call_id}.wav"
            )
            await broadcaster.broadcast("complaint_registered", complaint)
            logger.info(f"[Session {call_id}] Registered genuine citizen complaint: {prank_res.ticket_id} for {caller_num}")
        else:
            logger.info(f"[Session {call_id}] Prank/Spam filtered: {prank_res.reason}")

        await session.db.update_call_status(call_id, "completed")
        await broadcaster.broadcast("call_ended", {"call_id": call_id})
        logger.info(f"[WebSocket] Cleaned up session: {call_id}")
