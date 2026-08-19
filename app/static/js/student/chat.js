document.addEventListener('DOMContentLoaded', () => {
    const chatForm = document.getElementById('chatForm');
    const chatInput = document.getElementById('chatInput');
    const chatThread = document.getElementById('chatThread');
    const typingIndicator = document.getElementById('typingIndicator');
    const welcomeSection = document.getElementById('welcomeSection');

    // =========================================================
    // 1. SIDEBAR NAVIGATION (Natural Browser Navigation)
    // =========================================================
    const navItems = document.querySelectorAll('.sidebar-nav .nav-item');
    navItems.forEach(item => {
        item.addEventListener('click', (e) => {
            const href = item.getAttribute('href');
            // If it's a real page link, let browser navigate naturally
            if (href && href !== '#' && !href.startsWith('javascript:')) {
                window.location.href = href;
            }
        });
    });

    // =========================================================
    // 2. CHAT FORM SUBMISSION
    // =========================================================
    if (chatForm) {
        chatForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const text = chatInput.value.trim();
            if (!text) return;

            // Hide welcome banner on first message
            if (welcomeSection) {
                welcomeSection.style.display = 'none';
            }

            // 1. Display User Message
            appendUserMessage(text);
            chatInput.value = '';

            // 2. Show Typing Indicator
            if (typingIndicator) {
                typingIndicator.style.display = 'flex';
            }
            scrollToBottom();

            try {
                // 3. Endpoint Fallback Chain
                let endpoints = ['/api/chat', '/student/api/chat', '/student/chat/api'];
                let response = null;
                let data = null;

                for (let url of endpoints) {
                    try {
                        let res = await fetch(url, {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ message: text })
                        });

                        if (res.status !== 404) {
                            response = res;
                            data = await res.json();
                            break;
                        }
                    } catch (err) {
                        console.warn(`Attempt failed for endpoint ${url}`);
                    }
                }

                if (typingIndicator) {
                    typingIndicator.style.display = 'none';
                }

                if (response && response.ok) {
                    const replyText = data.answer || data.response || "No response received.";
                    const imagePath = data.image || null; 
                    const sources = data.sources || [];
                    
                    appendBotMessage(replyText, imagePath, sources);
                } else {
                    const errorMsg = data?.error || `Error ${response?.status || '500'}: Failed to fetch response from server.`;
                    appendBotMessage(`⚠️ ${errorMsg}`, null, []);
                }
            } catch (error) {
                if (typingIndicator) {
                    typingIndicator.style.display = 'none';
                }
                console.error("Chat API Error:", error);
                appendBotMessage('⚠️ Error connecting to server. Please check your backend terminal logs.', null, []);
            }
        });
    }
});

// =========================================================
// 3. HELPER FUNCTIONS
// =========================================================

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

function appendBotMessage(text, imagePath = null, sources = []) {
    const chatThread = document.getElementById('chatThread');
    if (!chatThread) return;

    const botRow = document.createElement('div');
    botRow.classList.add('chat-row', 'bot-row');

    let formattedBody = '';
    if (typeof marked !== 'undefined') {
        marked.setOptions({ breaks: true, gfm: true });
        formattedBody = marked.parse(text);
    } else {
        formattedBody = escapeHtml(text)
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\n/g, '<br>');
    }

    let imageHTML = '';
    if (imagePath) {
        let fullSrc = imagePath.startsWith('/static/') 
            ? imagePath 
            : `/static/${imagePath.replace(/^static\//, '')}`;

        imageHTML = `
            <div class="map-container" style="margin-top: 12px; margin-bottom: 8px;">
                <img src="${fullSrc}" 
                     alt="Campus Map" 
                     class="campus-map" 
                     onerror="this.parentElement.style.display='none';"
                     style="max-width: 100%; border-radius: 10px; border: 1px solid #e2e8f0; box-shadow: 0 2px 8px rgba(0,0,0,0.06);">
            </div>
        `;
    }

    let sourcesHTML = '';
    if (sources && sources.length > 0) {
        sourcesHTML = `
            <div class="sources-container" style="margin-top: 10px; padding-top: 8px; border-top: 1px dashed #e0e0e0; font-size: 0.82rem; color: #666;">
                <strong>📚 Sources:</strong> ${sources.map(s => `<span class="source-tag" style="background: #f0f4f8; padding: 2px 6px; border-radius: 4px; margin-left: 4px;">${escapeHtml(s)}</span>`).join('')}
            </div>
        `;
    }

    botRow.innerHTML = `
        <div class="bot-avatar-box">
            <i data-lucide="bot"></i>
        </div>
        <div class="bot-card">
            <div class="bot-content">${formattedBody}</div>
            ${imageHTML}
            ${sourcesHTML}
            <div class="bot-card-actions" style="margin-top: 8px;">
                <button class="action-btn" onclick="copyText(this)"><i data-lucide="copy"></i> Copy</button>
                <button class="action-btn icon-only"><i data-lucide="thumbs-up"></i></button>
                <button class="action-btn icon-only"><i data-lucide="thumbs-down"></i></button>
            </div>
        </div>
    `;

    chatThread.appendChild(botRow);

    if (window.lucide) {
        lucide.createIcons();
    }

    scrollToBottom();
}

function sendSuggested(questionText) {
    const chatInput = document.getElementById('chatInput');
    const chatForm = document.getElementById('chatForm');
    if (chatInput && chatForm) {
        chatInput.value = questionText;
        chatForm.dispatchEvent(new Event('submit', { cancelable: true }));
    }
}

function scrollToBottom() {
    const chatContainer = document.querySelector('.chat-container') || document.getElementById('chatThread');
    if (chatContainer) {
        chatContainer.scrollTop = chatContainer.scrollHeight;
    }
}

function escapeHtml(text) {
    if (typeof text !== 'string') return text;
    return text.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
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