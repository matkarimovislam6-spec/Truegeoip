import React, { useState, useEffect } from 'react';
import { Link, NavLink } from 'react-router-dom';
import axios from 'axios';

const Navbar = () => {
    const [user, setUser] = useState(null);
    const [scrolled, setScrolled] = useState(false);

    useEffect(() => {
        axios.get('/api/user')
            .then(res => setUser(res.data))
            .catch(() => setUser(null));
    }, []);

    useEffect(() => {
        const handleScroll = () => {
            setScrolled(window.scrollY > 10);
        };
        window.addEventListener('scroll', handleScroll);
        return () => window.removeEventListener('scroll', handleScroll);
    }, []);

    return (
        <nav className={`navbar ${scrolled ? 'scrolled' : ''}`}>
            <div className="nav-container">
                <div className="logo">
                    <Link to="/" style={{ textDecoration: 'none', color: 'inherit', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                        <img src="/img/logo.png" alt="IP Intelligence Logo" style={{ height: '32px', width: 'auto' }} />
                        IP Intelligence
                    </Link>
                </div>
                <div className="nav-links">
                    <a href="/#features">Features</a>
                    <a href="/#api">API</a>
                    <Link to="/dashboard">Analytics</Link>
                    <NavLink to="/pricing" className={({ isActive }) => isActive ? "active" : ""}>Pricing</NavLink>
                    <NavLink to="/contact" className={({ isActive }) => isActive ? "active" : ""}>Contact</NavLink>
                </div>

                {user ? (
                    <div className="profile-menu">
                        <a href="#" className="profile-avatar-btn">{user.name ? user.name[0] : 'U'}</a>
                        <div className="profile-dropdown">
                            <div className="dropdown-header">
                                <div className="dropdown-header-avatar">{user.name ? user.name[0] : 'U'}</div>
                                <div className="dropdown-header-info">
                                    <div className="dropdown-header-name">{user.name}</div>
                                    <div className="dropdown-header-email">{user.email}</div>
                                </div>
                            </div>
                            <div className="dropdown-section">
                                <a href="/profile" className="dropdown-item">
                                    <i className="fas fa-user"></i> Profile
                                </a>
                                <a href="#" className="dropdown-item">
                                    <i className="fas fa-key"></i> API Keys
                                </a>
                                <a href="/billing" className="dropdown-item">
                                    <i className="fas fa-credit-card"></i> Billing
                                </a>
                                <a href="#" className="dropdown-item">
                                    <i className="fas fa-cog"></i> Settings
                                </a>
                            </div>
                            <div className="dropdown-divider"></div>
                            <div className="dropdown-section">
                                <a href="/signout" className="dropdown-item danger">
                                    <i className="fas fa-sign-out-alt"></i> Sign Out
                                </a>
                            </div>
                        </div>
                    </div>
                ) : (
                    <div style={{ display: 'flex', gap: '0.75rem' }}>
                        <Link to="/signin" style={{ color: 'var(--text-secondary)', textDecoration: 'none', fontWeight: 500, display: 'flex', alignItems: 'center' }}>
                            Sign In
                        </Link>
                        <Link to="/signup" className="btn-primary">Get Started</Link>
                    </div>
                )}
            </div>
        </nav>
    );
};

export default Navbar;
