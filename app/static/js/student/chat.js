/**
 * SVIT AI Assistant - Frontend Chat Client
 * Features:
 * - Live SSE Token Streaming & Fast RAG
 * - Robust Dual-Engine Voice Input (Live Web Speech API + Hugging Face Whisper STT)
 * - Accurate Microphone Permission Handling & Secure Context Detection
 * - Animated Text-to-Speech (TTS) with Sound-wave Equalizer UI Indicator
 * - Persistent 👍 / 👎 Thumbs Feedback with History restoration
 * - Dynamic Contextual Follow-up Suggestions
 * - Markdown (.md) and PDF / Print Chat Export
 */
document.addEventListener('DOMContentLoaded', () => {
    console.log("[SVIT AI] Chat Client Initialized.");

    const chatForm = document.getElementById('chatForm');
    const chatInput = document.getElementById('chatInput');
    const chatThread = document.getElementById('chatThread');
    const typingIndicator = document.getElementById('typingIndicator');
    const welcomeSection = document.getElementById('welcomeSection');
    const voiceBtn = document.getElementById('voiceBtn');

    // =========================================================
    // 1. EVENT LISTENERS & NAVIGATION
    // =========================================================
    if (voiceBtn) {
        voiceBtn.addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation();
            toggleVoiceInput();
        });
    }

    const navItems = document.querySelectorAll('.sidebar-nav .nav-item');
    navItems.forEach(item => {
        item.addEventListener('click', (e) => {
            const href = item.getAttribute('href');
            if (href && href !== '#' && !href.startsWith('javascript:')) {
                stopTTS();
                stopVoiceInput();
                window.location.href = href;
            }
        });
    });

    // Close export dropdown when clicking outside
    window.addEventListener('click', (e) => {
        const menu = document.getElementById('exportMenu');
        if (menu && menu.style.display !== 'none' && !e.target.closest('.export-dropdown-wrapper')) {
            menu.style.display = 'none';
        }
    });

    // Restore Sidebar Collapse State from LocalStorage
    initSidebarState();

    // Load Recent Conversations in Sidebar
    loadSidebarRecents();

    // Check if a specific conversation or prompt was requested via URL query params
    const urlParams = new URLSearchParams(window.location.search);
    const convIdParam = urlParams.get('conversation_id');
    const promptParam = urlParams.get('prompt');

    if (convIdParam) {
        loadConversationMessages(convIdParam);
    } else if (promptParam) {
        setTimeout(() => {
            sendSuggested(decodeURIComponent(promptParam));
        }, 300);
    }

    // =========================================================
    // 2. CHAT FORM SUBMISSION (STREAMING FIRST WITH JSON FALLBACK)
    // =========================================================
    if (chatForm) {
        chatForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const text = chatInput.value.trim();
            if (!text) return;

            // Stop any playing TTS or active Voice Input when message is sent
            stopTTS();
            stopVoiceInput();

            if (welcomeSection) {
                welcomeSection.style.display = 'none';
            }

            const convIdInput = document.getElementById('activeConversationId');
            const activeConvId = convIdInput ? convIdInput.value : '';

            // Display user message
            appendUserMessage(text);
            chatInput.value = '';

            // Show typing indicator initially
            if (typingIndicator) {
                typingIndicator.style.display = 'flex';
            }
            scrollToBottom();

            let streamedSuccessfully = false;

            // Attempt Fast Streaming via SSE first
            try {
                const streamResponse = await fetch('/api/chat/stream', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ 
                        message: text,
                        conversation_id: activeConvId 
                    })
                });

                if (streamResponse.ok && streamResponse.headers.get('content-type')?.includes('text/event-stream')) {
                    if (typingIndicator) {
                        typingIndicator.style.display = 'none';
                    }

                    const streamCard = createStreamingBotRow(text);
                    const contentEl = streamCard.querySelector('.bot-content');
                    let accumulatedText = '';
                    let finalImage = null;
                    let finalSources = [];
                    let finalSuggestions = [];

                    const reader = streamResponse.body.getReader();
                    const decoder = new TextDecoder('utf-8');
                    let buffer = '';

                    while (true) {
                        const { done, value } = await reader.read();
                        if (done) break;

                        buffer += decoder.decode(value, { stream: true });
                        const lines = buffer.split('\n\n');
                        buffer = lines.pop();

                        for (const line of lines) {
                            if (line.startsWith('data: ')) {
                                try {
                                    const data = JSON.parse(line.substring(6));
                                    if (data.conversation_id) {
                                        if (convIdInput) convIdInput.value = data.conversation_id;
                                        streamCard.setAttribute('data-conv-id', data.conversation_id);
                                    }
                                    if (data.message_id) {
                                        streamCard.setAttribute('data-msg-id', data.message_id);
                                    }
                                    if (data.chunk) {
                                        accumulatedText += data.chunk;
                                        renderMarkdown(contentEl, accumulatedText);
                                        scrollToBottom();
                                    }
                                    if (data.done) {
                                        if (data.answer) accumulatedText = data.answer;
                                        if (data.message_id) streamCard.setAttribute('data-msg-id', data.message_id);
                                        finalImage = data.image || null;
                                        finalSources = data.sources || [];
                                        finalSuggestions = data.suggestions || [];
                                    }
                                } catch (parseErr) {
                                    // Keep-alive or comment
                                }
                            }
                        }
                    }

                    // Finalize rendering
                    renderMarkdown(contentEl, accumulatedText);
                    finalizeStreamingBotRow(streamCard, finalImage, finalSources, finalSuggestions);
                    streamedSuccessfully = true;
                }
            } catch (streamErr) {
                console.warn("Streaming unavailable, falling back to JSON:", streamErr);
            }

            // Fallback to standard JSON POST if streaming wasn't completed
            if (!streamedSuccessfully) {
                try {
                    let endpoints = ['/api/chat', '/student/api/chat'];
                    let response = null;
                    let data = null;

                    for (let url of endpoints) {
                        try {
                            let res = await fetch(url, {
                                method: 'POST',
                                headers: { 'Content-Type': 'application/json' },
                                body: JSON.stringify({ 
                                    message: text,
                                    conversation_id: activeConvId 
                                })
                            });
                            if (res.status !== 404) {
                                response = res;
                                data = await res.json();
                                break;
                            }
                        } catch (err) {
                            console.warn(`Attempt failed for ${url}`);
                        }
                    }

                    if (typingIndicator) {
                        typingIndicator.style.display = 'none';
                    }

                    if (response && response.ok) {
                        if (data.conversation_id && convIdInput) {
                            convIdInput.value = data.conversation_id;
                        }
                        const replyText = data.answer || data.response || "No response received.";
                        const imagePath = data.image || null;
                        const sources = data.sources || [];
                        const msgId = data.message_id || null;
                        const suggestions = data.suggestions || [];
                        appendBotMessage(replyText, imagePath, sources, text, data.conversation_id, msgId, null, suggestions);
                    } else {
                        const errorMsg = data?.error || `Error ${response?.status || '500'}: Failed to fetch response.`;
                        appendBotMessage(`⚠️ ${errorMsg}`, null, [], text);
                    }
                } catch (jsonErr) {
                    if (typingIndicator) {
                        typingIndicator.style.display = 'none';
                    }
                    console.error("Chat API Fallback Error:", jsonErr);
                    appendBotMessage('⚠️ Error connecting to server. Please check your backend terminal logs.', null, [], text);
                }
            }
        });
    }
});

