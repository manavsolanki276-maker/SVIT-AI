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

    // Navigation item listeners
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

    // Delegated submit handler for forms (handles both homeChatForm and chatForm)
    document.addEventListener('submit', (e) => {
        if (e.target && e.target.id === 'chatForm') {
            handleNormalFormSubmit(e);
        } else if (e.target && e.target.id === 'homeChatForm') {
            handleHomeFormSubmit(e);
        }
    });

    // Delegated click handler for voice buttons
    document.addEventListener('click', (e) => {
        const voiceBtn = e.target.closest('#voiceBtn');
        if (voiceBtn) {
            e.preventDefault();
            e.stopPropagation();
            toggleVoiceInput(e);
            return;
        }
        const homeVoiceBtn = e.target.closest('#homeVoiceBtn');
        if (homeVoiceBtn) {
            e.preventDefault();
            e.stopPropagation();
            triggerHomeVoiceInput(e);
            return;
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
    } else {
        showHomeState();
    }
});

// =========================================================
// 2. UNIFIED MESSAGE SUBMISSION & STREAMING ENGINE
// =========================================================
async function submitMessage(text) {
    if (!text || !text.trim()) return;
    text = text.trim();

    // Stop any playing TTS or active Voice Input when message is sent
    stopTTS();
    stopVoiceInput();

    // Ensure active chat state (Home Composer removed from DOM, Normal Composer mounted)
    showActiveChatState();

    const convIdInput = document.getElementById('activeConversationId');
    const activeConvId = convIdInput ? convIdInput.value : '';
    const typingIndicator = document.getElementById('typingIndicator');
    const chatInput = document.getElementById('chatInput');
    if (chatInput) chatInput.value = '';

    // Display user message
    appendUserMessage(text);

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
            let finalLocation = null;
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
                                finalLocation = data.location || null;
                                finalSources = data.sources || [];
                                finalSuggestions = data.suggestions || [];
                            }
                        } catch (parseErr) {
                            // Keep-alive or comment
                        }
                    }
                }
            }

            // Finalize rendering only if tokens were received
            if (accumulatedText && accumulatedText.trim().length > 0) {
                renderMarkdown(contentEl, accumulatedText);
                finalizeStreamingBotRow(streamCard, finalImage, finalSources, finalSuggestions, null, finalLocation);
                streamedSuccessfully = true;
                loadSidebarRecents();
            } else {
                // If stream yielded empty content, remove the placeholder and allow fallback
                streamCard.remove();
                streamedSuccessfully = false;
            }
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
                const locationData = data.location || null;
                const sources = data.sources || [];
                const msgId = data.message_id || null;
                const suggestions = data.suggestions || [];
                appendBotMessage(replyText, imagePath, sources, text, data.conversation_id, msgId, null, suggestions, locationData);
                loadSidebarRecents();
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
}
window.submitMessage = submitMessage;

// =========================================================
// 3. UI RENDERING & HISTORY RESTORATION HELPERS
// =========================================================

async function loadConversationMessages(convId) {
    if (!convId) return;

    const chatThread = document.getElementById('chatThread');
    const convIdInput = document.getElementById('activeConversationId');

    if (convIdInput) convIdInput.value = convId;
    showActiveChatState();
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
            <img src="/static/logo/svit%20logo%20u.png" alt="SVIT AI" class="bot-avatar-img" onerror="this.outerHTML='<i data-lucide=\\'bot\\'></i>'">
        </div>
        <div class="bot-card">
            <div class="bot-content"></div>
            <div class="map-slot"></div>
            <div class="sources-slot"></div>
            <div class="suggestions-slot"></div>
            <div class="actions-slot"></div>
        </div>
    `;

    chatThread.appendChild(botRow);
    if (window.lucide) lucide.createIcons();
    return botRow;
}

function openGoogleMapsDirections(location) {
    if (!location) {
        alert("Location coordinates are not available.");
        return;
    }

    let lat = null;
    let lng = null;

    if (typeof location === 'object') {
        lat = parseFloat(location.latitude !== undefined ? location.latitude : location.lat);
        lng = parseFloat(location.longitude !== undefined ? location.longitude : (location.lng !== undefined ? location.lng : location.lon));
    } else if (typeof location === 'string') {
        try {
            const parsed = JSON.parse(location);
            if (parsed && typeof parsed === 'object') {
                return openGoogleMapsDirections(parsed);
            }
        } catch (e) {
            const parts = location.split(',');
            if (parts.length === 2) {
                lat = parseFloat(parts[0].trim());
                lng = parseFloat(parts[1].trim());
            }
        }
    }

    if (lat === null || isNaN(lat) || lng === null || isNaN(lng)) {
        alert("Location coordinates are not available.");
        return;
    }

    const url = `https://www.google.com/maps/dir/?api=1&destination=${lat},${lng}&travelmode=walking&dir_action=navigate`;
    window.open(url, '_blank', 'noopener,noreferrer');
}
window.openGoogleMapsDirections = openGoogleMapsDirections;

