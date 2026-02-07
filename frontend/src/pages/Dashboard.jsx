import React, { useEffect, useMemo, useState } from 'react';
import axios from 'axios';
import { Link } from 'react-router-dom';

const formatNumber = (value) => new Intl.NumberFormat('en-US').format(value || 0);
const formatCompact = (value) => new Intl.NumberFormat('en-US', {
    notation: 'compact',
    maximumFractionDigits: 1
}).format(value || 0);

const ensureArray = (value) => Array.isArray(value) ? value : [];
const clamp = (value, min, max) => Math.min(max, Math.max(min, value));

const buildSparkPath = (values, width = 120, height = 36, padding = 4) => {
    if (!values.length) return '';
    const max = Math.max(...values);
    const min = Math.min(...values);
    const step = values.length > 1 ? (width - padding * 2) / (values.length - 1) : 0;
    const scaleY = (val) => {
        if (max === min) return height / 2;
        return height - padding - ((val - min) / (max - min)) * (height - padding * 2);
    };
    return values
        .map((val, i) => `${i === 0 ? 'M' : 'L'}${padding + i * step} ${scaleY(val)}`)
        .join(' ');
};

const buildLineChart = (values, width = 720, height = 220, padding = 26) => {
    if (!values.length) {
        return { linePath: '', areaPath: '', max: 0 };
    }
    const max = Math.max(...values);
    const min = Math.min(...values);
    const step = values.length > 1 ? (width - padding * 2) / (values.length - 1) : 0;
    const scaleY = (val) => {
        if (max === min) return height / 2;
        return height - padding - ((val - min) / (max - min)) * (height - padding * 2);
    };
    const points = values.map((val, i) => [padding + i * step, scaleY(val)]);
    const linePath = points.map((p, i) => `${i === 0 ? 'M' : 'L'}${p[0]} ${p[1]}`).join(' ');
    const areaPath = `${linePath} L ${padding + (values.length - 1) * step} ${height - padding} L ${padding} ${height - padding} Z`;
    return { linePath, areaPath, max };
};

const buildDemoAnalytics = (days, users = [], carts = []) => {
    const now = new Date();
    const totals = carts.map((cart) => cart.total || 0);
    const base = totals.length ? totals : Array.from({ length: 10 }, (_, i) => 90 + i * 12);

    const timeseries = Array.from({ length: days }, (_, index) => {
        const date = new Date(now);
        date.setDate(now.getDate() - (days - 1 - index));
        const baseValue = base[index % base.length];
        const requests = Math.round(baseValue * (0.75 + (index % 5) * 0.08));
        const unique = Math.max(1, Math.round(requests * 0.58));
        return {
            bucket: date.toISOString(),
            requests,
            unique_ips: unique
        };
    });

    const totalRequests = timeseries.reduce((sum, item) => sum + (item.requests || 0), 0);
    const uniqueIps = Math.round(totalRequests * 0.4);

    const countryMap = new Map();
    const cityMap = new Map();
    const asnMap = new Map();

    users.forEach((user) => {
        const country = user?.address?.country || 'Unknown';
        const city = user?.address?.city || 'Unknown';
        const region = user?.address?.state || 'N/A';
        const company = user?.company?.name || 'Independent';

        countryMap.set(country, (countryMap.get(country) || 0) + 1);
        cityMap.set(`${city}|${region}|${country}`, (cityMap.get(`${city}|${region}|${country}`) || 0) + 1);
        asnMap.set(company, (asnMap.get(company) || 0) + 1);
    });

    const countries = Array.from(countryMap.entries())
        .map(([country_name, requests]) => ({
            country_name,
            country_code: country_name.slice(0, 2).toUpperCase(),
            requests: requests * 120
        }))
        .sort((a, b) => b.requests - a.requests)
        .slice(0, 6);

    const cities = Array.from(cityMap.entries())
        .map(([key, requests]) => {
            const [city, region, country_code] = key.split('|');
            return {
                city,
                region,
                country_code: country_code.slice(0, 2).toUpperCase(),
                requests: requests * 80
            };
        })
        .sort((a, b) => b.requests - a.requests)
        .slice(0, 6);

    const asns = Array.from(asnMap.entries())
        .map(([name, requests], index) => ({
            asn: 1000 + index,
            asn_name: name,
            netname: name,
            requests: requests * 150,
            unique_ips: Math.round(requests * 70),
            datacenter_count: index % 3 === 0 ? Math.round(requests * 20) : 0
        }))
        .sort((a, b) => b.requests - a.requests)
        .slice(0, 6);

    const vpnPercent = 6;
    const datacenterPercent = 14;
    const residentialPercent = 60;
    const mobilePercent = 16;
    const otherPercent = clamp(100 - vpnPercent - datacenterPercent - residentialPercent - mobilePercent, 0, 100);

    const risk = {
        vpn: Math.round(totalRequests * vpnPercent / 100),
        vpn_percent: vpnPercent,
        datacenter: Math.round(totalRequests * datacenterPercent / 100),
        datacenter_percent: datacenterPercent,
        residential: Math.round(totalRequests * residentialPercent / 100),
        residential_percent: residentialPercent,
        mobile: Math.round(totalRequests * mobilePercent / 100),
        mobile_percent: mobilePercent,
        other: Math.round(totalRequests * otherPercent / 100),
        other_percent: otherPercent,
        total: totalRequests
    };

    const overview = {
        total_requests: totalRequests,
        unique_ips: uniqueIps,
        country_count: countryMap.size || countries.length,
        asn_count: asnMap.size || asns.length,
        datacenter_percent: datacenterPercent,
        vpn_percent: vpnPercent
    };

    return { overview, timeseries, countries, cities, asns, risk };
};