// =========================================================
// 3. UI RENDERING & HISTORY RESTORATION HELPERS
// =========================================================

async function loadConversationMessages(convId) {
    if (!convId) return;

    const chatThread = document.getElementById('chatThread');
    const welcomeSection = document.getElementById('welcomeSection');
    const convIdInput = document.getElementById('activeConversationId');

    if (convIdInput) convIdInput.value = convId;
    if (welcomeSection) welcomeSection.style.display = 'none';
    if (chatThread) chatThread.innerHTML = '';

    try {
        const res = await fetch(`/chat/${convId}`);
        const data = await res.json();

        if (data.status === 'success' && data.messages) {
            let lastUserMsg = '';
            data.messages.forEach(m => {
                const text = m.content || m.text || '';
                if (m.sender === 'user') {
                    lastUserMsg = text;
                    appendUserMessage(text);
                } else if (m.sender === 'assistant') {
                    appendBotMessage(
                        text, 
                        m.image_path, 
                        m.sources || [], 
                        lastUserMsg, 
                        convId, 
                        m.id, 
                        m.feedback,
                        []
                    );
                }
            });
            scrollToBottom();
        }
    } catch (err) {
        console.error('Failed to load conversation messages:', err);
    }
}

function appendUserMessage(text) {
    const chatThread = document.getElementById('chatThread');
    if (!chatThread) return;

    const userRow = document.createElement('div');
    userRow.classList.add('chat-row', 'user-row');
    userRow.innerHTML = `
        <div class="user-bubble">${escapeHtml(text)}</div>
        <div class="chat-avatar user-initial-avatar" style="width: 35px; height: 35px; border-radius: 50%; background: #4f46e5; color: #fff; display: flex; align-items: center; justify-content: center; font-weight: 600; font-size: 14px;">
            U
        </div>
    `;
    chatThread.appendChild(userRow);
    scrollToBottom();
}

function createStreamingBotRow(userQueryText = '', messageId = null, convId = '', feedback = null) {
    const chatThread = document.getElementById('chatThread');
    const botRow = document.createElement('div');
    botRow.classList.add('chat-row', 'bot-row');
    if (userQueryText) botRow.setAttribute('data-query', userQueryText);
    if (messageId) botRow.setAttribute('data-msg-id', messageId);
    if (convId) botRow.setAttribute('data-conv-id', convId);

    botRow.innerHTML = `
        <div class="bot-avatar-box">
            <i data-lucide="bot"></i>
        </div>
        <div class="bot-card">
            <div class="bot-content"></div>
            <div class="map-slot"></div>
            <div class="sources-slot"></div>
            <div class="suggestions-slot"></div>
            <div class="bot-card-actions" style="margin-top: 8px; display: flex; gap: 6px; align-items: center;">
                <button class="action-btn" onclick="copyText(this)" title="Copy response text"><i data-lucide="copy"></i> Copy</button>
                <button class="action-btn tts-btn" onclick="toggleTTS(this)" title="Read aloud response"><i data-lucide="volume-2"></i> <span>Listen</span></button>
                <button class="action-btn icon-only feedback-btn like-btn" onclick="submitFeedback(this, 'like')" title="Helpful response"><i data-lucide="thumbs-up"></i></button>
                <button class="action-btn icon-only feedback-btn dislike-btn" onclick="submitFeedback(this, 'dislike')" title="Not helpful"><i data-lucide="thumbs-down"></i></button>
            </div>
        </div>
    `;

    // Apply persisted feedback state if present
    if (feedback) {
        const likeBtn = botRow.querySelector('.like-btn');
        const dislikeBtn = botRow.querySelector('.dislike-btn');
        if (likeBtn && dislikeBtn) {
            likeBtn.disabled = true;
            dislikeBtn.disabled = true;
            likeBtn.style.cursor = 'default';
            dislikeBtn.style.cursor = 'default';

            if (feedback === 'like') {
                likeBtn.style.color = '#16a34a';
                likeBtn.style.backgroundColor = '#dcfce7';
                likeBtn.style.borderColor = '#86efac';
                likeBtn.style.opacity = '1';
                dislikeBtn.style.opacity = '0.35';
            } else if (feedback === 'dislike') {
                dislikeBtn.style.color = '#dc2626';
                dislikeBtn.style.backgroundColor = '#fee2e2';
                dislikeBtn.style.borderColor = '#fca5a5';
                dislikeBtn.style.opacity = '1';
                likeBtn.style.opacity = '0.35';
            }
        }
    }

    chatThread.appendChild(botRow);
    if (window.lucide) lucide.createIcons();
    return botRow;
}

