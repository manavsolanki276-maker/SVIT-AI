/**
 * SVIT Admin - Notices & Announcements Controller
 * Priority badges, target audience filtering, department & category filtering,
 * circular attachment upload (PDF/Image), emergency alert ticker, full CRUD.
 */

(function() {
    'use strict';

    const state = {
        search: '',
        category: '',
        priority: '',
        department: '',
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

    function showAdminToast(msg, type = 'success') {
        if (typeof window.showToast === 'function') {
            window.showToast(msg, type);
        } else if (typeof window.showNotification === 'function') {
            window.showNotification(msg, type);
        } else {
            console.log(`[Toast ${type}]`, msg);
        }
    }

    document.addEventListener('DOMContentLoaded', function() {
        const formEl = document.getElementById('noticeFormModal');
        const viewEl = document.getElementById('noticeViewModal');
        const delEl = document.getElementById('noticeDeleteModal');

        if (formEl && typeof bootstrap !== 'undefined') noticeModal = new bootstrap.Modal(formEl);
        if (viewEl && typeof bootstrap !== 'undefined') noticeViewModal = new bootstrap.Modal(viewEl);
        if (delEl && typeof bootstrap !== 'undefined') noticeDeleteModal = new bootstrap.Modal(delEl);

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

        const catFilter = document.getElementById('noticeCategoryFilter');
        if (catFilter) {
            catFilter.addEventListener('change', (e) => {
                state.category = e.target.value;
                state.page = 1;
                loadNotices();
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

        const deptFilter = document.getElementById('noticeDepartmentFilter');
        if (deptFilter) {
            deptFilter.addEventListener('change', (e) => {
                state.department = e.target.value;
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

        const btnGenId = document.getElementById('btnGenNoticeId');
        if (btnGenId) {
            btnGenId.addEventListener('click', () => {
                const rand = Math.floor(1000 + Math.random() * 9000);
                document.getElementById('noticeIdInput').value = `NOT_${rand}`;
            });
        }

        const createBtn = document.getElementById('openCreateNoticeModalBtn');
        if (createBtn) {
            createBtn.addEventListener('click', () => {
                document.getElementById('noticeModalTitle').innerText = 'Publish Campus Notice';
                document.getElementById('noticeFormRecordId').value = '';
                document.getElementById('noticeForm').reset();
                
                const idInput = document.getElementById('noticeIdInput');
                idInput.disabled = false;
                const rand = Math.floor(1000 + Math.random() * 9000);
                idInput.value = `NOT_${rand}`;

                // Default today's date
                const today = new Date().toISOString().split('T')[0];
                const dateInput = document.getElementById('noticeDateInput');
                if (dateInput) dateInput.value = today;

                const statusInput = document.getElementById('noticeStatusInput');
                if (statusInput) statusInput.value = 'Published';

                const urgentCheck = document.getElementById('noticeUrgentCheck');
                if (urgentCheck) urgentCheck.checked = false;

                state.uploadedDocData = null;
                resetCircularPreview();
                if (noticeModal) noticeModal.show();
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
            preview.innerHTML = '<span class="text-xs text-[#8B5CF6] flex items-center gap-1.5"><div class="w-3.5 h-3.5 border-2 border-[#8B5CF6] border-t-transparent rounded-full animate-spin"></div> Uploading document...</span>';
            preview.classList.remove('hidden');
        }

        try {
            const res = await fetch('/admin/api/upload', { method: 'POST', body: formData });
            const data = await res.json();
            if (res.ok && data.status === 'success') {
                state.uploadedDocData = data.file;
                if (preview) {
                    preview.innerHTML = `
                        <div class="flex items-center justify-between p-2.5 rounded-xl bg-emerald-50 border border-emerald-200 text-xs">
                            <div class="flex items-center gap-2 min-w-0">
                                <i data-lucide="file-text" class="w-4 h-4 text-emerald-600 flex-shrink-0"></i>
                                <span class="text-[#171D3A] font-semibold truncate">${escapeHtml(data.file.file_name || file.name)}</span>
                                <span class="text-[#66708F] text-[10px]">(${escapeHtml(data.file.file_size_formatted || '')})</span>
                            </div>
                            <button type="button" class="text-red-500 hover:text-red-700 ml-2" onclick="window.removeCircularDoc()">
                                <i data-lucide="x" class="w-4 h-4"></i>
                            </button>
                        </div>
                    `;
                    if (window.lucide) lucide.createIcons();
                }
                showAdminToast('Circular attachment uploaded.', 'success');
            } else {
                showAdminToast(data.message || 'File upload failed.', 'error');
                resetCircularPreview();
            }
        } catch (err) {
            showAdminToast(err.message || 'File upload failed.', 'error');
            resetCircularPreview();
        }
    }

    window.removeCircularDoc = function() {
        state.uploadedDocData = null;
        resetCircularPreview();
    };

    function resetCircularPreview() {
        const preview = document.getElementById('circularFilePreviewContainer');
        if (preview) {
            preview.innerHTML = '';
            preview.classList.add('hidden');
        }
        const fileInput = document.getElementById('circularFileInput');
        if (fileInput) fileInput.value = '';
    }

    async function loadNotices() {
        const tbody = document.getElementById('noticesTableBody');
        const mobileCards = document.getElementById('noticesMobileCards');
        if (!tbody) return;

        tbody.innerHTML = `
            <tr>
                <td colspan="9" class="text-center py-12 text-[#66708F] text-xs">
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
        if (state.category) params.append('filter_category', state.category);
        if (state.priority) params.append('filter_priority', state.priority);
        if (state.department) params.append('filter_department', state.department);
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
            showAdminToast(err.message || 'Error connecting to server.', 'error');
        }
        if (window.lucide) lucide.createIcons();
    }

    function renderPagination(totalPages) {
        const pagWrapper = document.getElementById('noticesPagination');
        if (!pagWrapper) return;

        if (totalPages <= 1 && state.total <= state.limit) {
            pagWrapper.classList.add('hidden');
            return;
        }

        pagWrapper.classList.remove('hidden');
        const start = state.total === 0 ? 0 : (state.page - 1) * state.limit + 1;
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
                btn.className = `px-2.5 py-1 rounded-xl text-xs font-semibold transition ${state.page === i ? 'bg-[#8B5CF6] text-white' : 'bg-white border border-[#E1E5F0] text-[#66708F] hover:text-[#171D3A]'}`;
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

        const emergency = state.items.find(n => {
            const p = (n.priority || '').toLowerCase();
            return p === 'emergency' || p === 'urgent' || n.is_urgent === true || n.is_urgent === 'true';
        });

        if (emergency) {
            ticker.innerHTML = `
                <div class="flex items-center justify-between gap-3 p-3.5 rounded-2xl bg-red-50 border border-red-200 text-[#171D3A] shadow-sm">
                    <div class="flex items-center gap-3 flex-wrap">
                        <span class="badge-emergency-pulse"><i data-lucide="alert-octagon" class="w-3.5 h-3.5"></i> ACTIVE ALERT</span>
                        <span class="text-xs font-bold text-[#171D3A]">${escapeHtml(emergency.title)}</span>
                        <span class="text-xs text-red-600">${escapeHtml(emergency.publish_date || 'Today')}</span>
                    </div>
                    <button class="px-3 py-1.5 rounded-xl bg-red-600 hover:bg-red-700 text-white text-xs font-semibold flex-shrink-0" onclick="window.viewNotice('${escapeQuotes(emergency.id || emergency.notice_id)}')">View</button>
                </div>
            `;
            ticker.classList.remove('hidden');
            if (window.lucide) lucide.createIcons();
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
                    <td colspan="9" class="text-center py-12 text-[#66708F] text-xs">
                        <i data-lucide="megaphone" class="w-8 h-8 mx-auto mb-2 text-[#8C95AD]"></i>
                        <p class="mb-0">No notices or announcements found.</p>
                    </td>
                </tr>
            `;
            if (mobileCards) mobileCards.innerHTML = '<div class="admin-mobile-empty">No notices found matching active filters.</div>';
            if (window.lucide) lucide.createIcons();
            return;
        }

        tbody.innerHTML = state.items.map(n => {
            const id = n.notice_id || n.id || '-';
            const title = n.title || 'Notice';
            const cat = n.category || 'General Updates';
            const dept = n.department || 'All Departments';
            const priority = (n.priority || 'Normal').toLowerCase();
            const target = n.target_audience || 'All Students & Faculty';
            const date = n.publish_date || '-';
            const status = (n.status || 'Published').toLowerCase();
            const fileUrl = n.file_url || n.attachment;
            const isUrgent = n.is_urgent === true || n.is_urgent === 'true' || priority === 'emergency' || priority === 'urgent';

            let badgeHtml = '';
            if (priority === 'emergency' || priority === 'urgent') {
                badgeHtml = '<span class="badge-emergency-pulse"><i data-lucide="alert-triangle" class="w-3 h-3"></i> EMERGENCY</span>';
            } else if (priority === 'high') {
                badgeHtml = '<span class="badge-priority-high">High</span>';
            } else if (priority === 'low') {
                badgeHtml = '<span class="badge-priority-low">Low</span>';
            } else {
                badgeHtml = '<span class="badge-priority-normal">Normal</span>';
            }

            let statusBadge = '';
            if (status === 'published') {
                statusBadge = '<span class="px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-50 text-emerald-700 border border-emerald-200">Published</span>';
            } else if (status === 'draft') {
                statusBadge = '<span class="px-2 py-0.5 rounded-full text-[10px] font-bold bg-amber-50 text-amber-700 border border-amber-200">Draft</span>';
            } else {
                statusBadge = '<span class="px-2 py-0.5 rounded-full text-[10px] font-bold bg-gray-100 text-gray-600 border border-gray-200">Archived</span>';
            }

            return `
                <tr>
                    <td>
                        <div class="flex items-center gap-2.5">
                            <div class="w-8 h-8 rounded-xl ${isUrgent ? 'bg-red-50 text-red-600 border border-red-200' : 'bg-[#E8EBFA] text-[#8B5CF6]'} flex items-center justify-center flex-shrink-0">
                                <i data-lucide="${isUrgent ? 'alert-octagon' : 'megaphone'}" class="w-4 h-4"></i>
                            </div>
                            <div class="min-w-0">
                                <p class="text-xs font-bold text-[#171D3A] mb-0 truncate max-w-xs" title="${escapeHtml(title)}">${escapeHtml(title)}</p>
                                <span class="text-[10px] text-[#66708F] font-mono">${escapeHtml(id)}</span>
                            </div>
                        </div>
                    </td>
                    <td class="text-[#171D3A] text-xs">${escapeHtml(cat)}</td>
                    <td class="text-[#66708F] text-xs">${escapeHtml(dept)}</td>
                    <td>${badgeHtml}</td>
                    <td class="text-[#66708F] text-xs">${escapeHtml(target)}</td>
                    <td class="text-[#66708F] text-xs">${escapeHtml(date)}</td>
                    <td>${statusBadge}</td>
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
                const cat = n.category || 'General Updates';
                const dept = n.department || 'All Departments';
                const priority = (n.priority || 'Normal').toLowerCase();
                const target = n.target_audience || 'All Students & Faculty';
                const date = n.publish_date || 'Recent';
                const fileUrl = n.file_url || n.attachment;
                const badge = (priority === 'emergency' || priority === 'urgent') ? 'badge-emergency-pulse' : priority === 'high' ? 'badge-priority-high' : priority === 'low' ? 'badge-priority-low' : 'badge-priority-normal';
                const priorityLabel = (priority === 'emergency' || priority === 'urgent') ? 'EMERGENCY' : priority.toUpperCase();

                return `
                    <article class="admin-mobile-record-card p-3 rounded-2xl bg-white border border-[#E1E5F0] shadow-sm mb-3">
                        <div class="flex items-center justify-between gap-2 mb-2">
                            <div class="flex items-center gap-2.5 min-w-0">
                                <div class="w-8 h-8 rounded-xl bg-[#E8EBFA] text-[#8B5CF6] flex items-center justify-center flex-shrink-0">
                                    <i data-lucide="megaphone" class="w-4 h-4"></i>
                                </div>
                                <div class="min-w-0">
                                    <h3 class="text-xs font-bold text-[#171D3A] mb-0 truncate">${escapeHtml(title)}</h3>
                                    <p class="text-[10px] text-[#66708F] font-mono mb-0">${escapeHtml(id)}</p>
                                </div>
                            </div>
                            <span class="${badge}">${priorityLabel}</span>
                        </div>
                        <div class="grid grid-cols-2 gap-2 text-[11px] text-[#66708F] my-2 p-2 rounded-xl bg-[#F8F9FE]">
                            <span><b>Category:</b> ${escapeHtml(cat)}</span>
                            <span><b>Dept:</b> ${escapeHtml(dept)}</span>
                            <span><b>Audience:</b> ${escapeHtml(target)}</span>
                            <span><b>Published:</b> ${escapeHtml(date)}</span>
                        </div>
                        <div class="flex items-center justify-end gap-2 pt-2 border-t border-[#E1E5F0]">
                            <button type="button" class="px-2.5 py-1 rounded-lg bg-white border border-[#E1E5F0] text-xs font-semibold text-[#171D3A]" onclick="window.viewNotice('${escapeQuotes(id)}')">
                                View
                            </button>
                            ${fileUrl ? `
                                <a href="${fileUrl}" target="_blank" class="px-2.5 py-1 rounded-lg bg-white border border-[#E1E5F0] text-xs font-semibold text-[#8B5CF6] flex items-center gap-1 text-decoration-none">
                                    <i data-lucide="paperclip" class="w-3 h-3"></i> File
                                </a>
                            ` : ''}
                            <button type="button" class="px-2.5 py-1 rounded-lg bg-[#E8EBFA] text-[#8B5CF6] text-xs font-semibold" onclick="window.editNotice('${escapeQuotes(id)}')">
                                Edit
                            </button>
                            <button type="button" class="p-1.5 rounded-lg text-red-600 hover:bg-red-50" onclick="window.deleteNotice('${escapeQuotes(id)}')">
                                <i data-lucide="trash-2" class="w-3.5 h-3.5"></i>
                            </button>
                        </div>
                    </article>
                `;
            }).join('');
        }

        if (window.lucide) lucide.createIcons();
    }

    async function handleNoticeFormSubmit(e) {
        e.preventDefault();
        const recordId = document.getElementById('noticeFormRecordId').value;
        const payload = {
            notice_id: document.getElementById('noticeIdInput').value.trim(),
            title: document.getElementById('noticeTitleInput').value.trim(),
            category: document.getElementById('noticeCategoryInput').value,
            priority: document.getElementById('noticePriorityInput').value,
            department: document.getElementById('noticeDeptInput').value,
            target_audience: document.getElementById('noticeTargetInput').value,
            publish_date: document.getElementById('noticeDateInput').value,
            expiry_date: document.getElementById('noticeExpiryInput').value || '',
            status: document.getElementById('noticeStatusInput').value,
            is_urgent: document.getElementById('noticeUrgentCheck').checked,
            description: document.getElementById('noticeDescInput').value.trim()
        };

        if (state.uploadedDocData) {
            payload.file_url = state.uploadedDocData.url || state.uploadedDocData.file_url;
            payload.attachment = payload.file_url;
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
                showAdminToast(data.message || 'Notice saved successfully.', 'success');
                if (noticeModal) noticeModal.hide();
                loadNotices();
            } else {
                showAdminToast(data.message || 'Error saving notice.', 'error');
            }
        } catch (err) {
            showAdminToast(err.message || 'Error saving notice.', 'error');
        }
    }

    window.editNotice = function(id) {
        const item = state.items.find(n => (n.notice_id || n.id) === id);
        if (!item) return;

        document.getElementById('noticeModalTitle').innerText = 'Edit Campus Notice';
        document.getElementById('noticeFormRecordId').value = id;
        
        const idInput = document.getElementById('noticeIdInput');
        idInput.value = item.notice_id || id;
        idInput.disabled = true;

        document.getElementById('noticeTitleInput').value = item.title || '';
        document.getElementById('noticeCategoryInput').value = item.category || 'General Updates';
        document.getElementById('noticePriorityInput').value = item.priority || 'Normal';
        document.getElementById('noticeDeptInput').value = item.department || 'All Departments';
        document.getElementById('noticeTargetInput').value = item.target_audience || 'All Students & Faculty';
        document.getElementById('noticeDateInput').value = item.publish_date || '';
        document.getElementById('noticeExpiryInput').value = item.expiry_date || '';
        document.getElementById('noticeStatusInput').value = item.status || 'Published';
        document.getElementById('noticeUrgentCheck').checked = Boolean(item.is_urgent === true || item.is_urgent === 'true' || item.priority === 'Emergency' || item.priority === 'Urgent');
        document.getElementById('noticeDescInput').value = item.description || '';

        const existingFile = item.file_url || item.attachment;
        if (existingFile) {
            state.uploadedDocData = { file_url: existingFile, file_name: 'Attached Circular File' };
            const preview = document.getElementById('circularFilePreviewContainer');
            if (preview) {
                preview.innerHTML = `
                    <div class="flex items-center justify-between p-2.5 rounded-xl bg-emerald-50 border border-emerald-200 text-xs">
                        <div class="flex items-center gap-2 min-w-0">
                            <i data-lucide="file-text" class="w-4 h-4 text-emerald-600 flex-shrink-0"></i>
                            <span class="text-[#171D3A] font-semibold truncate">Current Attachment</span>
                        </div>
                        <button type="button" class="text-red-500 hover:text-red-700 ml-2" onclick="window.removeCircularDoc()">
                            <i data-lucide="x" class="w-4 h-4"></i>
                        </button>
                    </div>
                `;
                preview.classList.remove('hidden');
                if (window.lucide) lucide.createIcons();
            }
        } else {
            state.uploadedDocData = null;
            resetCircularPreview();
        }

        if (noticeModal) noticeModal.show();
    };

    window.viewNotice = function(id) {
        const item = state.items.find(n => (n.notice_id || n.id) === id);
        if (!item) return;

        const container = document.getElementById('noticeViewContent');
        if (!container) return;

        const fileUrl = item.file_url || item.attachment;
        const priority = item.priority || 'Normal';
        const isUrgent = item.is_urgent === true || item.is_urgent === 'true';

        container.innerHTML = `
            <div class="space-y-4">
                <div class="flex items-center justify-between flex-wrap gap-2">
                    <div class="flex items-center gap-2">
                        <span class="px-2.5 py-1 rounded-full text-xs font-bold bg-[#E8EBFA] text-[#8B5CF6]">${escapeHtml(item.category || 'Circular')}</span>
                        <span class="px-2 py-0.5 rounded-full text-xs font-semibold ${priority.toLowerCase() === 'emergency' || priority.toLowerCase() === 'urgent' ? 'bg-red-100 text-red-700' : 'bg-blue-50 text-blue-700'}">${escapeHtml(priority)} Priority</span>
                        ${isUrgent ? '<span class="px-2 py-0.5 rounded-full text-xs font-bold bg-red-600 text-white">URGENT ALERT</span>' : ''}
                    </div>
                    <span class="text-xs text-[#66708F]">${escapeHtml(item.publish_date || 'Today')}</span>
                </div>

                <div>
                    <h3 class="text-base font-bold text-[#171D3A] mb-1">${escapeHtml(item.title)}</h3>
                    <p class="text-xs text-[#66708F] font-mono mb-0">ID: ${escapeHtml(item.notice_id || id)}</p>
                </div>

                <div class="grid grid-cols-2 sm:grid-cols-3 gap-3 p-3 rounded-xl bg-[#F8F9FE] border border-[#E1E5F0] text-xs">
                    <div>
                        <span class="text-[#66708F] block text-[10px] uppercase font-semibold">Department</span>
                        <span class="text-[#171D3A] font-semibold">${escapeHtml(item.department || 'All Departments')}</span>
                    </div>
                    <div>
                        <span class="text-[#66708F] block text-[10px] uppercase font-semibold">Audience</span>
                        <span class="text-[#171D3A] font-semibold">${escapeHtml(item.target_audience || 'All Students & Faculty')}</span>
                    </div>
                    <div>
                        <span class="text-[#66708F] block text-[10px] uppercase font-semibold">Status</span>
                        <span class="text-[#171D3A] font-semibold">${escapeHtml(item.status || 'Published')}</span>
                    </div>
                </div>

                <div class="p-3.5 rounded-xl bg-white border border-[#E1E5F0] text-xs text-[#171D3A] leading-relaxed">
                    <span class="text-[#66708F] block text-[10px] uppercase font-semibold mb-1.5">Announcement Details</span>
                    ${escapeHtml(item.description || 'No detailed content provided.').replace(/\n/g, '<br>')}
                </div>

                ${fileUrl ? `
                    <div class="pt-2 flex justify-between items-center">
                        <a href="${fileUrl}" target="_blank" class="btn-primary-custom text-xs inline-flex items-center gap-2 text-decoration-none">
                            <i data-lucide="download" class="w-4 h-4"></i> Download / View Circular Document
                        </a>
                    </div>
                ` : ''}
            </div>
        `;

        if (window.lucide) lucide.createIcons();
        if (noticeViewModal) noticeViewModal.show();
    };

    window.deleteNotice = function(id) {
        state.pendingDeleteId = id;
        const targetEl = document.getElementById('deleteNoticeTargetId');
        if (targetEl) targetEl.innerText = id;
        if (noticeDeleteModal) noticeDeleteModal.show();
    };

    async function handleConfirmDelete() {
        if (!state.pendingDeleteId) return;

        try {
            const res = await fetch(`/admin/api/crud/notices/${state.pendingDeleteId}`, { method: 'DELETE' });
            const data = await res.json();
            if (res.ok && data.status === 'success') {
                showAdminToast(data.message || 'Notice deleted successfully.', 'success');
                if (noticeDeleteModal) noticeDeleteModal.hide();
                loadNotices();
            } else {
                showAdminToast(data.message || 'Failed to delete notice.', 'error');
            }
        } catch (err) {
            showAdminToast(err.message || 'Failed to delete notice.', 'error');
        }
    }
})();
