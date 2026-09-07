/**
 * SVIT Admin - College Events Controller
 * Cultural fests, tech hackathons, workshops, and symposiums.
 * Supports poster upload, grid/table view modes, category/department/status filtering, full CRUD.
 */

(function() {
    'use strict';

    const state = {
        search: '',
        category: '',
        department: '',
        status: '',
        viewMode: 'table', // 'table' or 'grid'
        page: 1,
        limit: 20,
        total: 0,
        items: [],
        pendingDeleteId: null,
        uploadedBannerUrl: null
    };

    let eventModal = null;
    let eventViewModal = null;
    let eventDeleteModal = null;
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
        const formEl = document.getElementById('eventFormModal');
        const viewEl = document.getElementById('eventViewModal');
        const delEl = document.getElementById('eventDeleteModal');

        if (formEl && typeof bootstrap !== 'undefined') eventModal = new bootstrap.Modal(formEl);
        if (viewEl && typeof bootstrap !== 'undefined') eventViewModal = new bootstrap.Modal(viewEl);
        if (delEl && typeof bootstrap !== 'undefined') eventDeleteModal = new bootstrap.Modal(delEl);

        bindEvents();
        setupPosterUpload();
        loadEvents();
    });

    function bindEvents() {
        const searchInput = document.getElementById('eventSearchInput');
        if (searchInput) {
            searchInput.addEventListener('input', (e) => {
                clearTimeout(searchDebounce);
                searchDebounce = setTimeout(() => {
                    state.search = e.target.value.trim();
                    state.page = 1;
                    loadEvents();
                }, 300);
            });
        }

        const catFilter = document.getElementById('eventCategoryFilter');
        if (catFilter) {
            catFilter.addEventListener('change', (e) => {
                state.category = e.target.value;
                state.page = 1;
                loadEvents();
            });
        }

        const deptFilter = document.getElementById('eventDepartmentFilter');
        if (deptFilter) {
            deptFilter.addEventListener('change', (e) => {
                state.department = e.target.value;
                state.page = 1;
                loadEvents();
            });
        }

        const statusFilter = document.getElementById('eventStatusFilter');
        if (statusFilter) {
            statusFilter.addEventListener('change', (e) => {
                state.status = e.target.value;
                state.page = 1;
                loadEvents();
            });
        }

        const refreshBtn = document.getElementById('refreshEventsBtn');
        if (refreshBtn) refreshBtn.addEventListener('click', loadEvents);

        const limitSelect = document.getElementById('pageLimitSelect');
        if (limitSelect) {
            limitSelect.addEventListener('change', (e) => {
                state.limit = parseInt(e.target.value, 10) || 20;
                state.page = 1;
                loadEvents();
            });
        }

        const prevBtn = document.getElementById('prevPageBtn');
        if (prevBtn) {
            prevBtn.addEventListener('click', () => {
                if (state.page > 1) {
                    state.page--;
                    loadEvents();
                }
            });
        }

        const nextBtn = document.getElementById('nextPageBtn');
        if (nextBtn) {
            nextBtn.addEventListener('click', () => {
                const totalPages = Math.ceil(state.total / state.limit) || 1;
                if (state.page < totalPages) {
                    state.page++;
                    loadEvents();
                }
            });
        }

        const btnGenId = document.getElementById('btnGenEventId');
        if (btnGenId) {
            btnGenId.addEventListener('click', () => {
                const rand = Math.floor(1000 + Math.random() * 9000);
                document.getElementById('eventIdInput').value = `EVT_${rand}`;
            });
        }

        const createBtn = document.getElementById('openCreateEventModalBtn');
        if (createBtn) {
            createBtn.addEventListener('click', () => {
                document.getElementById('eventModalTitle').innerText = 'Add College Event';
                document.getElementById('eventFormRecordId').value = '';
                document.getElementById('eventForm').reset();
                
                const idInput = document.getElementById('eventIdInput');
                idInput.disabled = false;
                const rand = Math.floor(1000 + Math.random() * 9000);
                idInput.value = `EVT_${rand}`;

                const today = new Date().toISOString().split('T')[0];
                const dateInput = document.getElementById('eventStartDateInput');
                if (dateInput) dateInput.value = today;

                const deptInput = document.getElementById('eventDepartmentInput');
                if (deptInput) deptInput.value = 'All Departments';

                const statusInput = document.getElementById('eventStatusInput');
                if (statusInput) statusInput.value = 'Upcoming';

                const regReq = document.getElementById('eventRegRequiredInput');
                if (regReq) regReq.value = 'No';

                state.uploadedBannerUrl = null;
                resetPosterPreview();
                if (eventModal) eventModal.show();
            });
        }

        const form = document.getElementById('eventForm');
        if (form) form.addEventListener('submit', handleEventFormSubmit);

        const confirmDeleteBtn = document.getElementById('confirmDeleteEventBtn');
        if (confirmDeleteBtn) confirmDeleteBtn.addEventListener('click', handleConfirmDelete);

        // View toggle
        const toggleTableBtn = document.getElementById('viewTableToggleBtn');
        const toggleGridBtn = document.getElementById('viewGridToggleBtn');

        if (toggleTableBtn && toggleGridBtn) {
            toggleTableBtn.addEventListener('click', () => {
                state.viewMode = 'table';
                toggleTableBtn.classList.add('bg-pink-600', 'text-white');
                toggleTableBtn.classList.remove('text-[#66708F]');
                toggleGridBtn.classList.remove('bg-pink-600', 'text-white');
                toggleGridBtn.classList.add('text-[#66708F]');
                document.getElementById('eventsTableView').classList.remove('hidden');
                document.getElementById('eventsGridView').classList.add('hidden');
                renderEvents();
            });
            toggleGridBtn.addEventListener('click', () => {
                state.viewMode = 'grid';
                toggleGridBtn.classList.add('bg-pink-600', 'text-white');
                toggleGridBtn.classList.remove('text-[#66708F]');
                toggleTableBtn.classList.remove('bg-pink-600', 'text-white');
                toggleTableBtn.classList.add('text-[#66708F]');
                document.getElementById('eventsGridView').classList.remove('hidden');
                document.getElementById('eventsTableView').classList.add('hidden');
                renderEvents();
            });
        }
    }

    function setupPosterUpload() {
        const dropZone = document.getElementById('eventPosterDropZone');
        const fileInput = document.getElementById('eventPosterInput');

        if (dropZone && fileInput) {
            dropZone.addEventListener('click', () => fileInput.click());
            dropZone.addEventListener('dragover', (e) => { e.preventDefault(); dropZone.classList.add('border-pink-500'); });
            dropZone.addEventListener('dragleave', () => dropZone.classList.remove('border-pink-500'));
            dropZone.addEventListener('drop', (e) => {
                e.preventDefault();
                dropZone.classList.remove('border-pink-500');
                if (e.dataTransfer.files.length) uploadPosterImage(e.dataTransfer.files[0]);
            });
            fileInput.addEventListener('change', (e) => {
                if (e.target.files.length) uploadPosterImage(e.target.files[0]);
            });
        }
    }

    async function uploadPosterImage(file) {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('category', 'image');

        const preview = document.getElementById('eventPosterPreviewContainer');
        if (preview) {
            preview.innerHTML = '<span class="text-xs text-pink-600 flex items-center gap-1.5"><div class="w-3.5 h-3.5 border-2 border-pink-600 border-t-transparent rounded-full animate-spin"></div> Uploading poster...</span>';
            preview.classList.remove('hidden');
        }

        try {
            const res = await fetch('/admin/api/upload', { method: 'POST', body: formData });
            const data = await res.json();
            if (res.ok && data.status === 'success') {
                const url = data.file.url || data.file.file_url;
                state.uploadedBannerUrl = url;
                if (preview) {
                    preview.innerHTML = `
                        <div class="flex items-center gap-2 p-2 rounded-xl bg-pink-50 border border-pink-200">
                            <img src="${url}" class="w-12 h-12 rounded-lg object-cover border border-pink-300">
                            <span class="text-xs font-semibold text-[#171D3A]">Poster Uploaded</span>
                            <button type="button" class="text-red-500 hover:text-red-700 ml-auto p-1" onclick="window.removeEventPoster()">
                                <i data-lucide="x" class="w-4 h-4"></i>
                            </button>
                        </div>
                    `;
                    if (window.lucide) lucide.createIcons();
                }
                showAdminToast('Event banner uploaded.', 'success');
            } else {
                showAdminToast(data.message || 'Image upload failed.', 'error');
                resetPosterPreview();
            }
        } catch (err) {
            showAdminToast(err.message || 'Image upload failed.', 'error');
            resetPosterPreview();
        }
    }

    window.removeEventPoster = function() {
        state.uploadedBannerUrl = null;
        resetPosterPreview();
    };

    function resetPosterPreview() {
        const preview = document.getElementById('eventPosterPreviewContainer');
        if (preview) {
            preview.innerHTML = '';
            preview.classList.add('hidden');
        }
        const fileInput = document.getElementById('eventPosterInput');
        if (fileInput) fileInput.value = '';
    }

    async function loadEvents() {
        const tbody = document.getElementById('eventsTableBody');
        const grid = document.getElementById('eventsGridContainer');
        const mobileCards = document.getElementById('eventsMobileCards');

        if (tbody) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="9" class="text-center py-12 text-[#66708F] text-xs">
                        <div class="inline-block animate-spin rounded-full h-5 w-5 border-2 border-pink-500 border-t-transparent mb-2"></div>
                        <p class="mb-0">Loading college events...</p>
                    </td>
                </tr>
            `;
        }
        if (grid) grid.innerHTML = '<div class="col-span-full text-center py-10 text-[#66708F] text-xs">Loading events...</div>';
        if (mobileCards) mobileCards.innerHTML = '<div class="admin-mobile-empty">Loading events...</div>';

        const params = new URLSearchParams({
            page: state.page,
            limit: state.limit
        });
        if (state.search) params.append('search', state.search);
        if (state.category) params.append('filter_category', state.category);
        if (state.department) params.append('filter_department', state.department);
        if (state.status) params.append('filter_status', state.status);

        try {
            const res = await fetch(`/admin/api/crud/events?${params.toString()}`);
            const data = await res.json();
            if (res.ok && (data.status === 'success' || Array.isArray(data.items))) {
                state.items = Array.isArray(data.items)
                    ? data.items
                    : (Array.isArray(data?.data?.items) ? data.data.items : (Array.isArray(data?.data) ? data.data : []));
                state.total = typeof data.total === 'number'
                    ? data.total
                    : (typeof data?.data?.total === 'number' ? data.data.total : state.items.length);
                renderEvents();
                renderPagination(data.pages || data?.data?.pages || 1);
            } else {
                showAdminToast(data.message || 'Failed to load events.', 'error');
            }
        } catch (err) {
            showAdminToast(err.message || 'Error connecting to server.', 'error');
        }
        if (window.lucide) lucide.createIcons();
    }

    function renderPagination(totalPages) {
        const pagWrapper = document.getElementById('eventsPagination');
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
                    loadEvents();
                }
            };
        }

        if (nextBtn) {
            nextBtn.disabled = state.page >= totalPages;
            nextBtn.onclick = () => {
                if (state.page < totalPages) {
                    state.page++;
                    loadEvents();
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
                btn.className = `px-2.5 py-1 rounded-xl text-xs font-semibold transition ${state.page === i ? 'bg-pink-600 text-white' : 'bg-white border border-[#E1E5F0] text-[#66708F] hover:text-[#171D3A]'}`;
                btn.onclick = () => {
                    state.page = i;
                    loadEvents();
                };
                numbersContainer.appendChild(btn);
            }
        }
    }

    function renderEvents() {
        const countBadge = document.getElementById('eventsCountBadge');
        if (countBadge) countBadge.innerText = `${state.total} Events`;

        if (state.viewMode === 'table') {
            renderTableView();
        } else {
            renderGridView();
        }
        if (window.lucide) lucide.createIcons();
    }

    function renderTableView() {
        const tbody = document.getElementById('eventsTableBody');
        const mobileCards = document.getElementById('eventsMobileCards');
        if (!tbody) return;

        if (state.items.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="9" class="text-center py-12 text-[#66708F] text-xs">
                        <i data-lucide="party-popper" class="w-8 h-8 mx-auto mb-2 text-[#8C95AD]"></i>
                        <p class="mb-0">No college events found matching filters.</p>
                    </td>
                </tr>
            `;
            if (mobileCards) mobileCards.innerHTML = '<div class="admin-mobile-empty">No events found.</div>';
            return;
        }

        tbody.innerHTML = state.items.map(e => {
            const id = e.event_id || e.id || '-';
            const title = e.event_name || e.title || 'College Event';
            const cat = e.category || 'Cultural';
            const dept = e.department || 'All Departments';
            const dates = e.event_date || e.start_date || 'Upcoming';
            const time = e.start_time ? ` (${e.start_time})` : '';
            const venue = e.venue || 'SVIT Auditorium';
            const organizer = e.organizer || 'College Committee';
            const status = e.status || 'Upcoming';
            const poster = e.image_url || e.banner_url;
            const regReq = (e.registration_required || 'No').toLowerCase() === 'yes';

            let statusBadge = '';
            if (status.toLowerCase() === 'upcoming') {
                statusBadge = '<span class="px-2 py-0.5 rounded-full text-[10px] font-bold bg-blue-50 text-blue-700 border border-blue-200">Upcoming</span>';
            } else if (status.toLowerCase() === 'ongoing' || status.toLowerCase() === 'live') {
                statusBadge = '<span class="px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-50 text-emerald-700 border border-emerald-200">Live</span>';
            } else if (status.toLowerCase() === 'completed') {
                statusBadge = '<span class="px-2 py-0.5 rounded-full text-[10px] font-bold bg-gray-100 text-gray-600 border border-gray-200">Completed</span>';
            } else {
                statusBadge = `<span class="px-2 py-0.5 rounded-full text-[10px] font-bold bg-amber-50 text-amber-700 border border-amber-200">${escapeHtml(status)}</span>`;
            }

            return `
                <tr>
                    <td>
                        <div class="flex items-center gap-2.5">
                            <div class="event-banner-box flex-shrink-0">
                                ${poster ? `<img src="${poster}" alt="${escapeQuotes(title)}" class="w-full h-full object-cover rounded-lg">` : '<i data-lucide="sparkles" class="w-4 h-4 text-pink-500"></i>'}
                            </div>
                            <div class="min-w-0">
                                <p class="text-xs font-bold text-[#171D3A] mb-0 truncate max-w-xs" title="${escapeHtml(title)}">${escapeHtml(title)}</p>
                                <span class="text-[10px] text-pink-600 font-mono">${escapeHtml(id)}</span>
                            </div>
                        </div>
                    </td>
                    <td><span class="badge-event-cat">${escapeHtml(cat)}</span></td>
                    <td class="text-[#66708F] text-xs">${escapeHtml(dept)}</td>
                    <td class="text-[#171D3A] text-xs font-medium">${escapeHtml(dates)}${escapeHtml(time)}</td>
                    <td class="text-[#66708F] text-xs">${escapeHtml(venue)}</td>
                    <td class="text-[#66708F] text-xs">${escapeHtml(organizer)}</td>
                    <td>
                        ${regReq ? `
                            ${e.registration_link ? `
                                <a href="${e.registration_link}" target="_blank" class="text-indigo-600 hover:underline text-xs font-semibold flex items-center gap-1 text-decoration-none">
                                    <i data-lucide="link" class="w-3 h-3"></i> Register
                                </a>
                            ` : '<span class="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-indigo-50 text-indigo-700 border border-indigo-200">Required</span>'}
                        ` : '<span class="text-[#8C95AD] text-xs">Open Access</span>'}
                    </td>
                    <td>${statusBadge}</td>
                    <td class="text-end">
                        <div class="inline-flex items-center gap-1.5">
                            <button class="p-1.5 rounded-lg bg-white border border-[#E1E5F0] text-[#171D3A] hover:bg-pink-50" onclick="window.viewEvent('${escapeQuotes(id)}')" title="View Event">
                                <i data-lucide="eye" class="w-3.5 h-3.5"></i>
                            </button>
                            <button class="p-1.5 rounded-lg bg-white border border-[#E1E5F0] text-pink-600 hover:bg-pink-50" onclick="window.editEvent('${escapeQuotes(id)}')" title="Edit Event">
                                <i data-lucide="edit-2" class="w-3.5 h-3.5"></i>
                            </button>
                            <button class="p-1.5 rounded-lg bg-white border border-[#E1E5F0] text-red-600 hover:bg-red-50" onclick="window.deleteEvent('${escapeQuotes(id)}')" title="Delete Event">
                                <i data-lucide="trash-2" class="w-3.5 h-3.5"></i>
                            </button>
                        </div>
                    </td>
                </tr>
            `;
        }).join('');

        if (mobileCards) {
            mobileCards.innerHTML = state.items.map(e => {
                const id = e.event_id || e.id || '-';
                const title = e.event_name || e.title || 'College Event';
                const cat = e.category || 'Cultural';
                const dept = e.department || 'All Departments';
                const dates = e.event_date || e.start_date || 'Upcoming';
                const venue = e.venue || 'SVIT Auditorium';
                const status = e.status || 'Upcoming';
                const poster = e.image_url || e.banner_url;

                return `
                    <article class="p-3 rounded-2xl bg-white border border-[#E1E5F0] shadow-sm mb-3">
                        <div class="flex items-center justify-between gap-2 mb-2">
                            <div class="flex items-center gap-2.5 min-w-0">
                                <div class="w-8 h-8 rounded-xl bg-pink-50 text-pink-600 flex items-center justify-center flex-shrink-0">
                                    <i data-lucide="party-popper" class="w-4 h-4"></i>
                                </div>
                                <div class="min-w-0">
                                    <h3 class="text-xs font-bold text-[#171D3A] mb-0 truncate">${escapeHtml(title)}</h3>
                                    <p class="text-[10px] text-pink-600 font-mono mb-0">${escapeHtml(id)}</p>
                                </div>
                            </div>
                            <span class="badge-event-cat">${escapeHtml(cat)}</span>
                        </div>
                        <div class="grid grid-cols-2 gap-2 text-[11px] text-[#66708F] my-2 p-2 rounded-xl bg-[#F8F9FE]">
                            <span><b>Dates:</b> ${escapeHtml(dates)}</span>
                            <span><b>Venue:</b> ${escapeHtml(venue)}</span>
                            <span><b>Dept:</b> ${escapeHtml(dept)}</span>
                            <span><b>Status:</b> ${escapeHtml(status)}</span>
                        </div>
                        <div class="flex items-center justify-end gap-2 pt-2 border-t border-[#E1E5F0]">
                            <button type="button" class="px-2.5 py-1 rounded-lg bg-white border border-[#E1E5F0] text-xs font-semibold text-[#171D3A]" onclick="window.viewEvent('${escapeQuotes(id)}')">
                                View
                            </button>
                            <button type="button" class="px-2.5 py-1 rounded-lg bg-pink-50 text-pink-600 text-xs font-semibold border border-pink-200" onclick="window.editEvent('${escapeQuotes(id)}')">
                                Edit
                            </button>
                            <button type="button" class="p-1.5 rounded-lg text-red-600 hover:bg-red-50" onclick="window.deleteEvent('${escapeQuotes(id)}')">
                                <i data-lucide="trash-2" class="w-3.5 h-3.5"></i>
                            </button>
                        </div>
                    </article>
                `;
            }).join('');
        }
    }

    function renderGridView() {
        const grid = document.getElementById('eventsGridContainer');
        if (!grid) return;

        if (state.items.length === 0) {
            grid.innerHTML = `<div class="col-span-full text-center py-10 text-[#66708F] text-xs">No college events found.</div>`;
            return;
        }

        grid.innerHTML = state.items.map(e => {
            const id = e.event_id || e.id || '-';
            const title = e.event_name || e.title || 'College Event';
            const cat = e.category || 'Cultural';
            const dept = e.department || 'All Departments';
            const dates = e.event_date || e.start_date || 'Upcoming';
            const venue = e.venue || 'SVIT Auditorium';
            const organizer = e.organizer || 'College Committee';
            const status = e.status || 'Upcoming';
            const poster = e.image_url || e.banner_url;

            return `
                <div class="event-card-box rounded-2xl bg-white border border-[#E1E5F0] overflow-hidden shadow-sm hover:shadow-md transition">
                    <div class="h-36 bg-[#F8F9FE] relative flex items-center justify-center overflow-hidden border-b border-[#E1E5F0]">
                        ${poster ? `<img src="${poster}" class="w-full h-full object-cover">` : '<i data-lucide="party-popper" class="w-10 h-10 text-pink-400 opacity-60"></i>'}
                        <span class="badge-event-cat absolute top-3 right-3 shadow-sm">${escapeHtml(cat)}</span>
                        <span class="px-2 py-0.5 rounded-full text-[10px] font-bold bg-white/90 backdrop-blur-sm text-[#171D3A] border border-[#E1E5F0] absolute bottom-3 left-3">${escapeHtml(id)}</span>
                    </div>
                    <div class="p-4 space-y-2.5">
                        <h4 class="text-sm font-bold text-[#171D3A] mb-0 truncate" title="${escapeHtml(title)}">${escapeHtml(title)}</h4>
                        <div class="space-y-1 text-xs text-[#66708F]">
                            <p class="mb-0 flex items-center gap-1.5"><i data-lucide="calendar" class="w-3.5 h-3.5 text-pink-600"></i> ${escapeHtml(dates)}</p>
                            <p class="mb-0 flex items-center gap-1.5"><i data-lucide="map-pin" class="w-3.5 h-3.5 text-emerald-600"></i> ${escapeHtml(venue)}</p>
                            <p class="mb-0 flex items-center gap-1.5"><i data-lucide="building" class="w-3.5 h-3.5 text-[#8B5CF6]"></i> ${escapeHtml(dept)}</p>
                            <p class="mb-0 flex items-center gap-1.5"><i data-lucide="user-check" class="w-3.5 h-3.5 text-amber-600"></i> ${escapeHtml(organizer)}</p>
                        </div>
                        <div class="pt-3 flex items-center justify-between border-t border-[#E1E5F0]">
                            <span class="text-xs font-semibold text-pink-600">${escapeHtml(status)}</span>
                            <div class="flex items-center gap-1.5">
                                <button class="px-2.5 py-1 rounded-lg bg-white border border-[#E1E5F0] text-[#171D3A] text-xs hover:bg-[#F8F9FE]" onclick="window.viewEvent('${escapeQuotes(id)}')">Details</button>
                                <button class="px-2.5 py-1 rounded-lg bg-pink-600 hover:bg-pink-700 text-white text-xs font-semibold" onclick="window.editEvent('${escapeQuotes(id)}')">Edit</button>
                                <button class="p-1 rounded-lg text-red-600 hover:bg-red-50" onclick="window.deleteEvent('${escapeQuotes(id)}')">
                                    <i data-lucide="trash-2" class="w-3.5 h-3.5"></i>
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            `;
        }).join('');
    }

    async function handleEventFormSubmit(e) {
        e.preventDefault();
        const recordId = document.getElementById('eventFormRecordId').value;
        const payload = {
            event_id: document.getElementById('eventIdInput').value.trim(),
            event_name: document.getElementById('eventNameInput').value.trim(),
            category: document.getElementById('eventCategoryInput').value,
            department: document.getElementById('eventDepartmentInput').value,
            organizer: document.getElementById('eventOrganizerInput').value.trim(),
            event_date: document.getElementById('eventStartDateInput').value,
            start_date: document.getElementById('eventStartDateInput').value,
            end_date: document.getElementById('eventEndDateInput').value || '',
            start_time: document.getElementById('eventStartTimeInput').value || '',
            end_time: document.getElementById('eventEndTimeInput').value || '',
            venue: document.getElementById('eventVenueInput').value.trim(),
            speaker_or_guest: document.getElementById('eventSpeakerInput').value.trim(),
            registration_required: document.getElementById('eventRegRequiredInput').value,
            registration_link: document.getElementById('eventRegLinkInput').value.trim(),
            capacity: document.getElementById('eventCapacityInput').value ? parseInt(document.getElementById('eventCapacityInput').value, 10) : 0,
            status: document.getElementById('eventStatusInput').value,
            description: document.getElementById('eventDescInput').value.trim()
        };

        if (state.uploadedBannerUrl) {
            payload.banner_url = state.uploadedBannerUrl;
            payload.image_url = state.uploadedBannerUrl;
        }

        const isEdit = Boolean(recordId);
        const url = isEdit ? `/admin/api/crud/events/${recordId}` : '/admin/api/crud/events';
        const method = isEdit ? 'PUT' : 'POST';

        try {
            const res = await fetch(url, {
                method: method,
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            const data = await res.json();
            if (res.ok && data.status === 'success') {
                showAdminToast(data.message || 'Event saved successfully.', 'success');
                if (eventModal) eventModal.hide();
                loadEvents();
            } else {
                showAdminToast(data.message || 'Error saving event.', 'error');
            }
        } catch (err) {
            showAdminToast(err.message || 'Error saving event.', 'error');
        }
    }

    window.editEvent = function(id) {
        const item = state.items.find(e => (e.event_id || e.id) === id);
        if (!item) return;

        document.getElementById('eventModalTitle').innerText = 'Edit College Event';
        document.getElementById('eventFormRecordId').value = id;
        
        const idInput = document.getElementById('eventIdInput');
        idInput.value = item.event_id || id;
        idInput.disabled = true;

        document.getElementById('eventNameInput').value = item.event_name || item.title || '';
        document.getElementById('eventCategoryInput').value = item.category || 'Technical Events';
        document.getElementById('eventDepartmentInput').value = item.department || 'All Departments';
        document.getElementById('eventOrganizerInput').value = item.organizer || 'College Committee';
        document.getElementById('eventStartDateInput').value = item.event_date || item.start_date || '';
        document.getElementById('eventEndDateInput').value = item.end_date || '';
        document.getElementById('eventStartTimeInput').value = item.start_time || '';
        document.getElementById('eventEndTimeInput').value = item.end_time || '';
        document.getElementById('eventVenueInput').value = item.venue || 'SVIT Auditorium';
        document.getElementById('eventSpeakerInput').value = item.speaker_or_guest || '';
        document.getElementById('eventRegRequiredInput').value = item.registration_required || 'No';
        document.getElementById('eventRegLinkInput').value = item.registration_link || '';
        document.getElementById('eventCapacityInput').value = item.capacity || '';
        document.getElementById('eventStatusInput').value = item.status || 'Upcoming';
        document.getElementById('eventDescInput').value = item.description || '';

        state.uploadedBannerUrl = item.banner_url || item.image_url || null;
        if (state.uploadedBannerUrl) {
            const preview = document.getElementById('eventPosterPreviewContainer');
            if (preview) {
                preview.innerHTML = `
                    <div class="flex items-center gap-2 p-2 rounded-xl bg-pink-50 border border-pink-200">
                        <img src="${state.uploadedBannerUrl}" class="w-12 h-12 rounded-lg object-cover border border-pink-300">
                        <span class="text-xs font-semibold text-[#171D3A]">Current Poster</span>
                        <button type="button" class="text-red-500 hover:text-red-700 ml-auto p-1" onclick="window.removeEventPoster()">
                            <i data-lucide="x" class="w-4 h-4"></i>
                        </button>
                    </div>
                `;
                preview.classList.remove('hidden');
                if (window.lucide) lucide.createIcons();
            }
        } else {
            resetPosterPreview();
        }

        if (eventModal) eventModal.show();
    };

    window.viewEvent = function(id) {
        const item = state.items.find(e => (e.event_id || e.id) === id);
        if (!item) return;

        const container = document.getElementById('eventViewContent');
        if (!container) return;

        const poster = item.banner_url || item.image_url;
        const regReq = (item.registration_required || 'No').toLowerCase() === 'yes';

        container.innerHTML = `
            <div class="space-y-4">
                <div class="flex items-center gap-3.5 p-4 rounded-2xl bg-[#F8F9FE] border border-[#E1E5F0]">
                    <div class="w-16 h-16 rounded-2xl bg-pink-50 text-pink-600 font-bold text-lg flex items-center justify-center overflow-hidden flex-shrink-0 border border-pink-200">
                        ${poster ? `<img src="${poster}" class="w-full h-full object-cover">` : '<i data-lucide="party-popper" class="w-7 h-7"></i>'}
                    </div>
                    <div class="min-w-0">
                        <span class="badge-event-cat">${escapeHtml(item.category || 'Cultural Events')}</span>
                        <h3 class="text-base font-bold text-[#171D3A] mt-1 mb-0">${escapeHtml(item.event_name || item.title)}</h3>
                        <p class="text-xs text-pink-600 font-mono mb-0">${escapeHtml(item.event_id || id)}</p>
                    </div>
                </div>

                <div class="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
                    <div class="p-2.5 rounded-xl bg-[#F8F9FE] border border-[#E1E5F0]">
                        <span class="text-[#66708F] block text-[10px] font-semibold uppercase">Schedule / Dates</span>
                        <span class="text-[#171D3A] font-semibold">${escapeHtml(item.event_date || item.start_date || 'Upcoming')}</span>
                        ${item.start_time ? `<span class="text-[10px] text-[#66708F] block">${escapeHtml(item.start_time)} to ${escapeHtml(item.end_time || '-')}</span>` : ''}
                    </div>
                    <div class="p-2.5 rounded-xl bg-[#F8F9FE] border border-[#E1E5F0]">
                        <span class="text-[#66708F] block text-[10px] font-semibold uppercase">Campus Venue</span>
                        <span class="text-[#171D3A] font-semibold">${escapeHtml(item.venue || 'SVIT Auditorium')}</span>
                    </div>
                    <div class="p-2.5 rounded-xl bg-[#F8F9FE] border border-[#E1E5F0]">
                        <span class="text-[#66708F] block text-[10px] font-semibold uppercase">Department</span>
                        <span class="text-[#171D3A] font-semibold">${escapeHtml(item.department || 'All Departments')}</span>
                    </div>
                    <div class="p-2.5 rounded-xl bg-[#F8F9FE] border border-[#E1E5F0]">
                        <span class="text-[#66708F] block text-[10px] font-semibold uppercase">Coordinator</span>
                        <span class="text-[#171D3A] font-semibold">${escapeHtml(item.organizer || 'College Committee')}</span>
                    </div>
                </div>

                ${item.speaker_or_guest ? `
                    <div class="p-3 rounded-xl bg-pink-50 border border-pink-200 text-xs">
                        <span class="text-pink-700 font-semibold block text-[10px] uppercase">Keynote Speaker / Chief Guest</span>
                        <span class="text-[#171D3A] font-bold">${escapeHtml(item.speaker_or_guest)}</span>
                    </div>
                ` : ''}

                <div class="p-3.5 rounded-xl bg-white border border-[#E1E5F0] text-xs text-[#171D3A] leading-relaxed">
                    <span class="text-[#66708F] block text-[10px] uppercase font-semibold mb-1">Event Agenda &amp; Details</span>
                    ${escapeHtml(item.description || 'No detailed description provided.').replace(/\n/g, '<br>')}
                </div>

                <div class="flex items-center justify-between flex-wrap gap-2 text-xs pt-1">
                    <div>
                        <span class="text-[#66708F]">Registration: </span>
                        <strong class="text-[#171D3A]">${regReq ? 'Required' : 'Open to All'}</strong>
                    </div>
                    ${item.registration_link ? `
                        <a href="${item.registration_link}" target="_blank" class="btn-primary-custom text-xs inline-flex items-center gap-1.5 text-decoration-none !bg-pink-600 hover:!bg-pink-700">
                            <i data-lucide="link" class="w-3.5 h-3.5"></i> Open Registration Page
                        </a>
                    ` : ''}
                </div>
            </div>
        `;

        if (window.lucide) lucide.createIcons();
        if (eventViewModal) eventViewModal.show();
    };

    window.deleteEvent = function(id) {
        state.pendingDeleteId = id;
        const targetEl = document.getElementById('deleteEventTargetId');
        if (targetEl) targetEl.innerText = id;
        if (eventDeleteModal) eventDeleteModal.show();
    };

    async function handleConfirmDelete() {
        if (!state.pendingDeleteId) return;

        try {
            const res = await fetch(`/admin/api/crud/events/${state.pendingDeleteId}`, { method: 'DELETE' });
            const data = await res.json();
            if (res.ok && data.status === 'success') {
                showAdminToast(data.message || 'Event deleted successfully.', 'success');
                if (eventDeleteModal) eventDeleteModal.hide();
                loadEvents();
            } else {
                showAdminToast(data.message || 'Failed to delete event.', 'error');
            }
        } catch (err) {
            showAdminToast(err.message || 'Failed to delete event.', 'error');
        }
    }
})();