const fetchDemoAnalytics = async (days) => {
    try {
        const [usersRes, cartsRes] = await Promise.all([
            fetch('https://dummyjson.com/users?limit=60'),
            fetch('https://dummyjson.com/carts?limit=30')
        ]);

        const usersJson = usersRes.ok ? await usersRes.json() : { users: [] };
        const cartsJson = cartsRes.ok ? await cartsRes.json() : { carts: [] };

        return buildDemoAnalytics(days, usersJson.users || [], cartsJson.carts || []);
    } catch (error) {
        return buildDemoAnalytics(days, [], []);
    }
};

const Dashboard = () => {
    const [user, setUser] = useState(null);
    const [loading, setLoading] = useState(true);
    const [rangeDays, setRangeDays] = useState(7);
    const [loadingData, setLoadingData] = useState(false);
    const [dataError, setDataError] = useState(null);
    const [demoMode, setDemoMode] = useState(false);

    const [overview, setOverview] = useState(null);
    const [timeseries, setTimeseries] = useState([]);
    const [countries, setCountries] = useState([]);
    const [cities, setCities] = useState([]);
    const [asns, setAsns] = useState([]);
    const [risk, setRisk] = useState(null);

    useEffect(() => {
        axios.get('/api/user')
            .then(res => {
                setUser(res.data);
                setLoading(false);
            })
            .catch(() => {
                setUser(null);
                setLoading(false);
            });
    }, []);

    useEffect(() => {
        if (!user) return;

        const loadAnalytics = async () => {
            setLoadingData(true);
            setDataError(null);
            const interval = rangeDays > 2 ? 'day' : 'hour';

            try {
                const [overviewRes, seriesRes, countriesRes, citiesRes, asnsRes, riskRes] = await Promise.all([
                    axios.get('/v1/analytics/overview', { params: { days: rangeDays } }),
                    axios.get('/v1/analytics/timeseries', { params: { days: rangeDays, interval } }),
                    axios.get('/v1/analytics/countries', { params: { days: rangeDays, limit: 6 } }),
                    axios.get('/v1/analytics/cities', { params: { days: rangeDays, limit: 6 } }),
                    axios.get('/v1/analytics/asns', { params: { days: rangeDays, limit: 6 } }),
                    axios.get('/v1/analytics/risk', { params: { days: rangeDays } })
                ]);

                const liveOverview = overviewRes.data || null;
                const liveSeries = ensureArray(seriesRes.data);
                const liveCountries = ensureArray(countriesRes.data);
                const liveCities = ensureArray(citiesRes.data);
                const liveAsns = ensureArray(asnsRes.data);
                const liveRisk = riskRes.data || null;

                if (!liveOverview || liveOverview.total_requests === 0) {
                    const demo = await fetchDemoAnalytics(rangeDays);
                    setOverview(demo.overview);
                    setTimeseries(demo.timeseries);
                    setCountries(demo.countries);
                    setCities(demo.cities);
                    setAsns(demo.asns);
                    setRisk(demo.risk);
                    setDemoMode(true);
                } else {
                    setOverview(liveOverview);
                    setTimeseries(liveSeries);
                    setCountries(liveCountries);
                    setCities(liveCities);
                    setAsns(liveAsns);
                    setRisk(liveRisk);
                    setDemoMode(false);
                }
            } catch (error) {
                const demo = await fetchDemoAnalytics(rangeDays);
                setOverview(demo.overview);
                setTimeseries(demo.timeseries);
                setCountries(demo.countries);
                setCities(demo.cities);
                setAsns(demo.asns);
                setRisk(demo.risk);
                setDemoMode(true);
                setDataError('Live analytics unavailable. Showing demo data.');
            } finally {
                setLoadingData(false);
            }
        };

        loadAnalytics();
    }, [user, rangeDays]);

    const requestSeries = useMemo(() => timeseries.map(item => item.requests || 0), [timeseries]);
    const uniqueSeries = useMemo(() => timeseries.map(item => item.unique_ips || 0), [timeseries]);
    const lineChart = useMemo(() => buildLineChart(requestSeries), [requestSeries]);
    const lastValue = requestSeries.length ? requestSeries[requestSeries.length - 1] : 0;
    const prevValue = requestSeries.length > 1 ? requestSeries[requestSeries.length - 2] : 0;
    const delta = prevValue ? ((lastValue - prevValue) / prevValue) * 100 : 0;

    if (loading) {
        return (
            <div style={{ minHeight: '80vh', display: 'flex', justifyContent: 'center', alignItems: 'center', paddingTop: '80px' }}>
                <div className="loader" style={{ borderColor: 'var(--accent-primary)', borderTopColor: 'transparent', width: '40px', height: '40px' }}></div>
            </div>
        );
    }

    if (!user) {
        return (
            <div style={{ minHeight: '80vh', display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'center', paddingTop: '80px', textAlign: 'center' }}>
                <h1 style={{ fontSize: '2rem', marginBottom: '1rem' }}>Sign In</h1>
                <p style={{ color: 'var(--text-secondary)', marginBottom: '2rem' }}>You need to be signed in to view Analytics.</p>
                <Link to="/signin" className="btn-primary" style={{ padding: '0.8rem 2rem' }}>Go to Sign In</Link>
            </div>
        );
    }

    return (
        <div className="analytics-page">
            <div className="analytics-hero container">
                <div className="analytics-title">
                    <div className={`analytics-chip ${demoMode ? 'demo' : ''}`}>{demoMode ? 'Demo Data' : 'Live Analytics'}</div>
                    <h1>Traffic Intelligence</h1>
                    <p>Built-in, privacy-first analytics with edge-level visibility. Sharper than GA4, tailored for IP intelligence.</p>
                </div>
                <div className="analytics-controls">
                    <div className="analytics-range">
                        {[7, 30, 90].map((days) => (
                            <button
                                key={days}
                                className={rangeDays === days ? 'active' : ''}
                                onClick={() => setRangeDays(days)}
                            >
                                Last {days} days
                            </button>
                        ))}
                    </div>
                    <div className="analytics-user">
                        <div className="analytics-user-label">Welcome back</div>
                        <div className="analytics-user-name">{user.name}</div>
                    </div>
                </div>
            </div>

            <div className="container">
                <div className="analytics-kpis">
                    <div className="kpi-card">
                        <div className="kpi-label">Total Requests</div>
                        <div className="kpi-value">{formatCompact(overview?.total_requests || 0)}</div>
                        <div className={`kpi-delta ${delta >= 0 ? 'up' : 'down'}`}>{delta >= 0 ? '+' : ''}{delta.toFixed(1)}% vs prev</div>
                        <div className="kpi-spark">
                            <svg viewBox="0 0 120 36" aria-hidden="true">
                                <path d={buildSparkPath(requestSeries)} />
                            </svg>
                        </div>
                    </div>
                    <div className="kpi-card">
                        <div className="kpi-label">Unique IPs</div>
                        <div className="kpi-value">{formatCompact(overview?.unique_ips || 0)}</div>
                        <div className="kpi-meta">{formatNumber(overview?.unique_ips || 0)} total</div>
                        <div className="kpi-spark">
                            <svg viewBox="0 0 120 36" aria-hidden="true">
                                <path d={buildSparkPath(uniqueSeries)} />
                            </svg>
                        </div>
                    </div>
                    <div className="kpi-card">
                        <div className="kpi-label">Countries</div>
                        <div className="kpi-value">{formatNumber(overview?.country_count || 0)}</div>
                        <div className="kpi-meta">Global coverage</div>
                    </div>
                    <div className="kpi-card">
                        <div className="kpi-label">ASNs</div>
                        <div className="kpi-value">{formatNumber(overview?.asn_count || 0)}</div>
                        <div className="kpi-meta">Networks seen</div>
                    </div>
                    <div className="kpi-card">
                        <div className="kpi-label">VPN Share</div>
                        <div className="kpi-value">{overview?.vpn_percent || 0}%</div>
                        <div className="kpi-meta">Flagged requests</div>
                    </div>
                    <div className="kpi-card">
                        <div className="kpi-label">Datacenter</div>
                        <div className="kpi-value">{overview?.datacenter_percent || 0}%</div>
                        <div className="kpi-meta">Infrastructure traffic</div>
                    </div>
                </div>

                {loadingData && (
                    <div className="analytics-alert">Loading analytics data...</div>
                )}

                {dataError && (
                    <div className="analytics-alert">{dataError}</div>
                )}

                <div className="analytics-main">
                    <div className="analytics-panel chart-panel">
                        <div className="panel-header">
                            <div>
                                <h3>Request Volume</h3>
                                <p>Requests over time with unique IP overlays.</p>
                            </div>
                            <div className="panel-metric">
                                <span>Latest</span>
                                <strong>{formatCompact(lastValue)}</strong>
                            </div>
                        </div>
                        <div className="chart-wrap">
                            <svg viewBox="0 0 720 220" preserveAspectRatio="none">
                                <defs>
                                    <linearGradient id="areaGradient" x1="0" y1="0" x2="0" y2="1">
                                        <stop offset="0%" stopColor="var(--accent-secondary)" stopOpacity="0.22" />
                                        <stop offset="100%" stopColor="var(--accent-secondary)" stopOpacity="0" />
                                    </linearGradient>
                                </defs>
                                <path d={lineChart.areaPath} fill="url(#areaGradient)" />
                                <path d={lineChart.linePath} className="chart-line" />
                            </svg>
                        </div>
                        <div className="chart-footer">
                            <div>
                                <span>Peak</span>
                                <strong>{formatCompact(lineChart.max)}</strong>
                            </div>
                            <div>
                                <span>Time Range</span>
                                <strong>{rangeDays} days</strong>
                            </div>
                            <div>
                                <span>Unique IPs</span>
                                <strong>{formatCompact(overview?.unique_ips || 0)}</strong>
                            </div>
                        </div>
                    </div>

                    <div className="analytics-stack">
                        <div className="analytics-panel risk-panel">
                            <div className="panel-header">
                                <div>
                                    <h3>Risk Mix</h3>
                                    <p>Traffic classification breakdown.</p>
                                </div>
                            </div>
                            <div className="risk-body">
                                <div className="risk-donut">
                                    <svg viewBox="0 0 120 120">
                                        {(() => {
                                            const segments = [
                                                { label: 'VPN', value: risk?.vpn_percent || 0, color: 'var(--accent-tertiary)' },
                                                { label: 'Datacenter', value: risk?.datacenter_percent || 0, color: 'var(--accent-primary)' },
                                                { label: 'Residential', value: risk?.residential_percent || 0, color: 'var(--accent-secondary)' },
                                                { label: 'Mobile', value: risk?.mobile_percent || 0, color: '#1f2937' }
                                            ];
                                            const radius = 46;
                                            const circumference = 2 * Math.PI * radius;
                                            let offset = 0;
                                            return segments.map((segment) => {
                                                const length = circumference * (segment.value / 100);
                                                const dash = `${length} ${circumference - length}`;
                                                const circle = (
                                                    <circle
                                                        key={segment.label}
                                                        cx="60"
                                                        cy="60"
                                                        r={radius}
                                                        fill="none"
                                                        stroke={segment.color}
                                                        strokeWidth="10"
                                                        strokeDasharray={dash}
                                                        strokeDashoffset={-offset}
                                                        strokeLinecap="round"
                                                    />
                                                );
                                                offset += length + 2;
                                                return circle;
                                            });
                                        })()}
                                    </svg>
                                    <div className="risk-center">
                                        <strong>{formatCompact(risk?.total || 0)}</strong>
                                        <span>Requests</span>
                                    </div>
                                </div>
                                <div className="risk-list">
                                    <div>
                                        <span>VPN</span>
                                        <strong>{risk?.vpn_percent || 0}%</strong>
                                    </div>
                                    <div>
                                        <span>Datacenter</span>
                                        <strong>{risk?.datacenter_percent || 0}%</strong>
                                    </div>
                                    <div>
                                        <span>Residential</span>
                                        <strong>{risk?.residential_percent || 0}%</strong>
                                    </div>
                                    <div>
                                        <span>Mobile</span>
                                        <strong>{risk?.mobile_percent || 0}%</strong>
                                    </div>
                                </div>
                            </div>
                        </div>

                        <div className="analytics-panel list-panel">
                            <div className="panel-header">
                                <div>
                                    <h3>Top Countries</h3>
                                    <p>Requests by geography.</p>
                                </div>
                            </div>
                            <div className="bar-list">
                                {countries.map((item) => {
                                    const total = overview?.total_requests || 1;
                                    const width = Math.max(6, Math.round((item.requests / total) * 100));
                                    return (
                                        <div key={`${item.country_code}-${item.country_name}`} className="bar-row">
                                            <div>
                                                <strong>{item.country_name || item.country_code}</strong>
                                                <span>{item.country_code}</span>
                                            </div>
                                            <div className="bar-track">
                                                <div className="bar-fill" style={{ width: `${width}%` }}></div>
                                            </div>
                                            <div className="bar-metric">{formatCompact(item.requests)}</div>
                                        </div>
                                    );
                                })}
                                {!countries.length && (
                                    <div className="empty-mini">No country data yet.</div>
                                )}
                            </div>
                        </div>
                    </div>
                </div>

                <div className="analytics-secondary">
                    <div className="analytics-panel table-panel">
                        <div className="panel-header">
                            <div>
                                <h3>Top ASNs</h3>
                                <p>Highest volume networks and providers.</p>
                            </div>
                        </div>
                        <div className="analytics-table">
                            <div className="table-row table-head">
                                <span>ASN</span>
                                <span>Provider</span>
                                <span>Requests</span>
                                <span>Unique IPs</span>
                            </div>
                            {asns.map((item) => (
                                <div key={item.asn} className="table-row">
                                    <span>{item.asn}</span>
                                    <span>{item.asn_name || item.netname || 'N/A'}</span>
                                    <span>{formatCompact(item.requests)}</span>
                                    <span>{formatCompact(item.unique_ips)}</span>
                                </div>
                            ))}
                            {!asns.length && (
                                <div className="empty-mini">No ASN data yet.</div>
                            )}
                        </div>
                    </div>

                    <div className="analytics-panel list-panel">
                        <div className="panel-header">
                            <div>
                                <h3>Top Cities</h3>
                                <p>Localized traffic hotspots.</p>
                            </div>
                        </div>
                        <div className="city-list">
                            {cities.map((item) => (
                                <div key={`${item.city}-${item.country_code}`} className="city-row">
                                    <div>
                                        <strong>{item.city || 'Unknown'}</strong>
                                        <span>{item.region} · {item.country_code}</span>
                                    </div>
                                    <div className="bar-metric">{formatCompact(item.requests)}</div>
                                </div>
                            ))}
                            {!cities.length && (
                                <div className="empty-mini">No city data yet.</div>
                            )}
                        </div>
                    </div>

                    <div className="analytics-panel insight-panel">
                        <div className="panel-header">
                            <div>
                                <h3>Operational Highlights</h3>
                                <p>Actionable signals from your traffic.</p>
                            </div>
                        </div>
                        <div className="insight-grid">
                            <div>
                                <span>VPN Share</span>
                                <strong>{overview?.vpn_percent || 0}%</strong>
                            </div>
                            <div>
                                <span>Datacenter Share</span>
                                <strong>{overview?.datacenter_percent || 0}%</strong>
                            </div>
                            <div>
                                <span>Countries Active</span>
                                <strong>{formatNumber(overview?.country_count || 0)}</strong>
                            </div>
                            <div>
                                <span>ASN Density</span>
                                <strong>{formatNumber(overview?.asn_count || 0)}</strong>
                            </div>
                        </div>
                        <div className="insight-note">
                            Track spikes by integrating alerts with your webhook stream.
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default Dashboard;
