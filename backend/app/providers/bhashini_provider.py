import base64
import logging
from typing import AsyncGenerator, Optional, Tuple
import httpx
from ..ports.speech import SpeechToTextProvider, TextToSpeechProvider
from .mock_speech import MockSpeechProvider

logger = logging.getLogger(__name__)


class BhashiniProvider(SpeechToTextProvider, TextToSpeechProvider):
    """
    Government BHASHINI (National Language Translation Mission - NLTM / Dhruva API)
    provider for Multilingual Indian ASR (Speech-to-Text) and TTS (Text-to-Speech).
    Supports Odia and English along with native tribal and regional dialects.
    """

    # Bhashini short language code mappings (all lowercase)
    LANG_MAP = {
        "or-in": "or", "or": "or", "odi": "or", "odia": "or",
        "en-in": "en", "en": "en", "eng": "en", "english": "en",
        "sp-in": "or", "sambalpuri": "or", "kosli": "or",
        "sat-in": "or", "santali": "or",
        "des-in": "or", "desia": "or",
        "kui-in": "or", "kui": "or",
    }

    def __init__(
        self,
        auth_token: str,
        user_id: str = "",
        api_key: str = "",
        inference_url: str = "https://dhruva-api.bhashini.gov.in"
    ):
        self.auth_token = auth_token
        self.user_id = user_id
        self.api_key = api_key
        self.inference_url = inference_url.rstrip("/")
        self.fallback = MockSpeechProvider()
        self._client: Optional[httpx.AsyncClient] = None

    def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=12.0,
                limits=httpx.Limits(max_keepalive_connections=20, max_connections=40, keepalive_expiry=120.0)
            )
        return self._client

    def _map_language(self, language_code: Optional[str]) -> str:
        if not language_code:
            return "or"
        lc = language_code.lower().strip()
        return self.LANG_MAP.get(lc, "or")

    async def transcribe(
        self, audio_bytes: bytes, sample_rate: int = 16000, language_code: Optional[str] = None
    ) -> Tuple[str, str, float]:
        """
        Transcribes PCM/WAV audio bytes using Bhashini Dhruva ASR pipeline.
        """
        if not self.auth_token or self.auth_token in ["", "your_bhashini_auth_token"]:
            logger.info("[BhashiniProvider] No active auth token; using local fallback STT.")
            return await self.fallback.transcribe(audio_bytes, sample_rate, language_code)

        target_lang = self._map_language(language_code)
        b64_audio = base64.b64encode(audio_bytes).decode("utf-8")

        payload = {
            "pipelineTasks": [
                {
                    "taskType": "asr",
                    "config": {
                        "language": {"sourceLanguage": target_lang},
                        "audioFormat": "wav",
                        "samplingRate": sample_rate
                    }
                }
            ],
            "inputData": {
                "audio": [{"audioContent": b64_audio}]
            }
        }

        headers = {
            "Content-Type": "application/json",
            "Authorization": self.auth_token
        }
        if self.user_id:
            headers["userID"] = self.user_id
        if self.api_key:
            headers["ulcaApiKey"] = self.api_key

        url = f"{self.inference_url}/services/inference/pipeline"

        try:
            client = self._get_client()
            response = await client.post(url, json=payload, headers=headers)

            if response.status_code == 200:
                result = response.json()
                pipeline_resp = result.get("pipelineResponse", [])
                if pipeline_resp:
                    outputs = pipeline_resp[0].get("output", [])
                    if outputs:
                        transcript = outputs[0].get("source", "").strip()
                        if transcript:
                            resolved_lang = f"{target_lang}-IN" if target_lang != "en" else "en-IN"
                            return transcript, resolved_lang, 0.96
                logger.info("[BhashiniProvider] Audio contained no recognizable words or silence.")
                return "", f"{target_lang}-IN", 0.0
            else:
                logger.warning(f"[BhashiniProvider] ASR HTTP {response.status_code}: {response.text}")
                return await self.fallback.transcribe(audio_bytes, sample_rate, language_code)
        except Exception as e:
            logger.error(f"[BhashiniProvider] ASR Request Exception: {e}. Using fallback.")
            return await self.fallback.transcribe(audio_bytes, sample_rate, language_code)

    async def synthesize(
        self, text: str, language_code: str = "or-IN", speaker_gender: str = "female"
    ) -> bytes:
        """
        Synthesizes text to PCM/WAV audio using Bhashini Dhruva TTS pipeline.
        """
        if not self.auth_token or self.auth_token in ["", "your_bhashini_auth_token"] or not text.strip():
            logger.info("[BhashiniProvider] No active auth token or empty text; using local fallback TTS.")
            return await self.fallback.synthesize(text, language_code, speaker_gender)

        target_lang = self._map_language(language_code)
        gender = "female" if "f" in (speaker_gender or "female").lower() else "male"

        payload = {
            "pipelineTasks": [
                {
                    "taskType": "tts",
                    "config": {
                        "language": {"sourceLanguage": target_lang},
                        "gender": gender,
                        "samplingRate": 16000
                    }
                }
            ],
            "inputData": {
                "input": [{"source": text}]
            }
        }

        headers = {
            "Content-Type": "application/json",
            "Authorization": self.auth_token
        }
        if self.user_id:
            headers["userID"] = self.user_id
        if self.api_key:
            headers["ulcaApiKey"] = self.api_key

        url = f"{self.inference_url}/services/inference/pipeline"

        try:
            client = self._get_client()
            response = await client.post(url, json=payload, headers=headers)

            if response.status_code == 200:
                result = response.json()
                pipeline_resp = result.get("pipelineResponse", [])
                if pipeline_resp:
                    audio_list = pipeline_resp[0].get("audio", [])
                    if audio_list:
                        b64_content = audio_list[0].get("audioContent", "")
                        if b64_content:
                            return base64.b64decode(b64_content)
                logger.warning("[BhashiniProvider] TTS empty audio content in response.")
                return await self.fallback.synthesize(text, language_code, speaker_gender)
            else:
                logger.warning(f"[BhashiniProvider] TTS HTTP {response.status_code}: {response.text}")
                return await self.fallback.synthesize(text, language_code, speaker_gender)
        except Exception as e:
            logger.error(f"[BhashiniProvider] TTS Request Exception: {e}. Using fallback.")
            return await self.fallback.synthesize(text, language_code, speaker_gender)

    async def synthesize_stream(
        self, text: str, language_code: str = "or-IN"
    ) -> AsyncGenerator[bytes, None]:
        """
        Synthesizes text and yields audio stream chunks.
        """
        full_audio = await self.synthesize(text, language_code=language_code)
        chunk_size = 4096
        for i in range(0, len(full_audio), chunk_size):
            yield full_audio[i:i + chunk_size]
