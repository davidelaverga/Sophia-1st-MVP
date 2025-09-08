// Sophia DeFi Assistant - Frontend JavaScript

class SophiaChat {
    constructor() {
        this.apiUrl = localStorage.getItem('sophia_api_url') || window.location.origin;
        this.apiKey = localStorage.getItem('sophia_api_key') || 'dev-key'; // Default API key
        this.sessionId = this.generateSessionId();
        this.isRecording = false;
        this.mediaRecorder = null;
        this.audioChunks = [];
        this.recordingStartTime = null;
        this.minRecordingDuration = 500; // Minimum 500ms recording
        
        this.initializeEventListeners();
        this.loadSettings();
    }

    generateSessionId() {
        // Generate a UUID v4
        return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
            const r = Math.random() * 16 | 0;
            const v = c == 'x' ? r : (r & 0x3 | 0x8);
            return v.toString(16);
        });
    }

    initializeEventListeners() {
        // Text input events
        const textInput = document.getElementById('textInput');
        const sendBtn = document.getElementById('sendBtn');
        
        textInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendTextMessage();
            }
        });

        sendBtn.addEventListener('click', () => this.sendTextMessage());

        // Voice recording events
        const voiceBtn = document.getElementById('voiceBtn');
        
        // Mouse events
        voiceBtn.addEventListener('mousedown', (e) => {
            e.preventDefault();
            this.startRecording();
        });
        
        // Global mouse up to catch when user releases anywhere
        document.addEventListener('mouseup', () => {
            if (this.isRecording) {
                this.stopRecording();
            }
        });
        
        // Touch events for mobile
        voiceBtn.addEventListener('touchstart', (e) => {
            e.preventDefault();
            this.startRecording();
        });
        
        document.addEventListener('touchend', (e) => {
            if (this.isRecording) {
                e.preventDefault();
                this.stopRecording();
            }
        });
    }

    loadSettings() {
        const apiUrlInput = document.getElementById('apiUrl');
        const sessionDisplay = document.getElementById('sessionDisplay');
        
        if (this.apiUrl) {
            apiUrlInput.value = this.apiUrl;
        }
        sessionDisplay.value = this.sessionId;
    }

    saveSettings() {
        const apiUrl = document.getElementById('apiUrl').value;
        
        localStorage.setItem('sophia_api_url', apiUrl);
        this.apiUrl = apiUrl;
        
        this.showSuccessMessage('Settings saved successfully!');
        this.toggleSettings();
    }

    toggleSettings() {
        const panel = document.getElementById('settingsPanel');
        panel.classList.toggle('active');
    }

    async sendTextMessage() {
        const textInput = document.getElementById('textInput');
        const message = textInput.value.trim();
        
        if (!message) return;

        // Clear input and show user message
        textInput.value = '';
        this.addUserMessage(message);
        this.showTypingIndicator();

        try {
            const response = await fetch(`${this.apiUrl}/text-chat`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${this.apiKey}`
                },
                body: JSON.stringify({
                    message: message,
                    session_id: this.sessionId
                })
            });

            const result = await this.handleApiResponse(response);
            if (result) {
                this.hideTypingIndicator();
                this.addSophiaMessage(result);
            }

        } catch (error) {
            this.hideTypingIndicator();
            this.showError(`Failed to send message: ${error.message}`);
        }
    }

    async sendQuickMessage(message) {
        const textInput = document.getElementById('textInput');
        textInput.value = message;
        await this.sendTextMessage();
    }

    async startRecording() {
        if (this.isRecording) return;

        try {
            const stream = await navigator.mediaDevices.getUserMedia({ 
                audio: {
                    sampleRate: 16000,
                    channelCount: 1,
                    echoCancellation: true,
                    noiseSuppression: true
                } 
            });
            
            // Try to use WAV format if supported, otherwise fall back to WebM
            let options = { mimeType: 'audio/wav' };
            if (!MediaRecorder.isTypeSupported('audio/wav')) {
                options = { mimeType: 'audio/webm;codecs=opus' };
            }
            
            this.mediaRecorder = new MediaRecorder(stream, options);
            
            this.audioChunks = [];
            this.isRecording = true;
            this.recordingStartTime = Date.now();
            
            this.mediaRecorder.ondataavailable = (event) => {
                this.audioChunks.push(event.data);
            };
            
            this.mediaRecorder.onstop = () => {
                // Check minimum recording duration
                const recordingDuration = Date.now() - this.recordingStartTime;
                if (recordingDuration >= this.minRecordingDuration) {
                    this.processRecording();
                } else {
                    this.showError('Recording too short. Hold the button longer to record.');
                }
            };
            
            this.mediaRecorder.start();
            this.updateVoiceUI(true);
            
        } catch (error) {
            this.showError('Microphone access denied or not available');
            console.error('Recording error:', error);
        }
    }

    stopRecording() {
        if (!this.isRecording || !this.mediaRecorder) return;
        
        this.isRecording = false;
        this.mediaRecorder.stop();
        this.mediaRecorder.stream.getTracks().forEach(track => track.stop());
        this.updateVoiceUI(false);
    }

    updateVoiceUI(recording) {
        const voiceBtn = document.getElementById('voiceBtn');
        const recordingIndicator = document.getElementById('recordingIndicator');
        const voiceText = voiceBtn.querySelector('.voice-text');
        
        if (recording) {
            voiceBtn.classList.add('recording');
            recordingIndicator.classList.add('active');
            voiceText.textContent = 'Release to Send';
        } else {
            voiceBtn.classList.remove('recording');
            recordingIndicator.classList.remove('active');
            voiceText.textContent = 'Hold to Talk';
        }
    }

    async processRecording() {
        if (this.audioChunks.length === 0) {
            this.showError('No audio recorded');
            return;
        }

        this.showLoading(true);

        try {
            // Create audio blob with appropriate MIME type
            const mimeType = this.mediaRecorder.mimeType;
            const audioBlob = new Blob(this.audioChunks, { type: mimeType });
            const formData = new FormData();
            
            // Use appropriate file extension based on MIME type
            let fileName = 'recording.wav';
            if (mimeType.includes('webm')) {
                fileName = 'recording.webm';
            } else if (mimeType.includes('mp4')) {
                fileName = 'recording.mp4';
            }
            
            formData.append('file', audioBlob, fileName);
            
            if (this.sessionId) {
                formData.append('session_id', this.sessionId);
            }

            const response = await fetch(`${this.apiUrl}/defi-chat`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${this.apiKey}`
                },
                body: formData
            });

            const result = await this.handleApiResponse(response);
            if (result) {
                this.addUserMessage(result.transcript, result.user_emotion);
                this.addSophiaMessage(result);
            }

        } catch (error) {
            this.showError(`Voice message failed: ${error.message}`);
        } finally {
            this.showLoading(false);
        }
    }

    async handleApiResponse(response) {
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({ detail: 'Unknown error' }));
            throw new Error(errorData.detail || `HTTP ${response.status}`);
        }

        const result = await response.json();
        
        // Update session ID if provided
        if (result.session_id) {
            this.sessionId = result.session_id;
        }

        return result;
    }

    addUserMessage(text, emotion = null) {
        const messagesContainer = document.getElementById('chatMessages');
        const messageDiv = document.createElement('div');
        messageDiv.className = 'message user';
        
        const emotionBadge = emotion ? 
            `<span class="emotion-badge">${emotion.label} ${(emotion.confidence * 100).toFixed(0)}%</span>` : '';
        
        messageDiv.innerHTML = `
            <div class="avatar user-avatar">👤</div>
            <div class="message-content">
                <div class="message-text">${this.escapeHtml(text)}</div>
                <div class="message-meta">
                    <span>${new Date().toLocaleTimeString()}</span>
                    ${emotionBadge}
                </div>
            </div>
        `;
        
        messagesContainer.appendChild(messageDiv);
        this.scrollToBottom();
    }

    addSophiaMessage(result) {
        const messagesContainer = document.getElementById('chatMessages');
        const messageDiv = document.createElement('div');
        messageDiv.className = 'message sophia';
        
        const emotionBadge = result.sophia_emotion ? 
            `<span class="emotion-badge">${result.sophia_emotion.label} ${(result.sophia_emotion.confidence * 100).toFixed(0)}%</span>` : '';
        
        const audioControls = result.audio_url ? 
            `<div class="audio-controls">
                <button class="audio-btn" onclick="sophiaChat.playAudio('${result.audio_url}')">
                    🔊 Play Response
                </button>
            </div>` : '';
        
        const intentBadge = result.intent ? 
            `<span class="intent-badge">${result.intent.replace('_', ' ')}</span>` : '';

        messageDiv.innerHTML = `
            <div class="avatar sophia-avatar">
                <div class="avatar-pulse"></div>
                🤖
            </div>
            <div class="message-content">
                <div class="message-text">${this.escapeHtml(result.reply)}</div>
                ${audioControls}
                <div class="message-meta">
                    <span>${new Date().toLocaleTimeString()}</span>
                    <div>
                        ${intentBadge}
                        ${emotionBadge}
                    </div>
                </div>
            </div>
        `;
        
        messagesContainer.appendChild(messageDiv);
        this.scrollToBottom();

        // Auto-play audio if available
        if (result.audio_url) {
            setTimeout(() => this.playAudio(result.audio_url), 500);
        }
    }

    showTypingIndicator() {
        const messagesContainer = document.getElementById('chatMessages');
        const typingDiv = document.createElement('div');
        typingDiv.className = 'message sophia typing-indicator';
        typingDiv.id = 'typingIndicator';
        
        typingDiv.innerHTML = `
            <div class="avatar sophia-avatar">🤖</div>
            <div class="message-content">
                <div class="typing-dots">
                    <div class="typing-dot"></div>
                    <div class="typing-dot"></div>
                    <div class="typing-dot"></div>
                </div>
                <span style="margin-left: 10px; color: var(--text-muted);">Sophia is thinking...</span>
            </div>
        `;
        
        messagesContainer.appendChild(typingDiv);
        this.scrollToBottom();
    }

    hideTypingIndicator() {
        const typingIndicator = document.getElementById('typingIndicator');
        if (typingIndicator) {
            typingIndicator.remove();
        }
    }

    showLoading(show) {
        const overlay = document.getElementById('loadingOverlay');
        if (show) {
            overlay.classList.add('active');
        } else {
            overlay.classList.remove('active');
        }
    }

    showError(message) {
        const messagesContainer = document.getElementById('chatMessages');
        const errorDiv = document.createElement('div');
        errorDiv.className = 'error-message';
        errorDiv.innerHTML = `
            <strong>⚠️ Error:</strong> ${this.escapeHtml(message)}
        `;
        
        messagesContainer.appendChild(errorDiv);
        this.scrollToBottom();
        
        // Auto-remove after 5 seconds
        setTimeout(() => {
            if (errorDiv.parentNode) {
                errorDiv.remove();
            }
        }, 5000);
    }

    showSuccessMessage(message) {
        const messagesContainer = document.getElementById('chatMessages');
        const successDiv = document.createElement('div');
        successDiv.className = 'success-message';
        successDiv.innerHTML = `
            <strong>✅ Success:</strong> ${this.escapeHtml(message)}
        `;
        
        messagesContainer.appendChild(successDiv);
        this.scrollToBottom();
        
        // Auto-remove after 3 seconds
        setTimeout(() => {
            if (successDiv.parentNode) {
                successDiv.remove();
            }
        }, 3000);
    }

    async playAudio(audioUrl) {
        try {
            const audioPlayer = document.getElementById('audioPlayer');
            audioPlayer.src = audioUrl;
            await audioPlayer.play();
        } catch (error) {
            console.error('Audio playback failed:', error);
            this.showError('Audio playback failed');
        }
    }

    scrollToBottom() {
        const messagesContainer = document.getElementById('chatMessages');
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    // Health check to verify API connection
    async checkApiHealth() {
        try {
            const response = await fetch(`${this.apiUrl}/health`);
            if (response.ok) {
                const statusDot = document.querySelector('.status-dot');
                const statusText = document.querySelector('.status-text');
                statusDot.className = 'status-dot online';
                statusText.textContent = 'AI Online';
            }
        } catch (error) {
            const statusDot = document.querySelector('.status-dot');
            const statusText = document.querySelector('.status-text');
            statusDot.className = 'status-dot offline';
            statusText.textContent = 'AI Offline';
            console.error('API health check failed:', error);
        }
    }

    // Initialize session memory if needed
    async initializeSession() {
        try {
            const response = await fetch(`${this.apiUrl}/sessions/${this.sessionId}`, {
                headers: {
                    'Authorization': `Bearer ${this.apiKey}`
                }
            });
            
            if (response.ok) {
                const sessionData = await response.json();
                console.log('Session initialized:', sessionData);
            }
        } catch (error) {
            console.error('Session initialization failed:', error);
        }
    }
}