function finalizeStreamingBotRow(botRow, imagePath = null, sources = [], suggestions = []) {
    if (!botRow) return;

    if (imagePath) {
        let fullSrc = imagePath.startsWith('/static/') 
            ? imagePath 
            : `/static/${imagePath.replace(/^static\//, '')}`;

        const mapSlot = botRow.querySelector('.map-slot');
        if (mapSlot) {
            mapSlot.innerHTML = `
                <div class="map-container" style="margin-top: 12px; margin-bottom: 8px;">
                    <img src="${fullSrc}" 
                         alt="Campus Map" 
                         class="campus-map" 
                         onerror="this.parentElement.style.display='none';"
                         style="max-width: 100%; border-radius: 10px; border: 1px solid #e2e8f0; box-shadow: 0 2px 8px rgba(0,0,0,0.06);">
                </div>
            `;
        }
    }

    if (sources && sources.length > 0) {
        const sourcesSlot = botRow.querySelector('.sources-slot');
        if (sourcesSlot) {
            sourcesSlot.innerHTML = `
                <div class="sources-container" style="margin-top: 10px; padding-top: 8px; border-top: 1px dashed #e0e0e0; font-size: 0.82rem; color: #666;">
                    <strong>📚 Sources:</strong> ${sources.map(s => `<span class="source-tag" style="background: #f0f4f8; padding: 2px 6px; border-radius: 4px; margin-left: 4px;">${escapeHtml(s)}</span>`).join('')}
                </div>
            `;
        }
    }

    if (suggestions && suggestions.length > 0) {
        const suggSlot = botRow.querySelector('.suggestions-slot');
        if (suggSlot) {
            suggSlot.innerHTML = `
                <div class="followup-chips-container">
                    ${suggestions.map(s => `
                        <button type="button" class="followup-chip" data-suggestion="${encodeURIComponent(s)}">
                            <i data-lucide="sparkles" style="width: 12px; height: 12px; color: #6366f1;"></i>
                            <span>${escapeHtml(s)}</span>
                        </button>
                    `).join('')}
                </div>
            `;
        }
    }

    if (window.lucide) lucide.createIcons();
    scrollToBottom();
}

function renderMarkdown(element, text) {
    if (!element) return;
    if (typeof marked !== 'undefined') {
        marked.setOptions({ breaks: true, gfm: true });
        element.innerHTML = marked.parse(text);
    } else {
        element.innerHTML = escapeHtml(text)
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\n/g, '<br>');
    }
}

function appendBotMessage(text, imagePath = null, sources = [], userQueryText = '', convId = '', messageId = null, feedback = null, suggestions = []) {
    const row = createStreamingBotRow(userQueryText, messageId, convId, feedback);
    const contentEl = row.querySelector('.bot-content');
    renderMarkdown(contentEl, text);
    finalizeStreamingBotRow(row, imagePath, sources, suggestions);
}

function sendSuggested(questionText) {
    if (!questionText) return;
    const cleanText = questionText.replace(/[\u{1F300}-\u{1F9FF}\u{2600}-\u{26FF}\u{2700}-\u{27BF}]/gu, '').trim() || questionText.trim();
    const chatInput = document.getElementById('chatInput');
    const chatForm = document.getElementById('chatForm');
    if (chatInput && chatForm) {
        chatInput.value = cleanText;
        chatForm.dispatchEvent(new Event('submit', { cancelable: true, bubbles: true }));
    }
}
window.sendSuggested = sendSuggested;

// Global Delegated Click Listener for Follow-up Chips
document.addEventListener('click', (e) => {
    const chip = e.target.closest('.followup-chip');
    if (chip) {
        e.preventDefault();
        const raw = chip.getAttribute('data-suggestion');
        const text = raw ? decodeURIComponent(raw) : chip.querySelector('span')?.textContent;
        if (text) {
            sendSuggested(text);
        }
    }
});

function scrollToBottom() {
    const chatContainer = document.querySelector('.chat-container') || document.getElementById('chatThread');
    if (chatContainer) {
        chatContainer.scrollTop = chatContainer.scrollHeight;
    }
}

function escapeHtml(text) {
    if (typeof text !== 'string') return text;
    return text
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#39;");
}

