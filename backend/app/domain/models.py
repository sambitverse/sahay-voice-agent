from enum import Enum
from typing import Dict, List, Optional
from pydantic import BaseModel, Field
from datetime import datetime


class RiskLevel(str, Enum):
    LOW = "LOW"
    MODERATE = "MODERATE"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class CallStatus(str, Enum):
    INITIATED = "initiated"
    IN_PROGRESS = "in_progress"
    ESCALATED = "escalated"
    COMPLETED = "completed"
    ABANDONED = "abandoned"


class Speaker(str, Enum):
    CALLER = "caller"
    AGENT = "agent"
    OPERATOR = "operator"


class EmotionSignals(BaseModel):
    probabilities: Dict[str, float] = Field(default_factory=dict)
    dominant_emotion: str = "neutral"
    confidence: float = 0.0


class AcousticSignals(BaseModel):
    mean_pitch_f0: Optional[float] = None
    pitch_variability: Optional[float] = None
    jitter: Optional[float] = None
    shimmer: Optional[float] = None
    pause_ratio: Optional[float] = None
    speech_rate: Optional[float] = None
    voice_activity_ratio: Optional[float] = None


class LinguisticSignals(BaseModel):
    detected_keywords: List[str] = Field(default_factory=list)
    risk_indicators: List[str] = Field(default_factory=list)
    threat_severity: float = 0.0


class SafetyFlags(BaseModel):
    immediate_danger: bool = False
    self_harm_indicator: bool = False
    medical_emergency: bool = False
    active_violence: bool = False
    weapon_present: bool = False
    # Problem Statement 26093 Mandated Trauma Indicators
    severe_trauma: bool = False
    fear_anxiety: bool = False
    depression_indicator: bool = False
    suicidal_ideation: bool = False
    intimidation_threat: bool = False
    social_boycott_isolation: bool = False
    extreme_vulnerability: bool = False


class RiskAssessment(BaseModel):
    call_id: str
    risk_level: RiskLevel = RiskLevel.LOW
    risk_score: float = 0.0
    svi_score: float = 0.0  # Stress Vulnerability Index (0.00 - 1.00)
    svi_percentage: int = 0  # 0 - 100%
    sub_indices: Dict[str, float] = Field(default_factory=dict)
    confidence: float = 0.0
    safety_flags: SafetyFlags = Field(default_factory=SafetyFlags)
    evidence: List[str] = Field(default_factory=list)
    recommended_action: str = "Provide standard guidance."
    recommended_services: List[str] = Field(default_factory=list)
    requires_human_escalation: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)


class TranscriptSegment(BaseModel):
    id: Optional[str] = None
    call_id: str
    speaker: Speaker
    sequence_num: int
    text_content: str
    language: str = "und"
    start_time_ms: int = 0
    end_time_ms: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)


class DistressState(BaseModel):
    """Temporal rolling state tracking distress across multiple turns."""
    call_id: str
    turn_count: int = 0
    rolling_distress_score: float = 0.0
    svi_score: float = 0.0  # Normalized SVI
    sub_indices: Dict[str, float] = Field(default_factory=dict)
    current_risk_level: RiskLevel = RiskLevel.LOW
    latest_emotion: EmotionSignals = Field(default_factory=EmotionSignals)
    latest_acoustic: AcousticSignals = Field(default_factory=AcousticSignals)
    aggregated_evidence: List[str] = Field(default_factory=list)
    safety_flags: SafetyFlags = Field(default_factory=SafetyFlags)
    requires_escalation: bool = False

    @property
    def current_score(self) -> float:
        return self.rolling_distress_score

    @property
    def current_level(self) -> RiskLevel:
        return self.current_risk_level
