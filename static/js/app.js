// --- CONFIGURATION ---
const statusIndicator = document.getElementById('system-status-indicator');
const connectionStatus = document.getElementById('connection-status');
const feedContainer = document.getElementById('neural-feed');
const liveView = document.getElementById('live-view');
let ws;
let reconnectTimer;

// --- THEME ENGINE ---
function initTheme() {
    const savedTheme = localStorage.getItem('theme') || 'dark';
    document.documentElement.setAttribute('data-theme', savedTheme);
    updateThemeIcon(savedTheme);
}

function toggleTheme() {
    const current = document.documentElement.getAttribute('data-theme');
    const next = current === 'dark' ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', next);
    localStorage.setItem('theme', next);
    updateThemeIcon(next);
}

function updateThemeIcon(theme) {
    const btn = document.querySelector('.theme-toggle');
    btn.innerHTML = theme === 'dark' ? '☀' : '☾';
}

// --- WEBSOCKET ---
function connect() {
    clearTimeout(reconnectTimer);
    connectionStatus.innerText = "CONNECTING...";
    connectionStatus.style.color = "var(--text-secondary)";

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    ws = new WebSocket(`${protocol}//${window.location.host}/ws/feed`);

    ws.onopen = () => {
        connectionStatus.innerText = "ONLINE";
        connectionStatus.style.color = "var(--success)";
        addLog("System", "Uplink established.", "system-msg");
    };

    ws.onmessage = (event) => {
        if (event.data === "pong") return;
        try {
            const data = JSON.parse(event.data);
            handleMessage(data);
        } catch (e) {
            addLog("System", event.data, "text-secondary");
        }
    };

    ws.onclose = () => {
        connectionStatus.innerText = "OFFLINE";
        connectionStatus.style.color = "var(--danger)";
        reconnectTimer = setTimeout(connect, 3000);
    };

    setInterval(() => {
        if (ws.readyState === WebSocket.OPEN) ws.send("ping");
    }, 10000);
}

function handleMessage(data) {
    if (data.type === 'log') {
        addLog(data.agent, data.payload, getAgentClass(data.agent));
    } else if (data.type === 'status') {
        updateStatus(data.payload);
    } else if (data.type === 'image_update') {
        liveView.src = `/latest_view.png?t=${new Date().getTime()}`;
    }
}

function getAgentClass(agentName) {
    if (agentName === 'User') return 'user-msg';
    if (agentName === 'System') return 'system-msg';
    return '';
}

function addLog(agent, text, cssClass) {
    const div = document.createElement('div');
    div.className = `log-entry ${cssClass}`;

    // prettier timestamp
    const now = new Date();
    const time = `${now.getHours().toString().padStart(2, '0')}:${now.getMinutes().toString().padStart(2, '0')}:${now.getSeconds().toString().padStart(2, '0')}`;

    div.innerHTML = `<span style="opacity:0.6; font-size:11px; margin-right:8px">[${time}]</span><strong>${agent}</strong>: ${text}`;
    feedContainer.prepend(div);
}

function updateStatus(status) {
    // Small indicator color change
    if (status === 'RUNNING') {
        statusIndicator.style.backgroundColor = "var(--success)";
        statusIndicator.style.boxShadow = "0 0 10px var(--success)";
    } else if (status === 'STOPPED') {
        statusIndicator.style.backgroundColor = "var(--danger)";
        statusIndicator.style.boxShadow = "none";
    } else {
        statusIndicator.style.backgroundColor = "var(--text-secondary)";
    }
}

// --- API ACTIONS ---
async function fetchState() {
    try {
        const response = await fetch('/api/state');
        const data = await response.json();

        // Config placeholders
        if (data.query) document.getElementById('config-query').value = data.query;

        // CV Status
        const cvBadge = document.getElementById('cv-status');
        if (data.cv_loaded) {
            cvBadge.innerText = "LOADED";
            cvBadge.className = "status-badge loaded";
        } else {
            cvBadge.innerText = "MISSING";
            cvBadge.className = "status-badge missing";
        }

        // Stats
        if (data.stats) {
            document.getElementById('stat-total').innerText = data.stats.total;
            document.getElementById('stat-pending').innerText = data.stats.pending;
            document.getElementById('stat-applied').innerText = data.stats.applied;
        }

        updateStatus(data.status);

    } catch (e) {
        console.error("State Fetch Error", e);
    }
}

async function saveConfig(key, value) {
    try {
        await fetch('/api/config', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ key, value })
        });
        addLog("System", `Config [${key}] saved.`, "system-msg");
    } catch (e) {
        addLog("System", "Save failed.", "error-msg");
    }
}

async function uploadCV(input) {
    if (!input.files.length) return;
    const formData = new FormData();
    formData.append("file", input.files[0]);

    addLog("System", "Uploading data...", "text-secondary");
    try {
        const res = await fetch('/api/upload_cv', { method: 'POST', body: formData });
        const data = await res.json();
        if (data.status === 'success') {
            addLog("System", "Identity Module Updated.", "system-msg");
            fetchState();
        } else {
            addLog("System", "Upload Error: " + data.message, "error-msg");
        }
    } catch (e) {
        addLog("System", "Upload Failed.", "error-msg");
    }
}

