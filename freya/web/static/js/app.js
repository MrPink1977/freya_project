/**
 * Freya AI Assistant - Web GUI JavaScript
 * Handles WebSocket connections, API calls, and UI interactions
 */

// ============================================================================
// State Management
// ============================================================================

const state = {
    ws: null,
    connected: false,
    ollamaRunning: false,
    modelLoaded: null,
    debugOpen: false,
    stats: {
        messages: 0,
        memories: 0,
        tools: 0,
        sessionStart: Date.now(),
    },
};

// ============================================================================
// WebSocket Connection
// ============================================================================

function connectWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws`;

    state.ws = new WebSocket(wsUrl);

    state.ws.onopen = () => {
        console.log('WebSocket connected');
        state.connected = true;
        updateConnectionStatus(true);
        showToast('Connected to Freya', 'success');

        // Start heartbeat
        setInterval(() => {
            if (state.ws && state.ws.readyState === WebSocket.OPEN) {
                state.ws.send(JSON.stringify({ type: 'ping' }));
            }
        }, 30000);
    };

    state.ws.onmessage = (event) => {
        const message = JSON.parse(event.data);
        handleWebSocketMessage(message);
    };

    state.ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        showToast('Connection error', 'error');
    };

    state.ws.onclose = () => {
        console.log('WebSocket closed');
        state.connected = false;
        updateConnectionStatus(false);
        showToast('Disconnected from server', 'warning');

        // Attempt to reconnect after 5 seconds
        setTimeout(connectWebSocket, 5000);
    };
}

function handleWebSocketMessage(message) {
    console.log('Received:', message);

    switch (message.type) {
        case 'status':
            showToast(message.message, message.status || 'info');
            break;

        case 'error':
            showToast(message.message, 'error');
            addLog('ERROR', message.message);
            break;

        case 'chat_response':
            addMessage('assistant', message.message);
            break;

        case 'pong':
            // Heartbeat response
            break;

        default:
            console.log('Unknown message type:', message.type);
    }
}

// ============================================================================
// API Calls
// ============================================================================

async function apiCall(endpoint, method = 'GET', body = null) {
    const options = {
        method,
        headers: {
            'Content-Type': 'application/json',
        },
    };

    if (body) {
        options.body = JSON.stringify(body);
    }

    try {
        const response = await fetch(endpoint, options);
        const data = await response.json();
        return data;
    } catch (error) {
        console.error('API call failed:', error);
        showToast(`API Error: ${error.message}`, 'error');
        return { status: 'error', message: error.message };
    }
}

// ============================================================================
// Ollama Controls
// ============================================================================

async function startOllama() {
    addLog('INFO', 'Starting Ollama server...');
    const result = await apiCall('/api/ollama/start', 'POST');

    if (result.status === 'success') {
        state.ollamaRunning = true;
        updateOllamaStatus(true);
        loadModelList();
    } else {
        addLog('ERROR', `Failed to start Ollama: ${result.message}`);
    }
}

async function stopOllama() {
    addLog('INFO', 'Stopping Ollama server...');
    const result = await apiCall('/api/ollama/stop', 'POST');

    if (result.status === 'success') {
        state.ollamaRunning = false;
        state.modelLoaded = null;
        updateOllamaStatus(false);
        document.getElementById('currentModel').textContent = 'No model loaded';
        document.getElementById('modelSelect').innerHTML = '<option value="">Select a model...</option>';
    }
}

async function loadModelList() {
    const result = await apiCall('/api/ollama/models');

    if (result.status === 'success') {
        const select = document.getElementById('modelSelect');
        select.innerHTML = '<option value="">Select a model...</option>';

        result.models.forEach(model => {
            const option = document.createElement('option');
            option.value = model.name;
            option.textContent = `${model.name} (${model.size})`;
            select.appendChild(option);
        });

        addLog('INFO', `Found ${result.models.length} models`);
    }
}

async function loadModel() {
    const select = document.getElementById('modelSelect');
    const modelName = select.value;

    if (!modelName) {
        showToast('Please select a model', 'warning');
        return;
    }

    addLog('INFO', `Loading model: ${modelName}...`);
    showToast(`Loading ${modelName}...`, 'info');

    const result = await apiCall('/api/ollama/load-model', 'POST', { name: modelName });

    if (result.status === 'success') {
        state.modelLoaded = modelName;
        document.getElementById('currentModel').textContent = `✓ ${modelName}`;
        document.getElementById('currentModel').style.color = 'var(--success)';

        // Enable chat input
        document.getElementById('chatInput').disabled = false;
        document.getElementById('sendMessage').disabled = false;

        addLog('INFO', `Model ${modelName} loaded successfully`);
    }
}

function updateOllamaStatus(running) {
    const statusBadge = document.getElementById('ollamaStatus');
    if (running) {
        statusBadge.innerHTML = '<span class="badge badge-online">Online</span>';
    } else {
        statusBadge.innerHTML = '<span class="badge badge-offline">Offline</span>';
    }

    // Update network debug info
    const apiStatus = document.getElementById('ollamaApiStatus');
    if (apiStatus) {
        apiStatus.className = running ? 'badge badge-online' : 'badge badge-offline';
        apiStatus.textContent = running ? 'Online' : 'Offline';
    }
}

// ============================================================================
// Chat Functions
// ============================================================================

async function sendMessage() {
    const input = document.getElementById('chatInput');
    const message = input.value.trim();

    if (!message) return;

    // Add user message to chat
    addMessage('user', message);
    input.value = '';

    // Update stats
    state.stats.messages++;
    updateStats();

    // Send to API
    addLog('INFO', `Sending message: ${message}`);
    const result = await apiCall('/api/chat', 'POST', { message });

    if (result.status === 'success') {
        // Response will come via WebSocket
    }
}

function addMessage(role, text) {
    const messagesContainer = document.getElementById('chatMessages');
    const messageDiv = document.createElement('div');
    messageDiv.className = `${role}-message`;
    messageDiv.textContent = text;
    messagesContainer.appendChild(messageDiv);

    // Scroll to bottom
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

function clearChat() {
    const messagesContainer = document.getElementById('chatMessages');
    messagesContainer.innerHTML = '<div class="system-message">Chat cleared.</div>';
}

// ============================================================================
// Agent Status
// ============================================================================

async function loadAgentStatus() {
    const result = await apiCall('/api/debug/agents');

    if (result.agents) {
        updateAgentList(result.agents);
        updateAgentDebugList(result.agents);
    }
}

function updateAgentList(agents) {
    const container = document.getElementById('agentList');
    container.innerHTML = '';

    agents.forEach(agent => {
        const item = document.createElement('div');
        item.className = 'agent-item';
        item.innerHTML = `
            <span class="agent-name">${agent.name}</span>
            <span class="badge badge-${agent.status === 'ready' ? 'ready' : 'offline'}">
                ${agent.status}
            </span>
        `;
        container.appendChild(item);
    });
}

function updateAgentDebugList(agents) {
    const container = document.getElementById('agentDebugList');
    container.innerHTML = '';

    agents.forEach(agent => {
        const item = document.createElement('div');
        item.className = 'agent-debug-item';
        item.innerHTML = `
            <h4>${agent.name}</h4>
            <p>Status: <span class="badge badge-${agent.status === 'ready' ? 'ready' : 'offline'}">${agent.status}</span></p>
            <p>Messages: ${agent.messages_processed || 0}</p>
        `;
        container.appendChild(item);
    });
}

// ============================================================================
// Debug Console
// ============================================================================

function toggleDebugConsole() {
    const debugConsole = document.getElementById('debugConsole');
    state.debugOpen = !state.debugOpen;

    if (state.debugOpen) {
        debugConsole.style.display = 'flex';
        loadDebugData();
    } else {
        debugConsole.style.display = 'none';
    }
}

async function loadDebugData() {
    loadAgentStatus();
    // Add more debug data loading here
}

function addLog(level, message) {
    const container = document.getElementById('logContainer');
    const time = new Date().toLocaleTimeString();

    const entry = document.createElement('div');
    entry.className = `log-entry log-${level.toLowerCase()}`;
    entry.innerHTML = `
        <span class="log-time">${time}</span>
        <span class="log-level">${level}</span>
        <span class="log-message">${message}</span>
    `;

    container.appendChild(entry);

    // Limit to 100 log entries
    if (container.children.length > 100) {
        container.removeChild(container.firstChild);
    }

    // Scroll to bottom
    container.scrollTop = container.scrollHeight;
}

function addEvent(type) {
    const container = document.getElementById('eventList');
    const time = new Date().toLocaleTimeString();

    const entry = document.createElement('div');
    entry.className = 'event-item';
    entry.innerHTML = `
        <span class="event-time">${time}</span>
        <span class="event-type">${type}</span>
    `;

    container.insertBefore(entry, container.firstChild);

    // Limit to 50 events
    if (container.children.length > 50) {
        container.removeChild(container.lastChild);
    }
}

// ============================================================================
// UI Updates
// ============================================================================

function updateConnectionStatus(connected) {
    const statusIndicator = document.getElementById('connectionStatus');
    const dot = statusIndicator.querySelector('.dot');
    const text = statusIndicator.querySelector('.text');

    if (connected) {
        dot.className = 'dot online';
        text.textContent = 'Connected';
    } else {
        dot.className = 'dot offline';
        text.textContent = 'Disconnected';
    }

    // Update debug network status
    const wsStatus = document.getElementById('wsStatus');
    if (wsStatus) {
        wsStatus.className = connected ? 'badge badge-online' : 'badge badge-offline';
        wsStatus.textContent = connected ? 'Connected' : 'Disconnected';
    }
}

function updateStats() {
    document.getElementById('statMessages').textContent = state.stats.messages;
    document.getElementById('statMemories').textContent = state.stats.memories;
    document.getElementById('statTools').textContent = state.stats.tools;

    // Update session time
    const elapsed = Math.floor((Date.now() - state.stats.sessionStart) / 1000);
    const minutes = Math.floor(elapsed / 60);
    const seconds = elapsed % 60;
    document.getElementById('statTime').textContent = `${minutes}:${seconds.toString().padStart(2, '0')}`;
}

function showToast(message, type = 'info') {
    const container = document.getElementById('toastContainer');

    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.textContent = message;

    container.appendChild(toast);

    // Remove after 4 seconds
    setTimeout(() => {
        toast.style.opacity = '0';
        setTimeout(() => container.removeChild(toast), 300);
    }, 4000);
}

// ============================================================================
// Event Listeners
// ============================================================================

document.addEventListener('DOMContentLoaded', () => {
    // Ollama controls
    document.getElementById('startOllama').addEventListener('click', startOllama);
    document.getElementById('stopOllama').addEventListener('click', stopOllama);
    document.getElementById('loadModel').addEventListener('click', loadModel);

    // Chat controls
    document.getElementById('sendMessage').addEventListener('click', sendMessage);
    document.getElementById('chatInput').addEventListener('keypress', (e) => {
        if (e.key === 'Enter') sendMessage();
    });
    document.getElementById('clearChat').addEventListener('click', clearChat);

    // Debug console
    document.getElementById('debugToggle').addEventListener('click', toggleDebugConsole);
    document.getElementById('closeDebug').addEventListener('click', toggleDebugConsole);

    // Debug tabs
    document.querySelectorAll('.debug-tab').forEach(tab => {
        tab.addEventListener('click', () => {
            // Remove active class from all tabs and panels
            document.querySelectorAll('.debug-tab').forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.debug-panel').forEach(p => p.classList.remove('active'));

            // Add active class to clicked tab and corresponding panel
            tab.classList.add('active');
            const panelId = 'tab-' + tab.dataset.tab;
            document.getElementById(panelId).classList.add('active');
        });
    });

    // Initialize
    connectWebSocket();
    updateStats();

    // Update session time every second
    setInterval(updateStats, 1000);

    // Load agent status every 5 seconds
    setInterval(loadAgentStatus, 5000);
    loadAgentStatus();

    addLog('INFO', 'Freya Web GUI initialized');
    addEvent('app.initialized');
});
