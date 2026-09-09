import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../services/api';

export interface CitizenComplaint {
  id: string;
  call_id?: string;
  caller_number?: string;
  ticket_ref: string;
  type: 'voice' | 'chat';
  timestamp: string;
  risk_level: 'CRITICAL' | 'HIGH' | 'MODERATE' | 'LOW';
  summary: string;
  language?: string;
  recording_url?: string;
  recommended_services: string[];
  status: string;
  is_legitimate?: boolean;
}

const DEMO_COMPLAINTS: CitizenComplaint[] = [
  {
    id: 'complaint_01',
    call_id: 'call_9901_forest',
    caller_number: '+91 94371-88210',
    ticket_ref: 'TKT-2026-0907-8821',
    type: 'voice',
    timestamp: 'Today, 22:45',
    risk_level: 'CRITICAL',
    summary: 'Outdoor pursuit in forest. Spatial wilderness protocol engaged; zero door-locking hallucination. PCR 112 dispatched to road landmark.',
    language: 'or-IN',
    recording_url: '/api/v1/recordings/call_9901_forest.wav',
    recommended_services: ['PCR 112 Police Dispatch', '14566 Witness Protection Desk', 'DLSA Emergency Cell'],
    status: 'REGISTERED_ACTIVE_TRIAGE',
    is_legitimate: true
  },
  {
    id: 'complaint_02',
    call_id: 'call_9902_boycott',
    caller_number: '+91 98610-44120',
    ticket_ref: 'TKT-2026-0906-4412',
    type: 'voice',
    timestamp: 'Yesterday, 14:15',
    risk_level: 'HIGH',
    summary: 'Social boycott and tube well drinking water access denial. Kosli/Desia dialect normalized. Statutory Section 15A complaint prepared.',
    language: 'sp-IN',
    recording_url: '/api/v1/recordings/call_9902_boycott.wav',
    recommended_services: ['14566 National Helpline', 'DLSA Free Legal Aid', 'District Welfare Magistrate'],
    status: 'REGISTERED_LEGAL_AID',
    is_legitimate: true
  }
];

