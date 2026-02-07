import React, { useState, useEffect } from 'react';
import { useLocation } from 'react-router-dom';

const Legal = () => {
    const location = useLocation();
    const [activeSection, setActiveSection] = useState('privacy');

    useEffect(() => {
        if (location.hash === '#terms') {
            setActiveSection('terms');
            document.getElementById('terms')?.scrollIntoView({ behavior: 'smooth' });
        } else {
            setActiveSection('privacy');
            window.scrollTo(0, 0);
        }
    }, [location]);

    return (
        <div className="container" style={{ paddingTop: '100px', paddingBottom: '80px' }}>
            <div className="legal-layout" style={{ display: 'grid', gridTemplateColumns: '250px 1fr', gap: '4rem' }}>
                {/* Sidebar */}
                <aside style={{ position: 'sticky', top: '120px', height: 'fit-content' }}>
                    <h3 style={{ marginBottom: '1.5rem', fontSize: '1.2rem', fontWeight: 600 }}>Legal Center</h3>
                    <nav style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                        <button
                            onClick={() => { setActiveSection('privacy'); document.getElementById('privacy').scrollIntoView({ behavior: 'smooth' }); }}
                            style={{
                                textAlign: 'left',
                                background: activeSection === 'privacy' ? 'var(--input-bg)' : 'transparent',
                                border: 'none',
                                padding: '0.75rem 1rem',
                                borderRadius: '8px',
                                cursor: 'pointer',
                                color: activeSection === 'privacy' ? 'var(--accent-primary)' : 'var(--text-secondary)',
                                fontWeight: activeSection === 'privacy' ? 600 : 400,
                                transition: 'all 0.2s'
                            }}
                        >
                            Privacy Policy
                        </button>
                        <button
                            onClick={() => { setActiveSection('terms'); document.getElementById('terms').scrollIntoView({ behavior: 'smooth' }); }}
                            style={{
                                textAlign: 'left',
                                background: activeSection === 'terms' ? 'var(--input-bg)' : 'transparent',
                                border: 'none',
                                padding: '0.75rem 1rem',
                                borderRadius: '8px',
                                cursor: 'pointer',
                                color: activeSection === 'terms' ? 'var(--accent-primary)' : 'var(--text-secondary)',
                                fontWeight: activeSection === 'terms' ? 600 : 400,
                                transition: 'all 0.2s'
                            }}
                        >
                            Terms of Service
                        </button>
                    </nav>
                </aside>

                {/* Content */}
                <div className="legal-content">
                    {/* Privacy Section */}
                    <section id="privacy" style={{ marginBottom: '6rem', scrollMarginTop: '120px' }}>
                        <h1 style={{ fontSize: '2.5rem', marginBottom: '1rem' }}>Privacy Policy</h1>
                        <p style={{ color: 'var(--text-secondary)', marginBottom: '2rem' }}>Last updated: {new Date().toLocaleDateString()}</p>

                        <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
                            <div>
                                <h2 style={{ fontSize: '1.5rem', marginBottom: '1rem' }}>1. Introduction</h2>
                                <p style={{ color: 'var(--text-secondary)', lineHeight: 1.7 }}>
                                    Welcome to IP Intelligence. We are committed to protecting your personal information and your right to privacy.
                                    This Privacy Policy explains how we collect, use, and safeguard your information.
                                </p>
                            </div>
                            <div>
                                <h2 style={{ fontSize: '1.5rem', marginBottom: '1rem' }}>2. Data Collection</h2>
                                <p style={{ color: 'var(--text-secondary)', lineHeight: 1.7 }}>
                                    We collect minimal data necessary to provide our services, including IP addresses of API requests for rate limiting and analytics.
                                </p>
                            </div>
                            <div>
                                <h2 style={{ fontSize: '1.5rem', marginBottom: '1rem' }}>3. Data Usage</h2>
                                <p style={{ color: 'var(--text-secondary)', lineHeight: 1.7 }}>
                                    Your data is used solely to maintain service stability, improve performance, and prevent abuse. We do not sell your personal data to third parties.
                                </p>
                            </div>
                        </div>
                    </section>

                    <hr style={{ border: '0', borderTop: '1px solid var(--card-border)', marginBottom: '6rem' }} />

                    {/* Terms Section */}
                    <section id="terms" style={{ scrollMarginTop: '120px' }}>
                        <h1 style={{ fontSize: '2.5rem', marginBottom: '1rem' }}>Terms of Service</h1>
                        <p style={{ color: 'var(--text-secondary)', marginBottom: '2rem' }}>Last updated: {new Date().toLocaleDateString()}</p>

                        <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
                            <div>
                                <h2 style={{ fontSize: '1.5rem', marginBottom: '1rem' }}>1. Agreement</h2>
                                <p style={{ color: 'var(--text-secondary)', lineHeight: 1.7 }}>
                                    By accessing IP Intelligence, you agree to be bound by these Terms. If you disagree with any part of the terms, you may not access the service.
                                </p>
                            </div>
                            <div>
                                <h2 style={{ fontSize: '1.5rem', marginBottom: '1rem' }}>2. Usage Limits</h2>
                                <p style={{ color: 'var(--text-secondary)', lineHeight: 1.7 }}>
                                    You agree not to abuse the API. Requests are limited based on your subscription tier. Excessive usage may result in temporary or permanent blocking.
                                </p>
                            </div>
                            <div>
                                <h2 style={{ fontSize: '1.5rem', marginBottom: '1rem' }}>3. Disclaimer</h2>
                                <p style={{ color: 'var(--text-secondary)', lineHeight: 1.7 }}>
                                    The service is provided "AS IS" without warranties of any kind. We utilize best-effort data sources but cannot guarantee 100% accuracy of IP geolocation data.
                                </p>
                            </div>
                        </div>
                    </section>
                </div>
            </div>
        </div>
    );
};

export default Legal;
