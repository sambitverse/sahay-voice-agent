import io
import base64
import logging
from typing import AsyncGenerator, Optional, Tuple
import httpx
from ..ports.speech import SpeechToTextProvider, TextToSpeechProvider
from .mock_speech import MockSpeechProvider

logger = logging.getLogger(__name__)


class SarvamProvider(SpeechToTextProvider, TextToSpeechProvider):
    """
    Sarvam AI adapter for Indian Language STT (Saaras) and TTS (Bulbul).
    Gracefully falls back to MockSpeechProvider if API key is not configured.
    """

    def __init__(self, api_key: str, base_url: str = "https://api.sarvam.ai"):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.fallback = MockSpeechProvider()
        self._client: Optional[httpx.AsyncClient] = None

    def is_configured(self) -> bool:
        """Returns True if a valid Sarvam API key is configured."""
        return bool(self.api_key and str(self.api_key).strip() not in ["", "your_sarvam_api_key", "None"])

    def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=12.0,
                limits=httpx.Limits(max_keepalive_connections=20, max_connections=40, keepalive_expiry=120.0)
            )
        return self._client

    async def transcribe(
        self, audio_bytes: bytes, sample_rate: int = 16000, language_code: Optional[str] = None
    ) -> Tuple[str, str, float]:
        """
        Transcribe audio using Sarvam Saaras v3.
        """
        if not self.api_key or self.api_key == "your_sarvam_api_key":
            logger.info("[SarvamProvider] No active API key; using local fallback STT.")
            return await self.fallback.transcribe(audio_bytes, sample_rate, language_code)

        url = f"{self.base_url}/speech-to-text"
        headers = {"api-subscription-key": self.api_key}

        # Ensure audio has a valid RIFF WAV header for Sarvam API
        if not audio_bytes.startswith(b"RIFF"):
            import io, wave
            buf = io.BytesIO()
            with wave.open(buf, 'wb') as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(sample_rate)
                wf.writeframes(audio_bytes)
            audio_bytes = buf.getvalue()

        try:
            client = self._get_client()
            files = {"file": ("audio.wav", audio_bytes, "audio/wav")}
            data = {"model": "saaras:v3"}
            if language_code and language_code.lower() not in ["unknown", "und"]:
                # Sarvam uses 'od-IN' for Odia
                mapped_lang = "od-IN" if "or" in language_code.lower() else language_code
                data["language_code"] = mapped_lang
            else:
                # Let Sarvam Saaras v3 auto-detect across all 22 Indian languages
                data["language_code"] = "unknown"

            response = await client.post(url, headers=headers, files=files, data=data)

            if response.status_code == 200:
                result = response.json()
                transcript = result.get("transcript", "")
                detected_lang = result.get("language_code", language_code or "od-IN")
                if "od" in detected_lang.lower():
                    detected_lang = "or-IN"
                if transcript.strip():
                    return transcript, detected_lang, 0.95
                else:
                    logger.info("[SarvamProvider] Audio contained no recognizable human words (silence/ambient noise).")
                    return "", detected_lang, 0.0
            else:
                logger.warning(f"[SarvamProvider] STT API Error {response.status_code}: {response.text}")
                return "", language_code or "or-IN", 0.0

        except Exception as e:
            logger.error(f"[SarvamProvider] STT Request Exception: {e}")
            return "", language_code or "or-IN", 0.0

    async def synthesize(
        self, text: str, language_code: str = "or-IN", speaker_gender: str = "female"
    ) -> bytes:
        """
        Synthesize text using Sarvam Bulbul v3.
        """
        if not self.api_key or self.api_key == "your_sarvam_api_key":
            logger.info("[SarvamProvider] No active API key; using local fallback TTS.")
            return await self.fallback.synthesize(text, language_code, speaker_gender)

        url = f"{self.base_url}/text-to-speech"
        headers = {
            "api-subscription-key": self.api_key,
            "Content-Type": "application/json"
        }

        # Map regional/tribal dialects to supported Sarvam TTS models
        lc = (language_code or "or-IN").lower()
        if any(d in lc for d in ["or", "od", "sp", "sat", "sambalpur", "santali", "des", "kui"]):
            mapped_lang = "od-IN"
        elif "en" in lc:
            mapped_lang = "en-IN"
        else:
            mapped_lang = "od-IN"

        speaker = "ritu" if speaker_gender == "female" else "aditya"

        # Format inputs for Sarvam bulbul:v3
        payload = {
            "inputs": [text],
            "target_language_code": mapped_lang,
            "speaker": speaker,
            "pitch": 0,
            "pace": 1.0,  # Natural conversational voice cadence
            "loudness": 1.0,
            "speech_sample_rate": 16000,
            "enable_preprocessing": True,
            "model": "bulbul:v3"
        }

        try:
            client = self._get_client()
            response = await client.post(url, headers=headers, json=payload)

            if response.status_code == 200:
                result = response.json()
                audios = result.get("audios", [])
                if audios and len(audios) > 0:
                    audio_base64 = audios[0]
                    return base64.b64decode(audio_base64)

            logger.warning(f"[SarvamProvider] TTS API Error {response.status_code}: {response.text}")
            return await self.fallback.synthesize(text, language_code, speaker_gender)

        except Exception as e:
            logger.error(f"[SarvamProvider] TTS Request Exception: {e}. Using fallback.")
            return await self.fallback.synthesize(text, language_code, speaker_gender)

    async def synthesize_stream(
        self, text: str, language_code: str = "or-IN"
    ) -> AsyncGenerator[bytes, None]:
        """Stream synthesized audio chunks."""
        full_audio = await self.synthesize(text, language_code)
        chunk_size = 3200  # 100ms at 16kHz 16-bit PCM
        for i in range(0, len(full_audio), chunk_size):
            yield full_audio[i:i + chunk_size]
