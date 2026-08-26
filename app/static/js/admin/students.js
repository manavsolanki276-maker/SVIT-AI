/**
 * SVIT Admin - Page 5: Students Controller
 * Handles student roster querying, status tabs (All, Pending, Active, Rejected),
 * approval and rejection workflow, audit trail viewing, and record management.
 */

(function() {
    'use strict';

    const urlParams = new URLSearchParams(window.location.search);
    const initialStatus = urlParams.get('status') || '';

    const state = {
        moduleKey: 'students',
        search: '',
        department: '',
        semester: '',
        status: initialStatus,
        page: 1,
        limit: 50,
        total: 0,
        items: [],
        pendingDeleteId: null,
        pendingAcceptTarget: null,
        pendingRejectTarget: null
    };

    let studentFormModal = null;
    let studentViewModal = null;
    let studentAcceptModal = null;
    let studentRejectModal = null;
    let deleteConfirmModal = null;
    let searchDebounce = null;

    document.addEventListener('DOMContentLoaded', function() {
        const formEl = document.getElementById('studentFormModal');
        const viewEl = document.getElementById('studentViewModal');
        const acceptEl = document.getElementById('studentAcceptModal');
        const rejectEl = document.getElementById('studentRejectModal');
        const delEl = document.getElementById('studentDeleteModal');

        if (formEl) studentFormModal = new bootstrap.Modal(formEl);
        if (viewEl) studentViewModal = new bootstrap.Modal(viewEl);
        if (acceptEl) studentAcceptModal = new bootstrap.Modal(acceptEl);
        if (rejectEl) studentRejectModal = new bootstrap.Modal(rejectEl);
        if (delEl) deleteConfirmModal = new bootstrap.Modal(delEl);

        // Synchronize initial active tab from URL param if present
        if (initialStatus) {
            document.querySelectorAll('.status-tab-btn').forEach(btn => {
                const btnStatus = btn.getAttribute('data-status') || '';
                if (btnStatus.toLowerCase() === initialStatus.toLowerCase()) {
                    btn.classList.add('active');
                } else {
                    btn.classList.remove('active');
                }
            });
        }

        bindEvents();
        loadTabCounts();
        loadStudents();
    });

    function bindEvents() {
        // Status Tabs Click Event
        document.querySelectorAll('.status-tab-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                document.querySelectorAll('.status-tab-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                state.status = btn.getAttribute('data-status') || '';
                state.page = 1;

                // Update URL history smoothly without reload
                const currentUrl = new URL(window.location);
                if (state.status) {
                    currentUrl.searchParams.set('status', state.status);
                } else {
                    currentUrl.searchParams.delete('status');
                }
                window.history.replaceState({}, '', currentUrl);

                loadStudents();
            });
        });

        // Search Input
        const searchInput = document.getElementById('studentSearchInput');
        if (searchInput) {
            searchInput.addEventListener('input', (e) => {
                clearTimeout(searchDebounce);
                searchDebounce = setTimeout(() => {
                    state.search = e.target.value.trim();
                    state.page = 1;
                    loadStudents();
                }, 300);
            });
        }

        // Department Filter
        const deptFilter = document.getElementById('deptFilter');
        if (deptFilter) {
            deptFilter.addEventListener('change', (e) => {
                state.department = e.target.value;
                state.page = 1;
                loadStudents();
            });
        }

        // Semester Filter
        const semFilter = document.getElementById('semFilter');
        if (semFilter) {
            semFilter.addEventListener('change', (e) => {
                state.semester = e.target.value;
                state.page = 1;
                loadStudents();
            });
        }

        // Refresh Button
        const refreshBtn = document.getElementById('refreshStudentsBtn');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => {
                loadTabCounts();
                loadStudents();
            });
        }

        // Open Create Modal
        const openCreateBtn = document.getElementById('openCreateStudentModalBtn');
        if (openCreateBtn) {
            openCreateBtn.addEventListener('click', () => {
                document.getElementById('studentModalTitle').innerText = 'Register New Student';
                document.getElementById('studentFormRecordId').value = '';
                document.getElementById('studentForm').reset();
                document.getElementById('studentEnrollment').disabled = false;
                const stSelect = document.getElementById('studentStatus');
                if (stSelect) stSelect.value = 'active';
                studentFormModal.show();
            });
        }

        // Form Submit
        const form = document.getElementById('studentForm');
        if (form) form.addEventListener('submit', handleStudentFormSubmit);

        // Confirm Accept Student Button
        const confirmAcceptBtn = document.getElementById('confirmAcceptStudentBtn');
        if (confirmAcceptBtn) confirmAcceptBtn.addEventListener('click', handleConfirmAccept);

        // Confirm Reject Student Button
        const confirmRejectBtn = document.getElementById('confirmRejectStudentBtn');
        if (confirmRejectBtn) confirmRejectBtn.addEventListener('click', handleConfirmReject);

        // Confirm Delete Button
        const confirmDeleteBtn = document.getElementById('confirmDeleteStudentBtn');
        if (confirmDeleteBtn) confirmDeleteBtn.addEventListener('click', handleConfirmDelete);

        // Pagination Buttons
        const prevBtn = document.getElementById('prevPageBtn');
        if (prevBtn) {
            prevBtn.addEventListener('click', () => {
                if (state.page > 1) {
                    state.page--;
                    loadStudents();
                }
            });
        }

        const nextBtn = document.getElementById('nextPageBtn');
        if (nextBtn) {
            nextBtn.addEventListener('click', () => {
                const maxPage = Math.ceil(state.total / state.limit) || 1;
                if (state.page < maxPage) {
                    state.page++;
                    loadStudents();
                }
            });
        }
    }

    async function loadTabCounts() {
        try {
            const [allRes, pendingRes, activeRes, rejectedRes] = await Promise.all([
                fetch('/admin/api/crud/students?limit=1'),
                fetch('/admin/api/crud/students?status=pending&limit=1'),
                fetch('/admin/api/crud/students?status=active&limit=1'),
                fetch('/admin/api/crud/students?status=rejected&limit=1')
            ]);

            const allData = await allRes.json();
            const pendingData = await pendingRes.json();
            const activeData = await activeRes.json();
            const rejectedData = await rejectedRes.json();

            const cAll = document.getElementById('countAll');
            const cPend = document.getElementById('countPending');
            const cAct = document.getElementById('countActive');
            const cRej = document.getElementById('countRejected');

            if (cAll) cAll.innerText = allData.total || 0;
            if (cPend) cPend.innerText = pendingData.total || 0;
            if (cAct) cAct.innerText = activeData.total || 0;
            if (cRej) cRej.innerText = rejectedData.total || 0;
        } catch (e) {
            console.error('Failed to load status tab counts:', e);
        }
    }

    async function loadStudents() {
        const tbody = document.getElementById('studentsTableBody');
        if (!tbody) return;

        tbody.innerHTML = `
            <tr>
                <td colspan="8" class="text-center py-10 text-gray-400 text-xs">
                    <div class="w-5 h-5 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin mx-auto mb-2"></div>
                    Loading students roster...
                </td>
            </tr>
        `;

        const params = new URLSearchParams({
            page: state.page,
            limit: state.limit,
            search: state.search
        });
        if (state.status) params.append('status', state.status);
        if (state.department) params.append('filter_department', state.department);
        if (state.semester) params.append('filter_semester', state.semester);

        try {
            const res = await fetch(`/admin/api/crud/students?${params.toString()}`);
            const data = await res.json();
            if (data.status === 'success') {
                state.items = data.items || [];
                state.total = data.total || 0;
                renderStudentsTable();
                updatePagination();
            } else {
                tbody.innerHTML = `<tr><td colspan="8" class="text-center py-6 text-red-400 text-xs">${data.message}</td></tr>`;
            }
        } catch (err) {
            tbody.innerHTML = `<tr><td colspan="8" class="text-center py-6 text-red-400 text-xs">${err.message}</td></tr>`;
        }
        lucide.createIcons();
    }

    function renderStudentsTable() {
        const tbody = document.getElementById('studentsTableBody');
        const mobileCards = document.getElementById('studentsMobileCards');
        const countBadge = document.getElementById('studentsCountBadge');
        if (countBadge) countBadge.innerText = `${state.total} Students`;

        if (state.items.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="8" class="text-center py-12 text-gray-400 text-xs">
                        <i data-lucide="users" class="w-8 h-8 mx-auto mb-2 text-gray-600"></i>
                        <p class="mb-0">No student records found matching the active filter.</p>
                    </td>
                </tr>
            `;
            if (mobileCards) mobileCards.innerHTML = '<div class="admin-mobile-empty">No student records found matching the active filter.</div>';
            lucide.createIcons();
            return;
        }

        tbody.innerHTML = state.items.map(s => {
            const name = s.full_name || s.name || 'Unnamed Student';
            const enroll = s.enrollment_no || s.id || '-';
            const dept = s.department || '-';
            const sem = s.semester ? `Sem ${s.semester}` : 'Sem 1';
            const email = s.email || '-';
            const phone = s.phone || s.contact_number || '-';
            const status = (s.status || 'active').toLowerCase();
            const createdAt = s.created_at ? new Date(s.created_at).toLocaleDateString([], { month: 'short', day: 'numeric', year: 'numeric' }) : phone;

            let statusBadgeHtml = '';
            if (status === 'pending') {
                statusBadgeHtml = '<span class="badge-status-pending"><i data-lucide="clock" class="w-3 h-3"></i>PENDING</span>';
            } else if (status === 'rejected') {
                statusBadgeHtml = '<span class="badge-status-rejected"><i data-lucide="x-circle" class="w-3 h-3"></i>REJECTED</span>';
            } else {
                statusBadgeHtml = '<span class="badge-status-active"><i data-lucide="check-circle" class="w-3 h-3"></i>ACTIVE</span>';
            }

            const isPending = status === 'pending';

            return `
                <tr class="${isPending ? 'bg-amber-950/10' : ''}">
                    <td>
                        <span class="font-mono text-indigo-400 font-bold text-xs">${enroll}</span>
                    </td>
                    <td>
                        <div class="flex items-center gap-2.5">
                            <div class="student-avatar ${isPending ? 'bg-amber-600/30 text-amber-300' : ''}">
                                ${name.slice(0, 2).toUpperCase()}
                            </div>
                            <div>
                                <p class="text-xs font-bold text-white mb-0">${name}</p>
                                <span class="text-[10px] text-gray-400">${s.program || 'BE'}</span>
                            </div>
                        </div>
                    </td>
                    <td class="text-gray-300 text-xs">${dept}</td>
                    <td><span class="badge-sem">${sem}</span></td>
                    <td class="text-gray-300 text-xs">${email}</td>
                    <td class="text-gray-400 text-xs font-mono">${createdAt}</td>
                    <td>${statusBadgeHtml}</td>
                    <td class="text-end">
                        <div class="inline-flex items-center gap-1.5">
                            <!-- View Button -->
                            <button class="p-1.5 rounded-lg bg-[#0F172A] border border-[#1F2937] text-gray-300 hover:text-white" onclick="window.viewStudent('${enroll}')" title="View Profile">
                                <i data-lucide="eye" class="w-3.5 h-3.5"></i>
                            </button>

                            <!-- Accept Button (Visible on Pending or All) -->
                            ${status !== 'active' ? `
                            <button class="px-2 py-1 rounded-lg bg-emerald-600/20 text-emerald-400 border border-emerald-500/30 hover:bg-emerald-600 hover:text-white text-[11px] font-bold transition flex items-center gap-1" onclick="window.acceptStudent('${enroll}', '${escapeQuotes(name)}')" title="Accept Student">
                                <i data-lucide="check" class="w-3 h-3"></i> Accept
                            </button>
                            ` : ''}

                            <!-- Reject Button (Visible on Pending or Active) -->
                            ${status !== 'rejected' ? `
                            <button class="px-2 py-1 rounded-lg bg-red-600/20 text-red-400 border border-red-500/30 hover:bg-red-600 hover:text-white text-[11px] font-bold transition flex items-center gap-1" onclick="window.rejectStudent('${enroll}', '${escapeQuotes(name)}')" title="Reject Student">
                                <i data-lucide="x" class="w-3 h-3"></i> Reject
                            </button>
                            ` : ''}

                            <!-- Edit Button -->
                            <button class="p-1.5 rounded-lg bg-[#0F172A] border border-[#1F2937] text-gray-300 hover:text-white" onclick="window.editStudent('${enroll}')" title="Edit Student">
                                <i data-lucide="edit-2" class="w-3.5 h-3.5"></i>
                            </button>

                            <!-- Delete Button -->
                            <button class="p-1.5 rounded-lg bg-[#0F172A] border border-[#1F2937] text-red-400 hover:bg-red-500/20" onclick="window.deleteStudent('${enroll}')" title="Delete Student">
                                <i data-lucide="trash-2" class="w-3.5 h-3.5"></i>
                            </button>
                        </div>
                    </td>
                </tr>
            `;
        }).join('');

        if (mobileCards) {
            mobileCards.innerHTML = state.items.map(s => {
                const name = s.full_name || s.name || 'Unnamed Student';
                const enroll = s.enrollment_no || s.id || '-';
                const status = (s.status || 'active').toLowerCase();
                const badge = status === 'pending' ? 'badge-status-pending' : status === 'rejected' ? 'badge-status-rejected' : 'badge-status-active';
                const statusLabel = status.toUpperCase();
                return `<article class="admin-mobile-record-card student-mobile-card">
                    <div class="admin-record-heading"><div class="flex items-center gap-3 min-w-0"><div class="student-avatar">${name.slice(0, 2).toUpperCase()}</div><div class="min-w-0"><h3>${escapeHtml(name)}</h3><p>${escapeHtml(enroll)}</p></div></div><span class="${badge}">${statusLabel}</span></div>
                    <div class="admin-record-meta"><span><b>Program</b>${escapeHtml(s.program || 'BE')}</span><span><b>Department</b>${escapeHtml(s.department || '-')}</span><span><b>Semester</b>Sem ${escapeHtml(String(s.semester || 1))}</span><span><b>Email</b>${escapeHtml(s.email || '-')}</span><span><b>Phone</b>${escapeHtml(s.phone || s.contact_number || '-')}</span></div>
                    <div class="admin-record-actions"><button type="button" onclick="window.viewStudent('${escapeQuotes(enroll)}')" aria-label="View ${escapeQuotes(name)}"><i data-lucide="eye"></i></button><button type="button" onclick="window.editStudent('${escapeQuotes(enroll)}')" aria-label="Edit ${escapeQuotes(name)}"><i data-lucide="edit-2"></i></button><button type="button" class="is-danger" onclick="window.deleteStudent('${escapeQuotes(enroll)}')" aria-label="Delete ${escapeQuotes(name)}"><i data-lucide="trash-2"></i></button></div>
                </article>`;
            }).join('');
        }

        lucide.createIcons();
    }

    function escapeQuotes(str) {
        return (str || '').replace(/'/g, "\\'").replace(/"/g, '&quot;');
    }

    function updatePagination() {
        const start = state.total === 0 ? 0 : (state.page - 1) * state.limit + 1;
        const end = Math.min(state.page * state.limit, state.total);
        const maxPage = Math.ceil(state.total / state.limit) || 1;

        const infoEl = document.getElementById('paginationInfo');
        if (infoEl) infoEl.innerText = `Showing ${start} - ${end} of ${state.total} students`;

        const prevBtn = document.getElementById('prevPageBtn');
        const nextBtn = document.getElementById('nextPageBtn');
        if (prevBtn) prevBtn.disabled = state.page <= 1;
        if (nextBtn) nextBtn.disabled = state.page >= maxPage;
    }

    async function handleStudentFormSubmit(e) {
        e.preventDefault();
        const recordId = document.getElementById('studentFormRecordId').value;
        const payload = {
            enrollment_no: document.getElementById('studentEnrollment').value.trim(),
            full_name: document.getElementById('studentFullName').value.trim(),
            email: document.getElementById('studentEmail').value.trim(),
            program: document.getElementById('studentProgram').value,
            department: document.getElementById('studentDepartment').value,
            semester: parseInt(document.getElementById('studentSemester').value, 10) || 1,
            division: document.getElementById('studentDivision').value.trim(),
            phone: document.getElementById('studentPhone').value.trim(),
            status: document.getElementById('studentStatus') ? document.getElementById('studentStatus').value : 'active'
        };

        const isEdit = Boolean(recordId);
        const url = isEdit ? `/admin/api/crud/students/${recordId}` : '/admin/api/crud/students';
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
                studentFormModal.hide();
                loadTabCounts();
                loadStudents();
            } else {
                showAdminToast(data.message || 'Error saving student record.', 'error');
            }
        } catch (err) {
            showAdminToast(err.message, 'error');
        }
    }

    window.acceptStudent = function(enroll, name) {
        state.pendingAcceptTarget = { enroll, name };
        document.getElementById('acceptStudentTargetName').innerText = name || 'Student';
        document.getElementById('acceptStudentTargetEnroll').innerText = enroll;
        studentAcceptModal.show();
    };

    async function handleConfirmAccept() {
        if (!state.pendingAcceptTarget) return;
        const { enroll } = state.pendingAcceptTarget;

        try {
            const res = await fetch(`/admin/api/students/${encodeURIComponent(enroll)}/approve`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            });
            const data = await res.json();
            if (res.ok && data.status === 'success') {
                showAdminToast('Student registration approved successfully.', 'success');
                studentAcceptModal.hide();
                if (studentViewModal) studentViewModal.hide();
                loadTabCounts();
                loadStudents();
            } else {
                showAdminToast(data.message || 'Failed to approve student.', 'error');
            }
        } catch (err) {
            showAdminToast(err.message, 'error');
        }
    }

    window.rejectStudent = function(enroll, name) {
        state.pendingRejectTarget = { enroll, name };
        document.getElementById('rejectStudentTargetName').innerText = name || 'Student';
        document.getElementById('rejectStudentTargetEnroll').innerText = enroll;
        document.getElementById('studentRejectReason').value = '';
        studentRejectModal.show();
    };

    async function handleConfirmReject() {
        if (!state.pendingRejectTarget) return;
        const { enroll } = state.pendingRejectTarget;
        const reason = document.getElementById('studentRejectReason').value.trim();

        try {
            const res = await fetch(`/admin/api/students/${encodeURIComponent(enroll)}/reject`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ reason: reason })
            });
            const data = await res.json();
            if (res.ok && data.status === 'success') {
                showAdminToast('Student registration rejected.', 'warning');
                studentRejectModal.hide();
                if (studentViewModal) studentViewModal.hide();
                loadTabCounts();
                loadStudents();
            } else {
                showAdminToast(data.message || 'Failed to reject student.', 'error');
            }
        } catch (err) {
            showAdminToast(err.message, 'error');
        }
    }

    window.editStudent = function(enroll) {
        const student = state.items.find(s => (s.enrollment_no || s.id) === enroll);
        if (!student) return;

        document.getElementById('studentModalTitle').innerText = 'Edit Student Details';
        document.getElementById('studentFormRecordId').value = enroll;
        document.getElementById('studentEnrollment').value = student.enrollment_no || enroll;
        document.getElementById('studentEnrollment').disabled = true;
        document.getElementById('studentFullName').value = student.full_name || student.name || '';
        document.getElementById('studentEmail').value = student.email || '';
        document.getElementById('studentProgram').value = student.program || 'BE';
        document.getElementById('studentDepartment').value = student.department || 'Computer Engineering';
        document.getElementById('studentSemester').value = student.semester || 1;
        document.getElementById('studentDivision').value = student.division || '';
        document.getElementById('studentPhone').value = student.phone || student.contact_number || '';
        const stSelect = document.getElementById('studentStatus');
        if (stSelect) stSelect.value = student.status || 'active';

        studentFormModal.show();
    };

    window.viewStudent = function(enroll) {
        const student = state.items.find(s => (s.enrollment_no || s.id) === enroll);
        if (!student) return;

        const container = document.getElementById('studentViewContent');
        const quickActions = document.getElementById('studentViewQuickActions');
        if (!container) return;

        const status = (student.status || 'active').toLowerCase();
        let statusBadge = '';
        if (status === 'pending') {
            statusBadge = '<span class="badge-status-pending"><i data-lucide="clock" class="w-3 h-3"></i>PENDING APPROVAL</span>';
        } else if (status === 'rejected') {
            statusBadge = '<span class="badge-status-rejected"><i data-lucide="x-circle" class="w-3 h-3"></i>REJECTED</span>';
        } else {
            statusBadge = '<span class="badge-status-active"><i data-lucide="check-circle" class="w-3 h-3"></i>ACTIVE</span>';
        }

        const name = student.full_name || student.name || 'Student';

        container.innerHTML = `
            <div class="space-y-4">
                <div class="flex items-center justify-between p-3.5 rounded-xl bg-[#0F172A] border border-[#1F2937] flex-wrap gap-3">
                    <div class="flex items-center gap-3">
                        <div class="w-12 h-12 rounded-xl bg-indigo-600/30 text-indigo-400 font-bold text-base flex items-center justify-center">
                            ${name.slice(0, 2).toUpperCase()}
                        </div>
                        <div>
                            <h4 class="text-sm font-bold text-white mb-0.5">${name}</h4>
                            <p class="text-xs text-indigo-400 font-mono mb-0">${student.enrollment_no || enroll}</p>
                        </div>
                    </div>
                    <div>${statusBadge}</div>
                </div>

                <div class="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
                    <div class="p-2.5 rounded-lg bg-[#0F172A] border border-[#1F2937]">
                        <span class="text-gray-500 block text-[10px] uppercase font-semibold">DEPARTMENT</span>
                        <span class="text-white font-medium">${student.department || '-'}</span>
                    </div>
                    <div class="p-2.5 rounded-lg bg-[#0F172A] border border-[#1F2937]">
                        <span class="text-gray-500 block text-[10px] uppercase font-semibold">PROGRAM &amp; SEMESTER</span>
                        <span class="text-white font-medium">${student.program || 'BE'} - Sem ${student.semester || 1}</span>
                    </div>
                    <div class="p-2.5 rounded-lg bg-[#0F172A] border border-[#1F2937]">
                        <span class="text-gray-500 block text-[10px] uppercase font-semibold">EMAIL ADDRESS</span>
                        <span class="text-white font-medium">${student.email || '-'}</span>
                    </div>
                    <div class="p-2.5 rounded-lg bg-[#0F172A] border border-[#1F2937]">
                        <span class="text-gray-500 block text-[10px] uppercase font-semibold">CONTACT NUMBER</span>
                        <span class="text-white font-medium font-mono">${student.phone || student.contact_number || '-'}</span>
                    </div>
                    <div class="p-2.5 rounded-lg bg-[#0F172A] border border-[#1F2937]">
                        <span class="text-gray-500 block text-[10px] uppercase font-semibold">REQUEST ID / REF</span>
                        <span class="text-indigo-300 font-mono text-[11px]">${student.request_id || 'N/A'}</span>
                    </div>
                    <div class="p-2.5 rounded-lg bg-[#0F172A] border border-[#1F2937]">
                        <span class="text-gray-500 block text-[10px] uppercase font-semibold">REGISTERED AT</span>
                        <span class="text-gray-300 font-mono text-[11px]">${student.created_at ? new Date(student.created_at).toLocaleString() : 'N/A'}</span>
                    </div>
                </div>

                <!-- Audit Trail Box -->
                ${status === 'active' && student.approved_by ? `
                    <div class="p-3 rounded-xl bg-emerald-950/20 border border-emerald-500/30 text-xs">
                        <div class="flex items-center gap-1.5 text-emerald-400 font-semibold mb-1">
                            <i data-lucide="shield-check" class="w-4 h-4"></i> Approved Record
                        </div>
                        <p class="text-gray-300 mb-0">Approved by <strong class="text-white">${student.approved_by}</strong> on ${student.approved_at ? new Date(student.approved_at).toLocaleString() : 'N/A'}</p>
                    </div>
                ` : ''}

                ${status === 'rejected' ? `
                    <div class="p-3 rounded-xl bg-red-950/20 border border-red-500/30 text-xs">
                        <div class="flex items-center gap-1.5 text-red-400 font-semibold mb-1">
                            <i data-lucide="alert-triangle" class="w-4 h-4"></i> Rejection Details
                        </div>
                        <p class="text-gray-300 mb-1">Rejected by <strong class="text-white">${student.rejected_by || 'Admin'}</strong> on ${student.rejected_at ? new Date(student.rejected_at).toLocaleString() : 'N/A'}</p>
                        ${student.rejection_reason ? `<p class="text-red-300 mb-0 font-medium">Reason: ${student.rejection_reason}</p>` : ''}
                    </div>
                ` : ''}
            </div>
        `;

        if (quickActions) {
            quickActions.innerHTML = '';
            if (status !== 'active') {
                quickActions.innerHTML += `
                    <button class="px-3 py-1.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold flex items-center gap-1" onclick="window.acceptStudent('${enroll}', '${escapeQuotes(name)}')">
                        <i data-lucide="check" class="w-3.5 h-3.5"></i> Approve Student
                    </button>
                `;
            }
            if (status !== 'rejected') {
                quickActions.innerHTML += `
                    <button class="px-3 py-1.5 rounded-xl bg-red-600/20 text-red-400 border border-red-500/30 hover:bg-red-600 hover:text-white text-xs font-semibold flex items-center gap-1" onclick="window.rejectStudent('${enroll}', '${escapeQuotes(name)}')">
                        <i data-lucide="x" class="w-3.5 h-3.5"></i> Reject
                    </button>
                `;
            }
        }

        lucide.createIcons();
        studentViewModal.show();
    };

    window.deleteStudent = function(enroll) {
        state.pendingDeleteId = enroll;
        document.getElementById('deleteStudentTargetEnroll').innerText = enroll;
        deleteConfirmModal.show();
    };

    async function handleConfirmDelete() {
        if (!state.pendingDeleteId) return;

        try {
            const res = await fetch(`/admin/api/crud/students/${state.pendingDeleteId}`, { method: 'DELETE' });
            const data = await res.json();
            if (res.ok && data.status === 'success') {
                showAdminToast(data.message, 'success');
                deleteConfirmModal.hide();
                loadTabCounts();
                loadStudents();
            } else {
                showAdminToast(data.message || 'Failed to delete student.', 'error');
            }
        } catch (err) {
            showAdminToast(err.message, 'error');
        }
    }
})();
