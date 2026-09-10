import React, { useState, useEffect } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { checkIsSignedIn } from './VoiceAuthModal';

const isCitizenUserSignedIn = (): boolean => {
  if (typeof window === 'undefined') return false;
  if (!checkIsSignedIn()) return false;

  const userRaw = sessionStorage.getItem('sahay_user') || localStorage.getItem('sahay_user');
  if (userRaw) {
    try {
      const user = JSON.parse(userRaw);
      if (user && (user.role === 'operator' || user.badge?.includes('TRIAGE') || user.badge?.includes('OFFICER'))) {
        return false;
      }
    } catch {}
  }

  if (window.location.pathname.startsWith('/operator')) {
    return false;
  }

  return true;
};

export const Navbar: React.FC = () => {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const location = useLocation();
  const [isCitizenSignedIn, setIsCitizenSignedIn] = useState<boolean>(() => isCitizenUserSignedIn());

  useEffect(() => {
    const updateAuth = () => {
      setIsCitizenSignedIn(isCitizenUserSignedIn());
    };
    updateAuth();
    window.addEventListener('storage', updateAuth);
    window.addEventListener('sahay_auth_changed', updateAuth);
    return () => {
      window.removeEventListener('storage', updateAuth);
      window.removeEventListener('sahay_auth_changed', updateAuth);
    };
  }, [location.pathname]);

  const isActive = (path: string) => location.pathname === path;

  const handleHomeClick = (e: React.MouseEvent) => {
    if (location.pathname === '/') {
      e.preventDefault();
      window.scrollTo({ top: 0, behavior: 'smooth' });
    }
  };

  return (
    <nav className="nav">
      <div className="w-layout-blockcontainer container w-container">
        <div className="nav-wrapper">
          <Link 
            to="/" 
            onClick={handleHomeClick}
            className={`nav-logo-wrapper w-inline-block ${isActive('/') ? 'w--current' : ''}`}
            style={{ textDecoration: 'none' }}
          >
            <div 
              className="nav-logo-text" 
              style={{ 
                width: 'auto', 
                letterSpacing: '0.06em', 
                fontWeight: 800, 
                fontSize: '32px', 
                lineHeight: 1, 
                color: 'var(--black)' 
              }}
            >
              SAHAY
            </div>
          </Link>
          
          <div className="nav-menu-items-wrapper">
            <Link 
              to="/" 
              onClick={handleHomeClick}
              className={`nav-menu-item ${isActive('/') ? 'w--current' : ''}`}
            >
              Home
            </Link>
            <a href="/#services" className="nav-menu-item">
              Services
            </a>
            <Link to="/agent" className={`nav-menu-item ${isActive('/agent') ? 'w--current' : ''}`}>
              AI Voice Agent
            </Link>
            <Link to="/contact" className={`nav-menu-item ${isActive('/contact') ? 'w--current' : ''}`}>
              Contact Us
            </Link>
            {isCitizenSignedIn ? (
              <Link 
                to="/user-dashboard" 
                className="button primary small w-button"
                style={{ marginLeft: '12px', padding: '10px 22px', fontSize: '14px' }}
                title="User Dashboard"
              >
                Dashboard
              </Link>
            ) : (
              <Link 
                to="/login" 
                className="button primary small w-button"
                style={{ marginLeft: '12px', padding: '10px 22px', fontSize: '14px' }}
              >
                Sign In
              </Link>
            )}
          </div>

          <div 
            className={`menu-icon-wrapper ${mobileMenuOpen ? 'close' : 'open'}`}
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            style={{ display: 'none' }}
          >
            <img 
              src={mobileMenuOpen 
                ? "https://cdn.prod.website-files.com/65e1c0c2fd61a5053f5c7bc9/65e1ddac5fa44fd60b494d67_Cross.svg"
                : "https://cdn.prod.website-files.com/65e1c0c2fd61a5053f5c7bc9/65e1ddacd6ea5efbf21e94d2_Hamburger%20Menu.svg"
              } 
              loading="lazy" 
              alt="Menu" 
              className="icon-size-28"
            />
          </div>
        </div>
      </div>

      {/* Mobile adaptation drawer if opened */}
      {mobileMenuOpen && (
        <div className="nav-adaptation" style={{ display: 'block', backgroundColor: 'var(--white)', borderBottom: '1px solid var(--grey-8)', padding: '24px 32px' }}>
          <div className="nav-adaptation-links" style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            <Link 
              to="/" 
              className="nav-adaptation-link regular-xl" 
              onClick={(e) => { 
                handleHomeClick(e); 
                setMobileMenuOpen(false); 
              }}
            >
              Home
            </Link>
            <a href="/#services" className="nav-adaptation-link regular-xl" onClick={() => setMobileMenuOpen(false)}>Services</a>
            <Link to="/agent" className="nav-adaptation-link regular-xl" onClick={() => setMobileMenuOpen(false)}>AI Voice Agent</Link>
            <Link to="/contact" className="nav-adaptation-link regular-xl" onClick={() => setMobileMenuOpen(false)}>Contact Us</Link>
            {isCitizenSignedIn ? (
              <Link 
                to="/user-dashboard" 
                className="button primary small w-button" 
                onClick={() => setMobileMenuOpen(false)} 
                style={{ textAlign: 'center', marginTop: '8px' }}
                title="User Dashboard"
              >
                Dashboard
              </Link>
            ) : (
              <Link 
                to="/login" 
                className="button primary small w-button" 
                onClick={() => setMobileMenuOpen(false)} 
                style={{ textAlign: 'center', marginTop: '8px' }}
              >
                Sign In
              </Link>
            )}
          </div>
        </div>
      )}
    </nav>
  );
};
