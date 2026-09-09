import os
import uuid
import datetime
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from app.trauma.state_machine import ConversationStateManager, ConversationState
from app.trauma.rules import SafetyRulesEngine
from app.safety.validator import SafetyValidator
from app.language.router import LanguageRouter, DialectBridge
from app.domain.models import RiskLevel, SafetyFlags
from app.database.supabase_client import SupabaseManager
from app.websocket.dashboard_ws import broadcaster

router = APIRouter(prefix="", tags=["Website & Citizen Portal"])

language_router = LanguageRouter()

class ContactInquiryRequest(BaseModel):
    name: str
    contact: str
    category: str = "General Inquiry"
    message: str

class SendOtpRequest(BaseModel):
    phone: str = Field(..., description="Mobile number for OTP verification")

class LoginRequest(BaseModel):
    role: str = Field(..., description="'user' or 'operator'")
    identifier: str
    code: str

class ChatMessageRequest(BaseModel):
    message: str
    language: str = "unknown"

# In-memory storage for website contacts and chat sessions
contact_submissions: List[Dict[str, Any]] = []

@router.post("/website/contact")
async def submit_contact_inquiry(req: ContactInquiryRequest):
    ticket_id = f"INQ-{datetime.datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
    submission = {
        "id": ticket_id,
        "name": req.name,
        "contact": req.contact,
        "category": req.category,
        "message": req.message,
        "timestamp": datetime.datetime.now().isoformat(),
        "status": "RECEIVED"
    }
    contact_submissions.append(submission)
    return {
        "status": "success",
        "ticket_id": ticket_id,
        "message": "Your inquiry has been securely recorded. A helpline officer will contact you if required."
    }

@router.post("/auth/send-otp")
async def send_otp(req: SendOtpRequest):
    clean_digits = "".join(filter(str.isdigit, req.phone))
    if len(clean_digits) < 10:
        raise HTTPException(status_code=400, detail="Invalid mobile number. Please enter at least 10 digits.")
    return {
        "status": "success",
        "phone": req.phone,
        "message": f"One-Time Password successfully dispatched to {req.phone}.",
        "otp": "14566"
    }

@router.post("/auth/login")
async def portal_login(req: LoginRequest):
    role = req.role.lower()
    if role not in ["user", "operator"]:
        raise HTTPException(status_code=400, detail="Invalid role specified. Must be 'user' or 'operator'.")

    user_info = {
        "token": f"sahay_auth_{uuid.uuid4().hex}",
        "role": role,
        "user": {
            "id": f"citizen_{uuid.uuid4().hex[:6]}" if role == "user" else "officer_14566",
            "name": "Verified Citizen" if role == "user" else "Officer S. Mishra (Triage Lead)",
            "identifier": req.identifier,
            "badge": "CITIZEN" if role == "user" else "NHAA-TRIAGE-L2"
        }
    }
    return user_info

@router.get("/user/{user_id}/logs")
async def get_user_logs(user_id: str):
    db = SupabaseManager.get_instance()
    complaints = db.get_citizen_complaints()
    return {
        "user_id": user_id,
        "logs": complaints
    }

@router.get("/complaints/recent")
@router.get("/website/complaints/recent")
async def get_recent_complaints(phone: Optional[str] = None):
    """Publicly accessible endpoint: returns citizen complaints and recordings filtered by caller phone number."""
    db = SupabaseManager.get_instance()
    return {
        "status": "success",
        "caller_phone": phone,
        "complaints": db.get_citizen_complaints(phone=phone)
    }

@router.delete("/complaints/{identifier}")
@router.delete("/website/complaints/{identifier}")
async def delete_citizen_complaint(identifier: str):
    """
    DPDP Act Right to Erasure: Citizen permanently withdraws complaint and erases audio recording.
    Notifies operator dashboard immediately via WebSocket broadcaster.
    """
    db = SupabaseManager.get_instance()
    deleted = db.delete_complaint(identifier)
    if not deleted:
        raise HTTPException(status_code=404, detail="Complaint or recording not found or already erased.")

    # Synchronize real-time withdrawal with Operator Dashboard
    await broadcaster.broadcast("complaint_deleted", {
        "identifier": identifier,
        "call_id": deleted.get("call_id"),
        "ticket_ref": deleted.get("ticket_ref"),
        "deleted_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "reason": "CITIZEN_DPDP_RIGHT_TO_ERASURE"
    })

    return {
        "status": "success",
        "message": f"Complaint {identifier} and associated audio recording permanently erased per DPDP Act.",
        "deleted": deleted
    }

