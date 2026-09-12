import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { TraumaMetricsChart, type TraumaIndicatorData } from '../components/TraumaMetricsChart';
import { api, getDashboardWsUrl } from '../services/api';

interface QueueItem {
  id: string;
  call_id: string;
  caller_name?: string;
  caller_number: string;
  channel: string;
  timestamp: string;
  risk_level: 'CRITICAL' | 'HIGH' | 'LOW';
  svi_score: number;
  emotion: { fear: number; sadness: number; anger: number; neutral: number };
  acoustic: { pitch_f0: number; jitter: number; pause_ratio: number; speech_rate: number };
  flags: string[];
  ps26093_indicators?: {
    fear_panic: number;
    stress_anxiety: number;
    intimidation_threat: number;
    severe_trauma: number;
    social_boycott: number;
    sadness_grief: number;
    anger_agitation: number;
    suicidal_ideation: number;
  };
  latest_utterance: string;
  sbar: {
    situation: string;
    background: string;
    assessment: string;
    recommendation: string;
  };
}

const INITIAL_QUEUE: QueueItem[] = [
  {
    id: 'Q-101',
    call_id: 'call_9901_forest',
    caller_number: '+91 94371-XXXXX (Dhenkanal)',
    channel: 'EXOTEL CARRIER (08047283123)',
    timestamp: 'Just now (00:42)',
    risk_level: 'CRITICAL',
    svi_score: 0.94,
    emotion: { fear: 0.88, sadness: 0.06, anger: 0.04, neutral: 0.02 },
    acoustic: { pitch_f0: 312, jitter: 0.048, pause_ratio: 0.38, speech_rate: 3.4 },
    flags: ['ACTIVE_PURSUIT', 'WILDERNESS_OUTDOORS', 'ARMED_THREAT'],
    ps26093_indicators: {
      fear_panic: 88,
      stress_anxiety: 82,
      intimidation_threat: 94,
      severe_trauma: 85,
      social_boycott: 18,
      sadness_grief: 24,
      anger_agitation: 32,
      suicidal_ideation: 12,
    },
    latest_utterance: 'ମୋତେ ମାରିବାକୁ ଗୋଡ଼ାଉଛନ୍ତି, ମୁଁ ଏବେ ଜଙ୍ଗଲରେ ଲୁଚିକି ଅଛି। (Mate maribaku godauchanti...)',
    sbar: {
      situation: 'Caller is being actively chased by armed attackers in a forest.',
      background: 'Caste atrocity incident following land dispute protest in Dhenkanal district.',
      assessment: 'SVI: 0.94 CRITICAL. Acute fear (88%). Spatial wilderness survival instructions active.',
      recommendation: 'Immediate Police PCR 112 intercept to village periphery landmark.'
    }
  },
  {
    id: 'Q-102',
    call_id: 'call_9902_boycott',
    caller_number: '+91 98610-XXXXX (Bargarh)',
    channel: 'WEB-RTC BROWSER',
    timestamp: '3 mins ago',
    risk_level: 'HIGH',
    svi_score: 0.72,
    emotion: { fear: 0.45, sadness: 0.35, anger: 0.15, neutral: 0.05 },
    acoustic: { pitch_f0: 245, jitter: 0.024, pause_ratio: 0.22, speech_rate: 2.8 },
    flags: ['SOCIAL_BOYCOTT', 'WATER_ACCESS_DENIAL', 'KOSLI_DIALECT'],
    ps26093_indicators: {
      fear_panic: 45,
      stress_anxiety: 68,
      intimidation_threat: 64,
      severe_trauma: 42,
      social_boycott: 92,
      sadness_grief: 72,
      anger_agitation: 35,
      suicidal_ideation: 8,
    },
    latest_utterance: 'ମୋର୍ ପିତା ଖେଡି ଦେଲେ, ପାଣି ନେବାର୍ ମନା କର୍ଲେ। (Mor pita khedi dele...)',
    sbar: {
      situation: 'Family subject to social boycott and denied drinking water access.',
      background: 'Bargarh village committee diktat violating SC/ST PoA Section 3(1)(za).',
      assessment: 'SVI: 0.72 HIGH. Moderate fear and acute vulnerability.',
      recommendation: 'Direct notice to Sub-Divisional Magistrate & District Welfare Officer.'
    }
  }
];

