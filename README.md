# 🛡️ SAHAY (ସହାୟ) — Multilingual AI Voice Distress & Trauma Triage Helpline

> "Bridging acoustic vocal emotion, native tribal dialects, and statutory citizen protection in real time."

SAHAY is an AI-powered real-time stress and trauma triage voice agent and integrated citizen portal built for the **National Helpline Against Atrocities (NHAA - 14566)** under the Ministry of Social Justice and Empowerment (**Smart India Hackathon 2026 — Problem Statement 26093**). It analyzes raw voice tone prosody, understands native broken Odia and tribal dialects (Desia, Kui, Sambalpuri, Santali), deterministically assesses distress levels, and coordinates life-saving emergency intervention (PCR 112) with zero hallucination. 🚀

---

## ✨ Features

- 🎙️ **Dual-Layer Acoustic Emotion Intelligence:** Raw vocal prosody analysis (pitch tremor, speech rate, pause ratios) + fine-tuned Wav2Vec2 audio classification. LLMs never guess emotion—triage tiers are deterministically calculated.
- 🇮🇳 **Native Tribal & Regional Dialect Support:** Built-in comprehension and normalization bridges for Desia (Koraput), Kui (Kandha), Sambalpuri (Kosli), Santali (Ol Chiki), and colloquial broken Odia.
- 🛡️ **Deterministic Safety & Scope Guardrails:** Hardcoded unbypassable rules engine blocking clinical diagnosis, victim blaming, and out-of-scope inquiries (coding, trivia, sports, weather) with localized polite refusals.
- 🌲 **Spatial Environment Grounding:** Detects wilderness/forest pursuits vs. indoor scenarios to prevent dangerous hallucinations (e.g. never advising forest callers to lock doors).
- 📞 **PSTN Telephony & WebRTC Microphone:** Connects seamlessly over Exotel telephony PSTN lines as well as modern browser microphones with barge-in interruption.
- 📊 **Real-Time Dispatcher Triage Dashboard:** Live call telemetry, acoustic jitter/shimmer graphs, transcript diarization, and structured SBAR escalation handoffs for helpline officers.
- 📱 **Fully Responsive Citizen Portal:** High-fidelity government-grade web application with citizen case tracking, grievance logging, and emergency directory.

---

## 🛠️ Tech Stack & Tools Used

SAHAY is built using a modern full-stack architecture combining a reactive TypeScript frontend, high-concurrency FastAPI async voice gateway, and an acoustic ML pipeline.

### Frontend
- ⚛️ **React** - Component architecture (v19)
- ⚡ **Vite** - High-speed bundling and development server
- 📘 **TypeScript** - Strict type-safe interface and model contracts
- 🎨 **Vanilla CSS & Design Tokens** - Fluid, responsive layout grid matching Webflow design specifications
- 🧭 **React Router** - Single-page client-side application routing
- 📱 **Lucide & SVG Sprites** - Vector icons and emergency badges

### Backend & AI Pipeline
- 🐍 **FastAPI & Uvicorn** - High-throughput asynchronous Python ASGI server
- 🎙️ **Sarvam Saaras & Bhashini** - Native Indian speech-to-text (STT) and voice synthesis (TTS)
- 🧠 **PyTorch & HuggingFace Transformers** - Wav2Vec2 speech emotion recognition (SER)
- 🎵 **Librosa & openSMILE** - Digital signal processing, pitch tracking ($F_0$), and eGeMAPS prosodic extraction
- 🗄️ **FAISS & Sentence-Transformers** - Low-latency vector retrieval for SC/ST (PoA) Act 1989 & statutory rights
- 🔄 **WebSocket Engine** - Full-duplex bidirectional streaming for PSTN telephony and browser audio

