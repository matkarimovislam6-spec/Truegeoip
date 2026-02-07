import React, { useState } from 'react';

const Pricing = () => {
    const [category, setCategory] = useState('api');

    return (
        <>
            <section className="pricing-hero">
                <div className="container">
                    <h1>Simple, transparent <span className="gradient-text">Pricing</span></h1>
                    <p className="pricing-subtitle">Choose the perfect solution for your needs. Database for offline access, API for
                        real-time lookups.</p>

                    <div className="category-toggle">
                        <button
                            className={`category-btn ${category === 'api' ? 'active' : ''}`}
                            onClick={() => setCategory('api')}
                        >
                            <i className="fas fa-code"></i> API
                        </button>
                        <button
                            className={`category-btn ${category === 'database' ? 'active' : ''}`}
                            onClick={() => setCategory('database')}
                        >
                            <i className="fas fa-database"></i> Databases
                        </button>
                    </div>
                </div>
            </section>

            <section className="pricing-section">
                <div className="container">

                    {category === 'database' && (
                        <div className="category-content active fade-in">
                            <div className="database-hero">
                                <h2>IP Geolocation <span className="gradient-text">Database</span></h2>
                                <p className="pricing-subtitle" style={{ marginBottom: 0 }}>Download the complete database for local
                                    integration. No API calls, no latency, full control.</p>
                            </div>

                            <div className="pricing-grid grid-2-cols">
                                {/* Combined Plan */}
                                <div className="pricing-card popular">
                                    <div className="popular-badge">Most Flexible</div>

                                    <style>{`
                                        .old-price-banner {
                                            position: relative;
                                            display: inline-flex;
                                            align-items: center;
                                            justify-content: center;
                                            gap: 0.25rem;
                                            padding: 0.15rem 0.9rem 0.2rem;
                                            background: #0b0b0b;
                                            border-radius: 999px;
                                            color: #ffffff;
                                            margin-bottom: 0.35rem;
                                            font-weight: 700;
                                            letter-spacing: 0.01em;
                                        }

                                        .old-price-banner .old-price {
                                            font-size: 1.35rem;
                                            line-height: 1.2;
                                        }

                                        .old-price-banner .old-price span {
                                            font-size: 0.9rem;
                                            opacity: 0.8;
                                        }

                                        .old-price-banner::after {
                                            content: "";
                                            position: absolute;
                                            left: -6%;
                                            top: 58%;
                                            width: 112%;
                                            height: 4px;
                                            background: var(--accent-secondary);
                                            border-radius: 4px;
                                            transform: rotate(-6deg);
                                            opacity: 0.95;
                                            box-shadow: none;
                                        }

                                        .deal-price {
                                            color: var(--accent-secondary) !important;
                                            font-weight: 800 !important;
                                            text-shadow: none;
                                        }
                                    `}</style>

                                    <div className="plan-header">
                                        <h3>One-Time Purchase</h3>
                                        <div className="price">$599</div>
                                        <p className="plan-desc">Pay once for full database access.</p>
                                    </div>
                                    <ul className="features-list">
                                        <li><i className="fas fa-check" style={{ color: 'var(--text-primary)' }}></i> One-time payment</li>
                                        <li><i className="fas fa-check" style={{ color: 'var(--text-primary)' }}></i> Full Database Access</li>
                                        <li><i className="fas fa-check" style={{ color: 'var(--text-primary)' }}></i> SQLite Format</li>
                                        <li><i className="fas fa-check" style={{ color: 'var(--text-primary)' }}></i> Priority Support</li>
                                        <li><i className="fas fa-check" style={{ color: 'var(--text-primary)' }}></i> No recurring billing</li>
                                    </ul>
                                    <a href="/start-checkout?plan=db_onetime" className="btn-primary full-width">Buy One-Time Purchase</a>
                                </div>

                                {/* Annual License */}
                                <div className="pricing-card">
                                    <div className="plan-header">
                                        <h3>Annual License</h3>
                                        <div className="price">$999<span>/yr</span></div>
                                        <p className="plan-desc">Monthly updates included.</p>
                                    </div>
                                    <ul className="features-list">
                                        <li><i className="fas fa-check" style={{ color: 'var(--text-primary)' }}></i> <strong>Monthly Updates</strong> included</li>
                                        <li><i className="fas fa-check" style={{ color: 'var(--text-primary)' }}></i> Full Database Access</li>
                                        <li><i className="fas fa-check" style={{ color: 'var(--text-primary)' }}></i> Annual Usage License</li>
                                        <li><i className="fas fa-check" style={{ color: 'var(--text-primary)' }}></i> SQLite Format</li>
                                        <li><i className="fas fa-check" style={{ color: 'var(--text-primary)' }}></i> Business Support</li>
                                    </ul>
                                    <a href="/start-checkout?plan=db_license" className="btn-secondary full-width">Get Annual License</a>
                                </div>
                            </div>

                            <div style={{ marginTop: '4rem', marginBottom: '2rem', textAlign: 'center' }}>
                                <p style={{ color: 'var(--text-secondary)', marginBottom: '2rem' }}>All database plans include:</p>
                                <div className="database-features"
                                    style={{ maxWidth: '800px', margin: '0 auto', display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '1rem', textAlign: 'left' }}>
                                    <li><i className="fas fa-check" style={{ color: 'var(--text-primary)' }}></i> 5.4M+ IP ranges</li>
                                    <li><i className="fas fa-check" style={{ color: 'var(--text-primary)' }}></i> City-level accuracy</li>
                                    <li><i className="fas fa-check" style={{ color: 'var(--text-primary)' }}></i> ASN & Carrier data</li>
                                    <li><i className="fas fa-check" style={{ color: 'var(--text-primary)' }}></i> Elevation data</li>
                                    <li><i className="fas fa-check" style={{ color: 'var(--text-primary)' }}></i> VPN checks</li>
                                    <li><i className="fas fa-check" style={{ color: 'var(--text-primary)' }}></i> Unlimited queries</li>
                                </div>
                            </div>
                        </div>
                    )}

                    {category === 'api' && (
                        <div className="category-content active fade-in">
                            <div className="pricing-grid">
                                {/* Free */}
                                <div className="pricing-card">
                                    <div className="plan-header">
                                        <h3>Free</h3>
                                        <div className="price">$0<span>/mo</span></div>
                                        <p className="plan-desc">Perfect for hobbyists and testing.</p>
                                    </div>
                                    <ul className="features-list">
                                        <li><i className="fas fa-check" style={{ color: 'var(--text-primary)' }}></i> 100 requests / day</li>
                                        <li><i className="fas fa-check" style={{ color: 'var(--text-primary)' }}></i> Basic IP Geolocation</li>
                                        <li><i className="fas fa-check" style={{ color: 'var(--text-primary)' }}></i> Community Support</li>
                                        <li><i className="fas fa-times-circle" style={{ color: 'var(--error-fg)' }}></i> ASN Data</li>
                                        <li><i className="fas fa-times-circle" style={{ color: 'var(--error-fg)' }}></i> VPN Detection</li>
                                    </ul>
                                    <a href="/start-checkout?plan=free" className="btn-secondary full-width">Get Started</a>
                                </div>

                                {/* Starter */}
                                <div className="pricing-card popular">
                                    <div className="popular-badge">Most Popular</div>
                                    <div className="plan-header">
                                        <h3>Starter</h3>
                                        <div className="price">$7<span>/mo</span></div>
                                        <p className="plan-desc">For small apps and websites.</p>
                                    </div>
                                    <ul className="features-list">
                                        <li><i className="fas fa-check" style={{ color: 'var(--text-primary)' }}></i> 50,000 requests / month</li>
                                        <li><i className="fas fa-check" style={{ color: 'var(--text-primary)' }}></i> Includes: <code>ip_type</code>, <code>user_type</code>, <code>continent</code></li>
                                        <li><i className="fas fa-check" style={{ color: 'var(--text-primary)' }}></i> Includes: <code>country_code</code>, <code>country_name</code>, <code>is_eu</code></li>
                                        <li><i className="fas fa-check" style={{ color: 'var(--text-primary)' }}></i> Includes: <code>is_datacenter</code>, <code>netname</code></li>
                                        <li><i className="fas fa-check" style={{ color: 'var(--text-primary)' }}></i> Includes: <code>city</code>, <code>region</code>, <code>time_zone</code></li>
                                        <li><i className="fas fa-check" style={{ color: 'var(--text-primary)' }}></i> Includes: <code>lat/lon</code></li>
                                    </ul>
                                    <a href="/start-checkout?plan=start" className="btn-primary full-width">Start Free Trial</a>
                                </div>

                                {/* Pro */}
                                <div className="pricing-card">
                                    <div className="plan-header">
                                        <h3>Pro</h3>
                                        <div className="price">$15<span>/mo</span></div>
                                        <p className="plan-desc">For scaling businesses.</p>
                                    </div>
                                    <ul className="features-list">
                                        <li><i className="fas fa-check" style={{ color: 'var(--text-primary)' }}></i> 500,000 requests / month</li>
                                        <li><i className="fas fa-check" style={{ color: 'var(--text-primary)' }}></i> Everything in Starter</li>
                                        <li><i className="fas fa-check" style={{ color: 'var(--text-primary)' }}></i> Adds: <code>asn</code>, <code>asn_name</code>, <code>zip_code</code>, <code>elevation</code></li>
                                        <li><i className="fas fa-check" style={{ color: 'var(--text-primary)' }}></i> Adds: <code>utc_offset</code>, VPN detection, crawler detection</li>
                                        <li><i className="fas fa-check" style={{ color: 'var(--text-primary)' }}></i> Adds: <code>currency_code</code>, <code>currency_name</code></li>
                                    </ul>
                                    <a href="/start-checkout?plan=pro" className="btn-secondary full-width">Upgrade to Pro</a>
                                </div>

                                {/* Max */}
                                <div className="pricing-card" style={{ boxShadow: '0 0 0 2px var(--accent-secondary)', borderColor: 'transparent' }}>
                                    <div className="popular-badge" style={{ background: 'var(--accent-secondary)' }}>Best Value</div>
                                    <div className="plan-header">
                                        <h3>Max</h3>
                                        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                                            <div className="old-price-banner">
                                                <span className="old-price">$39.99<span>/mo</span></span>
                                            </div>
                                            <div className="price deal-price">$25<span>/mo</span></div>
                                        </div>
                                        <p className="plan-desc">Special deal for this month!</p>
                                    </div>
                                    <ul className="features-list">
                                        <li><i className="fas fa-check" style={{ color: 'var(--text-primary)' }}></i> 2,000,000 requests / month</li>
                                        <li><i className="fas fa-check" style={{ color: 'var(--text-primary)' }}></i> Everything in Pro</li>
                                        <li><i className="fas fa-check" style={{ color: 'var(--text-primary)' }}></i> Higher request limit</li>
                                        <li><i className="fas fa-check" style={{ color: 'var(--text-primary)' }}></i> Bulk endpoint</li>
                                    </ul>
                                    <a href="/start-checkout?plan=max" className="btn-primary full-width" style={{ background: 'var(--accent-secondary)' }}>Upgrade to Max</a>
                                </div>

                                {/* Enterprise */}
                                <div className="pricing-card" style={{ opacity: 0.8, borderStyle: 'dashed' }}>
                                    <div className="popular-badge" style={{ background: 'var(--text-secondary)', letterSpacing: '0.1em' }}>Coming Soon</div>
                                    <div className="plan-header">
                                        <h3>Enterprise</h3>
                                        <div className="price">Custom</div>
                                        <p className="plan-desc">Volume discounts & dedicated support.</p>
                                    </div>
                                    <ul className="features-list">
                                        <li><i className="fas fa-check" style={{ color: 'var(--text-primary)' }}></i> Unlimited requests</li>
                                        <li><i className="fas fa-check" style={{ color: 'var(--text-primary)' }}></i> Dedicated Account Manager</li>
                                        <li><i className="fas fa-check" style={{ color: 'var(--text-primary)' }}></i> Custom Contracts</li>
                                        <li><i className="fas fa-check" style={{ color: 'var(--text-primary)' }}></i> 24/7 Phone Support</li>
                                        <li><i className="fas fa-check" style={{ color: 'var(--text-primary)' }}></i> On-premise option</li>
                                    </ul>
                                    <button className="btn-secondary full-width" disabled style={{ cursor: 'not-allowed', opacity: 0.6 }}>Notify Me</button>
                                </div>
                            </div>
                        </div>
                    )}
                </div>
            </section>

            {/* FAQ Section */}
            <section className="faq-section">
                <div className="container">
                    <h2>Frequently Asked <span className="gradient-text">Questions</span></h2>
                    <div className="faq-grid">
                        <div className="faq-item">
                            <h4>What's the difference between Database and API?</h4>
                            <p>The Database is a one-time download for local/offline use with zero latency. The API provides
                                real-time lookups with automatic updates.</p>
                        </div>
                        <div className="faq-item">
                            <h4>How often is the database updated?</h4>
                            <p>The database receives weekly updates. As a lifetime customer, you get access to all future
                                updates at no extra cost.</p>
                        </div>
                        <div className="faq-item">
                            <h4>Can I switch between plans?</h4>
                            <p>Yes, you can upgrade or downgrade your API plan at any time. Changes take effect on your next
                                billing cycle.</p>
                        </div>
                        <div className="faq-item">
                            <h4>Do you offer refunds?</h4>
                            <p>We offer a 7-day money-back guarantee for both database purchases and API subscriptions.</p>
                        </div>
                    </div>
                </div>
            </section>
        </>
    );
};

export default Pricing;