function copyText(button) {
    const botCard = button.closest('.bot-card');
    const textToCopy = botCard ? botCard.querySelector('.bot-content').innerText : '';
    navigator.clipboard.writeText(textToCopy);
    
    button.innerHTML = `<i data-lucide="check"></i> Copied`;
    if (window.lucide) lucide.createIcons();
    setTimeout(() => {
        button.innerHTML = `<i data-lucide="copy"></i> Copy`;
        if (window.lucide) lucide.createIcons();
    }, 2000);
}

// =========================================================
// 4. ROBUST THUMBS UP / DOWN FEEDBACK PERSISTENCE
// =========================================================
async function submitFeedback(button, rating) {
    const actionsContainer = button.closest('.bot-card-actions');
    const botCard = button.closest('.bot-card');
    const botRow = button.closest('.bot-row');
    const botContent = botCard ? (botCard.querySelector('.bot-content')?.innerText || '') : '';

    // 1. Resolve conversation ID & message ID
    let convId = (botRow && botRow.getAttribute('data-conv-id')) 
                 || document.getElementById('activeConversationId')?.value 
                 || '';
    let msgId = (botRow && botRow.getAttribute('data-msg-id')) || null;

    // 2. Resolve user question
    let userQuery = (botRow && botRow.getAttribute('data-query')) || '';
    if (!userQuery && botRow) {
        let prev = botRow.previousElementSibling;
        while (prev) {
            if (prev.classList && prev.classList.contains('user-row')) {
                userQuery = prev.querySelector('.user-bubble')?.innerText || '';
                break;
            }
            prev = prev.previousElementSibling;
        }
    }

    // 3. Update UI state immediately
    if (actionsContainer) {
        const buttons = actionsContainer.querySelectorAll('.feedback-btn');
        buttons.forEach(btn => {
            btn.disabled = true;
            btn.style.opacity = '0.35';
            btn.style.cursor = 'default';
        });

        button.style.opacity = '1';
        if (rating === 'like') {
            button.style.color = '#16a34a';
            button.style.backgroundColor = '#dcfce7';
            button.style.borderColor = '#86efac';
        } else {
            button.style.color = '#dc2626';
            button.style.backgroundColor = '#fee2e2';
            button.style.borderColor = '#fca5a5';
        }
    }

    const payload = {
        rating: rating,
        message_id: msgId,
        conversation_id: convId,
        query_text: userQuery,
        response_text: botContent
    };

    // 4. Send feedback to backend with endpoint fallback
    const endpoints = ['/api/chat/feedback', '/student/api/chat/feedback', '/chat/feedback'];
    for (const url of endpoints) {
        try {
            const res = await fetch(url, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            if (res.ok) {
                const data = await res.json();
                if (data.message_id && botRow) {
                    botRow.setAttribute('data-msg-id', data.message_id);
                }
                return;
            }
        } catch (err) {
            console.warn(`[Feedback] Failed attempt for ${url}:`, err);
        }
    }
}

// =========================================================
// 5. BULLETPROOF DUAL-ENGINE VOICE INPUT & PERMISSION HANDLER
// =========================================================
let recognition = null;
let isVoiceActive = false;
let isVoiceStarting = false;
let audioContext = null;
let mediaStream = null;
let scriptProcessor = null;
let audioChunks = [];

async function checkMicrophoneEnvironment() {
    // 1. Check for Secure Context (HTTPS or Localhost)
    const isLocal = location.hostname === 'localhost' || location.hostname === '127.0.0.1';
    if (!window.isSecureContext && !isLocal) {
        return {
            ok: false,
            error: 'InsecureContext',
            message: 'Microphone access is blocked by the browser on insecure connections. Please access the application via http://localhost:5000 or configure HTTPS.'
        };
    }

    // 2. Check for mediaDevices API support
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        return {
            ok: false,
            error: 'NotSupported',
            message: 'Audio recording API is not supported in this browser. Please use Google Chrome, Microsoft Edge, or Firefox.'
        };
    }

    // 3. Inspect permission state if Permissions API is available
    if (navigator.permissions && navigator.permissions.query) {
        try {
            const permissionStatus = await navigator.permissions.query({ name: 'microphone' });
            console.log(`[VoiceInput] Browser microphone permission status: ${permissionStatus.state}`);
            if (permissionStatus.state === 'denied') {
                return {
                    ok: false,
                    error: 'PermissionDenied',
                    message: 'Microphone permission is blocked in your browser. Please click the permissions/lock icon in your URL address bar, set Microphone to "Allow", and refresh.'
                };
            }
        } catch (permErr) {
            // Some browsers throw on querying 'microphone', proceed to standard getUserMedia
        }
    }

    return { ok: true };
}

async function requestAudioStream() {
    // Request with simple, permissive audio constraints to avoid hardware driver rejections
    try {
        return await navigator.mediaDevices.getUserMedia({ audio: true });
    } catch (err) {
        console.warn(`[VoiceInput] getUserMedia({ audio: true }) failed with [${err.name}]: ${err.message}`);

        if (err.name === 'NotAllowedError' || err.name === 'PermissionDeniedError') {
            throw new Error('Microphone permission was denied. Please allow microphone access in your browser by clicking the lock/settings icon in the address bar.');
        } else if (err.name === 'NotFoundError' || err.name === 'DevicesNotFoundError') {
            throw new Error('No microphone hardware was detected on your device. Please plug in a microphone or headset and try again.');
        } else if (err.name === 'NotReadableError' || err.name === 'TrackStartError') {
            throw new Error('Your microphone is currently in use by another application (Zoom, Teams, Discord, etc.) or system driver. Please close other audio apps and try again.');
        } else if (err.name === 'OverconstrainedError') {
            // Retry with zero constraint parameters
            return await navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: false, noiseSuppression: false } });
        } else {
            throw new Error(`Microphone initialization error: ${err.message || err.name}`);
        }
    }
}

