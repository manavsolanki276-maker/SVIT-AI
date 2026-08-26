/**
 * SVIT Admin - Page 13: Notices & Announcements Controller
 * Priority badges (Emergency animated), target audience filtering,
 * circular attachment upload (PDF/Image), pin/publish toggle, add/edit/delete.
 */

(function() {
    'use strict';

    const state = {
        search: '',
        priority: '',
        target: '',
        page: 1,
        limit: 50,
        total: 0,
        items: [],
        pendingDeleteId: null,
        uploadedDocData: null
    };

    let noticeModal = null;
    let noticeViewModal = null;
    let noticeDeleteModal = null;
    let searchDebounce = null;

    function escapeHtml(value) {
        return String(value || '')
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
    }

    function escapeQuotes(value) {
        return String(value || '')
            .replace(/\\/g, '\\\\')
            .replace(/'/g, "\\'")
            .replace(/"/g, '&quot;');
    }

    document.addEventListener('DOMContentLoaded', function() {
        const formEl = document.getElementById('noticeFormModal');
        const viewEl = document.getElementById('noticeViewModal');
        const delEl = document.getElementById('noticeDeleteModal');

        if (formEl) noticeModal = new bootstrap.Modal(formEl);
        if (viewEl) noticeViewModal = new bootstrap.Modal(viewEl);
        if (delEl) noticeDeleteModal = new bootstrap.Modal(delEl);

        bindEvents();
        setupCircularUpload();
        loadNotices();
    });

    function bindEvents() {
        const searchInput = document.getElementById('noticeSearchInput');
        if (searchInput) {
            searchInput.addEventListener('input', (e) => {
                clearTimeout(searchDebounce);
                searchDebounce = setTimeout(() => {
                    state.search = e.target.value.trim();
                    state.page = 1;
                    loadNotices();
                }, 300);
            });
        }

        const priorityFilter = document.getElementById('noticePriorityFilter');
        if (priorityFilter) {
            priorityFilter.addEventListener('change', (e) => {
                state.priority = e.target.value;
                state.page = 1;
                loadNotices();
            });
        }

        const targetFilter = document.getElementById('noticeTargetFilter');
        if (targetFilter) {
            targetFilter.addEventListener('change', (e) => {
                state.target = e.target.value;
                state.page = 1;
                loadNotices();
            });
        }

        const refreshBtn = document.getElementById('refreshNoticesBtn');
        if (refreshBtn) refreshBtn.addEventListener('click', loadNotices);

        const limitSelect = document.getElementById('pageLimitSelect');
        if (limitSelect) {
            limitSelect.addEventListener('change', (e) => {
                state.limit = parseInt(e.target.value, 10) || 50;
                state.page = 1;
                loadNotices();
            });
        }

        const prevBtn = document.getElementById('prevPageBtn');
        if (prevBtn) {
            prevBtn.addEventListener('click', () => {
                if (state.page > 1) {
                    state.page--;
                    loadNotices();
                }
            });
        }

        const nextBtn = document.getElementById('nextPageBtn');
        if (nextBtn) {
            nextBtn.addEventListener('click', () => {
                const totalPages = Math.ceil(state.total / state.limit) || 1;
                if (state.page < totalPages) {
                    state.page++;
                    loadNotices();
                }
            });
        }

        const createBtn = document.getElementById('openCreateNoticeModalBtn');
        if (createBtn) {
            createBtn.addEventListener('click', () => {
                document.getElementById('noticeModalTitle').innerText = 'Publish Campus Notice';
                document.getElementById('noticeFormRecordId').value = '';
                document.getElementById('noticeForm').reset();
                document.getElementById('noticeIdInput').disabled = false;
                state.uploadedDocData = null;
                resetCircularPreview();
                noticeModal.show();
            });
        }

        const form = document.getElementById('noticeForm');
        if (form) form.addEventListener('submit', handleNoticeFormSubmit);

        const confirmDeleteBtn = document.getElementById('confirmDeleteNoticeBtn');
        if (confirmDeleteBtn) confirmDeleteBtn.addEventListener('click', handleConfirmDelete);
    }

    function setupCircularUpload() {
        const dropZone = document.getElementById('circularFileDropZone');
        const fileInput = document.getElementById('circularFileInput');

        if (dropZone && fileInput) {
            dropZone.addEventListener('click', () => fileInput.click());
            dropZone.addEventListener('dragover', (e) => { e.preventDefault(); dropZone.classList.add('border-[#8B5CF6]'); });
            dropZone.addEventListener('dragleave', () => dropZone.classList.remove('border-[#8B5CF6]'));
            dropZone.addEventListener('drop', (e) => {
                e.preventDefault();
                dropZone.classList.remove('border-[#8B5CF6]');
                if (e.dataTransfer.files.length) uploadCircularDoc(e.dataTransfer.files[0]);
            });
            fileInput.addEventListener('change', (e) => {
                if (e.target.files.length) uploadCircularDoc(e.target.files[0]);
            });
        }
    }

    async function uploadCircularDoc(file) {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('category', 'document');

        const preview = document.getElementById('circularFilePreviewContainer');
        if (preview) {
            preview.innerHTML = '<span class="text-xs text-[#8B5CF6]">Uploading document...</span>';
            preview.classList.remove('hidden');
        }

        try {
            const res = await fetch('/admin/api/upload', { method: 'POST', body: formData });
            const data = await res.json();
            if (res.ok && data.status === 'success') {
                state.uploadedDocData = data.file;
                if (preview) {
                    preview.innerHTML = `
                        <div class="flex items-center gap-2 p-2.5 rounded-xl bg-emerald-50 border border-emerald-200 text-xs">
                            <i data-lucide="file-text" class="w-4 h-4 text-emerald-600"></i>
                            <span class="text-[#171D3A] font-semibold">${escapeHtml(data.file.file_name)}</span>
                            <span class="text-[#66708F] text-[10px]">(${escapeHtml(data.file.file_size_formatted || '')})</span>
                        </div>
                    `;
                    lucide.createIcons();
                }
                showAdminToast('Notice attachment uploaded.', 'success');
            } else {
                showAdminToast(data.message || 'File upload failed.', 'error');
                resetCircularPreview();
            }
        } catch (err) {
            showAdminToast(err.message, 'error');
            resetCircularPreview();
        }
    }

    function resetCircularPreview() {
        const preview = document.getElementById('circularFilePreviewContainer');
        if (preview) {
            preview.innerHTML = '';
            preview.classList.add('hidden');
        }
    }

    async function loadNotices() {
        const tbody = document.getElementById('noticesTableBody');
        const mobileCards = document.getElementById('noticesMobileCards');
        if (!tbody) return;

        tbody.innerHTML = `
            <tr>
                <td colspan="7" class="text-center py-12 text-[#66708F] text-xs">
                    <div class="inline-block animate-spin rounded-full h-5 w-5 border-2 border-[#8B5CF6] border-t-transparent mb-2"></div>
                    <p class="mb-0">Loading published notices...</p>
                </td>
            </tr>
        `;
        if (mobileCards) mobileCards.innerHTML = '<div class="admin-mobile-empty">Loading notices...</div>';

        const params = new URLSearchParams({
            page: state.page,
            limit: state.limit
        });
        if (state.search) params.append('search', state.search);
        if (state.priority) params.append('filter_priority', state.priority);
        if (state.target) params.append('filter_target_audience', state.target);

        try {
            const res = await fetch(`/admin/api/crud/notices?${params.toString()}`);
            const data = await res.json();
            if (res.ok && (data.status === 'success' || Array.isArray(data.items))) {
                state.items = Array.isArray(data.items)
                    ? data.items
                    : (Array.isArray(data?.data?.items) ? data.data.items : (Array.isArray(data?.data) ? data.data : []));
                state.total = typeof data.total === 'number'
                    ? data.total
                    : (typeof data?.data?.total === 'number' ? data.data.total : state.items.length);
                renderNoticesTable();
                renderPagination(data.pages || data?.data?.pages || 1);
                updateEmergencyTicker();
            } else {
                showAdminToast(data.message || 'Failed to load notices.', 'error');
            }
        } catch (err) {
            showAdminToast(err.message, 'error');
        }
        lucide.createIcons();
    }

    function renderPagination(totalPages) {
        const pagWrapper = document.getElementById('noticesPagination');
        if (!pagWrapper) return;

        if (totalPages <= 1) {
            pagWrapper.classList.add('hidden');
            return;
        }

        pagWrapper.classList.remove('hidden');
        const start = (state.page - 1) * state.limit + 1;
        const end = Math.min(state.page * state.limit, state.total);
        const startEl = document.getElementById('pageStart');
        const endEl = document.getElementById('pageEnd');
        const totalEl = document.getElementById('pageTotal');
        if (startEl) startEl.innerText = start;
        if (endEl) endEl.innerText = end;
        if (totalEl) totalEl.innerText = state.total;

        const prevBtn = document.getElementById('prevPageBtn');
        const nextBtn = document.getElementById('nextPageBtn');

        if (prevBtn) {
            prevBtn.disabled = state.page <= 1;
            prevBtn.onclick = () => {
                if (state.page > 1) {
                    state.page--;
                    loadNotices();
                }
            };
        }

        if (nextBtn) {
            nextBtn.disabled = state.page >= totalPages;
            nextBtn.onclick = () => {
                if (state.page < totalPages) {
                    state.page++;
                    loadNotices();
                }
            };
        }

        const numbersContainer = document.getElementById('pageNumbers');
        if (numbersContainer) {
            numbersContainer.innerHTML = '';
            const maxVisible = 5;
            let startP = Math.max(1, state.page - Math.floor(maxVisible / 2));
            let endP = Math.min(totalPages, startP + maxVisible - 1);
            if (endP - startP < maxVisible - 1) {
                startP = Math.max(1, endP - maxVisible + 1);
            }

            for (let i = startP; i <= endP; i++) {
                const btn = document.createElement('button');
                btn.innerText = i;
                btn.className = `px-2 py-1 rounded-lg text-xs font-semibold transition ${state.page === i ? 'bg-[#8B5CF6] text-white' : 'bg-white border border-[#E1E5F0] text-[#66708F] hover:text-[#171D3A]'}`;
                btn.onclick = () => {
                    state.page = i;
                    loadNotices();
                };
                numbersContainer.appendChild(btn);
            }
        }
    }

    function updateEmergencyTicker() {
        const ticker = document.getElementById('emergencyNoticeTicker');
        if (!ticker) return;

        const emergency = state.items.find(n => (n.priority || '').toLowerCase() === 'emergency');
        if (emergency) {
            ticker.innerHTML = `
                <div class="flex items-center justify-between gap-3 p-3.5 rounded-2xl bg-red-50 border border-red-200 text-[#171D3A] shadow-sm">
                    <div class="flex items-center gap-3 flex-wrap">
                        <span class="badge-emergency-pulse"><i data-lucide="alert-octagon" class="w-3.5 h-3.5"></i> ACTIVE EMERGENCY</span>
                        <span class="text-xs font-bold text-[#171D3A]">${escapeHtml(emergency.title)}</span>
                        <span class="text-xs text-red-600">${escapeHtml(emergency.publish_date || 'Today')}</span>
                    </div>
                    <button class="px-3 py-1.5 rounded-xl bg-red-600 hover:bg-red-700 text-white text-xs font-semibold flex-shrink-0" onclick="window.viewNotice('${escapeQuotes(emergency.id || emergency.notice_id)}')">View</button>
                </div>
            `;
            ticker.classList.remove('hidden');
            lucide.createIcons();
        } else {
            ticker.classList.add('hidden');
        }
    }

    function renderNoticesTable() {
        const tbody = document.getElementById('noticesTableBody');
        const mobileCards = document.getElementById('noticesMobileCards');
        const countBadge = document.getElementById('noticesCountBadge');
        if (countBadge) countBadge.innerText = `${state.total} Notices`;

        if (state.items.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="7" class="text-center py-12 text-[#66708F] text-xs">
                        <i data-lucide="megaphone" class="w-8 h-8 mx-auto mb-2 text-[#8C95AD]"></i>
                        <p class="mb-0">No notices or announcements found.</p>
                    </td>
                </tr>
            `;
            if (mobileCards) mobileCards.innerHTML = '<div class="admin-mobile-empty">No notices found matching active filters.</div>';
            lucide.createIcons();
            return;
        }

        tbody.innerHTML = state.items.map(n => {
            const id = n.notice_id || n.id || '-';
            const title = n.title || 'Notice';
            const cat = n.category || 'General Circular';
            const priority = (n.priority || 'Normal').toLowerCase();
            const target = n.target_audience || 'All';
            const date = n.publish_date || 'Recent';
            const fileUrl = n.file_url;

            let badgeHtml = '';
            if (priority === 'emergency') {
                badgeHtml = '<span class="badge-emergency-pulse"><i data-lucide="alert-triangle" class="w-3 h-3"></i> EMERGENCY</span>';
            } else if (priority === 'high') {
                badgeHtml = '<span class="badge-priority-high">High</span>';
            } else if (priority === 'low') {
                badgeHtml = '<span class="badge-priority-low">Low</span>';
            } else {
                badgeHtml = '<span class="badge-priority-normal">Normal</span>';
            }

            return `
                <tr>
                    <td>
                        <div class="flex items-center gap-2.5">
                            <div class="pdf-icon-badge">
                                <i data-lucide="megaphone" class="w-4 h-4"></i>
                            </div>
                            <div>
                                <p class="text-xs font-bold text-[#171D3A] mb-0">${escapeHtml(title)}</p>
                                <span class="text-[10px] text-[#66708F] font-mono">${escapeHtml(id)}</span>
                            </div>
                        </div>
                    </td>
                    <td class="text-[#171D3A] text-xs">${escapeHtml(cat)}</td>
                    <td>${badgeHtml}</td>
                    <td class="text-[#66708F] text-xs">${escapeHtml(target)}</td>
                    <td class="text-[#66708F] text-xs">${escapeHtml(date)}</td>
                    <td>
                        ${fileUrl ? `
                            <a href="${fileUrl}" target="_blank" class="text-[#8B5CF6] hover:underline text-xs font-semibold flex items-center gap-1 text-decoration-none">
                                <i data-lucide="paperclip" class="w-3.5 h-3.5"></i> File
                            </a>
                        ` : '<span class="text-[#8C95AD] text-xs">-</span>'}
                    </td>
                    <td class="text-end">
                        <div class="inline-flex items-center gap-1.5">
                            <button class="p-1.5 rounded-lg bg-white border border-[#E1E5F0] text-[#171D3A] hover:bg-[#E8EBFA]" onclick="window.viewNotice('${escapeQuotes(id)}')" title="View Notice">
                                <i data-lucide="eye" class="w-3.5 h-3.5"></i>
                            </button>
                            <button class="p-1.5 rounded-lg bg-white border border-[#E1E5F0] text-[#171D3A] hover:bg-[#E8EBFA]" onclick="window.editNotice('${escapeQuotes(id)}')" title="Edit Notice">
                                <i data-lucide="edit-2" class="w-3.5 h-3.5"></i>
                            </button>
                            <button class="p-1.5 rounded-lg bg-white border border-[#E1E5F0] text-red-600 hover:bg-red-50" onclick="window.deleteNotice('${escapeQuotes(id)}')" title="Delete">
                                <i data-lucide="trash-2" class="w-3.5 h-3.5"></i>
                            </button>
                        </div>
                    </td>
                </tr>
            `;
        }).join('');

        if (mobileCards) {
            mobileCards.innerHTML = state.items.map(n => {
                const id = n.notice_id || n.id || '-';
                const title = n.title || 'Notice';
                const cat = n.category || 'General Circular';
                const priority = (n.priority || 'Normal').toLowerCase();
                const target = n.target_audience || 'All';
                const date = n.publish_date || 'Recent';
                const fileUrl = n.file_url;
                const badge = priority === 'emergency' ? 'badge-emergency-pulse' : priority === 'high' ? 'badge-priority-high' : priority === 'low' ? 'badge-priority-low' : 'badge-priority-normal';
                const priorityLabel = priority === 'emergency' ? 'EMERGENCY' : priority.toUpperCase();

                return `
                    <article class="admin-mobile-record-card">
                        <div class="admin-record-heading">
                            <div class="flex items-center gap-3 min-w-0">
                                <div class="admin-record-icon">
                                    <i data-lucide="megaphone"></i>
                                </div>
                                <div class="min-w-0">
                                    <h3>${escapeHtml(title)}</h3>
                                    <p>${escapeHtml(id)}</p>
                                </div>
                            </div>
                            <span class="${badge}">${priorityLabel}</span>
                        </div>
                        <div class="admin-record-meta">
                            <span><b>Category</b>${escapeHtml(cat)}</span>
                            <span><b>Audience</b>${escapeHtml(target)}</span>
                            <span><b>Published</b>${escapeHtml(date)}</span>
                        </div>
                        <div class="admin-record-actions">
                            <button type="button" onclick="window.viewNotice('${escapeQuotes(id)}')" title="View Notice">
                                <i data-lucide="eye"></i> <span>View</span>
                            </button>
                            ${fileUrl ? `
                                <a href="${fileUrl}" target="_blank" class="p-2 rounded-xl bg-white border border-[#E1E5F0] text-[#171D3A] text-xs font-semibold hover:bg-[#E8EBFA] inline-flex items-center gap-1 text-decoration-none" title="Attachment">
                                    <i data-lucide="paperclip" class="w-3.5 h-3.5"></i> <span>File</span>
                                </a>
                            ` : ''}
                            <button type="button" onclick="window.editNotice('${escapeQuotes(id)}')" title="Edit Notice">
                                <i data-lucide="edit-2"></i> <span>Edit</span>
                            </button>
                            <button type="button" class="is-danger" onclick="window.deleteNotice('${escapeQuotes(id)}')" title="Delete Notice">
                                <i data-lucide="trash-2"></i>
                            </button>
                        </div>
                    </article>
                `;
            }).join('');
        }

        lucide.createIcons();
    }

    async function handleNoticeFormSubmit(e) {
        e.preventDefault();
        const recordId = document.getElementById('noticeFormRecordId').value;
        const payload = {
            notice_id: document.getElementById('noticeIdInput').value.trim(),
            title: document.getElementById('noticeTitleInput').value.trim(),
            category: document.getElementById('noticeCategoryInput').value,
            priority: document.getElementById('noticePriorityInput').value,
            target_audience: document.getElementById('noticeTargetInput').value,
            publish_date: document.getElementById('noticeDateInput').value,
            description: document.getElementById('noticeDescInput').value.trim()
        };

        if (state.uploadedDocData) {
            payload.file_url = state.uploadedDocData.url || state.uploadedDocData.file_url;
        }

        const isEdit = Boolean(recordId);
        const url = isEdit ? `/admin/api/crud/notices/${recordId}` : '/admin/api/crud/notices';
        const method = isEdit ? 'PUT' : 'POST';

        try {
            const res = await fetch(url, {
                method: method,
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            const data = await res.json();
            if (res.ok && data.status === 'success') {
                showAdminToast(data.message, 'success');
                noticeModal.hide();
                loadNotices();
            } else {
                showAdminToast(data.message || 'Error saving notice.', 'error');
            }
        } catch (err) {
            showAdminToast(err.message, 'error');
        }
    }

    window.editNotice = function(id) {
        const item = state.items.find(n => (n.notice_id || n.id) === id);
        if (!item) return;

        document.getElementById('noticeModalTitle').innerText = 'Edit Notice';
        document.getElementById('noticeFormRecordId').value = id;
        document.getElementById('noticeIdInput').value = item.notice_id || id;
        document.getElementById('noticeIdInput').disabled = true;
        document.getElementById('noticeTitleInput').value = item.title || '';
        document.getElementById('noticeCategoryInput').value = item.category || 'General Circular';
        document.getElementById('noticePriorityInput').value = item.priority || 'Normal';
        document.getElementById('noticeTargetInput').value = item.target_audience || 'All Students & Faculty';
        document.getElementById('noticeDateInput').value = item.publish_date || '';
        document.getElementById('noticeDescInput').value = item.description || '';

        state.uploadedDocData = item.file_url ? { file_url: item.file_url, file_name: 'Attached Circular' } : null;
        noticeModal.show();
    };

    window.viewNotice = function(id) {
        const item = state.items.find(n => (n.notice_id || n.id) === id);
        if (!item) return;

        const container = document.getElementById('noticeViewContent');
        if (!container) return;

        container.innerHTML = `
            <div class="space-y-3">
                <div class="flex items-center justify-between">
                    <span class="px-2.5 py-0.5 rounded-full text-xs font-bold bg-[#E8EBFA] text-[#8B5CF6]">${escapeHtml(item.category || 'Circular')}</span>
                    <span class="text-xs text-[#66708F]">${escapeHtml(item.publish_date || 'Today')}</span>
                </div>
                <h3 class="text-base font-bold text-[#171D3A] mb-1">${escapeHtml(item.title)}</h3>
                <p class="text-xs text-[#66708F] leading-relaxed">${escapeHtml(item.description || 'No content provided.')}</p>
                <div class="pt-3 border-t border-[#E1E5F0] flex justify-between items-center text-xs text-[#66708F]">
                    <span>Target: <strong class="text-[#171D3A]">${escapeHtml(item.target_audience || 'All')}</strong></span>
                    ${item.file_url ? `<a href="${item.file_url}" target="_blank" class="text-[#8B5CF6] font-semibold hover:underline flex items-center gap-1"><i data-lucide="paperclip" class="w-3.5 h-3.5"></i> View Attachment</a>` : ''}
                </div>
            </div>
        `;

        lucide.createIcons();
        noticeViewModal.show();
    };

    window.deleteNotice = function(id) {
        state.pendingDeleteId = id;
        document.getElementById('deleteNoticeTargetId').innerText = id;
        noticeDeleteModal.show();
    };

    async function handleConfirmDelete() {
        if (!state.pendingDeleteId) return;

        try {
            const res = await fetch(`/admin/api/crud/notices/${state.pendingDeleteId}`, { method: 'DELETE' });
            const data = await res.json();
            if (res.ok && data.status === 'success') {
                showAdminToast(data.message, 'success');
                noticeDeleteModal.hide();
                loadNotices();
            } else {
                showAdminToast(data.message || 'Failed to delete notice.', 'error');
            }
        } catch (err) {
            showAdminToast(err.message, 'error');
        }
    }
})();
