/**
 * SVIT Admin - Page 24: Canteen Menu Controller (Visual Cards)
 * Displays interactive dish cards categorized by Breakfast, Lunch, Snacks, Beverages, etc.
 * Supports availability toggle, price updates, food photo upload, add/edit/delete.
 */

(function() {
    'use strict';

    const state = {
        category: '',
        search: '',
        items: [],
        pendingDeleteId: null,
        uploadedFoodImg: null
    };

    let foodModal = null;
    let deleteModal = null;
    let searchDebounce = null;

    document.addEventListener('DOMContentLoaded', function() {
        const formEl = document.getElementById('foodItemModal');
        const delEl = document.getElementById('foodItemDeleteModal');

        if (formEl) foodModal = new bootstrap.Modal(formEl);
        if (delEl) deleteModal = new bootstrap.Modal(delEl);

        bindEvents();
        setupFoodUpload();
        loadFoodMenu();
    });

    function bindEvents() {
        const catButtons = document.querySelectorAll('.food-cat-btn');
        catButtons.forEach(btn => {
            btn.addEventListener('click', () => {
                catButtons.forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                state.category = btn.getAttribute('data-category');
                renderFoodCards();
            });
        });

        const searchInput = document.getElementById('foodSearchInput');
        if (searchInput) {
            searchInput.addEventListener('input', (e) => {
                clearTimeout(searchDebounce);
                searchDebounce = setTimeout(() => {
                    state.search = e.target.value.trim().toLowerCase();
                    renderFoodCards();
                }, 300);
            });
        }

        const refreshBtn = document.getElementById('refreshMenuBtn');
        if (refreshBtn) refreshBtn.addEventListener('click', loadFoodMenu);

        const createBtn = document.getElementById('openCreateFoodModalBtn');
        if (createBtn) {
            createBtn.addEventListener('click', () => {
                document.getElementById('foodModalTitle').innerText = 'Add Food Item';
                document.getElementById('foodFormRecordId').value = '';
                document.getElementById('foodItemForm').reset();
                state.uploadedFoodImg = null;
                resetFoodPreview();
                foodModal.show();
            });
        }

        const form = document.getElementById('foodItemForm');
        if (form) form.addEventListener('submit', handleFoodFormSubmit);

        const confirmDeleteBtn = document.getElementById('confirmDeleteFoodBtn');
        if (confirmDeleteBtn) confirmDeleteBtn.addEventListener('click', handleConfirmDelete);
    }

    function setupFoodUpload() {
        const dropZone = document.getElementById('foodPhotoDropZone');
        const fileInput = document.getElementById('foodPhotoInput');

        if (dropZone && fileInput) {
            dropZone.addEventListener('click', () => fileInput.click());
            dropZone.addEventListener('dragover', (e) => { e.preventDefault(); dropZone.classList.add('border-orange-500'); });
            dropZone.addEventListener('dragleave', () => dropZone.classList.remove('border-orange-500'));
            dropZone.addEventListener('drop', (e) => {
                e.preventDefault();
                dropZone.classList.remove('border-orange-500');
                if (e.dataTransfer.files.length) uploadFoodImage(e.dataTransfer.files[0]);
            });
            fileInput.addEventListener('change', (e) => {
                if (e.target.files.length) uploadFoodImage(e.target.files[0]);
            });
        }
    }

    async function uploadFoodImage(file) {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('category', 'image');

        const preview = document.getElementById('foodPhotoPreviewContainer');
        if (preview) {
            preview.innerHTML = '<span class="text-xs text-orange-400">Uploading photo...</span>';
            preview.classList.remove('hidden');
        }

        try {
            const res = await fetch('/admin/api/upload', { method: 'POST', body: formData });
            const data = await res.json();
            if (res.ok && data.status === 'success') {
                state.uploadedFoodImg = data.file.url;
                if (preview) {
                    preview.innerHTML = `
                        <img src="${data.file.url}" class="w-16 h-16 rounded-xl object-cover border border-orange-500">
                        <span class="text-xs text-emerald-400 font-medium">Photo Attached</span>
                    `;
                }
                showAdminToast('Dish photo uploaded.', 'success');
            } else {
                showAdminToast(data.message || 'Upload failed.', 'error');
                resetFoodPreview();
            }
        } catch (err) {
            showAdminToast(err.message, 'error');
            resetFoodPreview();
        }
    }

    function resetFoodPreview() {
        const preview = document.getElementById('foodPhotoPreviewContainer');
        if (preview) {
            preview.innerHTML = '';
            preview.classList.add('hidden');
        }
    }

    async function loadFoodMenu() {
        const grid = document.getElementById('canteenMenuGrid');
        if (!grid) return;

        grid.innerHTML = `
            <div class="col-span-full text-center py-12 text-gray-400 text-xs">
                <div class="w-5 h-5 border-2 border-orange-500 border-t-transparent rounded-full animate-spin mx-auto mb-2"></div>
                Loading canteen menu dishes...
            </div>
        `;

        try {
            const res = await fetch('/admin/api/crud/canteen?limit=500');
            const data = await res.json();
            if (data.status === 'success') {
                state.items = data.items || [];
                renderFoodCards();
            } else {
                grid.innerHTML = `<div class="col-span-full text-center py-6 text-red-400 text-xs">${data.message}</div>`;
            }
        } catch (err) {
            grid.innerHTML = `<div class="col-span-full text-center py-6 text-red-400 text-xs">${err.message}</div>`;
        }
        lucide.createIcons();
    }

    function renderFoodCards() {
        const grid = document.getElementById('canteenMenuGrid');
        const countBadge = document.getElementById('menuCountBadge');
        if (!grid) return;

        const filtered = state.items.filter(item => {
            const matchSearch = !state.search ||
                (item.item_name || item.name || '').toLowerCase().includes(state.search);
            const matchCat = !state.category || item.category === state.category;
            return matchSearch && matchCat;
        });

        if (countBadge) countBadge.innerText = `${filtered.length} Items`;

        if (filtered.length === 0) {
            grid.innerHTML = `<div class="col-span-full text-center py-12 text-gray-400 text-xs">No food items found matching this category.</div>`;
            return;
        }

        grid.innerHTML = filtered.map(f => {
            const id = f.item_id || f.id || '-';
            const name = f.item_name || f.name || 'Dish';
            const price = f.price || 40;
            const cat = f.category || 'Breakfast';
            const isAvail = f.is_available !== false;
            const img = f.image_url;

            return `
                <div class="food-card-box">
                    <div class="food-card-img-wrapper">
                        ${img ? `<img src="${img}" alt="${name}">` : '<i data-lucide="utensils" class="w-8 h-8 text-orange-400 opacity-50"></i>'}
                        <div class="absolute top-2.5 left-2.5 bg-[#0F172A]/80 backdrop-blur px-2 py-1 rounded-lg flex items-center gap-1.5">
                            <span class="veg-symbol"></span>
                            <span class="text-[10px] font-bold text-emerald-400">100% VEG</span>
                        </div>
                        <span class="absolute top-2.5 right-2.5 px-2 py-0.5 rounded text-[10px] font-bold ${isAvail ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30' : 'bg-red-500/20 text-red-300 border border-red-500/30'}">
                            ${isAvail ? 'In Stock' : 'Sold Out'}
                        </span>
                    </div>

                    <div class="p-4 space-y-2">
                        <div class="flex items-start justify-between gap-2">
                            <div>
                                <span class="text-[10px] font-semibold text-orange-400 uppercase tracking-wider block">${cat}</span>
                                <h4 class="text-sm font-bold text-white mb-0">${name}</h4>
                            </div>
                            <span class="text-base font-black text-white font-mono">₹ ${price}</span>
                        </div>

                        <div class="pt-3 border-t border-[#1F2937] flex items-center justify-between gap-2">
                            <button class="px-2.5 py-1 rounded-lg text-xs font-semibold ${isAvail ? 'bg-amber-600/20 text-amber-300 hover:bg-amber-600/30' : 'bg-emerald-600/20 text-emerald-300 hover:bg-emerald-600/30'}" onclick="window.toggleFoodAvailability('${id}', ${!isAvail})">
                                ${isAvail ? 'Mark Sold Out' : 'Mark In Stock'}
                            </button>
                            <div class="flex items-center gap-1">
                                <button class="p-1.5 rounded-lg bg-[#0F172A] border border-[#1F2937] text-gray-300 hover:text-white" onclick="window.editFood('${id}')" title="Edit Item">
                                    <i data-lucide="edit-2" class="w-3.5 h-3.5"></i>
                                </button>
                                <button class="p-1.5 rounded-lg bg-[#0F172A] border border-[#1F2937] text-red-400 hover:bg-red-500/20" onclick="window.deleteFood('${id}')" title="Delete">
                                    <i data-lucide="trash-2" class="w-3.5 h-3.5"></i>
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            `;
        }).join('');

        lucide.createIcons();
    }

    async function handleFoodFormSubmit(e) {
        e.preventDefault();
        const recordId = document.getElementById('foodFormRecordId').value;
        const payload = {
            item_id: document.getElementById('foodIdInput').value.trim(),
            item_name: document.getElementById('foodNameInput').value.trim(),
            category: document.getElementById('foodCategorySelect').value,
            price: parseFloat(document.getElementById('foodPriceInput').value) || 30,
            is_available: document.getElementById('foodAvailSelect').value === 'true'
        };

        if (state.uploadedFoodImg) payload.image_url = state.uploadedFoodImg;

        const isEdit = Boolean(recordId);
        const url = isEdit ? `/admin/api/crud/canteen/${recordId}` : '/admin/api/crud/canteen';
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
                foodModal.hide();
                loadFoodMenu();
            } else {
                showAdminToast(data.message || 'Error saving dish.', 'error');
            }
        } catch (err) {
            showAdminToast(err.message, 'error');
        }
    }

    window.toggleFoodAvailability = async function(id, newState) {
        try {
            const res = await fetch(`/admin/api/crud/canteen/${id}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ is_available: newState })
            });
            const data = await res.json();
            if (res.ok && data.status === 'success') {
                showAdminToast('Item availability updated.', 'success');
                loadFoodMenu();
            } else {
                showAdminToast(data.message || 'Update failed.', 'error');
            }
        } catch (err) {
            showAdminToast(err.message, 'error');
        }
    };

    window.editFood = function(id) {
        const item = state.items.find(f => (f.item_id || f.id) === id);
        if (!item) return;

        document.getElementById('foodModalTitle').innerText = 'Edit Food Item';
        document.getElementById('foodFormRecordId').value = id;
        document.getElementById('foodIdInput').value = item.item_id || id;
        document.getElementById('foodIdInput').disabled = true;
        document.getElementById('foodNameInput').value = item.item_name || item.name || '';
        document.getElementById('foodCategorySelect').value = item.category || 'Breakfast';
        document.getElementById('foodPriceInput').value = item.price || 30;
        document.getElementById('foodAvailSelect').value = item.is_available !== false ? 'true' : 'false';

        state.uploadedFoodImg = item.image_url || null;
        if (item.image_url) {
            const preview = document.getElementById('foodPhotoPreviewContainer');
            if (preview) {
                preview.innerHTML = `<img src="${item.image_url}" class="w-16 h-16 rounded-xl object-cover border border-orange-500">`;
                preview.classList.remove('hidden');
            }
        } else {
            resetFoodPreview();
        }

        foodModal.show();
    };

    window.deleteFood = function(id) {
        state.pendingDeleteId = id;
        document.getElementById('deleteFoodTargetId').innerText = id;
        deleteModal.show();
    };

    async function handleConfirmDelete() {
        if (!state.pendingDeleteId) return;

        try {
            const res = await fetch(`/admin/api/crud/canteen/${state.pendingDeleteId}`, { method: 'DELETE' });
            const data = await res.json();
            if (res.ok && data.status === 'success') {
                showAdminToast(data.message, 'success');
                deleteModal.hide();
                loadFoodMenu();
            } else {
                showAdminToast(data.message || 'Delete failed.', 'error');
            }
        } catch (err) {
            showAdminToast(err.message, 'error');
        }
    }
})();