async function toggleVoiceInput() {
    if (isVoiceStarting) return; // Prevent double-trigger on rapid clicks
    
    if (isVoiceActive) {
        stopVoiceInput();
    } else {
        await startVoiceInput();
    }
}
window.toggleVoiceInput = toggleVoiceInput;

async function startVoiceInput() {
    isVoiceStarting = true;
    const voiceBtn = document.getElementById('voiceBtn');
    const chatInput = document.getElementById('chatInput');

    try {
        // Pre-flight environment check
        const envCheck = await checkMicrophoneEnvironment();
        if (!envCheck.ok) {
            alert(envCheck.message);
            isVoiceStarting = false;
            return;
        }

        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

        // -----------------------------------------------------
        // Engine 1: Native Web Speech API (Instant Live Dictation)
        // -----------------------------------------------------
        if (SpeechRecognition) {
            try {
                console.log("[VoiceInput] Initializing Web Speech Recognition engine...");
                
                if (recognition) {
                    try { recognition.stop(); } catch (e) {}
                    recognition = null;
                }

                recognition = new SpeechRecognition();
                recognition.continuous = false;
                recognition.interimResults = true;
                recognition.lang = 'en-IN';

                recognition.onstart = () => {
                    isVoiceActive = true;
                    isVoiceStarting = false;
                    console.log("[VoiceInput] Live Speech Recognition started.");
                    if (voiceBtn) {
                        voiceBtn.classList.add('recording-active');
                        voiceBtn.setAttribute('title', 'Listening... Click to stop');
                    }
                    if (chatInput) {
                        chatInput.placeholder = '🎙️ Listening... Speak now';
                    }
                };

                recognition.onresult = (event) => {
                    let transcript = '';
                    for (let i = event.resultIndex; i < event.results.length; ++i) {
                        transcript += event.results[i][0].transcript;
                    }
                    console.log("[VoiceInput] Live transcript:", transcript);
                    if (chatInput && transcript) {
                        chatInput.value = transcript;
                        chatInput.dispatchEvent(new Event('input', { bubbles: true }));
                    }
                };

                recognition.onerror = (event) => {
                    console.warn(`[VoiceInput] Web Speech error [${event.error}].`);
                    stopVoiceInput();

                    // If Web Speech failed due to network/service issues, seamlessly switch to Whisper
                    if (event.error === 'network' || event.error === 'service-not-allowed' || event.error === 'audio-capture') {
                        setTimeout(() => {
                            startWhisperAudioRecording();
                        }, 250);
                    } else if (event.error === 'not-allowed') {
                        alert("Microphone permission was denied. Please allow microphone access in your browser settings (click the lock icon in the URL bar).");
                    }
                };

                recognition.onend = () => {
                    console.log("[VoiceInput] Speech Recognition ended.");
                    stopVoiceInput();
                };

                recognition.start();
                return;
            } catch (recErr) {
                console.warn("[VoiceInput] Native SpeechRecognition start failed, switching to Whisper Audio Engine:", recErr);
            }
        }

        // -----------------------------------------------------
        // Engine 2: Hugging Face Whisper Audio Recording Engine
        // -----------------------------------------------------
        await startWhisperAudioRecording();

    } catch (err) {
        console.error("[VoiceInput] Error initializing voice input:", err);
        alert(err.message || "Could not access microphone.");
        stopVoiceInput();
    } finally {
        isVoiceStarting = false;
    }
}

async function startWhisperAudioRecording() {
    const voiceBtn = document.getElementById('voiceBtn');
    const chatInput = document.getElementById('chatInput');

    try {
        console.log("[VoiceInput] Requesting microphone stream for Whisper...");
        mediaStream = await requestAudioStream();

        const AudioCtx = window.AudioContext || window.webkitAudioContext;
        audioContext = new AudioCtx();
        if (audioContext.state === 'suspended') {
            await audioContext.resume();
        }

        const source = audioContext.createMediaStreamSource(mediaStream);
        scriptProcessor = audioContext.createScriptProcessor(4096, 1, 1);
        audioChunks = [];

        scriptProcessor.onaudioprocess = (e) => {
            if (!isVoiceActive) return;
            const inputData = e.inputBuffer.getChannelData(0);
            audioChunks.push(new Float32Array(inputData));
        };

        source.connect(scriptProcessor);
        scriptProcessor.connect(audioContext.destination);

        isVoiceActive = true;
        console.log("[VoiceInput] Whisper Audio Recording is active.");
        if (voiceBtn) {
            voiceBtn.classList.add('recording-active');
            voiceBtn.setAttribute('title', 'Listening... Click to finish');
        }
        if (chatInput) {
            chatInput.placeholder = '🎙️ Listening (Whisper AI)... Speak now';
        }

    } catch (err) {
        console.error("[VoiceInput] Whisper audio recording failed:", err);
        alert(err.message || "Microphone access could not be established.");
        stopVoiceInput();
    }
}

