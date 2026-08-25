/**
 * SVIT Admin - Page 25: Food Items Roster Controller
 * Handles food inventory pricing table, category filters, and quick availability updates.
 */

(function() {
    'use strict';

    const state = {
        search: '',
        category: '',
        page: 1,
        limit: 50,
        total: 0,
        items: [],
        pendingDeleteId: null
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
        loadFoodItems();
    });

    function bindEvents() {
        const searchInput = document.getElementById('foodSearchInput');
        if (searchInput) {
            searchInput.addEventListener('input', (e) => {
                clearTimeout(searchDebounce);
                searchDebounce = setTimeout(() => {
                    state.search = e.target.value.trim();
                    state.page = 1;
                    loadFoodItems();
                }, 300);
            });
        }

        const catFilter = document.getElementById('foodCatFilter');
        if (catFilter) {
            catFilter.addEventListener('change', (e) => {
                state.category = e.target.value;
                state.page = 1;
                loadFoodItems();
            });
        }

        const refreshBtn = document.getElementById('refreshFoodBtn');
        if (refreshBtn) refreshBtn.addEventListener('click', loadFoodItems);

        const createBtn = document.getElementById('openCreateFoodModalBtn');
        if (createBtn) {
            createBtn.addEventListener('click', () => {
                document.getElementById('foodModalTitle').innerText = 'Add Food Item';
                document.getElementById('foodFormRecordId').value = '';
                document.getElementById('foodItemForm').reset();
                document.getElementById('foodIdInput').disabled = false;
                foodModal.show();
            });
        }

        const form = document.getElementById('foodItemForm');
        if (form) form.addEventListener('submit', handleFoodFormSubmit);

        const confirmDeleteBtn = document.getElementById('confirmDeleteFoodBtn');
        if (confirmDeleteBtn) confirmDeleteBtn.addEventListener('click', handleConfirmDelete);
    }

    async function loadFoodItems() {
        const tbody = document.getElementById('foodItemsTableBody');
        if (!tbody) return;

        tbody.innerHTML = `
            <tr>
                <td colspan="6" class="text-center py-10 text-gray-400 text-xs">
                    <div class="w-5 h-5 border-2 border-orange-500 border-t-transparent rounded-full animate-spin mx-auto mb-2"></div>
                    Loading food items...
                </td>
            </tr>
        `;

        const params = new URLSearchParams({
            page: state.page,
            limit: state.limit,
            search: state.search
        });
        if (state.category) params.append('filter_category', state.category);

        try {
            const res = await fetch(`/admin/api/crud/canteen?${params.toString()}`);
            const data = await res.json();
            if (data.status === 'success') {
                state.items = data.items || [];
                state.total = data.total || 0;
                renderFoodTable();
            } else {
                tbody.innerHTML = `<tr><td colspan="6" class="text-center py-6 text-red-400 text-xs">${data.message}</td></tr>`;
            }
        } catch (err) {
            tbody.innerHTML = `<tr><td colspan="6" class="text-center py-6 text-red-400 text-xs">${err.message}</td></tr>`;
        }
        lucide.createIcons();
    }

    function renderFoodTable() {
        const tbody = document.getElementById('foodItemsTableBody');
        const countBadge = document.getElementById('foodCountBadge');
        if (countBadge) countBadge.innerText = `${state.total} Items`;

        if (state.items.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="6" class="text-center py-12 text-gray-400 text-xs">
                        <i data-lucide="utensils" class="w-8 h-8 mx-auto mb-2 text-gray-600"></i>
                        <p class="mb-0">No food items found.</p>
                    </td>
                </tr>
            `;
            return;
        }

        tbody.innerHTML = state.items.map(f => {
            const id = f.item_id || f.id || '-';
            const name = f.item_name || f.name || 'Dish';
            const cat = f.category || 'Breakfast';
            const price = f.price || 35;
            const isAvail = f.is_available !== false;

            return `
                <tr>
                    <td>
                        <span class="font-mono text-orange-400 font-bold text-xs">${id}</span>
                    </td>
                    <td class="font-bold text-white text-xs">${name}</td>
                    <td><span class="px-2 py-0.5 rounded text-[10px] bg-orange-500/20 text-orange-300 font-semibold">${cat}</span></td>
                    <td class="font-mono text-white font-bold text-xs">₹ ${price}</td>
                    <td>
                        <span class="px-2 py-0.5 rounded text-[10px] ${isAvail ? 'bg-emerald-500/20 text-emerald-300' : 'bg-red-500/20 text-red-300'} font-semibold">
                            ${isAvail ? 'In Stock' : 'Sold Out'}
                        </span>
                    </td>
                    <td class="text-end">
                        <div class="inline-flex items-center gap-1.5">
                            <button class="p-1.5 rounded-lg bg-[#0F172A] border border-[#1F2937] text-gray-300 hover:text-white" onclick="window.editFood('${id}')" title="Edit Item">
                                <i data-lucide="edit-2" class="w-3.5 h-3.5"></i>
                            </button>
                            <button class="p-1.5 rounded-lg bg-[#0F172A] border border-[#1F2937] text-red-400 hover:bg-red-500/20" onclick="window.deleteFood('${id}')" title="Delete">
                                <i data-lucide="trash-2" class="w-3.5 h-3.5"></i>
                            </button>
                        </div>
                    </td>
                </tr>
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
                loadFoodItems();
            } else {
                showAdminToast(data.message || 'Error saving dish.', 'error');
            }
        } catch (err) {
            showAdminToast(err.message, 'error');
        }
    }

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
                loadFoodItems();
            } else {
                showAdminToast(data.message || 'Delete failed.', 'error');
            }
        } catch (err) {
            showAdminToast(err.message, 'error');
        }
    }
})();
