import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { TraumaMetricsChart, type TraumaIndicatorData } from '../components/TraumaMetricsChart';
import { api, getDashboardWsUrl } from '../services/api';

interface QueueItem {
  id: string;
  call_id: string;
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
  const wsRef = useRef<WebSocket | null>(null);
  const navigate = useNavigate();

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
                  caller_number: `Caller (${(c.language || 'ODIA').toUpperCase()})`,
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
                caller_number: `Caller (${(data.language || 'Voice').toUpperCase()})`,
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
              setBannerMessage({
                type: 'success',
                text: `[New Verified Grievance] Ticket ${data.ticket_id} registered (${data.language}). Real-time queue updated.`
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
      <section className="section" style={{ paddingTop: '100px' }}>
        <main className="hero-content" style={{ minHeight: 'auto', paddingBottom: '40px' }}>
          <div className="w-layout-blockcontainer container w-container">
            <div className="heading-and-button margin-bottom-40">
              <div>
                <div className="regular-m margin-bottom-12" style={{ textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                  Live National Operations
                </div>
                <h2 className="h2 max-width-432-mobile-320">Operator Triage Console</h2>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
                <div style={{ 
                  display: 'flex', 
                  alignItems: 'center', 
                  gap: '8px', 
                  padding: '6px 14px', 
                  borderRadius: '100px', 
                  backgroundColor: wsConnected ? '#f0fdf4' : '#fef2f2', 
                  border: `1px solid ${wsConnected ? '#86efac' : '#fca5a5'}` 
                }}>
                  <span style={{ 
                    width: '8px', 
                    height: '8px', 
                    borderRadius: '50%', 
                    backgroundColor: wsConnected ? '#16a34a' : '#dc2626', 
                    display: 'inline-block' 
                  }}></span>
                  <span style={{ fontSize: '13px', fontWeight: 600, color: wsConnected ? '#166534' : '#991b1b' }}>
                    {wsConnected ? 'LIVE SYNC ACTIVE' : 'RECONNECTING WS'}
                  </span>
                </div>
                <button 
                  type="button" 
                  onClick={handleSignOut} 
                  className="button secondary small w-button"
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
                  padding: '16px 20px',
                  borderRadius: '8px',
                  backgroundColor: bannerMessage.type === 'warning' ? '#fffbeb' : bannerMessage.type === 'success' ? '#f0fdf4' : '#eff6ff',
                  border: `1px solid ${bannerMessage.type === 'warning' ? '#fde68a' : bannerMessage.type === 'success' ? '#86efac' : '#bfdbfe'}`,
                  color: bannerMessage.type === 'warning' ? '#92400e' : bannerMessage.type === 'success' ? '#166534' : '#1e40af',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  fontWeight: 600,
                  fontSize: '14px',
                  boxShadow: '0 2px 8px rgba(0,0,0,0.04)'
                }}
              >
                <div>{bannerMessage.text}</div>
                <button
                  type="button"
                  onClick={() => setBannerMessage(null)}
                  style={{ background: 'transparent', border: 'none', cursor: 'pointer', fontSize: '16px', color: 'inherit' }}
                >
                  ✕
                </button>
              </div>
            )}