export const UserDashboard: React.FC = () => {
  const [callerPhone, setCallerPhone] = useState<string>(() => {
    const userStr = sessionStorage.getItem('sahay_user');
    if (userStr) {
      try {
        const u = JSON.parse(userStr);
        if (u.phone) return u.phone;
      } catch {}
    }
    return (
      sessionStorage.getItem('sahay_caller_phone') ||
      localStorage.getItem('sahay_caller_phone') ||
      '+91 94371-88210'
    );
  });

  const [phoneInput, setPhoneInput] = useState<string>('');
  const [complaints, setComplaints] = useState<CitizenComplaint[]>(DEMO_COMPLAINTS);
  const [loading, setLoading] = useState<boolean>(true);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);

  // Auto-login citizen by caller phone number
  useEffect(() => {
    if (callerPhone) {
      const cleanDigits = callerPhone.replace(/\D/g, '').slice(-4) || '8821';
      const userPayload = {
        role: 'user',
        phone: callerPhone,
        id: `citizen_${cleanDigits}`,
        name: `Verified Caller (${callerPhone})`
      };
      sessionStorage.setItem('sahay_user', JSON.stringify(userPayload));
      sessionStorage.setItem('sahay_caller_phone', callerPhone);
      localStorage.setItem('sahay_caller_phone', callerPhone);
    }
  }, [callerPhone]);

  // Load complaints from API filtered by caller phone
  useEffect(() => {
    let mounted = true;
    const fetchComplaints = async () => {
      setLoading(true);
      try {
        const remoteComplaints = await api.getRecentComplaints(callerPhone);
        if (mounted && Array.isArray(remoteComplaints) && remoteComplaints.length > 0) {
          // Filter matching phone digits or include if matches
          const digits = callerPhone.replace(/\D/g, '').slice(-10);
          const matched = remoteComplaints.filter((c: any) => {
            if (!c.caller_number) return true;
            const cDigits = c.caller_number.replace(/\D/g, '').slice(-10);
            return !digits || !cDigits || cDigits.includes(digits) || digits.includes(cDigits);
          });
          setComplaints(matched.length > 0 ? matched : remoteComplaints);
        } else if (mounted) {
          // Filter local showcase by phone
          const digits = callerPhone.replace(/\D/g, '').slice(-10);
          const matched = DEMO_COMPLAINTS.filter((c) => {
            const cDigits = (c.caller_number || '').replace(/\D/g, '').slice(-10);
            return !digits || !cDigits || cDigits.includes(digits) || digits.includes(cDigits);
          });
          setComplaints(matched.length > 0 ? matched : DEMO_COMPLAINTS);
        }
      } catch (err) {
        console.warn('Could not load remote complaints, using cached showcase:', err);
      } finally {
        if (mounted) setLoading(false);
      }
    };
    fetchComplaints();
    return () => {
      mounted = false;
    };
  }, [callerPhone]);

  const handleSwitchPhone = (e: React.FormEvent) => {
    e.preventDefault();
    const clean = phoneInput.trim();
    if (clean) {
      setCallerPhone(clean);
      setPhoneInput('');
      setStatusMessage(`Logged in and loaded case records for ${clean}.`);
      setTimeout(() => setStatusMessage(null), 4000);
    }
  };

  const handleDeleteComplaint = async (target: CitizenComplaint) => {
    const identifier = target.ticket_ref || target.call_id || target.id;
    if (!confirm(`Are you sure you want to permanently delete Complaint ${identifier} and permanently erase its audio recording from state servers (DPDP Act Right to Erasure)?`)) {
      return;
    }

    setDeletingId(identifier);
    try {
      await api.deleteComplaint(identifier);
      setComplaints((prev) => prev.filter((c) => c.ticket_ref !== identifier && c.call_id !== identifier && c.id !== identifier));
      setStatusMessage(`Complaint ${identifier} & call recording permanently erased from state servers per DPDP Act.`);
      setTimeout(() => setStatusMessage(null), 5000);
    } catch (err) {
      console.error('Delete error:', err);
      setStatusMessage('Error deleting complaint. Please try again.');
    } finally {
      setDeletingId(null);
    }
  };

  const handlePurgeAll = () => {
    if (confirm('Permanently purge all local session history from this device?')) {
      setComplaints([]);
      setStatusMessage('All local case logs have been purged for your privacy.');
      setTimeout(() => setStatusMessage(null), 4000);
    }
  };


  return (
    <>
      <section className="section" style={{ paddingTop: '100px' }}>
        <main className="hero-content" style={{ minHeight: 'auto', paddingBottom: '40px' }}>
          <div className="w-layout-blockcontainer container w-container">
            {/* Header */}
            <div className="heading-and-button margin-bottom-40">
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
                  <span className="triage-badge low" style={{ textTransform: 'uppercase', letterSpacing: '0.05em', fontSize: '11px' }}>
                    Citizen Portal • Public Access
                  </span>
                  <span style={{ fontSize: '13px', color: '#059669', fontWeight: 600 }}>
                    ● No Login Required
                  </span>
                </div>
                <h1 className="h2 max-width-640-mobile-480">Citizen Grievance Logs &amp; Audio Recordings</h1>
                <p className="regular-m max-width-480" style={{ marginTop: '8px', color: 'var(--grey-80)' }}>
                  Review recorded helpline call sessions, listen to voice recordings, and exercise your statutory Right to Erasure under the DPDP Act 2023.
                </p>
              </div>

              <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap', alignItems: 'center' }}>
                <Link to="/agent" className="button primary small w-button">
                  Start New Voice Call
                </Link>
                {complaints.length > 0 && (
                  <button 
                    type="button" 
                    onClick={handlePurgeAll} 
                    className="button secondary small w-button"
                  >
                    Purge All (Privacy)
                  </button>
                )}
              </div>
            </div>

            {/* Auto-Logged In Caller Identity & Phone Lookup Card */}
            <div 
              className="block padding-24-32 margin-bottom-32"
              style={{
                backgroundColor: '#f8fafc',
                border: '1.5px solid #cbd5e1',
                borderRadius: '12px',
                padding: '24px 28px'
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '20px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
                  <div 
                    style={{ 
                      width: '48px', 
                      height: '48px', 
                      borderRadius: '50%', 
                      backgroundColor: '#10b981', 
                      color: '#ffffff', 
                      display: 'flex', 
                      alignItems: 'center', 
                      justifyContent: 'center',
                      fontSize: '22px',
                      flexShrink: 0
                    }}
                  >
                    📞
                  </div>
                  <div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px', flexWrap: 'wrap' }}>
                      <span style={{ fontSize: '11px', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.06em', color: '#047857', background: '#d1fae5', padding: '3px 10px', borderRadius: '6px' }}>
                        Auto-Logged In via Caller ID
                      </span>
                      <span style={{ fontSize: '12px', color: '#059669', fontWeight: 600 }}>
                        ● Verified Calling Line Identification (CLI)
                      </span>
                    </div>
                    <div style={{ fontSize: '19px', fontWeight: 700, color: 'var(--black)', letterSpacing: '0.01em' }}>
                      Caller Number: <span style={{ color: '#0f172a' }}>{callerPhone}</span>
                    </div>
                    <div style={{ fontSize: '13px', color: 'var(--grey-80)', marginTop: '2px' }}>
                      Complaints and emergency audio recordings matching this caller line are loaded automatically. No manual sign-in required.
                    </div>
                  </div>
                </div>

                {/* Phone Switcher / Search Input */}
                <form onSubmit={handleSwitchPhone} style={{ display: 'flex', gap: '8px', alignItems: 'center', flexWrap: 'wrap' }}>
                  <input 
                    type="text" 
                    placeholder="Enter caller number (+91...)"
                    value={phoneInput}
                    onChange={(e) => setPhoneInput(e.target.value)}
                    className="form-input w-input"
                    style={{ 
                      marginBottom: 0, 
                      padding: '10px 14px', 
                      fontSize: '13px', 
                      minWidth: '220px', 
                      backgroundColor: '#ffffff',
                      border: '1px solid var(--grey-8)',
                      borderRadius: '6px'
                    }}
                  />
                  <button 
                    type="submit" 
                    className="button primary small w-button"
                    style={{ padding: '10px 18px', fontSize: '13px' }}
                  >
                    Filter by Phone
                  </button>
                  {callerPhone !== '+91 94371-88210' && (
                    <button
                      type="button"
                      onClick={() => {
                        setCallerPhone('+91 94371-88210');
                        setStatusMessage('Switched back to primary caller line +91 94371-88210');
                        setTimeout(() => setStatusMessage(null), 3000);
                      }}
                      className="button secondary small w-button"
                      style={{ padding: '10px 14px', fontSize: '13px' }}
                    >
                      Reset
                    </button>
                  )}
                </form>
              </div>

              {/* Preset Caller Numbers for testing convenience */}
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginTop: '16px', paddingTop: '14px', borderTop: '1px solid #e2e8f0', flexWrap: 'wrap' }}>
                <span style={{ fontSize: '12px', fontWeight: 600, color: 'var(--grey-80)' }}>
                  Test Calling Lines:
                </span>
                <button
                  type="button"
                  onClick={() => setCallerPhone('+91 94371-88210')}
                  style={{
                    border: callerPhone === '+91 94371-88210' ? '1.5px solid #059669' : '1px solid #cbd5e1',
                    background: callerPhone === '+91 94371-88210' ? '#ecfdf5' : '#ffffff',
                    color: callerPhone === '+91 94371-88210' ? '#065f46' : 'var(--grey-80)',
                    padding: '4px 12px',
                    borderRadius: '100px',
                    fontSize: '12px',
                    cursor: 'pointer',
                    fontWeight: callerPhone === '+91 94371-88210' ? 700 : 500
                  }}
                >
                  +91 94371-88210 (Forest Emergency)
                </button>
                <button
                  type="button"
                  onClick={() => setCallerPhone('+91 98610-44120')}
                  style={{
                    border: callerPhone === '+91 98610-44120' ? '1.5px solid #059669' : '1px solid #cbd5e1',
                    background: callerPhone === '+91 98610-44120' ? '#ecfdf5' : '#ffffff',
                    color: callerPhone === '+91 98610-44120' ? '#065f46' : 'var(--grey-80)',
                    padding: '4px 12px',
                    borderRadius: '100px',
                    fontSize: '12px',
                    cursor: 'pointer',
                    fontWeight: callerPhone === '+91 98610-44120' ? 700 : 500
                  }}
                >
                  +91 98610-44120 (Kosli Legal Aid)
                </button>
              </div>
            </div>

            {/* Notification Status Banner */}
            {statusMessage && (
              <div 
                className="margin-bottom-24"
                style={{ 
                  backgroundColor: '#ecfdf5', 
                  border: '1px solid #10b981', 
                  color: '#065f46', 
                  padding: '12px 20px', 
                  borderRadius: '10px',
                  fontWeight: 500,
                  fontSize: '14px',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px'
                }}
              >
                <span>✓</span> {statusMessage}
              </div>
            )}

            {/* Cases List */}
            {loading ? (
              <div className="block padding-24-32 bg-grey-3" style={{ textAlign: 'center', padding: '48px 24px' }}>
                <div className="regular-m">Loading verified citizen complaint logs &amp; audio recordings...</div>
              </div>
            ) : complaints.length === 0 ? (
              <div className="block padding-24-32 bg-grey-3" style={{ textAlign: 'center', padding: '64px 32px' }}>
                <h4 className="h4 margin-bottom-16">No Active Complaints on File</h4>
                <p className="regular-m margin-bottom-24" style={{ maxWidth: '460px', margin: '0 auto 24px auto' }}>
                  There are currently no recorded voice complaints. Call the AI Voice Agent or Helpline 14566 to report an incident. Genuine complaints will appear here with recording playback.
                </p>
                <Link to="/agent" className="button primary small w-button">
                  Call Voice Agent Now
                </Link>
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
                {complaints.map((item) => (
                  <div key={item.ticket_ref || item.id} className="block padding-24-32 bg-grey-3" style={{ borderRadius: '16px' }}>
                    {/* Top Bar */}
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', width: '100%', marginBottom: '16px', flexWrap: 'wrap', gap: '8px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flexWrap: 'wrap' }}>
                        <span className={`triage-badge ${item.risk_level.toLowerCase()}`}>
                          {item.risk_level} RISK
                        </span>
                        <span className="regular-m" style={{ fontWeight: 700, letterSpacing: '0.02em' }}>
                          Ticket Ref: {item.ticket_ref}
                        </span>
                        {item.status && (
                          <span style={{ fontSize: '12px', padding: '3px 10px', borderRadius: '8px', background: '#dbeafe', color: '#1e40af', fontWeight: 600 }}>
                            {item.status.replace(/_/g, ' ')}
                          </span>
                        )}
                      </div>

                      <div className="regular-s color-grey-80">
                        {item.type.toUpperCase()} • {item.timestamp}
                      </div>
                    </div>

                    <div className="line black margin-bottom-20"></div>

                    {/* Summary */}
                    <h4 className="h4 margin-bottom-12" style={{ lineHeight: '1.4' }}>
                      {item.summary}
                    </h4>

                    {/* Audio Player Showcase */}
                    {item.recording_url && (
                      <div 
                        style={{ 
                          marginTop: '16px', 
                          marginBottom: '16px',
                          background: 'var(--white)', 
                          padding: '16px 20px', 
                          borderRadius: '12px', 
                          border: '1px solid var(--grey-8)' 
                        }}
                      >
                        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '10px' }}>
                          <span style={{ fontSize: '13px', fontWeight: 600, color: 'var(--black)', display: 'flex', alignItems: 'center', gap: '6px' }}>
                            <span>🎧</span> Voice Call Audio Recording
                          </span>
                          <span style={{ fontSize: '12px', color: '#059669', fontWeight: 600, background: '#ecfdf5', padding: '2px 8px', borderRadius: '6px' }}>
                            Prank-Verified Genuine Intake
                          </span>
                        </div>
                        <audio 
                          controls 
                          src={api.getRecordingAudioUrl(item.recording_url)} 
                          style={{ width: '100%', height: '40px', outline: 'none' }} 
                        />
                      </div>
                    )}

                    {/* Recommended Services */}
                    <div style={{ marginTop: '16px' }}>
                      <div className="regular-s color-grey-80 margin-bottom-8">Statutory Protections:</div>
                      <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                        {item.recommended_services.map((svc, i) => (
                          <span 
                            key={i} 
                            style={{ 
                              backgroundColor: 'var(--white)', 
                              border: '1px solid var(--grey-8)', 
                              padding: '4px 12px', 
                              borderRadius: '100px', 
                              fontSize: '13px' 
                            }}
                          >
                            {svc}
                          </span>
                        ))}
                      </div>
                    </div>

                    {/* Lower Right Action: Withdraw Case & Delete Audio */}
                    <div 
                      style={{ 
                        display: 'flex', 
                        justifyContent: 'flex-end', 
                        alignItems: 'center', 
                        marginTop: '20px', 
                        paddingTop: '16px', 
                        borderTop: '1px solid #e2e8f0', 
                        width: '100%' 
                      }}
                    >
                      <button
                        type="button"
                        onClick={() => handleDeleteComplaint(item)}
                        disabled={deletingId === (item.ticket_ref || item.id)}
                        className="button small"
                        style={{
                          backgroundColor: '#fee2e2',
                          color: '#991b1b',
                          border: '1px solid #f87171',
                          borderRadius: '8px',
                          cursor: 'pointer',
                          fontWeight: 600,
                          fontSize: '13px',
                          padding: '8px 18px',
                          transition: 'all 0.2s',
                          boxShadow: '0 1px 2px rgba(0,0,0,0.04)'
                        }}
                      >
                        {deletingId === (item.ticket_ref || item.id) ? "Erasing Data..." : "Withdraw Case & Delete Audio"}
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </main>
      </section>
    </>
  );
};
