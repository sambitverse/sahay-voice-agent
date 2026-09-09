import io
import time
import base64
import logging
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, HTTPException
from ...config import settings
from ...domain.models import DistressState, RiskAssessment
from ...providers.sarvam_provider import SarvamProvider
from ...providers.gemini_provider import GeminiProvider
from ...acoustic.extractor import StandardAcousticExtractor
from ...emotion.classifier import Wav2VecEmotionClassifier
from ...distress.fusion_engine import DistressFusionEngine
from ...trauma.controller import TraumaController
from ...safety.validator import SafetyValidator

logger = logging.getLogger(__name__)
router = APIRouter()

sarvam = SarvamProvider(api_key=settings.SARVAM_API_KEY, base_url=settings.SARVAM_BASE_URL)
gemini = GeminiProvider(api_key=settings.GEMINI_API_KEY, model=settings.GEMINI_MODEL)
acoustic_extractor = StandardAcousticExtractor()
emotion_classifier = Wav2VecEmotionClassifier()
fusion_engine = DistressFusionEngine()
trauma_controller = TraumaController()


async def process_raw_audio_bytes(audio_bytes: bytes, filename: str) -> dict:
    """Core evaluation pipeline shared by file upload and sample scenarios."""
    start_time = time.time()

    # 1. Transcribe audio with Sarvam Saaras
    transcript, detected_lang, lang_conf = await sarvam.transcribe(audio_bytes, 16000)

    # 2. Extract acoustic prosody
    acoustic_signals = await acoustic_extractor.extract(audio_bytes, 16000)

    # 3. Predict emotion probabilities
    emotion_signals = await emotion_classifier.predict_emotion(audio_bytes, 16000)

    # 4. Extract linguistic threat signals
    linguistic_signals = await gemini.extract_linguistic_signals(transcript)

    # 5. Fuse multimodal distress signals
    initial_state = DistressState(call_id="diagnostic_test")
    fused_state = fusion_engine.fuse(
        current_state=initial_state,
        acoustic=acoustic_signals,
        emotion=emotion_signals,
        linguistic=linguistic_signals
    )

    # 6. Apply deterministic Trauma Controller
    assessment: RiskAssessment = trauma_controller.assess_and_control(
        call_id="diagnostic_test",
        distress_state=fused_state,
        latest_transcript=transcript
    )

    # 7. Generate empathetic conversational response
    ai_draft = await gemini.generate_response(
        conversation_history=[{"role": "user", "content": transcript}],
        system_instructions=f"Helpline 14566. Risk: {assessment.risk_level.value}. Action: {assessment.recommended_action}. Language: {detected_lang}"
    )
    safe_response, _ = SafetyValidator.validate(ai_draft, detected_lang)

    # 8. Synthesize soothing voice audio with Sarvam Bulbul
    b64_audio = None
    try:
        tts_audio = await sarvam.synthesize(safe_response, detected_lang)
        if tts_audio:
            b64_audio = base64.b64encode(tts_audio).decode("utf-8")
    except Exception as e:
        logger.warning(f"Failed to synthesize voice response: {e}")

    elapsed_ms = int((time.time() - start_time) * 1000)

    return {
        "status": "success",
        "execution_time_ms": elapsed_ms,
        "filename": filename,
        "language": {
            "detected": detected_lang,
            "confidence": lang_conf
        },
        "transcript": transcript,
        "emotion": emotion_signals.model_dump(),
        "acoustic": acoustic_signals.model_dump(),
        "linguistic": linguistic_signals.model_dump(),
        "risk": {
            "level": assessment.risk_level.value,
            "score": assessment.risk_score,
            "confidence": assessment.confidence,
            "requires_human_escalation": assessment.requires_human_escalation,
            "recommended_action": assessment.recommended_action,
            "safety_flags": assessment.safety_flags.model_dump(),
            "evidence": assessment.evidence
        },
        "ai_response": {
            "text": safe_response,
            "audio_base64": b64_audio
        }
    }


@router.post("/test/audio")
async def test_audio_pipeline(file: UploadFile = File(...)):
    """
    Offline Audio Diagnostic Test Endpoint.
    Accepts WAV, MP3, OGG, M4A, or WEBM audio chunks.
    """
    valid_exts = ('.wav', '.mp3', '.ogg', '.m4a', '.webm')
    if not file.filename.lower().endswith(valid_exts):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid audio format. Allowed: {', '.join(valid_exts)}"
        )

    audio_bytes = await file.read()
    if len(audio_bytes) < 100:
        raise HTTPException(status_code=400, detail="Audio file is empty or corrupted.")

    try:
        return await process_raw_audio_bytes(audio_bytes, file.filename)
    except Exception as e:
        logger.error(f"Diagnostic audio test failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Diagnostic error: {str(e)}")


@router.get("/test/sample/{scenario_name}")
async def test_sample_scenario(scenario_name: str):
    """
    Runs evaluation on pre-recorded scenario audio files directly from the server.
    """
    # Locate data directory relative to repository root
    repo_root = Path(__file__).resolve().parents[4]
    scenario_files = {
        "odia_threat": repo_root / "data" / "test_audio" / "odia" / "threat_01.wav",
        "odia_calm": repo_root / "data" / "test_audio" / "odia" / "scenario_01_calm.wav",
        "english_distress": repo_root / "data" / "test_audio" / "english" / "distress_01.wav",
        "odia_critical": repo_root / "data" / "test_audio" / "odia" / "scenario_04_critical.wav",
        "odia_codeswitch": repo_root / "data" / "test_audio" / "odia" / "scenario_05_codeswitch.wav",
    }

    file_path = scenario_files.get(scenario_name)
    if not file_path or not file_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Scenario '{scenario_name}' not found. Available: {list(scenario_files.keys())}"
        )

    audio_bytes = file_path.read_bytes()
    return await process_raw_audio_bytes(audio_bytes, file_path.name)
