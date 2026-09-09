# Application & Interaction Flow (App Flow)
## Project SAHAY (ସହାୟ) – Voice Agent & Crisis Helpline System
**Document Version:** 2.0  
**Target Solution:** Smart India Hackathon (SIH 2026) – Problem Statement 26093  
**Status:** Approved & Production-Active  

---

## 1. System Navigation & Sitemap Architecture

The SAHAY application architecture is structured into two primary portals:
1. **Public Citizen Helpline Portal** (No mandatory login required; instant access to voice agent, case history, resources, and statutory data erasure).
2. **Authorized Operator & Triage Console** (Role-authenticated workspace for live telemetry monitoring, queue management, and SBAR emergency dispatch).

### Visual System Workflow Infographic
![SAHAY System Architecture & Workflow Diagram](file:///c:/Users/SAMBIT/OneDrive/Documents/My%20Projects/trauma-voice-agent/docs/images/sahay_agent_workflow.jpg)

```
SAHAY Portal Root (/)
 │
 ├── [Home Page (/)]
 │    ├── Hero Banner ("14566 National Helpline Against Atrocities")
 │    ├── Instant Emergency Call CTA ("Dial 14566" / "Start Voice Call")
 │    ├── Comprehensive Crisis Services Grid
 │    ├── Essential Resources for Citizens in Distress
 │    │    └── Learn More (/essential-resources) [Dropdown Q&A Guide]
 │    ├── Voice Distress Architecture & Dialect Coverage Showcase
 │    └── Statutory DPDP 2023 Compliance & Privacy Notice
 │
 ├── [AI Voice & Text Agent (/agent)]
 │    ├── Real-Time Voice Stream (Live microphone / WebRTC stream)
 │    │    ├── Live Animated Audio Waveform
 │    │    ├── Session Timer & Dialect Auto-Detect Badge
 │    │    ├── Live Prosody Telemetry (SVI, Pitch F0, Jitter, Voice Activity)
 │    │    ├── Direct Call 14566 Button
 │    │    └── Linked Caller Line ID (Phone Input with Instant Sync)
 │    ├── Text Guidance Chat (Bilingual Odia/English distress support)
 │    └── View My Complaints & Audio Recordings Link
 │
 ├── [Citizen Grievance Logs & Audio Recordings (/user-dashboard)]
 │    ├── Public Access Status Indicator ("No Login Required")
 │    ├── Active Caller Phone Display & Switch Form
 │    ├── Registered Complaints & Audio Playback Cards
 │    │    ├── Audio Waveform Player (/api/v1/recordings/*.wav)
 │    │    ├── Risk Badge (LOW, MODERATE, HIGH, CRITICAL)
 │    │    ├── Recommended Statutory Services (DLSA, PCR 112, 14416)
 │    │    └── Lower-Right Action Group:
 │    │         ├── Withdraw & Erase Single Complaint (DPDP Right to Erasure)
 │    │         └── Delete Audio Recording
 │    └── "Delete Records" Global Action (Wipes all local & server records)
 │
 ├── [Secure Portal Sign In (/login)]
 │    ├── Citizen Portal Tab
 │    │    ├── Registered Mobile Input
 │    │    ├── "Send OTP" Button (Triggers 6-digit random SMS OTP via Exotel)
 │    │    ├── Verification Code Input (Auto-populated with sent OTP)
 │    │    └── Direct Sign In Action
 │    └── Helpline Operator Tab
 │         ├── Officer Badge / Staff ID Input
 │         └── Authorized Security PIN Verification
 │
 ├── [Operator Live Telemetry Dashboard (/operator-dashboard)]
 │    ├── High-Distress Emergency Alert Banner (Active Pursuit / Weapons)
 │    ├── Active Call Sessions Metric Cards (Active, High Risk, Critical, Escalations)
 │    ├── Distress Indicators Bar Chart (Fear, Sadness, Anger, Stress, Voice Tremor)
 │    ├── Real-Time Telemetry Stream (Live SVI, Acoustic Prosody, Speech Emotion)
 │    ├── Live Incident Queue & SBAR Handoff Drawer
 │    └── Real-Time WebSocket Listener (Syncs deletions and registrations live)
 │
 └── [Contact & Legal Inquiries (/contact)]
      ├── District Legal Services Inquiry Form
      └── Emergency Contact Directory (112, 14566, 181, 14416)
```

---

## 2. Citizen User Journey Flowchart

```mermaid
sequenceDiagram
    autonumber
    actor Citizen as Citizen in Distress
    participant UI as Website / PWA
    participant API as FastAPI Gateway
    participant Agent as Multimodal Voice Agent
    participant Exotel as Exotel SMS Gateway
    participant DB as Supabase PostgreSQL

    Note over Citizen,UI: Phase 1: Access & Dialect Voice Connection
    Citizen->>UI: Visits sahay-helpline.vercel.app or dials 14566
    Citizen->>UI: Clicks "Start Voice Stream" on /agent
    UI->>API: Establishes WebSocket (/ws/client/{call_id})
    UI-->>Citizen: Plays Odia Welcome Greeting ("Namaskar, mu Sahay agent...")
    
    Note over Citizen,Agent: Phase 2: Trauma Assessment & Wilderness Safety
    Citizen->>UI: Speaks in Kosli/Desia ("Mor pache padila godauche bana re...")
    UI->>Agent: Streams 16kHz audio chunks
    Agent->>Agent: Dialect normalization + Wav2Vec2 SER (Fear: 0.88)
    Agent->>Agent: Spatial check: Wilderness Pursuit detected!
    Agent-->>UI: Audio response: "Chupi chap nuchi rahantu, mobile silent karantu..."
    Agent->>API: Broadcasts CRITICAL alert to Operator Dashboard
    
    Note over Citizen,DB: Phase 3: Call Conclusion & Grievance Registration
    Citizen->>UI: Ends call session
    UI->>API: POST /complaints/register (phone, audio URL, SVI, summary)
    API->>DB: Persists complaint & generates ticket TKT-2026-...
    
    Note over Citizen,UI: Phase 4: Review Records & DPDP Right to Erasure
    Citizen->>UI: Navigates to /user-dashboard
    UI->>API: GET /complaints/recent?phone=+91-94371-88210
    API-->>UI: Returns grievance logs and audio recording URL
    Citizen->>UI: Listens to recorded voice call
    Citizen->>UI: Clicks "Delete Records"
    UI-->>Citizen: Confirms DPDP Act Right to Erasure
    Citizen->>UI: Clicks "Confirm Erasure"
    UI->>API: DELETE /complaints?phone=+91-94371-88210
    API->>DB: Permanently erases complaint rows & wipes .wav file
    API->>UI: Broadcasts complaint_deleted via WebSocket
    UI-->>Citizen: "All grievance records and call history have been deleted."
```

---

## 3. Inbound Telephony (PSTN) Call Flow

```mermaid
flowchart TD
    CALLER["Citizen Dials 14566<br/>(or Exotel Virtual Number 095-138-86363)"] --> EXOTEL["Exotel Telephony Cloud<br/>(PSTN Ingestion & IVR)"]
    
    EXOTEL -->|HTTP Webhook Callback| WEBHOOK["FastAPI Voice Webhook<br/>POST /api/v1/calls/webhook/exotel"]
    WEBHOOK -->|Returns JSON Applet| AGENTSTREAM["Exotel AgentStream Applet<br/>wss://sahay.up.railway.app/ws/exotel/{call_id}"]
    
    AGENTSTREAM --> RESAMPLE["Audio Resampler<br/>8kHz μ-law ➔ 16kHz Linear PCM"]
    RESAMPLE --> VAD["Voice Activity Detector (VAD)<br/>Speech Boundary & Noise Filter"]
    
    VAD --> PARALLEL["Parallel Multimodal Processing"]
    
    subgraph ParallelProcessing["Parallel Analysis"]
        PARALLEL --> STT["Sarvam Saaras STT<br/>(Odia / Hindi / English)"]
        PARALLEL --> PROSODY["openSMILE Feature Extraction<br/>(Pitch F0, Jitter, Shimmer)"]
        PARALLEL --> SER["Wav2Vec2 SER<br/>(Fear, Sadness, Anger, Neutral)"]
    end
    
    STT --> FUSION["Multimodal Distress Fusion<br/>Computes SVI Score"]
    PROSODY --> FUSION
    SER --> FUSION
    
    FUSION --> DECISION{"Is SVI >= 0.85<br/>(CRITICAL)?"}
    
    DECISION -->|YES - Critical Threat| ESCALATE["Trigger Emergency Escalation<br/>1. Generate SBAR Report<br/>2. Ring Level-2 Officer Line<br/>3. Dispatch PCR 112 Patrol"]
    DECISION -->|NO - Low/Moderate Risk| NLU["Conversational Reasoning<br/>(Gemini Flash Lite + RAG Guidance)"]
    
    NLU --> TTS["Sarvam Bulbul TTS<br/>Synthesizes Odia Audio"]
    TTS --> STREAM_OUT["Exotel WebSocket Audio Out<br/>PSTN Caller Hears Empathetic Guidance"]
    ESCALATE --> STREAM_OUT
```

---

## 4. Operator Dashboard & Emergency Handoff Flow

```mermaid
flowchart LR
    subgraph OperatorConsole["Operator Dashboard (/operator-dashboard)"]
        WS_CLIENT["Live WebSocket Connection<br/>/ws/dashboard"] --> METRICS["Real-Time Metric Counters<br/>(Active, High Risk, Critical)"]
        WS_CLIENT --> CHART["Distress Indicators Bar Chart<br/>(Fear, Sadness, Stress, Anger)"]
        WS_CLIENT --> QUEUE["Live Incident Priority Queue"]
        QUEUE --> SELECTED["Select Critical Incident"]
    end

    subgraph ClinicalHandoff["SBAR Telemetry Inspection"]
        SELECTED --> SBAR["Automated SBAR Dossier:<br/>• Situation (Active pursuit / weapon)<br/>• Background (Dialect & location)<br/>• Assessment (SVI: 0.92, Fear: 88%)<br/>• Recommendation (PCR 112 + DLSA)"]
        SBAR --> ACTIONS{"Operator Intervention"}
        ACTIONS -->|Acknowledge| ACK["Acknowledge Queue Ticket"]
        ACTIONS -->|Patch Call| PATCH["Three-Way PSTN Bridge into Call"]
        ACTIONS -->|Dispatch Police| POLICE["1-Click Push to CCTNS / Police 112"]
    end
```

---

## 5. Mobile OTP Authentication Flow

```mermaid
sequenceDiagram
    autonumber
    actor User as Citizen User
    participant Page as /login Page
    participant API as Backend Auth Router
    participant Exotel as Exotel SMS Gateway
    participant Store as ACTIVE_OTPS Memory Cache

    User->>Page: Enters mobile number (+91 94371-88210)
    User->>Page: Clicks "Send OTP"
    Page->>API: POST /api/v1/auth/send-otp { phone }
    API->>API: Generates random 6-digit OTP (e.g. 749210)
    API->>Store: Saves OTP with 10-minute TTL
    API->>Exotel: POST /v1/Accounts/teamvortex1/Sms/send.json
    Exotel-->>User: SMS delivered to mobile: "Your SAHAY OTP is 749210"
    API-->>Page: { status: "success", otp: "749210", phone }
    Page-->>User: Displays "✓ OTP sent to +91 94371-88210 via SMS."
    Page->>Page: Auto-populates verification input
    User->>Page: Clicks "Sign In"
    Page->>API: POST /api/v1/auth/login { role: "user", identifier, code: "749210" }
    API->>Store: Validates code == stored_otp
    Store-->>API: Valid match & within 10 min
    API->>Store: Evicts used OTP
    API-->>Page: { token: "sahay_auth_...", role: "user", user: {...} }
    Page-->>User: Redirects to /user-dashboard
```