### Deployment & Telephony
- ▲ **Vercel** - High-performance edge deployment for the Citizen Portal: [https://sahay-helpline.vercel.app](https://sahay-helpline.vercel.app)
- 🚂 **Railway** - Containerized cloud hosting for the real-time FastAPI backend & WebSocket gateway
- 📞 **Exotel** - PSTN cloud telephony trunking (App ID: `1334274`)

---

## ⚙️ How It Works

1. **Call Initiation:** Citizen accesses the helpline via phone call (PSTN 14566 / Exotel) or the web portal microphone.
2. **Dual-Layer Emotion Profiling:** Acoustic prosody analyzer extracts vocal tremor, pitch spikes, and speech-to-pause ratio while Wav2Vec2 classifies acoustic distress without relying on LLM text guesswork.
3. **Dialect Normalization:** The Language Router detects the speaker's tongue and normalizes regional expressions (Desia, Kui, Sambalpuri, Santali, or broken Odia) into standard base semantics.
4. **Safety & Grounding Validation:** The safety rules engine verifies spatial surroundings (wilderness vs. indoor) and blocks out-of-scope queries or clinical diagnoses.
5. **Actionable Intervention:** Low/Medium inquiries receive verified statutory procedural guidance; High/Critical distress triggers immediate supervisor handoff and automated PCR 112 police dispatch coordination.

---

## 🚀 Installation Process

If you want to view and run the project locally:

### 1. Clone the repository:
```bash
git clone https://github.com/sambitverse/sahay-voice-agent.git
cd sahay-voice-agent
```

### 2. Setup & Run Backend (FastAPI):
```bash
cd backend
python -m venv venv

# Windows:
venv\Scripts\activate
# Linux/macOS:
# source venv/bin/activate

pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### 3. Setup & Run Frontend (React + Vite):
```bash
cd ../frontend
npm install
npm run dev
```

### 4. Run Automated Test Suite:
```bash
cd ../backend
python -m pytest tests -v
```
*(All 53 unit and integration tests will execute and validate the full triage loop.)*

*(Note: Production Exotel telephony credentials, Sarvam Saaras keys, and Gemini LLM tokens are securely kept in private environment variables and will fall back to local offline mock engines when unconfigured.)*

---

## 🔮 Future Improvements

- [ ] Direct CAD (Computer-Aided Dispatch) emergency integration with state police control rooms.
- [ ] Offline-first edge voice model execution for low-connectivity remote tribal pockets.
- [ ] Automated SMS / WhatsApp dispatch tracking with live emergency vehicle ETA.
- [ ] Multilingual voice sentiment trend forecasting for district administration dashboards.

---

## 🔗 Live Demos & Endpoints

- 🌐 **Citizen Portal (Vercel)**:  
  **[https://sahay-helpline.vercel.app](https://sahay-helpline.vercel.app)**
- 🚂 **Voice Gateway (Railway)**:  
  **[https://sahay.up.railway.app](https://sahay.up.railway.app)**
- 📊 **Operator Triage Dashboard**:  
  **[https://sahay.up.railway.app/dashboard](https://sahay.up.railway.app/dashboard)**
- 🎙️ **Web Microphone Test Console**:  
  **[https://sahay.up.railway.app/test-console](https://sahay.up.railway.app/test-console)**
- 📑 **API Documentation (Swagger UI)**:  
  **[https://sahay.up.railway.app/docs](https://sahay.up.railway.app/docs)**

---

## 📸 Screenshots

### Portal Home Page

### Statutory Seals & National Helpline Compliance

---

## 📜 Scientific & Ethical Notice

This system is an **AI-assisted decision-support and triage tool**, NOT a clinical diagnostic system. It does not diagnose PTSD, clinical depression, or psychological disorders. High-risk calls are escalated deterministically to authorized human operators, legal aid officers, and emergency services (112/108).

---

## 👨‍💻 Author

Created by **Team Vortex **<br>
-Shakti Ranjan Rout(Leader)<br>
-Sambit Moharana<br>
-Rohan Ku. Muduli<br>
-Satya Prasad Prusty<br>
-S Pritiparna Singh<br>
-Ritisha Sahoo<br>
