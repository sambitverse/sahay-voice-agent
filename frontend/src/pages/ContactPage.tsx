import React, { useState, useEffect } from 'react';
import { api } from '../services/api';

export const ContactPage: React.FC = () => {
  useEffect(() => {
    if (window.location.hash) {
      const el = document.getElementById(window.location.hash.substring(1));
      if (el) {
        setTimeout(() => el.scrollIntoView({ behavior: 'smooth' }), 100);
      }
    }
  }, []);

  const [formData, setFormData] = useState({
    name: '',
    contact: '',
    category: 'Legal Protection (PoA Act)',
    message: ''
  });
  const [submitting, setSubmitting] = useState(false);
  const [submittedTicket, setSubmittedTicket] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.name || !formData.contact || !formData.message) return;

    setSubmitting(true);
    const res = await api.submitContact(formData);
    setSubmitting(false);
    setSubmittedTicket(res.ticket_id || 'INQ-2026-CONFIRMED');
  };

  return (
    <>
      {/* Hero Section */}
      <section className="section">
        <main className="hero-content">
          <div className="w-layout-blockcontainer container hero internal w-container">
            <div className="hero-section-content">
              <div className="hero-section-content-block internal bg-light-orange">
                <div className="wrapper max-width-640-mobile-480">
                  <h1 className="h1 margin-bottom-28">SAHAY National Helpline Contacts</h1>
                  <p className="regular-xl max-width-420">
                    Whether you need immediate police PCR 112 protection, statutory legal aid under the SC/ST PoA Act, or trauma counseling, our dedicated team is on call 24/7.
                  </p>
                </div>
              </div>
              <div 
                className="hero-section-image internal contact"
                style={{ 
                  backgroundImage: 'url("/images/citizen_contact_phone.png")',
                  backgroundPosition: 'center 30%'
                }}
              ></div>
            </div>
          </div>
        </main>
      </section>

      {/* 3 Grid Blocks */}
      <section className="section margin-top-176-mobile-144">
        <div className="w-layout-blockcontainer container w-container">
          <h2 className="h2 max-width-432-mobile-320 margin-bottom-56">Stay Connected With The Helpline</h2>
          <div className="w-layout-grid blocks-grid-3-tablet-1-mobile-1">
            <a 
              href="https://maps.google.com/?q=DLSA+Odisha" 
              target="_blank" 
              rel="noopener noreferrer" 
              className="block padding-24-32 justify-content bg-grey-3 w-inline-block"
            >
              <div className="wrapper max-width-420-tablet-640 width-100 margin-bottom-32">
                <h4 className="h4 margin-bottom-20">Visit Nodal DLSA Cell</h4>
                <div className="line black margin-bottom-20"></div>
                <p className="regular-m">
                  District Legal Services Authority, Civil Court Complex, Cuttack &amp; Bhubaneswar. Dedicated SC/ST atrocity grievance assistance desk.
                </p>
              </div>
              <div className="tertiary-button">
                <div className="regular-m">View On Map</div>
                <div className="tertiary-button-icon">
                  <img src="https://cdn.prod.website-files.com/65e1c0c2fd61a5053f5c7bc9/65e1ddac5c1d21f3b536e04f_Arrow%20Right.svg" loading="lazy" alt="" className="icon-size-14"/>
                </div>
              </div>
            </a>

            <a 
              href="mailto:helpline14566@odisha.gov.in" 
              className="block padding-24-32 justify-content bg-grey-3 w-inline-block"
            >
              <div className="wrapper max-width-420-tablet-640 width-100 margin-bottom-32">
                <h4 className="h4 margin-bottom-20">Official Legal Intake</h4>
                <div className="line black margin-bottom-20"></div>
                <p className="regular-m">
                  Secure intake: helpline14566@odisha.gov.in. Monitored continuously by state legal officers and trauma triage coordinators.
                </p>
              </div>
              <div className="tertiary-button">
                <div className="regular-m">Send Email</div>
                <div className="tertiary-button-icon">
                  <img src="https://cdn.prod.website-files.com/65e1c0c2fd61a5053f5c7bc9/65e1ddac5c1d21f3b536e04f_Arrow%20Right.svg" loading="lazy" alt="" className="icon-size-14"/>
                </div>
              </div>
            </a>

            <div 
              className="block padding-24-32 justify-content bg-grey-3"
            >
              <div className="wrapper max-width-420-tablet-640 width-100 margin-bottom-32">
                <h4 className="h4 margin-bottom-20">Toll-Free Hotline</h4>
                <div className="line black margin-bottom-20"></div>
                <p className="regular-m">
                  Free 24/7 access from any landline or mobile across India. Dial 112 for Police Emergency PCR.
                </p>
              </div>
              <div style={{ fontSize: '15px', fontWeight: 600, color: 'var(--black)' }}>
                Toll free helpline no. is "08047283123"
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Banner Type Three: Reach Out to Us Form */}
      <section className="section margin-top-176-mobile-144" id="form">
        <div className="w-layout-blockcontainer container w-container">
          <div className="banner-type-three">
            <div className="banner-type-three-content bg-light-yellow">
              <div className="wrapper max-width-600">
                <h2 className="h2 max-width-432-mobile-320 margin-bottom-24">Reach Out to Us</h2>
                <p className="regular-l">
                  Whether you require legal assistance under the PoA Act, compensation processing, or immediate safety protection, submit your details below. An officer will review and reach out securely.
                </p>
              </div>

              <div className="form-block w-form">
                {submittedTicket ? (
                  <div className="success-message w-form-done" style={{ display: 'block', backgroundColor: 'var(--white)', padding: '32px', border: '1px solid var(--grey-8)' }}>
                    <div className="success-message-content">
                      <div className="success-message-icon" style={{ marginBottom: '16px' }}>
                        <img src="https://cdn.prod.website-files.com/65e1c0c2fd61a5053f5c7bc9/65e8751606d530badf35145d_Check.svg" loading="lazy" alt="" className="icon-size-20"/>
                      </div>
                      <div className="wrapper width-100 max-width-420">
                        <h4 className="h4 margin-bottom-12">Your Inquiry Has Been Recorded</h4>
                        <p className="regular-m margin-bottom-16">
                          Tracking Ticket: <strong>{submittedTicket}</strong>
                        </p>
                        <p className="regular-m">
                          A helpline triage officer has been assigned. In immediate danger, call <strong>112</strong> immediately.
                        </p>
                      </div>
                    </div>
                  </div>
                ) : (
                  <form onSubmit={handleSubmit} className="form">
                    <input 
                      className="form-input w-input" 
                      maxLength={256} 
                      placeholder="Full Name" 
                      type="text" 
                      required 
                      value={formData.name}
                      onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    />
                    <input 
                      className="form-input w-input" 
                      maxLength={256} 
                      placeholder="Mobile Phone / Contact" 
                      type="text" 
                      required 
                      value={formData.contact}
                      onChange={(e) => setFormData({ ...formData, contact: e.target.value })}
                    />
                    <input 
                      className="form-input w-input" 
                      maxLength={256} 
                      placeholder="Inquiry Category (e.g. Legal Aid, Police PCR, Boycott, Compensation)" 
                      type="text" 
                      value={formData.category}
                      onChange={(e) => setFormData({ ...formData, category: e.target.value })}
                    />
                    <input 
                      className="form-input last w-input" 
                      maxLength={500} 
                      placeholder="Details of situation or inquiry..." 
                      type="text" 
                      required 
                      value={formData.message}
                      onChange={(e) => setFormData({ ...formData, message: e.target.value })}
                    />
                    <input 
                      type="submit" 
                      disabled={submitting} 
                      className="button primary small w-button" 
                      value={submitting ? "Transmitting..." : "Send Message"}
                    />
                  </form>
                )}
              </div>
            </div>

            <div className="banner-type-three-image">
              <img 
                src="/images/helpline_callcenter.jpeg" 
                loading="lazy" 
                alt="SAHAY Helpline Triage Operators" 
                className="parallax-image"
                style={{ width: '100%', height: '100%', objectFit: 'cover', position: 'absolute', top: 0, left: 0 }}
              />
            </div>
          </div>
        </div>
      </section>

      {/* Follow / Directory */}
      <section className="section margin-top-176-mobile-144">
        <div className="w-layout-blockcontainer container w-container">
          <h2 className="h2 max-width-432-mobile-320 margin-bottom-56">Official Emergency Channels</h2>
          <div className="w-layout-grid cards-grid-2-tablet-2-mobile-1 socials">
            <div className="wrapper">
              <div className="line black margin-bottom-20"></div>
              <div className="wrapper social-link">
                <h4 className="h4">Toll Free Helpline: 08047283123</h4>
              </div>
            </div>
            <a href="tel:112" className="wrapper w-inline-block">
              <div className="line black margin-bottom-20"></div>
              <div className="wrapper social-link">
                <h4 className="h4">112 Police Emergency PCR</h4>
                <img src="https://cdn.prod.website-files.com/65e1c0c2fd61a5053f5c7bc9/65e1ddac852c806c77a38998_Arrow%20Up%20Right.svg" loading="lazy" alt="" className="icon-size-20"/>
              </div>
            </a>
            <a href="tel:14416" className="wrapper w-inline-block">
              <div className="line black margin-bottom-20"></div>
              <div className="wrapper social-link">
                <h4 className="h4">14416 Tele-MANAS Counseling</h4>
                <img src="https://cdn.prod.website-files.com/65e1c0c2fd61a5053f5c7bc9/65e1ddac852c806c77a38998_Arrow%20Up%20Right.svg" loading="lazy" alt="" className="icon-size-20"/>
              </div>
            </a>
            <a href="https://dlsa.gov.in" target="_blank" rel="noopener noreferrer" className="wrapper w-inline-block">
              <div className="line black margin-bottom-20"></div>
              <div className="wrapper social-link">
                <h4 className="h4">District Legal Services Authority</h4>
                <img src="https://cdn.prod.website-files.com/65e1c0c2fd61a5053f5c7bc9/65e1ddac852c806c77a38998_Arrow%20Up%20Right.svg" loading="lazy" alt="" className="icon-size-20"/>
              </div>
            </a>
          </div>
        </div>
      </section>
    </>
  );
};