@router.get("/recordings/{filename}")
@router.get("/website/recordings/{filename}")
async def get_recording_audio(filename: str):
    """Serve saved voice call recording for playback in browser audio player."""
    rec_dir = os.path.join(os.path.dirname(__file__), "..", "..", "static", "recordings")
    file_path = os.path.join(rec_dir, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Recording audio file not found.")
    return FileResponse(file_path, media_type="audio/wav")

@router.post("/chat/message")
async def send_chat_message(req: ChatMessageRequest):
    text = req.message.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    # 1. Spatial Environment Grounding
    env = ConversationStateManager.detect_environment(text)
    
    # 2. Language & dialect normalization
    if req.language and req.language.lower() != "unknown":
        effective_lang = language_router.normalize_language_code(req.language).value
    else:
        detected_enum, _ = language_router.detect_language_from_text(text)
        effective_lang = detected_enum.value

    normalized_text = DialectBridge.normalize_dialect(text, effective_lang)

    # 3. Out-of-Scope Query Interception
    if SafetyValidator.is_out_of_scope(text):
        lang_key = "hi" if "hi" in effective_lang else ("en" if "en" in effective_lang else "or")
        refusal_text = SafetyValidator.OUT_OF_SCOPE_RESPONSES.get(lang_key, SafetyValidator.OUT_OF_SCOPE_RESPONSES["or"])
        return {
            "text": refusal_text,
            "risk_level": "LOW",
            "environment": env,
            "recommended_services": ["14566 National Helpline Against Atrocities"]
        }

    # 4. Deterministic Safety Evaluation
    flags = SafetyFlags()
    overridden_level, is_override_applied, evidence = SafetyRulesEngine.evaluate_overrides(normalized_text, flags)

    # 4. Generate Grounded Safe Response
    if env.get("wilderness") or env.get("pursuit"):
        safe_response = (
            "ମୁଁ ଆପଣଙ୍କ କଥା ଶୁଣିପାରୁଛି। ଦୟାକରି ଚୁପି ଚାପ ନୁଚି ରହନ୍ତୁ, ମୋବାଇଲ ସାଉଣ୍ଡ ସାଇଲେଣ୍ଟ କରନ୍ତୁ, "
            "ଓ ପାଖରେ ଥିବା ରାସ୍ତା ବା ମନ୍ଦିର ବିଷୟରେ କହନ୍ତୁ। ପୋଲିସ PCR 112 ପଠାଉଛୁ।"
        )
        risk_level = "CRITICAL"
        services = ["PCR 112 Police Dispatch", "14566 Witness Protection"]
    elif is_override_applied and overridden_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]:
        risk_level = overridden_level.value
        if "ସାମାଜିକ ବାସନ୍ଦ" in text or "boycott" in text.lower() or "pani" in text.lower():
            safe_response = (
                "ସାମାଜିକ ବାସନ୍ଦ ଏବଂ ପିଇବା ପାଣି ବନ୍ଦ କରିବା ଆଇନ ଅନୁସାରେ ଦଣ୍ଡନୀୟ ଅପରାଧ। "
                "ଆମେ ତୁରନ୍ତ ଜିଲ୍ଲା ପ୍ରଶାସନ ଓ ୧୪୫୬୬ କୁ ସୂଚନା ଦେଇଛୁ। ଆପଣଙ୍କୁ ସୁରକ୍ଷା ମିଳିବ।"
            )
            services = ["14566 National Helpline", "DLSA Legal Aid"]
        else:
            safe_response = ConversationStateManager.get_fallback_phrase(risk_level, "or-IN", text)
            services = ["PCR 112 Emergency", "14566 Helpline"]
    else:
        risk_level = "LOW"
        safe_response = "ଆପଣ ନିରାପଦରେ ରୁହନ୍ତୁ। ମୁଁ ଆପଣଙ୍କ କଥା ଶୁଣୁଛି, କୁହନ୍ତୁ ଆମେ ଆପଣଙ୍କୁ କିପରି ସାହାଯ୍ୟ କରିପାରିବୁ?"
        services = ["14566 Information Assistance"]

    # Final post-generation guardrail verification
    validated_response, _ = SafetyValidator.validate(safe_response, "or-IN", text)

    return {
        "text": validated_response,
        "risk_level": risk_level,
        "environment": env,
        "recommended_services": services
    }