// Global functions
function toggleVoiceRecording() {
    // Handled by mousedown/mouseup events
}

function sendQuickMessage(message) {
    sophiaChat.sendQuickMessage(message);
}

function toggleSettings() {
    sophiaChat.toggleSettings();
}

function saveSettings() {
    sophiaChat.saveSettings();
}

// Initialize the chat application
const sophiaChat = new SophiaChat();

// Check API health on load
document.addEventListener('DOMContentLoaded', () => {
    sophiaChat.checkApiHealth();
    sophiaChat.initializeSession();
    
    // Check health every 30 seconds
    setInterval(() => sophiaChat.checkApiHealth(), 30000);
});

// Add CSS for offline status
const offlineStyles = `
.status-dot.offline {
    background: var(--error-red);
}

.intent-badge {
    background: var(--bg-tertiary);
    padding: 2px 8px;
    border-radius: var(--radius-sm);
    font-size: 0.7rem;
    color: var(--accent-cyan);
    margin-right: 8px;
}

.message.sophia .message-content {
    background: var(--bg-card);
    border: 1px solid var(--border-primary);
}

.message.sophia .message-content:hover {
    border-color: var(--primary-gold);
    box-shadow: var(--shadow-glow);
}

.message.user .message-content:hover {
    box-shadow: 0 4px 20px rgba(107, 70, 193, 0.3);
}
`;

