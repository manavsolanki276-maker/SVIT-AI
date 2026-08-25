/**
 * SVIT Admin - Page 26: Sports Disciplines Controller
 * Athletic disciplines (Cricket, Football, Badminton, Table Tennis, Volleyball, Chess),
 * indoor/outdoor filters, equipment notes, coach in-charge, photo upload, add/edit/delete.
 */

(function() {
    'use strict';

    const state = {
        search: '',
        type: '',
        page: 1,
        limit: 20,
        total: 0,
        items: [],
        pendingDeleteId: null,
        uploadedSportImg: null
    };

    let sportModal = null;
    let deleteModal = null;
    let searchDebounce = null;

    document.addEventListener('DOMContentLoaded', function() {
        const formEl = document.getElementById('sportModal');
        const delEl = document.getElementById('sportDeleteModal');

        if (formEl) sportModal = new bootstrap.Modal(formEl);
        if (delEl) deleteModal = new bootstrap.Modal(delEl);

        bindEvents();
        setupSportImageUpload();
        loadSports();
    });

    function bindEvents() {
        const searchInput = document.getElementById('sportSearchInput');
        if (searchInput) {
            searchInput.addEventListener('input', (e) => {
                clearTimeout(searchDebounce);
                searchDebounce = setTimeout(() => {
                    state.search = e.target.value.trim().toLowerCase();
                    renderSportsCards();
                }, 300);
            });
        }

        const typeFilter = document.getElementById('sportTypeFilter');
        if (typeFilter) {
            typeFilter.addEventListener('change', (e) => {
                state.type = e.target.value;
                renderSportsCards();
            });
        }

        const refreshBtn = document.getElementById('refreshSportsBtn');
        if (refreshBtn) refreshBtn.addEventListener('click', loadSports);

        const createBtn = document.getElementById('openCreateSportModalBtn');
        if (createBtn) {
            createBtn.addEventListener('click', () => {
                document.getElementById('sportModalTitle').innerText = 'Add Sports Discipline';
                document.getElementById('sportFormRecordId').value = '';
                document.getElementById('sportForm').reset();
                state.uploadedSportImg = null;
                resetSportPreview();
                sportModal.show();
            });
        }

        const form = document.getElementById('sportForm');
        if (form) form.addEventListener('submit', handleSportFormSubmit);

        const confirmDeleteBtn = document.getElementById('confirmDeleteSportBtn');
        if (confirmDeleteBtn) confirmDeleteBtn.addEventListener('click', handleConfirmDelete);
    }

    function setupSportImageUpload() {
        const dropZone = document.getElementById('sportPhotoDropZone');
        const fileInput = document.getElementById('sportPhotoInput');

        if (dropZone && fileInput) {
            dropZone.addEventListener('click', () => fileInput.click());
            dropZone.addEventListener('dragover', (e) => { e.preventDefault(); dropZone.classList.add('border-yellow-500'); });
            dropZone.addEventListener('dragleave', () => dropZone.classList.remove('border-yellow-500'));
            dropZone.addEventListener('drop', (e) => {
                e.preventDefault();
                dropZone.classList.remove('border-yellow-500');
                if (e.dataTransfer.files.length) uploadSportImage(e.dataTransfer.files[0]);
            });
            fileInput.addEventListener('change', (e) => {
                if (e.target.files.length) uploadSportImage(e.target.files[0]);
            });
        }
    }

    async function uploadSportImage(file) {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('category', 'image');

        const preview = document.getElementById('sportPhotoPreviewContainer');
        if (preview) {
            preview.innerHTML = '<span class="text-xs text-yellow-400">Uploading photo...</span>';
            preview.classList.remove('hidden');
        }

        try {
            const res = await fetch('/admin/api/upload', { method: 'POST', body: formData });
            const data = await res.json();
            if (res.ok && data.status === 'success') {
                state.uploadedSportImg = data.file.url;
                if (preview) {
                    preview.innerHTML = `
                        <img src="${data.file.url}" class="w-16 h-16 rounded-xl object-cover border border-yellow-500">
                        <span class="text-xs text-emerald-400 font-medium">Photo Attached</span>
                    `;
                }
                showAdminToast('Sports photo uploaded.', 'success');
            } else {
                showAdminToast(data.message || 'Upload failed.', 'error');
                resetSportPreview();
            }
        } catch (err) {
            showAdminToast(err.message, 'error');
            resetSportPreview();
        }
    }

    function resetSportPreview() {
        const preview = document.getElementById('sportPhotoPreviewContainer');
        if (preview) {
            preview.innerHTML = '';
            preview.classList.add('hidden');
        }
    }

    async function loadSports() {
        const grid = document.getElementById('sportsGridContainer');
        if (!grid) return;

        grid.innerHTML = `
            <div class="col-span-full text-center py-12 text-gray-400 text-xs">
                <div class="w-5 h-5 border-2 border-yellow-500 border-t-transparent rounded-full animate-spin mx-auto mb-2"></div>
                Loading sports disciplines...
            </div>
        `;

        try {
            const res = await fetch('/admin/api/crud/sports?limit=500');
            const data = await res.json();
            if (data.status === 'success') {
                state.items = data.items || [];
                renderSportsCards();
            } else {
                grid.innerHTML = `<div class="col-span-full text-center py-6 text-red-400 text-xs">${data.message}</div>`;
            }
        } catch (err) {
            grid.innerHTML = `<div class="col-span-full text-center py-6 text-red-400 text-xs">${err.message}</div>`;
        }
        lucide.createIcons();
    }

    function renderSportsCards() {
        const grid = document.getElementById('sportsGridContainer');
        const countBadge = document.getElementById('sportsCountBadge');
        if (!grid) return;

        const filtered = state.items.filter(s => {
            const matchSearch = !state.search ||
                (s.sport_name || s.name || '').toLowerCase().includes(state.search);
            const matchType = !state.type || s.type === state.type;
            return matchSearch && matchType;
        });

        if (countBadge) countBadge.innerText = `${filtered.length} Disciplines`;

        if (filtered.length === 0) {
            grid.innerHTML = `<div class="col-span-full text-center py-12 text-gray-400 text-xs">No sports disciplines found.</div>`;
            return;
        }

        grid.innerHTML = filtered.map(s => {
            const id = s.id || s.sport_name;
            const name = s.sport_name || s.name || 'Sport';
            const type = s.type || 'Outdoor';
            const coach = s.coach_incharge || s.coach || 'Athletics In-Charge';
            const grounds = s.grounds || s.ground_name || 'Campus Main Ground';
            const img = s.image_url;

            return `
                <div class="sport-card-box">
                    <div class="sport-img-wrapper">
                        ${img ? `<img src="${img}" alt="${name}">` : '<i data-lucide="trophy" class="w-10 h-10 text-yellow-400 opacity-60"></i>'}
                        <span class="badge-sport-type absolute top-2.5 right-2.5">${type}</span>
                    </div>
                    <div class="p-4 space-y-2">
                        <h4 class="text-sm font-bold text-white mb-0 truncate">${name}</h4>
                        <p class="text-xs text-gray-400 mb-0"><i data-lucide="user-check" class="w-3.5 h-3.5 text-yellow-400 d-inline mr-1"></i>Coach: <strong class="text-gray-200">${coach}</strong></p>
                        <p class="text-xs text-gray-400 mb-0"><i data-lucide="map-pin" class="w-3.5 h-3.5 text-emerald-400 d-inline mr-1"></i>${grounds}</p>
                        <div class="pt-3 border-t border-[#1F2937] flex justify-end gap-1.5">
                            <button class="p-1.5 rounded-lg bg-[#0F172A] border border-[#1F2937] text-gray-300 hover:text-white" onclick="window.editSport('${id}')">
                                <i data-lucide="edit-2" class="w-3.5 h-3.5"></i>
                            </button>
                            <button class="p-1.5 rounded-lg bg-[#0F172A] border border-[#1F2937] text-red-400 hover:bg-red-500/20" onclick="window.deleteSport('${id}')">
                                <i data-lucide="trash-2" class="w-3.5 h-3.5"></i>
                            </button>
                        </div>
                    </div>
                </div>
            `;
        }).join('');

        lucide.createIcons();
    }

    async function handleSportFormSubmit(e) {
        e.preventDefault();
        const recordId = document.getElementById('sportFormRecordId').value;
        const payload = {
            id: recordId || `SPORT-${Date.now()}`,
            sport_name: document.getElementById('sportNameInput').value.trim(),
            type: document.getElementById('sportTypeSelect').value,
            coach_incharge: document.getElementById('sportCoachInput').value.trim(),
            grounds: document.getElementById('sportGroundInput').value.trim(),
            equipment_info: document.getElementById('sportEquipInput').value.trim()
        };

        if (state.uploadedSportImg) payload.image_url = state.uploadedSportImg;

        const isEdit = Boolean(recordId);
        const url = isEdit ? `/admin/api/crud/sports/${recordId}` : '/admin/api/crud/sports';
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
                sportModal.hide();
                loadSports();
            } else {
                showAdminToast(data.message || 'Error saving sport.', 'error');
            }
        } catch (err) {
            showAdminToast(err.message, 'error');
        }
    }

    window.editSport = function(id) {
        const item = state.items.find(s => String(s.id) === String(id));
        if (!item) return;

        document.getElementById('sportModalTitle').innerText = 'Edit Sports Discipline';
        document.getElementById('sportFormRecordId').value = id;
        document.getElementById('sportNameInput').value = item.sport_name || item.name || '';
        document.getElementById('sportTypeSelect').value = item.type || 'Outdoor';
        document.getElementById('sportCoachInput').value = item.coach_incharge || item.coach || '';
        document.getElementById('sportGroundInput').value = item.grounds || item.ground_name || '';
        document.getElementById('sportEquipInput').value = item.equipment_info || '';

        state.uploadedSportImg = item.image_url || null;
        if (item.image_url) {
            const preview = document.getElementById('sportPhotoPreviewContainer');
            if (preview) {
                preview.innerHTML = `<img src="${item.image_url}" class="w-16 h-16 rounded-xl object-cover border border-yellow-500">`;
                preview.classList.remove('hidden');
            }
        } else {
            resetSportPreview();
        }

        sportModal.show();
    };

    window.deleteSport = function(id) {
        state.pendingDeleteId = id;
        document.getElementById('deleteSportTargetId').innerText = id;
        deleteModal.show();
    };

    async function handleConfirmDelete() {
        if (!state.pendingDeleteId) return;

        try {
            const res = await fetch(`/admin/api/crud/sports/${state.pendingDeleteId}`, { method: 'DELETE' });
            const data = await res.json();
            if (res.ok && data.status === 'success') {
                showAdminToast(data.message, 'success');
                deleteModal.hide();
                loadSports();
            } else {
                showAdminToast(data.message || 'Delete failed.', 'error');
            }
        } catch (err) {
            showAdminToast(err.message, 'error');
        }
    }
})();