function finalizeStreamingBotRow(botRow, imagePath = null, sources = [], suggestions = [], feedback = null, locationData = null) {
    if (!botRow) return;

    const contentEl = botRow.querySelector('.bot-content');
    if (contentEl && (!contentEl.innerHTML || !contentEl.textContent.trim())) {
        renderMarkdown(contentEl, "Thank you for asking! For specific details, please consult your department coordinator or student portal.");
    }

    let hasCoords = false;
    let latVal = null;
    let lngVal = null;
    let locName = '';
    let locBuilding = '';

    if (locationData && typeof locationData === 'object') {
        latVal = parseFloat(locationData.latitude !== undefined ? locationData.latitude : locationData.lat);
        lngVal = parseFloat(locationData.longitude !== undefined ? locationData.longitude : (locationData.lng !== undefined ? locationData.lng : locationData.lon));
        locName = locationData.name || locationData.place_name || locationData.department || '';
        locBuilding = locationData.building || locationData.zone || locationData.landmark || '';
        if (!isNaN(latVal) && !isNaN(lngVal) && latVal !== 0 && lngVal !== 0) {
            hasCoords = true;
        }
    }

    if (imagePath || hasCoords) {
        const mapSlot = botRow.querySelector('.map-slot');
        if (mapSlot) {
            let fullSrc = null;
            if (imagePath) {
                fullSrc = imagePath.startsWith('/static/')
                    ? imagePath
                    : `/static/${imagePath.replace(/^static\//, '')}`;
            }

            let locDataAttr = hasCoords ? encodeURIComponent(JSON.stringify(locationData)) : '';

            let cardHtml = `<div class="location-nav-card">`;

            if (hasCoords) {
                cardHtml += `
                    <div class="location-card-header">
                        <div class="location-meta-title">
                            <i data-lucide="map-pin" class="loc-pin-icon"></i>
                            <div class="loc-titles">
                                <span class="loc-primary-name">${escapeHtml(locName || 'Campus Location')}</span>
                                ${locBuilding ? `<span class="loc-secondary-zone">${escapeHtml(locBuilding)}</span>` : ''}
                            </div>
                        </div>
                        <button type="button" class="get-directions-btn" data-location="${locDataAttr}" onclick="openGoogleMapsDirections(JSON.parse(decodeURIComponent(this.getAttribute('data-location'))))" title="Get walking directions in Google Maps">
                            <i data-lucide="navigation" class="directions-icon"></i>
                            <span>Get Directions</span>
                            <i data-lucide="external-link" class="ext-icon"></i>
                        </button>
                    </div>
                `;
            }

            if (fullSrc) {
                cardHtml += `
                    <div class="map-container">
                        <img src="${fullSrc}"
                             alt="${escapeHtml(locName || 'Campus Map')}"
                             class="campus-map"
                             onerror="this.parentElement.style.display='none';">
                    </div>
                `;
            }

            cardHtml += `</div>`;
            mapSlot.innerHTML = cardHtml;
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

    // Mount Action Buttons (Copy, Listen, Like, Dislike) ONLY when the full answer is ready
    const actionsSlot = botRow.querySelector('.actions-slot');
    if (actionsSlot) {
        actionsSlot.innerHTML = `
            <div class="bot-card-actions" style="margin-top: 8px; display: flex; gap: 6px; align-items: center;">
                <button class="action-btn" onclick="copyText(this)" title="Copy response text"><i data-lucide="copy"></i> Copy</button>
                <button class="action-btn tts-btn" onclick="toggleTTS(this)" title="Read aloud response"><i data-lucide="volume-2"></i> <span>Listen</span></button>
                <button class="action-btn icon-only feedback-btn like-btn" onclick="submitFeedback(this, 'like')" title="Helpful response"><i data-lucide="thumbs-up"></i></button>
                <button class="action-btn icon-only feedback-btn dislike-btn" onclick="submitFeedback(this, 'dislike')" title="Not helpful"><i data-lucide="thumbs-down"></i></button>
            </div>
        `;

        // Apply persisted feedback state if present
        if (feedback) {
            const likeBtn = actionsSlot.querySelector('.like-btn');
            const dislikeBtn = actionsSlot.querySelector('.dislike-btn');
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
    }

    if (window.lucide) lucide.createIcons();
    scrollToBottom();
}

function renderMarkdown(element, text) {
    if (!element) return;
    if (typeof marked !== 'undefined') {
        marked.setOptions({ breaks: true, gfm: true });
        let html = marked.parse(text);
        // Wrap tables in responsive container to guarantee no mobile overflow
        html = html.replace(/<table>/g, '<div class="table-responsive"><table>').replace(/<\/table>/g, '</table></div>');
        element.innerHTML = html;
    } else {
        element.innerHTML = escapeHtml(text)
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\n/g, '<br>');
    }
}

function appendBotMessage(text, imagePath = null, sources = [], userQueryText = '', convId = '', messageId = null, feedback = null, suggestions = [], locationData = null) {
    const safeText = (text && text.trim().length > 0) ? text : "Thank you for asking! For specific details, please consult your department coordinator.";
    const row = createStreamingBotRow(userQueryText, messageId, convId, feedback);
    const contentEl = row.querySelector('.bot-content');
    renderMarkdown(contentEl, safeText);
    finalizeStreamingBotRow(row, imagePath, sources, suggestions, feedback, locationData);
}

function showHomeState() {
    // 1. Remove all Normal Chat Composer instances completely from active DOM
    document.querySelectorAll('#normalChatComposer').forEach(el => el.remove());

    // 2. Ensure Welcome Section (with Home Composer) is in DOM exactly once
    const chatContainer = document.getElementById('chatContainer');
    const chatThread = document.getElementById('chatThread');
    const welcomeSections = document.querySelectorAll('#welcomeSection');

    if (welcomeSections.length === 0) {
        const tpl = document.getElementById('welcomeSectionTemplate');
        if (tpl && chatContainer) {
            const clone = tpl.content.cloneNode(true);
            chatContainer.insertBefore(clone, chatThread || null);
        }
    } else {
        // Remove any duplicate welcome sections
        welcomeSections.forEach((el, index) => {
            if (index > 0) el.remove();
        });
    }

    // 3. Ensure no extra #homeComposerWrapper duplicates exist
    document.querySelectorAll('#homeComposerWrapper').forEach((el, index) => {
        if (index > 0) el.remove();
    });

    // 4. Hide chat thread and reset content
    if (chatThread) {
        chatThread.style.display = 'none';
        chatThread.innerHTML = '';
    }

    // 5. Ensure Lucide icons are initialized
    if (window.lucide) {
        lucide.createIcons();
    }

    // 6. Focus home chat input if available
    const homeInput = document.getElementById('homeChatInput');
    if (homeInput) {
        homeInput.value = '';
    }
}
window.showHomeState = showHomeState;

function showActiveChatState() {
    // 1. Remove all Welcome Section (and Home Composer) instances completely from DOM
    document.querySelectorAll('#welcomeSection').forEach(el => el.remove());
    document.querySelectorAll('#homeComposerWrapper').forEach(el => el.remove());

    // 2. Ensure Normal Chat Composer is in DOM exactly once
    const normalComposers = document.querySelectorAll('#normalChatComposer');
    if (normalComposers.length === 0) {
        const tpl = document.getElementById('normalComposerTemplate');
        const mainWrapper = document.querySelector('.main-wrapper') || document.body;
        if (tpl && mainWrapper) {
            const clone = tpl.content.cloneNode(true);
            mainWrapper.appendChild(clone);
        }
    } else {
        // Remove any duplicate normal composers
        normalComposers.forEach((el, index) => {
            if (index > 0) el.remove();
        });
    }

    // 3. Show chat thread
    const chatThread = document.getElementById('chatThread');
    if (chatThread) {
        chatThread.style.display = 'flex';
    }

    // 4. Ensure Lucide icons are initialized
    if (window.lucide) {
        lucide.createIcons();
    }
}
window.showActiveChatState = showActiveChatState;

function handleHomeFormSubmit(e) {
    if (e) {
        e.preventDefault();
        e.stopPropagation();
    }
    const homeInput = document.getElementById('homeChatInput');
    if (!homeInput || !homeInput.value.trim()) return;
    const text = homeInput.value.trim();
    homeInput.value = '';
    submitMessage(text);
}
window.handleHomeFormSubmit = handleHomeFormSubmit;

function handleNormalFormSubmit(e) {
    if (e) {
        e.preventDefault();
        e.stopPropagation();
    }
    const chatInput = document.getElementById('chatInput');
    if (!chatInput || !chatInput.value.trim()) return;
    const text = chatInput.value.trim();
    chatInput.value = '';
    submitMessage(text);
}
window.handleNormalFormSubmit = handleNormalFormSubmit;

function triggerHomeVoiceInput(e) {
    if (e) {
        e.preventDefault();
        e.stopPropagation();
    }
    const homeInput = document.getElementById('homeChatInput');
    const voiceBtn = document.getElementById('homeVoiceBtn');

    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
        alert("Speech recognition is not supported in this browser.");
        return;
    }

    if (window.activeVoiceRecognition) {
        window.activeVoiceRecognition.stop();
        window.activeVoiceRecognition = null;
        if (voiceBtn) voiceBtn.classList.remove('recording');
        return;
    }

    const recognition = new SpeechRecognition();
    recognition.lang = 'en-IN';
    recognition.continuous = false;
    recognition.interimResults = false;

    recognition.onstart = () => {
        window.activeVoiceRecognition = recognition;
        if (voiceBtn) voiceBtn.classList.add('recording');
        if (homeInput) homeInput.placeholder = '🎙️ Listening... Speak now';
    };

    recognition.onresult = (event) => {
        const transcript = event.results[0][0].transcript;
        if (transcript && transcript.trim()) {
            submitMessage(transcript.trim());
        }
    };

    recognition.onerror = () => {
        if (voiceBtn) voiceBtn.classList.remove('recording');
        if (homeInput) homeInput.placeholder = 'Ask anything about timetables, rooms, events, placements...';
        window.activeVoiceRecognition = null;
    };

    recognition.onend = () => {
        if (voiceBtn) voiceBtn.classList.remove('recording');
        if (homeInput) homeInput.placeholder = 'Ask anything about timetables, rooms, events, placements...';
        window.activeVoiceRecognition = null;
    };

    recognition.start();
}
window.triggerHomeVoiceInput = triggerHomeVoiceInput;

function resetChat() {
    stopTTS();
    stopVoiceInput();

    const convIdInput = document.getElementById('activeConversationId');
    if (convIdInput) convIdInput.value = '';

    if (window.history && window.history.pushState) {
        window.history.pushState(null, '', window.location.pathname);
    }

    document.querySelectorAll('.recent-chat-item').forEach(el => el.classList.remove('active'));

    showHomeState();
}
window.resetChat = resetChat;

function sendSuggested(questionText) {
    if (!questionText) return;
    const cleanText = questionText.replace(/[\u{1F300}-\u{1F9FF}\u{2600}-\u{26FF}\u{2700}-\u{27BF}]/gu, '').trim() || questionText.trim();
    if (!cleanText) return;
    submitMessage(cleanText);
}
window.sendSuggested = sendSuggested;

function sendFirstSuggestionOrFocus() {
    const homeInput = document.getElementById('homeChatInput');
    const normalInput = document.getElementById('chatInput');
    if (homeInput && homeInput.value.trim()) {
        handleHomeFormSubmit();
    } else if (normalInput && normalInput.value.trim()) {
        handleNormalFormSubmit();
    } else {
        sendSuggested("What's my next class right now?");
    }
}
window.sendFirstSuggestionOrFocus = sendFirstSuggestionOrFocus;

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

function checkScrollToBottomVisibility() {
    const chatContainer = document.querySelector('.chat-container');
    const scrollBtn = document.getElementById('scrollToBottomBtn');
    if (!chatContainer || !scrollBtn) return;

    const distanceToBottom = chatContainer.scrollHeight - chatContainer.scrollTop - chatContainer.clientHeight;
    if (distanceToBottom > 100 && chatContainer.scrollHeight > chatContainer.clientHeight + 80) {
        scrollBtn.classList.add('visible');
    } else {
        scrollBtn.classList.remove('visible');
    }
}

function smoothScrollToBottom() {
    const chatContainer = document.querySelector('.chat-container');
    if (chatContainer) {
        chatContainer.scrollTo({
            top: chatContainer.scrollHeight,
            behavior: 'smooth'
        });
        const scrollBtn = document.getElementById('scrollToBottomBtn');
        if (scrollBtn) scrollBtn.classList.remove('visible');
    }
}

function scrollToBottom() {
    const chatContainer = document.querySelector('.chat-container') || document.getElementById('chatThread');
    if (chatContainer) {
        chatContainer.scrollTop = chatContainer.scrollHeight;
        checkScrollToBottomVisibility();
    }
}

// Attach scroll listener to .chat-container for dynamic floating button visibility
window.addEventListener('DOMContentLoaded', () => {
    const chatContainer = document.querySelector('.chat-container');
    if (chatContainer) {
        chatContainer.addEventListener('scroll', checkScrollToBottomVisibility, { passive: true });
    }
});

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
        chatInput.placeholder = 'Ask anything about timetables, rooms, events, placements...';
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

function toggleMobileSidebar(force) {
    const sidebar = document.getElementById('sidebar');
    const backdrop = document.getElementById('sidebarBackdrop');
    if (!sidebar) return;
    const isOpen = (typeof force === 'boolean') ? force : !sidebar.classList.contains('mobile-open');
    sidebar.classList.toggle('mobile-open', isOpen);
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

function formatChatTime(dateStr) {
    if (!dateStr) return '';
    try {
        const d = new Date(dateStr);
        if (isNaN(d.getTime())) return '';
        let hours = d.getHours();
        const minutes = d.getMinutes();
        const ampm = hours >= 12 ? 'PM' : 'AM';
        hours = hours % 12;
        hours = hours ? hours : 12;
        const minStr = minutes < 10 ? '0' + minutes : minutes;
        return `${hours}:${minStr} ${ampm}`;
    } catch (e) {
        return '';
    }
}

function openMobileProfilePanel() {
    toggleMobileSidebar(false);
    const panel = document.getElementById('mobileProfilePanel');
    const backdrop = document.getElementById('mobileProfileBackdrop');
    if (panel) panel.classList.add('active');
    if (backdrop) backdrop.classList.add('active');
    if (window.lucide) lucide.createIcons();
}
window.openMobileProfilePanel = openMobileProfilePanel;

function closeMobileProfilePanel() {
    const panel = document.getElementById('mobileProfilePanel');
    const backdrop = document.getElementById('mobileProfileBackdrop');
    if (panel) panel.classList.remove('active');
    if (backdrop) backdrop.classList.remove('active');
}
window.closeMobileProfilePanel = closeMobileProfilePanel;

function renderRecentChatsList(chats) {
    const container = document.getElementById('sidebarRecentList');
    if (!container) return;

    if (!chats || chats.length === 0) {
        container.innerHTML = `<div class="recents-empty">No chats yet</div>`;
        return;
    }

    const currentConvId = document.getElementById('activeConversationId')?.value || '';

    // Prioritize pinned chats at the top
    const sortedChats = [...chats].sort((a, b) => {
        if (a.is_pinned && !b.is_pinned) return -1;
        if (!a.is_pinned && b.is_pinned) return 1;
        return 0;
    });

    container.innerHTML = sortedChats.slice(0, 30).map(c => {
        const timeStr = formatChatTime(c.updated_at || c.created_at);
        return `
        <a href="/student/chat?conversation_id=${encodeURIComponent(c.id)}"
           class="recent-chat-item ${c.id === currentConvId ? 'active' : ''} ${c.is_pinned ? 'pinned' : ''}"
           onclick="selectRecentChat(event, '${escapeHtml(c.id)}')"
           title="${escapeHtml(c.title || 'Untitled Conversation')}">
            ${c.is_pinned ? `<i data-lucide="pin" class="pin-indicator-icon" title="Pinned"></i>` : ''}
            <span class="chat-title-text">${escapeHtml(c.title || 'Conversation')}</span>
            ${timeStr ? `<span class="recent-chat-time">${escapeHtml(timeStr)}</span>` : ''}
            <button type="button" class="recent-item-options-btn" title="Options" onclick="openRecentChatMenu(event, '${escapeHtml(c.id)}', '${escapeHtml(c.title || '')}', ${Boolean(c.is_pinned)})">
                <i data-lucide="more-horizontal"></i>
            </button>
        </a>
    `}).join('');

    if (window.lucide) lucide.createIcons();
}

function selectRecentChat(e, convId) {
    if (window.location.pathname === '/' || window.location.pathname === '/student/' || window.location.pathname.endsWith('/chat') || window.location.pathname.startsWith('/student/chat')) {
        if (e) {
            e.preventDefault();
        }
        loadConversationMessages(convId);
        // Highlight active item
        document.querySelectorAll('.recent-chat-item').forEach(el => el.classList.remove('active'));
        if (e && e.currentTarget && e.currentTarget.classList) {
            e.currentTarget.classList.add('active');
        } else {
            const activeLink = document.querySelector(`.recent-chat-item[href*="${encodeURIComponent(convId)}"]`);
            if (activeLink) activeLink.classList.add('active');
        }
        // Close mobile drawer if open
        const sidebar = document.getElementById('sidebar');
        if (sidebar && sidebar.classList.contains('mobile-open')) {
            toggleMobileSidebar();
        }
        window.history.pushState(null, '', `/student/chat?conversation_id=${encodeURIComponent(convId)}`);
    } else {
        window.location.href = `/student/chat?conversation_id=${encodeURIComponent(convId)}`;
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

// =========================================================
// CHATGPT-STYLE RECENT CHAT & HEADER CONTEXT MENU ACTIONS
// =========================================================
let activeMenuConversationId = null;
let activeMenuConversationTitle = '';
let activeMenuIsPinned = false;
let activeMenuSource = null; // 'sidebar' | 'header'
let isActionProcessing = false;

function ensureContextMenuElements() {
    if (!document.getElementById('chatContextMenu')) {
        const menu = document.createElement('div');
        menu.id = 'chatContextMenu';
        menu.className = 'chat-context-menu';
        menu.setAttribute('role', 'menu');
        document.body.appendChild(menu);
    }

    if (!document.getElementById('chatActionModal')) {
        const modal = document.createElement('div');
        modal.id = 'chatActionModal';
        modal.className = 'chat-modal-backdrop';
        modal.style.display = 'none';
        modal.onclick = function(e) { if (e.target === modal) closeChatModal(); };
        modal.innerHTML = `
            <div class="chat-modal-box">
                <div class="chat-modal-header">
                    <h3 id="chatModalTitle">Rename Chat</h3>
                    <button type="button" class="chat-modal-close" onclick="closeChatModal()">&times;</button>
                </div>
                <div class="chat-modal-body" id="chatModalBody"></div>
                <div class="chat-modal-footer" id="chatModalFooter"></div>
            </div>
        `;
        document.body.appendChild(modal);
    }

    if (!document.getElementById('chatToast')) {
        const toast = document.createElement('div');
        toast.id = 'chatToast';
        toast.className = 'chat-floating-toast';
        toast.style.display = 'none';
        toast.innerHTML = `
            <i data-lucide="check-circle" id="chatToastIcon"></i>
            <span id="chatToastMessage">Done</span>
        `;
        document.body.appendChild(toast);
    }

    if (window.lucide) lucide.createIcons();
}

function showChatToast(message, isError = false) {
    ensureContextMenuElements();
    const toast = document.getElementById('chatToast');
    const toastMsg = document.getElementById('chatToastMessage');
    const toastIcon = document.getElementById('chatToastIcon');
    if (!toast || !toastMsg) return;

    toastMsg.textContent = message;
    if (toastIcon) {
        toastIcon.setAttribute('data-lucide', isError ? 'alert-circle' : 'check-circle');
        toastIcon.style.color = isError ? '#EF4444' : '#10B981';
    }
    toast.style.display = 'flex';
    if (window.lucide) lucide.createIcons();

    setTimeout(() => toast.classList.add('show'), 10);
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => { toast.style.display = 'none'; }, 220);
    }, 2800);
}

function openRecentChatMenu(e, convId, title, isPinned = false) {
    e.preventDefault();
    e.stopPropagation();

    ensureContextMenuElements();

    const menu = document.getElementById('chatContextMenu');
    if (menu && menu.classList.contains('active') && activeMenuConversationId === convId && activeMenuSource === 'sidebar') {
        closeRecentChatMenu();
        return;
    }

    closeRecentChatMenu();

    activeMenuConversationId = convId;
    activeMenuConversationTitle = title;
    activeMenuIsPinned = Boolean(isPinned);
    activeMenuSource = 'sidebar';

    if (!menu) return;

    // Sidebar menu items: Rename, Divider, Pin, Archive, Delete
    menu.innerHTML = `
        <button type="button" class="context-menu-item" onclick="handleContextMenuAction('rename')">
            <i data-lucide="edit-3"></i>
            <span>Rename</span>
        </button>
        <div class="context-menu-divider"></div>
        <button type="button" class="context-menu-item" id="contextMenuPinBtn" onclick="handleContextMenuAction('pin')">
            <i data-lucide="${activeMenuIsPinned ? 'pin-off' : 'pin'}" id="contextMenuPinIcon"></i>
            <span id="contextMenuPinText">${activeMenuIsPinned ? 'Unpin chat' : 'Pin chat'}</span>
        </button>
        <button type="button" class="context-menu-item" onclick="handleContextMenuAction('archive')">
            <i data-lucide="archive"></i>
            <span>Archive</span>
        </button>
        <button type="button" class="context-menu-item danger" onclick="handleContextMenuAction('delete')">
            <i data-lucide="trash-2"></i>
            <span>Delete</span>
        </button>
    `;

    const btnRect = e.currentTarget.getBoundingClientRect();
    const menuWidth = window.innerWidth <= 480 ? 210 : 250;
    const menuHeight = 220;

    let left = btnRect.right + 6;
    let top = btnRect.top - 4;

    // Reposition to left if near right edge
    if (left + menuWidth > window.innerWidth - 10) {
        left = btnRect.left - menuWidth - 6;
    }

    // Clamp inside viewport horizontally (375px/768px screens)
    if (left < 10) {
        left = Math.max(10, Math.min(window.innerWidth - menuWidth - 10, btnRect.left));
    }

    // Reposition upward if near bottom edge (handles bottom-most chat)
    if (top + menuHeight > window.innerHeight - 10) {
        top = Math.max(10, window.innerHeight - menuHeight - 10);
    }
    if (top < 10) top = 10;

    menu.style.left = `${left}px`;
    menu.style.top = `${top}px`;
    menu.classList.add('active');

    if (window.lucide) lucide.createIcons();
}

function closeRecentChatMenu() {
    const menu = document.getElementById('chatContextMenu');
    if (menu) menu.classList.remove('active');
    activeMenuSource = null;
}

function closeChatModal() {
    const modal = document.getElementById('chatActionModal');
    if (modal) modal.style.display = 'none';
}

async function handleContextMenuAction(action) {
    const convId = activeMenuConversationId;
    const currentTitle = activeMenuConversationTitle;
    closeRecentChatMenu();

    if (action === 'view_files') {
        if (isActionProcessing) return;
        isActionProcessing = true;
        try {
            ensureContextMenuElements();
            const modal = document.getElementById('chatActionModal');
            const modalTitle = document.getElementById('chatModalTitle');
            const modalBody = document.getElementById('chatModalBody');
            const modalFooter = document.getElementById('chatModalFooter');

            if (modalTitle) modalTitle.innerHTML = `<i data-lucide="folder" style="width:18px; height:18px; vertical-align:middle; margin-right:6px; color:#60A5FA;"></i> Files in this Chat`;
            if (modalBody) {
                modalBody.innerHTML = `
                    <div style="display:flex; align-items:center; justify-content:center; padding:24px 0; color:#9CA3AF; gap:8px;">
                        <i data-lucide="loader" class="spin-icon"></i>
                        <span>Fetching conversation files...</span>
                    </div>
                `;
            }
            if (modalFooter) {
                modalFooter.innerHTML = `
                    <button type="button" class="chat-modal-btn secondary" onclick="closeChatModal()">Close</button>
                `;
            }
            modal.style.display = 'flex';
            if (window.lucide) lucide.createIcons();

            if (!convId) {
                modalBody.innerHTML = `
                    <div style="text-align:center; padding:24px 12px;">
                        <div style="width:48px; height:48px; border-radius:14px; background:rgba(255,255,255,0.06); display:flex; align-items:center; justify-content:center; margin:0 auto 12px; color:#9CA3AF;">
                            <i data-lucide="file-x" style="width:24px; height:24px;"></i>
                        </div>
                        <p style="color:#F5F5F7; font-weight:600; margin-bottom:4px;">No Attached Files</p>
                        <p style="font-size:13px; color:#9CA3AF; margin:0;">Start chatting or upload a document to view attachments here.</p>
                    </div>
                `;
                if (window.lucide) lucide.createIcons();
                return;
            }

            const res = await fetch(`/chat/${encodeURIComponent(convId)}`);
            const data = await res.json();
            const messages = data.messages || [];

            const files = [];
            messages.forEach(m => {
                if (m.image_path) {
                    files.push({ type: 'image', path: m.image_path, name: m.image_path.split('/').pop() });
                }
                if (Array.isArray(m.sources) && m.sources.length > 0) {
                    m.sources.forEach(src => {
                        files.push({ type: 'source', name: src.name || src.title || (typeof src === 'string' ? src : 'Academic Document'), url: src.url || '#' });
                    });
                }
            });

            if (files.length === 0) {
                modalBody.innerHTML = `
                    <div style="text-align:center; padding:24px 12px;">
                        <div style="width:48px; height:48px; border-radius:14px; background:rgba(255,255,255,0.06); display:flex; align-items:center; justify-content:center; margin:0 auto 12px; color:#9CA3AF;">
                            <i data-lucide="file-x" style="width:24px; height:24px;"></i>
                        </div>
                        <p style="color:#F5F5F7; font-weight:600; margin-bottom:4px;">No Attached Files</p>
                        <p style="font-size:13px; color:#9CA3AF; margin:0;">No document files or images were uploaded or referenced in this conversation.</p>
                    </div>
                `;
            } else {
                let html = `<div style="display:flex; flex-direction:column; gap:8px; max-height:280px; overflow-y:auto;">`;
                files.forEach(f => {
                    html += `
                        <div style="display:flex; align-items:center; justify-content:space-between; background:rgba(255,255,255,0.05); padding:10px 14px; border-radius:10px; border:1px solid rgba(255,255,255,0.08);">
                            <div style="display:flex; align-items:center; gap:10px; overflow:hidden;">
                                <i data-lucide="${f.type === 'image' ? 'image' : 'file-text'}" style="width:18px; height:18px; color:#60A5FA; flex-shrink:0;"></i>
                                <span style="font-size:13px; color:#F5F5F7; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">${escapeHtml(f.name)}</span>
                            </div>
                            ${f.path ? `<a href="${escapeHtml(f.path)}" target="_blank" style="color:#60A5FA; font-size:12px; text-decoration:none; font-weight:500;">View</a>` : ''}
                        </div>
                    `;
                });
                html += `</div>`;
                modalBody.innerHTML = html;
            }
            if (window.lucide) lucide.createIcons();
        } catch (err) {
            showChatToast("Failed to load conversation files.", true);
        } finally {
            isActionProcessing = false;
        }
    } else if (action === 'rename') {
        if (!convId) return;
        ensureContextMenuElements();
        const modal = document.getElementById('chatActionModal');
        const modalTitle = document.getElementById('chatModalTitle');
        const modalBody = document.getElementById('chatModalBody');
        const modalFooter = document.getElementById('chatModalFooter');

        if (modalTitle) modalTitle.textContent = "Rename Conversation";
        if (modalBody) {
            modalBody.innerHTML = `
                <label style="display:block; margin-bottom:8px; font-size:13px; color:#9CA3AF;">Conversation title</label>
                <input type="text" id="renameChatInput" class="chat-modal-input" value="${escapeHtml(currentTitle)}" maxlength="100" />
            `;
        }
        if (modalFooter) {
            modalFooter.innerHTML = `
                <button type="button" class="chat-modal-btn secondary" onclick="closeChatModal()">Cancel</button>
                <button type="button" class="chat-modal-btn primary" id="confirmRenameBtn" onclick="submitRenameChat('${escapeHtml(convId)}')">Save</button>
            `;
        }
        modal.style.display = 'flex';
        const input = document.getElementById('renameChatInput');
        if (input) {
            input.focus();
            input.select();
            input.onkeydown = function(e) {
                if (e.key === 'Enter') submitRenameChat(convId);
            };
        }
    } else if (action === 'pin') {
        if (!convId) {
            showChatToast("No active chat to pin.");
            return;
        }
        try {
            const res = await fetch(`/chat/${encodeURIComponent(convId)}/pin`, { method: 'POST' });
            const data = await res.json();
            if (res.ok) {
                const isPinned = Boolean(data.is_pinned);
                cachedRecentChats = cachedRecentChats.map(c => c.id === convId ? { ...c, is_pinned: isPinned } : c);
                renderRecentChatsList(cachedRecentChats);
                showChatToast(isPinned ? "Chat pinned to top." : "Chat unpinned.");
            } else {
                showChatToast(data.message || "Failed to update pin state.", true);
            }
        } catch (err) {
            showChatToast("Error updating pin state.", true);
        }
    } else if (action === 'archive') {
        if (!convId) {
            showChatToast("Chat archived.");
            return;
        }
        cachedRecentChats = cachedRecentChats.filter(c => c.id !== convId);
        renderRecentChatsList(cachedRecentChats);
        const activeInput = document.getElementById('activeConversationId');
        if (activeInput && activeInput.value === convId) {
            if (typeof resetChat === 'function') resetChat();
        }
        showChatToast("Chat archived.");
    } else if (action === 'delete') {
        if (!convId) {
            showChatToast("No active conversation to delete.");
            return;
        }
        ensureContextMenuElements();
        const modal = document.getElementById('chatActionModal');
        const modalTitle = document.getElementById('chatModalTitle');
        const modalBody = document.getElementById('chatModalBody');
        const modalFooter = document.getElementById('chatModalFooter');

        if (modalTitle) modalTitle.textContent = "Delete Conversation?";
        if (modalBody) {
            modalBody.innerHTML = `
                <p style="margin:0 0 8px 0; color:#F5F5F7; font-weight:500;">Are you sure you want to delete this chat?</p>
                <p style="margin:0; font-size:13px; color:#9CA3AF;">This action cannot be undone and will permanently delete all messages in <em>"${escapeHtml(currentTitle)}"</em>.</p>
            `;
        }
        if (modalFooter) {
            modalFooter.innerHTML = `
                <button type="button" class="chat-modal-btn secondary" onclick="closeChatModal()">Cancel</button>
                <button type="button" class="chat-modal-btn danger" id="confirmDeleteBtn" onclick="submitDeleteChat('${escapeHtml(convId)}')">Delete</button>
            `;
        }
        modal.style.display = 'flex';
    }
}

async function submitRenameChat(convId) {
    const input = document.getElementById('renameChatInput');
    const newTitle = (input?.value || '').trim();
    if (!newTitle) return;

    const btn = document.getElementById('confirmRenameBtn');
    if (btn) {
        btn.disabled = true;
        btn.textContent = "Saving...";
    }

    try {
        const res = await fetch(`/chat/${encodeURIComponent(convId)}/rename`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ title: newTitle })
        });
        const data = await res.json();
        if (res.ok) {
            cachedRecentChats = cachedRecentChats.map(c => c.id === convId ? { ...c, title: newTitle } : c);
            renderRecentChatsList(cachedRecentChats);
            closeChatModal();
            showChatToast("Conversation renamed.");
        } else {
            showChatToast(data.message || "Failed to rename.", true);
        }
    } catch (err) {
        showChatToast("Error renaming conversation.", true);
    }
}

