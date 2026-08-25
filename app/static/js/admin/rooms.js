/**
 * SVIT Admin - Page 9: Rooms Controller
 * Handles campus rooms, facilities, categories, image uploads,
 * view toggles, add/edit modal, details modal, and deletion.
 */

(function() {
    'use strict';

    const state = {
        search: '',
        category: '',
        zone: '',
        viewMode: 'table', // 'table' or 'grid'
        page: 1,
        limit: 20,
        total: 0,
        items: [],
        pendingDeleteId: null,
        uploadedImageUrl: null
    };

    let roomModal = null;
    let roomViewModal = null;
    let roomDeleteModal = null;
    let searchDebounce = null;

    document.addEventListener('DOMContentLoaded', function() {
        const formEl = document.getElementById('roomFormModal');
        const viewEl = document.getElementById('roomViewModal');
        const delEl = document.getElementById('roomDeleteModal');

        if (formEl) roomModal = new bootstrap.Modal(formEl);
        if (viewEl) roomViewModal = new bootstrap.Modal(viewEl);
        if (delEl) roomDeleteModal = new bootstrap.Modal(delEl);

        bindEvents();
        setupImageUpload();
        loadRooms();
    });

    function bindEvents() {
        const searchInput = document.getElementById('roomSearchInput');
        if (searchInput) {
            searchInput.addEventListener('input', (e) => {
                clearTimeout(searchDebounce);
                searchDebounce = setTimeout(() => {
                    state.search = e.target.value.trim();
                    state.page = 1;
                    loadRooms();
                }, 300);
            });
        }

        const catFilter = document.getElementById('roomCategoryFilter');
        if (catFilter) {
            catFilter.addEventListener('change', (e) => {
                state.category = e.target.value;
                state.page = 1;
                loadRooms();
            });
        }

        const zoneFilter = document.getElementById('roomZoneFilter');
        if (zoneFilter) {
            zoneFilter.addEventListener('change', (e) => {
                state.zone = e.target.value;
                state.page = 1;
                loadRooms();
            });
        }

        const refreshBtn = document.getElementById('refreshRoomsBtn');
        if (refreshBtn) refreshBtn.addEventListener('click', loadRooms);

        const limitSelect = document.getElementById('pageLimitSelect');
        if (limitSelect) {
            limitSelect.addEventListener('change', (e) => {
                state.limit = parseInt(e.target.value, 10) || 50;
                state.page = 1;
                loadRooms();
            });
        }

        const prevBtn = document.getElementById('prevPageBtn');
        if (prevBtn) {
            prevBtn.addEventListener('click', () => {
                if (state.page > 1) {
                    state.page--;
                    loadRooms();
                }
            });
        }

        const nextBtn = document.getElementById('nextPageBtn');
        if (nextBtn) {
            nextBtn.addEventListener('click', () => {
                const totalPages = Math.ceil(state.total / state.limit) || 1;
                if (state.page < totalPages) {
                    state.page++;
                    loadRooms();
                }
            });
        }

        const createBtn = document.getElementById('openCreateRoomModalBtn');
        if (createBtn) {
            createBtn.addEventListener('click', () => {
                document.getElementById('roomModalTitle').innerText = 'Add Room / Facility';
                document.getElementById('roomFormRecordId').value = '';
                document.getElementById('roomForm').reset();
                document.getElementById('roomIdInput').disabled = false;
                state.uploadedImageUrl = null;
                resetImagePreview();
                roomModal.show();
            });
        }

        const form = document.getElementById('roomForm');
        if (form) form.addEventListener('submit', handleRoomFormSubmit);

        const confirmDeleteBtn = document.getElementById('confirmDeleteRoomBtn');
        if (confirmDeleteBtn) confirmDeleteBtn.addEventListener('click', handleConfirmDelete);

        // View toggle
        const toggleTableBtn = document.getElementById('viewTableToggleBtn');
        const toggleGridBtn = document.getElementById('viewGridToggleBtn');

        if (toggleTableBtn && toggleGridBtn) {
            toggleTableBtn.addEventListener('click', () => {
                state.viewMode = 'table';
                toggleTableBtn.classList.add('bg-indigo-600', 'text-white');
                toggleGridBtn.classList.remove('bg-indigo-600', 'text-white');
                document.getElementById('roomsTableView').classList.remove('hidden');
                document.getElementById('roomsGridView').classList.add('hidden');
                renderRooms();
            });
            toggleGridBtn.addEventListener('click', () => {
                state.viewMode = 'grid';
                toggleGridBtn.classList.add('bg-indigo-600', 'text-white');
                toggleTableBtn.classList.remove('bg-indigo-600', 'text-white');
                document.getElementById('roomsGridView').classList.remove('hidden');
                document.getElementById('roomsTableView').classList.add('hidden');
                renderRooms();
            });
        }
    }

    function setupImageUpload() {
        const dropZone = document.getElementById('roomImageDropZone');
        const fileInput = document.getElementById('roomImageInput');

        if (dropZone && fileInput) {
            dropZone.addEventListener('click', () => fileInput.click());
            dropZone.addEventListener('dragover', (e) => { e.preventDefault(); dropZone.classList.add('border-indigo-500'); });
            dropZone.addEventListener('dragleave', () => dropZone.classList.remove('border-indigo-500'));
            dropZone.addEventListener('drop', (e) => {
                e.preventDefault();
                dropZone.classList.remove('border-indigo-500');
                if (e.dataTransfer.files.length) uploadRoomImage(e.dataTransfer.files[0]);
            });
            fileInput.addEventListener('change', (e) => {
                if (e.target.files.length) uploadRoomImage(e.target.files[0]);
            });
        }
    }

    async function uploadRoomImage(file) {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('category', 'image');

        const preview = document.getElementById('roomImagePreviewContainer');
        if (preview) {
            preview.innerHTML = '<span class="text-xs text-indigo-400">Uploading photo...</span>';
            preview.classList.remove('hidden');
        }

        try {
            const res = await fetch('/admin/api/upload', { method: 'POST', body: formData });
            const data = await res.json();
            if (res.ok && data.status === 'success') {
                state.uploadedImageUrl = data.file.url;
                if (preview) {
                    preview.innerHTML = `
                        <img src="${data.file.url}" class="w-16 h-12 rounded-lg object-cover border border-indigo-500">
                        <span class="text-xs text-emerald-400 font-medium">Photo Attached</span>
                    `;
                }
                showAdminToast('Room image attached.', 'success');
            } else {
                showAdminToast(data.message || 'Upload failed.', 'error');
                resetImagePreview();
            }
        } catch (err) {
            showAdminToast(err.message, 'error');
            resetImagePreview();
        }
    }

    function resetImagePreview() {
        const preview = document.getElementById('roomImagePreviewContainer');
        if (preview) {
            preview.innerHTML = '';
            preview.classList.add('hidden');
        }
    }

    async function loadRooms() {
        const tbody = document.getElementById('roomsTableBody');
        if (tbody) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="7" class="text-center py-10 text-gray-400 text-xs">
                        <div class="w-5 h-5 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin mx-auto mb-2"></div>
                        Loading campus rooms...
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
        if (state.zone) params.append('filter_zone', state.zone);

        try {
            const res = await fetch(`/admin/api/crud/rooms?${params.toString()}`);
            const data = await res.json();
            if (data.status === 'success') {
                state.items = data.items || [];
                state.total = data.total || 0;
                renderRooms();
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
                btn.className = `px-2 py-1 rounded-lg text-xs font-semibold transition ${state.page === i ? 'bg-indigo-600 text-white' : 'bg-[#111827] border border-[#1F2937] text-gray-400 hover:text-white'}`;
                btn.onclick = () => {
                    state.page = i;
                    loadRooms();
                };
                numbersContainer.appendChild(btn);
            }
        }
    }

    function renderRooms() {
        const countBadge = document.getElementById('roomsCountBadge');
        if (countBadge) countBadge.innerText = `${state.total} Rooms & Facilities`;

        if (state.viewMode === 'table') {
            renderTableView();
        } else {
            renderGridView();
        }
        lucide.createIcons();
    }

    function renderTableView() {
        const tbody = document.getElementById('roomsTableBody');
        if (!tbody) return;

        if (state.items.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="7" class="text-center py-12 text-gray-400 text-xs">
                        <i data-lucide="map-pin" class="w-8 h-8 mx-auto mb-2 text-gray-600"></i>
                        <p class="mb-0">No room records found.</p>
                    </td>
                </tr>
            `;
            return;
        }

        tbody.innerHTML = state.items.map(r => {
            const id = r.place_id || r.id || '-';
            const name = r.place_name || r.name || 'Room';
            const cat = r.category || 'Classroom';
            const zone = r.zone || 'Main Block';
            const landmark = r.landmark || '-';

            return `
                <tr>
                    <td>
                        <span class="font-mono text-indigo-400 font-bold text-xs">${id}</span>
                    </td>
                    <td>
                        <div class="flex items-center gap-2.5">
                            <div class="w-8 h-8 rounded-lg bg-indigo-600/10 border border-indigo-500/20 text-indigo-400 flex items-center justify-center font-bold text-xs overflow-hidden">
                                ${r.image_url ? `<img src="${r.image_url}" class="w-full h-full object-cover">` : '<i data-lucide="door-open" class="w-4 h-4"></i>'}
                            </div>
                            <div>
                                <p class="text-xs font-bold text-white mb-0">${name}</p>
                                <span class="text-[10px] text-gray-500">${r.description ? r.description.slice(0, 35) + '...' : ''}</span>
                            </div>
                        </div>
                    </td>
                    <td><span class="badge-room-type">${cat}</span></td>
                    <td><span class="badge-zone">${zone}</span></td>
                    <td class="text-gray-300 text-xs">${landmark}</td>
                    <td>
                        <span class="px-2 py-0.5 rounded text-[10px] bg-emerald-500/20 text-emerald-300 font-semibold flex items-center gap-1 w-max">
                            <span class="w-1.5 h-1.5 rounded-full bg-emerald-400"></span> Available
                        </span>
                    </td>
                    <td class="text-end">
                        <div class="inline-flex items-center gap-1.5">
                            <button class="p-1.5 rounded-lg bg-[#0F172A] border border-[#1F2937] text-gray-300 hover:text-white" onclick="window.viewRoom('${id}')" title="View Details">
                                <i data-lucide="eye" class="w-3.5 h-3.5"></i>
                            </button>
                            <button class="p-1.5 rounded-lg bg-[#0F172A] border border-[#1F2937] text-gray-300 hover:text-white" onclick="window.editRoom('${id}')" title="Edit Room">
                                <i data-lucide="edit-2" class="w-3.5 h-3.5"></i>
                            </button>
                            <button class="p-1.5 rounded-lg bg-[#0F172A] border border-[#1F2937] text-red-400 hover:bg-red-500/20" onclick="window.deleteRoom('${id}')" title="Delete">
                                <i data-lucide="trash-2" class="w-3.5 h-3.5"></i>
                            </button>
                        </div>
                    </td>
                </tr>
            `;
        }).join('');
    }

    function renderGridView() {
        const grid = document.getElementById('roomsGridContainer');
        if (!grid) return;

        if (state.items.length === 0) {
            grid.innerHTML = `<div class="col-span-full text-center py-10 text-gray-400 text-xs">No rooms found.</div>`;
            return;
        }

        grid.innerHTML = state.items.map(r => {
            const id = r.place_id || r.id || '-';
            const name = r.place_name || r.name || 'Room';
            const cat = r.category || 'Classroom';
            const zone = r.zone || 'Main Block';

            return `
                <div class="room-card-box space-y-3">
                    <div class="flex items-start justify-between gap-2">
                        <div class="flex items-center gap-2.5">
                            <div class="w-10 h-10 rounded-xl bg-indigo-600/20 border border-indigo-500/30 text-indigo-400 flex items-center justify-center font-bold text-sm overflow-hidden">
                                ${r.image_url ? `<img src="${r.image_url}" class="w-full h-full object-cover">` : '<i data-lucide="door-open" class="w-5 h-5"></i>'}
                            </div>
                            <div>
                                <h4 class="text-sm font-bold text-white mb-0">${name}</h4>
                                <span class="font-mono text-xs text-indigo-400">${id}</span>
                            </div>
                        </div>
                        <span class="badge-room-type">${cat}</span>
                    </div>
                    <div class="text-xs text-gray-400 space-y-1 pt-2 border-t border-[#1F2937]">
                        <div class="flex justify-between"><span class="text-gray-500">Zone:</span> <span class="text-gray-200 font-medium">${zone}</span></div>
                        <div class="flex justify-between"><span class="text-gray-500">Landmark:</span> <span class="text-gray-300">${r.landmark || '-'}</span></div>
                    </div>
                    <div class="pt-2 flex justify-end gap-1.5">
                        <button class="px-3 py-1 rounded-lg bg-[#0F172A] border border-[#1F2937] text-gray-300 text-xs hover:text-white" onclick="window.viewRoom('${id}')">Details</button>
                        <button class="px-3 py-1 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs" onclick="window.editRoom('${id}')">Edit</button>
                    </div>
                </div>
            `;
        }).join('');
    }

    async function handleRoomFormSubmit(e) {
        e.preventDefault();
        const recordId = document.getElementById('roomFormRecordId').value;
        const payload = {
            place_id: document.getElementById('roomIdInput').value.trim(),
            place_name: document.getElementById('roomNameInput').value.trim(),
            category: document.getElementById('roomCategoryInput').value,
            zone: document.getElementById('roomZoneInput').value,
            landmark: document.getElementById('roomLandmarkInput').value.trim(),
            description: document.getElementById('roomDescInput').value.trim()
        };

        if (state.uploadedImageUrl) payload.image_url = state.uploadedImageUrl;

        const isEdit = Boolean(recordId);
        const url = isEdit ? `/admin/api/crud/rooms/${recordId}` : '/admin/api/crud/rooms';
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
                roomModal.hide();
                loadRooms();
            } else {
                showAdminToast(data.message || 'Error saving room record.', 'error');
            }
        } catch (err) {
            showAdminToast(err.message, 'error');
        }
    }

    window.editRoom = function(id) {
        const room = state.items.find(r => (r.place_id || r.id) === id);
        if (!room) return;

        document.getElementById('roomModalTitle').innerText = 'Edit Room / Facility';
        document.getElementById('roomFormRecordId').value = id;
        document.getElementById('roomIdInput').value = room.place_id || id;
        document.getElementById('roomIdInput').disabled = true;
        document.getElementById('roomNameInput').value = room.place_name || room.name || '';
        document.getElementById('roomCategoryInput').value = room.category || 'Classroom';
        document.getElementById('roomZoneInput').value = room.zone || 'Main Block';
        document.getElementById('roomLandmarkInput').value = room.landmark || '';
        document.getElementById('roomDescInput').value = room.description || '';

        state.uploadedImageUrl = room.image_url || null;
        if (room.image_url) {
            const preview = document.getElementById('roomImagePreviewContainer');
            if (preview) {
                preview.innerHTML = `<img src="${room.image_url}" class="w-16 h-16 rounded-xl object-cover border border-indigo-500/50">`;
                preview.classList.remove('hidden');
            }
        } else {
            resetImagePreview();
        }

        roomModal.show();
    };

    window.viewRoom = function(id) {
        const room = state.items.find(r => (r.place_id || r.id) === id);
        if (!room) return;

        const container = document.getElementById('roomViewContent');
        if (!container) return;

        container.innerHTML = `
            <div class="space-y-4">
                <div class="flex items-center gap-3.5 p-4 rounded-2xl bg-[#0F172A] border border-[#1F2937]">
                    <div class="w-16 h-16 rounded-2xl bg-indigo-600/20 border border-indigo-500/30 text-indigo-400 font-bold text-xl flex items-center justify-center overflow-hidden flex-shrink-0">
                        ${room.image_url ? `<img src="${room.image_url}" class="w-full h-full object-cover">` : '<i data-lucide="door-open" class="w-8 h-8"></i>'}
                    </div>
                    <div>
                        <span class="badge-room-type">${room.category || 'Classroom'}</span>
                        <h3 class="text-base font-bold text-white mt-1 mb-0">${room.place_name || room.name}</h3>
                        <p class="text-xs text-indigo-400 font-mono mb-0">${room.place_id || id}</p>
                    </div>
                </div>
                <div class="grid grid-cols-2 gap-3 text-xs">
                    <div class="p-2.5 rounded-lg bg-[#0F172A] border border-[#1F2937]">
                        <span class="text-gray-500 block text-[10px]">CAMPUS ZONE</span>
                        <span class="text-white font-medium">${room.zone || 'Main Block'}</span>
                    </div>
                    <div class="p-2.5 rounded-lg bg-[#0F172A] border border-[#1F2937]">
                        <span class="text-gray-500 block text-[10px]">NEAREST LANDMARK</span>
                        <span class="text-white font-medium">${room.landmark || '-'}</span>
                    </div>
                </div>
                <div class="p-3 rounded-lg bg-[#0F172A] border border-[#1F2937] text-xs text-gray-300">
                    <span class="text-gray-500 block text-[10px] mb-1">ACCESSIBILITY & DETAILS</span>
                    ${room.description || 'No special notes provided.'}
                </div>
            </div>
        `;

        roomViewModal.show();
    };

    window.deleteRoom = function(id) {
        state.pendingDeleteId = id;
        document.getElementById('deleteRoomTargetId').innerText = id;
        roomDeleteModal.show();
    };

    async function handleConfirmDelete() {
        if (!state.pendingDeleteId) return;

        try {
            const res = await fetch(`/admin/api/crud/rooms/${state.pendingDeleteId}`, { method: 'DELETE' });
            const data = await res.json();
            if (res.ok && data.status === 'success') {
                showAdminToast(data.message, 'success');
                roomDeleteModal.hide();
                loadRooms();
            } else {
                showAdminToast(data.message || 'Failed to delete room record.', 'error');
            }
        } catch (err) {
            showAdminToast(err.message, 'error');
        }
    }
})();