async function stopVoiceInput() {
    isVoiceActive = false;
    isVoiceStarting = false;
    const voiceBtn = document.getElementById('voiceBtn');
    const chatInput = document.getElementById('chatInput');

    if (voiceBtn) {
        voiceBtn.classList.remove('recording-active');
        voiceBtn.setAttribute('title', 'Voice Input (Speech-to-Text)');
    }

    // Stop Native Speech Recognition if active
    if (recognition) {
        try { recognition.stop(); } catch (e) {}
        recognition = null;
    }

    // Stop Whisper Audio Recording if active
    if (scriptProcessor) {
        try { scriptProcessor.disconnect(); } catch (e) {}
        scriptProcessor = null;
    }
    
    let actualSampleRate = 44100;
    if (audioContext) {
        actualSampleRate = audioContext.sampleRate || 44100;
        try { audioContext.close(); } catch (e) {}
        audioContext = null;
    }
    if (mediaStream) {
        mediaStream.getTracks().forEach(track => track.stop());
        mediaStream = null;
    }

    // Process audio chunks with Whisper backend if captured
    if (audioChunks && audioChunks.length > 0) {
        console.log(`[VoiceInput] Uploading ${audioChunks.length} audio chunks (${actualSampleRate}Hz) to Whisper backend...`);
        let totalLength = audioChunks.reduce((acc, chunk) => acc + chunk.length, 0);
        let mergedBuffer = new Float32Array(totalLength);
        let offset = 0;
        for (let chunk of audioChunks) {
            mergedBuffer.set(chunk, offset);
            offset += chunk.length;
        }
        audioChunks = [];

        if (chatInput) {
            chatInput.placeholder = '⏳ Transcribing with Whisper AI...';
        }

        const wavBlob = encodeWavBlob(mergedBuffer, actualSampleRate);
        const formData = new FormData();
        formData.append('audio', wavBlob, 'recording.wav');

        const endpoints = ['/api/speech-to-text', '/student/api/speech-to-text'];
        for (const url of endpoints) {
            try {
                const res = await fetch(url, {
                    method: 'POST',
                    body: formData
                });

                if (res.ok) {
                    const data = await res.json();
                    console.log("[VoiceInput] Whisper STT result:", data);
                    if (data.status === 'success' && data.text && data.text.trim()) {
                        if (chatInput) {
                            chatInput.value = data.text.trim();
                            chatInput.dispatchEvent(new Event('input', { bubbles: true }));
                            chatInput.focus();
                        }
                    }
                    break;
                }
            } catch (postErr) {
                console.warn(`[VoiceInput] Whisper STT failed on ${url}:`, postErr);
            }
        }
    }

    if (chatInput) {
        chatInput.placeholder = 'Ask anything about rooms, courses, events, or campus directions...';
        chatInput.focus();
    }
}

function encodeWavBlob(samples, sampleRate) {
    const buffer = new ArrayBuffer(44 + samples.length * 2);
    const view = new DataView(buffer);

    // RIFF chunk descriptor
    writeString(view, 0, 'RIFF');
    view.setUint32(4, 36 + samples.length * 2, true);
    writeString(view, 8, 'WAVE');

    // fmt sub-chunk
    writeString(view, 12, 'fmt ');
    view.setUint32(16, 16, true);
    view.setUint16(20, 1, true); // PCM format
    view.setUint16(22, 1, true); // 1 channel (mono)
    view.setUint32(24, sampleRate, true);
    view.setUint32(28, sampleRate * 2, true);
    view.setUint16(32, 2, true);
    view.setUint16(34, 16, true);

    // data sub-chunk
    writeString(view, 36, 'data');
    view.setUint32(40, samples.length * 2, true);

    // PCM samples
    let index = 44;
    for (let i = 0; i < samples.length; i++) {
        let s = Math.max(-1, Math.min(1, samples[i]));
        view.setInt16(index, s < 0 ? s * 0x8000 : s * 0x7FFF, true);
        index += 2;
    }

    return new Blob([view], { type: 'audio/wav' });
}

function writeString(view, offset, string) {
    for (let i = 0; i < string.length; i++) {
        view.setUint8(offset + i, string.charCodeAt(i));
    }
}

// =========================================================
// 6. TEXT-TO-SPEECH (TTS) ENGINE & ANIMATED SOUND-WAVE UI
// =========================================================
let currentUtterance = null;
let activeTTSButton = null;

function toggleTTS(button) {
    if (!('speechSynthesis' in window)) {
        alert("Text-to-Speech is not supported in this browser.");
        return;
    }

    // If currently speaking this exact message, stop it immediately
    if (activeTTSButton === button && (window.speechSynthesis.speaking || window.speechSynthesis.pending)) {
        stopTTS();
        return;
    }

    // Stop any ongoing speech first
    stopTTS();

    const botCard = button.closest('.bot-card');
    if (!botCard) return;

    const botContent = botCard.querySelector('.bot-content');
    if (!botContent) return;

    // Clean text: strip markdown tables, code blocks, URLs, and extra symbols
    let rawText = botContent.innerText || '';
    let cleanText = cleanTextForTTS(rawText);

    if (!cleanText) return;

    speakText(cleanText, button);
}
window.toggleTTS = toggleTTS;

