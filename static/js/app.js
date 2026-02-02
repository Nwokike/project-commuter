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
            document.getElementById('neural-feed-panel').classList.add('collapsed');
        }, 2000);
    }

    connectWebSocket() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws`;
        
        this.ws = new WebSocket(wsUrl);
        
        this.ws.onopen = () => {
            document.getElementById('connection-status').classList.add('connected');
            this.addActivity('Neural Core Online. Waiting for CV...', 'highlight');
        };
        
        this.ws.onclose = () => {
            document.getElementById('connection-status').classList.remove('connected');
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
                // Log to Neural Feed (Newest Top)
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
        const time = new Date().toLocaleTimeString([], { hour12: false, hour: '2-digit', minute:'2-digit', second:'2-digit' });
        
        const div = document.createElement('div');
        div.className = `activity-item ${type}`;
        div.innerHTML = `<span class="time">[${time}]</span> ${message}`;
        
        // PREPEND: Insert at the very top
        if (log.firstChild) {
            log.insertBefore(div, log.firstChild);
        } else {
            log.appendChild(div);
        }
        
        // Limit history to 50 items
        if (log.children.length > 50) {
            log.removeChild(log.lastChild);
        }
    }

    setupEventListeners() {
        // 1. CV Upload
        const uploadBtn = document.getElementById('upload-cv-btn');
        const fileInput = document.getElementById('cv-upload-input');
        
        uploadBtn.addEventListener('click', () => fileInput.click());
        
        fileInput.addEventListener('change', async (e) => {
            if (e.target.files.length > 0) {
                const file = e.target.files[0];
                const formData = new FormData();
                formData.append('file', file);
                
                this.addActivity(`Uploading CV: ${file.name}...`, 'highlight');
                
                try {
                    const response = await fetch('/api/upload_cv', {
                        method: 'POST',
                        body: formData
                    });
                    const result = await response.json();
                    if (result.status === 'success') {
                        this.addActivity('CV Analyzed. Context Updated.', 'highlight');
                        this.addChatMessage(`I've analyzed your CV, ${result.profile.full_name}. I know your skills in ${result.profile.skills.slice(0,3).join(', ')}. Ready to apply.`, 'agent');
                    }
                } catch (error) {
                    this.addActivity('CV Upload Failed', 'error');
                }
            }
        });

        // 2. Feed Toggle
        document.getElementById('feed-toggle').addEventListener('click', () => {
            document.getElementById('neural-feed-panel').classList.toggle('collapsed');
        });

        // 3. Chat Send
        const sendBtn = document.getElementById('send-btn');
        const chatInput = document.getElementById('chat-input');
        
        const sendMessage = () => {
            const text = chatInput.value.trim();
            if (!text) return;
            this.addChatMessage(text, 'user');
            this.ws.send(JSON.stringify({ type: 'chat', message: text }));
            chatInput.value = '';
        };

        sendBtn.addEventListener('click', sendMessage);
        chatInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendMessage();
            }
        });
    }

    // ... (Helpers: showThinkingIndicator, updateScreenshot - similar to before) ...
    
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
        div.innerHTML = `<div class="avatar">${avatar}</div><div class="content">${message}</div>`;
        container.appendChild(div);
        container.scrollTop = container.scrollHeight;
    }

    updateScreenshot(base64Data) {
        const img = document.getElementById('screenshot-img');
        const placeholder = document.querySelector('.placeholder');
        img.src = `data:image/png;base64,${base64Data}`;
        img.classList.remove('hidden');
        if (placeholder) placeholder.style.display = 'none';
    }
}

document.addEventListener('DOMContentLoaded', () => {
    window.app = new ProjectCommuter();
});
