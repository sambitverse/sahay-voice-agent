import os
from typing import List
from pathlib import Path
from dotenv import load_dotenv

# Load .env if present
env_path = Path(".env")
if not env_path.exists():
    env_path = Path(__file__).resolve().parent.parent / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path)

try:
    from pydantic_settings import BaseSettings, SettingsConfigDict
    class Settings(BaseSettings):
        model_config = SettingsConfigDict(
            env_file=".env",
            env_file_encoding="utf-8",
            extra="ignore"
        )

        APP_NAME: str = os.getenv("APP_NAME", "NHAA-TraumaVoiceAgent")
        ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
        DEBUG: bool = os.getenv("DEBUG", "True").lower() in ("true", "1")
        PORT: int = int(os.getenv("PORT", "8000"))
        HOST: str = os.getenv("HOST", "0.0.0.0")
        ALLOWED_ORIGINS: List[str] = ["*"]

        PRODUCTION_HELPLINE_NUMBER: str = os.getenv("PRODUCTION_HELPLINE_NUMBER", "14566")
        TELEPHONY_PROVIDER: str = os.getenv("TELEPHONY_PROVIDER", "mock")

        EXOTEL_ACCOUNT_SID: str = os.getenv("EXOTEL_ACCOUNT_SID") or os.getenv("EXOTEL_SID", "")
        EXOTEL_API_KEY: str = os.getenv("EXOTEL_API_KEY", "")
        EXOTEL_API_TOKEN: str = os.getenv("EXOTEL_API_TOKEN", "")
        EXOTEL_SUB_DOMAIN: str = os.getenv("EXOTEL_SUB_DOMAIN", "api.exotel.com")
        EXOTEL_VIRTUAL_NUMBER: str = os.getenv("EXOTEL_VIRTUAL_NUMBER") or os.getenv("EXOTEL_PHONE_NUMBER", "")
        EXOTEL_APP_ID: str = os.getenv("EXOTEL_APP_ID", "")

        SARVAM_API_KEY: str = os.getenv("SARVAM_API_KEY", "")
        SARVAM_BASE_URL: str = os.getenv("SARVAM_BASE_URL", "https://api.sarvam.ai")

        BHASHINI_API_KEY: str = os.getenv("BHASHINI_API_KEY", "")
        BHASHINI_USER_ID: str = os.getenv("BHASHINI_USER_ID", "")
        BHASHINI_AUTH_TOKEN: str = os.getenv("BHASHINI_AUTH_TOKEN", "")
        BHASHINI_INFERENCE_URL: str = os.getenv("BHASHINI_INFERENCE_URL", "https://dhruva-api.bhashini.gov.in")

        GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
        GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "models/gemini-3-flash-preview")

        SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
        SUPABASE_ANON_KEY: str = os.getenv("SUPABASE_ANON_KEY", "")
        SUPABASE_SERVICE_ROLE_KEY: str = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")

        VAD_CONFIDENCE_THRESHOLD: float = float(os.getenv("VAD_CONFIDENCE_THRESHOLD", "0.5"))
        AUDIO_SAMPLE_RATE_TELEPHONY: int = int(os.getenv("AUDIO_SAMPLE_RATE_TELEPHONY", "8000"))
        AUDIO_SAMPLE_RATE_PROCESSING: int = int(os.getenv("AUDIO_SAMPLE_RATE_PROCESSING", "16000"))
        WAV2VEC2_SER_MODEL: str = os.getenv("WAV2VEC2_SER_MODEL", "ehcalabres/wav2vec2-lg-xlsr-en-speech-emotion-recognition")
        USE_GPU: bool = os.getenv("USE_GPU", "False").lower() in ("true", "1")

        DISTRESS_THRESHOLD_MODERATE: float = float(os.getenv("DISTRESS_THRESHOLD_MODERATE", "0.35"))
        DISTRESS_THRESHOLD_HIGH: float = float(os.getenv("DISTRESS_THRESHOLD_HIGH", "0.65"))
        DISTRESS_THRESHOLD_CRITICAL: float = float(os.getenv("DISTRESS_THRESHOLD_CRITICAL", "0.85"))
        BARGE_IN_TRIGGER_DURATION_MS: int = int(os.getenv("BARGE_IN_TRIGGER_DURATION_MS", "160"))

