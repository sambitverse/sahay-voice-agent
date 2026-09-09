import io
import math
import wave
import struct
import logging
from typing import AsyncGenerator, Optional, Tuple
from ..ports.speech import SpeechToTextProvider, TextToSpeechProvider

logger = logging.getLogger(__name__)


class MockSpeechProvider(SpeechToTextProvider, TextToSpeechProvider):
    """Mock STT and TTS provider for offline development without paid API keys."""

    def __init__(self):
        self.mock_index = 0
        self.sample_phrases = [
            ("Mu bahut darichhi. Se mate dhamaka deichhi.", "or", 0.94),
            ("Mote emergency sahajya darkar, eithi marpit chalichi.", "or", 0.96),
            ("I need legal assistance regarding caste harassment.", "en", 0.92),
            ("Se mane mo ghara bhangideba boli dhamaka karuchhanti.", "or", 0.95),
            ("Sir I am scared, please help immediately.", "en", 0.90)
        ]

    async def transcribe(
        self, audio_bytes: bytes, sample_rate: int = 16000, language_code: Optional[str] = None
    ) -> Tuple[str, str, float]:
        """Return a simulated spoken transcript based on test audio length or cycle."""
        text, lang, conf = self.sample_phrases[self.mock_index % len(self.sample_phrases)]
        self.mock_index += 1
        logger.info(f"[MockSpeechProvider] Transcribed ({lang}): '{text}'")
        return text, lang, conf

    async def synthesize(
        self, text: str, language_code: str = "or-IN", speaker_gender: str = "female"
    ) -> bytes:
        """Generate a valid PCM WAV audio byte stream (gentle 440Hz tone simulation)."""
        logger.info(f"[MockSpeechProvider] Synthesizing ({language_code}): '{text[:50]}...'")
        sample_rate = 16000
        duration_s = max(1.0, min(len(text) * 0.06, 5.0))
        num_samples = int(sample_rate * duration_s)

        buffer = io.BytesIO()
        with wave.open(buffer, "wb") as wav_file:
            wav_file.setnchannels(1)  # Mono
            wav_file.setsampwidth(2)  # 16-bit
            wav_file.setframerate(sample_rate)

            for i in range(num_samples):
                # Gentle warm tone with envelope
                envelope = min(1.0, i / 800) * min(1.0, (num_samples - i) / 800)
                sample = int(3000 * envelope * math.sin(2 * math.pi * 330 * (i / sample_rate)))
                wav_file.writeframesraw(struct.pack("<h", sample))

        return buffer.getvalue()

    async def synthesize_stream(
        self, text: str, language_code: str = "or-IN"
    ) -> AsyncGenerator[bytes, None]:
        """Stream simulated audio in chunks."""
        full_audio = await self.synthesize(text, language_code)
        chunk_size = 3200  # 100ms chunks at 16kHz 16-bit
        for i in range(0, len(full_audio), chunk_size):
            yield full_audio[i:i + chunk_size]
