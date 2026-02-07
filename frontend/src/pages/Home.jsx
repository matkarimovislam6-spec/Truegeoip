import React, { useState, useEffect, useRef } from 'react';
import { Link } from 'react-router-dom';
import MapComponent from '../components/MapComponent';
import axios from 'axios';

const Home = () => {
    const [ip, setIp] = useState('');
    const [loading, setLoading] = useState(false);
    const [result, setResult] = useState(null);
    const [error, setError] = useState('');
    const [latency, setLatency] = useState(null);

    // Laptop Animation Refs
    const laptopRef = useRef(null);
    const [lidAngle, setLidAngle] = useState(96); // 0 = open, 96 = mostly closed

    // Default location (or detected)
    const [mapData, setMapData] = useState({
        lat: 20,
        lng: 0,
        city: '',
        region: '',
        country: '',
        zoom: 2,
        info: 'Location Unknown',
        sub: 'Detecting...'
    });

    // Auto-detect IP on load
    useEffect(() => {
        const detectIp = async () => {
            try {
                setLoading(true);
                let clientIp = '';
                try {
                    const res = await axios.get('https://api.ipify.org?format=json');
                    clientIp = res.data.ip;
                } catch (e) {
                    console.warn("External IP fetch failed", e);
                }

                if (clientIp) {
                    setIp(clientIp);
                    performCheck(clientIp);
                } else {
                    setLoading(false);
                }
            } catch (err) {
                setLoading(false);
            }
        };

        detectIp();
    }, []);

    // Scroll Animation Logic for Laptop
    useEffect(() => {
        const CLOSED_ANGLE = 96;
        const OPEN_ZONE = 0.42;
        const LERP = 0.14;
        const currentAngle = { value: CLOSED_ANGLE };
        const targetAngle = { value: CLOSED_ANGLE };
        let rafId = null;

        const clamp = (v, min, max) => Math.max(min, Math.min(max, v));

        const computeTargetAngle = () => {
            if (!laptopRef.current) return CLOSED_ANGLE;

            const rect = laptopRef.current.getBoundingClientRect();
            const viewportH = window.innerHeight;
            const viewportCenter = viewportH / 2;
            const laptopCenter = rect.top + rect.height / 2;
            const distanceFromCenter = Math.abs(laptopCenter - viewportCenter);

            // Close near top/bottom, open when laptop is centered in viewport.
            const centeredOpen = 1 - clamp(distanceFromCenter / (viewportH * OPEN_ZONE), 0, 1);

            // Fade closed when laptop starts leaving viewport.
            const visiblePx = Math.min(rect.bottom, viewportH) - Math.max(rect.top, 0);
            const visibleRatio = clamp(visiblePx / rect.height, 0, 1);

            const openAmount = centeredOpen * visibleRatio;
            return CLOSED_ANGLE * (1 - openAmount);
        };

        const animate = () => {
            const diff = targetAngle.value - currentAngle.value;
            currentAngle.value += diff * LERP;
            setLidAngle(currentAngle.value);

            if (Math.abs(diff) > 0.08) {
                rafId = window.requestAnimationFrame(animate);
            } else {
                currentAngle.value = targetAngle.value;
                setLidAngle(targetAngle.value);
                rafId = null;
            }
        };

        const syncTarget = () => {
            targetAngle.value = computeTargetAngle();
            if (rafId === null) {
                rafId = window.requestAnimationFrame(animate);
            }
        };

        const handleScroll = () => {
            syncTarget();
        };

        window.addEventListener('scroll', handleScroll);
        window.addEventListener('resize', handleScroll);
        // Initial check
        handleScroll();
        return () => {
            window.removeEventListener('scroll', handleScroll);
            window.removeEventListener('resize', handleScroll);
            if (rafId !== null) {
                window.cancelAnimationFrame(rafId);
            }
        };
    }, []);

    const performCheck = async (searchIp) => {
        if (!searchIp) return;

        setLoading(true);
        setError('');
        setResult(null);
        setLatency(null);

        try {
            const startTime = performance.now();
            const res = await axios.get(`/api/check?ip=${searchIp}`);
            const endTime = performance.now();
            setLatency(Math.round(endTime - startTime));

            const data = res.data;
            if (data.found) {
                setResult(data);

                // Update map data
                const lat = parseFloat(data.latitude);
                const lng = parseFloat(data.longitude);

                if (!isNaN(lat) && !isNaN(lng)) {
                    const city = data.city !== "N/A" ? data.city : "";
                    const region = data.region !== "N/A" ? data.region : "";
                    const country = data.country_full || data.country_name || data.country || ""; // country_full added in python

                    let locationText = [city, region, country].filter(Boolean).join(', ');
                    if (!locationText) locationText = 'Unknown Location';

                    const elevation = data.elevation ? ` • Elev: ${data.elevation}m` : '';

                    setMapData({
                        lat, lng,
                        city, region, country,
                        zoom: 10,
                        info: locationText,
                        sub: `IP: ${data.ip} • ${data.timezone || 'N/A'}${elevation}`
                    });
                } else {
                    setMapData(prev => ({ ...prev, info: 'Location Unknown', sub: 'No coordinates available' }));
                }

            } else {
                setError(`No data found for ${searchIp}`);
            }
        } catch (err) {
            setError(err.response?.data?.detail || err.message || "An error occurred");
        } finally {
            setLoading(false);
        }
    };

    const handleSearch = (e) => {
        e.preventDefault();
        performCheck(ip);
    };

    // Syntax Highlight Helper
    const renderJson = (data) => {
        if (!data) return null;

        const fieldsToShow = [
            "ip", "ip_type", "user_type", "country_code", "country_name", "is_eu", "is_datacenter", "is_vpn", "elevation", "netname", "domain", "city", "is_fallback", "region", "timezone", "utc_offset", "zip_code",
            "continent", "latitude", "longitude", "is_multicast",
            "asn", "asn_name", "country_numeric", "currency_name", "currency_code", "dial_code",
            "is_crawler"
        ];

        const filtered = {};
        fieldsToShow.forEach(field => {
            if (data[field] !== undefined) filtered[field] = data[field];
        });

        return (
            <pre style={{ textAlign: 'left', whiteSpace: 'pre-wrap' }}>
                <code dangerouslySetInnerHTML={{ __html: syntaxHighlight(filtered) }} />
            </pre>
        );
    };

    const syntaxHighlight = (json) => {
        if (typeof json !== 'string') {
            json = JSON.stringify(json, undefined, 4);
        }
        json = json.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
        return json.replace(/("(\\u[a-zA-Z0-9]{4}|\\[^u]|[^\\"])*"(\s*:)?|\b(true|false|null)\b|-?\d+(?:\.\d*)?(?:[eE][+\-]?\d+)?)/g, function (match) {
            let cls = 'json-number';
            if (/^"/.test(match)) {
                if (/:$/.test(match)) {
                    cls = 'json-key';
                } else {
                    cls = 'json-string';
                }
            } else if (/true|false/.test(match)) {
                cls = 'json-boolean';
            } else if (/null/.test(match)) {
                cls = 'json-null';
            }
            return '<span class="' + cls + '">' + match + '</span>';
        });
    };


    return (
        <>
            <section className="hero">
                <div className="hero-bg"></div>
                <div className="hero-content">
                    <div className="hero-text">
                        <h1>Precise IP Solution for <span className="gradient-text">Your Business</span></h1>
                        <p className="hero-subtitle">
                            Enrich your analytics, prevent fraud, and personalize content with carrier-grade IP geolocation and
                            ASN data. <br />
                            <strong>Ultra-low latency (&lt; 10ms). No logging.</strong>
                        </p>
                        <div className="hero-cta">
                            <a href="/docs" className="btn-secondary">View Documentation</a>
                            <a href="#features" className="btn-text" style={{ marginLeft: '1rem', textDecoration: 'none', color: 'var(--text-secondary)' }}>Learn more →</a>
                        </div>

                        {/* Compact Map Card */}
                        <div className="hero-map-card">
                            <div className="map-info-compact">
                                <span id="mapTitle">{mapData.info}</span>
                                <span id="mapSubtitle" className="map-subtitle">{mapData.sub}</span>
                            </div>
                            <div id="map" className="leaflet-map-compact" style={{ height: '200px' }}>
                                <MapComponent
                                    lat={mapData.lat}
                                    lng={mapData.lng}
                                    zoom={mapData.zoom}
                                    popupContent={`<div style="min-width: 180px; text-align: center;"><strong style="font-size: 1.1em;">${mapData.city || 'Unknown'}, ${mapData.country}</strong></div>`}
                                />
                            </div>
                        </div>
                    </div>

                    {/* Live Demo Card */}
                    <div className="hero-demo">
                        <div className="card">
                            <div className="card-header">
                                <div className="header-main">
                                    <h2>Live Lookup</h2>
                                    {latency && (
                                        <div id="resultStatus" className="status-indicator">
                                            <span className="status-dot"></span>
                                            <span className="status-text">{latency}ms</span>
                                        </div>
                                    )}
                                </div>
                            </div>

                            <form onSubmit={handleSearch} className="input-group">
                                <input
                                    type="text"
                                    placeholder="Enter IP address (e.g., 8.8.8.8)"
                                    value={ip}
                                    onChange={(e) => setIp(e.target.value)}
                                    autoComplete="off"
                                />
                                <button type="submit" disabled={loading} className="btn-primary search-btn">
                                    {loading ? <span>Loading...</span> : <span>Search</span>}
                                </button>
                            </form>

                            {error && <div id="message" style={{ display: 'block', color: 'var(--error-fg)', marginTop: '1rem' }}>{error}</div>}

                            <div id="resultContainer" className={`result-container ${result ? 'visible' : ''}`} style={{ display: result ? 'block' : 'none' }}>
                                <div className="json-container">
                                    {renderJson(result)}
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </section>

            {/* Why Choose Us Section */}
            <section className="why-choose-us">
                <div className="container">
                    <div className="wcu-grid">
                        <div className="wcu-visual">
                            {/* Animated Laptop */}
                            <div className="macbook" ref={laptopRef}>
                                <div
                                    className="screen"
                                    style={{
                                        transform: `rotateX(-${lidAngle}deg)`,
                                        willChange: 'transform'
                                    }}
                                >
                                    <div className="viewport">
                                        <img src="/img/dashboard-preview.png" alt="Analytics Dashboard Interface" />
                                    </div>
                                    <div className="notch"></div>
                                </div>
                                <div className="base"></div>
                            </div>
                        </div>

                        <div className="wcu-content">
                            <h2 className="section-title text-left">Insightful Data. <br /><span className="gradient-text">Unbeatable Value.</span></h2>
                            <p className="wcu-desc">
                                Stop overpaying for basic IP data. We provide premium, carrier-grade intelligence with a full
                                analytical suite included.
                            </p>

                            <div className="value-propositions">
                                <div className="value-item">
                                    <div className="value-icon">♾️</div>
                                    <div className="value-text">
                                        <strong>Unlimited Requests</strong>
                                        <span>No hard caps or overage fees.</span>
                                    </div>
                                </div>
                                <div className="value-item">
                                    <div className="value-icon">📉</div>
                                    <div className="value-text">
                                        <strong>Cost Effective</strong>
                                        <span>Significantly cheaper than competitors.</span>
                                    </div>
                                </div>
                            </div>

                            <ul className="wcu-features">
                                <li>
                                    <div className="icon-box"><i className="fas fa-eye-slash"></i></div>
                                    <div>
                                        <strong>Strict Privacy</strong>
                                        <span>No logging. Your queries are yours alone.</span>
                                    </div>
                                </li>
                                <li>
                                    <div className="icon-box"><i className="fas fa-chart-pie"></i></div>
                                    <div>
                                        <strong>Embedded Visuals</strong>
                                        <span>Visualize traffic, VPN usage, and more instantly.</span>
                                    </div>
                                </li>
                            </ul>

                            <Link to="/dashboard" className="btn-primary mt-4" style={{ display: 'inline-block', marginTop: '1.5rem' }}>Explore Dashboard</Link>
                        </div>
                    </div>
                </div>
            </section>

            {/* Features Section */}
            <section id="features" className="features">
                <div className="container">
                    <h2 className="section-title">Why choose <span className="gradient-text">IP Intelligence?</span></h2>
                    <div className="feature-grid">
                        <div className="feature-card">
                            <div className="icon">🚀</div>
                            <h3>Ultra-Low Latency</h3>
                            <p>Optimized for speed with local MMDB lookups and in-memory caching. Average response &lt; 10ms.</p>
                        </div>
                        <div className="feature-card">
                            <div className="icon">🎯</div>
                            <h3>High Accuracy</h3>
                            <p>Aggregated data from industry-leading trusted sources for precise geolocation and ASN details.</p>
                        </div>
                        <div className="feature-card">
                            <div className="icon">🛡️</div>
                            <h3>Privacy First</h3>
                            <p>We do not log your queries. Your data usage remains private and secure.</p>
                        </div>
                    </div>
                </div>
            </section>
        </>
    );
};

export default Home;
