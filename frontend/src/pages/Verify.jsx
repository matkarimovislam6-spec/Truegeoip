import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { useSearchParams, Link } from 'react-router-dom';

const Verify = () => {
    const [searchParams] = useSearchParams();
    const [email, setEmail] = useState(searchParams.get('email') || '');
    const [code, setCode] = useState('');
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(false);

    const handleSubmit = async (e) => {
        e.preventDefault();
        setLoading(true);
        setError('');

        const formData = new FormData();
        formData.append('email', email);
        formData.append('code', code);

        try {
            const res = await axios.post('/verify', formData, {
                headers: { 'Accept': 'application/json' }
            });
            if (res.data.success) {
                // Hard reload to refresh Navbar state
                window.location.href = '/';
            }
        } catch (err) {
            setError(err.response?.data?.error || "Invalid verification code.");
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="container" style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '80vh', paddingTop: '80px' }}>
            <div className="glass-card" style={{ padding: '2.5rem', width: '100%', maxWidth: '400px', background: '#ffffff', border: '1px solid var(--card-border)', boxShadow: 'none', borderRadius: '16px' }}>
                <div style={{ textAlign: 'center', marginBottom: '2rem' }}>
                    <div style={{ width: '64px', height: '64px', background: 'rgba(16, 185, 129, 0.1)', color: '#10b981', borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '1.5rem', margin: '0 auto 1rem auto' }}>
                        <i className="fas fa-envelope"></i>
                    </div>
                    <h1>Verify Email</h1>
                    <p style={{ color: 'var(--text-secondary)' }}>Enter the code sent to your email</p>
                </div>

                {error && (
                    <div style={{ background: 'rgba(244, 63, 94, 0.1)', border: '1px solid rgba(244, 63, 94, 0.2)', color: '#f43f5e', padding: '0.75rem', borderRadius: '8px', marginBottom: '1.5rem', fontSize: '0.9em', textAlign: 'center' }}>
                        {error}
                    </div>
                )}

                <form onSubmit={handleSubmit}>
                    <div style={{ marginBottom: '1.25rem' }}>
                        <label style={{ display: 'block', color: 'var(--text-secondary)', marginBottom: '0.5rem', fontSize: '0.9em' }}>Email Address</label>
                        <input
                            type="email"
                            name="email"
                            required
                            value={email}
                            onChange={(e) => setEmail(e.target.value)}
                            // readOnly
                            style={{ width: '100%', padding: '0.75rem', background: 'var(--input-bg)', border: '1px solid var(--card-border)', borderRadius: '8px', color: 'var(--text-primary)', fontFamily: 'inherit', fontSize: '1rem' }}
                        />
                    </div>

                    <div style={{ marginBottom: '1.5rem' }}>
                        <label style={{ display: 'block', color: 'var(--text-secondary)', marginBottom: '0.5rem', fontSize: '0.9em' }}>Verification Code</label>
                        <input
                            type="text"
                            name="code"
                            required
                            placeholder="123456"
                            value={code}
                            onChange={(e) => setCode(e.target.value)}
                            style={{ width: '100%', padding: '0.75rem', background: 'var(--input-bg)', border: '1px solid var(--card-border)', borderRadius: '8px', color: 'var(--text-primary)', fontFamily: 'inherit', fontSize: '1rem', letterSpacing: '0.2em', textAlign: 'center', fontWeight: 'bold' }}
                        />
                    </div>

                    <button type="submit" class="btn-primary" disabled={loading} style={{ width: '100%', justifyContent: 'center', padding: '0.875rem', opacity: loading ? 0.7 : 1 }}>
                        {loading ? 'Verifying...' : 'Verify Email'}
                    </button>
                </form>

                <div style={{ marginTop: '1.5rem', textAlign: 'center', color: 'var(--text-secondary)', fontSize: '0.9em' }}>
                    <Link to="/signin" style={{ color: 'var(--text-secondary)', textDecoration: 'none' }}>Back to Sign In</Link>
                </div>
            </div>
        </div>
    );
};

export default Verify;
