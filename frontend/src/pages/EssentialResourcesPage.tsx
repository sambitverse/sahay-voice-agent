import React, { useState, useEffect } from 'react';
import { Link, useLocation } from 'react-router-dom';

interface FAQItem {
  question: string;
  answer: string;
}

interface ResourceItem {
  id: string;
  icon: string;
  title: string;
  category: string;
  badge: string;
  overview: string;
  faqs: FAQItem[];
}

const RESOURCES: ResourceItem[] = [
  {
    id: 'pcr-112',
    icon: 'https://cdn.prod.website-files.com/65e1c0c2fd61a5053f5c7bc9/65e1ddac271bec0c838fff01_Bus.svg',
    title: 'Police PCR 112 Direct Escalation',
    category: 'Immediate Emergency Law Enforcement',
    badge: 'Statutory 112 Bridge',
    overview: 'Automated geolocation routing and SBAR (Situation-Background-Assessment-Recommendation) transmission dispatch state police units in acute physical emergencies within seconds.',
    faqs: [
      {
        question: 'How does SAHAY automatically escalate a call to Police PCR 112?',
        answer: 'When the acoustic prosody telemetry or linguistic risk rules detect active armed pursuit, physical violence, or immediate threat to life, an SBAR clinical handoff packet is generated and transmitted instantaneously to the State Police Emergency Command Centre (PCR 112) with geocoordinates and nearest terrain landmarks.'
      },
      {
        question: 'What information is shared with police dispatchers?',
        answer: 'Only critical safety information is transmitted: caller location or terrain landmark, emergency severity, weapon indicators, and immediate survival instructions given. Personal audio and private disclosures remain encrypted under the DPDP Act 2023.'
      },
      {
        question: 'Can an ongoing call be intercepted by a human police operator?',
        answer: 'Yes. Connected police dispatchers and Helpline 14566 operators can bridge directly into the call at any moment via the Live Operator Triage Console, overriding the AI agent to provide direct tactical instructions.'
      },
      {
        question: 'What happens if the caller cannot speak due to attackers nearby?',
        answer: 'The system recognizes silence, breathing tension, and whispered speech through Voice Activity Detection (VAD). It instructs the caller to keep the line open and automatically triggers silent PCR 112 geolocated dispatch without requiring verbal responses.'
      }
    ]
  },
  {
    id: 'sc-st-rights',
    icon: 'https://cdn.prod.website-files.com/65e1c0c2fd61a5053f5c7bc9/65e1ddad99de8a8440c54155_Books.svg',
    title: 'SC/ST PoA Statutory Rights & DLSA',
    category: 'Legal Aid & Witness Protection',
    badge: 'Section 15A Enforced',
    overview: 'Mandatory Section 15A rights under the SC/ST Prevention of Atrocities Act, free legal counsel via District Legal Services Authorities (DLSA), and government compensation claim processing.',
    faqs: [
      {
        question: 'What protections are guaranteed under Section 15A of the SC/ST PoA Act?',
        answer: 'Section 15A mandates that victims and witnesses be protected from all forms of intimidation, coercion, or harassment. It guarantees free legal representation, state-funded travel and daily allowance during hearings, immediate police protection, and notification of all bail proceedings.'
      },
      {
        question: 'How do I access free legal aid through DLSA?',
        answer: 'SAHAY automatically routes your verified grievance report to the nodal District Legal Services Authority (DLSA) cell. A dedicated empanelled advocate is appointed to draft the FIR, represent you in Special Courts, and record statements under Section 164 CrPC with zero legal fees.'
      },
      {
        question: 'What statutory compensation amounts are provided to victims?',
        answer: 'Under the Scheduled Castes and Scheduled Tribes (Prevention of Atrocities) Rules, prescribed compensation ranges between ₹85,000 and ₹8,25,000 depending on the offence, with up to 50% released immediately upon FIR registration and medical examination.'
      },
      {
        question: 'What if local village authorities or police refuse to register the FIR?',
        answer: 'Refusal to register an atrocity FIR constitutes an offence under Section 4 of the PoA Act. SAHAY escalates directly to the Superintendent of Police (SP) and District Magistrate (DM) and coordinates a mandamus grievance with the State Legal Services Authority.'
      }
    ]
  },
  {
    id: 'svi-triage',
    icon: 'https://cdn.prod.website-files.com/65e1c0c2fd61a5053f5c7bc9/65e1ddacc2cc0d921a4caf31_Graph.svg',
    title: 'Acoustic Emotion & SVI Triage',
    category: 'Prosodic Telemetry & AI Screening',
    badge: 'Wav2Vec2 Biomarkers',
    overview: 'Wav2Vec2 acoustic prosody telemetry (pitch, jitter, pause ratio) computes the Stress Vulnerability Index (SVI) without intrusive interrogation, measuring physiological fight-or-flight freeze states.',
    faqs: [
      {
        question: 'What is the Stress Vulnerability Index (SVI)?',
        answer: 'The Stress Vulnerability Index (SVI) is a normalized clinical score ranging from 0.00 (calm) to 1.00 (acute trauma/shock). It dynamically weights fundamental pitch frequency (F0), vocal tremor jitter, shimmer, speech-pause ratio, and semantic distress signals.'
      },
      {
        question: 'How does SAHAY detect distress without asking intrusive questions?',
        answer: 'Trauma victims often suffer from acute shock, mutism, or hyperventilation. By evaluating micro-tremors and acoustic freeze patterns directly from raw voice audio, SAHAY diagnoses distress levels objectively without forcing the caller to recount traumatic details.'
      },
      {
        question: 'How are prank and spam calls screened out?',
        answer: 'The integrated Prank & Spam Precaution Gate screens for premature hangups, empty audio, repetitive laughter, and troll keywords before generating official tickets. Genuine distress indicators immediately bypass this filter to ensure zero delay for real victims.'
      },
      {
        question: 'Are caller voice biometric models saved permanently?',
        answer: 'No. Raw vocal biometric parameters are computed in volatile memory during the active session. Under the DPDP Act 2023, citizens maintain complete Right to Erasure to permanently delete their call history and recordings with a single click.'
      }
    ]
  },
  {
    id: 'spatial-dialects',
    icon: 'https://cdn.prod.website-files.com/65e1c0c2fd61a5053f5c7bc9/65e1ddacf8932bbb9febfbe8_Notebook.svg',
    title: 'Spatial Grounding & Tribal Dialects',
    category: 'Linguistic Intelligence & Wilderness Safety',
    badge: 'Kui, Desia, Kosli, Santali',
    overview: 'Zero-hallucination outdoor wilderness guidance. Native dialect normalization for Sambalpuri (Kosli), Santali (Ol Chiki), Kui (Kandha tribal), Desia (Koraput), and Odia.',
    faqs: [
      {
        question: 'How does Spatial Grounding prevent dangerous AI hallucinations?',
        answer: 'In outdoor pursuit emergencies, standard LLMs often hallucinate indoor advice like "lock your room door" or "turn on the lights." SAHAY enforces strict environmental constraints: if forest or outdoor pursuit keywords are detected, indoor guidance is completely forbidden and replaced with terrain camouflage, phone silencing, and landmark navigation.'
      },
      {
        question: 'Which indigenous tribal dialects are natively supported?',
        answer: 'SAHAY includes verified phonetic and lexical models for Kui (Kandha tribal), Desia (Koraput / Southwestern Odia), Sambalpuri (Kosli), and Santali (Ol Chiki script and Romanized phonetics), alongside standard Odia and English.'
      },
      {
        question: 'Does the system understand broken or regional colloquial Odia?',
        answer: 'Yes. The system was trained on the 500-row Indian Linguistic Risk Corpus (ILRC), allowing it to comprehend colloquial phrases, accent variations, and rural distress expressions like "godauche", "marba", "khedi dele", and "havba boli vespanji".'
      },
      {
        question: 'What psychological grounding techniques are provided in tribal languages?',
        answer: 'The agent employs somatic grounding exercises (5-4-3-2-1 sensory orientation and box breathing) spoken in the caller’s mother tongue, helping de-escalate acute panic and enabling the victim to stay calm until emergency units arrive.'
      }
    ]
  }
];

