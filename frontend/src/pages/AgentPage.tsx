import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../services/api';
import { VoiceAuthModal, checkIsSignedIn } from '../components/VoiceAuthModal';

const detectChatLanguage = (text: string): string => {
  const trimmed = text.trim();
  if (!trimmed) return 'Auto-detect';

  if (/[\u0B00-\u0B7F]/.test(trimmed)) return 'Odia';
  if (/[\u0900-\u097F]/.test(trimmed)) return 'Hindi';
  if (/[\u1C50-\u1C7F]/.test(trimmed)) return 'Santali';

  const lower = trimmed.toLowerCase();
  if (/\b(kuvi|kuv|aane|gida|mera|haji|daha|jaga)\b/.test(lower)) return 'Kuvi';
  if (/\b(kui|aanu|gida|mera|haji|vespa|naju|iddu|daha)\b/.test(lower)) return 'Kui';
  if (/\b(desia|mor pache|godauche|khedi|banchao|bahiskara)\b/.test(lower)) return 'Desia';
  if (/\b(main|mujhe|mera|aap|hai|nahi|madad|bachao|darr|police|ghar|pani|jungle)\b/.test(lower)) return 'Hindi';
  if (/\b(mu|mora|mote|apan|sahajya|ghara|jangala|nuchi|police|banchao|pani)\b/.test(lower)) return 'Odia';
  return 'English';
};

const isLocalEnvironment = () => {
  if (typeof window === 'undefined') return false;
  const h = window.location.hostname;
  return h === 'localhost' || h === '127.0.0.1' || h === '0.0.0.0';
};

const getWebSocketBaseUrl = () => {
  if (import.meta.env.VITE_WS_URL) return import.meta.env.VITE_WS_URL;
  if (isLocalEnvironment()) {
    return `ws://${window.location.hostname === 'localhost' ? 'localhost' : '127.0.0.1'}:8000`;
  }
  return 'wss://sahay.up.railway.app';
};

const resampleTo16k = (samples: Float32Array, originalRate: number): Int16Array => {
  const targetRate = 16000;
  const ratio = originalRate / targetRate;
  const outLength = Math.max(1, Math.ceil(samples.length / ratio));
  const output = new Int16Array(outLength);

  for (let i = 0; i < outLength; i += 1) {
    const sourceIndex = i * ratio;
    const index = Math.min(samples.length - 1, Math.floor(sourceIndex));
    const nextIndex = Math.min(samples.length - 1, index + 1);
    const alpha = sourceIndex - index;
    const current = samples[index] ?? 0;
    const next = samples[nextIndex] ?? 0;
    const blended = current + (next - current) * alpha;
    const clipped = Math.max(-1, Math.min(1, blended));
    output[i] = clipped < 0 ? clipped * 0x8000 : clipped * 0x7fff;
  }

  return output;
};

interface VoiceChatMessage {
  id: string;
  sender: 'user' | 'agent';
  text: string;
  timestamp: string;
  risk?: string;
  phase?: string;
  language?: string;
}

