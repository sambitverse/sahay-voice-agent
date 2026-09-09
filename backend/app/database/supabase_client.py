"""
Supabase Persistence and Audit Logging Client.
Provides resilient asynchronous persistence for call sessions, acoustic features,
emotion vectors, triage assessments, escalations, and compliance audit logs.
"""

import os
import re
import hashlib
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
import httpx

logger = logging.getLogger(__name__)

try:
    from supabase import create_client, Client
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False



class SupabaseManager:
    """
    Singleton persistence manager for the NHAA Voice Triage system.
    Falls back to in-memory buffer if Supabase is offline or not configured.
    """

    _instance: Optional["SupabaseManager"] = None

    def __init__(self, url: Optional[str] = None, key: Optional[str] = None):
        self.url = url or os.getenv("SUPABASE_URL", "")
        self.key = key or os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_ANON_KEY", "")
        self.client: Optional[Client] = None
        self.in_memory_sessions: Dict[str, Dict[str, Any]] = {}
        self.in_memory_assessments: List[Dict[str, Any]] = []
        self.in_memory_escalations: List[Dict[str, Any]] = []
        self.in_memory_complaints: List[Dict[str, Any]] = [
            {
                "id": "complaint_01",
                "call_id": "call_9901_forest",
                "caller_number": "+91 94371-88210",
                "ticket_ref": "TKT-2026-0907-8821",
                "type": "voice",
                "timestamp": "Today, 22:45",
                "risk_level": "CRITICAL",
                "summary": "Outdoor pursuit in forest. Spatial wilderness protocol engaged; zero door-locking hallucination. PCR 112 dispatched to road landmark.",
                "language": "or-IN",
                "recording_url": "/api/v1/recordings/call_9901_forest.wav",
                "recommended_services": ["PCR 112 Police Dispatch", "14566 Witness Protection Desk", "DLSA Emergency Cell"],
                "status": "REGISTERED_ACTIVE_TRIAGE",
                "is_legitimate": True
            },
            {
                "id": "complaint_02",
                "call_id": "call_9902_boycott",
                "caller_number": "+91 98610-44120",
                "ticket_ref": "TKT-2026-0906-4412",
                "type": "voice",
                "timestamp": "Yesterday, 14:15",
                "risk_level": "HIGH",
                "summary": "Social boycott and tube well drinking water access denial. Kosli/Desia dialect normalized. Statutory Section 15A complaint prepared.",
                "language": "sp-IN",
                "recording_url": "/api/v1/recordings/call_9902_boycott.wav",
                "recommended_services": ["14566 National Helpline", "DLSA Free Legal Aid", "District Welfare Magistrate"],
                "status": "REGISTERED_LEGAL_AID",
                "is_legitimate": True
            }
        ]

        if SUPABASE_AVAILABLE and self.url and self.key and "your_" not in self.key:
            try:
                self.client = create_client(self.url, self.key)
                logger.info("[SupabaseManager] Connected to Supabase instance.")
            except Exception as e:
                logger.warning(f"[SupabaseManager] Could not initialize Supabase client: {e}. Using in-memory store.")
        else:
            logger.info("[SupabaseManager] Running with resilient in-memory storage.")

    @classmethod
    def get_instance(cls) -> "SupabaseManager":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @staticmethod
    def hash_phone(phone_number: str, salt: str = "nhaa_sih_2026_salt") -> str:
        """One-way salted SHA-256 phone hash for privacy compliance (DPDP Act)."""
        if not phone_number:
            return "anonymous_caller"
        return hashlib.sha256(f"{salt}_{phone_number}".encode("utf-8")).hexdigest()

    async def create_call_session(
        self,
        external_call_id: str,
        phone_hash: str,
        telephony_provider: str = "mock",
        detected_language: str = "or-IN"
    ) -> Dict[str, Any]:
        """Record the start of a call session."""
        session_data = {
            "external_call_id": external_call_id,
            "caller_phone_hash": phone_hash,
            "telephony_provider": telephony_provider,
            "status": "initiated",
            "detected_language": detected_language,
            "language_confidence": 0.95,
            "started_at": datetime.now(timezone.utc).isoformat()
        }

        self.in_memory_sessions[external_call_id] = session_data

        if self.client:
            try:
                res = self.client.table("call_sessions").insert(session_data).execute()
                if res.data:
                    return res.data[0]
            except Exception as e:
                logger.warning(f"[SupabaseManager] create_call_session fallback: {e}")

        return session_data

    async def update_call_status(
        self,
        external_call_id: str,
        status: str,
        detected_language: Optional[str] = None
    ) -> None:
        """Update the lifecycle status of a call session."""
        if external_call_id in self.in_memory_sessions:
            self.in_memory_sessions[external_call_id]["status"] = status
            if detected_language:
                self.in_memory_sessions[external_call_id]["detected_language"] = detected_language

        if self.client:
            try:
                update_data = {"status": status}
                if detected_language:
                    update_data["detected_language"] = detected_language
                self.client.table("call_sessions").update(update_data).eq("external_call_id", external_call_id).execute()
            except Exception as e:
                logger.warning(f"[SupabaseManager] update_call_status error: {e}")

    async def save_transcript_segment(
        self,
        external_call_id: str,
        speaker: str,
        text_content: str,
        sequence_num: int,
        language: str = "or-IN",
        start_ms: int = 0,
        end_ms: int = 0
    ) -> None:
        """Save an individual conversational turn."""
        segment_data = {
            "external_call_id": external_call_id,
            "speaker": speaker,
            "sequence_num": sequence_num,
            "text_content": text_content,
            "language": language,
            "start_time_ms": start_ms,
            "end_time_ms": end_ms,
            "created_at": datetime.now(timezone.utc).isoformat()
        }

        session = self.in_memory_sessions.get(external_call_id, {})
        if "transcripts" not in session:
            session["transcripts"] = []
        session["transcripts"].append(segment_data)

        if self.client:
            try:
                # Resolve internal session UUID if available
                self.client.table("transcript_segments").insert({
                    "call_session_id": external_call_id,
                    "speaker": speaker,
                    "sequence_num": sequence_num,
                    "text_content": text_content,
                    "language": language,
                    "start_time_ms": start_ms,
                    "end_time_ms": end_ms
                }).execute()
            except Exception as e:
                logger.debug(f"[SupabaseManager] save_transcript_segment fallback: {e}")

    async def save_risk_assessment(
        self,
        external_call_id: str,
        risk_score: float,
        risk_level: str,
        safety_flags: Dict[str, Any],
        evidence_summary: List[str],
        recommended_action: str,
        requires_human_escalation: bool
    ) -> None:
        """Save a multimodal risk assessment."""
        assessment_data = {
            "external_call_id": external_call_id,
            "risk_score": round(risk_score, 3),
            "risk_level": risk_level,
            "safety_flags": safety_flags,
            "evidence_summary": evidence_summary,
            "recommended_action": recommended_action,
            "requires_human_escalation": requires_human_escalation,
            "created_at": datetime.now(timezone.utc).isoformat()
        }

        self.in_memory_assessments.append(assessment_data)

        if self.client:
            try:
                self.client.table("risk_assessments").insert(assessment_data).execute()
            except Exception as e:
                logger.debug(f"[SupabaseManager] save_risk_assessment fallback: {e}")

    async def create_escalation(
        self,
        external_call_id: str,
        trigger_reason: str
    ) -> None:
        """Create an urgent operator escalation ticket."""
        escalation_data = {
            "external_call_id": external_call_id,
            "trigger_reason": trigger_reason,
            "status": "pending",
            "escalated_at": datetime.now(timezone.utc).isoformat()
        }

        self.in_memory_escalations.append(escalation_data)
        logger.warning(f"[SupabaseManager] ESCALATION CREATED: Call {external_call_id} -> {trigger_reason}")

        if self.client:
            try:
                self.client.table("escalations").insert(escalation_data).execute()
            except Exception as e:
                logger.debug(f"[SupabaseManager] create_escalation fallback: {e}")

    def get_recent_escalations(self) -> List[Dict[str, Any]]:
        """Fetch pending escalations for the operator triage dashboard."""
        return self.in_memory_escalations

    def get_active_sessions(self) -> List[Dict[str, Any]]:
        """Fetch active calls for the operator dashboard."""
        return list(self.in_memory_sessions.values())

    def register_complaint(
        self,
        call_id: str,
        ticket_id: str,
        summary: str,
        risk_level: str,
        caller_number: str = "+91 94371-88210",
        language: str = "or-IN",
        recording_url: Optional[str] = None,
        recommended_services: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Registers a legitimate complaint for public citizen dashboard showcase."""
        complaint = {
            "id": f"complaint_{call_id}",
            "call_id": call_id,
            "caller_number": caller_number,
            "ticket_ref": ticket_id,
            "type": "voice",
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M"),
            "risk_level": risk_level,
            "summary": summary,
            "language": language,
            "recording_url": recording_url or f"/api/v1/recordings/{call_id}.wav",
            "recommended_services": recommended_services or ["14566 National Helpline", "DLSA Legal Aid Council"],
            "status": "REGISTERED_ACTIVE_TRIAGE",
            "is_legitimate": True
        }
        # Prepend to top of list
        self.in_memory_complaints.insert(0, complaint)
        logger.info(f"[SupabaseManager] Registered complaint {ticket_id} for call {call_id} from {caller_number}")
        return complaint

    def get_citizen_complaints(self, phone: Optional[str] = None) -> List[Dict[str, Any]]:
        """Fetch legitimate citizen complaints and recordings for the public portal."""
        base = [c for c in self.in_memory_complaints if c.get("is_legitimate", True)]
        if phone:
            digits = re.sub(r"\D", "", phone)[-10:]
            if digits:
                matched = [
                    c for c in base 
                    if digits in re.sub(r"\D", "", c.get("caller_number", ""))
                ]
                if matched:
                    return matched
        return base

    def delete_complaint(self, identifier: str) -> Optional[Dict[str, Any]]:
        """
        DPDP Act Right to Erasure: Permanently delete citizen complaint and audio recording.
        Identifier can be ticket_ref, call_id, or internal id.
        """
        deleted_item = None
        for idx, comp in enumerate(list(self.in_memory_complaints)):
            if identifier in (comp.get("ticket_ref"), comp.get("call_id"), comp.get("id")):
                deleted_item = self.in_memory_complaints.pop(idx)
                break

        if deleted_item:
            call_id = deleted_item.get("call_id")
            # Remove from sessions and escalations as well
            if call_id in self.in_memory_sessions:
                self.in_memory_sessions.pop(call_id, None)
            self.in_memory_escalations = [e for e in self.in_memory_escalations if e.get("external_call_id") != call_id]

            # Erase physical recording file from disk for citizen privacy
            try:
                rec_dir = os.path.join(os.path.dirname(__file__), "..", "static", "recordings")
                wav_path = os.path.join(rec_dir, f"{call_id}.wav")
                if os.path.exists(wav_path):
                    os.remove(wav_path)
                    logger.info(f"[SupabaseManager] Permanently erased recording file: {wav_path}")
            except Exception as e:
                logger.warning(f"[SupabaseManager] Error deleting audio recording file: {e}")

            logger.info(f"[SupabaseManager] Complaint {identifier} permanently erased per citizen request.")

        return deleted_item

    def delete_all_complaints(self, phone: Optional[str] = None) -> int:
        """
        DPDP Act Right to Erasure: Permanently delete citizen complaints and audio recordings.
        If phone is provided, wipes complaints belonging to that phone number; otherwise all.
        """
        to_delete = []
        if phone:
            digits = re.sub(r"\D", "", phone)[-10:]
            to_delete = [
                c for c in self.in_memory_complaints
                if digits and digits in re.sub(r"\D", "", c.get("caller_number", ""))
            ]
        else:
            to_delete = list(self.in_memory_complaints)

        for comp in to_delete:
            identifier = comp.get("ticket_ref") or comp.get("call_id") or comp.get("id")
            if identifier:
                self.delete_complaint(identifier)

        logger.info(f"[SupabaseManager] Deleted {len(to_delete)} records per DPDP Act erasure request.")
        return len(to_delete)

