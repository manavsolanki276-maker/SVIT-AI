/**
 * SVIT Admin - Page 28: Grounds & Facilities Controller
 * Cricket pitch, football turf, basketball/badminton courts, floodlight status,
 * ground photo upload, add/edit/delete.
 */

(function() {
    'use strict';

    const state = {
        search: '',
        page: 1,
        limit: 50,
        total: 0,
        items: [],
        pendingDeleteId: null,
        uploadedGroundImg: null
    };

    let groundModal = null;
    let deleteModal = null;
    let searchDebounce = null;

    document.addEventListener('DOMContentLoaded', function() {
        const formEl = document.getElementById('groundModal');
        const delEl = document.getElementById('groundDeleteModal');

        if (formEl) groundModal = new bootstrap.Modal(formEl);
        if (delEl) deleteModal = new bootstrap.Modal(delEl);

        bindEvents();
        setupGroundImageUpload();
        loadGrounds();
    });

    function bindEvents() {
        const searchInput = document.getElementById('groundSearchInput');
        if (searchInput) {
            searchInput.addEventListener('input', (e) => {
                clearTimeout(searchDebounce);
                searchDebounce = setTimeout(() => {
                    state.search = e.target.value.trim();
                    state.page = 1;
                    loadGrounds();
                }, 300);
            });
        }

        const refreshBtn = document.getElementById('refreshGroundsBtn');
        if (refreshBtn) refreshBtn.addEventListener('click', loadGrounds);

        const createBtn = document.getElementById('openCreateGroundModalBtn');
        if (createBtn) {
            createBtn.addEventListener('click', () => {
                document.getElementById('groundModalTitle').innerText = 'Add Athletic Ground';
                document.getElementById('groundFormRecordId').value = '';
                document.getElementById('groundForm').reset();
                state.uploadedGroundImg = null;
                resetGroundPreview();
                groundModal.show();
            });
        }

        const form = document.getElementById('groundForm');
        if (form) form.addEventListener('submit', handleGroundFormSubmit);

        const confirmDeleteBtn = document.getElementById('confirmDeleteGroundBtn');
        if (confirmDeleteBtn) confirmDeleteBtn.addEventListener('click', handleConfirmDelete);
    }

    function setupGroundImageUpload() {
        const dropZone = document.getElementById('groundPhotoDropZone');
        const fileInput = document.getElementById('groundPhotoInput');

        if (dropZone && fileInput) {
            dropZone.addEventListener('click', () => fileInput.click());
            dropZone.addEventListener('dragover', (e) => { e.preventDefault(); dropZone.classList.add('border-yellow-500'); });
            dropZone.addEventListener('dragleave', () => dropZone.classList.remove('border-yellow-500'));
            dropZone.addEventListener('drop', (e) => {
                e.preventDefault();
                dropZone.classList.remove('border-yellow-500');
                if (e.dataTransfer.files.length) uploadGroundImage(e.dataTransfer.files[0]);
            });
            fileInput.addEventListener('change', (e) => {
                if (e.target.files.length) uploadGroundImage(e.target.files[0]);
            });
        }
    }

    async function uploadGroundImage(file) {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('category', 'image');

        const preview = document.getElementById('groundPhotoPreviewContainer');
        if (preview) {
            preview.innerHTML = '<span class="text-xs text-yellow-400">Uploading photo...</span>';
            preview.classList.remove('hidden');
        }

        try {
            const res = await fetch('/admin/api/upload', { method: 'POST', body: formData });
            const data = await res.json();
            if (res.ok && data.status === 'success') {
                state.uploadedGroundImg = data.file.url;
                if (preview) {
                    preview.innerHTML = `
                        <img src="${data.file.url}" class="w-16 h-16 rounded-xl object-cover border border-yellow-500">
                        <span class="text-xs text-emerald-400 font-medium">Photo Attached</span>
                    `;
                }
                showAdminToast('Ground photo uploaded.', 'success');
            } else {
                showAdminToast(data.message || 'Upload failed.', 'error');
                resetGroundPreview();
            }
        } catch (err) {
            showAdminToast(err.message, 'error');
            resetGroundPreview();
        }
    }

    function resetGroundPreview() {
        const preview = document.getElementById('groundPhotoPreviewContainer');
        if (preview) {
            preview.innerHTML = '';
            preview.classList.add('hidden');
        }
    }

    async function loadGrounds() {
        const grid = document.getElementById('groundsGridContainer');
        if (grid) {
            grid.innerHTML = `
                <div class="col-span-full text-center py-10 text-gray-400 text-xs">
                    <div class="w-5 h-5 border-2 border-yellow-500 border-t-transparent rounded-full animate-spin mx-auto mb-2"></div>
                    Loading grounds and courts...
                </div>
            `;
        }

        const params = new URLSearchParams({
            page: state.page,
            limit: state.limit,
            search: state.search
        });

        try {
            const res = await fetch(`/admin/api/crud/grounds?${params.toString()}`);
            const data = await res.json();
            if (data.status === 'success') {
                state.items = data.items || [];
                state.total = data.total || 0;
                renderGroundsCards();
            } else {
                if (grid) grid.innerHTML = `<div class="col-span-full text-center py-6 text-red-400 text-xs">${data.message}</div>`;
            }
        } catch (err) {
            if (grid) grid.innerHTML = `<div class="col-span-full text-center py-6 text-red-400 text-xs">${err.message}</div>`;
        }
        lucide.createIcons();
    }

    function renderGroundsCards() {
        const grid = document.getElementById('groundsGridContainer');
        const countBadge = document.getElementById('groundsCountBadge');
        if (!grid) return;

        if (countBadge) countBadge.innerText = `${state.total} Grounds`;

        if (state.items.length === 0) {
            grid.innerHTML = `<div class="col-span-full text-center py-12 text-gray-400 text-xs">No grounds or sports courts found.</div>`;
            return;
        }

        grid.innerHTML = state.items.map(g => {
            const id = g.ground_id || g.id || '-';
            const name = g.ground_name || g.name || 'Athletic Ground';
            const sport = g.sport_type || g.sport || 'Cricket Ground';
            const surface = g.surface || g.surface_type || 'Natural Turf';
            const floodlights = g.floodlights_available === 'Yes (Night Matches Allowed)' || g.floodlights === true;
            const img = g.image_url;

            return `
                <div class="ground-card-box">
                    <div class="ground-img-wrapper">
                        ${img ? `<img src="${img}" alt="${name}">` : '<i data-lucide="map" class="w-10 h-10 text-yellow-400 opacity-50"></i>'}
                        <span class="badge-surface absolute top-2.5 right-2.5">${surface}</span>
                    </div>
                    <div class="p-4 space-y-2">
                        <h4 class="text-sm font-bold text-white mb-0 truncate">${name}</h4>
                        <p class="text-xs text-gray-400 mb-0"><i data-lucide="activity" class="w-3.5 h-3.5 text-yellow-400 d-inline mr-1"></i>Sport: <strong class="text-gray-200">${sport}</strong></p>
                        <p class="text-xs text-gray-400 mb-0"><i data-lucide="sun" class="w-3.5 h-3.5 text-emerald-400 d-inline mr-1"></i>${floodlights ? 'Night Floodlights Enabled' : 'Daylight Only'}</p>
                        <div class="pt-3 border-t border-[#1F2937] flex justify-end gap-1.5">
                            <button class="p-1.5 rounded-lg bg-[#0F172A] border border-[#1F2937] text-gray-300 hover:text-white" onclick="window.editGround('${id}')">
                                <i data-lucide="edit-2" class="w-3.5 h-3.5"></i>
                            </button>
                            <button class="p-1.5 rounded-lg bg-[#0F172A] border border-[#1F2937] text-red-400 hover:bg-red-500/20" onclick="window.deleteGround('${id}')">
                                <i data-lucide="trash-2" class="w-3.5 h-3.5"></i>
                            </button>
                        </div>
                    </div>
                </div>
            `;
        }).join('');

        lucide.createIcons();
    }

    async function handleGroundFormSubmit(e) {
        e.preventDefault();
        const recordId = document.getElementById('groundFormRecordId').value;
        const name = document.getElementById('groundNameInput').value.trim();
        const sport = document.getElementById('groundSportInput').value.trim();
        const surface = document.getElementById('groundSurfaceInput').value.trim();

        const payload = {
            ground_id: recordId || `GND_${Date.now()}`,
            ground_name: name,
            sport_type: sport,
            surface: surface || 'Natural Turf',
            location: 'SVIT Campus',
            floodlights_available: 'Yes (Night Matches Allowed)',
            availability_status: 'Open for Practice',
            timings: '6:00 AM - 8:00 PM'
        };

        if (state.uploadedGroundImg) payload.image_url = state.uploadedGroundImg;

        const isEdit = Boolean(recordId);
        const url = isEdit ? `/admin/api/crud/grounds/${recordId}` : '/admin/api/crud/grounds';
        const method = isEdit ? 'PUT' : 'POST';

        try {
            const res = await fetch(url, {
                method: method,
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            const data = await res.json();
            if (res.ok && data.status === 'success') {
                showAdminToast(data.message || 'Ground facility saved successfully.', 'success');
                groundModal.hide();
                loadGrounds();
            } else {
                showAdminToast(data.message || 'Error saving ground.', 'error');
            }
        } catch (err) {
            showAdminToast(err.message, 'error');
        }
    }

    window.editGround = function(id) {
        const item = state.items.find(g => (g.ground_id || g.id) === id);
        if (!item) return;

        document.getElementById('groundModalTitle').innerText = 'Edit Ground Facility';
        document.getElementById('groundFormRecordId').value = id;
        document.getElementById('groundNameInput').value = item.ground_name || item.name || '';
        document.getElementById('groundSportInput').value = item.sport_type || item.sport || '';
        document.getElementById('groundSurfaceInput').value = item.surface || item.surface_type || '';

        state.uploadedGroundImg = item.image_url || null;
        if (item.image_url) {
            const preview = document.getElementById('groundPhotoPreviewContainer');
            if (preview) {
                preview.innerHTML = `<img src="${item.image_url}" class="w-16 h-16 rounded-xl object-cover border border-yellow-500">`;
                preview.classList.remove('hidden');
            }
        } else {
            resetGroundPreview();
        }

        groundModal.show();
    };

    window.deleteGround = function(id) {
        state.pendingDeleteId = id;
        document.getElementById('deleteGroundTargetId').innerText = id;
        deleteModal.show();
    };

    async function handleConfirmDelete() {
        if (!state.pendingDeleteId) return;

        try {
            const res = await fetch(`/admin/api/crud/grounds/${state.pendingDeleteId}`, { method: 'DELETE' });
            const data = await res.json();
            if (res.ok && data.status === 'success') {
                showAdminToast(data.message || 'Ground facility removed.', 'success');
                deleteModal.hide();
                loadGrounds();
            } else {
                showAdminToast(data.message || 'Failed to delete ground.', 'error');
            }
        } catch (err) {
            showAdminToast(err.message, 'error');
        }
    }
})();
