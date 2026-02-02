class ProjectCommuter {
    constructor() {
        this.ws = null;
        this.interventionMode = false;
        this.init();
    }

    init() {
        this.connectWebSocket();
        this.setupEventListeners();
    }

    connectWebSocket() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws`;
        
        this.ws = new WebSocket(wsUrl);
        
        this.ws.onopen = () => {
            this.updateConnectionStatus(true);
            this.addActivity('Connected to server');
        };
        
        this.ws.onclose = () => {
            this.updateConnectionStatus(false);
            this.addActivity('Disconnected from server');
            setTimeout(() => this.connectWebSocket(), 3000);
        };
        
        this.ws.onerror = (error) => {
            console.error('WebSocket error:', error);
            this.addActivity('Connection error');
        };
        
        this.ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            this.handleMessage(data);
        };
    }

    handleMessage(data) {
        switch (data.type) {
            case 'connected':
                this.addActivity(data.message);
                break;
            
            case 'screenshot':
                this.updateScreenshot(data.data);
                break;
            
            case 'thinking':
                this.addChatMessage(data.message, 'thinking');
                this.addActivity('Agent is thinking...');
                break;
            
            case 'agent_response':
                this.removeThinkingMessages();
                this.addChatMessage(data.message, 'agent');
                this.addActivity('Agent responded');
                this.checkForIntervention(data.message);
                break;
            
            case 'agent_action':
                this.addActivity(`Action: ${data.actions}`);
                break;
            
            case 'intervention_result':
                if (data.result.screenshot_base64) {
                    this.updateScreenshot(data.result.screenshot_base64);
                }
                break;
            
            case 'error':
                this.addChatMessage(`Error: ${data.message}`, 'system');
                this.addActivity(`Error: ${data.message}`);
                break;
        }
    }

    checkForIntervention(message) {
        const lowerMessage = message.toLowerCase();
        if (lowerMessage.includes('intervention') || 
            lowerMessage.includes('captcha') || 
            lowerMessage.includes('login') ||
            lowerMessage.includes('verify')) {
            this.setInterventionMode(true);
        }
    }

    setInterventionMode(active) {
        this.interventionMode = active;
        const badge = document.getElementById('intervention-badge');
        const controls = document.getElementById('intervention-controls');
        const overlay = document.getElementById('click-overlay');
        const pauseBtn = document.getElementById('pause-btn');
        const resumeBtn = document.getElementById('resume-btn');
        
        if (active) {
            badge.classList.remove('hidden');
            controls.classList.remove('hidden');
            overlay.classList.remove('hidden');
            pauseBtn.classList.add('hidden');
            resumeBtn.classList.remove('hidden');
            this.addActivity('INTERVENTION MODE ACTIVE');
        } else {
            badge.classList.add('hidden');
            controls.classList.add('hidden');
            overlay.classList.add('hidden');
            pauseBtn.classList.remove('hidden');
            resumeBtn.classList.add('hidden');
            this.addActivity('Intervention mode ended');
        }
    }

    updateScreenshot(base64Data) {
        const img = document.getElementById('screenshot-img');
        const placeholder = document.querySelector('.placeholder');
        
        img.src = `data:image/png;base64,${base64Data}`;
        img.classList.remove('hidden');
        if (placeholder) {
            placeholder.style.display = 'none';
        }
    }

    setupEventListeners() {
        const sendBtn = document.getElementById('send-btn');
        const chatInput = document.getElementById('chat-input');
        const profileForm = document.getElementById('profile-form');
        const screenshotBtn = document.getElementById('screenshot-btn');
        const pauseBtn = document.getElementById('pause-btn');
        const resumeBtn = document.getElementById('resume-btn');
        const sendTextBtn = document.getElementById('send-text-btn');
        const typeInput = document.getElementById('type-input');
        const screenshotImg = document.getElementById('screenshot-img');
        const clickOverlay = document.getElementById('click-overlay');

        sendBtn.addEventListener('click', () => this.sendMessage());
        
        chatInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });

        profileForm.addEventListener('submit', (e) => {
            e.preventDefault();
            this.saveProfile();
        });

        screenshotBtn.addEventListener('click', () => this.requestScreenshot());
        pauseBtn.addEventListener('click', () => this.sendInterventionAction({ action: 'pause' }));
        resumeBtn.addEventListener('click', () => {
            this.sendInterventionAction({ action: 'resume' });
            this.setInterventionMode(false);
            this.sendMessage('resume');
        });

        sendTextBtn.addEventListener('click', () => {
            const text = typeInput.value;
            if (text) {
                this.sendInterventionAction({ action: 'type', text: text });
                typeInput.value = '';
            }
        });

        typeInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                const text = typeInput.value;
                if (text) {
                    this.sendInterventionAction({ action: 'type', text: text });
                    typeInput.value = '';
                }
            }
        });

        screenshotImg.addEventListener('click', (e) => {
            if (!this.interventionMode) return;
            
            const rect = screenshotImg.getBoundingClientRect();
            const scaleX = screenshotImg.naturalWidth / rect.width;
            const scaleY = screenshotImg.naturalHeight / rect.height;
            
            const x = Math.round((e.clientX - rect.left) * scaleX);
            const y = Math.round((e.clientY - rect.top) * scaleY);
            
            this.sendInterventionAction({ action: 'click', x: x, y: y });
            this.addActivity(`Clicked at (${x}, ${y})`);
        });

        clickOverlay.addEventListener('click', (e) => {
            const img = document.getElementById('screenshot-img');
            const rect = img.getBoundingClientRect();
            const scaleX = img.naturalWidth / rect.width;
            const scaleY = img.naturalHeight / rect.height;
            
            const x = Math.round((e.clientX - rect.left) * scaleX);
            const y = Math.round((e.clientY - rect.top) * scaleY);
            
            this.sendInterventionAction({ action: 'click', x: x, y: y });
            this.addActivity(`Clicked at (${x}, ${y})`);
        });
    }

    sendMessage() {
        const chatInput = document.getElementById('chat-input');
        const message = chatInput.value.trim();
        
        if (!message) return;
        
        this.addChatMessage(message, 'user');
        chatInput.value = '';
        
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify({
                type: 'chat',
                message: message
            }));
            this.addActivity('Message sent');
        } else {
            this.addChatMessage('Not connected to server', 'system');
        }
    }

    sendInterventionAction(action) {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify({
                type: 'intervention',
                action: action
            }));
        }
    }

    requestScreenshot() {
        this.sendInterventionAction({ action: 'screenshot' });
    }

    async saveProfile() {
        const profile = {
            full_name: document.getElementById('full-name').value,
            email: document.getElementById('email').value,
            phone: document.getElementById('phone').value,
            location: document.getElementById('location').value,
            job_titles: document.getElementById('job-titles').value.split(',').map(s => s.trim()).filter(s => s),
            skills: document.getElementById('skills').value.split(',').map(s => s.trim()).filter(s => s)
        };

        try {
            const response = await fetch('/api/profile', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(profile)
            });
            
            if (response.ok) {
                this.addActivity('Profile saved');
                this.addChatMessage('Your profile has been saved!', 'system');
            }
        } catch (error) {
            console.error('Failed to save profile:', error);
        }
    }

    addChatMessage(message, type) {
        const container = document.getElementById('chat-messages');
        const div = document.createElement('div');
        div.className = `message ${type}`;
        div.innerHTML = `<p>${this.escapeHtml(message)}</p>`;
        container.appendChild(div);
        container.scrollTop = container.scrollHeight;
    }

    removeThinkingMessages() {
        const messages = document.querySelectorAll('.message.thinking');
        messages.forEach(m => m.remove());
    }

    addActivity(message) {
        const log = document.getElementById('activity-log');
        const time = new Date().toLocaleTimeString();
        const div = document.createElement('div');
        div.className = 'activity-item';
        div.textContent = `[${time}] ${message}`;
        log.insertBefore(div, log.firstChild);
        
        while (log.children.length > 50) {
            log.removeChild(log.lastChild);
        }
    }

    updateConnectionStatus(connected) {
        const status = document.getElementById('connection-status');
        if (connected) {
            status.textContent = 'Connected';
            status.className = 'status connected';
        } else {
            status.textContent = 'Disconnected';
            status.className = 'status disconnected';
        }
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

document.addEventListener('DOMContentLoaded', () => {
    window.app = new ProjectCommuter();
});
