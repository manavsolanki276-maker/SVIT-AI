/**
 * SVIT Admin - Page 27: Sports Events & Tournaments Controller
 * Intra/Inter-college sports tournaments, GTU Spirit matches, trophy/winner records (NO College Fests).
 */

(function() {
    'use strict';

    const state = {
        search: '',
        type: '',
        status: '',
        page: 1,
        limit: 50,
        total: 0,
        items: [],
        pendingDeleteId: null
    };

    let tourneyModal = null;
    let deleteModal = null;
    let searchDebounce = null;

    document.addEventListener('DOMContentLoaded', function() {
        const formEl = document.getElementById('tourneyModal');
        const delEl = document.getElementById('tourneyDeleteModal');

        if (formEl) tourneyModal = new bootstrap.Modal(formEl);
        if (delEl) deleteModal = new bootstrap.Modal(delEl);

        bindEvents();
        loadTournaments();
    });

    function bindEvents() {
        const searchInput = document.getElementById('tourneySearchInput');
        if (searchInput) {
            searchInput.addEventListener('input', (e) => {
                clearTimeout(searchDebounce);
                searchDebounce = setTimeout(() => {
                    state.search = e.target.value.trim();
                    state.page = 1;
                    loadTournaments();
                }, 300);
            });
        }

        const typeFilter = document.getElementById('tourneyTypeFilter');
        if (typeFilter) {
            typeFilter.addEventListener('change', (e) => {
                state.type = e.target.value;
                state.page = 1;
                loadTournaments();
            });
        }

        const refreshBtn = document.getElementById('refreshTourneysBtn');
        if (refreshBtn) refreshBtn.addEventListener('click', loadTournaments);

        const createBtn = document.getElementById('openCreateTourneyModalBtn');
        if (createBtn) {
            createBtn.addEventListener('click', () => {
                document.getElementById('tourneyModalTitle').innerText = 'Add Sports Tournament';
                document.getElementById('tourneyFormRecordId').value = '';
                document.getElementById('tourneyForm').reset();
                tourneyModal.show();
            });
        }

        const form = document.getElementById('tourneyForm');
        if (form) form.addEventListener('submit', handleTourneyFormSubmit);

        const confirmDeleteBtn = document.getElementById('confirmDeleteTourneyBtn');
        if (confirmDeleteBtn) confirmDeleteBtn.addEventListener('click', handleConfirmDelete);
    }

    async function loadTournaments() {
        const tbody = document.getElementById('tourneysTableBody');
        if (tbody) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="7" class="text-center py-10 text-gray-400 text-xs">
                        <div class="w-5 h-5 border-2 border-yellow-500 border-t-transparent rounded-full animate-spin mx-auto mb-2"></div>
                        Loading tournaments...
                    </td>
                </tr>
            `;
        }

        const params = new URLSearchParams({
            page: state.page,
            limit: state.limit,
            search: state.search
        });
        if (state.type) params.append('filter_sport_name', state.type);

        try {
            const res = await fetch(`/admin/api/crud/sports_events?${params.toString()}`);
            const data = await res.json();
            if (data.status === 'success') {
                state.items = data.items || [];
                state.total = data.total || 0;
                renderTournamentsTable();
            } else {
                if (tbody) tbody.innerHTML = `<tr><td colspan="7" class="text-center py-6 text-red-400 text-xs">${data.message}</td></tr>`;
            }
        } catch (err) {
            if (tbody) tbody.innerHTML = `<tr><td colspan="7" class="text-center py-6 text-red-400 text-xs">${err.message}</td></tr>`;
        }
        lucide.createIcons();
    }

    function renderTournamentsTable() {
        const tbody = document.getElementById('tourneysTableBody');
        const countBadge = document.getElementById('tourneysCountBadge');
        if (!tbody) return;

        if (countBadge) countBadge.innerText = `${state.total} Tournaments`;

        if (state.items.length === 0) {
            tbody.innerHTML = `<tr><td colspan="7" class="text-center py-12 text-gray-400 text-xs">No tournaments found.</td></tr>`;
            return;
        }

        tbody.innerHTML = state.items.map(t => {
            const id = t.event_id || t.id || '-';
            const name = t.event_name || t.tournament_name || 'Tournament';
            const sport = t.sport_name || t.sport || 'Cricket';
            const type = t.tournament_type || 'GTU Spirit';
            const date = t.event_date || t.start_date || 'Upcoming';
            const venue = t.venue || 'SVIT Ground';
            const champ = t.prize_details || t.winner || 'Trophy';

            return `
                <tr>
                    <td>
                        <div class="flex items-center gap-2.5">
                            <div class="w-8 h-8 rounded-lg bg-yellow-600/10 border border-yellow-500/20 text-yellow-400 flex items-center justify-center font-bold text-xs">
                                <i data-lucide="medal" class="w-4 h-4"></i>
                            </div>
                            <div>
                                <p class="text-xs font-bold text-white mb-0">${name}</p>
                                <span class="text-[10px] text-yellow-400 font-mono">${id}</span>
                            </div>
                        </div>
                    </td>
                    <td class="text-gray-200 font-medium text-xs">${sport}</td>
                    <td><span class="badge-tourney-type">${type}</span></td>
                    <td class="text-gray-300 text-xs">${date}</td>
                    <td class="text-gray-300 text-xs">${venue}</td>
                    <td>
                        <span class="text-xs text-emerald-400 font-semibold">${champ}</span>
                    </td>
                    <td class="text-end">
                        <button class="p-1.5 rounded-lg bg-[#0F172A] border border-[#1F2937] text-gray-300 hover:text-white" onclick="window.editTourney('${id}')">
                            <i data-lucide="edit-2" class="w-3.5 h-3.5"></i>
                        </button>
                        <button class="p-1.5 rounded-lg bg-[#0F172A] border border-[#1F2937] text-red-400 hover:bg-red-500/20" onclick="window.deleteTourney('${id}')">
                            <i data-lucide="trash-2" class="w-3.5 h-3.5"></i>
                        </button>
                    </td>
                </tr>
            `;
        }).join('');

        lucide.createIcons();
    }

    async function handleTourneyFormSubmit(e) {
        e.preventDefault();
        const recordId = document.getElementById('tourneyFormRecordId').value;
        const name = document.getElementById('tourneyNameInput').value.trim();
        const sport = document.getElementById('tourneySportInput').value.trim();
        const type = document.getElementById('tourneyTypeSelect').value;
        const venue = document.getElementById('tourneyVenueInput').value.trim();

        const payload = {
            event_id: recordId || `SPT_EVT_${Date.now()}`,
            event_name: name,
            sport_name: sport,
            tournament_type: type,
            venue: venue,
            event_date: new Date().toISOString().split('T')[0],
            organizer: 'SVIT Sports Committee',
            status: 'Upcoming'
        };

        const isEdit = Boolean(recordId);
        const url = isEdit ? `/admin/api/crud/sports_events/${recordId}` : '/admin/api/crud/sports_events';
        const method = isEdit ? 'PUT' : 'POST';

        try {
            const res = await fetch(url, {
                method: method,
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            const data = await res.json();
            if (res.ok && data.status === 'success') {
                showAdminToast(data.message || 'Tournament saved successfully.', 'success');
                tourneyModal.hide();
                loadTournaments();
            } else {
                showAdminToast(data.message || 'Error saving tournament.', 'error');
            }
        } catch (err) {
            showAdminToast(err.message, 'error');
        }
    }

    window.editTourney = function(id) {
        const item = state.items.find(t => (t.event_id || t.id) === id);
        if (!item) return;

        document.getElementById('tourneyModalTitle').innerText = 'Edit Tournament';
        document.getElementById('tourneyFormRecordId').value = id;
        document.getElementById('tourneyNameInput').value = item.event_name || item.tournament_name || '';
        document.getElementById('tourneySportInput').value = item.sport_name || item.sport || '';
        document.getElementById('tourneyTypeSelect').value = item.tournament_type || 'GTU Spirit';
        document.getElementById('tourneyVenueInput').value = item.venue || '';

        tourneyModal.show();
    };

    window.deleteTourney = function(id) {
        state.pendingDeleteId = id;
        document.getElementById('deleteTourneyTargetId').innerText = id;
        deleteModal.show();
    };

    async function handleConfirmDelete() {
        if (!state.pendingDeleteId) return;

        try {
            const res = await fetch(`/admin/api/crud/sports_events/${state.pendingDeleteId}`, { method: 'DELETE' });
            const data = await res.json();
            if (res.ok && data.status === 'success') {
                showAdminToast(data.message || 'Tournament deleted.', 'success');
                deleteModal.hide();
                loadTournaments();
            } else {
                showAdminToast(data.message || 'Failed to delete tournament.', 'error');
            }
        } catch (err) {
            showAdminToast(err.message, 'error');
        }
    }
})();
