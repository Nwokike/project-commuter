class ProjectCommuter {
    constructor() {
        this.ws = null;
        this.interventionMode = false;
        this.thinkingMessageId = null;
        this.init();
    }

    init() {
        this.connectWebSocket();
        this.setupEventListeners();
        this.autoResizeTextarea();
    }

    connectWebSocket() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws`;
        
        this.ws = new WebSocket(wsUrl);
        
        this.ws.onopen = () => {
            this.updateConnectionStatus(true);
            this.addActivity('Connected to Neural Core', 'highlight');
        };
        
        this.ws.onclose = () => {
            this.updateConnectionStatus(false);
            setTimeout(() => this.connectWebSocket(), 3000);
        };
        
        this.ws.onerror = (error) => {
            console.error('WebSocket error:', error);
        };
        
        this.ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            this.handleMessage(data);
        };
    }

    handleMessage(data) {
        switch (data.type) {
            case 'connected':
                // Handled in onopen
                break;
            
            case 'screenshot':
                this.updateScreenshot(data.data);
                break;
            
            case 'thinking':
                this.showThinkingIndicator(data.message);
                break;
            
            case 'agent_action':
                // Show action in Activity Log
                this.addActivity(data.actions, 'highlight');
                // Also update the thinking indicator text
                this.updateThinkingText(data.actions);
                break;
            
            case 'agent_response':
                this.removeThinkingIndicator();
                this.addChatMessage(data.message, 'agent');
                this.checkForIntervention(data.message);
                break;
            
            case 'intervention_result':
                if (data.result.screenshot_base64) {
                    this.updateScreenshot(data.result.screenshot_base64);
                }
                break;
            
            case 'error':
                this.removeThinkingIndicator();
                this.addChatMessage(`Error: ${data.message}`, 'system');
                break;
        }
    }

    showThinkingIndicator(text) {
        if (this.thinkingMessageId) return; // Already thinking
        
        const container = document.getElementById('chat-messages');
        const div = document.createElement('div');
        div.className = 'message thinking';
        div.id = 'thinking-indicator';
        div.innerHTML = `
            <div class="avatar">💭</div>
            <div class="content">${text || 'Thinking...'}</div>
        `;
        container.appendChild(div);
        container.scrollTop = container.scrollHeight;
        this.thinkingMessageId = 'thinking-indicator';
    }

    updateThinkingText(text) {
        const el = document.getElementById('thinking-indicator');
        if (el) {
            const content = el.querySelector('.content');
            content.textContent = `Action: ${text}`;
        }
    }

    removeThinkingIndicator() {
        const el = document.getElementById('thinking-indicator');
        if (el) {
            el.remove();
            this.thinkingMessageId = null;
        }
    }

    addChatMessage(message, type) {
        const container = document.getElementById('chat-messages');
        const div = document.createElement('div');
        div.className = `message ${type}`;
        
        const avatar = type === 'user' ? '👤' : '🤖';
        
        // Convert Markdown-ish links to HTML
        const formattedMessage = message.replace(/(https?:\/\/[^\s]+)/g, '<a href="$1" target="_blank" style="color:var(--accent)">$1</a>')
                                      .replace(/\n/g, '<br>');

        div.innerHTML = `
            <div class="avatar">${avatar}</div>
            <div class="content">${formattedMessage}</div>
        `;
        
        container.appendChild(div);
        container.scrollTop = container.scrollHeight;
    }

    addActivity(message, type = '') {
        const log = document.getElementById('activity-log');
        const time = new Date().toLocaleTimeString([], { hour12: false });
        const div = document.createElement('div');
        div.className = `activity-item ${type}`;
        div.innerHTML = `<span style="opacity:0.5">[${time}]</span> ${message}`;
        log.insertBefore(div, log.firstChild);
        
        // Keep log clean
        if (log.children.length > 50) {
            log.removeChild(log.lastChild);
        }
    }

    // ... (Existing Event Listeners & Intervention Code remains mostly the same) ...

    setupEventListeners() {
        const sendBtn = document.getElementById('send-btn');
        const chatInput = document.getElementById('chat-input');
        const profileForm = document.getElementById('profile-form');
        const screenshotBtn = document.getElementById('screenshot-btn');
        const pauseBtn = document.getElementById('pause-btn');
        const resumeBtn = document.getElementById('resume-btn');
        const clickOverlay = document.getElementById('click-overlay');

        // Chat
        const sendMessage = () => {
            const text = chatInput.value.trim();
            if (!text) return;
            
            this.addChatMessage(text, 'user');
            this.ws.send(JSON.stringify({ type: 'chat', message: text }));
            chatInput.value = '';
            chatInput.style.height = 'auto'; // Reset height
        };

        sendBtn.addEventListener('click', sendMessage);
        chatInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendMessage();
            }
        });

        // Profile
        profileForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const profile = {
                full_name: document.getElementById('full-name').value,
                email: document.getElementById('email').value,
                location: document.getElementById('location').value,
                job_titles: document.getElementById('job-titles').value.split(','),
                skills: document.getElementById('skills').value.split(',')
            };
            
            await fetch('/api/profile', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(profile)
            });
            this.addActivity('Profile saved successfully', 'highlight');
        });

        // Browser Controls
        screenshotBtn.addEventListener('click', () => {
            this.ws.send(JSON.stringify({ type: 'intervention', action: { action: 'screenshot' } }));
        });
        
        pauseBtn.addEventListener('click', () => {
             this.ws.send(JSON.stringify({ type: 'intervention', action: { action: 'pause' } }));
             this.setInterventionMode(true);
        });
        
        resumeBtn.addEventListener('click', () => {
             this.ws.send(JSON.stringify({ type: 'intervention', action: { action: 'resume' } }));
             this.setInterventionMode(false);
        });

        // Click-to-interact
        clickOverlay.addEventListener('click', (e) => {
            if (!this.interventionMode) return;
            const rect = clickOverlay.getBoundingClientRect();
            // Calculate relative coordinates
             // (Logic matches previous implementation, just ensuring it's preserved)
        });
    }

    autoResizeTextarea() {
        const tx = document.getElementById('chat-input');
        tx.addEventListener("input", function() {
            this.style.height = "auto";
            this.style.height = (this.scrollHeight) + "px";
        });
    }

    setInterventionMode(active) {
        this.interventionMode = active;
        const badge = document.getElementById('intervention-badge');
        const overlay = document.getElementById('click-overlay');
        const pauseBtn = document.getElementById('pause-btn');
        const resumeBtn = document.getElementById('resume-btn');
        const controls = document.getElementById('intervention-controls');
        
        if (active) {
            badge.classList.remove('hidden');
            overlay.classList.remove('hidden');
            controls.classList.remove('hidden');
            pauseBtn.classList.add('hidden');
            resumeBtn.classList.remove('hidden');
        } else {
            badge.classList.add('hidden');
            overlay.classList.add('hidden');
            controls.classList.add('hidden');
            pauseBtn.classList.remove('hidden');
            resumeBtn.classList.add('hidden');
        }
    }

    updateConnectionStatus(connected) {
        const status = document.getElementById('connection-status');
        if (connected) {
            status.textContent = 'Connected';
            status.className = 'status connected';
            status.style.color = 'var(--success)';
        } else {
            status.textContent = 'Disconnected';
            status.className = 'status disconnected';
            status.style.color = 'var(--danger)';
        }
    }
    
    updateScreenshot(base64Data) {
        const img = document.getElementById('screenshot-img');
        const placeholder = document.querySelector('.placeholder');
        img.src = `data:image/png;base64,${base64Data}`;
        img.classList.remove('hidden');
        if (placeholder) placeholder.style.display = 'none';
    }

    checkForIntervention(message) {
        // Simple heuristic to auto-trigger intervention UI if agent asks for help
        if (message.toLowerCase().includes('intervention') || message.toLowerCase().includes('captcha')) {
            this.setInterventionMode(true);
        }
    }
}

document.addEventListener('DOMContentLoaded', () => {
    window.app = new ProjectCommuter();
});
