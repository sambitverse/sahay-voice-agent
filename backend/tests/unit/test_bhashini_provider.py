import pytest
from app.providers.bhashini_provider import BhashiniProvider
from app.providers.hybrid_speech import HybridSpeechProvider


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_bhashini_provider_unconfigured_fallback():
    provider = BhashiniProvider(auth_token="")
    transcript, lang, conf = await provider.transcribe(b"RIFF" + b"\x00" * 3200, 16000, "or-IN")
    assert transcript is not None
    assert lang in ["or-IN", "or"]

    audio = await provider.synthesize("test", "or-IN")
    assert len(audio) > 0


@pytest.mark.anyio
async def test_hybrid_speech_provider_fallback_to_mock():
    hybrid = HybridSpeechProvider(
        sarvam_api_key="",
        sarvam_base_url="https://api.sarvam.ai",
        bhashini_auth_token="",
        primary_provider="sarvam"
    )

    transcript, lang, conf = await hybrid.transcribe(b"RIFF" + b"\x00" * 3200, 16000, "or-IN")
    assert transcript is not None

    audio = await hybrid.synthesize("namaskar", "or-IN")
    assert len(audio) > 0


def test_bhashini_language_code_mapping():
    provider = BhashiniProvider(auth_token="dummy")
    assert provider._map_language("or-IN") == "or"
    assert provider._map_language("hi-IN") == "hi"
    assert provider._map_language("en-IN") == "en"
    assert provider._map_language("sp-IN") == "or"
    assert provider._map_language("des-IN") == "or"
    assert provider._map_language("kui-IN") == "or"
    assert provider._map_language("unknown") == "or"
