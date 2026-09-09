# Product Requirements Document (PRD)
## Project SAHAY (ସହାୟ) – AI Multimodal Voice Distress & Crisis Helpline Agent
**Document Version:** 2.0  
**Target Solution:** Smart India Hackathon (SIH 2026) – Problem Statement 26093  
**Helpline Identity:** National Helpline Against Atrocities (NHAA - 14566)  
**Status:** Approved & Production-Active  

---

## 1. Executive Summary & Problem Overview

### 1.1 Problem Statement (PS 26093)
The National Helpline Against Atrocities (NHAA - 14566) is mandated to provide immediate relief, legal protection, and psychosocial support to citizens facing caste-based atrocities, physical violence, acute intimidation, and social discrimination under the Scheduled Castes and the Scheduled Tribes (Prevention of Atrocities) Act, 1989.

Existing helpline infrastructure suffers from critical operational bottlenecks:
1. **Operator Cognitive Overload & Burnout:** Human dispatchers handle high call volumes with traumatic narratives, resulting in fatigue, delayed risk assessment, and subjective triage.
2. **Linguistic & Dialect Barriers:** Vulnerable marginalized communities in tribal and rural regions (e.g., Koraput, Malkangiri, Mayurbhanj, Kalahandi) speak regional dialects (Kosli, Desia, Kui, Santali, Sambalpuri) or colloquial "broken" Odia. Commercial STT engines hallucinate or fail entirely on these dialects.
3. **The "Whispered Threat" Dilemma (Acoustic Blindness):** In active intimidation scenarios, victims cannot speak openly. They whisper or sound terrified while using deceptively neutral words (e.g., *"haan sab theek hai"* while hiding). Purely text-based LLMs classify these as low-risk, missing life-threatening emergencies.
4. **Spatial Hallucination in Emergencies:** Generic voice AI agents advise callers to *"lock all doors and stay inside"*—a catastrophic hallucination when the caller is fleeing through an open forest, fields, or isolated rural roads.
5. **Statutory Non-Compliance:** Lack of automated compliance with the Digital Personal Data Protection (DPDP) Act 2023, specifically citizen consent management and the enforceable **Right to Erasure**.

### 1.2 The SAHAY Solution
SAHAY (ସହାୟ) is an end-to-end, real-time multimodal voice triage agent that combines:
- **Streaming Telephony & WebRTC Ingestion** (Exotel carrier PSTN + browser microphone).
- **Multimodal Distress Fusion** combining what is said (ASR/NLU), how it is said (Acoustic Prosody + Speech Emotion Recognition), and situational context.
- **Dialect Bridge** supporting standard Odia, Kosli, Desia, Kui, Santali, Sambalpuri, Hindi, and English.
- **Deterministic Safety Engine** ensuring zero spatial hallucinations and instant SBAR operator handoff.
- **Citizen Portal & Transparent Data Control** enabling public complaint tracking and statutory one-click **Delete Records** (DPDP Act).

---

## 2. User Personas & Target Stakeholders

| Persona | Role | Core Goals | Pain Points Addressed |
| :--- | :--- | :--- | :--- |
| **Citizen in Distress** | Victim or witness calling 14566 | Immediate safety guidance, zero judgment, dialect comprehension, privacy control | Eliminates robotic menus; listens to dialects; permits Right to Erasure ("Delete Records") |
| **Helpline Triage Operator** | Level-2 Helpline Staff | Instant situational awareness, structured SBAR reports, automated priority queue | Cuts triage evaluation time from 4+ minutes to <15 seconds with live telemetry |
| **Emergency Dispatcher (112)** | Police/Medical First Responder | Precise GPS/landmark location, threat severity, weapon presence, victim status | Receives structured, verified telemetry before dispatching PCR patrol vans |
| **Legal Aid Officer (DLSA)** | District Legal Services Authority | Section 15A statutory witness compliance, automated case documentation | Automated generation of Section 15A complaint briefs with acoustic audit trail |

---

## 3. Core Functional Requirements (FR)

### FR-1: Telephony & Audio Ingestion
- **FR-1.1 Dual-Channel Ingestion:** The system must accept live phone calls via Exotel PSTN (8kHz μ-law/PCM via WebSocket) and browser microphone streams (16kHz linear PCM via WebRTC/WebSocket).
- **FR-1.2 Ultra-Low Latency VAD:** Voice Activity Detection (Silero/Energy-based) must detect user speech boundaries within 160ms to support natural conversational barge-in.
- **FR-1.3 Resilience & Reconnection:** If carrier WebSocket terminates prematurely, session state must freeze and auto-save without losing assessment records.

### FR-2: Linguistic & Dialect Normalization
- **FR-2.1 Supported Dialects:** Standard Odia (`or-IN`), Kosli/Sambalpuri (`sp-IN`), Desia (`des-IN`), Kui (`kui-IN`), Santali (`sat-IN`), Hindi (`hi-IN`), and Indian English (`en-IN`).
- **FR-2.2 Phonetic Dialect Bridge:** Real-time regex and phonetic transformation engine mapping colloquial distress phrases (e.g., *"mor pache padila godauche"*, *"bana dongar re nuchi achhe"*) to normalized semantic emergency representations.
- **FR-2.3 Automatic Script Detection:** Dynamic detection of Odia script (`\u0b00-\u0b7f`) and Romanized phonetic Odia.

