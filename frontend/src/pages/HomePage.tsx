import React from 'react';
import { Link } from 'react-router-dom';

export const HomePage: React.FC = () => {
  React.useEffect(() => {
    if (window.location.hash) {
      const elem = document.querySelector(window.location.hash);
      if (elem) {
        elem.scrollIntoView();
      }
    }
  }, []);

  return (
    <>
      {/* Hero Section */}
      <section className="section">
        <main className="hero-content">
          <div className="w-layout-blockcontainer container hero w-container">
            <div className="hero-section-content">
              <div className="hero-section-content-block home">
                <div className="wrapper max-width-640-mobile-480">
                  <h1 className="h1 margin-bottom-28">Empowering Voices, Restoring Dignity</h1>
                  <p className="regular-xl max-width-420">
                    National Emergency Helpline 14566 &amp; AI Voice Agent. Immediate trauma-informed psychological triage, multilingual support in 22+ languages and tribal dialects, and statutory PCR 112 police dispatch.
                  </p>
                </div>
                <div className="buttons-wrapper">
                  <Link to="/agent" className="button primary w-button">
                    Speak to Agent
                  </Link>
                  <Link to="/contact" className="button secondary w-button">
                    Contact Helpline
                  </Link>
                </div>
              </div>

              <div 
                className="hero-section-image home-block"
                style={{ 
                  backgroundImage: 'url("/images/hero_tribal_woman.webp")',
                  backgroundPosition: 'center top'
                }}
              ></div>
            </div>
          </div>
        </main>
      </section>

      {/* Banner Type One */}
      <section className="section margin-top-64-tablet-48-mobile-24">
        <div className="w-layout-blockcontainer container w-container">
          <div className="banner-type-one">
            <div className="banner-type-one-content">
              <div className="wrapper max-width-880-tablet-640-mobile-480">
                <p className="banner-heading">
                  Immediate Protection Under The SC/ST Prevention of Atrocities Act &amp; Statutory Compensation
                </p>
              </div>
              <Link to="/agent" className="button primary w-button">
                Launch Voice Triage
              </Link>
            </div>
            <div className="banner-type-one-pattern hero-one"></div>
          </div>
        </div>
      </section>

      {/* 4 Grid Blocks: Essential Resources */}
      <section className="section margin-top-176-mobile-144">
        <div className="w-layout-blockcontainer container w-container">
          <h2 className="h2 max-width-432-mobile-320 margin-bottom-56">
            Essential Resources for Citizens in Distress
          </h2>
          <div className="w-layout-grid blocks-grid-4-tablet-2-mobile-1">
            <Link to="/essential-resources#pcr-112" className="block padding-24-32 bg-grey-3 w-inline-block">
              <img 
                src="https://cdn.prod.website-files.com/65e1c0c2fd61a5053f5c7bc9/65e1ddac271bec0c838fff01_Bus.svg" 
                loading="lazy" 
                alt="" 
                className="icon-size-40 margin-bottom-40"
              />
              <div className="wrapper justify-content">
                <div className="wrapper max-width-420 margin-bottom-32">
                  <h4 className="h4 margin-bottom-16">Police PCR 112 Direct Escalation</h4>
                  <p className="regular-m">
                    Automated geolocation routing and SBAR transmission dispatch police units in acute physical emergencies within seconds.
                  </p>
                </div>
                <div className="tertiary-button">
                  <div className="regular-m">Learn More</div>
                  <div className="tertiary-button-icon">
                    <img src="https://cdn.prod.website-files.com/65e1c0c2fd61a5053f5c7bc9/65e1ddac852c806c77a38998_Arrow%20Up%20Right.svg" loading="lazy" alt="" className="icon-size-14"/>
                  </div>
                </div>
              </div>
            </Link>

            <Link to="/essential-resources#sc-st-rights" className="block padding-24-32 bg-grey-3 w-inline-block">
              <img 
                src="https://cdn.prod.website-files.com/65e1c0c2fd61a5053f5c7bc9/65e1ddad99de8a8440c54155_Books.svg" 
                loading="lazy" 
                alt="" 
                className="icon-size-40 margin-bottom-40"
              />
              <div className="wrapper justify-content">
                <div className="wrapper max-width-420 margin-bottom-32">
                  <h4 className="h4 margin-bottom-16">SC/ST PoA Statutory Rights &amp; DLSA</h4>
                  <p className="regular-m">
                    Mandatory Section 15A rights, free legal aid via District Legal Services Authorities, and compensation claim processing.
                  </p>
                </div>
                <div className="tertiary-button">
                  <div className="regular-m">Learn More</div>
                  <div className="tertiary-button-icon">
                    <img src="https://cdn.prod.website-files.com/65e1c0c2fd61a5053f5c7bc9/65e1ddac852c806c77a38998_Arrow%20Up%20Right.svg" loading="lazy" alt="" className="icon-size-14"/>
                  </div>
                </div>
              </div>
            </Link>

            <Link to="/essential-resources#svi-triage" className="block padding-24-32 bg-grey-3 w-inline-block">
              <img 
                src="https://cdn.prod.website-files.com/65e1c0c2fd61a5053f5c7bc9/65e1ddacc2cc0d921a4caf31_Graph.svg" 
                loading="lazy" 
                alt="" 
                className="icon-size-40 margin-bottom-40"
              />
              <div className="wrapper justify-content">
                <div className="wrapper max-width-420 margin-bottom-32">
                  <h4 className="h4 margin-bottom-16">Acoustic Emotion &amp; SVI Triage</h4>
                  <p className="regular-m">
                    Wav2Vec2 acoustic prosody telemetry (pitch, jitter, pause ratio) computes Stress Vulnerability Index without intrusive interrogation.
                  </p>
                </div>
                <div className="tertiary-button">
                  <div className="regular-m">Learn More</div>
                  <div className="tertiary-button-icon">
                    <img src="https://cdn.prod.website-files.com/65e1c0c2fd61a5053f5c7bc9/65e1ddac852c806c77a38998_Arrow%20Up%20Right.svg" loading="lazy" alt="" className="icon-size-14"/>
                  </div>
                </div>
              </div>
            </Link>

            <Link to="/essential-resources#spatial-dialects" className="block padding-24-32 bg-grey-3 w-inline-block">
              <img 
                src="https://cdn.prod.website-files.com/65e1c0c2fd61a5053f5c7bc9/65e1ddacf8932bbb9febfbe8_Notebook.svg" 
                loading="lazy" 
                alt="" 
                className="icon-size-40 margin-bottom-40"
              />
              <div className="wrapper justify-content">
                <div className="wrapper max-width-420 margin-bottom-32">
                  <h4 className="h4 margin-bottom-16">Spatial Grounding &amp; Tribal Dialects</h4>
                  <p className="regular-m">
                    Zero-hallucination outdoor wilderness guidance. Native normalization for Sambalpuri (Kosli), Santali (Ol Chiki), Odia, and Hindi.
                  </p>
                </div>
                <div className="tertiary-button">
                  <div className="regular-m">Learn More</div>
                  <div className="tertiary-button-icon">
                    <img src="https://cdn.prod.website-files.com/65e1c0c2fd61a5053f5c7bc9/65e1ddac852c806c77a38998_Arrow%20Up%20Right.svg" loading="lazy" alt="" className="icon-size-14"/>
                  </div>
                </div>
              </div>
            </Link>
          </div>
        </div>
      </section>

      {/* Comprehensive Services (3 Image Overlay Blocks) */}
      <section className="section margin-top-176-mobile-144" id="services">
        <div className="w-layout-blockcontainer container w-container">
          <div className="heading-and-button margin-bottom-56">
            <h2 className="h2 max-width-432-mobile-320">Comprehensive Crisis Services</h2>
            <Link to="/contact" className="button secondary small w-button">
              Request Emergency Assistance
            </Link>
          </div>

          <div className="w-layout-grid blocks-grid-3-tablet-1-mobile-1">
            <div className="block service">
              <img 
                src="/images/service_psychological.jpeg" 
                loading="eager" 
                alt="Psychological First Aid" 
                className="service-image"
              />
              <div className="wrapper max-width-420-tablet-560-mobile-420">
                <h4 className="h4 color-white margin-bottom-20">Psychological First Aid</h4>
                <div className="line white margin-bottom-16"></div>
                <p className="regular-m color-white">
                  Trained counsellors and conversational AI stabilize callers experiencing extreme panic, shock, or silence, with direct Tele-MANAS escalation.
                </p>
              </div>
            </div>

            <div className="block service">
              <img 
                src="/images/service_police.jpeg" 
                loading="eager" 
                alt="Legal & Police Protection" 
                className="service-image"
              />
              <div className="wrapper max-width-420-tablet-560-mobile-420">
                <h4 className="h4 color-white margin-bottom-20">Legal &amp; Police Protection</h4>
                <div className="line white margin-bottom-16"></div>
                <p className="regular-m color-white">
                  Provides statutory rights enforcement under the SC/ST PoA Act, Section 15A protection orders, and legal representation through DLSA advocates.
                </p>
              </div>
            </div>

            <div className="block service">
              <img 
                src="/images/service_multilingual.jpeg" 
                loading="eager" 
                alt="Multi-Dialect Crisis Care" 
                className="service-image"
              />
              <div className="wrapper max-width-420-tablet-560-mobile-420">
                <h4 className="h4 color-white margin-bottom-20">Multi-Dialect Crisis Care</h4>
                <div className="line white margin-bottom-16"></div>
                <p className="regular-m color-white">
                  Seamlessly understands callers in their mother tongue—including Kosli Sambalpuri, Santali, Odia, and Hindi—ensuring everyone is understood.
                </p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Active Helpline Intel & News (bg-grey-3) */}
      <section className="section margin-top-176-mobile-144 bg-grey-3" id="intel">
        <div className="w-layout-blockcontainer container w-container">
          <div className="wrapper bg-section-padding">
            <div className="heading-and-button margin-bottom-56">
              <h2 className="h2 max-width-432-mobile-320">Active Helpline Intel &amp; Updates</h2>
              <Link to="/agent" className="button secondary small w-button">
                Start Voice Session
              </Link>
            </div>

            <div className="collection-list-wrapper-type-one w-dyn-list">
              <div role="list" className="collection-list-type-one w-dyn-items">
                <div role="listitem" className="collection-item-type-one w-dyn-item">
                  <Link to="/agent" className="collection-link-block-type-one w-inline-block">
                    <div className="wrapper">
                      <div className="regular-m margin-bottom-12">Emergency Alert</div>
                      <div className="line black"></div>
                    </div>
                    <div className="collection-content-type-one">
                      <div className="collection-image-type-one wrapper">
                        <img 
                          src="/images/police_triage_desk.jpeg" 
                          loading="lazy" 
                          alt="Police PCR 112 Integration" 
                          className="collection-image-type-one image"
                        />
                      </div>
                      <div className="collection-text-type-one">
                        <div className="wrapper collection-date-and-heading padding-right-16-tablet-0 table-max-width-320">
                          <div className="regular-s color-grey-80">Sep 2026</div>
                          <h4 className="h4">Police PCR 112 Integration Live in All 30 Districts</h4>
                        </div>
                        <div className="tertiary-button">
                          <div className="regular-m">Learn More</div>
                          <div className="tertiary-button-icon">
                            <img src="https://cdn.prod.website-files.com/65e1c0c2fd61a5053f5c7bc9/65e1ddac5c1d21f3b536e04f_Arrow%20Right.svg" loading="lazy" alt="" className="icon-size-14"/>
                          </div>
                        </div>
                      </div>
                    </div>
                  </Link>
                </div>

                <div role="listitem" className="collection-item-type-one w-dyn-item">
                  <Link to="/agent" className="collection-link-block-type-one w-inline-block">
                    <div className="wrapper">
                      <div className="regular-m margin-bottom-12">Dialect Coverage</div>
                      <div className="line black"></div>
                    </div>
                    <div className="collection-content-type-one">
                      <div className="collection-image-type-one wrapper">
                        <img 
                          src="/images/tribal_man_phone.png" 
                          loading="lazy" 
                          alt="Sambalpuri and Santali Dialects" 
                          className="collection-image-type-one image"
                        />
                      </div>
                      <div className="collection-text-type-one">
                        <div className="wrapper collection-date-and-heading padding-right-16-tablet-0 table-max-width-320">
                          <div className="regular-s color-grey-80">Aug 2026</div>
                          <h4 className="h4">Sambalpuri &amp; Santali Dialect Normalization Deployed</h4>
                        </div>
                        <div className="tertiary-button">
                          <div className="regular-m">Learn More</div>
                          <div className="tertiary-button-icon">
                            <img src="https://cdn.prod.website-files.com/65e1c0c2fd61a5053f5c7bc9/65e1ddac5c1d21f3b536e04f_Arrow%20Right.svg" loading="lazy" alt="" className="icon-size-14"/>
                          </div>
                        </div>
                      </div>
                    </div>
                  </Link>
                </div>

                <div role="listitem" className="collection-item-type-one w-dyn-item">
                  <Link to="/agent" className="collection-link-block-type-one w-inline-block">
                    <div className="wrapper">
                      <div className="regular-m margin-bottom-12">Mental Health</div>
                      <div className="line black"></div>
                    </div>
                    <div className="collection-content-type-one">
                      <div className="collection-image-type-one wrapper">
                        <img 
                          src="/images/tribal_dancers.jpg" 
                          loading="lazy" 
                          alt="Tele-MANAS Psychological Protocol" 
                          className="collection-image-type-one image"
                        />
                      </div>
                      <div className="collection-text-type-one">
                        <div className="wrapper collection-date-and-heading padding-right-16-tablet-0 table-max-width-320">
                          <div className="regular-s color-grey-80">Jul 2026</div>
                          <h4 className="h4">Tele-MANAS Toll-Free 14416 Psychological Protocol</h4>
                        </div>
                        <div className="tertiary-button">
                          <div className="regular-m">Learn More</div>
                          <div className="tertiary-button-icon">
                            <img src="https://cdn.prod.website-files.com/65e1c0c2fd61a5053f5c7bc9/65e1ddac5c1d21f3b536e04f_Arrow%20Right.svg" loading="lazy" alt="" className="icon-size-14"/>
                          </div>
                        </div>
                      </div>
                    </div>
                  </Link>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Sticky Banners Wrapper (bg-blue, bg-green, bg-purple) */}
      <section className="section margin-top-176-mobile-144">
        <div className="w-layout-blockcontainer container w-container">
          <div className="banners-wrapper">
            <div className="banner-type-one sticky">
              <div className="banner-type-one-content bg-blue">
                <div className="wrapper max-width-880-tablet-640-mobile-480">
                  <p className="banner-heading">22 Indian Languages + Native Sambalpuri &amp; Santali Dialects</p>
                </div>
                <Link to="/agent" className="button primary w-button">Test Language Router</Link>
              </div>
              <div className="banner-type-one-pattern home-one"></div>
            </div>

            <div className="banner-type-one sticky">
              <div className="banner-type-one-content bg-green">
                <div className="wrapper max-width-880-tablet-640-mobile-480">
                  <p className="banner-heading">Zero-Hallucination Spatial Awareness in Forest &amp; Wilderness</p>
                </div>
                <Link to="/agent" className="button primary w-button">Review Safety Rules</Link>
              </div>
              <div className="banner-type-one-pattern home-two"></div>
            </div>

            <div className="banner-type-one sticky">
              <div className="banner-type-one-content bg-purple">
                <div className="wrapper max-width-880-tablet-640-mobile-480">
                  <p className="banner-heading">SBAR Clinical Handoff &amp; Automated 1-Click Police 112 Dispatch</p>
                </div>
                <Link to="/login" className="button primary w-button">Operator Dashboard</Link>
              </div>
              <div className="banner-type-one-pattern home-three"></div>
            </div>
          </div>
        </div>
      </section>
    </>
  );
};
