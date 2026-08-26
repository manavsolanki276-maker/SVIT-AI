/**
 * SVIT Admin - Timetable Management Controller (Mobile-First Architecture)
 * Handles progressive multi-tier academic filtering (Program -> Department -> Semester -> Division),
 * weekly desktop schedule matrix, mobile timeline with live NOW/NEXT tags, conflict detection,
 * KPI calculations, and complete CRUD operations.
 */

(function() {
    'use strict';

    const DAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
    const TIME_SLOTS = [
        { label: '09:00 - 10:00', start: '09:00', end: '10:00' },
        { label: '10:00 - 11:00', start: '10:00', end: '11:00' },
        { label: '11:15 - 12:15', start: '11:15', end: '12:15' },
        { label: '12:15 - 01:15', start: '12:15', end: '01:15', end24: '13:15' },
        { label: '02:00 - 03:00', start: '02:00', end: '03:00', start24: '14:00', end24: '15:00' },
        { label: '03:00 - 04:00', start: '03:00', end: '04:00', start24: '15:00', end24: '16:00' }
    ];

    const state = {
        program: 'Diploma',
        department: 'Computer Engineering',
        semester: '1',
        division: 'A',
        dayFilter: '',       // '' means All Days, or specific Day
        selectedDay: 'Monday', // Active tab on mobile view
        search: '',
        items: [],
        totalCount: 0,
        pendingDeleteId: null,
        pendingDeleteDoc: null
    };

    let slotModal = null;
    let detailsModal = null;
    let deleteModal = null;
    let filterDrawerModal = null;

    document.addEventListener('DOMContentLoaded', function() {
        // Initialize Modals
        const slotEl = document.getElementById('timetableSlotModal');
        const detailsEl = document.getElementById('timetableDetailsModal');
        const deleteEl = document.getElementById('timetableDeleteModal');
        const filterDrawerEl = document.getElementById('timetableMobileFilterModal');

        if (slotEl && typeof bootstrap !== 'undefined') slotModal = new bootstrap.Modal(slotEl);
        if (detailsEl && typeof bootstrap !== 'undefined') detailsModal = new bootstrap.Modal(detailsEl);
        if (deleteEl && typeof bootstrap !== 'undefined') deleteModal = new bootstrap.Modal(deleteEl);
        if (filterDrawerEl && typeof bootstrap !== 'undefined') filterDrawerModal = new bootstrap.Modal(filterDrawerEl);

        // Smart Day Determination (Default to today if Mon-Sat)
        const currentDayIndex = new Date().getDay(); // 0 is Sun, 1 is Mon...
        if (currentDayIndex >= 1 && currentDayIndex <= 6) {
            state.selectedDay = DAYS[currentDayIndex - 1];
        }

        bindEvents();
        syncFilterSelectors();
        loadTimetable();
    });

    function bindEvents() {
        // Primary Desktop Selectors
        const progSelect = document.getElementById('ttProgramSelect');
        if (progSelect) {
            progSelect.addEventListener('change', (e) => {
                state.program = e.target.value;
                syncFilterSelectors();
                loadTimetable();
            });
        }

        const deptSelect = document.getElementById('ttDeptSelect');
        if (deptSelect) {
            deptSelect.addEventListener('change', (e) => {
                state.department = e.target.value;
                syncFilterSelectors();
                loadTimetable();
            });
        }

        const semSelect = document.getElementById('ttSemSelect');
        if (semSelect) {
            semSelect.addEventListener('change', (e) => {
                state.semester = e.target.value;
                syncFilterSelectors();
                loadTimetable();
            });
        }

        const divSelect = document.getElementById('ttDivSelect');
        if (divSelect) {
            divSelect.addEventListener('change', (e) => {
                state.division = e.target.value;
                syncFilterSelectors();
                loadTimetable();
            });
        }

        const daySelect = document.getElementById('ttDaySelect');
        if (daySelect) {
            daySelect.addEventListener('change', (e) => {
                state.dayFilter = e.target.value;
                if (state.dayFilter) {
                    state.selectedDay = state.dayFilter;
                }
                updateMobileDayTabs();
                renderTimetableViews();
            });
        }

        // Live Search Input (Debounced)
        const searchInput = document.getElementById('ttSearchInput');
        const clearSearchBtn = document.getElementById('ttSearchClearBtn');
        let searchDebounceTimer = null;

        if (searchInput) {
            searchInput.addEventListener('input', (e) => {
                state.search = e.target.value.trim();
                if (clearSearchBtn) {
                    clearSearchBtn.classList.toggle('hidden', !state.search);
                }
                clearTimeout(searchDebounceTimer);
                searchDebounceTimer = setTimeout(() => {
                    renderTimetableViews();
                }, 200);
            });
        }

        if (clearSearchBtn) {
            clearSearchBtn.addEventListener('click', () => {
                state.search = '';
                if (searchInput) searchInput.value = '';
                clearSearchBtn.classList.add('hidden');
                renderTimetableViews();
            });
        }

        // Mobile Day Tab Buttons
        document.querySelectorAll('#mobileDayTabs .mobile-day-pill').forEach(btn => {
            btn.addEventListener('click', () => {
                const day = btn.getAttribute('data-day');
                if (!day) return;
                state.selectedDay = day;
                updateMobileDayTabs();
                renderMobileTimeline();
            });
        });

        // Mobile Filter Drawer Button
        const mobileDrawerBtn = document.getElementById('mobileFilterDrawerBtn');
        if (mobileDrawerBtn) {
            mobileDrawerBtn.addEventListener('click', () => {
                syncFilterSelectors();
                if (filterDrawerModal) filterDrawerModal.show();
            });
        }

        // Apply Mobile Filters
        const applyMobileBtn = document.getElementById('mFilterApplyBtn');
        if (applyMobileBtn) {
            applyMobileBtn.addEventListener('click', () => {
                state.program = document.getElementById('mFilterProgram').value;
                state.department = document.getElementById('mFilterDept').value;
                state.semester = document.getElementById('mFilterSem').value;
                state.division = document.getElementById('mFilterDiv').value;
                state.dayFilter = document.getElementById('mFilterDay').value;
                if (state.dayFilter) state.selectedDay = state.dayFilter;

                syncFilterSelectors();
                if (filterDrawerModal) filterDrawerModal.hide();
                loadTimetable();
            });
        }

        // Reset Mobile Filters
        const resetMobileBtn = document.getElementById('mFilterResetBtn');
        if (resetMobileBtn) {
            resetMobileBtn.addEventListener('click', () => {
                state.program = 'Diploma';
                state.department = 'Computer Engineering';
                state.semester = '1';
                state.division = 'A';
                state.dayFilter = '';
                state.search = '';
                syncFilterSelectors();
                if (filterDrawerModal) filterDrawerModal.hide();
                loadTimetable();
            });
        }

        // Reset Filter Chips
        const clearAllBtn = document.getElementById('ttClearAllFiltersBtn');
        if (clearAllBtn) {
            clearAllBtn.addEventListener('click', () => {
                state.dayFilter = '';
                state.search = '';
                if (searchInput) searchInput.value = '';
                if (clearSearchBtn) clearSearchBtn.classList.add('hidden');
                syncFilterSelectors();
                renderTimetableViews();
            });
        }

        // Refresh Button
        const refreshBtn = document.getElementById('refreshTimetableBtn');
        if (refreshBtn) refreshBtn.addEventListener('click', loadTimetable);

        // Add Schedule CTA
        const addBtn = document.getElementById('openAddSlotModalBtn');
        if (addBtn) {
            addBtn.addEventListener('click', () => {
                window.quickAddSlot(state.selectedDay || 'Monday', '09:00', '10:00');
            });
        }

        // Print / Export Button
        const exportBtn = document.getElementById('exportTimetableBtn');
        if (exportBtn) {
            exportBtn.addEventListener('click', handleExportPrint);
        }

        // Timetable Form Submit
        const form = document.getElementById('timetableForm');
        if (form) form.addEventListener('submit', handleSlotFormSubmit);

        // Confirm Delete Button
        const confirmDeleteBtn = document.getElementById('confirmDeleteSlotBtn');
        if (confirmDeleteBtn) confirmDeleteBtn.addEventListener('click', handleConfirmDelete);
    }

    function syncFilterSelectors() {
        const progSelect = document.getElementById('ttProgramSelect');
        if (progSelect) progSelect.value = state.program;

        const deptSelect = document.getElementById('ttDeptSelect');
        if (deptSelect) deptSelect.value = state.department;

        const semSelect = document.getElementById('ttSemSelect');
        if (semSelect) semSelect.value = state.semester;

        const divSelect = document.getElementById('ttDivSelect');
        if (divSelect) divSelect.value = state.division;

        const daySelect = document.getElementById('ttDaySelect');
        if (daySelect) daySelect.value = state.dayFilter;

        // Mobile drawer selectors
        const mProg = document.getElementById('mFilterProgram');
        if (mProg) mProg.value = state.program;

        const mDept = document.getElementById('mFilterDept');
        if (mDept) mDept.value = state.department;

        const mSem = document.getElementById('mFilterSem');
        if (mSem) mSem.value = state.semester;

        const mDiv = document.getElementById('mFilterDiv');
        if (mDiv) mDiv.value = state.division;

        const mDay = document.getElementById('mFilterDay');
        if (mDay) mDay.value = state.dayFilter;

        updateMobileDayTabs();
    }

    function updateMobileDayTabs() {
        document.querySelectorAll('#mobileDayTabs .mobile-day-pill').forEach(btn => {
            const day = btn.getAttribute('data-day');
            btn.classList.toggle('active', day === state.selectedDay);
        });
    }

    // =========================================================================
    // DATA FETCHING & API INTERACTION
    // =========================================================================

    async function loadTimetable() {
        const gridBody = document.getElementById('timetableGridBody');
        const mobileSchedule = document.getElementById('timetableMobileSchedule');

        // Loading Skeletons
        if (gridBody) {
            gridBody.innerHTML = `
                <tr>
                    <td colspan="7" class="text-center py-16 text-[#66708F] text-xs">
                        <div class="w-6 h-6 border-2 border-[#8B5CF6] border-t-transparent rounded-full animate-spin mx-auto mb-3"></div>
                        <p class="font-bold text-[#171D3A] mb-1">Loading Schedule Matrix...</p>
                        <p class="text-[11px] text-[#8C95AD] mb-0">${state.program} • ${state.department} (Sem ${state.semester}, Div ${state.division})</p>
                    </td>
                </tr>
            `;
        }

        if (mobileSchedule) {
            mobileSchedule.innerHTML = `
                <div class="text-center py-12 bg-white border border-[#E1E5F0] rounded-2xl p-6 shadow-sm">
                    <div class="w-6 h-6 border-2 border-[#8B5CF6] border-t-transparent rounded-full animate-spin mx-auto mb-3"></div>
                    <p class="font-bold text-xs text-[#171D3A] mb-1">Loading Academic Classes...</p>
                    <p class="text-[11px] text-[#8C95AD] mb-0">${state.department} • Sem ${state.semester}</p>
                </div>
            `;
        }

        const params = new URLSearchParams({
            limit: 500,
            filter_program: state.program,
            filter_department: state.department,
            filter_semester: state.semester,
            filter_division: state.division
        });

        try {
            const res = await fetch(`/admin/api/crud/timetable?${params.toString()}`);
            const data = await res.json();
            if (res.ok && data.status === 'success') {
                state.items = data.items || [];
                state.totalCount = data.total || state.items.length;
                renderTimetableViews();
            } else {
                showErrorState(data.message || 'Error loading timetable data.');
            }
        } catch (err) {
            showErrorState(err.message || 'Network error fetching timetable.');
        }
    }

    function showErrorState(msg) {
        const gridBody = document.getElementById('timetableGridBody');
        const mobileSchedule = document.getElementById('timetableMobileSchedule');
        const errorHtml = `
            <div class="text-center py-8 p-6 bg-red-50 border border-red-200 rounded-2xl text-red-600">
                <i data-lucide="alert-circle" class="w-6 h-6 mx-auto mb-2"></i>
                <p class="text-xs font-bold mb-1">Failed to Load Schedule</p>
                <p class="text-[11px] text-red-500 mb-3">${escapeHtml(msg)}</p>
                <button type="button" class="px-3 py-1.5 rounded-xl bg-white border border-red-200 text-red-700 text-xs font-bold shadow-sm hover:bg-red-100" onclick="location.reload()">
                    Retry
                </button>
            </div>
        `;
        if (gridBody) gridBody.innerHTML = `<tr><td colspan="7">${errorHtml}</td></tr>`;
        if (mobileSchedule) mobileSchedule.innerHTML = errorHtml;
        if (window.lucide) lucide.createIcons();
    }

    // =========================================================================
    // RENDERING & CONFLICT DETECTION
    // =========================================================================

    function renderTimetableViews() {
        updateKpisAndContext();
        renderActiveFilterChips();
        updateDayCountBadges();
        renderDesktopMatrix();
        renderMobileTimeline();
        if (window.lucide) lucide.createIcons();
    }

    function detectConflicts(itemsList) {
        // Returns a Set of conflicting item IDs
        const conflictIds = new Set();
        const facultySlots = {};
        const roomSlots = {};

        itemsList.forEach(item => {
            const day = (item.day || '').toLowerCase();
            const time = (item.start_time || '') + '-' + (item.end_time || '');
            const fKey = `${day}_${time}_${(item.faculty || '').toLowerCase()}`;
            const rKey = `${day}_${time}_${(item.room || '').toLowerCase()}`;

            if (item.faculty && item.faculty.trim()) {
                if (facultySlots[fKey]) {
                    conflictIds.add(item.id);
                    conflictIds.add(facultySlots[fKey]);
                } else {
                    facultySlots[fKey] = item.id;
                }
            }

            if (item.room && item.room.trim()) {
                if (roomSlots[rKey]) {
                    conflictIds.add(item.id);
                    conflictIds.add(roomSlots[rKey]);
                } else {
                    roomSlots[rKey] = item.id;
                }
            }
        });

        return conflictIds;
    }

    function getFilteredItems() {
        let items = [...state.items];

        if (state.search) {
            const q = state.search.toLowerCase();
            items = items.filter(it => {
                const subj = (it.subject || '').toLowerCase();
                const fac = (it.faculty || '').toLowerCase();
                const rm = (it.room || '').toLowerCase();
                const dept = (it.department || '').toLowerCase();
                const prog = (it.program || '').toLowerCase();
                return subj.includes(q) || fac.includes(q) || rm.includes(q) || dept.includes(q) || prog.includes(q);
            });
        }

        if (state.dayFilter) {
            items = items.filter(it => (it.day || '').toLowerCase() === state.dayFilter.toLowerCase());
        }

        return items;
    }

    function updateKpisAndContext() {
        const allItems = state.items;
        const filtered = getFilteredItems();

        // Distinct Calculations
        const distinctFaculty = new Set(allItems.map(i => i.faculty).filter(Boolean));
        const distinctRooms = new Set(allItems.map(i => i.room).filter(Boolean));

        // Today's classes
        const todayDayName = DAYS[new Date().getDay() - 1] || 'Monday';
        const todayClasses = allItems.filter(i => (i.day || '').toLowerCase() === todayDayName.toLowerCase());

        // Update KPI values
        const totalEl = document.getElementById('kpiTotalClasses');
        if (totalEl) totalEl.innerText = `${allItems.length}`;

        const todayEl = document.getElementById('kpiTodayClasses');
        if (todayEl) todayEl.innerText = `${todayClasses.length}`;

        const facEl = document.getElementById('kpiFacultyCount');
        if (facEl) facEl.innerText = `${distinctFaculty.size}`;

        const roomEl = document.getElementById('kpiRoomsCount');
        if (roomEl) roomEl.innerText = `${distinctRooms.size}`;

        // Context Bar
        const titleEl = document.getElementById('ttContextTitle');
        if (titleEl) {
            titleEl.innerText = `${state.department} • Semester ${state.semester} • Division ${state.division}`;
        }

        const subTitleEl = document.getElementById('ttContextSubtitle');
        if (subTitleEl) {
            subTitleEl.innerText = `${state.program} • Weekly Schedule Matrix`;
        }

        const classCountEl = document.getElementById('ttContextClassCount');
        if (classCountEl) classCountEl.innerText = `${filtered.length} Classes`;

        const facCountEl = document.getElementById('ttContextFacultyCount');
        if (facCountEl) facCountEl.innerText = `${distinctFaculty.size} Faculty`;

        const rmCountEl = document.getElementById('ttContextRoomCount');
        if (rmCountEl) rmCountEl.innerText = `${distinctRooms.size} Rooms`;
    }

    function updateDayCountBadges() {
        const counts = {
            Monday: 0,
            Tuesday: 0,
            Wednesday: 0,
            Thursday: 0,
            Friday: 0,
            Saturday: 0
        };

        state.items.forEach(it => {
            if (it.day && counts[it.day] !== undefined) {
                counts[it.day]++;
            }
        });

        const map = {
            Monday: 'countMon',
            Tuesday: 'countTue',
            Wednesday: 'countWed',
            Thursday: 'countThu',
            Friday: 'countFri',
            Saturday: 'countSat'
        };

        Object.keys(map).forEach(day => {
            const el = document.getElementById(map[day]);
            if (el) el.innerText = counts[day];
        });
    }

    function renderActiveFilterChips() {
        const chipsBar = document.getElementById('ttActiveChipsBar');
        const container = document.getElementById('ttActiveChipsContainer');
        if (!chipsBar || !container) return;

        const chips = [];

        chips.push({ label: `${state.program}`, key: 'program' });
        chips.push({ label: `Sem ${state.semester}`, key: 'semester' });
        chips.push({ label: `Div ${state.division}`, key: 'division' });

        if (state.dayFilter) {
            chips.push({ label: `Day: ${state.dayFilter}`, key: 'day', removable: true });
        }

        if (state.search) {
            chips.push({ label: `Search: "${state.search}"`, key: 'search', removable: true });
        }

        container.innerHTML = chips.map(c => `
            <span class="filter-chip">
                <span>${escapeHtml(c.label)}</span>
                ${c.removable ? `<span class="filter-chip-remove" onclick="window.removeFilterChip('${c.key}')"><i data-lucide="x" class="w-3 h-3"></i></span>` : ''}
            </span>
        `).join('');

        chipsBar.classList.remove('hidden');
    }

    window.removeFilterChip = function(key) {
        if (key === 'day') {
            state.dayFilter = '';
            const daySelect = document.getElementById('ttDaySelect');
            if (daySelect) daySelect.value = '';
        } else if (key === 'search') {
            state.search = '';
            const searchInput = document.getElementById('ttSearchInput');
            if (searchInput) searchInput.value = '';
            const clearBtn = document.getElementById('ttSearchClearBtn');
            if (clearBtn) clearBtn.classList.add('hidden');
        }
        renderTimetableViews();
    };

    // =========================================================================
    // DESKTOP MATRIX TABLE RENDERING (>= 768px)
    // =========================================================================

    function renderDesktopMatrix() {
        const gridBody = document.getElementById('timetableGridBody');
        if (!gridBody) return;

        const filteredItems = getFilteredItems();
        const conflictIds = detectConflicts(state.items);
        const activeDays = state.dayFilter ? [state.dayFilter] : DAYS;

        // Build header
        const headerTr = document.getElementById('timetableHeaderRow');
        if (headerTr) {
            headerTr.innerHTML = `<th class="time-col text-left">TIME / SLOT</th>` +
                activeDays.map(d => `<th class="text-center">${d.toUpperCase()}</th>`).join('');
        }

        if (!filteredItems.length) {
            gridBody.innerHTML = `
                <tr>
                    <td colspan="${activeDays.length + 1}" class="text-center py-12 text-[#66708F] bg-white">
                        <div class="w-12 h-12 rounded-2xl bg-[#E8EBFA] text-[#8B5CF6] flex items-center justify-center mx-auto mb-3 shadow-sm">
                            <i data-lucide="calendar-x" class="w-6 h-6"></i>
                        </div>
                        <h4 class="text-sm font-bold text-[#171D3A] mb-1">No Schedule Entries Found</h4>
                        <p class="text-xs text-[#66708F] mb-3">No classes match the selected program, semester, division or search query.</p>
                        <button type="button" class="btn-primary-custom text-xs font-bold mx-auto py-2 px-4" onclick="window.quickAddSlot('Monday', '09:00', '10:00')">
                            <i data-lucide="plus"></i> Add First Schedule
                        </button>
                    </td>
                </tr>
            `;
            return;
        }

        gridBody.innerHTML = TIME_SLOTS.map(slot => {
            const dayCells = activeDays.map(day => {
                // Find matching entries for this slot and day
                const matches = filteredItems.filter(it => {
                    const dayMatch = (it.day || '').toLowerCase() === day.toLowerCase();
                    const startTime = String(it.start_time || '').trim();
                    const slotStart = String(slot.start).trim();
                    const slotStartPrefix = slotStart.slice(0, 2);

                    const timeMatch = startTime.startsWith(slotStartPrefix) ||
                                      (slot.start24 && startTime.startsWith(slot.start24.slice(0, 2))) ||
                                      (it.time && it.time.includes(slotStart));

                    return dayMatch && timeMatch;
                });

                if (matches.length === 0) {
                    return `
                        <td>
                            <div class="timetable-empty-cell" onclick="window.quickAddSlot('${day}', '${slot.start}', '${slot.end}')" title="Click to schedule class on ${day} at ${slot.label}">
                                <i data-lucide="plus" class="w-4 h-4 opacity-40"></i>
                            </div>
                        </td>
                    `;
                }

                return `
                    <td>
                        <div class="space-y-2">
                            ${matches.map(m => {
                                const hasConflict = conflictIds.has(m.id);
                                return `
                                    <div class="timetable-slot-card ${hasConflict ? 'has-conflict' : ''}" onclick="window.viewSlotDetails('${escapeQuotes(m.id)}')">
                                        <div class="flex items-center justify-between gap-1 mb-1">
                                            <h5 class="text-xs font-bold text-[#171D3A] m-0 truncate" title="${escapeHtml(m.subject)}">${escapeHtml(m.subject || 'Lecture')}</h5>
                                            <span class="text-[10px] font-mono font-bold px-1.5 py-0.5 rounded-lg bg-[#E8EBFA] text-[#8B5CF6]">${escapeHtml(m.room || 'Room')}</span>
                                        </div>
                                        <div class="flex items-center justify-between text-[11px] text-[#66708F]">
                                            <span class="truncate flex items-center gap-1 font-medium">
                                                <i data-lucide="user" class="w-3 h-3 text-[#8B5CF6]"></i> ${escapeHtml(m.faculty || 'Faculty')}
                                            </span>
                                        </div>
                                        ${hasConflict ? `
                                            <div class="mt-1 flex items-center gap-1 text-[10px] font-bold text-amber-700">
                                                <i data-lucide="alert-triangle" class="w-3 h-3 text-amber-600"></i> Overlap Conflict
                                            </div>
                                        ` : ''}
                                    </div>
                                `;
                            }).join('')}
                        </div>
                    </td>
                `;
            }).join('');

            return `
                <tr>
                    <td class="time-col-cell">
                        <div class="flex items-center gap-1.5">
                            <i data-lucide="clock" class="w-3.5 h-3.5 text-[#8B5CF6] flex-shrink-0"></i>
                            <span>${slot.label}</span>
                        </div>
                    </td>
                    ${dayCells}
                </tr>
            `;
        }).join('');
    }

    // =========================================================================
    // MOBILE TIMELINE RENDERING (< 768px)
    // =========================================================================

    function renderMobileTimeline() {
        const mobileSchedule = document.getElementById('timetableMobileSchedule');
        if (!mobileSchedule) return;

        const currentDay = state.selectedDay || 'Monday';
        const filteredItems = getFilteredItems();
        const conflictIds = detectConflicts(state.items);

        const dayItems = filteredItems
            .filter(item => (item.day || '').toLowerCase() === currentDay.toLowerCase())
            .sort((a, b) => String(a.start_time || '').localeCompare(String(b.start_time || '')));

        if (!dayItems.length) {
            mobileSchedule.innerHTML = `
                <div class="text-center py-10 bg-white border border-[#E1E5F0] rounded-2xl p-6 shadow-sm">
                    <div class="w-12 h-12 rounded-2xl bg-[#E8EBFA] text-[#8B5CF6] flex items-center justify-center mx-auto mb-3 shadow-sm">
                        <i data-lucide="calendar-x" class="w-6 h-6"></i>
                    </div>
                    <h4 class="text-sm font-bold text-[#171D3A] mb-1">No Classes on ${currentDay}</h4>
                    <p class="text-xs text-[#66708F] mb-4">No scheduled lectures for ${state.department} on ${currentDay}.</p>
                    <button type="button" class="btn-primary-custom text-xs font-bold mx-auto py-2 px-4 shadow-sm" onclick="window.quickAddSlot('${currentDay}', '09:00', '10:00')">
                        <i data-lucide="plus"></i> Add ${currentDay} Lecture
                    </button>
                </div>
            `;
            return;
        }

        // Live Time Check for NOW / NEXT status
        const now = new Date();
        const todayDayIndex = now.getDay();
        const isToday = (todayDayIndex >= 1 && todayDayIndex <= 6 && DAYS[todayDayIndex - 1] === currentDay);
        const currentHours = now.getHours();
        const currentMins = now.getMinutes();
        const currentMinutesTotal = currentHours * 60 + currentMins;

        mobileSchedule.innerHTML = `
            <div class="flex items-center justify-between pb-1 px-1">
                <span class="text-xs font-bold text-[#171D3A] tracking-wider uppercase">${currentDay} Classes (${dayItems.length})</span>
                <button type="button" class="text-xs text-[#8B5CF6] font-bold flex items-center gap-1" onclick="window.quickAddSlot('${currentDay}', '09:00', '10:00')">
                    <i data-lucide="plus-circle" class="w-3.5 h-3.5"></i> Add Slot
                </button>
            </div>

            <div class="space-y-3">
                ${dayItems.map((item, idx) => {
                    const hasConflict = conflictIds.has(item.id);
                    
                    // Parse start & end for now/next
                    let isNow = false;
                    let isNext = false;

                    if (isToday && item.start_time) {
                        const startParts = item.start_time.split(':').map(n => parseInt(n, 10));
                        const endParts = (item.end_time || '').split(':').map(n => parseInt(n, 10));
                        if (startParts.length >= 2 && endParts.length >= 2) {
                            let startMin = startParts[0] * 60 + startParts[1];
                            let endMin = endParts[0] * 60 + endParts[1];
                            // Adjust for PM hours if format is 02:00
                            if (startParts[0] < 8) startMin += 12 * 60;
                            if (endParts[0] < 8) endMin += 12 * 60;

                            if (currentMinutesTotal >= startMin && currentMinutesTotal <= endMin) {
                                isNow = true;
                            } else if (currentMinutesTotal < startMin && idx === 0) {
                                isNext = true;
                            }
                        }
                    }

                    return `
                        <div class="mobile-schedule-card ${isNow ? 'is-now' : isNext ? 'is-next' : ''}">
                            <!-- Top Status & Time Row -->
                            <div class="flex items-center justify-between gap-2 mb-2">
                                <div class="flex items-center gap-1.5">
                                    <span class="inline-flex items-center gap-1 px-2 py-0.5 rounded-lg bg-[#E8EBFA] text-[#8B5CF6] font-mono text-xs font-bold">
                                        <i data-lucide="clock" class="w-3 h-3"></i> ${escapeHtml(item.start_time || '')} - ${escapeHtml(item.end_time || '')}
                                    </span>
                                    ${isNow ? `<span class="badge-now"><span class="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-ping"></span> NOW</span>` : ''}
                                    ${isNext ? `<span class="badge-next">NEXT</span>` : ''}
                                </div>
                                <span class="px-2 py-0.5 rounded-lg bg-[#F8F9FE] border border-[#E1E5F0] text-[#171D3A] font-mono text-xs font-bold">
                                    <i data-lucide="map-pin" class="w-3 h-3 text-[#8B5CF6] inline"></i> ${escapeHtml(item.room || 'Room')}
                                </span>
                            </div>

                            <!-- Subject Title -->
                            <h4 class="text-sm font-bold text-[#171D3A] mb-2">${escapeHtml(item.subject || 'Scheduled Lecture')}</h4>

                            <!-- Faculty & Academic Meta -->
                            <div class="flex items-center justify-between text-xs text-[#66708F] gap-2 pt-2 border-t border-[#E1E5F0]">
                                <div class="flex items-center gap-1.5 truncate">
                                    <div class="w-5 h-5 rounded-full bg-[#E8EBFA] text-[#8B5CF6] flex items-center justify-center text-[10px] font-bold">
                                        <i data-lucide="user" class="w-3 h-3"></i>
                                    </div>
                                    <span class="font-semibold text-[#171D3A] truncate">${escapeHtml(item.faculty || 'Faculty In-Charge')}</span>
                                </div>
                                <span class="text-[11px] text-[#8C95AD] whitespace-nowrap">${escapeHtml(item.program || state.program)} • Sem ${escapeHtml(item.semester || state.semester)}</span>
                            </div>

                            <!-- Overlap Warning -->
                            ${hasConflict ? `
                                <div class="conflict-alert-banner">
                                    <i data-lucide="alert-triangle" class="w-3.5 h-3.5 flex-shrink-0"></i>
                                    <span>Schedule Overlap Conflict Detected</span>
                                </div>
                            ` : ''}

                            <!-- Card Bottom Actions -->
                            <div class="pt-3 mt-2.5 border-t border-[#E1E5F0] flex items-center justify-end gap-1.5">
                                <button type="button" class="px-3 py-1.5 rounded-xl bg-[#F8F9FE] border border-[#E1E5F0] text-[#171D3A] text-xs font-semibold hover:bg-[#E8EBFA]" onclick="window.viewSlotDetails('${escapeQuotes(item.id)}')">
                                    Details
                                </button>
                                <button type="button" class="px-3 py-1.5 rounded-xl bg-white border border-[#E1E5F0] text-[#8B5CF6] text-xs font-bold hover:bg-[#E8EBFA]" onclick="window.editSlot('${escapeQuotes(item.id)}')">
                                    Edit
                                </button>
                                <button type="button" class="p-1.5 rounded-xl bg-white border border-[#E1E5F0] text-[#8C95AD] hover:text-red-600 hover:bg-red-50" onclick="window.deleteSlot('${escapeQuotes(item.id)}')">
                                    <i data-lucide="trash-2" class="w-3.5 h-3.5"></i>
                                </button>
                            </div>
                        </div>
                    `;
                }).join('')}
            </div>
        `;
    }

    // =========================================================================
    // CRUD OPERATIONS: ADD, EDIT, DELETE, DETAILS
    // =========================================================================

    window.quickAddSlot = function(day, startTime, endTime) {
        document.getElementById('ttModalTitle').innerText = 'Add Lecture Schedule';
        document.getElementById('ttModalSubtitle').innerText = 'Assign subject, faculty, classroom and time allocation';
        document.getElementById('slotSubmitBtn').innerText = 'Save Schedule';

        document.getElementById('ttSlotId').value = '';
        document.getElementById('timetableForm').reset();

        document.getElementById('slotProgram').value = state.program;
        document.getElementById('slotDepartment').value = state.department;
        document.getElementById('slotSemester').value = state.semester;
        document.getElementById('slotDivision').value = state.division;
        document.getElementById('slotDay').value = day || state.selectedDay || 'Monday';
        document.getElementById('slotStartTime').value = startTime || '09:00';
        document.getElementById('slotEndTime').value = endTime || '10:00';

        if (slotModal) slotModal.show();
    };

    window.editSlot = function(slotId) {
        const item = state.items.find(it => String(it.id) === String(slotId));
        if (!item) return;

        document.getElementById('ttModalTitle').innerText = 'Edit Lecture Schedule';
        document.getElementById('ttModalSubtitle').innerText = 'Update class timing, faculty, or classroom assignment';
        document.getElementById('slotSubmitBtn').innerText = 'Save Changes';

        document.getElementById('ttSlotId').value = item.id;
        document.getElementById('slotProgram').value = item.program || state.program;
        document.getElementById('slotDepartment').value = item.department || state.department;
        document.getElementById('slotYear').value = item.year || 'FY';
        document.getElementById('slotSemester').value = item.semester || state.semester;
        document.getElementById('slotDivision').value = item.division || state.division;
        document.getElementById('slotDay').value = item.day || 'Monday';
        document.getElementById('slotStartTime').value = item.start_time || '09:00';
        document.getElementById('slotEndTime').value = item.end_time || '10:00';
        document.getElementById('slotSubject').value = item.subject || '';
        document.getElementById('slotFaculty').value = item.faculty || '';
        document.getElementById('slotRoom').value = item.room || '';

        if (detailsModal) detailsModal.hide();
        if (slotModal) slotModal.show();
    };

    window.viewSlotDetails = function(slotId) {
        const item = state.items.find(it => String(it.id) === String(slotId));
        if (!item) return;

        const container = document.getElementById('timetableDetailsContent');
        if (!container) return;

        container.innerHTML = `
            <div class="space-y-4 text-xs">
                <!-- Primary Header Card -->
                <div class="p-4 rounded-2xl bg-[#F8F9FE] border border-[#E1E5F0]">
                    <span class="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg bg-[#E8EBFA] text-[#8B5CF6] font-mono font-bold text-xs mb-2">
                        <i data-lucide="clock" class="w-3.5 h-3.5"></i> ${escapeHtml(item.day || '')} • ${escapeHtml(item.start_time || '')} - ${escapeHtml(item.end_time || '')}
                    </span>
                    <h3 class="text-base font-bold text-[#171D3A] mb-1">${escapeHtml(item.subject || 'Lecture Schedule')}</h3>
                    <p class="text-xs text-[#8B5CF6] font-semibold mb-0">${escapeHtml(item.faculty || 'Faculty In-Charge')}</p>
                </div>

                <!-- 2-Column Info Grid -->
                <div class="grid grid-cols-2 gap-2.5">
                    <div class="p-3 rounded-xl bg-[#F8F9FE] border border-[#E1E5F0]">
                        <span class="text-[#8C95AD] block text-[10px] uppercase font-bold tracking-wider mb-0.5">Program</span>
                        <span class="text-[#171D3A] font-bold text-xs">${escapeHtml(item.program || state.program)}</span>
                    </div>
                    <div class="p-3 rounded-xl bg-[#F8F9FE] border border-[#E1E5F0]">
                        <span class="text-[#8C95AD] block text-[10px] uppercase font-bold tracking-wider mb-0.5">Department</span>
                        <span class="text-[#171D3A] font-bold text-xs">${escapeHtml(item.department || state.department)}</span>
                    </div>
                    <div class="p-3 rounded-xl bg-[#F8F9FE] border border-[#E1E5F0]">
                        <span class="text-[#8C95AD] block text-[10px] uppercase font-bold tracking-wider mb-0.5">Semester &amp; Div</span>
                        <span class="text-[#171D3A] font-bold text-xs">Sem ${escapeHtml(item.semester || state.semester)} • Div ${escapeHtml(item.division || state.division)}</span>
                    </div>
                    <div class="p-3 rounded-xl bg-[#F8F9FE] border border-[#E1E5F0]">
                        <span class="text-[#8C95AD] block text-[10px] uppercase font-bold tracking-wider mb-0.5">Classroom / Lab</span>
                        <span class="text-[#171D3A] font-bold font-mono text-xs">${escapeHtml(item.room || 'TBA')}</span>
                    </div>
                </div>
            </div>
        `;

        const editBtn = document.getElementById('detailsEditBtn');
        if (editBtn) {
            editBtn.onclick = () => window.editSlot(item.id);
        }

        const delBtn = document.getElementById('detailsDeleteBtn');
        if (delBtn) {
            delBtn.onclick = () => {
                if (detailsModal) detailsModal.hide();
                window.deleteSlot(item.id);
            };
        }

        if (detailsModal) detailsModal.show();
        if (window.lucide) lucide.createIcons();
    };

    async function handleSlotFormSubmit(e) {
        e.preventDefault();
        const recordId = document.getElementById('ttSlotId').value;
        const payload = {
            program: document.getElementById('slotProgram').value,
            department: document.getElementById('slotDepartment').value,
            year: document.getElementById('slotYear').value,
            semester: document.getElementById('slotSemester').value,
            division: document.getElementById('slotDivision').value.trim(),
            day: document.getElementById('slotDay').value,
            start_time: document.getElementById('slotStartTime').value,
            end_time: document.getElementById('slotEndTime').value,
            subject: document.getElementById('slotSubject').value.trim(),
            faculty: document.getElementById('slotFaculty').value.trim(),
            room: document.getElementById('slotRoom').value.trim()
        };

        const isEdit = Boolean(recordId);
        const url = isEdit ? `/admin/api/crud/timetable/${recordId}` : '/admin/api/crud/timetable';
        const method = isEdit ? 'PUT' : 'POST';

        try {
            const res = await fetch(url, {
                method: method,
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            const data = await res.json();
            if (res.ok && data.status === 'success') {
                showAdminToast(data.message || (isEdit ? 'Schedule updated.' : 'Schedule created.'), 'success');
                if (slotModal) slotModal.hide();
                loadTimetable();
            } else {
                showAdminToast(data.message || 'Error saving timetable slot.', 'error');
            }
        } catch (err) {
            showAdminToast(err.message || 'Error saving slot.', 'error');
        }
    }

    window.deleteSlot = function(slotId) {
        const item = state.items.find(it => String(it.id) === String(slotId));
        if (!item) return;

        state.pendingDeleteId = slotId;
        state.pendingDeleteDoc = item;

        const textEl = document.getElementById('deleteSlotDetailsText');
        if (textEl) {
            textEl.innerHTML = `Are you sure you want to remove <strong>${escapeHtml(item.subject)}</strong> (${escapeHtml(item.day)} ${escapeHtml(item.start_time)}-${escapeHtml(item.end_time)}) in room <span class="font-mono text-[#8B5CF6]">${escapeHtml(item.room)}</span>?`;
        }

        if (deleteModal) deleteModal.show();
    };

    async function handleConfirmDelete() {
        if (!state.pendingDeleteId) return;

        try {
            const res = await fetch(`/admin/api/crud/timetable/${state.pendingDeleteId}`, { method: 'DELETE' });
            const data = await res.json();
            if (res.ok && data.status === 'success') {
                showAdminToast(data.message, 'success');
                deleteModal.hide();
                loadTimetable();
            } else {
                showAdminToast(data.message || 'Failed to delete slot.', 'error');
            }
        } catch (err) {
            showAdminToast(err.message, 'error');
        }
    }
})();
