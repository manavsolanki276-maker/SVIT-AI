/**
 * SVIT Admin - Page 18: Bus Timings Controller
 * Transit schedule board, morning pickup timestamps, campus arrival target,
 * evening departure timings, and route search.
 */

(function() {
    'use strict';

    const state = {
        search: '',
        items: []
    };

    document.addEventListener('DOMContentLoaded', function() {
        bindEvents();
        loadTimings();
    });

    function bindEvents() {
        const searchInput = document.getElementById('timingsSearchInput');
        if (searchInput) {
            searchInput.addEventListener('input', (e) => {
                state.search = e.target.value.trim().toLowerCase();
                renderTimings();
            });
        }

        const refreshBtn = document.getElementById('refreshTimingsBtn');
        if (refreshBtn) refreshBtn.addEventListener('click', loadTimings);
    }

    async function loadTimings() {
        const tbody = document.getElementById('timingsTableBody');
        if (!tbody) return;

        tbody.innerHTML = `
            <tr>
                <td colspan="6" class="text-center py-10 text-gray-400 text-xs">
                    <div class="w-5 h-5 border-2 border-cyan-500 border-t-transparent rounded-full animate-spin mx-auto mb-2"></div>
                    Loading transit departure board...
                </td>
            </tr>
        `;

        try {
            const res = await fetch('/admin/api/crud/transport?limit=500');
            const data = await res.json();
            if (data.status === 'success') {
                state.items = data.items || [];
                renderTimings();
            } else {
                tbody.innerHTML = `<tr><td colspan="6" class="text-center py-6 text-red-400 text-xs">${data.message}</td></tr>`;
            }
        } catch (err) {
            tbody.innerHTML = `<tr><td colspan="6" class="text-center py-6 text-red-400 text-xs">${err.message}</td></tr>`;
        }
        lucide.createIcons();
    }

    function renderTimings() {
        const tbody = document.getElementById('timingsTableBody');
        if (!tbody) return;

        const filtered = state.items.filter(t => {
            if (!state.search) return true;
            return (t.route_name || '').toLowerCase().includes(state.search) ||
                   (t.route_no || '').toLowerCase().includes(state.search);
        });

        if (filtered.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="6" class="text-center py-12 text-gray-400 text-xs">
                        <i data-lucide="clock" class="w-8 h-8 mx-auto mb-2 text-gray-600"></i>
                        <p class="mb-0">No transit timings scheduled.</p>
                    </td>
                </tr>
            `;
            return;
        }

        tbody.innerHTML = filtered.map(t => {
            const routeNo = t.route_no || t.bus_number || 'Route 1';
            const name = t.route_name || 'Vasad Campus Line';
            const driver = t.driver_name || 'Driver In-Charge';
            const phone = t.driver_contact || '-';

            const morningDep = t.morning_departure || t.pickup_time || t.departure_time || '-';
            const morningArr = t.morning_arrival || t.arrival_time || '-';
            const eveningDep = t.evening_departure || t.return_time || '-';

            return `
                <tr>
                    <td>
                        <span class="px-2.5 py-1 rounded-lg text-xs font-bold bg-cyan-500/20 text-cyan-300 border border-cyan-500/30">
                            ${routeNo}
                        </span>
                    </td>
                    <td class="font-bold text-white text-xs">${name}</td>
                    <td><span class="timing-badge-departure">${morningDep}</span></td>
                    <td><span class="timing-badge-arrival">${morningArr}</span></td>
                    <td><span class="timing-badge-departure">${eveningDep}</span></td>
                    <td class="text-gray-300 text-xs font-medium">${driver} <span class="text-gray-500 text-[11px]">(${phone})</span></td>
                </tr>
            `;
        }).join('');

        lucide.createIcons();
    }
})();
