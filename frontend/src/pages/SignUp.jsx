import React, { useState } from 'react';
import axios from 'axios';
import { Link, useNavigate } from 'react-router-dom';

const SignUp = () => {
    const [name, setName] = useState('');
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(false);
    const navigate = useNavigate();

    const handleSubmit = async (e) => {
        e.preventDefault();
        setLoading(true);
        setError('');

        const formData = new FormData();
        formData.append('name', name);
        formData.append('email', email);
        formData.append('password', password);

        try {
            const res = await axios.post('/signup', formData, {
                headers: { 'Accept': 'application/json' }
            });
            if (res.data.success) {
                navigate(`/verify?email=${encodeURIComponent(email)}`);
            }
        } catch (err) {
            setError(err.response?.data?.error || "Registration failed. Try again.");
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="container" style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '80vh', paddingTop: '80px' }}>
            <div className="glass-card" style={{ padding: '2.5rem', width: '100%', maxWidth: '400px', background: '#ffffff', border: '1px solid var(--card-border)', boxShadow: 'none', borderRadius: '16px' }}>
                <div style={{ textAlign: 'center', marginBottom: '2rem' }}>
                    <img src="/img/logo.png" alt="Logo" style={{ width: '48px', marginBottom: '1rem' }} />
                    <h1>Create Account</h1>
                    <p style={{ color: 'var(--text-secondary)' }}>Get started with IP Intelligence</p>
                </div>

                {error && (
                    <div style={{ background: 'rgba(244, 63, 94, 0.1)', border: '1px solid rgba(244, 63, 94, 0.2)', color: '#f43f5e', padding: '0.75rem', borderRadius: '8px', marginBottom: '1.5rem', fontSize: '0.9em', textAlign: 'center' }}>
                        {error}
                    </div>
                )}

                <form onSubmit={handleSubmit}>
                    <div style={{ marginBottom: '1.25rem' }}>
                        <label style={{ display: 'block', color: 'var(--text-secondary)', marginBottom: '0.5rem', fontSize: '0.9em' }}>Full Name</label>
                        <input
                            type="text"
                            name="name"
                            required
                            placeholder="John Doe"
                            value={name}
                            onChange={(e) => setName(e.target.value)}
                            style={{ width: '100%', padding: '0.75rem', background: 'var(--input-bg)', border: '1px solid var(--card-border)', borderRadius: '8px', color: 'var(--text-primary)', fontFamily: 'inherit', fontSize: '1rem' }}
                        />
                    </div>
                    <div style={{ marginBottom: '1.25rem' }}>
                        <label style={{ display: 'block', color: 'var(--text-secondary)', marginBottom: '0.5rem', fontSize: '0.9em' }}>Email Address</label>
                        <input
                            type="email"
                            name="email"
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
                            name="password"
                            required
                            placeholder="••••••••"
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                            style={{ width: '100%', padding: '0.75rem', background: 'var(--input-bg)', border: '1px solid var(--card-border)', borderRadius: '8px', color: 'var(--text-primary)', fontFamily: 'inherit', fontSize: '1rem' }}
                        />
                    </div>

                    <button type="submit" class="btn-primary" disabled={loading} style={{ width: '100%', justifyContent: 'center', padding: '0.875rem', opacity: loading ? 0.7 : 1 }}>
                        {loading ? 'Creating Account...' : 'Sign Up'}
                    </button>
                </form>

                <div style={{ marginTop: '1.5rem', textAlign: 'center', color: 'var(--text-secondary)', fontSize: '0.9em' }}>
                    Already have an account? <Link to="/signin" style={{ color: 'var(--accent-primary)', textDecoration: 'none', fontWeight: 500 }}>Sign In</Link>
                </div>
            </div>
        </div>
    );
};

export default SignUp;
