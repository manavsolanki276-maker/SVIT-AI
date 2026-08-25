/**
 * SVIT Admin - Page 15: Buses Fleet Controller
 * Handles bus vehicle fleet, driver contact records, route numbers,
 * capacity, status filtering, add/edit modal, and deletion.
 */

(function() {
    'use strict';

    const state = {
        search: '',
        status: '',
        page: 1,
        limit: 50,
        total: 0,
        items: [],
        pendingDeleteId: null
    };

    let busModal = null;
    let busViewModal = null;
    let busDeleteModal = null;
    let searchDebounce = null;

    document.addEventListener('DOMContentLoaded', function() {
        const formEl = document.getElementById('busFormModal');
        const viewEl = document.getElementById('busViewModal');
        const delEl = document.getElementById('busDeleteModal');

        if (formEl) busModal = new bootstrap.Modal(formEl);
        if (viewEl) busViewModal = new bootstrap.Modal(viewEl);
        if (delEl) busDeleteModal = new bootstrap.Modal(delEl);

        bindEvents();
        loadBuses();
    });

    function bindEvents() {
        const searchInput = document.getElementById('busSearchInput');
        if (searchInput) {
            searchInput.addEventListener('input', (e) => {
                clearTimeout(searchDebounce);
                searchDebounce = setTimeout(() => {
                    state.search = e.target.value.trim();
                    state.page = 1;
                    loadBuses();
                }, 300);
            });
        }

        const refreshBtn = document.getElementById('refreshBusesBtn');
        if (refreshBtn) refreshBtn.addEventListener('click', loadBuses);

        const limitSelect = document.getElementById('pageLimitSelect');
        if (limitSelect) {
            limitSelect.addEventListener('change', (e) => {
                state.limit = parseInt(e.target.value, 10) || 50;
                state.page = 1;
                loadBuses();
            });
        }

        const prevBtn = document.getElementById('prevPageBtn');
        if (prevBtn) {
            prevBtn.addEventListener('click', () => {
                if (state.page > 1) {
                    state.page--;
                    loadBuses();
                }
            });
        }

        const nextBtn = document.getElementById('nextPageBtn');
        if (nextBtn) {
            nextBtn.addEventListener('click', () => {
                const totalPages = Math.ceil(state.total / state.limit) || 1;
                if (state.page < totalPages) {
                    state.page++;
                    loadBuses();
                }
            });
        }

        const createBtn = document.getElementById('openCreateBusModalBtn');
        if (createBtn) {
            createBtn.addEventListener('click', () => {
                document.getElementById('busModalTitle').innerText = 'Register Campus Bus';
                document.getElementById('busFormRecordId').value = '';
                document.getElementById('busForm').reset();
                document.getElementById('busNumberInput').disabled = false;
                busModal.show();
            });
        }

        const form = document.getElementById('busForm');
        if (form) form.addEventListener('submit', handleBusFormSubmit);

        const confirmDeleteBtn = document.getElementById('confirmDeleteBusBtn');
        if (confirmDeleteBtn) confirmDeleteBtn.addEventListener('click', handleConfirmDelete);
    }

    async function loadBuses() {
        const tbody = document.getElementById('busesTableBody');
        if (!tbody) return;

        tbody.innerHTML = `
            <tr>
                <td colspan="7" class="text-center py-10 text-gray-400 text-xs">
                    <div class="w-5 h-5 border-2 border-cyan-500 border-t-transparent rounded-full animate-spin mx-auto mb-2"></div>
                    Loading transit fleet...
                </td>
            </tr>
        `;

        const params = new URLSearchParams({
            page: state.page,
            limit: state.limit,
            search: state.search
        });

        try {
            const res = await fetch(`/admin/api/crud/transport?${params.toString()}`);
            const data = await res.json();
            if (data.status === 'success') {
                state.items = data.items || [];
                state.total = data.total || 0;
                renderBusesTable();
                renderPagination(data);
            } else {
                tbody.innerHTML = `<tr><td colspan="7" class="text-center py-6 text-red-400 text-xs">${data.message}</td></tr>`;
            }
        } catch (err) {
            tbody.innerHTML = `<tr><td colspan="7" class="text-center py-6 text-red-400 text-xs">${err.message}</td></tr>`;
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
                btn.className = `px-2 py-1 rounded-lg text-xs font-semibold transition ${state.page === i ? 'bg-cyan-600 text-white' : 'bg-[#111827] border border-[#1F2937] text-gray-400 hover:text-white'}`;
                btn.onclick = () => {
                    state.page = i;
                    loadBuses();
                };
                numbersContainer.appendChild(btn);
            }
        }
    }

    function renderBusesTable() {
        const tbody = document.getElementById('busesTableBody');
        const countBadge = document.getElementById('busesCountBadge');
        if (countBadge) countBadge.innerText = `${state.total} Buses`;

        if (state.items.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="7" class="text-center py-12 text-gray-400 text-xs">
                        <i data-lucide="bus" class="w-8 h-8 mx-auto mb-2 text-gray-600"></i>
                        <p class="mb-0">No buses registered in the transit fleet.</p>
                    </td>
                </tr>
            `;
            return;
        }

        tbody.innerHTML = state.items.map(b => {
            const routeNo = b.route_no || b.bus_number || b.id || 'Route 1';
            const name = b.route_name || b.name || 'Transit Route';
            const plate = b.vehicle_number || b.registration_no || 'GJ-06-XX';
            const driver = b.driver_name || 'Driver In-Charge';
            const phone = b.driver_contact || b.phone || '-';
            const seats = b.capacity || 50;
            const id = b.id || routeNo;

            return `
                <tr>
                    <td>
                        <div class="flex items-center gap-2.5">
                            <div class="bus-icon-badge">
                                <i data-lucide="bus" class="w-4 h-4"></i>
                            </div>
                            <div>
                                <span class="badge-bus-route mb-0.5 d-inline-block">${routeNo}</span>
                                <p class="text-xs font-bold text-white mb-0">${name}</p>
                            </div>
                        </div>
                    </td>
                    <td class="font-mono text-cyan-400 font-bold text-xs">${plate}</td>
                    <td class="text-gray-300 text-xs">${driver}</td>
                    <td class="text-gray-400 text-xs font-mono">${phone}</td>
                    <td class="text-gray-300 text-xs">${seats} Seats</td>
                    <td>
                        <span class="px-2 py-0.5 rounded text-[10px] bg-emerald-500/20 text-emerald-300 font-semibold flex items-center gap-1 w-max">
                            <span class="w-1.5 h-1.5 rounded-full bg-emerald-400"></span> Active Fleet
                        </span>
                    </td>
                    <td class="text-end">
                        <div class="inline-flex items-center gap-1.5">
                            <button class="p-1.5 rounded-lg bg-[#0F172A] border border-[#1F2937] text-gray-300 hover:text-white" onclick="window.viewBus('${id}')" title="View Bus">
                                <i data-lucide="eye" class="w-3.5 h-3.5"></i>
                            </button>
                            <button class="p-1.5 rounded-lg bg-[#0F172A] border border-[#1F2937] text-gray-300 hover:text-white" onclick="window.editBus('${id}')" title="Edit Bus">
                                <i data-lucide="edit-2" class="w-3.5 h-3.5"></i>
                            </button>
                            <button class="p-1.5 rounded-lg bg-[#0F172A] border border-[#1F2937] text-red-400 hover:bg-red-500/20" onclick="window.deleteBus('${id}')" title="Delete">
                                <i data-lucide="trash-2" class="w-3.5 h-3.5"></i>
                            </button>
                        </div>
                    </td>
                </tr>
            `;
        }).join('');
    }

    async function handleBusFormSubmit(e) {
        e.preventDefault();
        const recordId = document.getElementById('busFormRecordId').value;
        const payload = {
            id: recordId || `BUS-${Date.now()}`,
            route_no: document.getElementById('busNumberInput').value.trim(),
            route_name: document.getElementById('busRouteNameInput').value.trim(),
            vehicle_number: document.getElementById('busPlateInput').value.trim(),
            driver_name: document.getElementById('busDriverNameInput').value.trim(),
            driver_contact: document.getElementById('busDriverPhoneInput').value.trim(),
            capacity: parseInt(document.getElementById('busCapacityInput').value, 10) || 50
        };

        const isEdit = Boolean(recordId);
        const url = isEdit ? `/admin/api/crud/transport/${recordId}` : '/admin/api/crud/transport';
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
                busModal.hide();
                loadBuses();
            } else {
                showAdminToast(data.message || 'Error saving bus record.', 'error');
            }
        } catch (err) {
            showAdminToast(err.message, 'error');
        }
    }

    window.editBus = function(id) {
        const item = state.items.find(b => String(b.id) === String(id) || b.route_no === id);
        if (!item) return;

        document.getElementById('busModalTitle').innerText = 'Edit Bus Vehicle';
        document.getElementById('busFormRecordId').value = id;
        document.getElementById('busNumberInput').value = item.route_no || item.bus_number || '';
        document.getElementById('busRouteNameInput').value = item.route_name || '';
        document.getElementById('busPlateInput').value = item.vehicle_number || item.registration_no || '';
        document.getElementById('busDriverNameInput').value = item.driver_name || '';
        document.getElementById('busDriverPhoneInput').value = item.driver_contact || item.phone || '';
        document.getElementById('busCapacityInput').value = item.capacity || 50;

        busModal.show();
    };

    window.viewBus = function(id) {
        const item = state.items.find(b => String(b.id) === String(id) || b.route_no === id);
        if (!item) return;

        const container = document.getElementById('busViewContent');
        if (!container) return;

        container.innerHTML = `
            <div class="space-y-4">
                <div class="flex items-center gap-3.5 p-4 rounded-2xl bg-[#0F172A] border border-[#1F2937]">
                    <div class="bus-icon-badge w-14 h-14 rounded-2xl font-bold text-lg">
                        <i data-lucide="bus" class="w-7 h-7"></i>
                    </div>
                    <div>
                        <span class="badge-bus-route">${item.route_no || 'Route'}</span>
                        <h3 class="text-base font-bold text-white mt-1 mb-0">${item.route_name || 'Campus Transit'}</h3>
                        <p class="text-xs text-cyan-400 font-mono mb-0">${item.vehicle_number || 'GJ-06-XX'}</p>
                    </div>
                </div>
                <div class="grid grid-cols-2 gap-3 text-xs">
                    <div class="p-2.5 rounded-lg bg-[#0F172A] border border-[#1F2937]">
                        <span class="text-gray-500 block text-[10px]">DRIVER NAME</span>
                        <span class="text-white font-medium">${item.driver_name || '-'}</span>
                    </div>
                    <div class="p-2.5 rounded-lg bg-[#0F172A] border border-[#1F2937]">
                        <span class="text-gray-500 block text-[10px]">DRIVER PHONE</span>
                        <span class="text-cyan-300 font-mono font-medium">${item.driver_contact || item.phone || '-'}</span>
                    </div>
                </div>
            </div>
        `;

        busViewModal.show();
    };

    window.deleteBus = function(id) {
        state.pendingDeleteId = id;
        document.getElementById('deleteBusTargetId').innerText = id;
        busDeleteModal.show();
    };

    async function handleConfirmDelete() {
        if (!state.pendingDeleteId) return;

        try {
            const res = await fetch(`/admin/api/crud/transport/${state.pendingDeleteId}`, { method: 'DELETE' });
            const data = await res.json();
            if (res.ok && data.status === 'success') {
                showAdminToast(data.message, 'success');
                busDeleteModal.hide();
                loadBuses();
            } else {
                showAdminToast(data.message || 'Failed to delete bus record.', 'error');
            }
        } catch (err) {
            showAdminToast(err.message, 'error');
        }
    }
})();
