import React from 'react';

const Contact = () => {
    return (
        <section className="hero" style={{ minHeight: '80vh', display: 'flex', alignItems: 'center' }}>
            <div className="hero-bg"></div>
            <div className="container">
                <div style={{ maxWidth: '800px', margin: '0 auto', textAlign: 'center' }}>
                    <h1 style={{ marginBottom: '1rem' }}>Get in Touch with <span className="gradient-text">MarioSolutions</span></h1>
                    <p className="hero-subtitle" style={{ marginBottom: '3rem' }}>
                        We are here to help you with your IP intelligence needs.
                    </p>

                    <div className="glass-card" style={{ textAlign: 'left', padding: '2.5rem', maxWidth: '500px', margin: '0 auto', background: '#ffffff', border: '1px solid var(--card-border)', boxShadow: 'none', borderRadius: '16px' }}>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>

                            {/* Email */}
                            <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                                <div style={{ width: '50px', height: '50px', background: 'rgba(59, 130, 246, 0.1)', borderRadius: '12px', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-primary)' }}>
                                    <i className="fas fa-envelope fa-lg"></i>
                                </div>
                                <div>
                                    <div style={{ fontSize: '0.9em', color: 'var(--text-secondary)', marginBottom: '0.2rem' }}>Email</div>
                                    <a href="mailto:matkarimovislam6@gmail.com" style={{ color: 'var(--text-primary)', textDecoration: 'none', fontWeight: 500, fontSize: '1.1em' }}>
                                        matkarimovislam6@gmail.com
                                    </a>
                                </div>
                            </div>

                            {/* Telegram */}
                            <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                                <div style={{ width: '50px', height: '50px', background: 'var(--badge-bg)', borderRadius: '12px', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--accent-primary)' }}>
                                    <i className="fab fa-telegram fa-lg"></i>
                                </div>
                                <div>
                                    <div style={{ fontSize: '0.9em', color: 'var(--text-secondary)', marginBottom: '0.2rem' }}>Telegram</div>
                                    <a href="https://t.me/truegeoip" target="_blank" rel="noopener noreferrer" style={{ color: 'var(--text-primary)', textDecoration: 'none', fontWeight: 500, fontSize: '1.1em' }}>
                                        @truegeoip
                                    </a>
                                </div>
                            </div>


                        </div>
                    </div>
                </div>
            </div>
        </section>
    );
};

export default Contact;
