from abc import ABC, abstractmethod
from typing import AsyncGenerator, Optional, Tuple


class SpeechToTextProvider(ABC):
    """Abstract interface for Speech-to-Text providers (Sarvam, Bhashini, Whisper)."""

    @abstractmethod
    async def transcribe(
        self, audio_bytes: bytes, sample_rate: int = 16000, language_code: Optional[str] = None
    ) -> Tuple[str, str, float]:
        """
        Transcribe raw PCM/WAV audio bytes.
        Returns: (transcript_text, detected_language_code, confidence)
        """
        pass


class TextToSpeechProvider(ABC):
    """Abstract interface for Text-to-Speech providers (Sarvam Bulbul, Bhashini TTS)."""

    @abstractmethod
    async def synthesize(
        self, text: str, language_code: str = "or-IN", speaker_gender: str = "female"
    ) -> bytes:
        """
        Synthesize text into audio bytes (WAV/MP3/PCM).
        """
        pass

    @abstractmethod
    async def synthesize_stream(
        self, text: str, language_code: str = "or-IN"
    ) -> AsyncGenerator[bytes, None]:
        """
        Stream synthesized audio chunks as they become available.
        """
        pass
