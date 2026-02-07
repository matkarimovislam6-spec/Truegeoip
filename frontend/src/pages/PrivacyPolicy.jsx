import React from 'react';
import { Link } from 'react-router-dom';

const sectionStyle = {
    marginBottom: '2.25rem'
};

const h2Style = {
    fontSize: '1.4rem',
    marginBottom: '0.8rem'
};

const pStyle = {
    color: 'var(--text-secondary)',
    lineHeight: 1.75
};

const listStyle = {
    listStyle: 'disc',
    marginLeft: '1.5rem',
    marginTop: '0.8rem',
    color: 'var(--text-secondary)',
    lineHeight: 1.75
};

const tabContainerStyle = {
    display: 'inline-flex',
    background: '#22153a',
    borderRadius: '10px',
    padding: '0.35rem',
    marginBottom: '2rem',
    gap: '0.35rem'
};

const activeTabStyle = {
    color: '#ffffff',
    background: 'rgba(255, 255, 255, 0.12)',
    textDecoration: 'none',
    padding: '0.65rem 1.2rem',
    borderRadius: '8px',
    fontWeight: 600
};

const inactiveTabStyle = {
    color: '#ffffff',
    textDecoration: 'none',
    padding: '0.65rem 1.2rem',
    borderRadius: '8px',
    fontWeight: 500
};

const PrivacyPolicy = () => {
    return (
        <div className="container" style={{ paddingTop: '110px', paddingBottom: '70px', maxWidth: '900px' }}>
            <div style={tabContainerStyle}>
                <Link to="/privacy" style={activeTabStyle}>Privacy</Link>
                <Link to="/terms" style={inactiveTabStyle}>Terms</Link>
            </div>

            <h1 style={{ fontSize: '2.5rem', marginBottom: '0.8rem' }}>Privacy Policy</h1>
            <p style={{ color: 'var(--text-secondary)', marginBottom: '2rem' }}>Last updated: February 6, 2026</p>

            <section style={sectionStyle}>
                <h2 style={h2Style}>1. Scope and Principles</h2>
                <p style={pStyle}>
                    This Privacy Policy explains how IP Intelligence collects, uses, shares, and protects personal data across our website, dashboards, APIs, and support channels.
                    Our privacy program is built on data minimization, purpose limitation, transparency, and accountability.
                </p>
            </section>

            <section style={sectionStyle}>
                <h2 style={h2Style}>2. Data We Collect</h2>
                <p style={pStyle}>We process only the data needed to deliver and secure the service.</p>
                <ul style={listStyle}>
                    <li><strong>Account Data:</strong> name, email, organization, authentication credentials.</li>
                    <li><strong>Billing Data:</strong> subscription status, transaction metadata from payment providers.</li>
                    <li><strong>Service Data:</strong> IP query inputs, API usage metadata, request timestamps, error and latency telemetry.</li>
                    <li><strong>Security Data:</strong> logs and signals used for abuse prevention, fraud detection, and incident response.</li>
                </ul>
            </section>

            <section style={sectionStyle}>
                <h2 style={h2Style}>3. Legal Bases and Regional Compliance</h2>
                <p style={pStyle}>
                    Where required, we rely on lawful bases such as contract performance, legitimate interests, legal obligations, and consent.
                    Our controls are designed to support major frameworks including GDPR and UK GDPR, CCPA/CPRA, Brazil LGPD, Canada PIPEDA, Japan APPI, and Singapore PDPA.
                </p>
            </section>

            <section style={sectionStyle}>
                <h2 style={h2Style}>4. How We Use Data</h2>
                <ul style={listStyle}>
                    <li>Provide geolocation, ASN, and network intelligence services.</li>
                    <li>Maintain platform reliability, uptime, and performance.</li>
                    <li>Prevent abuse, monitor fraud risk, and enforce usage limits.</li>
                    <li>Support customer requests, account administration, and billing operations.</li>
                    <li>Meet legal, regulatory, and contractual obligations.</li>
                </ul>
            </section>

            <section style={sectionStyle}>
                <h2 style={h2Style}>5. Security Standards and Controls</h2>
                <p style={pStyle}>
                    Our security program is aligned with globally recognized control models (including ISO/IEC 27001 concepts, SOC 2 trust principles, and NIST-style risk management).
                    This includes role-based access controls, least privilege, secure development practices, logging and monitoring, vulnerability management, and incident response procedures.
                </p>
            </section>

            <section style={sectionStyle}>
                <h2 style={h2Style}>6. International Transfers</h2>
                <p style={pStyle}>
                    If personal data is transferred across borders, we apply appropriate safeguards such as contractual protections and transfer-risk assessments, as required by applicable law.
                </p>
            </section>

            <section style={sectionStyle}>
                <h2 style={h2Style}>7. Data Retention and Deletion</h2>
                <p style={pStyle}>
                    We retain personal data for the minimum period necessary to provide services, maintain security, resolve disputes, and satisfy legal obligations.
                    After retention periods expire, data is deleted or de-identified where feasible.
                </p>
            </section>

            <section style={sectionStyle}>
                <h2 style={h2Style}>8. Your Rights</h2>
                <p style={pStyle}>Depending on your location, you may have rights to:</p>
                <ul style={listStyle}>
                    <li>Access, correct, delete, or port your data.</li>
                    <li>Object to or restrict specific processing activities.</li>
                    <li>Withdraw consent where processing depends on consent.</li>
                    <li>Opt out of certain disclosures or targeted advertising practices where applicable.</li>
                </ul>
                <p style={{ ...pStyle, marginTop: '0.8rem' }}>
                    To exercise rights requests, contact us at <strong>support@ipintelligence.com</strong>.
                </p>
            </section>

            <section style={sectionStyle}>
                <h2 style={h2Style}>9. Subprocessors and Third Parties</h2>
                <p style={pStyle}>
                    We use vetted subprocessors for infrastructure, monitoring, billing, and support. We require contractual confidentiality and data-protection commitments from those providers.
                    We do not sell personal information.
                </p>
            </section>

            <section style={sectionStyle}>
                <h2 style={h2Style}>10. Contact</h2>
                <p style={pStyle}>
                    Privacy inquiries, incident reports, or data rights requests can be sent to <strong>support@ipintelligence.com</strong>.
                </p>
            </section>
        </div>
    );
};

export default PrivacyPolicy;
