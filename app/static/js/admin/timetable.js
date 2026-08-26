/**
 * SVIT Admin - Page 7: Timetable Weekly Matrix Controller
 * Builds the interactive weekly schedule matrix (Monday-Saturday vs Time Slots),
 * supports departmental & semester filtering, lecture slot creation, edit, and deletion.
 */

(function() {
    'use strict';

    const DAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
    const TIME_SLOTS = [
        { label: '09:00 - 10:00', start: '09:00', end: '10:00' },
        { label: '10:00 - 11:00', start: '10:00', end: '11:00' },
        { label: '11:15 - 12:15', start: '11:15', end: '12:15' },
        { label: '12:15 - 01:15', start: '12:15', end: '13:15' },
        { label: '02:00 - 03:00', start: '14:00', end: '15:00' },
        { label: '03:00 - 04:00', start: '15:00', end: '16:00' }
    ];

    const state = {
        department: 'Computer Engineering',
        semester: '5',
        division: 'A',
        dayFilter: '',
        items: [],
        pendingDeleteId: null
    };

    let slotModal = null;
    let deleteModal = null;

    document.addEventListener('DOMContentLoaded', function() {
        const slotModalEl = document.getElementById('timetableSlotModal');
        const deleteModalEl = document.getElementById('timetableDeleteModal');

        if (slotModalEl) slotModal = new bootstrap.Modal(slotModalEl);
        if (deleteModalEl) deleteModal = new bootstrap.Modal(deleteModalEl);

        bindEvents();
        loadTimetable();
    });

    function bindEvents() {
        const deptSelect = document.getElementById('ttDeptFilter');
        if (deptSelect) {
            deptSelect.addEventListener('change', (e) => {
                state.department = e.target.value;
                loadTimetable();
            });
        }

        const semSelect = document.getElementById('ttSemFilter');
        if (semSelect) {
            semSelect.addEventListener('change', (e) => {
                state.semester = e.target.value;
                loadTimetable();
            });
        }

        const divSelect = document.getElementById('ttDivFilter');
        if (divSelect) {
            divSelect.addEventListener('change', (e) => {
                state.division = e.target.value;
                loadTimetable();
            });
        }

        const daySelect = document.getElementById('ttDayFilter');
        if (daySelect) {
            daySelect.addEventListener('change', (e) => {
                state.dayFilter = e.target.value;
                renderTimetableGrid();
            });
        }

        const refreshBtn = document.getElementById('refreshTimetableBtn');
        if (refreshBtn) refreshBtn.addEventListener('click', loadTimetable);

        const addSlotBtn = document.getElementById('openAddSlotModalBtn');
        if (addSlotBtn) {
            addSlotBtn.addEventListener('click', () => {
                document.getElementById('ttModalTitle').innerText = 'Add Lecture Slot';
                document.getElementById('ttSlotId').value = '';
                document.getElementById('timetableForm').reset();
                document.getElementById('slotDepartment').value = state.department;
                document.getElementById('slotSemester').value = state.semester;
                document.getElementById('slotDivision').value = state.division;
                slotModal.show();
            });
        }

        const form = document.getElementById('timetableForm');
        if (form) form.addEventListener('submit', handleSlotFormSubmit);

        const confirmDeleteBtn = document.getElementById('confirmDeleteSlotBtn');
        if (confirmDeleteBtn) confirmDeleteBtn.addEventListener('click', handleConfirmDelete);
    }

    async function loadTimetable() {
        const gridBody = document.getElementById('timetableGridBody');
        if (!gridBody) return;

        gridBody.innerHTML = `
            <tr>
                <td colspan="7" class="text-center py-12 text-gray-400 text-xs">
                    <div class="w-5 h-5 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin mx-auto mb-2"></div>
                    Loading weekly schedule for ${state.department} (Sem ${state.semester})...
                </td>
            </tr>
        `;

        const params = new URLSearchParams({
            limit: 500,
            filter_department: state.department,
            filter_semester: state.semester
        });

        try {
            const res = await fetch(`/admin/api/crud/timetable?${params.toString()}`);
            const data = await res.json();
            if (data.status === 'success') {
                state.items = data.items || [];
                renderTimetableGrid();
            } else {
                gridBody.innerHTML = `<tr><td colspan="7" class="text-center py-6 text-red-400 text-xs">${data.message}</td></tr>`;
            }
        } catch (err) {
            gridBody.innerHTML = `<tr><td colspan="7" class="text-center py-6 text-red-400 text-xs">${err.message}</td></tr>`;
        }
        lucide.createIcons();
    }

    function renderTimetableGrid() {
        const gridBody = document.getElementById('timetableGridBody');
        const mobileSchedule = document.getElementById('timetableMobileSchedule');
        if (!gridBody) return;

        const activeDays = state.dayFilter ? [state.dayFilter] : DAYS;

        // Build header
        const headerTr = document.getElementById('timetableHeaderRow');
        if (headerTr) {
            headerTr.innerHTML = `<th class="time-col">TIME / SLOT</th>` + activeDays.map(d => `<th class="text-center">${d.toUpperCase()}</th>`).join('');
        }

        gridBody.innerHTML = TIME_SLOTS.map(slot => {
            const dayCells = activeDays.map(day => {
                // Find matching entries
                const matches = state.items.filter(it => {
                    const dayMatch = it.day && it.day.toLowerCase() === day.toLowerCase();
                    const timeMatch = (it.start_time && it.start_time.startsWith(slot.start.slice(0, 2))) ||
                                      (it.time && it.time.includes(slot.start));
                    return dayMatch && timeMatch;
                });

                if (matches.length === 0) {
                    return `
                        <td>
                            <div class="h-full flex items-center justify-center text-[11px] text-gray-700 hover:text-gray-500 cursor-pointer transition border border-dashed border-transparent hover:border-gray-800 rounded-lg p-2" onclick="window.quickAddSlot('${day}', '${slot.start}', '${slot.end}')">
                                <i data-lucide="plus" class="w-3.5 h-3.5 opacity-40"></i>
                            </div>
                        </td>
                    `;
                }

                return `
                    <td>
                        <div class="space-y-1.5 h-full">
                            ${matches.map(m => `
                                <div class="lecture-card" onclick="window.editSlot('${m.id}')">
                                    <div>
                                        <h5 class="lecture-subject">${m.subject || 'Lecture'}</h5>
                                        <div class="lecture-meta">
                                            <i data-lucide="user" class="w-3 h-3"></i>
                                            <span class="truncate">${m.faculty || 'Faculty'}</span>
                                        </div>
                                    </div>
                                    <div class="flex items-center justify-between mt-1">
                                        <span class="lecture-room"><i data-lucide="map-pin" class="w-2.5 h-2.5 d-inline"></i> ${m.room || 'Room'}</span>
                                        <button class="text-gray-500 hover:text-red-400 p-0.5" onclick="event.stopPropagation(); window.deleteSlot('${m.id}')" title="Delete slot">
                                            <i data-lucide="trash" class="w-3 h-3"></i>
                                        </button>
                                    </div>
                                </div>
                            `).join('')}
                        </div>
                    </td>
                `;
            }).join('');

            return `
                <tr>
                    <td class="time-col">
                        <i data-lucide="clock" class="w-3 h-3 d-inline mr-1 text-indigo-400"></i>
                        ${slot.label}
                    </td>
                    ${dayCells}
                </tr>
            `;
        }).join('');

        if (mobileSchedule) {
            const mobileItems = state.items
                .filter(item => !state.dayFilter || String(item.day || '').toLowerCase() === state.dayFilter.toLowerCase())
                .sort((a, b) => String(a.start_time || '').localeCompare(String(b.start_time || '')));
            mobileSchedule.innerHTML = mobileItems.length ? mobileItems.map(item => `<article class="admin-mobile-schedule-card"><div class="schedule-time"><i data-lucide="clock"></i><span>${escapeHtml(item.start_time || '-')} - ${escapeHtml(item.end_time || '-')}</span></div><div class="schedule-body"><h3>${escapeHtml(item.subject || 'Lecture')}</h3><p><i data-lucide="user"></i>${escapeHtml(item.faculty || 'Faculty')}</p><p><i data-lucide="map-pin"></i>${escapeHtml(item.room || 'Room')}</p></div><button type="button" class="schedule-edit" onclick="window.editSlot('${escapeQuotes(item.id)}')" aria-label="Edit ${escapeQuotes(item.subject || 'lecture')}"><i data-lucide="edit-2"></i></button></article>`).join('') : '<div class="admin-mobile-empty">No lecture slots found for this selection.</div>';
        }

        lucide.createIcons();
    }

    function escapeHtml(value) {
        return String(value || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#039;');
    }

    function escapeQuotes(value) {
        return String(value || '').replace(/\\/g, '\\\\').replace(/'/g, "\\'");
    }

    window.quickAddSlot = function(day, startTime, endTime) {
        document.getElementById('ttModalTitle').innerText = `Add Slot for ${day}`;
        document.getElementById('ttSlotId').value = '';
        document.getElementById('timetableForm').reset();
        document.getElementById('slotDepartment').value = state.department;
        document.getElementById('slotSemester').value = state.semester;
        document.getElementById('slotDivision').value = state.division;
        document.getElementById('slotDay').value = day;
        document.getElementById('slotStartTime').value = startTime;
        document.getElementById('slotEndTime').value = endTime;
        slotModal.show();
    };

    window.editSlot = function(id) {
        const slot = state.items.find(s => String(s.id) === String(id));
        if (!slot) return;

        document.getElementById('ttModalTitle').innerText = 'Edit Lecture Slot';
        document.getElementById('ttSlotId').value = id;
        document.getElementById('slotDepartment').value = slot.department || state.department;
        document.getElementById('slotSemester').value = slot.semester || state.semester;
        document.getElementById('slotDivision').value = slot.division || state.division;
        document.getElementById('slotDay').value = slot.day || 'Monday';
        document.getElementById('slotStartTime').value = slot.start_time || '09:00';
        document.getElementById('slotEndTime').value = slot.end_time || '10:00';
        document.getElementById('slotSubject').value = slot.subject || '';
        document.getElementById('slotFaculty').value = slot.faculty || '';
        document.getElementById('slotRoom').value = slot.room || '';

        slotModal.show();
    };

    window.deleteSlot = function(id) {
        state.pendingDeleteId = id;
        document.getElementById('deleteSlotTargetId').innerText = id;
        deleteModal.show();
    };

    async function handleSlotFormSubmit(e) {
        e.preventDefault();
        const slotId = document.getElementById('ttSlotId').value;
        const payload = {
            id: slotId || `TT-${Date.now()}`,
            department: document.getElementById('slotDepartment').value,
            semester: parseInt(document.getElementById('slotSemester').value, 10) || 1,
            division: document.getElementById('slotDivision').value,
            day: document.getElementById('slotDay').value,
            start_time: document.getElementById('slotStartTime').value,
            end_time: document.getElementById('slotEndTime').value,
            subject: document.getElementById('slotSubject').value.trim(),
            faculty: document.getElementById('slotFaculty').value.trim(),
            room: document.getElementById('slotRoom').value.trim()
        };

        const isEdit = Boolean(slotId);
        const url = isEdit ? `/admin/api/crud/timetable/${slotId}` : '/admin/api/crud/timetable';
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
                slotModal.hide();
                loadTimetable();
            } else {
                showAdminToast(data.message || 'Failed to save timetable slot.', 'error');
            }
        } catch (err) {
            showAdminToast(err.message, 'error');
        }
    }

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