export const EssentialResourcesPage: React.FC = () => {
  const [openFaqs, setOpenFaqs] = useState<{ [key: string]: boolean }>({});
  const location = useLocation();

  useEffect(() => {
    // Scroll to top or specific hash anchor if present
    if (location.hash) {
      const el = document.getElementById(location.hash.replace('#', ''));
      if (el) {
        el.scrollIntoView({ behavior: 'smooth' });
        return;
      }
    }
    window.scrollTo(0, 0);
  }, [location]);

  const toggleFaq = (key: string) => {
    setOpenFaqs((prev) => ({
      ...prev,
      [key]: !prev[key]
    }));
  };

  return (
    <div style={{ paddingTop: '100px', minHeight: '100vh', backgroundColor: 'var(--white)' }}>
      {/* Top Breadcrumb & Header */}
      <section className="section">
        <div className="w-layout-blockcontainer container w-container">
          <div style={{ marginBottom: '32px' }}>
            <Link 
              to="/" 
              style={{ 
                display: 'inline-flex', 
                alignItems: 'center', 
                gap: '8px', 
                color: 'var(--grey-80)', 
                fontSize: '14px', 
                textDecoration: 'none',
                fontWeight: 600,
                marginBottom: '16px' 
              }}
            >
              ← Back to Homepage
            </Link>
            <div className="regular-m margin-bottom-12" style={{ textTransform: 'uppercase', letterSpacing: '0.05em', color: '#b91c1c', fontWeight: 600 }}>
              Helpline 14566 Knowledge Base
            </div>
            <h1 className="h1 margin-bottom-20">Essential Resources for Citizens in Distress</h1>
            <p className="regular-xl max-width-640-mobile-480" style={{ color: 'var(--grey-80)' }}>
              Comprehensive information, statutory rights, technical architecture, and interactive questions &amp; answers for the 4 core pillars of SAHAY crisis response.
            </p>
          </div>
          <div className="line black margin-bottom-56"></div>

          {/* The 4 Resource Cards with Dropdown Q&A */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '48px', marginBottom: '80px' }}>
            {RESOURCES.map((resource, idx) => (
              <div 
                key={resource.id} 
                id={resource.id}
                className="block bg-grey-3 padding-24-32" 
                style={{ 
                  borderRadius: '8px', 
                  border: '1px solid var(--grey-8)',
                  padding: '36px 32px'
                }}
              >
                {/* Header Row */}
                <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', flexWrap: 'wrap', gap: '16px', marginBottom: '20px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '20px' }}>
                    <img 
                      src={resource.icon} 
                      alt="" 
                      className="icon-size-40" 
                      style={{ padding: '8px', backgroundColor: 'var(--white)', borderRadius: '8px', border: '1px solid var(--grey-8)' }}
                    />
                    <div>
                      <div className="regular-s color-grey-80" style={{ textTransform: 'uppercase', letterSpacing: '0.05em', fontWeight: 600 }}>
                        Resource #{idx + 1} • {resource.category}
                      </div>
                      <h2 className="h3" style={{ marginTop: '4px' }}>{resource.title}</h2>
                    </div>
                  </div>
                  <span className="triage-badge low" style={{ fontSize: '13px', padding: '6px 14px' }}>
                    {resource.badge}
                  </span>
                </div>

                {/* Overview */}
                <p className="regular-m" style={{ fontSize: '16px', lineHeight: '1.6', marginBottom: '28px', color: 'var(--black)' }}>
                  {resource.overview}
                </p>

                <div className="line" style={{ backgroundColor: 'var(--grey-8)', marginBottom: '24px' }}></div>

                {/* Dropdowns Section */}
                <div style={{ width: '100%' }}>
                  <div className="regular-s color-grey-80 margin-bottom-16" style={{ fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                    Frequently Asked Questions &amp; Technical Insights:
                  </div>

                  <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                    {resource.faqs.map((faq, fIdx) => {
                      const faqKey = `${resource.id}-${fIdx}`;
                      const isOpen = !!openFaqs[faqKey];

                      return (
                        <div 
                          key={faqKey}
                          style={{
                            backgroundColor: 'var(--white)',
                            border: isOpen ? '1px solid var(--black)' : '1px solid var(--grey-8)',
                            borderRadius: '6px',
                            overflow: 'hidden',
                            transition: 'all 0.2s ease'
                          }}
                        >
                          <button
                            type="button"
                            onClick={() => toggleFaq(faqKey)}
                            style={{
                              width: '100%',
                              padding: '16px 20px',
                              display: 'flex',
                              justifyContent: 'space-between',
                              alignItems: 'center',
                              background: 'transparent',
                              border: 'none',
                              cursor: 'pointer',
                              textAlign: 'left'
                            }}
                          >
                            <span style={{ fontSize: '16px', fontWeight: 600, color: 'var(--black)', paddingRight: '16px' }}>
                              {faq.question}
                            </span>
                            <span 
                              style={{ 
                                fontSize: '20px', 
                                fontWeight: 700, 
                                minWidth: '24px', 
                                textAlign: 'center',
                                color: isOpen ? '#b91c1c' : 'var(--grey-80)',
                                transform: isOpen ? 'rotate(45deg)' : 'none',
                                transition: 'transform 0.2s'
                              }}
                            >
                              +
                            </span>
                          </button>

                          {isOpen && (
                            <div style={{ padding: '0 20px 20px 20px', color: 'var(--grey-80)', fontSize: '15px', lineHeight: '1.6' }}>
                              <div style={{ borderTop: '1px solid var(--grey-8)', paddingTop: '12px' }}>
                                {faq.answer}
                              </div>
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>
    </div>
  );
};

export default EssentialResourcesPage;
