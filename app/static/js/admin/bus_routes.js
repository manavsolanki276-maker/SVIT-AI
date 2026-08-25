/**
 * SVIT Admin - Page 16: Bus Routes Controller
 * Features visual route stop progression timeline, starting/ending point indicators,
 * morning/evening departure schedule, and route editing.
 */

(function() {
    'use strict';

    const state = {
        search: '',
        items: [],
        pendingDeleteId: null
    };

    let routeModal = null;
    let deleteModal = null;
    let searchDebounce = null;

    document.addEventListener('DOMContentLoaded', function() {
        const formEl = document.getElementById('routeFormModal');
        const delEl = document.getElementById('routeDeleteModal');

        if (formEl) routeModal = new bootstrap.Modal(formEl);
        if (delEl) deleteModal = new bootstrap.Modal(delEl);

        bindEvents();
        loadBusRoutes();
    });

    function bindEvents() {
        const searchInput = document.getElementById('routeSearchInput');
        if (searchInput) {
            searchInput.addEventListener('input', (e) => {
                clearTimeout(searchDebounce);
                searchDebounce = setTimeout(() => {
                    state.search = e.target.value.trim().toLowerCase();
                    renderRoutes();
                }, 300);
            });
        }

        const refreshBtn = document.getElementById('refreshRoutesBtn');
        if (refreshBtn) refreshBtn.addEventListener('click', loadBusRoutes);

        const createBtn = document.getElementById('openCreateRouteModalBtn');
        if (createBtn) {
            createBtn.addEventListener('click', () => {
                document.getElementById('routeModalTitle').innerText = 'Add Transit Route';
                document.getElementById('routeFormRecordId').value = '';
                document.getElementById('routeForm').reset();
                routeModal.show();
            });
        }

        const form = document.getElementById('routeForm');
        if (form) form.addEventListener('submit', handleRouteFormSubmit);

        const confirmDeleteBtn = document.getElementById('confirmDeleteRouteBtn');
        if (confirmDeleteBtn) confirmDeleteBtn.addEventListener('click', handleConfirmDelete);
    }

    async function loadBusRoutes() {
        const container = document.getElementById('routesListContainer');
        if (!container) return;

        container.innerHTML = `
            <div class="text-center py-12 text-gray-400 text-xs">
                <div class="w-5 h-5 border-2 border-cyan-500 border-t-transparent rounded-full animate-spin mx-auto mb-2"></div>
                Loading bus transit routes & stop timelines...
            </div>
        `;

        try {
            const res = await fetch('/admin/api/crud/transport?limit=500');
            const data = await res.json();
            if (data.status === 'success') {
                state.items = data.items || [];
                renderRoutes();
            } else {
                container.innerHTML = `<div class="text-center py-6 text-red-400 text-xs">${data.message}</div>`;
            }
        } catch (err) {
            container.innerHTML = `<div class="text-center py-6 text-red-400 text-xs">${err.message}</div>`;
        }
        lucide.createIcons();
    }

    function renderRoutes() {
        const container = document.getElementById('routesListContainer');
        const countBadge = document.getElementById('routesCountBadge');
        if (countBadge) countBadge.innerText = `${state.items.length} Routes`;

        const filtered = state.items.filter(r => {
            if (!state.search) return true;
            return (r.route_name || '').toLowerCase().includes(state.search) ||
                   (r.route_no || '').toLowerCase().includes(state.search);
        });

        if (filtered.length === 0) {
            container.innerHTML = `<div class="text-center py-12 text-gray-400 text-xs">No transit routes found.</div>`;
            return;
        }

        container.innerHTML = filtered.map(r => {
            const routeNo = r.route_no || r.bus_number || 'Route 1';
            const name = r.route_name || 'Vasad Campus Express';
            const stops = r.stops && Array.isArray(r.stops) ? r.stops : [
                { name: 'Starting Point', time: '07:15 AM' },
                { name: 'City Center Stop', time: '07:35 AM' },
                { name: 'Highway Junction', time: '07:55 AM' },
                { name: 'SVIT Vasad Campus', time: '08:20 AM' }
            ];

            return `
                <div class="route-card-item space-y-4">
                    <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-[#1F2937]">
                        <div class="flex items-center gap-3">
                            <span class="px-2.5 py-1 rounded-lg text-xs font-bold bg-cyan-500/20 text-cyan-300 border border-cyan-500/30">
                                ${routeNo}
                            </span>
                            <div>
                                <h3 class="text-sm font-bold text-white mb-0.5">${name}</h3>
                                <p class="text-xs text-gray-400 mb-0">Driver: <strong class="text-white">${r.driver_name || 'Assigned Driver'}</strong> (${r.driver_contact || '-'})</p>
                            </div>
                        </div>
                        <div class="flex items-center gap-2">
                            <span class="text-xs text-gray-400">Morning Dep: <strong class="text-cyan-400">07:15 AM</strong></span>
                            <span class="text-gray-600">•</span>
                            <span class="text-xs text-gray-400">Evening Dep: <strong class="text-cyan-400">04:45 PM</strong></span>
                            <button class="p-1.5 rounded-lg bg-[#0F172A] border border-[#1F2937] text-gray-300 hover:text-white ms-2" onclick="window.editRoute('${r.id}')" title="Edit Route">
                                <i data-lucide="edit-2" class="w-3.5 h-3.5"></i>
                            </button>
                            <button class="p-1.5 rounded-lg bg-[#0F172A] border border-[#1F2937] text-red-400 hover:bg-red-500/20" onclick="window.deleteRoute('${r.id}')" title="Delete Route">
                                <i data-lucide="trash-2" class="w-3.5 h-3.5"></i>
                            </button>
                        </div>
                    </div>

                    <!-- Visual Timeline of Stops -->
                    <div>
                        <span class="text-[11px] uppercase font-bold text-gray-400 block mb-2">Transit Stops Progression:</span>
                        <div class="route-timeline-container custom-scrollbar">
                            ${stops.map((st, idx) => `
                                <div class="route-step-node">
                                    <div class="route-step-dot">${idx + 1}</div>
                                    <span class="text-xs font-bold text-white mt-1.5 text-center truncate max-w-[120px]">${st.name || st}</span>
                                    <span class="text-[10px] text-cyan-300 font-mono">${st.time || ''}</span>
                                </div>
                            `).join('')}
                        </div>
                    </div>
                </div>
            `;
        }).join('');

        lucide.createIcons();
    }

    async function handleRouteFormSubmit(e) {
        e.preventDefault();
        const recordId = document.getElementById('routeFormRecordId').value;
        const payload = {
            id: recordId || `ROUTE-${Date.now()}`,
            route_no: document.getElementById('routeNameNumInput').value.trim(),
            route_name: document.getElementById('routeFullNameInput').value.trim(),
            driver_name: document.getElementById('routeDriverInput').value.trim(),
            driver_contact: document.getElementById('routePhoneInput').value.trim()
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
                routeModal.hide();
                loadBusRoutes();
            } else {
                showAdminToast(data.message || 'Error saving route.', 'error');
            }
        } catch (err) {
            showAdminToast(err.message, 'error');
        }
    }

    window.editRoute = function(id) {
        const item = state.items.find(r => String(r.id) === String(id));
        if (!item) return;

        document.getElementById('routeModalTitle').innerText = 'Edit Transit Route';
        document.getElementById('routeFormRecordId').value = id;
        document.getElementById('routeNameNumInput').value = item.route_no || item.bus_number || '';
        document.getElementById('routeFullNameInput').value = item.route_name || '';
        document.getElementById('routeDriverInput').value = item.driver_name || '';
        document.getElementById('routePhoneInput').value = item.driver_contact || '';

        routeModal.show();
    };

    window.deleteRoute = function(id) {
        state.pendingDeleteId = id;
        document.getElementById('deleteRouteTargetId').innerText = id;
        deleteModal.show();
    };

    async function handleConfirmDelete() {
        if (!state.pendingDeleteId) return;

        try {
            const res = await fetch(`/admin/api/crud/transport/${state.pendingDeleteId}`, { method: 'DELETE' });
            const data = await res.json();
            if (res.ok && data.status === 'success') {
                showAdminToast(data.message, 'success');
                deleteModal.hide();
                loadBusRoutes();
            } else {
                showAdminToast(data.message || 'Delete failed.', 'error');
            }
        } catch (err) {
            showAdminToast(err.message, 'error');
        }
    }
})();