async function sendCommand(cmd) {
    try {
        await fetch('/api/command', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ command: cmd })
        });
        addLog("User", `CMD: ${cmd}`, "user-msg");
    } catch (e) {
        addLog("System", "Command failed.", "error-msg");
    }
}

function handleChat(e) {
    e.preventDefault();
    const input = document.getElementById('chat-input');
    if (input.value.trim()) {
        sendCommand(input.value.trim());
        input.value = '';
    }
}

// --- BOOTSTRAP ---
initTheme();
connect();
fetchState();
// Poll state for stats updates every 5s
setInterval(fetchState, 5000);

function connect() {
    connectionStatus.innerText = "CONNECTING...";
    connectionStatus.className = "text-xs text-yellow-500";

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    ws = new WebSocket(`${protocol}//${window.location.host}/ws/feed`);

    ws.onopen = () => {
        connectionStatus.innerText = "ONLINE";
        connectionStatus.className = "text-xs text-green-500 animate-pulse";
        addLog("System", "Uplink established.", "system-msg");
    };

    ws.onmessage = (event) => {
        if (event.data === "pong") return;

        try {
            const data = JSON.parse(event.data);
            handleMessage(data);
        } catch (e) {
            // If simple text
            addLog("System", event.data, "text-gray-400");
        }
    };

    ws.onclose = () => {
        connectionStatus.innerText = "OFFLINE";
        connectionStatus.className = "text-xs text-red-500";
        setTimeout(connect, 3000); // Retry connection
    };

    // Keep alive
    setInterval(() => {
        if (ws.readyState === WebSocket.OPEN) ws.send("ping");
    }, 10000);
}

function handleMessage(data) {
    if (data.type === 'log') {
        addLog(data.agent, data.payload, getAgentClass(data.agent));
    } else if (data.type === 'status') {
        updateStatus(data.payload);
    } else if (data.type === 'image_update') {
        // Refresh image with cache buster
        liveView.src = `/latest_view.png?t=${new Date().getTime()}`;
    }
}

function getAgentClass(agentName) {
    if (agentName === 'User') return 'user-msg';
    if (agentName === 'System') return 'system-msg';
    return 'text-white';
}

function addLog(agent, text, cssClass) {
    const div = document.createElement('div');
    div.className = `log-entry ${cssClass} text-sm`;

    // Parse timestamp if needed, for now just simple
    const time = new Date().toLocaleTimeString([], { hour12: false });
    div.innerHTML = `<span class="opacity-50 mr-2">[${time}]</span> <span class="font-bold">${agent}:</span> ${text}`;

    feedContainer.prepend(div);
    // feedContainer.scrollTop = 0; // Optional: Force scroll to top? Default is top.
}

function updateStatus(status) {
    statusIndicator.innerText = status;
    if (status === 'RUNNING') {
        statusIndicator.className = "px-3 py-1 text-xs font-bold bg-green-900 text-green-100 rounded animate-pulse";
    } else if (status === 'STOPPED') {
        statusIndicator.className = "px-3 py-1 text-xs font-bold bg-red-900 text-red-100 rounded";
    } else {
        statusIndicator.className = "px-3 py-1 text-xs font-bold bg-gray-800 text-gray-300 rounded";
    }
}

async function sendCommand(cmd) {
    try {
        const response = await fetch('/api/command', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ command: cmd })
        });
        const res = await response.json();
        addLog("User", `Command Sent: ${cmd}`, "user-msg");
    } catch (e) {
        addLog("System", "Failed to send command.", "error-msg");
    }
}

function handleChat(e) {
    e.preventDefault();
    const input = document.getElementById('chat-input');
    const cmd = input.value.trim();
    if (cmd) {
        sendCommand(cmd);
        input.value = '';
    }
}

// Start
connect();
fetchState();

async function fetchState() {
    try {
        const response = await fetch('/api/state');
        const data = await response.json();

        // Update Query
        document.getElementById('config-query').value = data.query;

        // Update CV Status
        const cvStatus = document.getElementById('cv-status');
        if (data.cv_loaded) {
            cvStatus.innerText = "LOADED";
            cvStatus.className = "text-xs font-bold text-neon-green";
        } else {
            cvStatus.innerText = "MISSING";
            cvStatus.className = "text-xs font-bold text-red-500";
        }

        // Update System Status
        updateStatus(data.status);

    } catch (e) {
        console.error("Failed to fetch state:", e);
    }
}

async function saveConfig(key, value) {
    try {
        const response = await fetch('/api/config', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ key, value })
        });
        await response.json();
        addLog("System", `Configuration Updated: ${key}`, "system-msg");
    } catch (e) {
        addLog("System", "Failed to save configuration.", "error-msg");
    }
}

async function uploadCV(input) {
    if (input.files.length === 0) return;

    const file = input.files[0];
    const formData = new FormData();
    formData.append("file", file);

    addLog("System", "Uploading CV...", "text-gray-400");

    try {
        const response = await fetch('/api/upload_cv', {
            method: 'POST',
            body: formData
        });
        const data = await response.json();

        if (data.status === "success") {
            addLog("System", "CV Ingested Successfully.", "system-msg");
            fetchState(); // Refresh status
        } else {
            addLog("System", `CV Upload Error: ${data.message}`, "error-msg");
        }
    } catch (e) {
        addLog("System", "CV Upload Failed.", "error-msg");
    }
}
