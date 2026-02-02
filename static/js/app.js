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
        
        // Auto-expand logs briefly on load then collapse
        setTimeout(() => {
            const panel = document.getElementById('neural-feed-panel');
            if(panel) panel.classList.add('collapsed');
        }, 2000);
    }

    connectWebSocket() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws`;
        
        this.ws = new WebSocket(wsUrl);
        
        this.ws.onopen = () => {
            document.getElementById('connection-status').classList.add('connected');
            document.getElementById('connection-status').title = "Connected";
            this.addActivity('Neural Core Online. Waiting for CV...', 'highlight');
        };
        
        this.ws.onclose = () => {
            document.getElementById('connection-status').classList.remove('connected');
            document.getElementById('connection-status').title = "Disconnected";
            setTimeout(() => this.connectWebSocket(), 3000);
        };
        
        this.ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            this.handleMessage(data);
        };
    }

    handleMessage(data) {
        switch (data.type) {
            case 'screenshot':
                this.updateScreenshot(data.data);
                break;
            case 'thinking':
                this.showThinkingIndicator(data.message);
                break;
            case 'agent_action':
                this.addActivity(data.actions, 'highlight');
                this.updateThinkingText(data.actions);
                break;
            case 'agent_response':
                this.removeThinkingIndicator();
                this.addChatMessage(data.message, 'agent');
                break;
            case 'error':
                this.removeThinkingIndicator();
                this.addActivity(`ERROR: ${data.message}`, 'error');
                break;
        }
    }

    addActivity(message, type = '') {
        const log = document.getElementById('activity-log');
        if (!log) return;
        
        const time = new Date().toLocaleTimeString([], { hour12: false, hour: '2-digit', minute:'2-digit', second:'2-digit' });
        
        const div = document.createElement('div');
        div.className = `activity-item ${type}`;
        div.innerHTML = `<span class="time">[${time}]</span> ${message}`;
        
        if (log.firstChild) {
            log.insertBefore(div, log.firstChild);
        } else {
            log.appendChild(div);
        }
        
        if (log.children.length > 50) {
            log.removeChild(log.lastChild);
        }
    }

    setupEventListeners() {
        // 1. CV Upload
        const uploadBtn = document.getElementById('upload-cv-btn');
        const fileInput = document.getElementById('cv-upload-input');
        
        if (uploadBtn && fileInput) {
            uploadBtn.addEventListener('click', () => fileInput.click());
            
            fileInput.addEventListener('change', async (e) => {
                if (e.target.files.length > 0) {
                    const file = e.target.files[0];
                    const formData = new FormData();
                    formData.append('file', file);
                    
                    this.addActivity(`Uploading CV: ${file.name}...`, 'highlight');
                    this.addChatMessage(`Uploading ${file.name}...`, 'user');
                    
                    try {
                        const response = await fetch('/api/upload_cv', {
                            method: 'POST',
                            body: formData
                        });
                        const result = await response.json();
                        if (result.status === 'success') {
                            this.addActivity('CV Analyzed. Auto-launching LinkedIn...', 'highlight');
                            this.addChatMessage(`I've read your CV, ${result.profile.full_name}. Opening LinkedIn login page for you now...`, 'agent');
                            
                            // AUTO-ACTION: Open LinkedIn immediately so user can log in
                            this.sendChatMessage("Open linkedin.com/login so I can sign in");
                        }
                    } catch (error) {
                        this.addActivity('CV Upload Failed', 'error');
                        this.addChatMessage('Error uploading CV. Please try again.', 'system');
                    }
                }
            });
        }

        // 2. Feed Toggle
        const feedToggle = document.getElementById('feed-toggle');
        if (feedToggle) {
            feedToggle.addEventListener('click', () => {
                document.getElementById('neural-feed-panel').classList.toggle('collapsed');
            });
        }

        // 3. Chat Send
        const sendBtn = document.getElementById('send-btn');
        const chatInput = document.getElementById('chat-input');
        
        if (sendBtn && chatInput) {
            sendBtn.addEventListener('click', () => this.handleUserSend());
            chatInput.addEventListener('keydown', (e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    this.handleUserSend();
                }
            });
        }
        
        // 4. Intervention Controls
        const intSendBtn = document.getElementById('send-text-btn');
        const intInput = document.getElementById('type-input');
        const resumeBtn = document.getElementById('resume-btn');
        
        if (intSendBtn) {
            intSendBtn.addEventListener('click', () => {
                const text = intInput.value;
                if(text) {
                     this.ws.send(JSON.stringify({ type: 'intervention', action: { action: 'type', text: text, selector: 'body' } })); // Simple type fallback
                     intInput.value = '';
                }
            });
        }
        
        if (resumeBtn) {
            resumeBtn.addEventListener('click', () => {
                this.ws.send(JSON.stringify({ type: 'intervention', action: { action: 'resume' } }));
                document.getElementById('intervention-controls').classList.add('hidden');
            });
        }
    }

    handleUserSend() {
        const chatInput = document.getElementById('chat-input');
        const text = chatInput.value.trim();
        if (!text) return;
        this.addChatMessage(text, 'user');
        this.sendChatMessage(text);
        chatInput.value = '';
    }

    sendChatMessage(text) {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify({ type: 'chat', message: text }));
        } else {
            this.addActivity('Error: WebSocket not connected', 'error');
        }
    }

    showThinkingIndicator(text) {
        if (this.thinkingMessageId) return;
        const container = document.getElementById('chat-messages');
        const div = document.createElement('div');
        div.className = 'message thinking';
        div.id = 'thinking-indicator';
        div.innerHTML = `<div class="avatar">💭</div><div class="content">${text || 'Thinking...'}</div>`;
        container.appendChild(div);
        container.scrollTop = container.scrollHeight;
        this.thinkingMessageId = 'thinking-indicator';
    }

    updateThinkingText(text) {
        const el = document.getElementById('thinking-indicator');
        if (el) el.querySelector('.content').textContent = `Action: ${text}`;
    }

    removeThinkingIndicator() {
        const el = document.getElementById('thinking-indicator');
        if (el) { el.remove(); this.thinkingMessageId = null; }
    }

    addChatMessage(message, type) {
        const container = document.getElementById('chat-messages');
        const div = document.createElement('div');
        div.className = `message ${type}`;
        const avatar = type === 'user' ? '👤' : '🎯';
        
        // Convert URLs to links
        const formatted = message.replace(/(https?:\/\/[^\s]+)/g, '<a href="$1" target="_blank" style="color:#fff;text-decoration:underline;">$1</a>');
        
        div.innerHTML = `<div class="avatar">${avatar}</div><div class="content">${formatted}</div>`;
        container.appendChild(div);
        container.scrollTop = container.scrollHeight;
    }

    updateScreenshot(base64Data) {
        const img = document.getElementById('screenshot-img');
        const placeholder = document.querySelector('.placeholder');
        if (img) {
            img.src = `data:image/png;base64,${base64Data}`;
            img.classList.remove('hidden');
        }
        if (placeholder) placeholder.style.display = 'none';
    }
}

document.addEventListener('DOMContentLoaded', () => {
    window.app = new ProjectCommuter();
});