### FR-3: Multimodal Distress Fusion & Scoring (SVI)
- **FR-3.1 Stress Vulnerability Index (SVI):** Compute a continuous normalized score $SVI \in [0.0, 1.0]$ updated turn-by-turn.
- **FR-3.2 Multi-Signal Weights:**
  - Acoustic Prosody ($W_A = 0.35$): Pitch variability, mean F0, shimmer, jitter, pause ratio, speech rate.
  - Speech Emotion Recognition ($W_E = 0.30$): Wav2Vec2 softmax probabilities for Fear, Sadness, Anger, Neutral.
  - Semantic Risk Indicators ($W_L = 0.35$): Active pursuit, weapon presence, physical violence, suicide ideation, caste boycott.
- **FR-3.3 Categorical Triage Levels:**
  - `LOW` ($SVI < 0.35$): Routine query, legal advice, government welfare scheme guidance.
  - `MODERATE` ($0.35 \le SVI < 0.65$): Verbal harassment, procedural delay, non-violent civil dispute.
  - `HIGH` ($0.65 \le SVI < 0.85$): Impending threat, social boycott, physical intimidation, denial of water access.
  - `CRITICAL` ($SVI \ge 0.85$): Active pursuit, armed violence, suicidal ideation, immediate life threat.

### FR-4: Deterministic Trauma Safeguards & Spatial Awareness
- **FR-4.1 Zero Door-Locking Hallucination:** In outdoor, forest, field, or open highway environments, the agent is strictly prohibited from instructing callers to "lock doors", "close windows", or "stay inside".
- **FR-4.2 Wilderness Pursuit Protocol:** The agent must advise: silent movement, phone muted/screen dimmed, finding natural concealment, identifying visible landmarks (temple, road marker, bridge), and queuing silent PCR 112 dispatch.
- **FR-4.3 Emergency Overrides:** Unbypassable rule engine overriding conversational LLM output whenever safety triggers fire.

### FR-5: Citizen Portal & Statutory DPDP Compliance
- **FR-5.1 Public Case Showcase:** Citizens can view their complaints, summaries, and audio recordings using their phone number without mandatory prior login.
- **FR-5.2 Dynamic Random OTP via SMS:** Login requires mobile number verification via genuine 6-digit random OTP generated dynamically and sent via Exotel SMS gateway.
- **FR-5.3 DPDP Right to Erasure ("Delete Records"):** Citizens can permanently withdraw single complaints or trigger **"Delete Records"** to erase all grievance logs and delete physical audio recordings from state servers.

### FR-6: Real-Time Operator Dashboard
- **FR-6.1 Live Telemetry Stream:** WebSocket stream broadcasting SVI score, acoustic prosody, emotion breakdown, and safety flags.
- **FR-6.2 SBAR Clinical Handoff:** Automated generation of Situation-Background-Assessment-Recommendation reports upon Level-2 human escalation.
- **FR-6.3 Real-Time Deletion Synchronization:** When a citizen exercises the Right to Erasure, the operator dashboard removes the record instantly via WebSocket broadcast.

---

## 4. Non-Functional Requirements (NFR)

| Category | Metric / Standard | Requirement |
| :--- | :--- | :--- |
| **End-to-End Latency** | Speech-to-Speech Turnaround | $< 600\text{ ms}$ total pipeline latency |
| **VAD Response** | Barge-In Trigger | $< 160\text{ ms}$ voice activity detection |
| **Availability** | System Uptime | $99.95\%$ for telephony endpoints |
| **Concurrent Capacity** | Call Sessions | $\ge 250$ simultaneous VoIP/telephony sessions per node |
| **Security & Cryptography** | PII Protection | Salted SHA-256 phone hashing (`caller_phone_hash`) |
| **Data In-Transit** | Network Encryption | TLS 1.3 for HTTPS, WSS for WebSockets |
| **Statutory Data Retention** | DPDP Act 2023 | Zero persistent call audio unless explicit citizen consent provided |

---

## 5. Success Metrics & Key Performance Indicators (KPIs)

1. **Average Triage Evaluation Time:** Reduced from $>240$ seconds (manual) to $<15$ seconds (automated SVI).
2. **Linguistic Recognition Rate:** $>92\%$ comprehension accuracy across Kosli, Desia, Kui, and colloquial Odia.
3. **Emergency Interception Rate:** $100\%$ interception of active pursuit/violence cases with zero door-locking hallucinations.
4. **False Positive Escalation Rate:** $<4.5\%$ on routine inquiries, minimizing operator alert fatigue.
5. **Citizen Trust & DPDP Compliance:** 100% compliance with statutory Right to Erasure within $<500\text{ ms}$ of request.
