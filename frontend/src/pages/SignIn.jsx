import React, { useState } from 'react';
import axios from 'axios';
import { Link } from 'react-router-dom';

const SignIn = () => {
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(false);

    const handleSubmit = async (e) => {
        e.preventDefault();
        setLoading(true);
        setError('');

        const formData = new FormData();
        formData.append('email', email);
        formData.append('password', password);

        try {
            const res = await axios.post('/signin', formData, {
                headers: { 'Accept': 'application/json' }
            });
            if (res.data.success) {
                // Hard reload to refresh Navbar state (simplest for migration)
                window.location.href = '/';
            }
        } catch (err) {
            setError(err.response?.data?.error || "Invalid credentials or server error");
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="container" style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '80vh', paddingTop: '80px' }}>
            <div className="glass-card" style={{ padding: '2.5rem', width: '100%', maxWidth: '400px', background: '#ffffff', border: '1px solid var(--card-border)', boxShadow: 'none', borderRadius: '16px' }}>
                <div style={{ textAlign: 'center', marginBottom: '2rem' }}>
                    <img src="/img/logo.png" alt="Logo" style={{ width: '48px', marginBottom: '1rem' }} />
                    <h1>Welcome Back</h1>
                    <p style={{ color: 'var(--text-secondary)' }}>Sign in to your account</p>
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
                            required
                            placeholder="name@company.com"
                            value={email}
                            onChange={(e) => setEmail(e.target.value)}
                            style={{ width: '100%', padding: '0.75rem', background: 'var(--input-bg)', border: '1px solid var(--card-border)', borderRadius: '8px', color: 'var(--text-primary)', fontFamily: 'inherit', fontSize: '1rem' }}
                        />
                    </div>

                    <div style={{ marginBottom: '1.5rem' }}>
                        <label style={{ display: 'block', color: 'var(--text-secondary)', marginBottom: '0.5rem', fontSize: '0.9em' }}>Password</label>
                        <input
                            type="password"
                            required
                            placeholder="••••••••"
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                            style={{ width: '100%', padding: '0.75rem', background: 'var(--input-bg)', border: '1px solid var(--card-border)', borderRadius: '8px', color: 'var(--text-primary)', fontFamily: 'inherit', fontSize: '1rem' }}
                        />
                    </div>

                    <button type="submit" class="btn-primary" disabled={loading} style={{ width: '100%', justifyContent: 'center', padding: '0.875rem', opacity: loading ? 0.7 : 1 }}>
                        {loading ? 'Signing In...' : 'Sign In'}
                    </button>
                </form>

                <div style={{ marginTop: '1.5rem', textAlign: 'center', color: 'var(--text-secondary)', fontSize: '0.9em' }}>
                    Don't have an account? <Link to="/signup" style={{ color: 'var(--accent-primary)', textDecoration: 'none', fontWeight: 500 }}>Sign Up</Link>
                </div>

                <div style={{ position: 'relative', margin: '2rem 0', textAlign: 'center' }}>
                    <hr style={{ border: 0, borderTop: '1px solid var(--card-border)' }} />
                    <span style={{ position: 'absolute', top: '-10px', left: '50%', transform: 'translateX(-50%)', background: '#ffffff', padding: '0 0.75rem', color: 'var(--text-secondary)', fontSize: '0.85em' }}>OR</span>
                </div>

                <a href="/auth/google" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.75rem', width: '100%', padding: '0.875rem', background: 'white', color: 'var(--text-primary)', border: '1px solid var(--card-border)', borderRadius: '8px', textDecoration: 'none', fontWeight: 500, transition: 'all 0.2s' }}>
                    <img src="https://www.svgrepo.com/show/475656/google-color.svg" alt="Google" style={{ width: '20px', height: '20px' }} />
                    Sign in with Google
                </a>
            </div>
        </div>
    );
};

export default SignIn;
