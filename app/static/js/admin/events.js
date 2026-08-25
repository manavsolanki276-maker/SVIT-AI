/**
 * SVIT Admin - Page 14: College Events Controller
 * Cultural fests, tech hackathons, workshops, and symposiums (NO Sports events).
 * Supports poster upload, grid/table view modes, category/status filtering.
 */

(function() {
    'use strict';

    const state = {
        search: '',
        category: '',
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

    document.addEventListener('DOMContentLoaded', function() {
        const formEl = document.getElementById('eventFormModal');
        const viewEl = document.getElementById('eventViewModal');
        const delEl = document.getElementById('eventDeleteModal');

        if (formEl) eventModal = new bootstrap.Modal(formEl);
        if (viewEl) eventViewModal = new bootstrap.Modal(viewEl);
        if (delEl) eventDeleteModal = new bootstrap.Modal(delEl);

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
                state.limit = parseInt(e.target.value, 10) || 50;
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

        const createBtn = document.getElementById('openCreateEventModalBtn');
        if (createBtn) {
            createBtn.addEventListener('click', () => {
                document.getElementById('eventModalTitle').innerText = 'Add College Event';
                document.getElementById('eventFormRecordId').value = '';
                document.getElementById('eventForm').reset();
                document.getElementById('eventIdInput').disabled = false;
                state.uploadedBannerUrl = null;
                resetPosterPreview();
                eventModal.show();
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
                toggleGridBtn.classList.remove('bg-pink-600', 'text-white');
                document.getElementById('eventsTableView').classList.remove('hidden');
                document.getElementById('eventsGridView').classList.add('hidden');
                renderEvents();
            });
            toggleGridBtn.addEventListener('click', () => {
                state.viewMode = 'grid';
                toggleGridBtn.classList.add('bg-pink-600', 'text-white');
                toggleTableBtn.classList.remove('bg-pink-600', 'text-white');
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
                if (e.dataTransfer.files.length) uploadEventPoster(e.dataTransfer.files[0]);
            });
            fileInput.addEventListener('change', (e) => {
                if (e.target.files.length) uploadEventPoster(e.target.files[0]);
            });
        }
    }

    async function uploadEventPoster(file) {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('category', 'image');

        const preview = document.getElementById('eventPosterPreviewContainer');
        if (preview) {
            preview.innerHTML = '<span class="text-xs text-pink-400">Uploading banner...</span>';
            preview.classList.remove('hidden');
        }

        try {
            const res = await fetch('/admin/api/upload', { method: 'POST', body: formData });
            const data = await res.json();
            if (res.ok && data.status === 'success') {
                state.uploadedBannerUrl = data.file.url;
                if (preview) {
                    preview.innerHTML = `
                        <img src="${data.file.url}" class="w-20 h-12 rounded-lg object-cover border border-pink-500">
                        <span class="text-xs text-emerald-400 font-medium">Banner Attached</span>
                    `;
                }
                showAdminToast('Event banner attached.', 'success');
            } else {
                showAdminToast(data.message || 'Upload failed.', 'error');
                resetPosterPreview();
            }
        } catch (err) {
            showAdminToast(err.message, 'error');
            resetPosterPreview();
        }
    }

    function resetPosterPreview() {
        const preview = document.getElementById('eventPosterPreviewContainer');
        if (preview) {
            preview.innerHTML = '';
            preview.classList.add('hidden');
        }
    }

    async function loadEvents() {
        const tbody = document.getElementById('eventsTableBody');
        const grid = document.getElementById('eventsGridContainer');

        if (tbody) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="7" class="text-center py-10 text-gray-400 text-xs">
                        <div class="w-5 h-5 border-2 border-pink-500 border-t-transparent rounded-full animate-spin mx-auto mb-2"></div>
                        Loading college events...
                    </td>
                </tr>
            `;
        }

        const params = new URLSearchParams({
            page: state.page,
            limit: state.limit,
            search: state.search
        });
        if (state.category) params.append('filter_category', state.category);
        if (state.status) params.append('filter_status', state.status);

        try {
            const res = await fetch(`/admin/api/crud/events?${params.toString()}`);
            const data = await res.json();
            if (data.status === 'success') {
                state.items = data.items || [];
                state.total = data.total || 0;
                renderEvents();
                renderPagination(data);
            } else {
                if (tbody) tbody.innerHTML = `<tr><td colspan="7" class="text-center py-6 text-red-400 text-xs">${data.message}</td></tr>`;
            }
        } catch (err) {
            if (tbody) tbody.innerHTML = `<tr><td colspan="7" class="text-center py-6 text-red-400 text-xs">${err.message}</td></tr>`;
        }
        lucide.createIcons();
    }

    function renderPagination(data) {
        const start = state.total === 0 ? 0 : (state.page - 1) * state.limit + 1;
        const end = Math.min(state.page * state.limit, state.total);
        const totalPages = data.pages || Math.ceil(state.total / state.limit) || 1;

        const startEl = document.getElementById('pageStart');
        const endEl = document.getElementById('pageEnd');
        const totalEl = document.getElementById('pageTotal');
        const prevBtn = document.getElementById('prevPageBtn');
        const nextBtn = document.getElementById('nextPageBtn');
        const numbersContainer = document.getElementById('pageNumbers');

        if (startEl) startEl.innerText = start;
        if (endEl) endEl.innerText = end;
        if (totalEl) totalEl.innerText = state.total;

        if (prevBtn) prevBtn.disabled = (state.page <= 1);
        if (nextBtn) nextBtn.disabled = (state.page >= totalPages);

        if (numbersContainer) {
            numbersContainer.innerHTML = '';
            const maxVisible = 5;
            let startP = Math.max(1, state.page - 2);
            let endP = Math.min(totalPages, startP + maxVisible - 1);
            if (endP - startP < maxVisible - 1) {
                startP = Math.max(1, endP - maxVisible + 1);
            }

            for (let i = startP; i <= endP; i++) {
                const btn = document.createElement('button');
                btn.innerText = i;
                btn.className = `px-2 py-1 rounded-lg text-xs font-semibold transition ${state.page === i ? 'bg-pink-600 text-white' : 'bg-[#111827] border border-[#1F2937] text-gray-400 hover:text-white'}`;
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
        lucide.createIcons();
    }

    function renderTableView() {
        const tbody = document.getElementById('eventsTableBody');
        if (!tbody) return;

        if (state.items.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="7" class="text-center py-12 text-gray-400 text-xs">
                        <i data-lucide="party-popper" class="w-8 h-8 mx-auto mb-2 text-gray-600"></i>
                        <p class="mb-0">No college events found.</p>
                    </td>
                </tr>
            `;
            return;
        }

        tbody.innerHTML = state.items.map(e => {
            const id = e.event_id || e.id || '-';
            const title = e.event_name || e.title || 'College Event';
            const cat = e.category || 'Cultural';
            const dates = e.event_date || (e.start_date ? `${e.start_date} to ${e.end_date || ''}` : 'Upcoming');
            const venue = e.venue || 'SVIT Auditorium';
            const status = e.status || 'Upcoming';
            const poster = e.image_url || e.banner_url;

            return `
                <tr>
                    <td>
                        <div class="flex items-center gap-2.5">
                            <div class="event-banner-box">
                                ${poster ? `<img src="${poster}" alt="${title}">` : '<i data-lucide="sparkles" class="w-4 h-4 text-pink-400"></i>'}
                            </div>
                            <div>
                                <p class="text-xs font-bold text-white mb-0">${title}</p>
                                <span class="text-[10px] text-pink-400 font-mono">${id}</span>
                            </div>
                        </div>
                    </td>
                    <td><span class="badge-event-cat">${cat}</span></td>
                    <td class="text-gray-300 text-xs">${dates}</td>
                    <td class="text-gray-300 text-xs">${venue}</td>
                    <td>
                        ${e.registration_link ? `
                            <a href="${e.registration_link}" target="_blank" class="text-indigo-400 hover:text-indigo-300 text-xs font-semibold flex items-center gap-1 text-decoration-none">
                                <i data-lucide="link" class="w-3 h-3"></i> Register
                            </a>
                        ` : '<span class="text-gray-600 text-xs">-</span>'}
                    </td>
                    <td>
                        <span class="px-2 py-0.5 rounded text-[10px] bg-emerald-500/20 text-emerald-300 font-semibold">${status}</span>
                    </td>
                    <td class="text-end">
                        <div class="inline-flex items-center gap-1.5">
                            <button class="p-1.5 rounded-lg bg-[#0F172A] border border-[#1F2937] text-gray-300 hover:text-white" onclick="window.viewEvent('${id}')" title="View Event">
                                <i data-lucide="eye" class="w-3.5 h-3.5"></i>
                            </button>
                            <button class="p-1.5 rounded-lg bg-[#0F172A] border border-[#1F2937] text-gray-300 hover:text-white" onclick="window.editEvent('${id}')" title="Edit Event">
                                <i data-lucide="edit-2" class="w-3.5 h-3.5"></i>
                            </button>
                            <button class="p-1.5 rounded-lg bg-[#0F172A] border border-[#1F2937] text-red-400 hover:bg-red-500/20" onclick="window.deleteEvent('${id}')" title="Delete">
                                <i data-lucide="trash-2" class="w-3.5 h-3.5"></i>
                            </button>
                        </div>
                    </td>
                </tr>
            `;
        }).join('');
    }

    function renderGridView() {
        const grid = document.getElementById('eventsGridContainer');
        if (!grid) return;

        if (state.items.length === 0) {
            grid.innerHTML = `<div class="col-span-full text-center py-10 text-gray-400 text-xs">No events found.</div>`;
            return;
        }

        grid.innerHTML = state.items.map(e => {
            const id = e.event_id || e.id || '-';
            const title = e.event_name || e.title || 'College Event';
            const cat = e.category || 'Cultural';
            const dates = e.event_date || (e.start_date ? `${e.start_date}` : 'Upcoming');
            const venue = e.venue || 'SVIT Auditorium';
            const poster = e.image_url || e.banner_url;

            return `
                <div class="event-card-box">
                    <div class="h-32 bg-[#0F172A] relative flex items-center justify-center overflow-hidden">
                        ${poster ? `<img src="${poster}" class="w-full h-full object-cover">` : '<i data-lucide="sparkles" class="w-10 h-10 text-pink-400 opacity-60"></i>'}
                        <span class="badge-event-cat absolute top-2 right-2">${cat}</span>
                    </div>
                    <div class="p-4 space-y-2">
                        <h4 class="text-sm font-bold text-white mb-0 truncate">${title}</h4>
                        <p class="text-xs text-gray-400 mb-0 flex items-center gap-1.5"><i data-lucide="calendar" class="w-3 h-3 text-pink-400"></i> ${dates}</p>
                        <p class="text-xs text-gray-400 mb-0 flex items-center gap-1.5"><i data-lucide="map-pin" class="w-3 h-3 text-emerald-400"></i> ${venue}</p>
                        <div class="pt-2 flex justify-end gap-1.5 border-t border-[#1F2937]">
                            <button class="px-3 py-1 rounded-lg bg-[#0F172A] border border-[#1F2937] text-gray-300 text-xs hover:text-white" onclick="window.viewEvent('${id}')">Details</button>
                            <button class="px-3 py-1 rounded-lg bg-pink-600 hover:bg-pink-500 text-white text-xs" onclick="window.editEvent('${id}')">Edit</button>
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
            event_date: document.getElementById('eventStartDateInput').value,
            start_date: document.getElementById('eventStartDateInput').value,
            end_date: document.getElementById('eventEndDateInput').value,
            venue: document.getElementById('eventVenueInput').value.trim(),
            registration_link: document.getElementById('eventRegLinkInput').value.trim(),
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
                showAdminToast(data.message, 'success');
                eventModal.hide();
                loadEvents();
            } else {
                showAdminToast(data.message || 'Error saving event.', 'error');
            }
        } catch (err) {
            showAdminToast(err.message, 'error');
        }
    }

    window.editEvent = function(id) {
        const item = state.items.find(e => (e.event_id || e.id) === id);
        if (!item) return;

        document.getElementById('eventModalTitle').innerText = 'Edit College Event';
        document.getElementById('eventFormRecordId').value = id;
        document.getElementById('eventIdInput').value = item.event_id || id;
        document.getElementById('eventIdInput').disabled = true;
        document.getElementById('eventNameInput').value = item.event_name || item.title || '';
        document.getElementById('eventCategoryInput').value = item.category || 'Cultural';
        document.getElementById('eventStartDateInput').value = item.start_date || item.event_date || '';
        document.getElementById('eventEndDateInput').value = item.end_date || '';
        document.getElementById('eventVenueInput').value = item.venue || 'SVIT Auditorium';
        document.getElementById('eventRegLinkInput').value = item.registration_link || '';
        document.getElementById('eventStatusInput').value = item.status || 'Upcoming';
        document.getElementById('eventDescInput').value = item.description || '';

        state.uploadedBannerUrl = item.banner_url || item.image_url || null;
        if (state.uploadedBannerUrl) {
            const preview = document.getElementById('eventPosterPreviewContainer');
            if (preview) {
                preview.innerHTML = `<img src="${state.uploadedBannerUrl}" class="w-16 h-16 rounded-xl object-cover border border-pink-500">`;
                preview.classList.remove('hidden');
            }
        } else {
            resetPosterPreview();
        }

        eventModal.show();
    };

    window.viewEvent = function(id) {
        const item = state.items.find(e => (e.event_id || e.id) === id);
        if (!item) return;

        const container = document.getElementById('eventViewContent');
        if (!container) return;

        container.innerHTML = `
            <div class="space-y-4">
                <div class="flex items-center gap-3.5 p-4 rounded-2xl bg-[#0F172A] border border-[#1F2937]">
                    <div class="w-16 h-16 rounded-2xl bg-pink-600/20 text-pink-400 font-bold text-lg flex items-center justify-center overflow-hidden flex-shrink-0">
                        ${(item.banner_url || item.image_url) ? `<img src="${item.banner_url || item.image_url}" class="w-full h-full object-cover">` : '<i data-lucide="sparkles" class="w-7 h-7"></i>'}
                    </div>
                    <div>
                        <span class="badge-event-cat">${item.category || 'Cultural'}</span>
                        <h3 class="text-base font-bold text-white mt-1 mb-0">${item.event_name || item.title}</h3>
                        <p class="text-xs text-pink-400 font-mono mb-0">${item.event_id || id}</p>
                    </div>
                </div>
                <div class="grid grid-cols-2 gap-3 text-xs">
                    <div class="p-2.5 rounded-lg bg-[#0F172A] border border-[#1F2937]">
                        <span class="text-gray-500 block text-[10px]">SCHEDULE / DATES</span>
                        <span class="text-white font-medium">${item.event_date || item.start_date || 'Upcoming'}</span>
                    </div>
                    <div class="p-2.5 rounded-lg bg-[#0F172A] border border-[#1F2937]">
                        <span class="text-gray-500 block text-[10px]">CAMPUS VENUE</span>
                        <span class="text-white font-medium">${item.venue || 'SVIT Auditorium'}</span>
                    </div>
                </div>
                <div class="p-3 rounded-lg bg-[#0F172A] border border-[#1F2937] text-xs text-gray-300">
                    <span class="text-gray-500 block text-[10px] mb-1">EVENT DESCRIPTION</span>
                    ${item.description || 'No detailed description provided.'}
                </div>
            </div>
        `;

        eventViewModal.show();
    };

    window.deleteEvent = function(id) {
        state.pendingDeleteId = id;
        document.getElementById('deleteEventTargetId').innerText = id;
        eventDeleteModal.show();
    };

    async function handleConfirmDelete() {
        if (!state.pendingDeleteId) return;

        try {
            const res = await fetch(`/admin/api/crud/events/${state.pendingDeleteId}`, { method: 'DELETE' });
            const data = await res.json();
            if (res.ok && data.status === 'success') {
                showAdminToast(data.message, 'success');
                eventDeleteModal.hide();
                loadEvents();
            } else {
                showAdminToast(data.message || 'Failed to delete event.', 'error');
            }
        } catch (err) {
            showAdminToast(err.message, 'error');
        }
    }
})();