except ImportError:
    from pydantic import BaseModel
    class Settings(BaseModel):
        APP_NAME: str = os.getenv("APP_NAME", "NHAA-TraumaVoiceAgent")
        ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
        DEBUG: bool = os.getenv("DEBUG", "True").lower() in ("true", "1")
        PORT: int = int(os.getenv("PORT", "8000"))
        HOST: str = os.getenv("HOST", "0.0.0.0")
        ALLOWED_ORIGINS: List[str] = ["*"]

        PRODUCTION_HELPLINE_NUMBER: str = os.getenv("PRODUCTION_HELPLINE_NUMBER", "14566")
        TELEPHONY_PROVIDER: str = os.getenv("TELEPHONY_PROVIDER", "mock")

        EXOTEL_ACCOUNT_SID: str = os.getenv("EXOTEL_ACCOUNT_SID") or os.getenv("EXOTEL_SID", "")
        EXOTEL_API_KEY: str = os.getenv("EXOTEL_API_KEY", "")
        EXOTEL_API_TOKEN: str = os.getenv("EXOTEL_API_TOKEN", "")
        EXOTEL_SUB_DOMAIN: str = os.getenv("EXOTEL_SUB_DOMAIN", "api.exotel.com")
        EXOTEL_VIRTUAL_NUMBER: str = os.getenv("EXOTEL_VIRTUAL_NUMBER") or os.getenv("EXOTEL_PHONE_NUMBER", "")
        EXOTEL_APP_ID: str = os.getenv("EXOTEL_APP_ID", "")

        SARVAM_API_KEY: str = os.getenv("SARVAM_API_KEY", "")
        SARVAM_BASE_URL: str = os.getenv("SARVAM_BASE_URL", "https://api.sarvam.ai")

        BHASHINI_API_KEY: str = os.getenv("BHASHINI_API_KEY", "")
        BHASHINI_USER_ID: str = os.getenv("BHASHINI_USER_ID", "")
        BHASHINI_AUTH_TOKEN: str = os.getenv("BHASHINI_AUTH_TOKEN", "")
        BHASHINI_INFERENCE_URL: str = os.getenv("BHASHINI_INFERENCE_URL", "https://dhruva-api.bhashini.gov.in")

        GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
        GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "models/gemini-flash-lite-latest")

        SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
        SUPABASE_ANON_KEY: str = os.getenv("SUPABASE_ANON_KEY", "")
        SUPABASE_SERVICE_ROLE_KEY: str = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")

        VAD_CONFIDENCE_THRESHOLD: float = float(os.getenv("VAD_CONFIDENCE_THRESHOLD", "0.5"))
        AUDIO_SAMPLE_RATE_TELEPHONY: int = int(os.getenv("AUDIO_SAMPLE_RATE_TELEPHONY", "8000"))
        AUDIO_SAMPLE_RATE_PROCESSING: int = int(os.getenv("AUDIO_SAMPLE_RATE_PROCESSING", "16000"))
        WAV2VEC2_SER_MODEL: str = os.getenv("WAV2VEC2_SER_MODEL", "ehcalabres/wav2vec2-lg-xlsr-en-speech-emotion-recognition")
        USE_GPU: bool = os.getenv("USE_GPU", "False").lower() in ("true", "1")

        DISTRESS_THRESHOLD_MODERATE: float = float(os.getenv("DISTRESS_THRESHOLD_MODERATE", "0.35"))
        DISTRESS_THRESHOLD_HIGH: float = float(os.getenv("DISTRESS_THRESHOLD_HIGH", "0.65"))
        DISTRESS_THRESHOLD_CRITICAL: float = float(os.getenv("DISTRESS_THRESHOLD_CRITICAL", "0.85"))
        BARGE_IN_TRIGGER_DURATION_MS: int = int(os.getenv("BARGE_IN_TRIGGER_DURATION_MS", "160"))

settings = Settings()
