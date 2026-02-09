import React from 'react';
import { Link } from 'react-router-dom';

const Footer = () => {
    return (
        <footer>
            <div className="container footer-content">
                <p>&copy; 2026 True Geo IP.</p>
                <div className="footer-links">
                    <Link to="/privacy">Privacy</Link>
                    <Link to="/terms">Terms</Link>
                    <Link to="/contact">Contact</Link>
                </div>
            </div>
        </footer>
    );
};

export default Footer;