function cleanTextForTTS(text) {
    return text
        .replace(/\|[\s\S]*?\|/g, '') // remove markdown tables
        .replace(/```[\s\S]*?```/g, '') // remove code blocks
        .replace(/`([^`]+)`/g, '$1')
        .replace(/\[([^\]]+)\]\([^\)]+\)/g, '$1') // links to text
        .replace(/[\u{1F300}-\u{1F9FF}\u{2600}-\u{26FF}\u{2700}-\u{27BF}]/gu, '') // remove emojis
        .replace(/[\*\#\_\~]/g, '') // remove markdown format marks
        .replace(/\n+/g, '. ') // newlines to periods
        .trim();
}

function speakText(text, button) {
    try {
        window.speechSynthesis.cancel();
    } catch (e) {}

    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = 'en-IN';
    utterance.rate = 1.0;
    utterance.pitch = 1.0;

    // Pick best English voice if available
    try {
        const voices = window.speechSynthesis.getVoices();
        if (voices && voices.length > 0) {
            const preferredVoice = voices.find(v => (v.lang.includes('en-IN') || v.lang.includes('en-GB') || v.lang.includes('en-US')) && !v.name.includes('Google'));
            if (preferredVoice) utterance.voice = preferredVoice;
        }
    } catch (vErr) {}

    utterance.onstart = () => {
        setTTSActiveState(button, true);
    };

    utterance.onend = () => {
        setTTSActiveState(button, false);
        activeTTSButton = null;
        currentUtterance = null;
    };

    utterance.onerror = (e) => {
        console.warn("[TTS] Utterance error or cancelled:", e);
        setTTSActiveState(button, false);
        activeTTSButton = null;
        currentUtterance = null;
    };

    currentUtterance = utterance;
    activeTTSButton = button;
    
    // Set UI state immediately for instant responsive feedback
    setTTSActiveState(button, true);

    window.speechSynthesis.speak(utterance);
}

function stopTTS() {
    try {
        if ('speechSynthesis' in window) {
            window.speechSynthesis.cancel();
        }
    } catch (e) {}

    if (activeTTSButton) {
        setTTSActiveState(activeTTSButton, false);
    }
    currentUtterance = null;
    activeTTSButton = null;
}
window.stopTTS = stopTTS;

function setTTSActiveState(button, isSpeaking) {
    if (!button) return;

    if (isSpeaking) {
        button.classList.add('tts-active');
        button.setAttribute('title', 'Click to stop speaking');
        button.innerHTML = `
            <span class="tts-soundwave" aria-hidden="true">
                <span class="bar"></span>
                <span class="bar"></span>
                <span class="bar"></span>
                <span class="bar"></span>
            </span>
            <span class="tts-label">Speaking...</span>
        `;
    } else {
        button.classList.remove('tts-active');
        button.setAttribute('title', 'Read aloud response');
        button.innerHTML = `<i data-lucide="volume-2"></i> <span>Listen</span>`;
        if (window.lucide) lucide.createIcons();
    }
}

// =========================================================
// 7. CHAT EXPORT (MARKDOWN & PDF / PRINT)
// =========================================================
function toggleExportMenu(event) {
    if (event) event.stopPropagation();
    const menu = document.getElementById('exportMenu');
    if (menu) {
        menu.style.display = menu.style.display === 'block' ? 'none' : 'block';
    }
}

function exportChatAsMarkdown() {
    const chatThread = document.getElementById('chatThread');
    if (!chatThread) return;

    const rows = chatThread.querySelectorAll('.chat-row');
    if (!rows || rows.length === 0) {
        alert("No conversation messages to export yet.");
        return;
    }

    let mdContent = `# SVIT AI Assistant - Conversation Transcript\n`;
    mdContent += `*Export Date: ${new Date().toLocaleString()}*\n\n---\n\n`;

    rows.forEach(row => {
        if (row.classList.contains('user-row')) {
            const userText = row.querySelector('.user-bubble')?.innerText || '';
            mdContent += `### 👤 Student:\n${userText}\n\n`;
        } else if (row.classList.contains('bot-row') && row.id !== 'typingIndicator') {
            const botText = row.querySelector('.bot-content')?.innerText || '';
            mdContent += `### 🤖 SVIT AI Assistant:\n${botText}\n\n---\n\n`;
        }
    });

    const blob = new Blob([mdContent], { type: 'text/markdown;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', `SVIT_Chat_${new Date().toISOString().slice(0,10)}.md`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);

    const menu = document.getElementById('exportMenu');
    if (menu) menu.style.display = 'none';
}

function exportChatAsPDF() {
    const chatThread = document.getElementById('chatThread');
    if (!chatThread) return;

    const rows = chatThread.querySelectorAll('.chat-row');
    if (!rows || rows.length === 0) {
        alert("No conversation messages to export yet.");
        return;
    }

    const menu = document.getElementById('exportMenu');
    if (menu) menu.style.display = 'none';

    // Trigger browser print formatted as PDF
    window.print();
}

// =========================================================
// 8. CHATGPT SIDEBAR COLLAPSE, RECENTS & ACTION HANDLERS
// =========================================================

let cachedRecentChats = [];

function initSidebarState() {
    const sidebar = document.getElementById('sidebar');
    const isCollapsed = localStorage.getItem('svit_sidebar_collapsed') === 'true';
    if (sidebar && isCollapsed && window.innerWidth > 768) {
        sidebar.classList.add('collapsed');
        updateCollapseIcon(true);
    }
}

function toggleSidebarCollapse() {
    const sidebar = document.getElementById('sidebar');
    if (!sidebar) return;
    const isNowCollapsed = sidebar.classList.toggle('collapsed');
    localStorage.setItem('svit_sidebar_collapsed', isNowCollapsed);
    updateCollapseIcon(isNowCollapsed);
}

function updateCollapseIcon(isCollapsed) {
    const collapseBtn = document.getElementById('sidebarCollapseBtn');
    if (collapseBtn) {
        collapseBtn.innerHTML = isCollapsed ? `<i data-lucide="panel-left-open"></i>` : `<i data-lucide="panel-left-close"></i>`;
        collapseBtn.title = isCollapsed ? "Expand Sidebar" : "Collapse Sidebar";
        if (window.lucide) lucide.createIcons();
    }
}