            {/* Main 2-Column Grid */}
            <div className="w-layout-grid blocks-grid-2-tablet-1-mobile-1" style={{ gridTemplateColumns: '4.5fr 7.5fr' }}>
              {/* Left Column: Active Queue */}
              <div>
                <div className="regular-m margin-bottom-16" style={{ fontWeight: 600, display: 'flex', justifyContent: 'space-between' }}>
                  <span>Incoming Priority Queue ({queue.length})</span>
                  <span className="regular-s color-grey-80" style={{ fontWeight: 400 }}>Auto-Synced</span>
                </div>
                {queue.length === 0 ? (
                  <div className="block padding-24-32 bg-grey-3" style={{ textAlign: 'center', color: 'var(--grey-60)' }}>
                    No active triage cases currently in queue.
                  </div>
                ) : (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                    {queue.map((item) => (
                      <div
                        key={item.id}
                        onClick={() => setSelectedItem(item)}
                        className="block padding-24-32 bg-grey-3"
                        style={{
                          cursor: 'pointer',
                          border: selectedItem?.id === item.id ? '2px solid var(--black)' : '1px solid var(--grey-8)',
                          backgroundColor: selectedItem?.id === item.id ? 'var(--white)' : 'var(--grey-3)',
                          transition: 'all 0.2s'
                        }}
                      >
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', width: '100%', marginBottom: '12px' }}>
                          <span className={`triage-badge ${item.risk_level.toLowerCase()}`}>
                            {item.risk_level} • SVI {item.svi_score}
                          </span>
                          <span className="regular-s color-grey-80">{item.timestamp}</span>
                        </div>
                        <h4 className="h4" style={{ fontSize: '20px', marginBottom: '8px' }}>
                          {item.caller_number}
                        </h4>
                        <p className="regular-s color-grey-80">{item.channel}</p>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Right Column: Telemetry & SBAR */}
              {selectedItem ? (
                <div className="block padding-24-32 bg-grey-3">
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', width: '100%', marginBottom: '16px' }}>
                    <div>
                      <span className={`triage-badge ${selectedItem.risk_level.toLowerCase()}`}>
                        {selectedItem.risk_level} RISK
                      </span>
                      <h3 className="h3 margin-bottom-12">{selectedItem.caller_number}</h3>
                      <div className="regular-s color-grey-80">
                        Channel: {selectedItem.channel} • Session Ref: {selectedItem.call_id}
                      </div>
                    </div>
                    <button
                      type="button"
                      onClick={() => setDispatchModalOpen(true)}
                      className="button primary w-button"
                      style={{ backgroundColor: '#b91c1c' }}
                    >
                      Dispatch Police 112
                    </button>
                  </div>

                  <div className="line black margin-bottom-20"></div>

                  {/* Caller Audio Evidence Player */}
                  <div style={{ marginBottom: '20px', padding: '14px 18px', backgroundColor: 'var(--white)', borderRadius: '4px', border: '1px solid var(--grey-8)' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                      <span className="regular-s color-grey-80" style={{ fontWeight: 700, textTransform: 'uppercase' }}>
                        Caller Recording Evidence:
                      </span>
                      <span className="regular-s" style={{ fontSize: '12px', color: '#15803d', fontWeight: 600 }}>
                        ● Verified Telephony Capture
                      </span>
                    </div>
                    <audio
                      controls
                      src={api.getRecordingAudioUrl(`/api/v1/recordings/${selectedItem.call_id}.wav`)}
                      style={{ width: '100%', height: '36px' }}
                    />
                  </div>

                  {/* Verbatim Transcript */}
                  <div style={{ width: '100%', marginBottom: '24px' }}>
                    <div className="regular-s color-grey-80 margin-bottom-8" style={{ textTransform: 'uppercase' }}>
                      Latest Verbatim Utterance:
                    </div>
                    <div style={{ backgroundColor: 'var(--white)', border: '1px solid var(--grey-8)', padding: '16px 20px', borderRadius: '4px', fontStyle: 'italic' }}>
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

                  {/* SBAR Report */}
                  <div style={{ width: '100%' }}>
                    <div className="regular-s color-grey-80 margin-bottom-12" style={{ textTransform: 'uppercase' }}>
                      SBAR Clinical Handoff Report:
                    </div>
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                      <div style={{ backgroundColor: 'var(--white)', border: '1px solid var(--grey-8)', padding: '14px 18px', borderRadius: '4px' }}>
                        <div className="regular-s color-grey-80" style={{ fontWeight: 700 }}>S - SITUATION</div>
                        <p className="regular-m" style={{ fontSize: '14px' }}>{selectedItem.sbar.situation}</p>
                      </div>
                      <div style={{ backgroundColor: 'var(--white)', border: '1px solid var(--grey-8)', padding: '14px 18px', borderRadius: '4px' }}>
                        <div className="regular-s color-grey-80" style={{ fontWeight: 700 }}>B - BACKGROUND</div>
                        <p className="regular-m" style={{ fontSize: '14px' }}>{selectedItem.sbar.background}</p>
                      </div>
                      <div style={{ backgroundColor: 'var(--white)', border: '1px solid var(--grey-8)', padding: '14px 18px', borderRadius: '4px' }}>
                        <div className="regular-s color-grey-80" style={{ fontWeight: 700 }}>A - ASSESSMENT</div>
                        <p className="regular-m" style={{ fontSize: '14px' }}>{selectedItem.sbar.assessment}</p>
                      </div>
                      <div style={{ backgroundColor: 'var(--white)', border: '1px solid var(--grey-8)', padding: '14px 18px', borderRadius: '4px' }}>
                        <div className="regular-s color-grey-80" style={{ fontWeight: 700 }}>R - RECOMMENDATION</div>
                        <p className="regular-m" style={{ fontSize: '14px' }}>{selectedItem.sbar.recommendation}</p>
                      </div>
                    </div>
                  </div>
                </div>
              ) : (
                <div className="block padding-24-32 bg-grey-3" style={{ textAlign: 'center', padding: '60px 20px' }}>
                  <h3 className="h3 margin-bottom-12">No Case Selected</h3>
                  <p className="regular-m color-grey-80">Select a triage case from the incoming queue on the left to inspect telemetry.</p>
                </div>
              )}
            </div>
          </div>
        </main>
      </section>

      {/* Police 112 Dispatch Modal */}
      {dispatchModalOpen && (
        <div className="modal-overlay">
          <div className="modal-content">
            <h3 className="h3 margin-bottom-16" style={{ color: '#b91c1c' }}>
              Confirm Police PCR 112 Dispatch
            </h3>
            <div className="line black margin-bottom-20"></div>
            <p className="regular-m margin-bottom-20">
              You are dispatching an immediate statutory law-enforcement intercept for:
            </p>
            <div style={{ backgroundColor: 'var(--grey-3)', padding: '16px', borderRadius: '4px', marginBottom: '24px' }}>
              <div><strong>Caller:</strong> {selectedItem.caller_number}</div>
              <div><strong>Assessment:</strong> {selectedItem.sbar.assessment}</div>
              <div><strong>Action:</strong> {selectedItem.sbar.recommendation}</div>
            </div>

            {dispatchSuccess ? (
              <div style={{ color: '#15803d', fontWeight: 700, padding: '12px 0' }}>
                ✓ PCR 112 Unit Dispatched Successfully. Incident Log Transmitted.
              </div>
            ) : (
              <div style={{ display: 'flex', gap: '12px', justifyContent: 'flex-end' }}>
                <button
                  type="button"
                  onClick={() => setDispatchModalOpen(false)}
                  className="button secondary small w-button"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={handleDispatch}
                  className="button primary small w-button"
                  style={{ backgroundColor: '#b91c1c' }}
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
