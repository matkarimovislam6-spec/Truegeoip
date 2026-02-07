document.addEventListener('DOMContentLoaded', async () => {
    const ipInput = document.getElementById('ipInput');
    const checkBtn = document.getElementById('checkBtn');
    const resultContainer = document.getElementById('resultContainer');
    const messageDiv = document.getElementById('message');
    const macbook = document.querySelector('.macbook');
    const laptopScreen = macbook ? macbook.querySelector('.screen') : null;

    // Map variables
    let map = null;
    let marker = null;

    // Initialize Leaflet Map
    function initMap() {
        if (map) return; // Already initialized

        const mapContainer = document.getElementById('map');
        if (!mapContainer) return;

        // Default to world view
        map = L.map('map').setView([20, 0], 2);

        // Add OpenStreetMap tiles
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
            maxZoom: 18,
        }).addTo(map);
    }

    // Update map with location
    function updateMap(data) {
        if (!map) initMap();
        if (!map) return;

        const lat = parseFloat(data.latitude);
        const lng = parseFloat(data.longitude);

        if (isNaN(lat) || isNaN(lng) || data.latitude === "N/A" || data.longitude === "N/A") {
            // No valid coordinates
            document.getElementById('mapTitle').textContent = 'Location Unknown';
            document.getElementById('mapSubtitle').textContent = 'No coordinates available for this IP';
            return;
        }

        // Update map info header
        const city = data.city !== "N/A" ? data.city : "";
        const region = data.region !== "N/A" ? data.region : "";
        const country = data.country_full || data.country || "";

        let locationText = [city, region, country].filter(Boolean).join(', ');
        if (!locationText) locationText = 'Unknown Location';

        const elevation = data.elevation ? ` • Elev: ${data.elevation}m` : '';
        document.getElementById('mapTitle').textContent = locationText;
        document.getElementById('mapSubtitle').textContent = `IP: ${data.ip} • ${data.timezone || 'N/A'}${elevation}`;

        // Remove existing marker
        if (marker) {
            map.removeLayer(marker);
        }

        // Add new marker with custom popup
        marker = L.marker([lat, lng]).addTo(map);

        const popupContent = `
            <div style="min-width: 180px; text-align: center;">
                <strong style="font-size: 1.1em;">${city || 'Unknown'}, ${country}</strong>
            </div>
        `;

        marker.bindPopup(popupContent).openPopup();

        // Keep interactions flat/minimal.
        map.setView([lat, lng], 10, { animate: false });
    }

    // Initialize map on page load
    initMap();

    // Scroll-linked laptop lid animation
    function setupLaptopAnimation() {
        if (!macbook || !laptopScreen) return;

        const CLOSED_ANGLE = 96;
        const OPEN_ZONE = 0.42;
        const LERP = 0.14;
        const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

        let currentAngle = CLOSED_ANGLE;
        let targetAngle = CLOSED_ANGLE;
        let rafId = null;

        const clamp = (value, min, max) => Math.max(min, Math.min(max, value));

        const computeTargetAngle = () => {
            const rect = macbook.getBoundingClientRect();
            const viewportHeight = window.innerHeight;
            const viewportCenter = viewportHeight / 2;
            const laptopCenter = rect.top + (rect.height / 2);
            const distanceFromCenter = Math.abs(laptopCenter - viewportCenter);

            // Open most when near viewport center.
            const centeredOpen = 1 - clamp(distanceFromCenter / (viewportHeight * OPEN_ZONE), 0, 1);
            // Close near top/bottom by combining with visibility amount.
            const visiblePx = Math.min(rect.bottom, viewportHeight) - Math.max(rect.top, 0);
            const visibleRatio = clamp(visiblePx / rect.height, 0, 1);

            const openAmount = centeredOpen * visibleRatio;
            return CLOSED_ANGLE * (1 - openAmount);
        };

        const renderAngle = (angle) => {
            laptopScreen.style.transform = `rotateX(-${angle.toFixed(2)}deg)`;
        };

        const animate = () => {
            const diff = targetAngle - currentAngle;
            currentAngle += diff * LERP;
            renderAngle(currentAngle);

            if (Math.abs(diff) > 0.08) {
                rafId = window.requestAnimationFrame(animate);
            } else {
                currentAngle = targetAngle;
                renderAngle(currentAngle);
                rafId = null;
            }
        };

        const syncTarget = () => {
            targetAngle = computeTargetAngle();
            if (prefersReducedMotion) {
                currentAngle = targetAngle;
                renderAngle(currentAngle);
                return;
            }
            if (rafId === null) {
                rafId = window.requestAnimationFrame(animate);
            }
        };

        // Start closed then react to viewport position.
        renderAngle(CLOSED_ANGLE);
        window.addEventListener('scroll', syncTarget, { passive: true });
        window.addEventListener('resize', syncTarget);
        syncTarget();
    }

    setupLaptopAnimation();

    // Theme Toggle Logic (cycles: dark → light → sunset → dark)
    const themeToggle = document.getElementById('themeToggle');
    const htmlEl = document.documentElement;
    const icon = themeToggle ? themeToggle.querySelector('i') : null;

    const themes = ['dark', 'light', 'sunset'];
    const themeIcons = {
        'dark': 'fa-moon',
        'light': 'fa-sun',
        'sunset': 'fa-palette'
    };

    function setTheme(theme) {
        if (!themeToggle || !icon) return;

        if (theme === 'light') {
            htmlEl.setAttribute('data-theme', 'light');
        } else if (theme === 'sunset') {
            htmlEl.setAttribute('data-theme', 'sunset');
        } else {
            htmlEl.removeAttribute('data-theme');
            theme = 'dark';
        }

        // Update icon
        icon.classList.remove('fa-moon', 'fa-sun', 'fa-palette');
        icon.classList.add(themeIcons[theme]);
        localStorage.setItem('theme', theme);
    }

    // Check saved preference
    const savedTheme = localStorage.getItem('theme');
    if (savedTheme && themes.includes(savedTheme)) {
        setTheme(savedTheme);
    }

    if (themeToggle) {
        themeToggle.addEventListener('click', () => {
            const currentTheme = htmlEl.getAttribute('data-theme') || 'dark';
            const currentIndex = themes.indexOf(currentTheme);
            const nextIndex = (currentIndex + 1) % themes.length;
            setTheme(themes[nextIndex]);
        });
    }

    if (checkBtn && ipInput) {
        checkBtn.addEventListener('click', performCheck);
        ipInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') performCheck();
        });
    }

    // Auto-check client IP on load
    // Auto-check client IP on load
    const inputGroup = document.querySelector('.input-group');
    let clientIp = inputGroup ? inputGroup.dataset.clientIp : null;

    // If local/private, fetch real public IP
    if (clientIp && (clientIp === '127.0.0.1' || clientIp === '::1' || clientIp.startsWith('192.168.') || clientIp.startsWith('10.'))) {
        // Function to fetch with timeout
        const fetchWithTimeout = async (resource, options = {}) => {
            const { timeout = 3000 } = options;
            const controller = new AbortController();
            const id = setTimeout(() => controller.abort(), timeout);
            const response = await fetch(resource, { ...options, signal: controller.signal });
            clearTimeout(id);
            return response;
        };

        try {
            console.log("Local IP detected, fetching public IP...");
            ipInput.value = "";
            ipInput.placeholder = "Detecting public IP...";

            // Try primary service
            const response = await fetchWithTimeout('https://api.ipify.org?format=json');
            const data = await response.json();
            clientIp = data.ip;
        } catch (e) {
            console.warn("Primary IP fetch failed, trying fallback...", e);
            try {
                // Try fallback service (Cloudflare trace)
                const response = await fetchWithTimeout('https://www.cloudflare.com/cdn-cgi/trace');
                const text = await response.text();
                // Extract IP from trace (ip=X.X.X.X)
                const match = text.match(/ip=(.+)/);
                if (match && match[1]) {
                    clientIp = match[1];
                }
            } catch (e2) {
                console.error("All IP fetch attempts failed:", e2);
                // If all fails, use the local IP anyway so the UI doesn't stick
                if (!clientIp) clientIp = "127.0.0.1";
            }
        }
    }

    if (clientIp && ipInput) {
        ipInput.value = clientIp;
        performCheck();
    }

    async function performCheck(ipOrEvent) {
        let ip = ipOrEvent;

        // If called via event listener or empty, get from input
        if (!ip || typeof ip !== 'string') {
            ip = ipInput.value.trim();
        }

        if (!ip) {
            showMessage("Please enter an IP address", "error");
            return;
        }

        setLoading(true);
        messageDiv.style.display = 'none';

        // Reset UI for new search
        resultContainer.classList.remove('visible');
        const statusEl = document.getElementById('resultStatus');
        if (statusEl) statusEl.classList.add('hidden');

        try {
            const startTime = performance.now();
            const response = await fetch(`/api/check?ip=${encodeURIComponent(ip)}`);
            const data = await response.json();
            const endTime = performance.now();
            const totalLatency = endTime - startTime;

            setLoading(false);

            if (!response.ok) {
                const errorMsg = data.error || data.detail || "An error occurred";
                if (response.status === 403) {
                    showMessage(`Sign in required. <a href="/signin" style="color: var(--accent-primary); text-decoration: underline;">Sign In</a>`, "error");
                    messageDiv.innerHTML = `Sign in required. <a href="/signin" style="color: var(--accent-primary); text-decoration: underline;">Sign In</a>`; // Explicitly set innerHTML for link
                } else {
                    showMessage(errorMsg, "error");
                }
                return;
            }

            if (data.found) {
                // Latency
                const serverTime = data.latency_server || 0;
                // Client-side round trip minus server processing time estimate
                const networkLatency = Math.max(0, Math.round(totalLatency - serverTime));

                const latencyText = `${Math.round(totalLatency)}ms`;
                if (statusEl) {
                    statusEl.classList.remove('hidden');
                    statusEl.querySelector('.status-text').textContent = latencyText;
                }
                resultContainer.classList.add('visible');

                // Render JSON Output
                const jsonOutput = document.getElementById('jsonOutput');
                if (jsonOutput) {
                    const fieldsToShow = [
                        "ip", "ip_type", "user_type", "threat_level", "country_code", "country_name", "is_eu", "is_datacenter", "is_vpn", "elevation", "netname", "domain", "city", "region", "timezone", "utc_offset", "zip_code",
                        "continent", "latitude", "longitude",
                        "asn", "asn_name", "country_numeric", "currency_code", "currency_name", "dial_code",
                        "is_crawler"
                    ];

                    const filteredData = {};
                    fieldsToShow.forEach(field => {
                        if (data.hasOwnProperty(field)) {
                            filteredData[field] = data[field];
                        }
                    });

                    function syntaxHighlight(json) {
                        if (typeof json != 'string') {
                            json = JSON.stringify(json, undefined, 4);
                        }
                        json = json.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
                        return json.replace(/("(\\u[a-zA-Z0-9]{4}|\\[^u]|[^\\"])*"(\s*:)?|\b(true|false|null)\b|-?\d+(?:\.\d*)?(?:[eE][+\-]?\d+)?)/g, function (match) {
                            var cls = 'json-number';
                            if (/^"/.test(match)) {
                                if (/:$/.test(match)) {
                                    cls = 'json-key';
                                } else {
                                    cls = 'json-string';
                                    var value = match.slice(1, -1);
                                    // Treat numeric-looking strings (e.g. ASN, ZIP, UTC offsets) as numeric tokens.
                                    if (
                                        /^[+-]?\d+(?:\.\d+)?(?:[eE][+\-]?\d+)?$/.test(value) ||
                                        /^[+-]\d{2}:\d{2}$/.test(value) ||
                                        /^\d{4,}(?:-\d{3,4})?$/.test(value)
                                    ) {
                                        cls = 'json-number';
                                    }
                                }
                            } else if (/true|false/.test(match)) {
                                cls = 'json-boolean';
                            } else if (/null/.test(match)) {
                                cls = 'json-null';
                            }
                            return '<span class="' + cls + '">' + match + '</span>';
                        });
                    }

                    jsonOutput.innerHTML = syntaxHighlight(filteredData);
                }

                // Update Map with location
                updateMap(data);

                // Show Result with Animation
                resultContainer.style.display = '';
                resultContainer.classList.add('visible');
            } else {
                showMessage(`No data found for ${data.ip}`, "error");
            }

        } catch (error) {
            setLoading(false);
            showMessage(`Error: ${error.message}`, "error");
            console.error("Lookup error:", error);
        }
    }

    function setLoading(isLoading) {
        if (isLoading) {
            checkBtn.disabled = true;
            checkBtn.innerHTML = '<div class="loader"></div> Check IP';
        } else {
            checkBtn.disabled = false;
            checkBtn.textContent = 'Search';
        }
    }

    function showMessage(text, type) {
        messageDiv.textContent = text;
        messageDiv.style.display = 'block';

        if (type === 'error') {
            messageDiv.style.color = 'var(--accent-primary)';
            messageDiv.style.border = '1px solid var(--accent-primary)';
            messageDiv.style.background = 'var(--input-bg)';
        } else {
            messageDiv.style.color = 'var(--text-primary)';
            messageDiv.style.border = 'none';
            messageDiv.style.background = 'transparent';
        }
    }


});
