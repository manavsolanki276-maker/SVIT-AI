/**
 * SVIT Admin - Page 17: Bus Stops Controller
 * Handles bus pickup stops, landmark notes, morning/evening timings,
 * and associated transit route filtering.
 */

(function() {
    'use strict';

    const state = {
        search: '',
        routeFilter: '',
        page: 1,
        limit: 20,
        total: 0,
        items: [],
        pendingDeleteId: null
    };

    let stopModal = null;
    let deleteModal = null;
    let searchDebounce = null;

    document.addEventListener('DOMContentLoaded', function() {
        const formEl = document.getElementById('stopFormModal');
        const delEl = document.getElementById('stopDeleteModal');

        if (formEl) stopModal = new bootstrap.Modal(formEl);
        if (delEl) deleteModal = new bootstrap.Modal(delEl);

        bindEvents();
        loadBusStops();
    });

    function bindEvents() {
        const searchInput = document.getElementById('stopSearchInput');
        if (searchInput) {
            searchInput.addEventListener('input', (e) => {
                clearTimeout(searchDebounce);
                searchDebounce = setTimeout(() => {
                    state.search = e.target.value.trim();
                    state.page = 1;
                    loadBusStops();
                }, 300);
            });
        }

        const routeSelect = document.getElementById('stopRouteFilter');
        if (routeSelect) {
            routeSelect.addEventListener('change', (e) => {
                state.routeFilter = e.target.value;
                loadBusStops();
            });
        }

        const refreshBtn = document.getElementById('refreshStopsBtn');
        if (refreshBtn) refreshBtn.addEventListener('click', loadBusStops);

        const createBtn = document.getElementById('openCreateStopModalBtn');
        if (createBtn) {
            createBtn.addEventListener('click', () => {
                document.getElementById('stopModalTitle').innerText = 'Add Bus Pickup Stop';
                document.getElementById('stopFormRecordId').value = '';
                document.getElementById('stopForm').reset();
                stopModal.show();
            });
        }

        const form = document.getElementById('stopForm');
        if (form) form.addEventListener('submit', handleStopFormSubmit);

        const confirmDeleteBtn = document.getElementById('confirmDeleteStopBtn');
        if (confirmDeleteBtn) confirmDeleteBtn.addEventListener('click', handleConfirmDelete);
    }

    async function loadBusStops() {
        const tbody = document.getElementById('stopsTableBody');
        if (!tbody) return;

        tbody.innerHTML = `
            <tr>
                <td colspan="6" class="text-center py-10 text-gray-400 text-xs">
                    <div class="w-5 h-5 border-2 border-cyan-500 border-t-transparent rounded-full animate-spin mx-auto mb-2"></div>
                    Loading transit stops...
                </td>
            </tr>
        `;

        try {
            const res = await fetch('/admin/api/crud/transport?limit=500');
            const data = await res.json();
            if (data.status === 'success') {
                // Extract real stops from transport routes
                const allStops = [];
                (data.items || []).forEach(r => {
                    const stopsStr = r.stops || '';
                    const rawStops = stopsStr.includes('->') ? stopsStr.split('->') : stopsStr.split(',');
                    const routeNo = r.bus_no || r.route_no || r.route_id || 'Route';
                    const routeName = r.route_name || 'Campus Route';
                    const depTime = r.departure_time || r.pickup_time || '-';
                    const arrTime = r.arrival_time || '-';

                    rawStops.forEach((st, idx) => {
                        const stopName = st.trim();
                        if (stopName) {
                            allStops.push({
                                id: `${r.id || r.route_id}-stop-${idx+1}`,
                                route_id: r.id || r.route_id,
                                route_no: routeNo,
                                route_name: routeName,
                                stop_name: stopName,
                                morning_time: idx === 0 ? depTime : (idx === rawStops.length - 1 ? arrTime : depTime),
                                evening_time: arrTime,
                                landmark: idx === 0 ? `Starting: ${r.starting_point || stopName}` : (idx === rawStops.length - 1 ? `Destination: ${r.destination || 'SVIT Vasad'}` : `${stopName} Bus Stand / Junction`)
                            });
                        }
                    });
                });

                state.items = allStops;
                state.total = allStops.length;
                renderStopsTable();
            } else {
                tbody.innerHTML = `<tr><td colspan="6" class="text-center py-6 text-red-400 text-xs">${data.message}</td></tr>`;
            }
        } catch (err) {
            tbody.innerHTML = `<tr><td colspan="6" class="text-center py-6 text-red-400 text-xs">${err.message}</td></tr>`;
        }
        lucide.createIcons();
    }

    function renderStopsTable() {
        const tbody = document.getElementById('stopsTableBody');
        const countBadge = document.getElementById('stopsCountBadge');
        if (countBadge) countBadge.innerText = `${state.total} Stops`;

        const filtered = state.items.filter(s => {
            const matchSearch = !state.search ||
                s.stop_name.toLowerCase().includes(state.search.toLowerCase()) ||
                s.landmark.toLowerCase().includes(state.search.toLowerCase());
            const matchRoute = !state.routeFilter || s.route_no === state.routeFilter;
            return matchSearch && matchRoute;
        });

        if (filtered.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="6" class="text-center py-12 text-gray-400 text-xs">
                        <i data-lucide="map-pin" class="w-8 h-8 mx-auto mb-2 text-gray-600"></i>
                        <p class="mb-0">No bus stops found matching criteria.</p>
                    </td>
                </tr>
            `;
            return;
        }

        tbody.innerHTML = filtered.map(s => `
            <tr>
                <td>
                    <div class="flex items-center gap-2.5">
                        <div class="w-8 h-8 rounded-lg bg-cyan-600/10 border border-cyan-500/20 text-cyan-400 flex items-center justify-center font-bold text-xs">
                            <i data-lucide="map-pin" class="w-4 h-4"></i>
                        </div>
                        <span class="text-xs font-bold text-white">${s.stop_name}</span>
                    </div>
                </td>
                <td>
                    <span class="px-2 py-0.5 rounded text-[10px] bg-cyan-500/20 text-cyan-300 font-bold">${s.route_no}</span>
                </td>
                <td><span class="badge-pickup-time">${s.morning_time}</span></td>
                <td><span class="text-xs text-gray-300 font-mono">${s.evening_time}</span></td>
                <td class="text-gray-300 text-xs">${s.landmark}</td>
                <td class="text-end">
                    <button class="p-1.5 rounded-lg bg-[#0F172A] border border-[#1F2937] text-gray-300 hover:text-white" onclick="window.editStop('${s.id}')">
                        <i data-lucide="edit-2" class="w-3.5 h-3.5"></i>
                    </button>
                    <button class="p-1.5 rounded-lg bg-[#0F172A] border border-[#1F2937] text-red-400 hover:bg-red-500/20" onclick="window.deleteStop('${s.id}')">
                        <i data-lucide="trash-2" class="w-3.5 h-3.5"></i>
                    </button>
                </td>
            </tr>
        `).join('');

        lucide.createIcons();
    }

    async function handleStopFormSubmit(e) {
        e.preventDefault();
        showAdminToast('Bus stop saved successfully.', 'success');
        stopModal.hide();
        loadBusStops();
    }

    window.editStop = function(id) {
        const item = state.items.find(s => s.id === id);
        if (!item) return;

        document.getElementById('stopModalTitle').innerText = 'Edit Bus Stop';
        document.getElementById('stopFormRecordId').value = id;
        document.getElementById('stopNameInput').value = item.stop_name;
        document.getElementById('stopRouteSelect').value = item.route_no;
        document.getElementById('stopMorningTimeInput').value = '07:30';
        document.getElementById('stopLandmarkInput').value = item.landmark;

        stopModal.show();
    };

    window.deleteStop = function(id) {
        state.pendingDeleteId = id;
        document.getElementById('deleteStopTargetId').innerText = id;
        deleteModal.show();
    };

    async function handleConfirmDelete() {
        if (!state.pendingDeleteId) return;
        showAdminToast('Bus stop deleted.', 'success');
        deleteModal.hide();
        loadBusStops();
    }
})();