export const AgentPage: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'voice' | 'chat'>('voice');
  const [callerPhone, setCallerPhone] = useState<string>(() => {
    return (
      sessionStorage.getItem('sahay_caller_phone') ||
      localStorage.getItem('sahay_caller_phone') ||
      '+91 94371-88210'
    );
  });
  const [isSignedIn, setIsSignedIn] = useState<boolean>(() => checkIsSignedIn());
  const [showAuthModal, setShowAuthModal] = useState<boolean>(false);
  const [isCalling, setIsCalling] = useState(false);
  const [isConnecting, setIsConnecting] = useState(false);
  const [callDuration, setCallDuration] = useState(0);
  const [detectedLanguage, setDetectedLanguage] = useState('Gemini Multilingual Auto-Detect');
  const [preferredLanguage, setPreferredLanguage] = useState<string>('auto');
  const [speechSpeed, setSpeechSpeed] = useState<number>(1.2);
  const [voiceStatus, setVoiceStatus] = useState('Ready — allow mic access to begin the voice session.');
  const [vadDebug, setVadDebug] = useState<{ rms: number; threshold: number; reason: string; is_speaking: boolean; zcr: number } | null>(null);

  // Live Voice Stream Chat Messages
  const [voiceChatMessages, setVoiceChatMessages] = useState<VoiceChatMessage[]>([
    {
      id: 'greet_init',
      sender: 'agent',
      text: 'ନମସ୍କାର, ମୁଁ ସହାୟ ୧୪୫୬୬ ହେଲ୍ପଲାଇନ୍ ଏଜେଣ୍ଟ୍ କହୁଛି। ଆପଣ ନିରାପଦରେ ଅଛନ୍ତି କି? ଦୟାକରି ଆପଣଙ୍କ ସମସ୍ୟା କୁହନ୍ତୁ। (Namaskar, I am SAHAY Helpline Agent. Are you safe right now? Please state your emergency or problem.)',
      timestamp: 'Helpline Ready',
      risk: 'LOW'
    }
  ]);
  const [liveSpeechText, setLiveSpeechText] = useState('');
  const [voiceInputText, setVoiceInputText] = useState('');
  const [isAiThinking, setIsAiThinking] = useState(false);
  const [isAiSpeakingOutLoud, setIsAiSpeakingOutLoud] = useState(false);
  const [isListeningNow, setIsListeningNow] = useState(false);
  const isListeningNowRef = useRef<boolean>(false);

  // Live Telemetry state
  const [liveSvi, setLiveSvi] = useState(0.12);
  const [liveRiskLevel, setLiveRiskLevel] = useState('STANDBY');
  const [liveAcoustic, setLiveAcoustic] = useState<{ mean_pitch_f0?: number; jitter?: number; pause_ratio?: number; speech_rate?: number }>({});

  // Text tab state
  const [chatMessages, setChatMessages] = useState<Array<{ sender: 'user' | 'agent'; text: string; risk?: string }>>([
    {
      sender: 'agent',
      text: 'ନମସ୍କାର, ମୁଁ ସହାୟ ଭଏସ୍ ଏଜେଣ୍ଟ୍ କହୁଛି। ଆପଣ ନିରାପଦରେ ଅଛନ୍ତି କି? କୁହନ୍ତୁ ଆମେ ଆପଣଙ୍କୁ କିପରି ସାହାଯ୍ୟ କରିପାରିବୁ? (Namaskar, I am SAHAY Helpline Agent. Are you safe right now? Please tell me how we can support you.)'
    }
  ]);
  const [inputMessage, setInputMessage] = useState('');
  const detectedChatLanguage = detectChatLanguage(inputMessage);
  const [isTyping, setIsTyping] = useState(false);

  // Refs
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const mediaStreamRef = useRef<MediaStream | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const sourceNodeRef = useRef<MediaStreamAudioSourceNode | null>(null);
  const processorNodeRef = useRef<ScriptProcessorNode | null>(null);
  const audioPlaybackRef = useRef<HTMLAudioElement | null>(null);
  const sessionCallIdRef = useRef<string>('');
  const stopVoiceSessionRef = useRef<() => Promise<void>>(() => Promise.resolve());
  const recognitionRef = useRef<any>(null);
  const chatContainerRef = useRef<HTMLDivElement | null>(null);
  const hasReceivedAudioRef = useRef<boolean>(false);
  const audioTimeoutRef = useRef<number | null>(null);
  const latestAgentTextRef = useRef<string>('');
  const isCallingRef = useRef<boolean>(false);
  const isAiSpeakingOutLoudRef = useRef<boolean>(false);
  const lastAiSpeakingEndTimeRef = useRef<number>(0);
  const recentAiTextsRef = useRef<string[]>([
    'ନମସ୍କାର, ମୁଁ ସହାୟ ୧୪୫୬୬ ହେଲ୍ପଲାଇନ୍ ଏଜେଣ୍ଟ୍ କହୁଛି। ଆପଣ ନିରାପଦରେ ଅଛନ୍ତି କି? ଦୟାକରି ଆପଣଙ୍କ ସମସ୍ୟା କୁହନ୍ତୁ।',
    'Namaskar. NHAA 14566 helpline re apananku swagata. Daya kari apananka samasya kuhan tu.',
    'Namaskar. Rashtriya Helpline 14566 mein aapka swagat hai. Kripya apni samasya batayein.',
    'Hello. Welcome to the National Helpline Against Atrocities (14566). Please tell us how we can help you.',
    'Johar. NHAA 14566 helpline re sagun daram. Daya kate apanar samasya lai tabon pe.',
    'नमस्ते, मैं सहाय 14566 हेल्पलाइन एजेंट हूँ। क्या आप सुरक्षित हैं? कृपया अपनी समस्या बताएं।'
  ]);

  const syncCallerSession = (phone: string) => {
    localStorage.setItem('sahay_caller_phone', phone);
    sessionStorage.setItem('sahay_caller_phone', phone);
    if (checkIsSignedIn()) {
      const cleanDigits = phone.replace(/\D/g, '').slice(-4) || '8821';
      const existingUserStr = sessionStorage.getItem('sahay_user');
      let userName = `Verified Citizen (${phone})`;
      if (existingUserStr) {
        try {
          const u = JSON.parse(existingUserStr);
          if (u.name) userName = u.name;
        } catch {}
      }
      sessionStorage.setItem(
        'sahay_user',
        JSON.stringify({
          role: 'user',
          phone: phone,
          id: `citizen_${cleanDigits}`,
          name: userName,
          authenticated: true,
          is_signed_in: true
        })
      );
    }
  };

  const handleSignOut = () => {
    if (isCalling || isConnecting) {
      stopVoiceSessionRef.current();
    }
    sessionStorage.removeItem('sahay_token');
    sessionStorage.removeItem('sahay_signed_in');
    sessionStorage.removeItem('sahay_user');
    setIsSignedIn(false);
    window.dispatchEvent(new Event('storage'));
    window.dispatchEvent(new CustomEvent('sahay_auth_changed'));
    setVoiceStatus('Signed out. Sign up or sign in required before starting microphone voice stream.');
  };

  const isEchoOfRecentAiSpeech = (text: string): boolean => {
    if (!text || !text.trim()) return false;
    const cleanInput = text.toLowerCase().replace(/[^\w\s\u0900-\u0D7F]/gi, ' ').trim();
    if (!cleanInput) return false;
    const inputWords = cleanInput.split(/\s+/).filter((w) => w.length > 2);
    if (inputWords.length === 0) return false;

    for (const recent of recentAiTextsRef.current) {
      const cleanRecent = recent.toLowerCase().replace(/[^\w\s\u0900-\u0D7F]/gi, ' ').trim();
      if (!cleanRecent) continue;

      if (cleanRecent.includes(cleanInput) || cleanInput.includes(cleanRecent)) {
        return true;
      }
      const recentWords = new Set(cleanRecent.split(/\s+/).filter((w) => w.length > 2));
      let matchCount = 0;
      for (const w of inputWords) {
        if (recentWords.has(w)) matchCount++;
      }
      if (matchCount / inputWords.length >= 0.35) {
        return true;
      }
    }
    return false;
  };

  useEffect(() => {
    isCallingRef.current = isCalling;
  }, [isCalling]);

  // Auto-scroll inside chat box only
  useEffect(() => {
    if (chatContainerRef.current) {
      chatContainerRef.current.scrollTop = chatContainerRef.current.scrollHeight;
    }
  }, [voiceChatMessages, liveSpeechText, isAiThinking]);

  useEffect(() => {
    if (!isCalling) return;
    const timer = window.setInterval(() => setCallDuration((prev) => prev + 1), 1000);
    return () => window.clearInterval(timer);
  }, [isCalling]);

  // Waveform canvas animation
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let animId: number;
    let phase = 0;

    const render = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      const width = canvas.width;
      const height = canvas.height;
      const centerY = height / 2;

      ctx.lineWidth = 2.5;
      ctx.strokeStyle = isCalling
        ? (isAiSpeakingOutLoud ? '#0284c7' : (isListeningNow ? '#10b981' : '#f59e0b'))
        : '#94a3b8';

      ctx.beginPath();
      for (let x = 0; x < width; x++) {
        const freq = isCalling ? (isAiSpeakingOutLoud ? 0.05 : (isListeningNow ? 0.035 : 0.02)) : 0.015;
        const amp = isCalling
          ? (isAiSpeakingOutLoud ? Math.sin(phase + x * 0.08) * 30 + 12 : (isListeningNow ? Math.sin(phase + x * 0.05) * 22 + 9 : Math.sin(phase + x * 0.03) * 12 + 4))
          : 3;
        const y = centerY + Math.sin(x * freq + phase) * amp;
        if (x === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      }
      ctx.stroke();

      phase += isCalling ? (isAiSpeakingOutLoud ? 0.16 : 0.08) : 0.02;
      animId = requestAnimationFrame(render);
    };

    render();
    return () => cancelAnimationFrame(animId);
  }, [isCalling, isAiSpeakingOutLoud, isListeningNow]);

  useEffect(() => {
    return () => {
      stopVoiceSessionRef.current();
    };
  }, []);

  const handleAiSpeechCompleted = useCallback(() => {
    setIsAiSpeakingOutLoud(false);
    isAiSpeakingOutLoudRef.current = false;
    setIsAiThinking(false);
    lastAiSpeakingEndTimeRef.current = Date.now();

    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ event: 'ai_speaking_ended' }));
    }

    // Acoustic room reverb guard: allow 500ms for physical speaker sound & room echo to dissipate
    window.setTimeout(() => {
      if (!isCallingRef.current || isAiSpeakingOutLoudRef.current) return;
      isListeningNowRef.current = true;
      setIsListeningNow(true);
      setLiveSpeechText('');
      setVoiceStatus('🟢 Listening now — please speak your message.');

      if (recognitionRef.current && isCallingRef.current) {
        try {
          recognitionRef.current.start();
        } catch {
          // already active or not supported
        }
      }
    }, 500);
  }, []);

  // Web Speech synthesis fallback with natural Indian voice selection
  const speakAiResponse = useCallback((text: string, languageHint?: string) => {
    if (!('speechSynthesis' in window)) return;
    try {
      window.speechSynthesis.cancel();
      let cleanText = text
        .replace(/[*_#`~]/g, '')
        .replace(/\(http[^)]+\)/g, '')
        .replace(/\[VERIFIED[^\]]*\]/g, '')
        .replace(/\b14566\b/g, '1 4 5 6 6')
        .replace(/\b112\b/g, '1 1 2')
        .replace(/\b108\b/g, '1 0 8')
        .trim();
      if (!cleanText) return;

      const utterance = new SpeechSynthesisUtterance(cleanText);
      const voices = window.speechSynthesis.getVoices();

      const lh = (languageHint || '').toLowerCase();
      const hasDevanagari = /[\u0900-\u097F]/.test(cleanText);
      const hasOdia = /[\u0B00-\u0B7F]/.test(cleanText);

      let preferredVoice = null;
      if (hasDevanagari || lh.includes('hi')) {
        preferredVoice = voices.find(v => v.lang.includes('hi') || v.name.includes('Swara') || v.name.includes('हिन्दी'));
      } else if (hasOdia || lh.includes('or') || lh.includes('od') || lh.includes('sat') || lh.includes('des') || lh.includes('kui') || lh.includes('kuvi')) {
        preferredVoice = voices.find(v => v.lang.includes('or') || v.lang.includes('hi') || v.name.includes('Swara'));
      } else if (lh.includes('en')) {
        preferredVoice = voices.find(v => v.lang === 'en-IN' || v.name.includes('Neerja') || v.name.includes('India'));
      }

      if (!preferredVoice) {
        preferredVoice =
          voices.find(v => v.lang === 'hi-IN' || v.name.includes('Swara') || v.name.includes('हिन्दी')) ||
          voices.find(v => v.lang === 'en-IN' || v.name.includes('Neerja') || v.name.includes('India')) ||
          voices.find(v => v.lang.includes('hi') || v.name.toLowerCase().includes('hindi')) ||
          voices.find(v => v.lang.startsWith('en')) ||
          voices[0];
      }

      if (preferredVoice) {
        utterance.voice = preferredVoice;
        utterance.lang = preferredVoice.lang;
      }
      utterance.rate = speechSpeed;
      utterance.pitch = 1.0;
      utterance.onstart = () => {
        setIsAiSpeakingOutLoud(true);
        isAiSpeakingOutLoudRef.current = true;
        isListeningNowRef.current = false;
        setIsListeningNow(false);
        setVoiceStatus('🔊 AI is speaking...');
        recentAiTextsRef.current = [cleanText, ...recentAiTextsRef.current.slice(0, 8)];
        if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
          wsRef.current.send(JSON.stringify({ event: 'ai_speaking_started' }));
        }
      };
      utterance.onend = () => {
        handleAiSpeechCompleted();
      };
      utterance.onerror = () => {
        handleAiSpeechCompleted();
      };
      window.speechSynthesis.speak(utterance);
    } catch (err) {
      console.warn('Speech synthesis notice:', err);
      handleAiSpeechCompleted();
    }
  }, [speechSpeed, handleAiSpeechCompleted]);

  const handleReplayVoice = (text: string) => {
    isListeningNowRef.current = false;
    setIsListeningNow(false);
    if (recognitionRef.current) {
      try { recognitionRef.current.stop(); } catch {}
    }
    speakAiResponse(text);
  };

  const getRecognitionLang = (lang: string): string => {
    switch (lang) {
      case 'or-IN':
        return 'or-IN';
      case 'hi-IN':
        return 'hi-IN';
      case 'en-IN':
        return 'en-IN';
      case 'sat-IN':
      case 'des-IN':
      case 'kui-IN':
      case 'kuvi-IN':
        return 'or-IN';
      case 'auto':
      default: {
        const navLang = (typeof navigator !== 'undefined' ? navigator.language || '' : '').toLowerCase();
        if (navLang.startsWith('hi')) return 'hi-IN';
        if (navLang.startsWith('en')) return 'en-IN';
        return 'or-IN';
      }
    }
  };

  const handleLanguageChange = (newLang: string) => {
    setPreferredLanguage(newLang);
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        event: 'set_language',
        language: newLang
      }));
    }
    if (recognitionRef.current) {
      const recLang = getRecognitionLang(newLang);
      recognitionRef.current.lang = recLang;
      try {
        recognitionRef.current.stop();
      } catch {
        // will restart in onend
      }
    }
  };

  const stopVoiceSession = useCallback(async () => {
    setIsConnecting(false);
    setIsCalling(false);
    setIsAiThinking(false);
    setIsAiSpeakingOutLoud(false);
    isAiSpeakingOutLoudRef.current = false;
    isListeningNowRef.current = false;
    setIsListeningNow(false);
    lastAiSpeakingEndTimeRef.current = 0;
    setLiveSpeechText('');
    setVoiceStatus('Voice session ended. Start again when ready to speak.');

    if (audioTimeoutRef.current) {
      clearTimeout(audioTimeoutRef.current);
      audioTimeoutRef.current = null;
    }

    if ('speechSynthesis' in window) {
      window.speechSynthesis.cancel();
    }

    if (recognitionRef.current) {
      try {
        recognitionRef.current.stop();
      } catch {}
      recognitionRef.current = null;
    }

    if (audioPlaybackRef.current) {
      audioPlaybackRef.current.pause();
      audioPlaybackRef.current.currentTime = 0;
      audioPlaybackRef.current.src = '';
    }

    if (wsRef.current) {
      try {
        wsRef.current.send(JSON.stringify({ event: 'barge_in' }));
        wsRef.current.send(JSON.stringify({ event: 'stop' }));
      } catch {}
    }

    if (processorNodeRef.current) {
      processorNodeRef.current.disconnect();
      processorNodeRef.current = null;
    }
    if (sourceNodeRef.current) {
      sourceNodeRef.current.disconnect();
      sourceNodeRef.current = null;
    }
    if (mediaStreamRef.current) {
      mediaStreamRef.current.getTracks().forEach((track) => track.stop());
      mediaStreamRef.current = null;
    }
    if (audioContextRef.current) {
      try {
        await audioContextRef.current.close();
      } catch {}
      audioContextRef.current = null;
    }
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }

    // Automatically register completed helpline call session with grievance database & user dashboard
    if (callDuration >= 3) {
      const randId = Math.floor(1000 + Math.random() * 9000);
      const ticketRef = `TKT-${new Date().toISOString().slice(0, 10).replace(/-/g, '')}-${randId}`;
      try {
        await api.registerComplaint({
          id: `complaint_${Date.now()}`,
          call_id: sessionCallIdRef.current || `call_${randId}_agent`,
          caller_number: callerPhone,
          ticket_ref: ticketRef,
          type: 'voice',
          timestamp: new Date().toISOString().replace('T', ' ').slice(0, 16),
          risk_level: liveRiskLevel === 'CRITICAL' ? 'CRITICAL' : (liveRiskLevel === 'HIGH' ? 'HIGH' : 'LOW'),
          summary: `Helpline voice triage stream (${formatSeconds(callDuration)}). Spoken dialect: ${preferredLanguage}. SVI: ${(liveSvi * 100).toFixed(0)}%.`,
          language: preferredLanguage === 'auto' ? 'or-IN' : preferredLanguage,
          recording_url: `/api/v1/recordings/${sessionCallIdRef.current || `call_${randId}_agent`}.wav`,
          recommended_services: ['14566 National Helpline', 'DLSA Emergency Cell', 'PCR 112 Police Dispatch'],
          status: 'REGISTERED_ACTIVE_TRIAGE',
          is_legitimate: true
        });
      } catch (err) {
        console.warn('Could not sync call recording to backend:', err);
      }
    }

    setCallDuration(0);
  }, [callDuration, callerPhone, liveRiskLevel, preferredLanguage, liveSvi]);

  useEffect(() => {
    stopVoiceSessionRef.current = stopVoiceSession;
  }, [stopVoiceSession]);

  const startVoiceSession = useCallback(async (phoneToUse?: string) => {
    const targetPhone = phoneToUse || callerPhone;
    syncCallerSession(targetPhone);
    setIsConnecting(true);
    setVoiceStatus('Requesting microphone access in browser...');

    if (!navigator?.mediaDevices?.getUserMedia) {
      setIsConnecting(false);
      setVoiceStatus('❌ Microphone API is not available or blocked in this browser context.');
      alert('Microphone access is unavailable. Please ensure you are opening this on http://localhost:5173 or http://127.0.0.1:5173 with microphone permissions enabled.');
      return;
    }

    let stream: MediaStream;
    let audioContext: AudioContext;

    try {
      stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: false
        }
      });
      mediaStreamRef.current = stream;

      const AudioContextClass = window.AudioContext || (window as any).webkitAudioContext;
      audioContext = new AudioContextClass();
      audioContextRef.current = audioContext;
      if (audioContext.state === 'suspended') {
        await audioContext.resume();
      }
    } catch (micErr: any) {
      console.error('[VoiceAgent] Microphone access error:', micErr);
      setIsConnecting(false);
      const isDenied = micErr?.name === 'NotAllowedError' || micErr?.name === 'PermissionDeniedError';
      const msg = isDenied
        ? '❌ Microphone permission denied. Please allow microphone access in your browser address bar and try again.'
        : `❌ Microphone error: ${micErr?.message || micErr?.name || 'Device unavailable'}. Check your audio settings.`;
      setVoiceStatus(msg);
      setDetectedLanguage('Microphone denied');
      return;
    }

    try {
      sessionCallIdRef.current = `browser_${Date.now()}`;
      const langParam = preferredLanguage && preferredLanguage !== 'auto' ? `&language=${encodeURIComponent(preferredLanguage)}` : '';
      const phoneParam = `&phone=${encodeURIComponent(targetPhone)}`;

      let currentUserName = 'Citizen';
      try {
        const u = JSON.parse(sessionStorage.getItem('sahay_user') || '{}');
        if (u && u.name) currentUserName = u.name;
      } catch {}
      const nameParam = `&name=${encodeURIComponent(currentUserName)}`;

      const socketUrl = `${getWebSocketBaseUrl()}/ws/client/${sessionCallIdRef.current}?${phoneParam.slice(1)}${nameParam}${langParam}`;
      console.log('[VoiceAgent] Connecting WebSocket to:', socketUrl);
      setVoiceStatus('Connecting to SAHAY 14566 Crisis Voice Gateway on port 8000...');

      const ws = new WebSocket(socketUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        console.log('[VoiceAgent] WebSocket connected successfully');
        setIsConnecting(false);
        setIsCalling(true);
        isCallingRef.current = true;
        isListeningNowRef.current = false;
        setIsListeningNow(false);
        setIsAiSpeakingOutLoud(true);
        isAiSpeakingOutLoudRef.current = true;
        setVoiceStatus('Connected — AI helpline greeting is speaking...');
        setDetectedLanguage('Live WebSocket Connected');
        setLiveRiskLevel('ACTIVE');
        const initLang = preferredLanguage === 'auto' ? 'auto' : preferredLanguage;
        ws.send(JSON.stringify({ event: 'set_language', language: initLang }));

        try {
          const source = audioContext.createMediaStreamSource(stream);
          sourceNodeRef.current = source;
          const processor = audioContext.createScriptProcessor(2048, 1, 1);
          processorNodeRef.current = processor;

          processor.onaudioprocess = (event) => {
            if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return;
            if (!isCallingRef.current) return;
            // STRICT MICROPHONE LOOPBACK SUPPRESSION:
            // Never capture or stream microphone audio while AI is speaking, while not in listening phase,
            // or during the 500ms room reverb cooldown after AI finishes speaking.
            if (!isListeningNowRef.current || isAiSpeakingOutLoudRef.current) return;
            if (Date.now() - lastAiSpeakingEndTimeRef.current < 500) return;

            const input = event.inputBuffer.getChannelData(0);
            const pcm16 = resampleTo16k(input, audioContext.sampleRate || 48000);
            const payload = new ArrayBuffer(pcm16.length * 2);
            const view = new DataView(payload);
            for (let i = 0; i < pcm16.length; i += 1) {
              view.setInt16(i * 2, pcm16[i], true);
            }
            wsRef.current.send(payload);
          };

          const gainNode = audioContext.createGain();
          gainNode.gain.value = 0;
          source.connect(processor);
          processor.connect(gainNode);
          gainNode.connect(audioContext.destination);

          const SpeechRec = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
          if (SpeechRec) {
            try {
              const recognition = new SpeechRec();
              recognition.continuous = true;
              recognition.interimResults = true;
              recognition.maxAlternatives = 1;
              recognition.lang = getRecognitionLang(preferredLanguage);

              let silenceCommitTimer: any = null;

              const commitTranscript = (finalText: string) => {
                const cleaned = finalText.trim();
                if (silenceCommitTimer) {
                  clearTimeout(silenceCommitTimer);
                  silenceCommitTimer = null;
                }
                setLiveSpeechText('');
                if (!isListeningNowRef.current || isAiSpeakingOutLoudRef.current) {
                  console.log('[VoiceAgent] Dropped transcript commit: not in listening phase');
                  return;
                }
                if (!cleaned) return;
                if (isEchoOfRecentAiSpeech(cleaned)) {
                  console.log('[VoiceAgent] Dropped transcript commit: echo of recent AI speech:', cleaned);
                  return;
                }
                const isSingleWordEnglish = /^[a-zA-Z]{1,12}$/.test(cleaned);
                if (isSingleWordEnglish && preferredLanguage !== 'en-IN') {
                  console.log('[VoiceAgent] Dropped single-word English hallucination from browser speech recognition:', cleaned);
                  return;
                }

                isListeningNowRef.current = false;
                setIsListeningNow(false);
                if (recognitionRef.current) {
                  try {
                    recognitionRef.current.stop();
                  } catch {}
                }

                if (cleaned && ws.readyState === WebSocket.OPEN) {
                  console.log('[VoiceAgent] Signaling utterance commit to Bhashini ASR for speech:', cleaned);
                  setIsAiThinking(true);
                  setVoiceStatus('Input captured — Bhashini analyzing speech...');
                  ws.send(JSON.stringify({
                    event: 'commit'
                  }));
                }
              };

              recognition.onresult = (e: any) => {
                if (!isListeningNowRef.current || isAiSpeakingOutLoudRef.current) {
                  return;
                }

                let completeFinal = '';
                let completeInterim = '';
                for (let i = 0; i < e.results.length; i++) {
                  const trans = e.results[i][0].transcript;
                  if (e.results[i].isFinal) {
                    completeFinal += ' ' + trans;
                  } else {
                    completeInterim += ' ' + trans;
                  }
                }

                completeFinal = completeFinal.trim();
                completeInterim = completeInterim.trim();
                const fullSentence = (completeFinal ? completeFinal + (completeInterim ? ' ' + completeInterim : '') : completeInterim).trim();

                if (!fullSentence) return;
                if (isEchoOfRecentAiSpeech(fullSentence)) return;

                setLiveSpeechText(fullSentence);

                if (silenceCommitTimer) {
                  clearTimeout(silenceCommitTimer);
                }
                silenceCommitTimer = setTimeout(() => {
                  if (fullSentence && isListeningNowRef.current && !isAiSpeakingOutLoudRef.current) {
                    if (!isEchoOfRecentAiSpeech(fullSentence)) {
                      commitTranscript(fullSentence);
                    }
                  }
                }, 1200);
              };

              recognition.onend = () => {
                if (isCallingRef.current && isListeningNowRef.current && recognitionRef.current) {
                  try {
                    recognitionRef.current.start();
                  } catch {}
                }
              };

              recognition.onerror = (recErr: any) => {
                console.warn('[VoiceAgent] Speech recognition notice:', recErr);
              };

              recognitionRef.current = recognition;
            } catch {}
          }
        } catch (audioSetupErr) {
          console.error('[VoiceAgent] Audio processing pipeline setup error:', audioSetupErr);
          setVoiceStatus('⚠️ Audio pipeline initialization failed.');
        }
      };

      ws.onerror = (err) => {
        console.error('[VoiceAgent] WebSocket error:', err);
        setIsConnecting(false);
        setVoiceStatus('❌ Voice WebSocket failed. Verify the backend server is running on port 8000.');
        setDetectedLanguage('Voice connection failed');
        stopVoiceSession();
      };

      ws.onmessage = async (event) => {
        try {
          const payload = JSON.parse(event.data);

          if (payload.event === 'connected') {
            setVoiceStatus('Connected to SAHAY 14566 Crisis Voice Gateway.');
          }

          if (payload.event === 'user_transcript' && payload.text) {
            const userText = payload.text;
            if (isEchoOfRecentAiSpeech(userText)) {
              console.log('[VoiceAgent] Dropped user_transcript: acoustic loopback of AI speech:', userText);
              return;
            }
            setVoiceChatMessages((prev) => {
              if (prev.length > 0 && prev[prev.length - 1].sender === 'user') {
                const updated = [...prev];
                updated[updated.length - 1] = {
                  ...updated[updated.length - 1],
                  text: userText,
                  language: payload.language
                };
                return updated;
              }
              if (prev.some((m) => m.sender === 'user' && m.text === userText)) {
                return prev;
              }
              return [
                ...prev,
                {
                  id: `usr_${Date.now()}_${Math.random().toString(36).substring(2, 6)}`,
                  sender: 'user',
                  text: userText,
                  timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
                  language: payload.language
                }
              ];
            });
            setIsAiThinking(true);
            setVoiceStatus('User speech received — analyzing distress & formulating response...');
          }

          if (payload.event === 'assessment_update') {
            if (payload.language) {
              setDetectedLanguage(payload.language.toUpperCase());
            }
            if (payload.transcript && !isEchoOfRecentAiSpeech(payload.transcript)) {
              setVoiceChatMessages((prev) => {
                if (prev.some((m) => m.sender === 'user' && m.text === payload.transcript)) {
                  return prev;
                }
                return [
                  ...prev,
                  {
                    id: `usr_${Date.now()}_${Math.random().toString(36).substring(2, 6)}`,
                    sender: 'user',
                    text: payload.transcript,
                    timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
                    language: payload.language
                  }
                ];
              });
            }
            if (payload.svi_score !== undefined) {
              setLiveSvi(payload.svi_score);
            }
            if (payload.risk && payload.risk.risk_level) {
              setLiveRiskLevel(payload.risk.risk_level);
            }
            if (payload.acoustic) {
              setLiveAcoustic(payload.acoustic);
            }
          }

          if (payload.event === 'noise_ignored') {
            setVoiceStatus('Background noise filtered — listening for your speech.');
          }

          if (payload.event === 'vad_debug') {
            setVadDebug({
              rms: payload.rms ?? 0,
              threshold: payload.threshold ?? 0,
              reason: payload.reason ?? 'unknown',
              is_speaking: Boolean(payload.is_speaking),
              zcr: payload.zcr ?? 0,
            });
          }

          if (payload.event === 'clear') {
            if (audioPlaybackRef.current) {
              audioPlaybackRef.current.pause();
            }
            if (audioTimeoutRef.current) {
              clearTimeout(audioTimeoutRef.current);
              audioTimeoutRef.current = null;
            }
            setIsAiSpeakingOutLoud(false);
            isAiSpeakingOutLoudRef.current = false;
            setIsAiThinking(false);
            isListeningNowRef.current = true;
            setIsListeningNow(true);
            setVoiceStatus('🟢 Listening now — please speak your message.');
          }

          if (payload.event === 'agent_response' && payload.text) {
            setIsAiThinking(false);
            const agentText = payload.text;
            latestAgentTextRef.current = agentText;
            recentAiTextsRef.current = [agentText, ...recentAiTextsRef.current.slice(0, 5)];
            if (payload.language) {
              setDetectedLanguage(payload.language.toUpperCase());
            } else {
              setDetectedLanguage(payload.risk_level || 'LIVE');
            }
            setLiveRiskLevel(payload.risk_level || 'ACTIVE');
            setVoiceStatus('AI response generated.');

            setVoiceChatMessages((prev) => {
              if (prev.length > 0 && prev[prev.length - 1].sender === 'agent' && prev[prev.length - 1].text === agentText) {
                return prev;
              }
              return [
                ...prev,
                {
                  id: `agt_${Date.now()}_${Math.random().toString(36).substring(2, 6)}`,
                  sender: 'agent',
                  text: agentText,
                  risk: payload.risk_level,
                  phase: payload.phase,
                  timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
                }
              ];
            });

            hasReceivedAudioRef.current = false;
            if (audioTimeoutRef.current) clearTimeout(audioTimeoutRef.current);
            // Safety timeout: if TTS media does not arrive within 3.5s, switch back to listening
            audioTimeoutRef.current = window.setTimeout(() => {
              if (!hasReceivedAudioRef.current) {
                console.log('[VoiceAgent] Audio timeout fallback triggered: listening now');
                handleAiSpeechCompleted();
              }
            }, 3500);
          }

          if (payload.event === 'media' && payload.payload) {
            hasReceivedAudioRef.current = true;
            if (audioTimeoutRef.current) clearTimeout(audioTimeoutRef.current);
            isListeningNowRef.current = false;
            setIsListeningNow(false);
            setVoiceStatus('🔊 AI is speaking...');
            setIsAiSpeakingOutLoud(true);
            isAiSpeakingOutLoudRef.current = true;
            if (latestAgentTextRef.current) {
              recentAiTextsRef.current = [latestAgentTextRef.current, ...recentAiTextsRef.current.slice(0, 8)];
            }
            if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
              wsRef.current.send(JSON.stringify({ event: 'ai_speaking_started' }));
            }

            try {
              const audioBytes = Uint8Array.from(atob(payload.payload), (c) => c.charCodeAt(0));
              const audioBlob = new Blob([audioBytes], { type: 'audio/wav' });
              const audioUrl = URL.createObjectURL(audioBlob);
              if (audioPlaybackRef.current) {
                audioPlaybackRef.current.pause();
                if (audioPlaybackRef.current.src) {
                  URL.revokeObjectURL(audioPlaybackRef.current.src);
                }
              }
              const audio = new Audio(audioUrl);
              audio.playbackRate = speechSpeed;
              audioPlaybackRef.current = audio;

              // Playback duration safety timeout in case audio.onended fails to fire
              const approxDurationMs = Math.max(3000, (audioBytes.length / 32) + 1200);
              audioTimeoutRef.current = window.setTimeout(() => {
                handleAiSpeechCompleted();
              }, approxDurationMs);

              audio.onended = () => {
                if (audioTimeoutRef.current) clearTimeout(audioTimeoutRef.current);
                handleAiSpeechCompleted();
              };
              audio.onerror = () => {
                if (audioTimeoutRef.current) clearTimeout(audioTimeoutRef.current);
                speakAiResponse(latestAgentTextRef.current, payload.language);
              };
              audio.play().catch(() => {
                speakAiResponse(latestAgentTextRef.current, payload.language);
              });
            } catch {
              speakAiResponse(latestAgentTextRef.current, payload.language);
            }
          }

          if (payload.event === 'tts_unavailable') {
            hasReceivedAudioRef.current = true;
            if (audioTimeoutRef.current) clearTimeout(audioTimeoutRef.current);
            isListeningNowRef.current = false;
            setIsListeningNow(false);
            setIsAiSpeakingOutLoud(true);
            isAiSpeakingOutLoudRef.current = true;
            setVoiceStatus('🔊 AI is speaking...');
            if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
              wsRef.current.send(JSON.stringify({ event: 'ai_speaking_started' }));
            }
            speakAiResponse(payload.text || latestAgentTextRef.current, payload.language);
          }
        } catch {}
      };

      ws.onclose = () => {
        setIsConnecting(false);
        setIsCalling(false);
        setIsAiThinking(false);
        setIsAiSpeakingOutLoud(false);
        isAiSpeakingOutLoudRef.current = false;
        isListeningNowRef.current = false;
        setIsListeningNow(false);
        lastAiSpeakingEndTimeRef.current = 0;
        setVoiceStatus('Voice session ended. Start again when ready to speak.');
        setDetectedLanguage('Sarvam 22+ Auto-Detect');
      };
    } catch {
      setIsConnecting(false);
      setVoiceStatus('Voice connection failed. Start again after checking backend status.');
      setDetectedLanguage('Voice connection failed');
      setIsCalling(false);
    }
  }, [callerPhone, preferredLanguage, speechSpeed, speakAiResponse, stopVoiceSession, handleAiSpeechCompleted]);

  const toggleCall = useCallback(async () => {
    if (isCalling || isConnecting) {
      await stopVoiceSession();
      return;
    }

    // 1. When user starts microphone voice agent, first check if signed in or not
    if (!checkIsSignedIn()) {
      setShowAuthModal(true);
      setVoiceStatus('⚠️ Sign-up / Sign-in required before starting the live microphone voice stream.');
      return;
    }

    await startVoiceSession(callerPhone);
  }, [isCalling, isConnecting, stopVoiceSession, startVoiceSession, callerPhone]);

  const handleAuthSuccess = useCallback(async (authenticatedPhone: string) => {
    setShowAuthModal(false);
    setIsSignedIn(true);
    setCallerPhone(authenticatedPhone);
    window.dispatchEvent(new Event('storage'));
    window.dispatchEvent(new CustomEvent('sahay_auth_changed'));
    setVoiceStatus('✓ Authentication verified! Starting live microphone voice stream...');
    // After sign in, start the microphone voice stream
    await startVoiceSession(authenticatedPhone);
  }, [startVoiceSession]);

  const handleSendVoiceChat = (customText?: string) => {
    const textToSend = (customText || voiceInputText).trim();
    if (!textToSend) return;

    isListeningNowRef.current = false;
    setIsListeningNow(false);
    if (recognitionRef.current) {
      try {
        recognitionRef.current.stop();
      } catch {}
    }

    setVoiceChatMessages((prev) => [
      ...prev,
      {
        id: `usr_${Date.now()}`,
        sender: 'user',
        text: textToSend,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        language: 'User Input'
      }
    ]);
    setVoiceInputText('');
    setIsAiThinking(true);
    setVoiceStatus('Processing user message & generating response...');

    // Detect language of the input text so agent responds in the same language
    const detectedLang = detectChatLanguage(textToSend);
    const langCodeMap: Record<string, string> = {
      'Odia': 'or-IN',
      'Hindi': 'hi-IN',
      'English': 'en-IN',
      'Santali': 'sat-IN',
      'Desia': 'des-IN',
      'Kui': 'kui-IN',
      'Kuvi': 'kuvi-IN'
    };
    const effectiveLang = (preferredLanguage && preferredLanguage !== 'auto')
      ? preferredLanguage
      : (langCodeMap[detectedLang] || 'or-IN');

    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        event: 'user_speech',
        text: textToSend,
        language: effectiveLang
      }));
    } else {
      api.sendChatMessage(textToSend, effectiveLang).then((res) => {
        setIsAiThinking(false);
        setVoiceChatMessages((prev) => [
          ...prev,
          {
            id: `agt_${Date.now()}`,
            sender: 'agent',
            text: res.text,
            risk: res.risk_level,
            timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
          }
        ]);
        if (res && res.audio_b64) {
          try {
            const audioBytes = Uint8Array.from(atob(res.audio_b64), (c) => c.charCodeAt(0));
            const audioBlob = new Blob([audioBytes], { type: 'audio/wav' });
            const audioUrl = URL.createObjectURL(audioBlob);
            const audio = new Audio(audioUrl);
            audio.playbackRate = speechSpeed;
            audio.onended = () => { handleAiSpeechCompleted(); };
            audio.play().catch(() => {
              speakAiResponse(res.text, res.language);
            });
          } catch {
            speakAiResponse(res.text, res.language);
          }
        } else {
          speakAiResponse(res.text, res.language);
        }
      }).catch(() => {
        setIsAiThinking(false);
      });
    }
  };

  const handleSendMessage = async (customText?: string) => {
    const textToSend = (customText || inputMessage).trim();
    if (!textToSend) return;
    syncCallerSession(callerPhone);

    const newMsgs = [...chatMessages, { sender: 'user' as const, text: textToSend }];
    setChatMessages(newMsgs);
    setInputMessage('');
    setIsTyping(true);

    const detectedLang = detectChatLanguage(textToSend);
    const langCodeMap: Record<string, string> = {
      'Odia': 'or-IN',
      'Hindi': 'hi-IN',
      'English': 'en-IN',
      'Santali': 'sat-IN',
      'Desia': 'des-IN',
      'Kui': 'kui-IN',
      'Kuvi': 'kuvi-IN'
    };
    const effectiveLang = (preferredLanguage && preferredLanguage !== 'auto')
      ? preferredLanguage
      : (langCodeMap[detectedLang] || 'or-IN');

    try {
      // In text guidance chat, only text response is needed (skip voice synthesis and audio playback)
      const res = await api.sendChatMessage(textToSend, effectiveLang, true);
      setChatMessages([
        ...newMsgs,
        {
          sender: 'agent',
          text: res.text,
          risk: res.risk_level
        }
      ]);
    } catch {
      setChatMessages([
        ...newMsgs,
        {
          sender: 'agent',
          text: 'ମୁଁ ଆପଣଙ୍କ କଥା ଶୁଣୁଛି। ଦୟାକରି ଶାନ୍ତ ରୁହନ୍ତୁ, ପୋଲିସ PCR 112 କୁ ସୂଚନା ଦିଆଯାଉଛି।'
        }
      ]);
    } finally {
      setIsTyping(false);
    }
  };

  const formatSeconds = (sec: number) => {
    const m = Math.floor(sec / 60);
    const s = sec % 60;
    return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
  };

  return (
    <>
      {/* Hero Section */}
      <section className="section" style={{ paddingTop: '74px', paddingBottom: 0 }}>
        <main className="hero-content" style={{ paddingTop: 0, minHeight: 'auto' }}>
          <div className="w-layout-blockcontainer container hero internal w-container">
            <div className="hero-section-content">
              <div className="hero-section-content-block internal bg-light-blue">
                <div className="wrapper max-width-640-mobile-480">
                  <h1 className="h1 margin-bottom-28">AI Voice &amp; Distress Triage Agent</h1>
                  <p className="regular-xl max-width-420">
                    Multilingual crisis response with spatial wilderness awareness, acoustic prosody analysis, and 1-click police dispatch.
                  </p>
                </div>
              </div>
              <div 
                className="hero-section-image internal" 
                style={{ 
                  backgroundImage: 'url("/images/ai_humanoid_support.png")',
                  backgroundPosition: '20% center'
                }}
              ></div>
            </div>
          </div>
        </main>
      </section>

      {/* Main Agent Interface */}
      <section className="section margin-top-64-tablet-48-mobile-24">
        <div className="w-layout-blockcontainer container w-container">
          {/* Mode Switcher */}
          <div style={{ display: 'flex', gap: '12px', marginBottom: '32px', borderBottom: '1px solid var(--grey-8)', paddingBottom: '16px' }}>
            <button
              type="button"
              className={`button ${activeTab === 'voice' ? 'primary' : 'secondary'} small w-button`}
              onClick={() => setActiveTab('voice')}
            >
              Real-Time Voice Stream
            </button>
            <button
              type="button"
              className={`button ${activeTab === 'chat' ? 'primary' : 'secondary'} small w-button`}
              onClick={() => setActiveTab('chat')}
            >
              Text Guidance Chat
            </button>
          </div>

          {activeTab === 'voice' ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '32px' }}>
              {/* 2-Column Voice Stream & Live AI Chat Box Grid */}
              <div className="w-layout-grid blocks-grid-2-tablet-1-mobile-1">
                {/* Column 1: Voice Stream Controls */}
                <div className="block padding-24-32 bg-grey-3" style={{ display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
                  <div>
                    <div className="wrapper width-100 margin-bottom-20">
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
                        <span className="regular-s color-grey-80" style={{ textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                          Acoustic Telephony Stream
                        </span>
                        <span style={{ display: 'inline-flex', alignItems: 'center', gap: '6px', fontSize: '12px', fontWeight: 600 }}>
                          <span className="pulse-dot" style={{ background: isCalling ? (isAiSpeakingOutLoud ? '#0284c7' : (isListeningNow ? '#10b981' : '#f59e0b')) : '#94a3b8' }}></span>
                          {isCalling ? (isAiSpeakingOutLoud ? 'AI Speaking' : (isListeningNow ? 'Listening Now' : (isAiThinking ? 'AI Thinking' : 'Live Connected'))) : 'Standby'}
                        </span>
                      </div>
                      <h3 className="h3 margin-bottom-16">
                        {isCalling ? 'Live Voice Session Active' : 'Helpline Standby'}
                      </h3>
                      <div className="line black margin-bottom-20"></div>
                      <p className="regular-m margin-bottom-20">
                        Direct real-time microphone stream to Sarvam Saaras STT, Gemini Flash LLM, and Sarvam Bulbul TTS with browser Web Speech backup.
                      </p>
                    </div>

                    {/* Animated Waveform Canvas */}
                    <canvas 
                      ref={canvasRef} 
                      width={600} 
                      height={90} 
                      className="waveform-canvas"
                    />

                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', width: '100%', marginBottom: '12px', flexWrap: 'wrap', gap: '8px' }}>
                      <div className="regular-m">
                        Duration: <strong>{formatSeconds(callDuration)}</strong>
                      </div>
                      <div className="regular-m">
                        Triage: <strong>{liveRiskLevel}</strong> (SVI: {(liveSvi * 100).toFixed(0)}%)
                      </div>
                      <div className="regular-m">
                        Language: <strong>{detectedLanguage}</strong>
                      </div>
                    </div>

                    <div style={{ marginBottom: '12px', color: '#4b5563', fontSize: '13.5px', minHeight: '20px', fontWeight: 500 }}>
                      {voiceStatus}
                    </div>

                    {/* VAD Debug indicator */}
                    <div style={{ marginBottom: '20px', padding: '10px 12px', borderRadius: '8px', background: '#f3f4f6', color: '#111827', fontSize: '11.5px', lineHeight: 1.5 }}>
                      <strong>VAD Diagnostics:</strong>{' '}
                      {vadDebug ? `RMS=${vadDebug.rms.toFixed(1)} | threshold=${vadDebug.threshold.toFixed(1)} | zcr=${vadDebug.zcr.toFixed(4)} | reason=${vadDebug.reason} | speaking=${vadDebug.is_speaking ? 'YES' : 'no'}` : 'Click Start to initialize microphone & VAD'}
                      {liveAcoustic.mean_pitch_f0 ? ` | Pitch: ${liveAcoustic.mean_pitch_f0.toFixed(0)}Hz` : ''}
                    </div>

                    {/* Voice Controls: Language & Speed */}
                    <div style={{ marginBottom: '16px', display: 'flex', flexDirection: 'column', gap: '10px' }}>
                      <div style={{ background: '#ffffff', padding: '10px 14px', borderRadius: '10px', border: '1px solid #e2e8f0', display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '12px' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                          <span style={{ fontSize: '15px' }}>🌐</span>
                          <div>
                            <div style={{ fontSize: '12.5px', fontWeight: 600, color: '#1e293b' }}>Spoken Voice Language:</div>
                            <div style={{ fontSize: '11px', color: '#64748b' }}>Gemini responds in the exact same language you speak</div>
                          </div>
                        </div>
                        <select
                          value={preferredLanguage}
                          onChange={(e) => handleLanguageChange(e.target.value)}
                          style={{
                            padding: '6px 10px',
                            borderRadius: '6px',
                            border: '1px solid #cbd5e1',
                            fontSize: '12px',
                            fontWeight: 600,
                            background: '#f8fafc',
                            color: '#0f172a',
                            cursor: 'pointer'
                          }}
                        >
                          <option value="auto">✨ Auto-Detect (Same as User)</option>
                          <option value="or-IN">🏛️ Odia (ଓଡ଼ିଆ)</option>
                          <option value="hi-IN">🇮🇳 Hindi (हिन्दी)</option>
                          <option value="en-IN">🌍 Indian English</option>
                          <option value="sat-IN">🏹 Santali (संताली / Ol Chiki)</option>
                          <option value="des-IN">🌾 Desia (Koraput Odia)</option>
                          <option value="kui-IN">🌿 Kui (Kandha / କୁଇ)</option>
                          <option value="kuvi-IN">🍃 Kuvi (କୁଭି)</option>
                        </select>
                      </div>

                      <div style={{ background: '#ffffff', padding: '10px 14px', borderRadius: '10px', border: '1px solid #e2e8f0', display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '12px' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                          <span style={{ fontSize: '15px' }}>⚡</span>
                          <div>
                            <div style={{ fontSize: '12.5px', fontWeight: 600, color: '#1e293b' }}>AI Speaking Speed:</div>
                            <div style={{ fontSize: '11px', color: '#64748b' }}>Accelerated audio playback for rapid, natural conversation</div>
                          </div>
                        </div>
                        <select
                          value={speechSpeed}
                          onChange={(e) => {
                            const spd = parseFloat(e.target.value);
                            setSpeechSpeed(spd);
                            if (audioPlaybackRef.current) {
                              audioPlaybackRef.current.playbackRate = spd;
                            }
                          }}
                          style={{
                            padding: '6px 10px',
                            borderRadius: '6px',
                            border: '1px solid #cbd5e1',
                            fontSize: '12px',
                            fontWeight: 600,
                            background: '#f8fafc',
                            color: '#0f172a',
                            cursor: 'pointer'
                          }}
                        >
                          <option value="1.0">1.0x Normal</option>
                          <option value="1.15">⚡ 1.15x Brisk</option>
                          <option value="1.25">🚀 1.25x Fast (Recommended)</option>
                          <option value="1.4">⚡⚡ 1.4x Super Fast</option>
                        </select>
                      </div>
                    </div>


                  </div>

                  {/* Caller ID input & User Dashboard Link */}
                  <div 
                    style={{ 
                      marginTop: '8px', 
                      marginBottom: '16px',
                      paddingTop: '12px', 
                      borderTop: '1px solid var(--grey-8)', 
                      display: 'flex', 
                      justifyContent: 'space-between', 
                      alignItems: 'center', 
                      width: '100%', 
                      flexWrap: 'wrap', 
                      gap: '10px' 
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
                      <span style={{ fontSize: '11px', background: '#d1fae5', color: '#065f46', padding: '3px 8px', borderRadius: '4px', fontWeight: 700, letterSpacing: '0.04em' }}>
                        CALLER LINE ID
                      </span>
                      <input 
                        type="text" 
                        value={callerPhone} 
                        onChange={(e) => {
                          const val = e.target.value;
                          setCallerPhone(val);
                          syncCallerSession(val);
                        }}
                        title="Caller phone number automatically linked to your grievances and recordings"
                        style={{ 
                          fontSize: '13px', 
                          fontWeight: 600, 
                          border: '1px solid #cbd5e1', 
                          padding: '4px 10px', 
                          borderRadius: '6px', 
                          width: '160px',
                          backgroundColor: '#ffffff'
                        }}
                      />
                      {isSignedIn ? (
                        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                          <span style={{ fontSize: '11px', color: '#059669', background: '#ecfdf5', border: '1px solid #a7f3d0', padding: '2px 7px', borderRadius: '4px', fontWeight: 700 }}>
                            ✓ Signed In
                          </span>
                          <button
                            type="button"
                            onClick={handleSignOut}
                            title="Sign out of current citizen session"
                            style={{ fontSize: '11.5px', color: '#64748b', background: 'transparent', border: 'none', cursor: 'pointer', textDecoration: 'underline' }}
                          >
                            (Sign Out)
                          </button>
                        </div>
                      ) : (
                        <span style={{ fontSize: '11px', color: '#b45309', background: '#fef3c7', border: '1px solid #fde68a', padding: '2px 7px', borderRadius: '4px', fontWeight: 600 }}>
                          🔒 Sign-Up Required
                        </span>
                      )}
                    </div>
                    <Link 
                      to="/user-dashboard" 
                      style={{ 
                        fontSize: '12.5px', 
                        fontWeight: 600, 
                        color: 'var(--black)', 
                        textDecoration: 'underline' 
                      }}
                    >
                      View My Grievances &amp; Recordings →
                    </Link>
                  </div>

                  {/* Main Call Action Buttons */}
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', width: '100%' }}>
                    <button
                      type="button"
                      onClick={toggleCall}
                      disabled={isConnecting}
                      className={`button ${isCalling ? 'secondary' : 'primary'} w-button`}
                      style={{ 
                        width: '100%', 
                        padding: '16px 20px', 
                        fontWeight: 700,
                        opacity: isConnecting ? 0.85 : 1,
                        cursor: isConnecting ? 'wait' : 'pointer',
                        transition: 'all 0.2s ease'
                      }}
                    >
                      {isConnecting
                        ? '⏳ Requesting Mic & Connecting...'
                        : (isCalling ? '🛑 End Voice Stream' : '🎙️ Start Microphone Voice Stream')}
                    </button>
                    <div style={{ fontSize: '13px', color: 'var(--grey-80)', textAlign: 'center', fontWeight: 500 }}>
                      Toll free helpline no. is "08047283123"
                    </div>
                  </div>
                </div>

                {/* Column 2: Live AI Voice Conversation Chat Box */}
                <div className="block padding-24-32 bg-grey-3" style={{ display: 'flex', flexDirection: 'column' }}>
                  <div className="voice-chat-box">
                    {/* Chat Box Header */}
                    <div className="voice-chat-header">
                      <div>
                        <div style={{ fontWeight: 700, fontSize: '15px', color: '#0f172a', display: 'flex', alignItems: 'center', gap: '8px' }}>
                          <span>💬 Live Voice Conversation Box</span>
                          <span className="pulse-dot" style={{ background: isCalling ? (isAiSpeakingOutLoud ? '#0284c7' : '#10b981') : '#94a3b8' }}></span>
                        </div>
                        <div style={{ fontSize: '11.5px', color: '#64748b' }}>
                          {isCalling
                            ? (isAiSpeakingOutLoud ? '🔊 AI is speaking the response aloud...' : isAiThinking ? '🧠 AI analyzing voice distress...' : '🎤 Listening to your microphone input...')
                            : 'Standby — click Start Microphone Voice Stream to talk'}
                        </div>
                      </div>
                      <button
                        type="button"
                        onClick={() => setVoiceChatMessages([])}
                        style={{ background: 'transparent', border: 'none', color: '#64748b', fontSize: '12px', cursor: 'pointer', textDecoration: 'underline' }}
                      >
                        Clear
                      </button>
                    </div>

                    {/* Messages Area */}
                    <div className="voice-chat-messages" ref={chatContainerRef}>
                      {voiceChatMessages.map((msg) => (
                        <div
                          key={msg.id}
                          className={msg.sender === 'user' ? 'voice-bubble-user' : 'voice-bubble-agent'}
                        >
                          <div className="voice-bubble-header">
                            <span style={{ color: msg.sender === 'user' ? '#93c5fd' : '#854d0e' }}>
                              {msg.sender === 'user' ? '🎤 You (Caller)' : '🤖 SAHAY Agent'}
                            </span>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                              <span style={{ color: msg.sender === 'user' ? '#94a3b8' : '#94a3b8', fontSize: '10.5px' }}>
                                {msg.timestamp}
                              </span>
                            </div>
                          </div>
                          <p style={{ margin: 0 }}>{msg.text}</p>
                          {msg.sender === 'agent' && (
                            <button
                              type="button"
                              className="voice-replay-btn"
                              onClick={() => handleReplayVoice(msg.text)}
                              title="Listen to this AI response again"
                            >
                              🔊 Listen Again
                            </button>
                          )}
                        </div>
                      ))}

                      {/* Live Interim Speech Recognition Bubble */}
                      {liveSpeechText && (
                        <div className="voice-interim-bubble">
                          🎤 Hearing: "{liveSpeechText}..."
                        </div>
                      )}

                      {/* AI Thinking Indicator */}
                      {isAiThinking && (
                        <div className="voice-bubble-agent" style={{ fontStyle: 'italic', color: '#854d0e' }}>
                          🧠 Formulating trauma-informed triage response...
                        </div>
                      )}
                    </div>

                    {/* Quick Input Bar inside Voice Chat Box */}
                    <form
                      onSubmit={(e) => { e.preventDefault(); handleSendVoiceChat(); }}
                      className="voice-input-bar"
                    >
                      <input
                        type="text"
                        placeholder="Speak into microphone, or type your message here..."
                        value={voiceInputText}
                        onChange={(e) => setVoiceInputText(e.target.value)}
                        style={{ flex: 1, padding: '10px 14px', borderRadius: '6px', border: '1px solid #cbd5e1', fontSize: '13.5px', outline: 'none' }}
                      />
                      <button
                        type="submit"
                        className="button primary small w-button"
                        style={{ padding: '0 20px', borderRadius: '6px' }}
                      >
                        Send
                      </button>
                    </form>
                  </div>
                </div>
              </div>

            </div>
          ) : (
            /* Text Guidance Chat */
            <div className="block padding-24-32 bg-grey-3" style={{ width: '100%' }}>
              <div className="wrapper width-100 margin-bottom-24">
                <div className="regular-s color-grey-80 margin-bottom-12" style={{ textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                  Interactive Distress Guidance
                </div>
                <h3 className="h3 margin-bottom-16">Trauma-Informed Text Chat</h3>
                <div className="line black margin-bottom-20"></div>
                <p className="regular-m margin-bottom-16">
                  Test the agent's spatial awareness, Santali and Odia dialect normalization, and non-hallucinatory guidance.
                </p>

                {/* Scenario Presets */}
                <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', marginBottom: '24px' }}>
                  <button
                    type="button"
                    onClick={() => handleSendMessage("mate maribaku godauchanti mu ebe jangala re nuchiki achi")}
                    className="button secondary small w-button"
                    style={{ fontSize: '12px', padding: '6px 12px' }}
                  >
                    🏛️ Forest Pursuit (Odia)
                  </button>
                  <button
                    type="button"
                    onClick={() => handleSendMessage("Mujhe emergency help chahiye, yahan ladai ho rahi hai aur dhamki mil rahi hai.")}
                    className="button secondary small w-button"
                    style={{ fontSize: '12px', padding: '6px 12px' }}
                  >
                    🇮🇳 Emergency Help (Hindi)
                  </button>
                  <button
                    type="button"
                    onClick={() => handleSendMessage("I need urgent legal assistance regarding threat, violence, and harassment.")}
                    className="button secondary small w-button"
                    style={{ fontSize: '12px', padding: '6px 12px' }}
                  >
                    🌍 Legal Aid (English)
                  </button>
                  <button
                    type="button"
                    onClick={() => handleSendMessage("bir re ukanakana panjayedina botor ge aikawkana banchaoing pe")}
                    className="button secondary small w-button"
                    style={{ fontSize: '12px', padding: '6px 12px' }}
                  >
                    🏹 Forest Threat (Santali)
                  </button>
                  <button
                    type="button"
                    onClick={() => handleSendMessage("mor pache padila godauche bhay laguche dada banchao")}
                    className="button secondary small w-button"
                    style={{ fontSize: '12px', padding: '6px 12px' }}
                  >
                    🌾 Pursuit Crisis (Desia)
                  </button>
                  <button
                    type="button"
                    onClick={() => handleSendMessage("aanu bana re huji aane gahi laguri dohpa banchao")}
                    className="button secondary small w-button"
                    style={{ fontSize: '12px', padding: '6px 12px' }}
                  >
                    🌿 Forest Distress (Kui)
                  </button>
                  <button
                    type="button"
                    onClick={() => handleSendMessage("aane gahi laguri mera bhanguchhanti kaan banchao")}
                    className="button secondary small w-button"
                    style={{ fontSize: '12px', padding: '6px 12px' }}
                  >
                    🍃 Village Attack (Kuvi)
                  </button>
                </div>
              </div>

              {/* Chat Log Window */}
              <div style={{ minHeight: '320px', maxHeight: '480px', overflowY: 'auto', width: '100%', paddingRight: '8px', marginBottom: '24px' }}>
                {chatMessages.map((msg, idx) => (
                  <div key={idx} className={msg.sender === 'user' ? 'chat-bubble-user' : 'chat-bubble-agent'}>
                    <p style={{ margin: 0 }}>{msg.text}</p>
                  </div>
                ))}
                {isTyping && (
                  <div className="chat-bubble-agent" style={{ fontStyle: 'italic' }}>
                    Agent is formulating trauma response...
                  </div>
                )}
              </div>

              {/* Message Input */}
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px', width: '100%', marginBottom: '12px' }}>
                <div style={{ fontSize: '12px', fontWeight: 700, letterSpacing: '0.04em', textTransform: 'uppercase', color: '#4b5563' }}>
                  Detected language: <span style={{ color: '#0f172a' }}>{detectedChatLanguage}</span>
                </div>
              </div>
              <form 
                onSubmit={(e) => { e.preventDefault(); handleSendMessage(); }}
                style={{ display: 'flex', gap: '12px', width: '100%' }}
              >
                <input
                  className="form-input w-input"
                  placeholder="Type your emergency or query in Odia, Santali, Kui, Kuvi, Hindi, or English..."
                  type="text"
                  value={inputMessage}
                  onChange={(e) => setInputMessage(e.target.value)}
                  style={{ marginBottom: 0 }}
                />
                <input
                  type="submit"
                  className="button primary small w-button"
                  value="Send"
                  style={{ padding: '0 28px' }}
                />
              </form>
            </div>
          )}
        </div>
      </section>

      {/* Sign-up / Sign-in required prompt before voice streaming */}
      <VoiceAuthModal
        isOpen={showAuthModal}
        onClose={() => setShowAuthModal(false)}
        onAuthSuccess={handleAuthSuccess}
        defaultPhone={callerPhone}
      />
    </>
  );
};