// Inject additional styles
const styleSheet = document.createElement('style');
styleSheet.textContent = offlineStyles;
document.head.appendChild(styleSheet);

// Add crypto-themed particle effect (optional enhancement)
function createCryptoParticles() {
    const particleContainer = document.createElement('div');
    particleContainer.className = 'crypto-particles';
    particleContainer.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        pointer-events: none;
        z-index: -1;
        overflow: hidden;
    `;
    
    document.body.appendChild(particleContainer);
    
    // Create floating crypto symbols
    const symbols = ['₿', 'Ξ', '⟐', '◊', '◈'];
    
    function createParticle() {
        const particle = document.createElement('div');
        particle.textContent = symbols[Math.floor(Math.random() * symbols.length)];
        particle.style.cssText = `
            position: absolute;
            color: rgba(255, 215, 0, 0.1);
            font-size: ${Math.random() * 20 + 10}px;
            left: ${Math.random() * 100}%;
            animation: float ${Math.random() * 10 + 15}s linear infinite;
        `;
        
        particleContainer.appendChild(particle);
        
        // Remove particle after animation
        setTimeout(() => {
            if (particle.parentNode) {
                particle.remove();
            }
        }, 25000);
    }
    
    // Add CSS for floating animation
    const particleStyles = `
        @keyframes float {
            0% {
                transform: translateY(100vh) rotate(0deg);
                opacity: 0;
            }
            10% {
                opacity: 1;
            }
            90% {
                opacity: 1;
            }
            100% {
                transform: translateY(-100px) rotate(360deg);
                opacity: 0;
            }
        }
    `;
    
    const particleStyleSheet = document.createElement('style');
    particleStyleSheet.textContent = particleStyles;
    document.head.appendChild(particleStyleSheet);
    
    // Create particles periodically
    setInterval(createParticle, 3000);
}

// Enable particle effect after page load
setTimeout(createCryptoParticles, 2000);