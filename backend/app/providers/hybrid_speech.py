import logging
from typing import AsyncGenerator, Optional, Tuple
from ..ports.speech import SpeechToTextProvider, TextToSpeechProvider
from .sarvam_provider import SarvamProvider
from .bhashini_provider import BhashiniProvider
from .mock_speech import MockSpeechProvider

logger = logging.getLogger(__name__)


class HybridSpeechProvider(SpeechToTextProvider, TextToSpeechProvider):
    """
    High-Availability Hybrid Speech Pipeline integrating Sarvam AI & Government BHASHINI.
    - Uses Sarvam Saaras for primary ultra-low-latency ASR / TTS.
    - Automatically fails over to Government BHASHINI (Dhruva) if Sarvam encounters an issue or quota limit.
    - Provides zero-downtime resilience for critical emergency triage calls.
    """

    def __init__(
        self,
        sarvam_api_key: str,
        sarvam_base_url: str,
        bhashini_auth_token: str,
        bhashini_user_id: str = "",
        bhashini_api_key: str = "",
        bhashini_inference_url: str = "https://dhruva-api.bhashini.gov.in",
        primary_provider: str = "bhashini"
    ):
        self.primary_provider = primary_provider.lower()
        self.sarvam = SarvamProvider(api_key=sarvam_api_key, base_url=sarvam_base_url)
        self.bhashini = BhashiniProvider(
            auth_token=bhashini_auth_token,
            user_id=bhashini_user_id,
            api_key=bhashini_api_key,
            inference_url=bhashini_inference_url
        )
        self.mock_fallback = MockSpeechProvider()

    def is_configured(self) -> bool:
        """Returns True if at least one speech provider is configured."""
        return self.bhashini.is_configured() or self.sarvam.is_configured()

    async def transcribe(
        self, audio_bytes: bytes, sample_rate: int = 16000, language_code: Optional[str] = None
    ) -> Tuple[str, str, float]:
        """Transcribes audio trying primary provider, with automatic fallback to secondary."""
        first, second = (self.sarvam, self.bhashini) if self.primary_provider == "sarvam" else (self.bhashini, self.sarvam)
        first_name, second_name = ("Sarvam", "Bhashini") if self.primary_provider == "sarvam" else ("Bhashini", "Sarvam")

        try:
            transcript, lang, conf = await first.transcribe(audio_bytes, sample_rate, language_code)
            if transcript.strip():
                return transcript, lang, conf
            logger.info(f"[HybridSpeechProvider] {first_name} STT returned empty. Trying {second_name}...")
        except Exception as e:
            logger.warning(f"[HybridSpeechProvider] {first_name} STT failed: {e}. Failing over to {second_name}...")

        # Fallover to second provider
        try:
            logger.info(f"[HybridSpeechProvider] Routing STT to {second_name}...")
            transcript, lang, conf = await second.transcribe(audio_bytes, sample_rate, language_code)
            if transcript.strip():
                return transcript, lang, conf
        except Exception as e:
            logger.error(f"[HybridSpeechProvider] Both {first_name} and {second_name} STT failed: {e}.")

        return "", language_code or "or-IN", 0.0

    async def synthesize(
        self, text: str, language_code: str = "or-IN", speaker_gender: str = "female"
    ) -> bytes:
        """Synthesizes speech trying primary provider, with automatic failover to secondary."""
        first, second = (self.sarvam, self.bhashini) if self.primary_provider == "sarvam" else (self.bhashini, self.sarvam)
        first_name, second_name = ("Sarvam", "Bhashini") if self.primary_provider == "sarvam" else ("Bhashini", "Sarvam")

        try:
            audio = await first.synthesize(text, language_code, speaker_gender)
            if audio and len(audio) > 100:
                return audio
            logger.info(f"[HybridSpeechProvider] {first_name} TTS returned empty audio. Failing over to {second_name}...")
        except Exception as e:
            logger.warning(f"[HybridSpeechProvider] {first_name} TTS failed: {e}. Failing over to {second_name}...")

        # Fallover to second provider
        try:
            logger.info(f"[HybridSpeechProvider] Routing TTS to {second_name}...")
            audio = await second.synthesize(text, language_code, speaker_gender)
            if audio and len(audio) > 100:
                return audio
        except Exception as e:
            logger.error(f"[HybridSpeechProvider] Both {first_name} and {second_name} TTS failed: {e}.")

        return b""

    async def synthesize_stream(
        self, text: str, language_code: str = "or-IN"
    ) -> AsyncGenerator[bytes, None]:
        """Streams synthesized speech chunks."""
        full_audio = await self.synthesize(text, language_code=language_code)
        chunk_size = 4096
        for i in range(0, len(full_audio), chunk_size):
            yield full_audio[i:i + chunk_size]
