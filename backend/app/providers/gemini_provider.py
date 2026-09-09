import re
import logging
import json
from typing import AsyncGenerator, Dict, List, Optional
import httpx
from ..ports.llm import LLMProvider
from ..domain.models import LinguisticSignals

logger = logging.getLogger(__name__)


def clean_spoken_text(text: str) -> str:
    """Strip markdown formatting, asterisks, hashtags, and lists so TTS speaks natural conversational audio."""
    if not text:
        return ""
    # Strip bold and italics markdown
    t = re.sub(r'[*_]{1,3}([^*_]+)[*_]{1,3}', r'\1', text)
    # Strip markdown headers (#, ##, etc.)
    t = re.sub(r'^#+\s*', '', t, flags=re.MULTILINE)
    # Strip bullet points and numbered list markers
    t = re.sub(r'^\s*[-*•]\s*', '', t, flags=re.MULTILINE)
    t = re.sub(r'^\s*\d+[\.\)]\s*', '', t, flags=re.MULTILINE)
    # Strip inline code ticks
    t = t.replace('`', '')
    # Normalize whitespace
    t = re.sub(r'\s+', ' ', t).strip()
    return t


class GeminiProvider(LLMProvider):
    """
    Gemini LLM Provider using Google AI REST API.
    Handles dialogue reasoning and structured linguistic extraction.
    """

    def __init__(self, api_key: str, model: str = "models/gemini-flash-lite-latest"):
        self.api_key = api_key
        self.model = model if model.startswith("models/") else f"models/{model}"
        self.base_url = "https://generativelanguage.googleapis.com/v1beta"
        self._client: Optional[httpx.AsyncClient] = None

    def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=8.0,
                limits=httpx.Limits(max_keepalive_connections=20, max_connections=40, keepalive_expiry=120.0)
            )
        return self._client

    async def generate_response(
        self,
        conversation_history: List[Dict[str, str]],
        system_instructions: str,
        retrieved_context: Optional[str] = None
    ) -> str:
        """Generate conversational response using Gemini Flash."""
        if not self.api_key or self.api_key == "your_gemini_api_key":
            logger.info("[GeminiProvider] No API key; using local safe template response.")
            return "Namaskar. Mu apananka katha sunuchhi. Apan bartaman surakshita achhanti ki? Daya kari kuhan tu."

        url = f"{self.base_url}/{self.model}:generateContent?key={self.api_key}"

        # Build contents array, merging consecutive identical roles for Gemini API stability
        contents = []
        for msg in conversation_history:
            role = "user" if msg["role"] == "caller" or msg["role"] == "user" else "model"
            text_part = msg.get("content", "").strip()
            if not text_part:
                continue
            if contents and contents[-1]["role"] == role:
                contents[-1]["parts"][0]["text"] += f"\n{text_part}"
            else:
                contents.append({
                    "role": role,
                    "parts": [{"text": text_part}]
                })

        system_instruction_payload = {
            "parts": [{"text": system_instructions}]
        }
        if retrieved_context:
            system_instruction_payload["parts"].append({
                "text": f"\n\n[VERIFIED LEGAL/HELPLINE CONTEXT]:\n{retrieved_context}"
            })

        payload = {
            "contents": contents,
            "systemInstruction": system_instruction_payload,
            "generationConfig": {
                "temperature": 0.25,  # Low temperature for direct, fast, deterministic voice responses
                "maxOutputTokens": 160,  # Token budget for concise spoken answers
                "topP": 0.80
            }
        }

        try:
            client = self._get_client()
            response = await client.post(url, json=payload)

            if response.status_code == 200:
                data = response.json()
                candidates = data.get("candidates", [])
                if candidates:
                    parts = candidates[0].get("content", {}).get("parts", [])
                    if parts:
                        raw_text = parts[0].get("text", "").strip()
                        cleaned = clean_spoken_text(raw_text)
                        if cleaned:
                            return cleaned

            logger.warning(f"[GeminiProvider] API Error {response.status_code}: {response.text}")
            return self._get_fallback_response(system_instructions)

        except Exception as e:
            logger.error(f"[GeminiProvider] Exception: {e}")
            return self._get_fallback_response(system_instructions)

    @staticmethod
    def _get_fallback_response(system_instructions: str) -> str:
        """Language-aware soothing response if API experiences quota or network interruptions."""
        instr_lower = (system_instructions or "").lower()
        # Determine language from explicit cues in the system instruction.
        # Avoid naive substring checks like 'en' which can match unrelated words (e.g., 'conversation').
        odia_indicators = ["odia", "or-in", "spoken odia", "sambalpuri", "desia", "kui", "santali"]
        english_indicators = ["english", "indian english", "en-in"]

        if any(k in instr_lower for k in odia_indicators):
            return "Mu apananka katha suni paruchhi. Apan bartaman surakshita sthana re achhanti ki? Daya kari kuhan tu."
        if any(k in instr_lower for k in english_indicators):
            return "I hear you clearly. Are you currently in a safe location, and is anyone with you right now?"

        # Fallback: prefer Odia for this helpline unless English is explicitly requested.
        return "Mu apananka katha suni paruchhi. Apan bartaman surakshita sthana re achhanti ki? Daya kari kuhan tu."

    async def stream_response(
        self,
        conversation_history: List[Dict[str, str]],
        system_instructions: str,
        retrieved_context: Optional[str] = None
    ) -> AsyncGenerator[str, None]:
        """Stream response (yields full text or tokens)."""
        full_text = await self.generate_response(conversation_history, system_instructions, retrieved_context)
        # Yield in sentence or word chunks for streaming
        words = full_text.split()
        for i in range(0, len(words), 3):
            chunk = " ".join(words[i:i + 3]) + " "
            yield chunk

    async def extract_linguistic_signals(self, text: str) -> LinguisticSignals:
        """Rule-assisted linguistic threat and safety extraction."""
        lower = text.lower()
        signals = LinguisticSignals()

        # Danger & violence keywords (Odia, Hindi, English - Romanized and Native Scripts)
        danger_keywords = {
            "threat": [
                "dhamaka", "dhamki", "threat", "kill", "marideba", "jaan se maar", "attack", "akramana",
                "ଧମକ", "ଧମକା", "ମାରିଦେବା", "ମାରିବା", "ଆକ୍ରମଣ", "ଥ୍ରେଟନ୍", "କର୍ମ କ୍ଷେତ୍ରରେ", "धमकी", "जान से मार", "मार दूंगा"
            ],
            "violence": [
                "maripit", "beating", "lathi", "talwar", "weapon", "hatahati", "chaku", "knife", "bhang",
                "ଲାଠି", "ଖଣ୍ଡା", "ଛୁରୀ", "ଭାଙ୍ଗୁଛନ୍ତି", "ଭାଙ୍ଗି", "ମାରପିଟ", "ହାତାହାତି", "କପାଟ",
                "लाठी", "तलवार", "चाकू", "दरवाजा तोड़", "मारपीट"
            ],
            "self_harm": [
                "mariba", "suicide", "khatam", "jeeban", "end my life",
                "ଆତ୍ମହତ୍ୟା", "ଜୀବନ ହାରି", "ମରିବା", "आत्महत्या"
            ],
            "fear": [
                "dari", "dara", "scared", "fear", "panic", "bhayabheeta", "help", "bachao", "sahajya", "bhaya", "bhayata", "asanti",
                "not safe", "unsafe", "surakshita naahi", "surakshit nahi", "in danger",
                "ଡରି", "ଡର", "ଭୟ", "ଭୟା", "ଭୟାତା", "ସୁରକ୍ଷିତ ନାହିଁ", "ସୁରକ୍ଷିତ ନୁହେଁ", "ଅସୁରକ୍ଷିତ", "ଅସହାୟ", "ଅଶାନ୍ତି", "ବଚାଅ", "ସାହାଯ୍ୟ", "ଡରିଛି", "ସ୍କେର୍ଡ୍", "ହେଲ୍ପ", "ଅର୍ଜେଣ୍ଟ",
                "डर", "घबराहट", "बचाओ", "मदद", "सुरक्षित नहीं", "असुरक्षित", "खतरा"
            ]
        }

        detected = []
        indicators = []

        for category, kws in danger_keywords.items():
            for kw in kws:
                if kw in lower:
                    detected.append(kw)
                    if category not in indicators:
                        indicators.append(category)

        signals.detected_keywords = detected
        signals.risk_indicators = indicators
        signals.threat_severity = min(1.0, len(indicators) * 0.35)

        return signals