async function submitDeleteChat(convId) {
    const btn = document.getElementById('confirmDeleteBtn');
    if (btn) {
        btn.disabled = true;
        btn.textContent = "Deleting...";
    }

    try {
        const res = await fetch(`/chat/${encodeURIComponent(convId)}`, { method: 'DELETE' });
        const data = await res.json();
        if (res.ok) {
            cachedRecentChats = cachedRecentChats.filter(c => c.id !== convId);
            renderRecentChatsList(cachedRecentChats);
            closeChatModal();

            const activeInput = document.getElementById('activeConversationId');
            if (activeInput && activeInput.value === convId) {
                if (typeof resetChat === 'function') {
                    resetChat();
                }
            }
            showChatToast("Conversation deleted.");
        } else {
            showChatToast(data.message || "Failed to delete.", true);
        }
    } catch (err) {
        showChatToast("Error deleting conversation.", true);
    }
}

// Global click and keydown listeners for closing context menu
document.addEventListener('click', function(e) {
    const menu = document.getElementById('chatContextMenu');
    if (menu && menu.classList.contains('active') && !menu.contains(e.target) && !e.target.closest('.recent-item-options-btn')) {
        closeRecentChatMenu();
    }
});

document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') {
        closeRecentChatMenu();
        closeChatModal();
    }
});

window.openRecentChatMenu = openRecentChatMenu;
window.closeRecentChatMenu = closeRecentChatMenu;
window.handleContextMenuAction = handleContextMenuAction;
window.submitRenameChat = submitRenameChat;
window.submitDeleteChat = submitDeleteChat;
window.closeChatModal = closeChatModal;
window.smoothScrollToBottom = smoothScrollToBottom;
window.checkScrollToBottomVisibility = checkScrollToBottomVisibility;