function toggleMobileSidebar() {
    const sidebar = document.getElementById('sidebar');
    const backdrop = document.getElementById('sidebarBackdrop');
    if (!sidebar) return;
    const isOpen = sidebar.classList.toggle('mobile-open');
    if (backdrop) {
        backdrop.classList.toggle('active', isOpen);
    }
}

function toggleSidebarSearch() {
    const searchBox = document.getElementById('sidebarSearchBox');
    const searchInput = document.getElementById('recentSearchInput');
    const sidebar = document.getElementById('sidebar');
    if (sidebar && sidebar.classList.contains('collapsed')) {
        toggleSidebarCollapse();
    }
    if (searchBox) {
        const isHidden = searchBox.style.display === 'none' || !searchBox.style.display;
        searchBox.style.display = isHidden ? 'flex' : 'none';
        if (isHidden && searchInput) {
            searchInput.focus();
        } else if (!isHidden && searchInput) {
            clearRecentSearch();
        }
    }
}

function toggleSidebarMoreAccordion(e) {
    if (e) e.stopPropagation();
    const sidebar = document.getElementById('sidebar');
    if (sidebar && sidebar.classList.contains('collapsed')) {
        toggleSidebarCollapse();
    }
    const moreContent = document.getElementById('sidebarMoreContent');
    const moreBtn = document.getElementById('sidebarMoreBtn');
    if (moreContent) {
        const isShown = moreContent.classList.toggle('show');
        if (moreBtn) moreBtn.classList.toggle('open', isShown);
    }
}
window.toggleSidebarMoreAccordion = toggleSidebarMoreAccordion;
window.toggleSidebarMoreMenu = toggleSidebarMoreAccordion;

function triggerSidebarAction(prompt) {
    // Close mobile drawer if open
    const sidebar = document.getElementById('sidebar');
    if (sidebar && sidebar.classList.contains('mobile-open')) {
        toggleMobileSidebar();
    }

    if (window.location.pathname === '/' || window.location.pathname === '/student/' || window.location.pathname.endsWith('/chat')) {
        sendSuggested(prompt);
    } else {
        window.location.href = '/?prompt=' + encodeURIComponent(prompt);
    }
}
window.triggerSidebarAction = triggerSidebarAction;

async function loadSidebarRecents() {
    const container = document.getElementById('sidebarRecentList');
    if (!container) return;

    try {
        const res = await fetch('/chat/history');
        if (!res.ok) {
            container.innerHTML = `<div class="recents-empty">No recent chats</div>`;
            return;
        }
        const data = await res.json();
        const grouped = data?.history || {};
        
        let allChats = [];
        ['today', 'yesterday', 'last_7_days', 'last_month', 'older'].forEach(key => {
            if (Array.isArray(grouped[key])) {
                allChats = allChats.concat(grouped[key]);
            }
        });

        cachedRecentChats = allChats;
        renderRecentChatsList(allChats);
    } catch (err) {
        console.warn("[Sidebar] Error loading recent chats:", err);
        container.innerHTML = `<div class="recents-empty">No recent chats</div>`;
    }
}

function renderRecentChatsList(chats) {
    const container = document.getElementById('sidebarRecentList');
    if (!container) return;

    if (!chats || chats.length === 0) {
        container.innerHTML = `<div class="recents-empty">No chats yet</div>`;
        return;
    }

    const currentConvId = document.getElementById('activeConversationId')?.value || '';

    container.innerHTML = chats.slice(0, 30).map(c => `
        <a href="/?conversation_id=${encodeURIComponent(c.id)}" 
           class="recent-chat-item ${c.id === currentConvId ? 'active' : ''}" 
           onclick="selectRecentChat(event, '${escapeHtml(c.id)}')" 
           title="${escapeHtml(c.title || 'Untitled Conversation')}">
            <span class="chat-title-text">${escapeHtml(c.title || 'Conversation')}</span>
            <button type="button" class="recent-item-options-btn" title="Options" onclick="event.stopPropagation(); window.location.href='/chat/history-page';">
                <i data-lucide="more-horizontal"></i>
            </button>
        </a>
    `).join('');

    if (window.lucide) lucide.createIcons();
}

function selectRecentChat(e, convId) {
    if (window.location.pathname === '/' || window.location.pathname === '/student/' || window.location.pathname.endsWith('/chat')) {
        e.preventDefault();
        loadConversationMessages(convId);
        // Highlight active item
        document.querySelectorAll('.recent-chat-item').forEach(el => el.classList.remove('active'));
        e.currentTarget?.classList.add('active');
        // Close mobile drawer if open
        const sidebar = document.getElementById('sidebar');
        if (sidebar && sidebar.classList.contains('mobile-open')) {
            toggleMobileSidebar();
        }
        window.history.pushState(null, '', `/?conversation_id=${encodeURIComponent(convId)}`);
    }
}

function filterRecentConversations(query) {
    const q = (query || '').toLowerCase().trim();
    if (!q) {
        renderRecentChatsList(cachedRecentChats);
        return;
    }
    const filtered = cachedRecentChats.filter(c => (c.title || '').toLowerCase().includes(q));
    renderRecentChatsList(filtered);
}

function clearRecentSearch() {
    const input = document.getElementById('recentSearchInput');
    if (input) input.value = '';
    renderRecentChatsList(cachedRecentChats);
}