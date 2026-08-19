/**
 * SVIT AI Assistant Phase 2 Engine
 * Theme Persistence, History Management & Notifications
 */

document.addEventListener('DOMContentLoaded', () => {
    initTheme();
    loadNotifications();
    loadChatHistory();
});

/* -------------------------------------------------------------------------
   1. Theme & Appearance Manager
   ------------------------------------------------------------------------- */
function initTheme() {
    const savedTheme = localStorage.getItem('svit_theme') || 'system';
    applyTheme(savedTheme);
}

function applyTheme(theme) {
    let activeTheme = theme;
    if (theme === 'system') {
        activeTheme = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
    }
    document.documentElement.setAttribute('data-theme', activeTheme);
    localStorage.setItem('svit_theme', theme);
}

/* -------------------------------------------------------------------------
   2. Chat History & Saved Conversations Manager
   ------------------------------------------------------------------------- */
async function loadChatHistory(query = '') {
    try {
        const res = await fetch(`/chat/history?search=${encodeURIComponent(query)}`);
        const data = await res.json();
        
        if (data.status === 'success') {
            renderHistorySidebar(data.history);
        }
    } catch (err) {
        console.error('Failed to load chat history:', err);
    }
}

function renderHistorySidebar(history) {
    const container = document.getElementById('historyContainer');
    if (!container) return;

    container.innerHTML = '';
    const sections = [
        { key: 'today', title: 'Today' },
        { key: 'yesterday', title: 'Yesterday' },
        { key: 'last_7_days', title: 'Last 7 Days' },
        { key: 'last_month', title: 'Last Month' },
        { key: 'older', title: 'Older' }
    ];

    sections.forEach(sec => {
        const items = history[sec.key];
        if (items && items.length > 0) {
            const groupTitle = document.createElement('div');
            groupTitle.className = 'history-group-title';
            groupTitle.innerText = sec.title;
            container.appendChild(groupTitle);

            items.forEach(chat => {
                const item = document.createElement('div');
                item.className = 'history-item';
                item.onclick = () => loadConversationMessages(chat.id);
                item.innerHTML = `
                    <div class="text-truncate" style="max-width: 180px;">
                        <i class="bi bi-chat-left-text me-2"></i>
                        <span>${escapeHtml(chat.title)}</span>
                    </div>
                    <div class="actions">
                        <button class="btn btn-sm text-warning" onclick="event.stopPropagation(); toggleSaveChat('${chat.id}')" title="Bookmark">
                            <i class="bi bi-star${chat.is_saved ? '-fill' : ''}"></i>
                        </button>
                        <button class="btn btn-sm text-danger" onclick="event.stopPropagation(); deleteChat('${chat.id}')" title="Delete">
                            <i class="bi bi-trash"></i>
                        </button>
                    </div>
                `;
                container.appendChild(item);
            });
        }
    });
}

async function toggleSaveChat(convId) {
    try {
        const res = await fetch(`/chat/${convId}/toggle-save`, { method: 'POST' });
        const data = await res.json();
        if (data.status === 'success') {
            showToast(data.message, 'success');
            loadChatHistory();
        }
    } catch (err) {
        showToast('Failed to update bookmark.', 'danger');
    }
}

async function deleteChat(convId) {
    if (!confirm('Are you sure you want to delete this chat?')) return;
    try {
        const res = await fetch(`/chat/${convId}`, { method: 'DELETE' });
        const data = await res.json();
        if (data.status === 'success') {
            showToast('Conversation deleted.', 'info');
            loadChatHistory();
        }
    } catch (err) {
        showToast('Failed to delete chat.', 'danger');
    }
}

/* -------------------------------------------------------------------------
   3. Notification Center Manager
   ------------------------------------------------------------------------- */
async function loadNotifications() {
    try {
        const res = await fetch('/notifications/');
        const data = await res.json();
        if (data.status === 'success') {
            const badge = document.getElementById('notifBadge');
            if (badge) {
                badge.innerText = data.unread_count;
                badge.style.display = data.unread_count > 0 ? 'inline-block' : 'none';
            }
            renderNotificationList(data.notifications);
        }
    } catch (err) {
        console.error('Failed to load notifications:', err);
    }
}

function renderNotificationList(notifications) {
    const list = document.getElementById('notifList');
    if (!list) return;

    if (notifications.length === 0) {
        list.innerHTML = `<div class="p-3 text-center text-muted">No notifications found.</div>`;
        return;
    }

    list.innerHTML = notifications.map(n => `
        <div class="notif-card ${n.is_read ? '' : 'unread'}" id="notif-${n.id}">
            <div class="d-flex justify-content-between align-items-start">
                <h6 class="mb-1 text-sm font-bold">${escapeHtml(n.title)}</h6>
                <small class="text-muted" style="font-size: 0.7rem;">${n.created_at}</small>
            </div>
            <p class="mb-1 text-xs text-muted">${escapeHtml(n.description)}</p>
            <div class="d-flex justify-content-end gap-2 mt-2">
                ${!n.is_read ? `<button class="btn btn-xs btn-link text-primary p-0" onclick="markNotifRead(${n.id})">Mark Read</button>` : ''}
                <button class="btn btn-xs btn-link text-danger p-0" onclick="deleteNotif(${n.id})">Delete</button>
            </div>
        </div>
    `).join('');
}

async function markNotifRead(id) {
    await fetch(`/notifications/${id}/read`, { method: 'PATCH' });
    loadNotifications();
}

async function deleteNotif(id) {
    await fetch(`/notifications/${id}`, { method: 'DELETE' });
    loadNotifications();
}

/* -------------------------------------------------------------------------
   4. Helper Functions
   ------------------------------------------------------------------------- */
function escapeHtml(str) {
    return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

function showToast(message, type = 'info') {
    const toastEl = document.getElementById('appToast');
    const toastBody = document.getElementById('toastBody');
    if (toastEl && toastBody) {
        toastBody.innerText = message;
        toastEl.className = `toast align-items-center text-white bg-${type} border-0`;
        const bsToast = new bootstrap.Toast(toastEl);
        bsToast.show();
    }
}