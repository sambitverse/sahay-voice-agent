import React from 'react';
import { Link } from 'react-router-dom';

export const Footer: React.FC = () => {
  const handleHomeClick = (e: React.MouseEvent) => {
    if (window.location.pathname === '/') {
      e.preventDefault();
      window.scrollTo({ top: 0, behavior: 'smooth' });
    }
  };

  return (
    <section className="footer margin-top-176-mobile-144">
      <div className="w-layout-blockcontainer container w-container">
        <div className="w-layout-grid footer-content-grid">
          <div className="footer-block">
            <div className="wrapper">
              <div className="regular-m margin-bottom-16">Helpline & Triage</div>
              <div className="line black"></div>
            </div>
            <div className="footer-block-links">
              <Link to="/" onClick={handleHomeClick} className="regular-m footer-link">Home</Link>
              <Link to="/agent" className="regular-m footer-link">AI Voice Agent</Link>
              <a href="/#services" className="regular-m footer-link">Services</a>
              <Link to="/contact" className="regular-m footer-link">Contact Us</Link>
              <Link to="/login" className="regular-m footer-link">Sign In (Citizen & Operator)</Link>
            </div>
          </div>

          <div className="footer-block">
            <div className="wrapper">
              <div className="regular-m margin-bottom-16">Statutory Helplines</div>
              <div className="line black"></div>
            </div>
            <div className="footer-block-links">
              <a href="tel:14566" className="regular-m footer-link">14566 National Helpline (Toll-Free)</a>
              <a href="tel:112" className="regular-m footer-link">112 Police Emergency PCR Dispatch</a>
              <a href="tel:14416" className="regular-m footer-link">14416 Tele-MANAS Psychological First Aid</a>
              <a href="tel:181" className="regular-m footer-link">181 Women in Distress Helpline</a>
              <a href="tel:108" className="regular-m footer-link">108 Emergency Medical Response</a>
            </div>
          </div>

          <div id="w-node-a131b771-2a49-3f3f-ead4-9cb52dab31a8-2dab3189" className="footer-block">
            <div className="wrapper">
              <div className="regular-m margin-bottom-16">Institutional Framework</div>
              <div className="line black"></div>
            </div>
            <div className="footer-block-links socials">
              <a href="https://socialjustice.gov.in" target="_blank" rel="noopener noreferrer" className="regular-m footer-link">Ministry of Social Justice & Empowerment</a>
              <a href="https://telemanas.mohfw.gov.in" target="_blank" rel="noopener noreferrer" className="regular-m footer-link">Tele-MANAS Comprehensive Care</a>
              <a href="https://odishapolice.gov.in" target="_blank" rel="noopener noreferrer" className="regular-m footer-link">State Police Emergency Operations</a>
              <a href="https://nalsa.gov.in" target="_blank" rel="noopener noreferrer" className="regular-m footer-link">NALSA / DLSA Legal Aid Authority</a>
            </div>
          </div>
        </div>

        <div className="footer-legal">
          <div className="regular-s color-grey-80">
            © 2026 SAHAY (14566) — National Trauma Voice & Crisis Support System. All Rights Reserved.
          </div>
          <div className="regular-s color-grey-80">
            Enforced under SC/ST Prevention of Atrocities Act 1989 & Witness Protection Scheme 2018.
          </div>
        </div>
      </div>
    </section>
  );
};
