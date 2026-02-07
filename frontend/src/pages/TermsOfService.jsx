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

const TermsOfService = () => {
    return (
        <div className="container" style={{ paddingTop: '110px', paddingBottom: '70px', maxWidth: '900px' }}>
            <div style={tabContainerStyle}>
                <Link to="/privacy" style={inactiveTabStyle}>Privacy</Link>
                <Link to="/terms" style={activeTabStyle}>Terms</Link>
            </div>

            <h1 style={{ fontSize: '2.5rem', marginBottom: '0.8rem' }}>Terms of Service</h1>
            <p style={{ color: 'var(--text-secondary)', marginBottom: '2rem' }}>Last updated: February 6, 2026</p>

            <section style={sectionStyle}>
                <h2 style={h2Style}>1. Acceptance of Terms</h2>
                <p style={pStyle}>
                    By accessing or using IP Intelligence, you agree to these Terms of Service and all applicable laws.
                    If you use the service on behalf of an organization, you confirm authority to bind that organization.
                </p>
            </section>

            <section style={sectionStyle}>
                <h2 style={h2Style}>2. Service Description</h2>
                <p style={pStyle}>
                    IP Intelligence provides API and dashboard services for IP geolocation, ASN enrichment, and related analytics.
                    Data is provided on a best-effort basis and may vary by source quality, internet routing behavior, or regulatory constraints.
                </p>
            </section>

            <section style={sectionStyle}>
                <h2 style={h2Style}>3. Privacy and Data Protection Commitments</h2>
                <p style={pStyle}>
                    Our processing practices are described in the Privacy Policy. We maintain a security and privacy program designed to align with globally recognized frameworks
                    and customer expectations for enterprise controls, including governance, access control, logging, and incident handling.
                </p>
            </section>

            <section style={sectionStyle}>
                <h2 style={h2Style}>4. Customer Responsibilities</h2>
                <ul style={listStyle}>
                    <li>Use the services lawfully and in compliance with applicable privacy and export laws.</li>
                    <li>Maintain account credential security and promptly report unauthorized access.</li>
                    <li>Avoid processing unlawful or prohibited content through the API.</li>
                    <li>Provide notices and legal bases required for your own downstream processing activities.</li>
                </ul>
            </section>

            <section style={sectionStyle}>
                <h2 style={h2Style}>5. Acceptable Use and Abuse Prevention</h2>
                <p style={pStyle}>
                    You must not attempt unauthorized access, interfere with platform availability, perform denial-of-service behavior, reverse engineer private systems, or bypass rate limits.
                    We may throttle, suspend, or terminate abusive traffic to protect platform integrity.
                </p>
            </section>

            <section style={sectionStyle}>
                <h2 style={h2Style}>6. Subscriptions, Billing, and Suspension</h2>
                <p style={pStyle}>
                    Paid plans renew as agreed during purchase unless canceled in advance. Non-payment, fraud risk, or material policy violations may result in temporary suspension or account termination.
                </p>
            </section>

            <section style={sectionStyle}>
                <h2 style={h2Style}>7. Intellectual Property</h2>
                <p style={pStyle}>
                    The platform, branding, software, and documentation are protected by intellectual property laws. Except for limited use rights granted by your plan,
                    no ownership rights are transferred to you.
                </p>
            </section>

            <section style={sectionStyle}>
                <h2 style={h2Style}>8. Warranties and Liability Limits</h2>
                <p style={pStyle}>
                    The services are provided "as is" and "as available." To the maximum extent permitted by law, we disclaim implied warranties and are not liable for indirect, incidental,
                    special, consequential, or punitive damages, including loss of profits, data, or goodwill.
                </p>
            </section>

            <section style={sectionStyle}>
                <h2 style={h2Style}>9. Regulatory and International Use</h2>
                <p style={pStyle}>
                    You are responsible for ensuring your use complies with regional laws applicable to your organization, including sector-specific rules and cross-border transfer obligations.
                    If you require additional contractual protections, contact us regarding a data processing addendum.
                </p>
            </section>

            <section style={sectionStyle}>
                <h2 style={h2Style}>10. Changes and Contact</h2>
                <p style={pStyle}>
                    We may update these terms from time to time. Material changes will be published on this page with an updated effective date.
                    Questions about these terms can be sent to <strong>support@ipintelligence.com</strong>.
                </p>
            </section>
        </div>
    );
};

export default TermsOfService;