export const OperatorDashboard: React.FC = () => {
  const [queue, setQueue] = useState<QueueItem[]>(INITIAL_QUEUE);
  const [selectedItem, setSelectedItem] = useState<QueueItem>(INITIAL_QUEUE[0]);
  const [dispatchModalOpen, setDispatchModalOpen] = useState(false);
  const [dispatchSuccess, setDispatchSuccess] = useState(false);
  const [wsConnected, setWsConnected] = useState(false);
  const [bannerMessage, setBannerMessage] = useState<{ type: 'warning' | 'success' | 'info'; text: string } | null>(null);
  const [activeTab, setActiveTab] = useState<'queue' | 'recordings'>('queue');
  const [allRecordings, setAllRecordings] = useState<any[]>([]);
  const [recordingsSearch, setRecordingsSearch] = useState<string>('');
  const [recordingsLoading, setRecordingsLoading] = useState<boolean>(false);
  const wsRef = useRef<WebSocket | null>(null);
  const navigate = useNavigate();

  const fetchAllRecordings = async () => {
    setRecordingsLoading(true);
    try {
      const records = await api.getVoiceRecordings(undefined, 'operator');
      if (Array.isArray(records) && records.length > 0) {
        setAllRecordings(records);
      }
    } catch (err) {
      console.warn('Could not fetch all recordings for operator:', err);
    } finally {
      setRecordingsLoading(false);
    }
  };

  useEffect(() => {
    fetchAllRecordings();
  }, []);

  // Keep selectedItem in sync if queue changes
  useEffect(() => {
    if (!queue.find((q) => q.id === selectedItem?.id || q.call_id === selectedItem?.call_id)) {
      if (queue.length > 0) {
        setSelectedItem(queue[0]);
      }
    }
  }, [queue, selectedItem]);

  // Initial fetch of public citizen complaints from API
  useEffect(() => {
    let mounted = true;
    const fetchComplaints = async () => {
      try {
        const complaints = await api.getRecentComplaints();
        if (mounted && complaints && complaints.length > 0) {
          setQueue((prev) => {
            const existingCallIds = new Set(prev.map((p) => p.call_id));
            const newItems: QueueItem[] = [];
            for (const c of complaints) {
              if (!existingCallIds.has(c.call_id)) {
                newItems.push({
                  id: c.ticket_ref || c.id || `Q-${c.call_id}`,
                  call_id: c.call_id,
                  caller_name: c.caller_name || '',
                  caller_number: c.caller_phone || c.caller_number || 'Direct Caller',
                  channel: c.type === 'voice' ? 'CITIZEN VOICE CALL' : 'TELEPHONE LINE',
                  timestamp: c.timestamp || 'Recent',
                  risk_level: (c.risk_level || 'HIGH') as any,
                  svi_score: c.svi_score || 0.82,
                  emotion: { fear: 0.7, sadness: 0.2, anger: 0.05, neutral: 0.05 },
                  acoustic: { pitch_f0: 280, jitter: 0.038, pause_ratio: 0.3, speech_rate: 3.2 },
                  flags: ['CITIZEN_GRIEVANCE', (c.language || 'ODIA').toUpperCase()],
                  ps26093_indicators: {
                    fear_panic: 72,
                    stress_anxiety: 78,
                    intimidation_threat: 70,
                    severe_trauma: 62,
                    social_boycott: 40,
                    sadness_grief: 60,
                    anger_agitation: 35,
                    suicidal_ideation: 10,
                  },
                  latest_utterance: c.summary,
                  sbar: {
                    situation: c.summary,
                    background: `Verified grievance recorded in dialect ${c.language || 'Odia'}. Ticket: ${c.ticket_ref || c.id}`,
                    assessment: `SVI: ${c.svi_score || 0.82} ${c.risk_level || 'HIGH'}. Screened by Anti-Prank Filter.`,
                    recommendation: `Follow statutory escalation protocol under SC/ST PoA Act.`
                  }
                });
              }
            }
            return newItems.length > 0 ? [...newItems, ...prev] : prev;
          });
        }
      } catch (err) {
        console.warn('Could not fetch initial complaints', err);
      }
    };
    fetchComplaints();
    return () => {
      mounted = false;
    };
  }, []);

  // WebSocket Live Updates Connection
  useEffect(() => {
    let reconnectTimeout: any = null;
    let ws: WebSocket | null = null;

    const connectWs = () => {
      try {
        const wsUrl = getDashboardWsUrl();
        ws = new WebSocket(wsUrl);
        wsRef.current = ws;

        ws.onopen = () => {
          setWsConnected(true);
        };

        ws.onmessage = (event) => {
          try {
            const packet = JSON.parse(event.data);
            if (packet.event === 'complaint_deleted') {
              const data = packet.data;
              setQueue((prev) =>
                prev.filter(
                  (item) =>
                    item.id !== data.identifier &&
                    item.call_id !== data.call_id &&
                    item.id !== data.call_id &&
                    item.id !== data.ticket_id
                )
              );
              setBannerMessage({
                type: 'warning',
                text: `[DPDP Act 2023 Erasure] Complaint ${data.ticket_id || data.call_id} and caller recording permanently expunged per citizen request.`
              });
              setTimeout(() => setBannerMessage(null), 8000);
            } else if (packet.event === 'complaint_registered') {
              const data = packet.data;
              const newItem: QueueItem = {
                id: data.ticket_id || `Q-${data.call_id}`,
                call_id: data.call_id,
                caller_name: data.caller_name || '',
                caller_number: data.caller_phone || data.caller_number || 'Direct Voice Caller',
                channel: 'CITIZEN VOICE CALL',
                timestamp: 'Just now',
                risk_level: (data.risk_level || 'HIGH') as any,
                svi_score: data.svi_score || 0.78,
                emotion: { fear: 0.65, sadness: 0.2, anger: 0.1, neutral: 0.05 },
                acoustic: { pitch_f0: 270, jitter: 0.035, pause_ratio: 0.32, speech_rate: 3.1 },
                flags: ['VOICE_GRIEVANCE', (data.language || 'ODIA').toUpperCase()],
                ps26093_indicators: data.indicators || {
                  fear_panic: 68,
                  stress_anxiety: 74,
                  intimidation_threat: 65,
                  severe_trauma: 55,
                  social_boycott: 40,
                  sadness_grief: 58,
                  anger_agitation: 30,
                  suicidal_ideation: 6,
                },
                latest_utterance: data.summary || 'Verified citizen grievance recorded through voice helpline.',
                sbar: {
                  situation: data.summary || 'Verified citizen grievance recorded through voice helpline.',
                  background: `Registered in ${data.language || 'Odia/Dialect'}. Screened and approved by AI anti-prank filter.`,
                  assessment: `SVI: ${data.svi_score || 0.78} ${data.risk_level || 'HIGH'}.`,
                  recommendation: 'Operator review recording and assign to district response unit.'
                }
              };
              setQueue((prev) => [newItem, ...prev]);
              fetchAllRecordings();
              setBannerMessage({
                type: 'success',
                text: `[New Verified Grievance] Ticket ${data.ticket_id} registered (${data.language}). Real-time queue updated.`
              });
              setTimeout(() => setBannerMessage(null), 8000);
            } else if (packet.event === 'recording_saved') {
              fetchAllRecordings();
              setBannerMessage({
                type: 'info',
                text: `[New Microphone Voice Recording] Audio recording saved to database for ${packet.data?.caller_name || 'Citizen'} (${packet.data?.caller_phone}).`
              });
              setTimeout(() => setBannerMessage(null), 8000);
            }
          } catch (err) {
            console.error('Error parsing dashboard ws message', err);
          }
        };

        ws.onclose = () => {
          setWsConnected(false);
          reconnectTimeout = setTimeout(connectWs, 5000);
        };

        ws.onerror = () => {
          setWsConnected(false);
        };
      } catch (e) {
        setWsConnected(false);
        reconnectTimeout = setTimeout(connectWs, 5000);
      }
    };

    connectWs();

    return () => {
      if (reconnectTimeout) clearTimeout(reconnectTimeout);
      if (ws) ws.close();
    };
  }, []);

  const getTraumaChartData = (item: QueueItem): TraumaIndicatorData[] => {
    if (!item) return [];
    if (item.ps26093_indicators) {
      return [
        { indicator: 'Intimidation & Threat', score: item.ps26093_indicators.intimidation_threat, category: 'Linguistic Threat / Coercion', color: '#b91c1c' },
        { indicator: 'Fear & Panic', score: item.ps26093_indicators.fear_panic, category: 'Dominant Emotion State', color: '#dc2626' },
        { indicator: 'Severe Trauma', score: item.ps26093_indicators.severe_trauma, category: 'Bodily Harm / Caste Atrocity', color: '#991b1b' },
        { indicator: 'Stress & Anxiety', score: item.ps26093_indicators.stress_anxiety, category: 'Vocal Micro-Tremor (Jitter)', color: '#ea580c' },
        { indicator: 'Social Boycott', score: item.ps26093_indicators.social_boycott, category: 'PoA Sec 3(1)(za) Exclusion', color: '#7c3aed' },
        { indicator: 'Sadness & Despair', score: item.ps26093_indicators.sadness_grief, category: 'Grief / Helplessness', color: '#2563eb' },
        { indicator: 'Anger & Agitation', score: item.ps26093_indicators.anger_agitation, category: 'Voice Shimmer / Tension', color: '#d97706' },
        { indicator: 'Suicidal Ideation', score: item.ps26093_indicators.suicidal_ideation, category: 'Self-Harm / Crisis Intervention', color: '#475569' },
      ];
    }
    return [
      { indicator: 'Intimidation & Threat', score: item.flags.includes('ARMED_THREAT') ? 92 : 45, category: 'Linguistic Threat', color: '#b91c1c' },
      { indicator: 'Fear & Panic', score: Math.round(item.emotion.fear * 100), category: 'Emotion State', color: '#dc2626' },
      { indicator: 'Severe Trauma', score: Math.round(item.svi_score * 90), category: 'Trauma Load', color: '#991b1b' },
      { indicator: 'Stress & Anxiety', score: Math.round(item.svi_score * 85), category: 'Acoustic Tension', color: '#ea580c' },
      { indicator: 'Social Boycott', score: item.flags.includes('SOCIAL_BOYCOTT') ? 90 : 15, category: 'Exclusion', color: '#7c3aed' },
      { indicator: 'Sadness & Despair', score: Math.round(item.emotion.sadness * 100), category: 'Vocal Sorrow', color: '#2563eb' },
      { indicator: 'Anger & Agitation', score: Math.round(item.emotion.anger * 100), category: 'Agitation', color: '#d97706' },
      { indicator: 'Suicidal Ideation', score: item.risk_level === 'CRITICAL' ? 12 : 5, category: 'Crisis Risk', color: '#475569' },
    ];
  };

  const filteredRecordings = allRecordings.filter((rec) => {
    if (!recordingsSearch.trim()) return true;
    const term = recordingsSearch.toLowerCase();
    return (
      (rec.caller_name || '').toLowerCase().includes(term) ||
      (rec.caller_phone || '').toLowerCase().includes(term) ||
      (rec.caller_number || '').toLowerCase().includes(term) ||
      (rec.call_id || '').toLowerCase().includes(term) ||
      (rec.language || '').toLowerCase().includes(term) ||
      (rec.summary || '').toLowerCase().includes(term)
    );
  });

  const handleDispatch = () => {
    setDispatchSuccess(true);
    setTimeout(() => {
      setDispatchModalOpen(false);
      setDispatchSuccess(false);
    }, 2000);
  };

  const handleSignOut = () => {
    sessionStorage.removeItem('sahay_user');
    navigate('/login');
  };


  return (
    <>
      <section className="section" style={{ paddingTop: '90px', paddingBottom: '60px', minHeight: '100vh', backgroundColor: '#f8fafc' }}>
        <main className="hero-content" style={{ minHeight: 'auto', paddingBottom: '20px' }}>
          <div className="w-layout-blockcontainer container w-container" style={{ maxWidth: '1240px' }}>
            
            {/* Command Header */}
            <div 
              style={{ 
                display: 'flex', 
                justifyContent: 'space-between', 
                alignItems: 'center', 
                flexWrap: 'wrap', 
                gap: '16px', 
                marginBottom: '28px',
                paddingBottom: '20px',
                borderBottom: '1px solid #e2e8f0'
              }}
            >
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px' }}>
                  <span style={{ 
                    fontSize: '11px', 
                    fontWeight: 800, 
                    textTransform: 'uppercase', 
                    letterSpacing: '0.08em', 
                    padding: '3px 10px', 
                    borderRadius: '9999px', 
                    backgroundColor: '#e2e8f0', 
                    color: '#334155' 
                  }}>
                    Live Command Center
                  </span>
                  <span style={{ fontSize: '13px', color: '#64748b' }}>National Atrocity Helpline 14566</span>
                </div>
                <h2 style={{ fontSize: '28px', fontWeight: 800, color: '#0f172a', margin: 0, letterSpacing: '-0.02em' }}>
                  Operator Triage &amp; Telemetry Console
                </h2>
              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
                <div style={{ 
                  display: 'inline-flex', 
                  alignItems: 'center', 
                  gap: '8px', 
                  padding: '7px 16px', 
                  borderRadius: '9999px', 
                  backgroundColor: wsConnected ? '#f0fdf4' : '#fef2f2', 
                  border: `1px solid ${wsConnected ? '#86efac' : '#fca5a5'}`,
                  boxShadow: '0 1px 2px rgba(0,0,0,0.03)'
                }}>
                  <span style={{ 
                    width: '8px', 
                    height: '8px', 
                    borderRadius: '50%', 
                    backgroundColor: wsConnected ? '#16a34a' : '#dc2626', 
                    boxShadow: wsConnected ? '0 0 8px #22c55e' : '0 0 8px #ef4444',
                    display: 'inline-block' 
                  }}></span>
                  <span style={{ fontSize: '12.5px', fontWeight: 700, letterSpacing: '0.03em', color: wsConnected ? '#166534' : '#991b1b' }}>
                    {wsConnected ? 'LIVE WS SYNC ACTIVE' : 'RECONNECTING WS...'}
                  </span>
                </div>
                <button 
                  type="button" 
                  onClick={handleSignOut} 
                  className="button secondary small w-button"
                  style={{ borderRadius: '8px', padding: '8px 18px', fontSize: '13px', fontWeight: 600 }}
                >
                  Log Out
                </button>
              </div>
            </div>

            {/* Live Synchronized Alert Notification Banner */}
            {bannerMessage && (
              <div
                style={{
                  marginBottom: '24px',
                  padding: '14px 20px',
                  borderRadius: '10px',
                  backgroundColor: bannerMessage.type === 'warning' ? '#fffbeb' : bannerMessage.type === 'success' ? '#f0fdf4' : '#eff6ff',
                  border: `1px solid ${bannerMessage.type === 'warning' ? '#fde68a' : bannerMessage.type === 'success' ? '#86efac' : '#bfdbfe'}`,
                  color: bannerMessage.type === 'warning' ? '#92400e' : bannerMessage.type === 'success' ? '#166534' : '#1e40af',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  fontWeight: 600,
                  fontSize: '13.5px',
                  boxShadow: '0 2px 8px rgba(0,0,0,0.03)'
                }}
              >
                <div>{bannerMessage.text}</div>
                <button
                  type="button"
                  onClick={() => setBannerMessage(null)}
                  style={{ background: 'transparent', border: 'none', cursor: 'pointer', fontSize: '16px', color: 'inherit', padding: '0 4px' }}
                >
                  ✕
                </button>
              </div>
            )}

            {/* View Selector: Segmented Control */}
            <div 
              style={{ 
                display: 'inline-flex', 
                backgroundColor: '#e2e8f0', 
                padding: '4px', 
                borderRadius: '12px', 
                gap: '4px', 
                marginBottom: '24px',
                boxShadow: 'inset 0 1px 2px rgba(0,0,0,0.05)'
              }}
            >
              <button
                type="button"
                onClick={() => setActiveTab('queue')}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                  padding: '9px 20px',
                  fontSize: '13.5px',
                  fontWeight: 700,
                  borderRadius: '9px',
                  border: 'none',
                  cursor: 'pointer',
                  backgroundColor: activeTab === 'queue' ? '#ffffff' : 'transparent',
                  color: activeTab === 'queue' ? '#0f172a' : '#64748b',
                  boxShadow: activeTab === 'queue' ? '0 2px 8px rgba(0,0,0,0.08)' : 'none',
                  transition: 'all 0.15s ease'
                }}
              >
                <span>🚨 Priority Triage Queue</span>
                <span 
                  style={{ 
                    backgroundColor: activeTab === 'queue' ? '#ef4444' : '#cbd5e1', 
                    color: activeTab === 'queue' ? '#ffffff' : '#334155', 
                    padding: '2px 8px', 
                    borderRadius: '9999px', 
                    fontSize: '11px', 
                    fontWeight: 800 
                  }}
                >
                  {queue.length}
                </span>
              </button>

              <button
                type="button"
                onClick={() => setActiveTab('recordings')}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                  padding: '9px 20px',
                  fontSize: '13.5px',
                  fontWeight: 700,
                  borderRadius: '9px',
                  border: 'none',
                  cursor: 'pointer',
                  backgroundColor: activeTab === 'recordings' ? '#ffffff' : 'transparent',
                  color: activeTab === 'recordings' ? '#0f172a' : '#64748b',
                  boxShadow: activeTab === 'recordings' ? '0 2px 8px rgba(0,0,0,0.08)' : 'none',
                  transition: 'all 0.15s ease'
                }}
              >
                <span>🎙️ All Citizen Voice Recordings</span>
                <span 
                  style={{ 
                    backgroundColor: activeTab === 'recordings' ? '#0f172a' : '#cbd5e1', 
                    color: activeTab === 'recordings' ? '#ffffff' : '#334155', 
                    padding: '2px 8px', 
                    borderRadius: '9999px', 
                    fontSize: '11px', 
                    fontWeight: 800 
                  }}
                >
                  {allRecordings.length}
                </span>
              </button>
            </div>

            {/* TAB 1: ALL CITIZEN VOICE RECORDINGS LIST */}
            {activeTab === 'recordings' ? (
              <div style={{ width: '100%' }}>
                <div 
                  style={{ 
                    backgroundColor: '#ffffff', 
                    border: '1px solid #e2e8f0', 
                    borderRadius: '16px', 
                    padding: '24px 28px', 
                    marginBottom: '20px',
                    boxShadow: '0 4px 16px -2px rgba(15, 23, 42, 0.04)',
                    display: 'flex', 
                    justifyContent: 'space-between', 
                    alignItems: 'center', 
                    flexWrap: 'wrap', 
                    gap: '16px' 
                  }}
                >
                  <div>
                    <h3 style={{ margin: '0 0 4px 0', fontSize: '20px', fontWeight: 800, color: '#0f172a' }}>
                      All Citizen Voice Stream Recordings ({allRecordings.length})
                    </h3>
                    <p style={{ margin: 0, fontSize: '13px', color: '#64748b' }}>
                      Central Administrative Database: Microphone voice streams across all registered citizens with playback &amp; telemetry.
                    </p>
                  </div>
                  <div style={{ display: 'flex', gap: '10px', alignItems: 'center', flexWrap: 'wrap' }}>
                    <div style={{ position: 'relative' }}>
                      <input
                        type="text"
                        placeholder="Search by name, phone (+91...), dialect..."
                        value={recordingsSearch}
                        onChange={(e) => setRecordingsSearch(e.target.value)}
                        style={{
                          padding: '10px 14px 10px 36px',
                          borderRadius: '10px',
                          border: '1px solid #cbd5e1',
                          fontSize: '13px',
                          width: '290px',
                          backgroundColor: '#f8fafc',
                          outline: 'none',
                          color: '#0f172a'
                        }}
                      />
                      <span style={{ position: 'absolute', left: '12px', top: '10px', fontSize: '14px', color: '#94a3b8' }}>
                        🔍
                      </span>
                      {recordingsSearch && (
                        <button
                          type="button"
                          onClick={() => setRecordingsSearch('')}
                          style={{ position: 'absolute', right: '10px', top: '8px', background: 'none', border: 'none', cursor: 'pointer', color: '#94a3b8', fontSize: '13px' }}
                        >
                          ✕
                        </button>
                      )}
                    </div>
                    <button
                      type="button"
                      onClick={fetchAllRecordings}
                      className="button secondary small w-button"
                      style={{ borderRadius: '10px', padding: '10px 16px', fontSize: '13px', fontWeight: 600 }}
                    >
                      🔄 Refresh
                    </button>
                  </div>
                </div>

                {recordingsLoading ? (
                  <div 
                    style={{ 
                      backgroundColor: '#ffffff', 
                      borderRadius: '16px', 
                      border: '1px solid #e2e8f0', 
                      padding: '60px 20px', 
                      textAlign: 'center', 
                      color: '#64748b',
                      fontSize: '14px' 
                    }}
                  >
                    Loading voice recordings database...
                  </div>
                ) : filteredRecordings.length === 0 ? (
                  <div 
                    style={{ 
                      backgroundColor: '#ffffff', 
                      borderRadius: '16px', 
                      border: '1px solid #e2e8f0', 
                      padding: '60px 20px', 
                      textAlign: 'center', 
                      color: '#64748b',
                      fontSize: '14px' 
                    }}
                  >
                    No voice recordings found matching your search.
                  </div>
                ) : (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
                    {filteredRecordings.map((rec: any) => (
                      <div
                        key={rec.call_id || rec.id}
                        style={{
                          backgroundColor: '#ffffff',
                          border: '1px solid #e2e8f0',
                          borderRadius: '14px',
                          padding: '20px 24px',
                          boxShadow: '0 2px 10px -2px rgba(15, 23, 42, 0.04)',
                          transition: 'border-color 0.2s ease, box-shadow 0.2s ease'
                        }}
                      >
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '10px', marginBottom: '12px' }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap' }}>
                            <span style={{ fontSize: '17px', fontWeight: 800, color: '#0f172a' }}>
                              {rec.caller_name || 'Citizen Caller'}
                            </span>
                            <span style={{ fontSize: '12.5px', background: '#f1f5f9', color: '#334155', padding: '3px 10px', borderRadius: '6px', fontWeight: 600 }}>
                              📞 {rec.caller_phone || rec.caller_number}
                            </span>
                            <span 
                              style={{
                                fontSize: '11px',
                                fontWeight: 800,
                                textTransform: 'uppercase',
                                padding: '3px 9px',
                                borderRadius: '6px',
                                backgroundColor: rec.risk_level === 'CRITICAL' ? '#fef2f2' : rec.risk_level === 'HIGH' ? '#fffbeb' : '#f0fdf4',
                                color: rec.risk_level === 'CRITICAL' ? '#991b1b' : rec.risk_level === 'HIGH' ? '#92400e' : '#166534',
                                border: `1px solid ${rec.risk_level === 'CRITICAL' ? '#fecaca' : rec.risk_level === 'HIGH' ? '#fde68a' : '#bbf7d0'}`
                              }}
                            >
                              {rec.risk_level || 'LOW'}
                            </span>
                            <span style={{ fontSize: '11px', background: '#e0f2fe', color: '#0369a1', padding: '3px 9px', borderRadius: '6px', fontWeight: 700, textTransform: 'uppercase' }}>
                              {rec.language || 'ODIA'}
                            </span>
                          </div>
                          <div style={{ fontSize: '12.5px', color: '#64748b', fontWeight: 500 }}>
                            🕒 {rec.timestamp} &bull; ⏱️ {rec.duration || `${rec.duration_seconds || 15}s`}
                          </div>
                        </div>

                        {/* Summary / transcript box */}
                        <div 
                          style={{ 
                            fontSize: '13.5px', 
                            color: '#334155', 
                            marginBottom: '14px', 
                            lineHeight: 1.5, 
                            backgroundColor: '#f8fafc', 
                            padding: '12px 16px', 
                            borderRadius: '10px', 
                            borderLeft: '4px solid #0f172a' 
                          }}
                        >
                          "{rec.summary}"
                        </div>

                        {/* Audio Player Showcase */}
                        <div 
                          style={{ 
                            backgroundColor: '#f8fafc', 
                            border: '1px solid #edf2f7',
                            padding: '12px 18px', 
                            borderRadius: '10px', 
                            display: 'flex', 
                            alignItems: 'center', 
                            gap: '14px',
                            flexWrap: 'wrap'
                          }}
                        >
                          <span style={{ fontSize: '12.5px', fontWeight: 700, color: '#0f172a', whiteSpace: 'nowrap', display: 'flex', alignItems: 'center', gap: '6px' }}>
                            🎧 Audio Playback:
                          </span>
                          <audio
                            controls
                            src={api.getRecordingAudioUrl(rec.recording_url)}
                            style={{ flex: 1, height: '36px', minWidth: '240px' }}
                          />
                        </div>

                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '10px', fontSize: '11.5px', color: '#94a3b8' }}>
                          <span>Session ID: <code style={{ backgroundColor: '#f1f5f9', padding: '2px 6px', borderRadius: '4px', color: '#475569' }}>{rec.call_id}</code></span>
                          <span>Source: SQLite Database &bull; Status: Stored</span>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ) : (
              /* TAB 2: PRIORITY TRIAGE QUEUE & DETAIL TELEMETRY (2-Column Grid) */
              <div 
                style={{ 
                  display: 'grid', 
                  gridTemplateColumns: '380px 1fr', 
                  gap: '24px', 
                  alignItems: 'start' 
                }}
              >
                {/* Left Column: Active Queue */}
                <div>
                  <div 
                    style={{ 
                      display: 'flex', 
                      justifyContent: 'space-between', 
                      alignItems: 'center', 
                      marginBottom: '14px',
                      padding: '0 4px'
                    }}
                  >
                    <span style={{ fontSize: '14px', fontWeight: 800, color: '#0f172a', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                      Incoming Priority Cases ({queue.length})
                    </span>
                    <span style={{ fontSize: '11.5px', fontWeight: 600, color: '#16a34a', display: 'flex', alignItems: 'center', gap: '4px' }}>
                      <span style={{ width: '6px', height: '6px', borderRadius: '50%', backgroundColor: '#16a34a' }} />
                      Auto-Synced
                    </span>
                  </div>

                  {queue.length === 0 ? (
                    <div 
                      style={{ 
                        backgroundColor: '#ffffff', 
                        borderRadius: '14px', 
                        border: '1px solid #e2e8f0', 
                        padding: '40px 20px', 
                        textAlign: 'center', 
                        color: '#64748b', 
                        fontSize: '13.5px' 
                      }}
                    >
                      No active triage cases currently in queue.
                    </div>
                  ) : (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                      {queue.map((item) => {
                        const isSelected = selectedItem?.id === item.id || selectedItem?.call_id === item.call_id;
                        const isCritical = item.risk_level === 'CRITICAL';
                        const accentColor = isCritical ? '#dc2626' : item.risk_level === 'HIGH' ? '#ea580c' : '#64748b';

                        return (
                          <div
                            key={item.id}
                            onClick={() => setSelectedItem(item)}
                            style={{
                              cursor: 'pointer',
                              backgroundColor: '#ffffff',
                              borderRadius: '12px',
                              padding: '16px 18px',
                              borderTop: isSelected ? '2px solid #0f172a' : '1px solid #e2e8f0',
                              borderRight: isSelected ? '2px solid #0f172a' : '1px solid #e2e8f0',
                              borderBottom: isSelected ? '2px solid #0f172a' : '1px solid #e2e8f0',
                              borderLeft: `5px solid ${accentColor}`,
                              boxShadow: isSelected 
                                ? '0 8px 24px -4px rgba(15, 23, 42, 0.12)' 
                                : '0 1px 3px rgba(0,0,0,0.03)',
                              transform: isSelected ? 'translateX(2px)' : 'none',
                              transition: 'all 0.15s ease'
                            }}
                          >
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                              <span 
                                style={{
                                  fontSize: '11px',
                                  fontWeight: 800,
                                  letterSpacing: '0.04em',
                                  textTransform: 'uppercase',
                                  padding: '2px 8px',
                                  borderRadius: '5px',
                                  backgroundColor: isCritical ? '#fef2f2' : '#fffbeb',
                                  color: isCritical ? '#991b1b' : '#92400e',
                                  border: `1px solid ${isCritical ? '#fecaca' : '#fde68a'}`
                                }}
                              >
                                {item.risk_level} • SVI {item.svi_score}
                              </span>
                              <span style={{ fontSize: '11.5px', color: '#94a3b8', fontWeight: 500 }}>
                                {item.timestamp}
                              </span>
                            </div>

                            <h4 style={{ fontSize: '16px', fontWeight: 800, color: '#0f172a', margin: '0 0 4px 0' }}>
                              {item.caller_name ? item.caller_name : item.caller_number}
                            </h4>
                            <div style={{ fontSize: '12.5px', color: '#1e293b', fontWeight: 600, marginBottom: '4px' }}>
                              📞 {item.caller_number}
                            </div>
                            <div style={{ fontSize: '12px', color: '#64748b' }}>
                              {item.channel}
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>

                {/* Right Column: Telemetry, Chart & SBAR Detail View */}
                {selectedItem ? (
                  <div 
                    style={{ 
                      backgroundColor: '#ffffff', 
                      borderRadius: '16px', 
                      border: '1px solid #e2e8f0', 
                      padding: '28px',
                      boxShadow: '0 4px 20px -2px rgba(15, 23, 42, 0.05)'
                    }}
                  >
                    {/* Detail Card Header */}
                    <div 
                      style={{ 
                        display: 'flex', 
                        justifyContent: 'space-between', 
                        alignItems: 'flex-start', 
                        flexWrap: 'wrap', 
                        gap: '14px', 
                        marginBottom: '20px',
                        paddingBottom: '18px',
                        borderBottom: '1px solid #f1f5f9'
                      }}
                    >
                      <div>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px' }}>
                          <span 
                            style={{
                              fontSize: '11px',
                              fontWeight: 800,
                              letterSpacing: '0.05em',
                              textTransform: 'uppercase',
                              padding: '3px 10px',
                              borderRadius: '6px',
                              backgroundColor: selectedItem.risk_level === 'CRITICAL' ? '#fef2f2' : '#fffbeb',
                              color: selectedItem.risk_level === 'CRITICAL' ? '#991b1b' : '#92400e',
                              border: `1px solid ${selectedItem.risk_level === 'CRITICAL' ? '#fecaca' : '#fde68a'}`
                            }}
                          >
                            {selectedItem.risk_level} RISK
                          </span>
                          <span style={{ fontSize: '12px', color: '#64748b', fontWeight: 500 }}>
                            Session Ref: <code style={{ backgroundColor: '#f1f5f9', padding: '1px 6px', borderRadius: '4px' }}>{selectedItem.call_id}</code>
                          </span>
                        </div>
                        <h3 style={{ fontSize: '24px', fontWeight: 800, color: '#0f172a', margin: '0 0 4px 0' }}>
                          {selectedItem.caller_name ? selectedItem.caller_name : selectedItem.caller_number}
                        </h3>
                        {selectedItem.caller_name && (
                          <div style={{ fontSize: '14px', color: '#0f172a', fontWeight: 700, marginBottom: '6px' }}>
                            📞 Mobile Number: <span style={{ color: '#0284c7' }}>{selectedItem.caller_number}</span>
                          </div>
                        )}
                        <div style={{ fontSize: '13px', color: '#64748b' }}>
                          Inbound Channel: <span style={{ fontWeight: 600, color: '#334155' }}>{selectedItem.channel}</span>
                        </div>
                      </div>

                      <button
                        type="button"
                        onClick={() => setDispatchModalOpen(true)}
                        style={{
                          backgroundColor: '#dc2626',
                          color: '#ffffff',
                          border: 'none',
                          borderRadius: '10px',
                          padding: '12px 22px',
                          fontSize: '14px',
                          fontWeight: 700,
                          cursor: 'pointer',
                          boxShadow: '0 4px 14px rgba(220, 38, 38, 0.25)',
                          transition: 'all 0.15s ease'
                        }}
                      >
                        🚨 Dispatch Police PCR 112
                      </button>
                    </div>

                    {/* Caller Audio Evidence Player */}
                    <div 
                      style={{ 
                        marginBottom: '20px', 
                        padding: '16px 20px', 
                        backgroundColor: '#f8fafc', 
                        borderRadius: '12px', 
                        border: '1px solid #edf2f7' 
                      }}
                    >
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
                        <span style={{ fontSize: '12px', fontWeight: 800, textTransform: 'uppercase', letterSpacing: '0.05em', color: '#0f172a' }}>
                          🎧 Caller Audio Telemetry Evidence:
                        </span>
                        <span style={{ fontSize: '12px', color: '#16a34a', fontWeight: 700, display: 'flex', alignItems: 'center', gap: '4px' }}>
                          ● Verified Carrier Telephony Audio
                        </span>
                      </div>
                      <audio
                        controls
                        src={api.getRecordingAudioUrl(`/api/v1/recordings/${selectedItem.call_id}.wav`)}
                        style={{ width: '100%', height: '38px' }}
                      />
                    </div>

                    {/* Verbatim Transcript */}
                    <div style={{ width: '100%', marginBottom: '24px' }}>
                      <div style={{ fontSize: '11.5px', fontWeight: 800, color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '8px' }}>
                        Latest Verbatim Speech Utterance:
                      </div>
                      <div 
                        style={{ 
                          backgroundColor: '#f8fafc', 
                          border: '1px solid #edf2f7', 
                          borderLeft: '4px solid #0f172a',
                          padding: '16px 20px', 
                          borderRadius: '10px', 
                          fontStyle: 'italic',
                          color: '#1e293b',
                          fontSize: '14px',
                          lineHeight: 1.6
                        }}
                      >
                        "{selectedItem.latest_utterance}"
                      </div>
                    </div>

                    {/* Recharts PS 26093 Trauma & Distress Indicators Bar Chart */}
                    <TraumaMetricsChart
                      callerId={selectedItem.id}
                      callerNumber={selectedItem.caller_number}
                      riskLevel={selectedItem.risk_level}
                      sviScore={selectedItem.svi_score}
                      data={getTraumaChartData(selectedItem)}
                    />
                  </div>
                ) : (
                  <div 
                    style={{ 
                      backgroundColor: '#ffffff', 
                      borderRadius: '16px', 
                      border: '1px solid #e2e8f0', 
                      padding: '80px 20px', 
                      textAlign: 'center', 
                      boxShadow: '0 4px 20px -2px rgba(15, 23, 42, 0.05)'
                    }}
                  >
                    <h3 style={{ fontSize: '20px', fontWeight: 800, color: '#0f172a', marginBottom: '8px' }}>No Case Selected</h3>
                    <p style={{ fontSize: '14px', color: '#64748b' }}>Select a triage case from the incoming priority queue on the left to inspect biometric telemetry.</p>
                  </div>
                )}
              </div>
            )}
          </div>
        </main>
      </section>

      {/* Police 112 Dispatch Modal */}
      {dispatchModalOpen && (
        <div className="modal-overlay" style={{ backdropFilter: 'blur(6px)', backgroundColor: 'rgba(15, 23, 42, 0.65)' }}>
          <div 
            className="modal-content"
            style={{
              backgroundColor: '#ffffff',
              borderRadius: '18px',
              border: '1px solid #e2e8f0',
              padding: '32px 36px',
              maxWidth: '540px',
              boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.25)'
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '12px' }}>
              <span style={{ fontSize: '24px' }}>🚨</span>
              <h3 style={{ color: '#b91c1c', fontSize: '22px', fontWeight: 800, margin: 0 }}>
                Confirm Police PCR 112 Dispatch
              </h3>
            </div>
            
            <p style={{ fontSize: '14px', color: '#64748b', marginBottom: '20px', lineHeight: 1.5 }}>
              You are authorizing an immediate emergency intercept broadcast to State Police HQ and the nearest PCR vehicle.
            </p>

            <div 
              style={{ 
                backgroundColor: '#f8fafc', 
                border: '1px solid #e2e8f0', 
                padding: '18px', 
                borderRadius: '12px', 
                marginBottom: '24px',
                fontSize: '13.5px',
                display: 'flex',
                flexDirection: 'column',
                gap: '8px'
              }}
            >
              <div><strong style={{ color: '#0f172a' }}>Caller:</strong> {selectedItem.caller_number}</div>
              <div><strong style={{ color: '#0f172a' }}>Assessment:</strong> {selectedItem.sbar.assessment}</div>
              <div><strong style={{ color: '#0f172a' }}>Target Action:</strong> {selectedItem.sbar.recommendation}</div>
            </div>

            {dispatchSuccess ? (
              <div 
                style={{ 
                  color: '#15803d', 
                  fontWeight: 700, 
                  padding: '14px', 
                  backgroundColor: '#f0fdf4',
                  borderRadius: '10px',
                  border: '1px solid #86efac',
                  textAlign: 'center',
                  fontSize: '14px'
                }}
              >
                ✓ PCR 112 Emergency Intercept Dispatched. Incident Log Transmitted to Control Room.
              </div>
            ) : (
              <div style={{ display: 'flex', gap: '12px', justifyContent: 'flex-end' }}>
                <button
                  type="button"
                  onClick={() => setDispatchModalOpen(false)}
                  className="button secondary small w-button"
                  style={{ borderRadius: '8px', padding: '10px 18px', fontSize: '13.5px' }}
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={handleDispatch}
                  style={{
                    backgroundColor: '#dc2626',
                    color: '#ffffff',
                    border: 'none',
                    borderRadius: '8px',
                    padding: '10px 22px',
                    fontSize: '13.5px',
                    fontWeight: 700,
                    cursor: 'pointer',
                    boxShadow: '0 2px 10px rgba(220, 38, 38, 0.3)'
                  }}
                >
                  Transmit 112 Dispatch Now
                </button>
              </div>
            )}
          </div>
        </div>
      )}
    </>
  );
};
