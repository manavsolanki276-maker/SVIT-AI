/**
 * SVIT Admin - Rooms, Facilities & Campus Navigation Controller
 * Unified Management for:
 * 1. Academic Rooms (1,699 Timetable Rooms)
 * 2. Campus Facilities (Girls Room, Reading Room, Library, etc.)
 * 3. Campus Navigation & Locations (40 Locations with Real Campus Photos)
 */

(function() {
    'use strict';

    // Master State
    const state = {
        activeTab: 'rooms', // 'rooms' | 'facilities' | 'navigation'
        searchQuery: '',
        searchDebounceTimer: null,
        viewMode: 'card', // 'card' | 'table' (rooms only)
        
        // 1. Rooms State
        rooms: {
            page: 1,
            limit: 24,
            total: 0,
            pages: 1,
            items: [],
            loading: false,
            filters: {
                department: '',
                status: '',
                room_type: '',
                building: '',
                floor: ''
            }
        },

        // 2. Facilities State
        facilities: {
            page: 1,
            limit: 100,
            total: 0,
            pages: 1,
            items: [],
            loading: false,
            filters: {
                category: '',
                status: '',
                building: '',
                floor: ''
            }
        },

        // 3. Navigation State (Explore Campus)
        navigation: {
            page: 1,
            limit: 100,
            total: 0,
            pages: 1,
            items: [],
            loading: false,
            filters: {
                category: '',
                zone: ''
            }
        },

        // Live KPI Metrics
        stats: {
            totalRooms: 0,
            totalFacilities: 0,
            totalLocations: 0,
            totalDepts: 8
        },

        // Action Context
        pendingDelete: null // { module: 'rooms'|'facilities'|'campus_info', id: string, name: string }
    };

    // Modal Instances
    let roomFormModal = null;
    let facilityFormModal = null;
    let itemDetailsModal = null;
    let deleteConfirmModal = null;

    // Initialization
    document.addEventListener('DOMContentLoaded', () => {
        initModals();
        bindDomEvents();
        refreshAllData();
    });

    /**
     * Initialize Bootstrap Modal Instances
     */
    function initModals() {
        const roomModalEl = document.getElementById('roomFormModal');
        const facModalEl = document.getElementById('facilityFormModal');
        const detailsModalEl = document.getElementById('itemDetailsModal');
        const deleteModalEl = document.getElementById('deleteConfirmModal');

        if (roomModalEl && typeof bootstrap !== 'undefined') {
            roomFormModal = new bootstrap.Modal(roomModalEl);
        }
        if (facModalEl && typeof bootstrap !== 'undefined') {
            facilityFormModal = new bootstrap.Modal(facModalEl);
        }
        if (detailsModalEl && typeof bootstrap !== 'undefined') {
            itemDetailsModal = new bootstrap.Modal(detailsModalEl);
        }
        if (deleteModalEl && typeof bootstrap !== 'undefined') {
            deleteConfirmModal = new bootstrap.Modal(deleteModalEl);
        }
    }

    /**
     * Bind DOM events
     */
    function bindDomEvents() {
        // Tab Buttons
        const tabRoomsBtn = document.getElementById('tabRoomsBtn');
        const tabFacBtn = document.getElementById('tabFacilitiesBtn');
        const tabNavBtn = document.getElementById('tabNavigationBtn');
        
        if (tabRoomsBtn) tabRoomsBtn.addEventListener('click', () => switchTab('rooms'));
        if (tabFacBtn) tabFacBtn.addEventListener('click', () => switchTab('facilities'));
        if (tabNavBtn) tabNavBtn.addEventListener('click', () => switchTab('navigation'));

        // KPI Card Clicks (Quick Switch)
        const kpiRooms = document.getElementById('kpiTotalRoomsCard');
        const kpiFac = document.getElementById('kpiFacilitiesCard');
        const kpiLoc = document.getElementById('kpiLocationsCard');
        if (kpiRooms) kpiRooms.addEventListener('click', () => switchTab('rooms'));
        if (kpiFac) kpiFac.addEventListener('click', () => switchTab('facilities'));
        if (kpiLoc) kpiLoc.addEventListener('click', () => switchTab('navigation'));

        // Add Buttons
        const openAddRoomBtn = document.getElementById('openAddRoomBtn');
        const emptyAddRoomBtn = document.getElementById('emptyAddRoomBtn');
        if (openAddRoomBtn) openAddRoomBtn.addEventListener('click', () => openRoomFormModal('create'));
        if (emptyAddRoomBtn) emptyAddRoomBtn.addEventListener('click', () => openRoomFormModal('create'));

        const openAddFacBtn = document.getElementById('openAddFacilityBtn');
        const quickAddFacBtn = document.getElementById('quickAddFacilityBtn');
        const emptyAddFacBtn = document.getElementById('emptyAddFacBtn');
        if (openAddFacBtn) openAddFacBtn.addEventListener('click', () => openFacilityFormModal('create'));
        if (quickAddFacBtn) quickAddFacBtn.addEventListener('click', () => openFacilityFormModal('create'));
        if (emptyAddFacBtn) emptyAddFacBtn.addEventListener('click', () => openFacilityFormModal('create'));

        // Global Search
        const searchInput = document.getElementById('globalSearchInput');
        const clearSearchBtn = document.getElementById('clearSearchBtn');
        if (searchInput) {
            searchInput.addEventListener('input', (e) => {
                const val = e.target.value;
                if (clearSearchBtn) clearSearchBtn.classList.toggle('hidden', !val);
                clearTimeout(state.searchDebounceTimer);
                state.searchDebounceTimer = setTimeout(() => {
                    state.searchQuery = val.trim();
                    if (state.activeTab === 'rooms') {
                        state.rooms.page = 1;
                        fetchRooms();
                    } else if (state.activeTab === 'facilities') {
                        state.facilities.page = 1;
                        fetchFacilities();
                    } else {
                        state.navigation.page = 1;
                        fetchNavigation();
                    }
                }, 250);
            });
        }
        if (clearSearchBtn) {
            clearSearchBtn.addEventListener('click', () => {
                if (searchInput) searchInput.value = '';
                clearSearchBtn.classList.add('hidden');
                state.searchQuery = '';
                if (state.activeTab === 'rooms') {
                    state.rooms.page = 1;
                    fetchRooms();
                } else if (state.activeTab === 'facilities') {
                    state.facilities.page = 1;
                    fetchFacilities();
                } else {
                    state.navigation.page = 1;
                    fetchNavigation();
                }
            });
        }

        // Desktop Filters (Rooms)
        const filterDept = document.getElementById('filterDepartmentSelect');
        const filterStatus = document.getElementById('filterStatusSelect');
        const filterType = document.getElementById('filterTypeSelect');

        if (filterDept) {
            filterDept.addEventListener('change', (e) => {
                state.rooms.filters.department = e.target.value;
                state.rooms.page = 1;
                syncMobileFilterInputs();
                fetchRooms();
            });
        }
        if (filterStatus) {
            filterStatus.addEventListener('change', (e) => {
                state.rooms.filters.status = e.target.value;
                state.rooms.page = 1;
                syncMobileFilterInputs();
                fetchRooms();
            });
        }
        if (filterType) {
            filterType.addEventListener('change', (e) => {
                state.rooms.filters.room_type = e.target.value;
                state.rooms.page = 1;
                syncMobileFilterInputs();
                fetchRooms();
            });
        }

        // Desktop Filters (Facilities)
        const filterFacCat = document.getElementById('filterFacilityCategorySelect');
        const filterFacStatus = document.getElementById('filterFacilityStatusSelect');

        if (filterFacCat) {
            filterFacCat.addEventListener('change', (e) => {
                state.facilities.filters.category = e.target.value;
                state.facilities.page = 1;
                syncMobileFilterInputs();
                fetchFacilities();
            });
        }
        if (filterFacStatus) {
            filterFacStatus.addEventListener('change', (e) => {
                state.facilities.filters.status = e.target.value;
                state.facilities.page = 1;
                syncMobileFilterInputs();
                fetchFacilities();
            });
        }

        // Desktop Filters (Navigation)
        const filterNavCat = document.getElementById('filterNavCategorySelect');
        const filterNavZone = document.getElementById('filterNavZoneSelect');

        if (filterNavCat) {
            filterNavCat.addEventListener('change', (e) => {
                state.navigation.filters.category = e.target.value;
                state.navigation.page = 1;
                syncMobileFilterInputs();
                fetchNavigation();
            });
        }
        if (filterNavZone) {
            filterNavZone.addEventListener('change', (e) => {
                state.navigation.filters.zone = e.target.value;
                state.navigation.page = 1;
                syncMobileFilterInputs();
                fetchNavigation();
            });
        }

        // Pagination Limit (Rooms)
        const roomsLimit = document.getElementById('roomsLimitSelect');
        if (roomsLimit) {
            roomsLimit.addEventListener('change', (e) => {
                state.rooms.limit = parseInt(e.target.value, 10) || 24;
                state.rooms.page = 1;
                fetchRooms();
            });
        }

        // Pagination Prev / Next (Rooms)
        const prevRoomsBtn = document.getElementById('prevRoomsPageBtn');
        const nextRoomsBtn = document.getElementById('nextRoomsPageBtn');
        if (prevRoomsBtn) {
            prevRoomsBtn.addEventListener('click', () => {
                if (state.rooms.page > 1) {
                    state.rooms.page--;
                    fetchRooms();
                }
            });
        }
        if (nextRoomsBtn) {
            nextRoomsBtn.addEventListener('click', () => {
                if (state.rooms.page < state.rooms.pages) {
                    state.rooms.page++;
                    fetchRooms();
                }
            });
        }

        // Reset & Refresh Buttons
        const resetFiltersBtn = document.getElementById('resetFiltersBtn');
        const clearAllFiltersBtn = document.getElementById('clearAllFiltersBtn');
        const emptyResetRoomsBtn = document.getElementById('emptyResetRoomsBtn');
        const emptyResetFacBtn = document.getElementById('emptyResetFacBtn');
        const emptyResetNavBtn = document.getElementById('emptyResetNavBtn');
        const refreshDataBtn = document.getElementById('refreshDataBtn');

        if (resetFiltersBtn) resetFiltersBtn.addEventListener('click', resetAllFilters);
        if (clearAllFiltersBtn) clearAllFiltersBtn.addEventListener('click', resetAllFilters);
        if (emptyResetRoomsBtn) emptyResetRoomsBtn.addEventListener('click', resetAllFilters);
        if (emptyResetFacBtn) emptyResetFacBtn.addEventListener('click', resetAllFilters);
        if (emptyResetNavBtn) emptyResetNavBtn.addEventListener('click', resetAllFilters);
        if (refreshDataBtn) refreshDataBtn.addEventListener('click', refreshAllData);

        // View Mode Switcher
        const viewModeCardBtn = document.getElementById('viewModeCardBtn');
        const viewModeTableBtn = document.getElementById('viewModeTableBtn');
        if (viewModeCardBtn) viewModeCardBtn.addEventListener('click', () => setViewMode('card'));
        if (viewModeTableBtn) viewModeTableBtn.addEventListener('click', () => setViewMode('table'));

        // Mobile Filter Drawer
        const openMobileFilterBtn = document.getElementById('openMobileFilterBtn');
        const closeMobileFilterBtn = document.getElementById('closeMobileFilterBtn');
        const mobileFilterBackdrop = document.getElementById('mobileFilterBackdrop');
        const mobileResetFiltersBtn = document.getElementById('mobileResetFiltersBtn');
        const mobileApplyFiltersBtn = document.getElementById('mobileApplyFiltersBtn');

        if (openMobileFilterBtn) openMobileFilterBtn.addEventListener('click', openMobileDrawer);
        if (closeMobileFilterBtn) closeMobileFilterBtn.addEventListener('click', closeMobileDrawer);
        if (mobileFilterBackdrop) mobileFilterBackdrop.addEventListener('click', closeMobileDrawer);
        if (mobileResetFiltersBtn) {
            mobileResetFiltersBtn.addEventListener('click', () => {
                resetAllFilters();
                closeMobileDrawer();
            });
        }
        if (mobileApplyFiltersBtn) {
            mobileApplyFiltersBtn.addEventListener('click', () => {
                applyMobileFilters();
                closeMobileDrawer();
            });
        }

        // Form Submit Listeners
        const roomForm = document.getElementById('roomForm');
        if (roomForm) roomForm.addEventListener('submit', handleRoomFormSubmit);

        const facilityForm = document.getElementById('facilityForm');
        if (facilityForm) facilityForm.addEventListener('submit', handleFacilityFormSubmit);

        // Delete Confirm Button
        const confirmDeleteBtn = document.getElementById('confirmDeleteBtn');
        if (confirmDeleteBtn) confirmDeleteBtn.addEventListener('click', handleConfirmDelete);
    }

    /**
     * Switch Tabs (Rooms, Facilities, Navigation)
     */
    function switchTab(tab) {
        state.activeTab = tab;

        const tabRoomsBtn = document.getElementById('tabRoomsBtn');
        const tabFacBtn = document.getElementById('tabFacilitiesBtn');
        const tabNavBtn = document.getElementById('tabNavigationBtn');

        const paneRooms = document.getElementById('paneRooms');
        const paneFacilities = document.getElementById('paneFacilities');
        const paneNav = document.getElementById('paneNavigation');

        const roomsFilters = document.getElementById('roomsDesktopFilters');
        const facFilters = document.getElementById('facilitiesDesktopFilters');
        const navFilters = document.getElementById('navigationDesktopFilters');

        const viewToggle = document.getElementById('viewModeToggleWrap');
        const mobRoomSec = document.getElementById('mobileRoomFiltersSection');
        const mobFacSec = document.getElementById('mobileFacilityFiltersSection');
        const mobNavSec = document.getElementById('mobileNavigationFiltersSection');

        // Reset tab styles
        [tabRoomsBtn, tabFacBtn, tabNavBtn].forEach(b => {
            if (b) {
                b.classList.remove('active');
                b.setAttribute('aria-selected', 'false');
            }
        });

        // Hide all panes & filters
        if (paneRooms) paneRooms.classList.add('hidden');
        if (paneFacilities) paneFacilities.classList.add('hidden');
        if (paneNav) paneNav.classList.add('hidden');

        if (roomsFilters) roomsFilters.classList.add('hidden');
        if (facFilters) facFilters.classList.add('hidden');
        if (navFilters) navFilters.classList.add('hidden');

        if (mobRoomSec) mobRoomSec.classList.add('hidden');
        if (mobFacSec) mobFacSec.classList.add('hidden');
        if (mobNavSec) mobNavSec.classList.add('hidden');

        if (tab === 'rooms') {
            if (tabRoomsBtn) {
                tabRoomsBtn.classList.add('active');
                tabRoomsBtn.setAttribute('aria-selected', 'true');
            }
            if (paneRooms) paneRooms.classList.remove('hidden');
            if (roomsFilters) roomsFilters.classList.remove('hidden');
            if (viewToggle) viewToggle.classList.remove('hidden');
            if (mobRoomSec) mobRoomSec.classList.remove('hidden');

            if (state.rooms.items.length === 0) fetchRooms();
        } else if (tab === 'facilities') {
            if (tabFacBtn) {
                tabFacBtn.classList.add('active');
                tabFacBtn.setAttribute('aria-selected', 'true');
            }
            if (paneFacilities) paneFacilities.classList.remove('hidden');
            if (facFilters) facFilters.classList.remove('hidden');
            if (viewToggle) viewToggle.classList.add('hidden');
            if (mobFacSec) mobFacSec.classList.remove('hidden');

            if (state.facilities.items.length === 0) fetchFacilities();
        } else {
            if (tabNavBtn) {
                tabNavBtn.classList.add('active');
                tabNavBtn.setAttribute('aria-selected', 'true');
            }
            if (paneNav) paneNav.classList.remove('hidden');
            if (navFilters) navFilters.classList.remove('hidden');
            if (viewToggle) viewToggle.classList.add('hidden');
            if (mobNavSec) mobNavSec.classList.remove('hidden');

            if (state.navigation.items.length === 0) fetchNavigation();
        }

        renderActiveFilterPills();
        if (window.lucide) window.lucide.createIcons();
    }

    /**
     * Switch view mode between Card and Table (Rooms only)
     */
    function setViewMode(mode) {
        state.viewMode = mode;
        const btnCard = document.getElementById('viewModeCardBtn');
        const btnTable = document.getElementById('viewModeTableBtn');
        const cardGrid = document.getElementById('roomsCardGrid');
        const tableView = document.getElementById('roomsTableView');

        if (mode === 'card') {
            if (btnCard) btnCard.classList.add('active');
            if (btnTable) btnTable.classList.remove('active');
            if (cardGrid) cardGrid.classList.remove('hidden');
            if (tableView) tableView.classList.add('hidden');
        } else {
            if (btnTable) btnTable.classList.add('active');
            if (btnCard) btnCard.classList.remove('active');
            if (cardGrid) cardGrid.classList.add('hidden');
            if (tableView) tableView.classList.remove('hidden');
        }
    }

    /**
     * Refresh All 3 Datasets
     */
    function refreshAllData() {
        fetchRooms();
        fetchFacilities();
        fetchNavigation();
    }

    /**
     * 1. Fetch Academic Rooms
     */
    async function fetchRooms() {
        state.rooms.loading = true;
        renderRoomsLoading(true);

        const params = new URLSearchParams();
        params.set('page', state.rooms.page.toString());
        params.set('limit', state.rooms.limit.toString());

        if (state.searchQuery) params.set('search', state.searchQuery);

        const activeFilters = {};
        for (const [k, v] of Object.entries(state.rooms.filters)) {
            if (v && v.trim() !== '') activeFilters[k] = v.trim();
        }
        if (Object.keys(activeFilters).length > 0) {
            params.set('filters', JSON.stringify(activeFilters));
        }

        try {
            const resp = await fetch(`/admin/api/crud/rooms_facilities?${params.toString()}`);
            const data = await resp.json();

            if (data.status === 'success') {
                state.rooms.items = data.items || [];
                state.rooms.total = data.total || 0;
                state.rooms.pages = data.pages || 1;
                state.rooms.page = data.page || 1;

                if (!state.searchQuery && Object.keys(activeFilters).length === 0) {
                    state.stats.totalRooms = data.total;
                }

                renderRooms();
                renderRoomsPagination();
            } else {
                showToast(data.message || 'Failed to load academic rooms.', 'error');
            }
        } catch (err) {
            console.error('Error fetching rooms:', err);
            showToast('Network error while loading academic rooms.', 'error');
        } finally {
            state.rooms.loading = false;
            renderRoomsLoading(false);
            renderActiveFilterPills();
            updateKpiDisplay();
        }
    }

    /**
     * 2. Fetch Campus Facilities
     */
    async function fetchFacilities() {
        state.facilities.loading = true;
        renderFacilitiesLoading(true);

        const params = new URLSearchParams();
        params.set('page', state.facilities.page.toString());
        params.set('limit', state.facilities.limit.toString());

        if (state.searchQuery) params.set('search', state.searchQuery);

        const activeFilters = {};
        for (const [k, v] of Object.entries(state.facilities.filters)) {
            if (v && v.trim() !== '') activeFilters[k] = v.trim();
        }
        if (Object.keys(activeFilters).length > 0) {
            params.set('filters', JSON.stringify(activeFilters));
        }

        try {
            const resp = await fetch(`/admin/api/crud/facilities?${params.toString()}`);
            const data = await resp.json();

            if (data.status === 'success') {
                state.facilities.items = data.items || [];
                state.facilities.total = data.total || 0;

                if (!state.searchQuery && Object.keys(activeFilters).length === 0) {
                    state.stats.totalFacilities = data.total;
                }

                renderFacilities();
            } else {
                showToast(data.message || 'Failed to load facilities.', 'error');
            }
        } catch (err) {
            console.error('Error fetching facilities:', err);
            showToast('Network error while loading facilities.', 'error');
        } finally {
            state.facilities.loading = false;
            renderFacilitiesLoading(false);
            renderActiveFilterPills();
            updateKpiDisplay();
        }
    }

    /**
     * 3. Fetch Campus Navigation & Locations (with Images)
     */
    async function fetchNavigation() {
        state.navigation.loading = true;
        renderNavigationLoading(true);

        const params = new URLSearchParams();
        params.set('page', state.navigation.page.toString());
        params.set('limit', state.navigation.limit.toString());

        if (state.searchQuery) params.set('search', state.searchQuery);

        const activeFilters = {};
        for (const [k, v] of Object.entries(state.navigation.filters)) {
            if (v && v.trim() !== '') activeFilters[k] = v.trim();
        }
        if (Object.keys(activeFilters).length > 0) {
            params.set('filters', JSON.stringify(activeFilters));
        }

        try {
            const resp = await fetch(`/admin/api/crud/campus_info?${params.toString()}`);
            const data = await resp.json();

            if (data.status === 'success') {
                state.navigation.items = data.items || [];
                state.navigation.total = data.total || 0;

                if (!state.searchQuery && Object.keys(activeFilters).length === 0) {
                    state.stats.totalLocations = data.total;
                }

                renderNavigation();
            } else {
                showToast(data.message || 'Failed to load campus locations.', 'error');
            }
        } catch (err) {
            console.error('Error fetching navigation places:', err);
            showToast('Network error while loading campus locations.', 'error');
        } finally {
            state.navigation.loading = false;
            renderNavigationLoading(false);
            renderActiveFilterPills();
            updateKpiDisplay();
        }
    }

    /**
     * Update KPI display
     */
    function updateKpiDisplay() {
        const headerCount = document.getElementById('headerTotalCount');
        const kpiTotalRooms = document.getElementById('kpiTotalRooms');
        const kpiTotalFac = document.getElementById('kpiTotalFacilities');
        const kpiTotalLoc = document.getElementById('kpiTotalLocations');
        const kpiDepts = document.getElementById('kpiTotalDepts');
        const tabRoomsCount = document.getElementById('tabRoomsCount');
        const tabFacCount = document.getElementById('tabFacilitiesCount');
        const tabNavCount = document.getElementById('tabNavigationCount');

        const totalCombined = (state.stats.totalRooms || 0) + (state.stats.totalFacilities || 0) + (state.stats.totalLocations || 0);

        if (headerCount) headerCount.textContent = totalCombined.toLocaleString();
        if (kpiTotalRooms) kpiTotalRooms.textContent = (state.stats.totalRooms || 0).toLocaleString();
        if (kpiTotalFac) kpiTotalFac.textContent = (state.stats.totalFacilities || 0).toLocaleString();
        if (kpiTotalLoc) kpiTotalLoc.textContent = (state.stats.totalLocations || 0).toLocaleString();
        if (kpiDepts) kpiDepts.textContent = '8';
        if (tabRoomsCount) tabRoomsCount.textContent = (state.stats.totalRooms || 0).toLocaleString();
        if (tabFacCount) tabFacCount.textContent = (state.stats.totalFacilities || 0).toLocaleString();
        if (tabNavCount) tabNavCount.textContent = (state.stats.totalLocations || 0).toLocaleString();
    }

    /**
     * Render Academic Rooms Cards & Table
     */
    function renderRooms() {
        const cardGrid = document.getElementById('roomsCardGrid');
        const tableBody = document.getElementById('roomsTableBody');
        const emptyState = document.getElementById('roomsEmptyState');
        const rangeText = document.getElementById('showingRoomsRange');
        const totalText = document.getElementById('totalRoomsCount');

        const items = state.rooms.items;
        const total = state.rooms.total;

        if (totalText) totalText.textContent = total.toLocaleString();
        if (rangeText) {
            const start = total === 0 ? 0 : (state.rooms.page - 1) * state.rooms.limit + 1;
            const end = Math.min(state.rooms.page * state.rooms.limit, total);
            rangeText.textContent = `${start}-${end}`;
        }

        if (items.length === 0) {
            if (cardGrid) cardGrid.innerHTML = '';
            if (tableBody) tableBody.innerHTML = '';
            if (emptyState) emptyState.classList.remove('hidden');
            return;
        }

        if (emptyState) emptyState.classList.add('hidden');

        // 1. Render Cards
        if (cardGrid) {
            let cardsHtml = '';
            items.forEach(room => {
                const id = escapeHtml(room.room_id || room.id || '');
                const name = escapeHtml(room.room_name || id);
                const dept = escapeHtml(room.department || 'General Academic');
                const status = (room.status || 'Active').trim();
                const type = escapeHtml(room.room_type || (name.includes('Lab') ? 'Laboratory' : 'Classroom'));
                const bldg = escapeHtml(room.building || '');
                const floor = escapeHtml(room.floor || '');
                const capacity = escapeHtml(room.capacity || '');

                const statusClass = getStatusClass(status);

                cardsHtml += `
                <div class="room-card" data-room-id="${id}">
                    <div>
                        <div class="room-card-header">
                            <div>
                                <span class="room-id-tag">${id}</span>
                                <h4 class="room-name-title">${name}</h4>
                            </div>
                            <span class="room-status-badge ${statusClass}">
                                <span class="status-badge-dot"></span>
                                ${escapeHtml(status)}
                            </span>
                        </div>

                        <div class="room-card-body">
                            <div class="room-dept-badge" title="${dept}">
                                <i data-lucide="graduation-cap" class="w-3.5 h-3.5"></i>
                                <span>${dept}</span>
                            </div>

                            <div class="room-meta-row">
                                <span class="room-meta-item" title="Room Type">
                                    <i data-lucide="door-closed" class="w-3.5 h-3.5 text-[#8C95AD]"></i>
                                    ${type}
                                </span>
                                ${bldg ? `
                                <span class="room-meta-item" title="Building">
                                    <i data-lucide="building" class="w-3.5 h-3.5 text-[#8C95AD]"></i>
                                    ${bldg}${floor ? ` (${floor})` : ''}
                                </span>` : ''}
                                ${capacity ? `
                                <span class="room-meta-item" title="Capacity">
                                    <i data-lucide="users" class="w-3.5 h-3.5 text-[#8C95AD]"></i>
                                    ${capacity} seats
                                </span>` : ''}
                            </div>
                        </div>
                    </div>

                    <div class="room-card-footer">
                        <button type="button" class="btn-card-action view-room-details-btn" data-room-id="${id}">
                            <i data-lucide="eye" class="w-3.5 h-3.5"></i>
                            <span>Details</span>
                        </button>
                        <div class="card-action-menu">
                            <button type="button" class="btn-card-icon edit-room-btn" data-room-id="${id}" title="Edit Room">
                                <i data-lucide="edit-2" class="w-3.5 h-3.5"></i>
                            </button>
                            <button type="button" class="btn-card-icon delete-hover delete-room-btn" data-room-id="${id}" data-room-name="${name}" title="Delete Room">
                                <i data-lucide="trash-2" class="w-3.5 h-3.5"></i>
                            </button>
                        </div>
                    </div>
                </div>`;
            });
            cardGrid.innerHTML = cardsHtml;
        }

        // 2. Render Table View
        if (tableBody) {
            let rowsHtml = '';
            items.forEach(room => {
                const id = escapeHtml(room.room_id || room.id || '');
                const name = escapeHtml(room.room_name || id);
                const dept = escapeHtml(room.department || 'General Academic');
                const status = (room.status || 'Active').trim();
                const type = escapeHtml(room.room_type || 'Classroom');
                const bldg = escapeHtml(room.building || '-');
                const floor = escapeHtml(room.floor || '');
                const capacity = escapeHtml(room.capacity ? `${room.capacity} seats` : '-');
                const statusClass = getStatusClass(status);

                rowsHtml += `
                <tr>
                    <td class="font-mono text-xs text-[#8C95AD]">${id}</td>
                    <td class="font-bold text-[#171D3A]">${name}</td>
                    <td><span class="text-xs text-[#171D3A] font-medium">${dept}</span></td>
                    <td class="text-xs text-[#66708F]">${bldg}${floor ? ` (${floor})` : ''}</td>
                    <td class="text-xs text-[#66708F]">${type}</td>
                    <td class="text-xs text-[#66708F]">${capacity}</td>
                    <td>
                        <span class="room-status-badge ${statusClass}">
                            <span class="status-badge-dot"></span>
                            ${escapeHtml(status)}
                        </span>
                    </td>
                    <td class="text-end">
                        <div class="inline-flex items-center gap-1">
                            <button type="button" class="btn-card-icon view-room-details-btn" data-room-id="${id}" title="View Details">
                                <i data-lucide="eye" class="w-3.5 h-3.5"></i>
                            </button>
                            <button type="button" class="btn-card-icon edit-room-btn" data-room-id="${id}" title="Edit Room">
                                <i data-lucide="edit-2" class="w-3.5 h-3.5"></i>
                            </button>
                            <button type="button" class="btn-card-icon delete-hover delete-room-btn" data-room-id="${id}" data-room-name="${name}" title="Delete Room">
                                <i data-lucide="trash-2" class="w-3.5 h-3.5"></i>
                            </button>
                        </div>
                    </td>
                </tr>`;
            });
            tableBody.innerHTML = rowsHtml;
        }

        attachRoomCardListeners();
        if (window.lucide) window.lucide.createIcons();
    }

    /**
     * Render Campus Facilities Cards
     */
    function renderFacilities() {
        const cardGrid = document.getElementById('facilitiesCardGrid');
        const emptyState = document.getElementById('facilitiesEmptyState');
        const totalText = document.getElementById('totalFacilitiesCount');

        const items = state.facilities.items;
        const total = state.facilities.total;

        if (totalText) totalText.textContent = total.toLocaleString();

        if (items.length === 0) {
            if (cardGrid) cardGrid.innerHTML = '';
            if (emptyState) emptyState.classList.remove('hidden');
            return;
        }

        if (emptyState) emptyState.classList.add('hidden');

        if (cardGrid) {
            let cardsHtml = '';
            items.forEach(fac => {
                const id = escapeHtml(fac.facility_id || fac.id || '');
                const name = escapeHtml(fac.facility_name || id);
                const category = escapeHtml(fac.category || 'Campus Facility');
                const desc = escapeHtml(fac.description || 'Campus resource for students and faculty.');
                const location = escapeHtml(fac.location || fac.building || 'Campus Central Area');
                const status = (fac.status || 'Active').trim();
                const amenities = escapeHtml(fac.facilities || '');
                const statusClass = getStatusClass(status);

                let iconName = 'building-2';
                if (category.toLowerCase().includes('student') || name.toLowerCase().includes('girls')) iconName = 'sparkles';
                else if (category.toLowerCase().includes('study') || category.toLowerCase().includes('library') || name.toLowerCase().includes('reading')) iconName = 'book-open';
                else if (category.toLowerCase().includes('health') || name.toLowerCase().includes('medical')) iconName = 'heart-pulse';
                else if (category.toLowerCase().includes('sports')) iconName = 'trophy';
                else if (category.toLowerCase().includes('entry') || name.toLowerCase().includes('gate')) iconName = 'navigation';

                cardsHtml += `
                <div class="facility-card" data-facility-id="${id}">
                    <div>
                        <div class="facility-card-header">
                            <div class="facility-icon-circle">
                                <i data-lucide="${iconName}" class="w-5 h-5"></i>
                            </div>
                            <div class="facility-title-wrap">
                                <h4 class="facility-name">${name}</h4>
                                <span class="facility-category-badge">${category}</span>
                            </div>
                            <span class="room-status-badge ${statusClass}">
                                <span class="status-badge-dot"></span>
                                ${escapeHtml(status)}
                            </span>
                        </div>

                        <div class="facility-card-body">
                            <p class="facility-desc">${desc}</p>

                            <div class="facility-location-row">
                                <i data-lucide="map-pin" class="w-3.5 h-3.5 text-[#8C95AD]"></i>
                                <span>${location}</span>
                            </div>

                            ${amenities ? `
                            <div class="facility-amenities-box">
                                <i data-lucide="check-circle" class="w-3.5 h-3.5 text-[#10B981] flex-shrink-0"></i>
                                <span class="truncate" title="${amenities}">${amenities}</span>
                            </div>` : ''}
                        </div>
                    </div>

                    <div class="facility-card-footer">
                        <button type="button" class="btn-card-action view-facility-details-btn" data-facility-id="${id}">
                            <i data-lucide="eye" class="w-3.5 h-3.5"></i>
                            <span>Details</span>
                        </button>
                        <div class="card-action-menu">
                            <button type="button" class="btn-card-icon edit-facility-btn" data-facility-id="${id}" title="Edit Facility">
                                <i data-lucide="edit-2" class="w-3.5 h-3.5"></i>
                            </button>
                            <button type="button" class="btn-card-icon delete-hover delete-facility-btn" data-facility-id="${id}" data-facility-name="${name}" title="Delete Facility">
                                <i data-lucide="trash-2" class="w-3.5 h-3.5"></i>
                            </button>
                        </div>
                    </div>
                </div>`;
            });
            cardGrid.innerHTML = cardsHtml;
        }

        attachFacilityCardListeners();
        if (window.lucide) window.lucide.createIcons();
    }

    /**
     * Render Campus Navigation & Locations (Explore Campus with Real Photos)
     */
    function renderNavigation() {
        const cardGrid = document.getElementById('navigationCardGrid');
        const emptyState = document.getElementById('navigationEmptyState');
        const totalText = document.getElementById('totalNavigationCount');

        const items = state.navigation.items;
        const total = state.navigation.total;

        if (totalText) totalText.textContent = total.toLocaleString();

        if (items.length === 0) {
            if (cardGrid) cardGrid.innerHTML = '';
            if (emptyState) emptyState.classList.remove('hidden');
            return;
        }

        if (emptyState) emptyState.classList.add('hidden');

        if (cardGrid) {
            let cardsHtml = '';
            items.forEach(loc => {
                const id = escapeHtml(loc.place_id || loc.id || '');
                const name = escapeHtml(loc.place_name || id);
                const category = escapeHtml(loc.category || 'Campus Location');
                const zone = escapeHtml(loc.zone || 'Campus Area');
                const landmark = escapeHtml(loc.landmark || '');
                const desc = escapeHtml(loc.description || `SVIT Campus landmark situated in ${zone}.`);
                const imgUrl = loc.image_url || '/static/navigation_maps/SVIT with all dep.jpeg';

                cardsHtml += `
                <div class="navigation-card view-navigation-details-card" data-nav-id="${id}">
                    <div class="nav-card-img-wrap">
                        <img src="${imgUrl}" alt="${name}" class="nav-card-img" loading="lazy" onerror="this.onerror=null; this.src='/static/navigation_maps/SVIT with all dep.jpeg';">
                        <span class="nav-card-category-badge">${category}</span>
                    </div>

                    <div class="nav-card-body">
                        <div>
                            <h4 class="nav-card-title">${name}</h4>
                            <div class="nav-card-zone-row">
                                <i data-lucide="map-pin" class="w-3.5 h-3.5 text-[#3B82F6] flex-shrink-0"></i>
                                <span class="font-semibold text-[#171D3A]">${zone}</span>
                                ${landmark ? `<span class="text-[#8C95AD]">• ${landmark}</span>` : ''}
                            </div>
                            <p class="nav-card-desc">${desc}</p>
                        </div>

                        <div class="nav-card-footer">
                            <span class="text-xs font-mono text-[#8C95AD]">${id}</span>
                            <button type="button" class="nav-card-link-btn">
                                <span>Explore Location</span>
                                <i data-lucide="arrow-right" class="w-3.5 h-3.5"></i>
                            </button>
                        </div>
                    </div>
                </div>`;
            });
            cardGrid.innerHTML = cardsHtml;
        }

        attachNavigationCardListeners();
        if (window.lucide) window.lucide.createIcons();
    }

    /**
     * Attach Click Listeners
     */
    function attachRoomCardListeners() {
        document.querySelectorAll('.view-room-details-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                const id = btn.getAttribute('data-room-id');
                const room = state.rooms.items.find(r => (r.room_id || r.id) === id);
                if (room) openDetailsModal('room', room);
            });
        });

        document.querySelectorAll('.edit-room-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                const id = btn.getAttribute('data-room-id');
                const room = state.rooms.items.find(r => (r.room_id || r.id) === id);
                if (room) openRoomFormModal('edit', room);
            });
        });

        document.querySelectorAll('.delete-room-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                const id = btn.getAttribute('data-room-id');
                const name = btn.getAttribute('data-room-name') || id;
                openDeleteConfirmModal('rooms', id, name);
            });
        });
    }

    function attachFacilityCardListeners() {
        document.querySelectorAll('.view-facility-details-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                const id = btn.getAttribute('data-facility-id');
                const fac = state.facilities.items.find(f => (f.facility_id || f.id) === id);
                if (fac) openDetailsModal('facility', fac);
            });
        });

        document.querySelectorAll('.edit-facility-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                const id = btn.getAttribute('data-facility-id');
                const fac = state.facilities.items.find(f => (f.facility_id || f.id) === id);
                if (fac) openFacilityFormModal('edit', fac);
            });
        });

        document.querySelectorAll('.delete-facility-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                const id = btn.getAttribute('data-facility-id');
                const name = btn.getAttribute('data-facility-name') || id;
                openDeleteConfirmModal('facilities', id, name);
            });
        });
    }

    function attachNavigationCardListeners() {
        document.querySelectorAll('.view-navigation-details-card').forEach(card => {
            card.addEventListener('click', () => {
                const id = card.getAttribute('data-nav-id');
                const loc = state.navigation.items.find(n => (n.place_id || n.id) === id);
                if (loc) openDetailsModal('navigation', loc);
            });
        });
    }

    /**
     * Modals: Add / Edit Room
     */
    function openRoomFormModal(mode, roomData = null) {
        const titleEl = document.getElementById('roomFormModalLabel');
        const editModeInput = document.getElementById('roomEditMode');
        const origIdInput = document.getElementById('roomOriginalId');
        const idInput = document.getElementById('inputRoomId');
        const nameInput = document.getElementById('inputRoomName');
        const deptInput = document.getElementById('inputRoomDepartment');
        const typeInput = document.getElementById('inputRoomType');
        const bldgInput = document.getElementById('inputRoomBuilding');
        const floorInput = document.getElementById('inputRoomFloor');
        const capInput = document.getElementById('inputRoomCapacity');
        const statusInput = document.getElementById('inputRoomStatus');
        const facInput = document.getElementById('inputRoomFacilities');

        if (mode === 'edit' && roomData) {
            if (titleEl) titleEl.textContent = `Edit Room: ${roomData.room_name || roomData.id}`;
            if (editModeInput) editModeInput.value = 'edit';
            if (origIdInput) origIdInput.value = roomData.id || roomData.room_id;
            if (idInput) {
                idInput.value = roomData.room_id || roomData.id || '';
                idInput.disabled = true;
            }
            if (nameInput) nameInput.value = roomData.room_name || '';
            if (deptInput) deptInput.value = roomData.department || '';
            if (typeInput) typeInput.value = roomData.room_type || '';
            if (bldgInput) bldgInput.value = roomData.building || '';
            if (floorInput) floorInput.value = roomData.floor || '';
            if (capInput) capInput.value = roomData.capacity || '';
            if (statusInput) statusInput.value = roomData.status || 'Active';
            if (facInput) facInput.value = roomData.facilities || '';
        } else {
            if (titleEl) titleEl.textContent = 'Add Academic Room';
            if (editModeInput) editModeInput.value = 'create';
            if (origIdInput) origIdInput.value = '';
            if (idInput) {
                idInput.value = '';
                idInput.disabled = false;
            }
            if (nameInput) nameInput.value = '';
            if (deptInput) deptInput.value = '';
            if (typeInput) typeInput.value = 'Classroom';
            if (bldgInput) bldgInput.value = '';
            if (floorInput) floorInput.value = '';
            if (capInput) capInput.value = '';
            if (statusInput) statusInput.value = 'Active';
            if (facInput) facInput.value = '';
        }

        if (roomFormModal) roomFormModal.show();
        if (window.lucide) window.lucide.createIcons();
    }

    /**
     * Modals: Add / Edit Facility
     */
    function openFacilityFormModal(mode, facData = null) {
        const titleEl = document.getElementById('facilityFormModalLabel');
        const editModeInput = document.getElementById('facilityEditMode');
        const origIdInput = document.getElementById('facilityOriginalId');
        const idInput = document.getElementById('inputFacilityId');
        const nameInput = document.getElementById('inputFacilityName');
        const catInput = document.getElementById('inputFacilityCategory');
        const statusInput = document.getElementById('inputFacilityStatus');
        const bldgInput = document.getElementById('inputFacilityBuilding');
        const floorInput = document.getElementById('inputFacilityFloor');
        const locInput = document.getElementById('inputFacilityLocation');
        const capInput = document.getElementById('inputFacilityCapacity');
        const descInput = document.getElementById('inputFacilityDescription');
        const amenInput = document.getElementById('inputFacilityAmenities');

        if (mode === 'edit' && facData) {
            if (titleEl) titleEl.textContent = `Edit Facility: ${facData.facility_name || facData.id}`;
            if (editModeInput) editModeInput.value = 'edit';
            if (origIdInput) origIdInput.value = facData.id || facData.facility_id;
            if (idInput) {
                idInput.value = facData.facility_id || facData.id || '';
                idInput.disabled = true;
            }
            if (nameInput) nameInput.value = facData.facility_name || '';
            if (catInput) catInput.value = facData.category || '';
            if (statusInput) statusInput.value = facData.status || 'Active';
            if (bldgInput) bldgInput.value = facData.building || '';
            if (floorInput) floorInput.value = facData.floor || '';
            if (locInput) locInput.value = facData.location || '';
            if (capInput) capInput.value = facData.capacity || '';
            if (descInput) descInput.value = facData.description || '';
            if (amenInput) amenInput.value = facData.facilities || '';
        } else {
            if (titleEl) titleEl.textContent = 'Add Campus Facility';
            if (editModeInput) editModeInput.value = 'create';
            if (origIdInput) origIdInput.value = '';
            if (idInput) {
                idInput.value = '';
                idInput.disabled = false;
            }
            if (nameInput) nameInput.value = '';
            if (catInput) catInput.value = 'Student Facility';
            if (statusInput) statusInput.value = 'Active';
            if (bldgInput) bldgInput.value = '';
            if (floorInput) floorInput.value = '';
            if (locInput) locInput.value = '';
            if (capInput) capInput.value = '';
            if (descInput) descInput.value = '';
            if (amenInput) amenInput.value = '';
        }

        if (facilityFormModal) facilityFormModal.show();
        if (window.lucide) window.lucide.createIcons();
    }

    /**
     * Details Modal (Room, Facility, or Navigation)
     */
    function openDetailsModal(type, item) {
        const titleEl = document.getElementById('itemDetailsModalLabel');
        const subLabelEl = document.getElementById('detailsSubLabel');
        const iconEl = document.getElementById('detailsHeaderIcon');
        const contentEl = document.getElementById('detailsContentContainer');
        const editBtn = document.getElementById('detailsEditBtn');

        if (type === 'room') {
            const name = escapeHtml(item.room_name || item.id);
            const id = escapeHtml(item.room_id || item.id);
            const dept = escapeHtml(item.department || '-');
            const roomType = escapeHtml(item.room_type || 'Classroom');
            const status = (item.status || 'Active').trim();
            const bldg = escapeHtml(item.building || '');
            const floor = escapeHtml(item.floor || '');
            const cap = escapeHtml(item.capacity || '');
            const facilities = escapeHtml(item.facilities || '');
            const statusClass = getStatusClass(status);

            if (titleEl) titleEl.textContent = `Room: ${name}`;
            if (subLabelEl) subLabelEl.textContent = 'Academic classroom & timetable inventory record';
            if (iconEl) iconEl.innerHTML = '<i data-lucide="door-closed" class="w-5 h-5"></i>';

            let detailsHtml = `
            <div class="details-hero-box">
                <div>
                    <span class="text-xs font-mono text-[#8C95AD]">${id}</span>
                    <h3 class="text-xl font-bold text-[#171D3A] m-0">${name}</h3>
                    <p class="text-xs text-[#66708F] mt-1 mb-0">${dept}</p>
                </div>
                <span class="room-status-badge ${statusClass}">
                    <span class="status-badge-dot"></span>
                    ${escapeHtml(status)}
                </span>
            </div>

            <div class="details-grid">
                <div class="details-item">
                    <span class="details-item-label">Room Type</span>
                    <span class="details-item-val">${roomType}</span>
                </div>
                <div class="details-item">
                    <span class="details-item-label">Department</span>
                    <span class="details-item-val">${dept}</span>
                </div>
                ${bldg ? `
                <div class="details-item">
                    <span class="details-item-label">Building / Block</span>
                    <span class="details-item-val">${bldg}</span>
                </div>` : ''}
                ${floor ? `
                <div class="details-item">
                    <span class="details-item-label">Floor</span>
                    <span class="details-item-val">${floor}</span>
                </div>` : ''}
                ${cap ? `
                <div class="details-item">
                    <span class="details-item-label">Seating Capacity</span>
                    <span class="details-item-val">${cap} Students</span>
                </div>` : ''}
            </div>

            ${facilities ? `
            <div class="details-full-box">
                <span class="details-item-label mb-1">Equipment & Amenities</span>
                <p class="text-xs text-[#171D3A] m-0 leading-relaxed">${facilities}</p>
            </div>` : ''}`;

            if (contentEl) contentEl.innerHTML = detailsHtml;

            if (editBtn) {
                editBtn.classList.remove('hidden');
                editBtn.onclick = () => {
                    if (itemDetailsModal) itemDetailsModal.hide();
                    openRoomFormModal('edit', item);
                };
            }
        } else if (type === 'facility') {
            const name = escapeHtml(item.facility_name || item.id);
            const id = escapeHtml(item.facility_id || item.id);
            const cat = escapeHtml(item.category || 'Campus Facility');
            const desc = escapeHtml(item.description || '');
            const loc = escapeHtml(item.location || item.building || 'Campus Central Area');
            const status = (item.status || 'Active').trim();
            const bldg = escapeHtml(item.building || '');
            const floor = escapeHtml(item.floor || '');
            const cap = escapeHtml(item.capacity || '');
            const amenities = escapeHtml(item.facilities || '');
            const statusClass = getStatusClass(status);

            if (titleEl) titleEl.textContent = `Facility: ${name}`;
            if (subLabelEl) subLabelEl.textContent = 'Campus resource & student utility record';
            if (iconEl) iconEl.innerHTML = '<i data-lucide="building-2" class="w-5 h-5"></i>';

            let detailsHtml = `
            <div class="details-hero-box">
                <div>
                    <span class="text-xs font-mono text-[#8C95AD]">${id}</span>
                    <h3 class="text-xl font-bold text-[#171D3A] m-0">${name}</h3>
                    <span class="facility-category-badge mt-1">${cat}</span>
                </div>
                <span class="room-status-badge ${statusClass}">
                    <span class="status-badge-dot"></span>
                    ${escapeHtml(status)}
                </span>
            </div>

            ${desc ? `
            <div class="details-full-box">
                <span class="details-item-label mb-1">About Facility</span>
                <p class="text-xs text-[#171D3A] m-0 leading-relaxed">${desc}</p>
            </div>` : ''}

            <div class="details-grid">
                <div class="details-item">
                    <span class="details-item-label">Location / Landmark</span>
                    <span class="details-item-val">${loc}</span>
                </div>
                ${bldg ? `
                <div class="details-item">
                    <span class="details-item-label">Building</span>
                    <span class="details-item-val">${bldg}${floor ? ` (${floor})` : ''}</span>
                </div>` : ''}
                ${cap ? `
                <div class="details-item">
                    <span class="details-item-label">Capacity</span>
                    <span class="details-item-val">${cap} Persons</span>
                </div>` : ''}
            </div>

            ${amenities ? `
            <div class="details-full-box">
                <span class="details-item-label mb-1">Features & Amenities Available</span>
                <p class="text-xs text-[#171D3A] m-0 leading-relaxed">${amenities}</p>
            </div>` : ''}`;

            if (contentEl) contentEl.innerHTML = detailsHtml;

            if (editBtn) {
                editBtn.classList.remove('hidden');
                editBtn.onclick = () => {
                    if (itemDetailsModal) itemDetailsModal.hide();
                    openFacilityFormModal('edit', item);
                };
            }
        } else {
            // Navigation / Campus Location
            const name = escapeHtml(item.place_name || item.id);
            const id = escapeHtml(item.place_id || item.id);
            const cat = escapeHtml(item.category || 'Campus Location');
            const zone = escapeHtml(item.zone || 'Campus Area');
            const landmark = escapeHtml(item.landmark || '');
            const desc = escapeHtml(item.description || `SVIT Campus landmark situated in ${zone}.`);
            const imgUrl = item.image_url || '/static/navigation_maps/SVIT with all dep.jpeg';

            if (titleEl) titleEl.textContent = `Location: ${name}`;
            if (subLabelEl) subLabelEl.textContent = 'Campus map and navigation landmark';
            if (iconEl) iconEl.innerHTML = '<i data-lucide="map-pin" class="w-5 h-5"></i>';

            let detailsHtml = `
            <div class="details-img-preview mb-3">
                <img src="${imgUrl}" alt="${name}" onerror="this.onerror=null; this.src='/static/navigation_maps/SVIT with all dep.jpeg';">
            </div>

            <div class="details-hero-box">
                <div>
                    <span class="text-xs font-mono text-[#8C95AD]">${id}</span>
                    <h3 class="text-xl font-bold text-[#171D3A] m-0">${name}</h3>
                    <span class="facility-category-badge mt-1">${cat}</span>
                </div>
                <div class="text-end">
                    <span class="text-xs font-bold text-[#3B82F6] block">${zone}</span>
                </div>
            </div>

            ${desc ? `
            <div class="details-full-box">
                <span class="details-item-label mb-1">Campus Description</span>
                <p class="text-xs text-[#171D3A] m-0 leading-relaxed">${desc}</p>
            </div>` : ''}

            <div class="details-grid">
                <div class="details-item">
                    <span class="details-item-label">Campus Zone</span>
                    <span class="details-item-val">${zone}</span>
                </div>
                <div class="details-item">
                    <span class="details-item-label">Landmark Reference</span>
                    <span class="details-item-val">${landmark || 'Central Campus'}</span>
                </div>
            </div>`;

            if (contentEl) contentEl.innerHTML = detailsHtml;
            if (editBtn) editBtn.classList.add('hidden'); // Read-only navigation landmark
        }

        if (itemDetailsModal) itemDetailsModal.show();
        if (window.lucide) window.lucide.createIcons();
    }

    /**
     * Delete Confirmation Modal
     */
    function openDeleteConfirmModal(module, id, name) {
        state.pendingDelete = { module, id, name };
        const nameEl = document.getElementById('deleteTargetName');
        if (nameEl) nameEl.textContent = `"${name}" (${id})`;
        if (deleteConfirmModal) deleteConfirmModal.show();
    }

    async function handleConfirmDelete() {
        if (!state.pendingDelete) return;

        const { module, id } = state.pendingDelete;
        const confirmBtn = document.getElementById('confirmDeleteBtn');
        if (confirmBtn) {
            confirmBtn.disabled = true;
            confirmBtn.textContent = 'Deleting...';
        }

        try {
            const resp = await fetch(`/admin/api/crud/${module}/${encodeURIComponent(id)}`, { method: 'DELETE' });
            const data = await resp.json();

            if (data.status === 'success') {
                showToast('Record deleted successfully.', 'success');
                if (deleteConfirmModal) deleteConfirmModal.hide();
                if (module === 'rooms' || module === 'rooms_facilities') {
                    fetchRooms();
                } else if (module === 'facilities') {
                    fetchFacilities();
                } else {
                    fetchNavigation();
                }
            } else {
                showToast(data.message || 'Error deleting record.', 'error');
            }
        } catch (err) {
            console.error('Delete error:', err);
            showToast('Network error while deleting record.', 'error');
        } finally {
            if (confirmBtn) {
                confirmBtn.disabled = false;
                confirmBtn.textContent = 'Delete';
            }
            state.pendingDelete = null;
        }
    }

    /**
     * Handle Form Submits
     */
    async function handleRoomFormSubmit(e) {
        e.preventDefault();
        const form = e.target;
        if (!form.checkValidity()) {
            form.classList.add('was-validated');
            return;
        }

        const mode = document.getElementById('roomEditMode').value;
        const origId = document.getElementById('roomOriginalId').value;
        const submitBtn = document.getElementById('saveRoomSubmitBtn');

        const payload = {
            room_id: document.getElementById('inputRoomId').value.trim(),
            room_name: document.getElementById('inputRoomName').value.trim(),
            department: document.getElementById('inputRoomDepartment').value.trim(),
            room_type: document.getElementById('inputRoomType').value.trim(),
            building: document.getElementById('inputRoomBuilding').value.trim(),
            floor: document.getElementById('inputRoomFloor').value.trim(),
            capacity: document.getElementById('inputRoomCapacity').value.trim(),
            status: document.getElementById('inputRoomStatus').value.trim(),
            facilities: document.getElementById('inputRoomFacilities').value.trim()
        };

        if (submitBtn) {
            submitBtn.disabled = true;
            submitBtn.innerHTML = '<i data-lucide="loader-2" class="w-4 h-4 animate-spin"></i> Saving...';
        }

        try {
            const url = mode === 'edit'
                ? `/admin/api/crud/rooms/${encodeURIComponent(origId)}`
                : '/admin/api/crud/rooms';
            const method = mode === 'edit' ? 'PUT' : 'POST';

            const resp = await fetch(url, {
                method: method,
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            const data = await resp.json();

            if (data.status === 'success') {
                showToast(mode === 'edit' ? 'Room updated successfully.' : 'Room added successfully.', 'success');
                if (roomFormModal) roomFormModal.hide();
                fetchRooms();
            } else {
                showToast(data.message || 'Error saving room.', 'error');
            }
        } catch (err) {
            console.error('Error saving room:', err);
            showToast('Network error saving room.', 'error');
        } finally {
            if (submitBtn) {
                submitBtn.disabled = false;
                submitBtn.innerHTML = '<i data-lucide="check" class="w-4 h-4"></i> Save Room';
            }
            if (window.lucide) window.lucide.createIcons();
        }
    }

    async function handleFacilityFormSubmit(e) {
        e.preventDefault();
        const form = e.target;
        if (!form.checkValidity()) {
            form.classList.add('was-validated');
            return;
        }

        const mode = document.getElementById('facilityEditMode').value;
        const origId = document.getElementById('facilityOriginalId').value;
        const submitBtn = document.getElementById('saveFacilitySubmitBtn');

        const payload = {
            facility_id: document.getElementById('inputFacilityId').value.trim(),
            facility_name: document.getElementById('inputFacilityName').value.trim(),
            category: document.getElementById('inputFacilityCategory').value.trim(),
            status: document.getElementById('inputFacilityStatus').value.trim(),
            building: document.getElementById('inputFacilityBuilding').value.trim(),
            floor: document.getElementById('inputFacilityFloor').value.trim(),
            location: document.getElementById('inputFacilityLocation').value.trim(),
            capacity: document.getElementById('inputFacilityCapacity').value.trim(),
            description: document.getElementById('inputFacilityDescription').value.trim(),
            facilities: document.getElementById('inputFacilityAmenities').value.trim()
        };

        if (submitBtn) {
            submitBtn.disabled = true;
            submitBtn.innerHTML = '<i data-lucide="loader-2" class="w-4 h-4 animate-spin"></i> Saving...';
        }

        try {
            const url = mode === 'edit'
                ? `/admin/api/crud/facilities/${encodeURIComponent(origId)}`
                : '/admin/api/crud/facilities';
            const method = mode === 'edit' ? 'PUT' : 'POST';

            const resp = await fetch(url, {
                method: method,
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            const data = await resp.json();

            if (data.status === 'success') {
                showToast(mode === 'edit' ? 'Facility updated successfully.' : 'Facility added successfully.', 'success');
                if (facilityFormModal) facilityFormModal.hide();
                fetchFacilities();
            } else {
                showToast(data.message || 'Error saving facility.', 'error');
            }
        } catch (err) {
            console.error('Error saving facility:', err);
            showToast('Network error saving facility.', 'error');
        } finally {
            if (submitBtn) {
                submitBtn.disabled = false;
                submitBtn.innerHTML = '<i data-lucide="check" class="w-4 h-4"></i> Save Facility';
            }
            if (window.lucide) window.lucide.createIcons();
        }
    }

    /**
     * Pagination Controls (Rooms)
     */
    function renderRoomsPagination() {
        const infoEl = document.getElementById('currentRoomsPage');
        const pagesEl = document.getElementById('totalRoomsPages');
        const prevBtn = document.getElementById('prevRoomsPageBtn');
        const nextBtn = document.getElementById('nextRoomsPageBtn');
        const listEl = document.getElementById('roomsPageNumbers');

        const { page, pages } = state.rooms;

        if (infoEl) infoEl.textContent = page.toString();
        if (pagesEl) pagesEl.textContent = pages.toString();
        if (prevBtn) prevBtn.disabled = page <= 1;
        if (nextBtn) nextBtn.disabled = page >= pages;

        if (listEl) {
            let html = '';
            const start = Math.max(1, page - 2);
            const end = Math.min(pages, page + 2);

            if (start > 1) {
                html += `<button type="button" class="page-num-btn" data-page="1">1</button>`;
                if (start > 2) html += `<span class="px-1 text-xs text-[#8C95AD]">...</span>`;
            }

            for (let p = start; p <= end; p++) {
                html += `<button type="button" class="page-num-btn ${p === page ? 'active' : ''}" data-page="${p}">${p}</button>`;
            }

            if (end < pages) {
                if (end < pages - 1) html += `<span class="px-1 text-xs text-[#8C95AD]">...</span>`;
                html += `<button type="button" class="page-num-btn" data-page="${pages}">${pages}</button>`;
            }

            listEl.innerHTML = html;

            listEl.querySelectorAll('.page-num-btn').forEach(btn => {
                btn.addEventListener('click', () => {
                    const targetPage = parseInt(btn.getAttribute('data-page'), 10);
                    if (targetPage && targetPage !== state.rooms.page) {
                        state.rooms.page = targetPage;
                        fetchRooms();
                    }
                });
            });
        }
    }

    /**
     * Active Filters Feedback Pills
     */
    function renderActiveFilterPills() {
        const container = document.getElementById('activeFiltersContainer');
        const pillsList = document.getElementById('activeFilterPills');
        const badgeDot = document.getElementById('activeFilterBadge');

        let activeFilters = {};
        if (state.activeTab === 'rooms') activeFilters = state.rooms.filters;
        else if (state.activeTab === 'facilities') activeFilters = state.facilities.filters;
        else activeFilters = state.navigation.filters;

        let activeCount = 0;
        let pillsHtml = '';

        for (const [key, val] of Object.entries(activeFilters)) {
            if (val && val.trim() !== '') {
                activeCount++;
                const label = formatFilterLabel(key, val);
                pillsHtml += `
                <span class="filter-pill">
                    <span>${label}</span>
                    <button type="button" class="filter-pill-remove" data-filter-key="${key}" title="Remove filter">
                        <i data-lucide="x" class="w-3 h-3"></i>
                    </button>
                </span>`;
            }
        }

        if (container) container.classList.toggle('hidden', activeCount === 0);
        if (pillsList) {
            pillsList.innerHTML = pillsHtml;
            pillsList.querySelectorAll('.filter-pill-remove').forEach(btn => {
                btn.addEventListener('click', () => {
                    const filterKey = btn.getAttribute('data-filter-key');
                    if (state.activeTab === 'rooms') {
                        state.rooms.filters[filterKey] = '';
                        state.rooms.page = 1;
                        syncDesktopFilterInputs();
                        syncMobileFilterInputs();
                        fetchRooms();
                    } else if (state.activeTab === 'facilities') {
                        state.facilities.filters[filterKey] = '';
                        state.facilities.page = 1;
                        syncDesktopFilterInputs();
                        syncMobileFilterInputs();
                        fetchFacilities();
                    } else {
                        state.navigation.filters[filterKey] = '';
                        state.navigation.page = 1;
                        syncDesktopFilterInputs();
                        syncMobileFilterInputs();
                        fetchNavigation();
                    }
                });
            });
        }

        if (badgeDot) badgeDot.classList.toggle('hidden', activeCount === 0);
        if (window.lucide) window.lucide.createIcons();
    }

    function resetAllFilters() {
        state.searchQuery = '';
        const searchInput = document.getElementById('globalSearchInput');
        const clearSearchBtn = document.getElementById('clearSearchBtn');
        if (searchInput) searchInput.value = '';
        if (clearSearchBtn) clearSearchBtn.classList.add('hidden');

        state.rooms.filters = { department: '', status: '', room_type: '', building: '', floor: '' };
        state.facilities.filters = { category: '', status: '', building: '', floor: '' };
        state.navigation.filters = { category: '', zone: '' };

        state.rooms.page = 1;
        state.facilities.page = 1;
        state.navigation.page = 1;

        syncDesktopFilterInputs();
        syncMobileFilterInputs();

        if (state.activeTab === 'rooms') fetchRooms();
        else if (state.activeTab === 'facilities') fetchFacilities();
        else fetchNavigation();
    }

    /**
     * Mobile Drawer Controls
     */
    function openMobileDrawer() {
        const backdrop = document.getElementById('mobileFilterBackdrop');
        const drawer = document.getElementById('mobileFilterDrawer');
        if (backdrop) backdrop.classList.remove('hidden');
        if (drawer) drawer.classList.remove('hidden');
        syncMobileFilterInputs();
    }

    function closeMobileDrawer() {
        const backdrop = document.getElementById('mobileFilterBackdrop');
        const drawer = document.getElementById('mobileFilterDrawer');
        if (backdrop) backdrop.classList.add('hidden');
        if (drawer) drawer.classList.add('hidden');
    }

    function applyMobileFilters() {
        if (state.activeTab === 'rooms') {
            state.rooms.filters.department = document.getElementById('mobileFilterDept')?.value || '';
            state.rooms.filters.room_type = document.getElementById('mobileFilterType')?.value || '';
            state.rooms.filters.status = document.getElementById('mobileFilterStatus')?.value || '';
            state.rooms.page = 1;
            syncDesktopFilterInputs();
            fetchRooms();
        } else if (state.activeTab === 'facilities') {
            state.facilities.filters.category = document.getElementById('mobileFilterFacCat')?.value || '';
            state.facilities.filters.status = document.getElementById('mobileFilterFacStatus')?.value || '';
            state.facilities.page = 1;
            syncDesktopFilterInputs();
            fetchFacilities();
        } else {
            state.navigation.filters.category = document.getElementById('mobileFilterNavCat')?.value || '';
            state.navigation.filters.zone = document.getElementById('mobileFilterNavZone')?.value || '';
            state.navigation.page = 1;
            syncDesktopFilterInputs();
            fetchNavigation();
        }
    }

    function syncDesktopFilterInputs() {
        const filterDept = document.getElementById('filterDepartmentSelect');
        const filterStatus = document.getElementById('filterStatusSelect');
        const filterType = document.getElementById('filterTypeSelect');
        const filterFacCat = document.getElementById('filterFacilityCategorySelect');
        const filterFacStatus = document.getElementById('filterFacilityStatusSelect');
        const filterNavCat = document.getElementById('filterNavCategorySelect');
        const filterNavZone = document.getElementById('filterNavZoneSelect');

        if (filterDept) filterDept.value = state.rooms.filters.department;
        if (filterStatus) filterStatus.value = state.rooms.filters.status;
        if (filterType) filterType.value = state.rooms.filters.room_type;
        if (filterFacCat) filterFacCat.value = state.facilities.filters.category;
        if (filterFacStatus) filterFacStatus.value = state.facilities.filters.status;
        if (filterNavCat) filterNavCat.value = state.navigation.filters.category;
        if (filterNavZone) filterNavZone.value = state.navigation.filters.zone;
    }

    function syncMobileFilterInputs() {
        const mobDept = document.getElementById('mobileFilterDept');
        const mobType = document.getElementById('mobileFilterType');
        const mobStatus = document.getElementById('mobileFilterStatus');
        const mobFacCat = document.getElementById('mobileFilterFacCat');
        const mobFacStatus = document.getElementById('mobileFilterFacStatus');
        const mobNavCat = document.getElementById('mobileFilterNavCat');
        const mobNavZone = document.getElementById('mobileFilterNavZone');

        if (mobDept) mobDept.value = state.rooms.filters.department;
        if (mobType) mobType.value = state.rooms.filters.room_type;
        if (mobStatus) mobStatus.value = state.rooms.filters.status;
        if (mobFacCat) mobFacCat.value = state.facilities.filters.category;
        if (mobFacStatus) mobFacStatus.value = state.facilities.filters.status;
        if (mobNavCat) mobNavCat.value = state.navigation.filters.category;
        if (mobNavZone) mobNavZone.value = state.navigation.filters.zone;
    }

    /**
     * Helpers & Formatters
     */
    function renderRoomsLoading(isLoading) {
        const skel = document.getElementById('roomsSkeletonGrid');
        const grid = document.getElementById('roomsCardGrid');
        const tbl = document.getElementById('roomsTableView');
        if (skel) skel.classList.toggle('hidden', !isLoading);
        if (grid && isLoading) grid.classList.add('hidden');
        else if (grid && !isLoading && state.viewMode === 'card') grid.classList.remove('hidden');
        if (tbl && isLoading) tbl.classList.add('hidden');
        else if (tbl && !isLoading && state.viewMode === 'table') tbl.classList.remove('hidden');
    }

    function renderFacilitiesLoading(isLoading) {
        const skel = document.getElementById('facilitiesSkeletonGrid');
        const grid = document.getElementById('facilitiesCardGrid');
        if (skel) skel.classList.toggle('hidden', !isLoading);
        if (grid) grid.classList.toggle('hidden', isLoading);
    }

    function renderNavigationLoading(isLoading) {
        const skel = document.getElementById('navigationSkeletonGrid');
        const grid = document.getElementById('navigationCardGrid');
        if (skel) skel.classList.toggle('hidden', !isLoading);
        if (grid) grid.classList.toggle('hidden', isLoading);
    }

    function getStatusClass(status) {
        const s = (status || '').toLowerCase().trim();
        if (s === 'active') return 'status-active';
        if (s === 'available') return 'status-available';
        if (s === 'occupied') return 'status-occupied';
        if (s === 'maintenance') return 'status-maintenance';
        return 'status-inactive';
    }

    function formatFilterLabel(key, val) {
        const keyLabels = {
            department: 'Dept',
            room_type: 'Type',
            status: 'Status',
            category: 'Category',
            zone: 'Zone',
            building: 'Bldg'
        };
        const prefix = keyLabels[key] || key;
        return `${prefix}: ${val}`;
    }

    function escapeHtml(str) {
        if (!str) return '';
        return String(str)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
    }

    function showToast(message, type = 'info') {
        if (window.showAdminNotification) {
            window.showAdminNotification(message, type);
            return;
        }
        const toast = document.createElement('div');
        toast.className = `fixed bottom-4 right-4 z-50 px-4 py-2.5 rounded-xl shadow-lg text-xs font-semibold flex items-center gap-2 ${
            type === 'success' ? 'bg-[#10B981] text-white' : type === 'error' ? 'bg-[#EF4444] text-white' : 'bg-[#171D3A] text-white'
        }`;
        toast.innerHTML = `<i data-lucide="${type === 'success' ? 'check' : 'alert-circle'}" class="w-4 h-4"></i> <span>${escapeHtml(message)}</span>`;
        document.body.appendChild(toast);
        if (window.lucide) window.lucide.createIcons();
        setTimeout(() => toast.remove(), 3500);
    }

})();
