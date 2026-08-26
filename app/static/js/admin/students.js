/**
 * SVIT Admin - Page 5: Students Controller
 * Handles student roster querying, status tabs (All, Pending, Active, Rejected),
 * approval and rejection workflow, mobile filter sheet, audit trail viewing, and record management.
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
    let studentMobileFilterModal = null;
    let searchDebounce = null;

    function escapeHtml(value) {
        return String(value || '')
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
    }

    function escapeQuotes(value) {
        return String(value || '')
            .replace(/\\/g, '\\\\')
            .replace(/'/g, "\\'")
            .replace(/"/g, '&quot;');
    }

    document.addEventListener('DOMContentLoaded', function() {
        const formEl = document.getElementById('studentFormModal');
        const viewEl = document.getElementById('studentViewModal');
        const acceptEl = document.getElementById('studentAcceptModal');
        const rejectEl = document.getElementById('studentRejectModal');
        const delEl = document.getElementById('studentDeleteModal');
        const mobFilterEl = document.getElementById('studentMobileFilterModal');

        if (formEl) studentFormModal = new bootstrap.Modal(formEl);
        if (viewEl) studentViewModal = new bootstrap.Modal(viewEl);
        if (acceptEl) studentAcceptModal = new bootstrap.Modal(acceptEl);
        if (rejectEl) studentRejectModal = new bootstrap.Modal(rejectEl);
        if (delEl) deleteConfirmModal = new bootstrap.Modal(delEl);
        if (mobFilterEl) studentMobileFilterModal = new bootstrap.Modal(mobFilterEl);

        // Synchronize initial active tab from URL param if present
        if (initialStatus) {
            document.querySelectorAll('.status-tab-btn').forEach(btn => {
                const btnStatus = btn.getAttribute('data-status') || '';
                if (btnStatus.toLowerCase() === initialStatus.toLowerCase()) {
                    btn.classList.add('active');
                    btn.setAttribute('aria-selected', 'true');
                } else {
                    btn.classList.remove('active');
                    btn.setAttribute('aria-selected', 'false');
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
                document.querySelectorAll('.status-tab-btn').forEach(b => {
                    b.classList.remove('active');
                    b.setAttribute('aria-selected', 'false');
                });
                btn.classList.add('active');
                btn.setAttribute('aria-selected', 'true');
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

        // Search Input with Debounce & Clear Button
        const searchInput = document.getElementById('studentSearchInput');
        const clearSearchBtn = document.getElementById('clearSearchBtn');
        if (searchInput) {
            searchInput.addEventListener('input', (e) => {
                const val = e.target.value;
                if (clearSearchBtn) {
                    if (val.length > 0) clearSearchBtn.classList.remove('hidden');
                    else clearSearchBtn.classList.add('hidden');
                }
                clearTimeout(searchDebounce);
                searchDebounce = setTimeout(() => {
                    state.search = val.trim();
                    state.page = 1;
                    loadStudents();
                }, 280);
            });
        }

        if (clearSearchBtn && searchInput) {
            clearSearchBtn.addEventListener('click', () => {
                searchInput.value = '';
                clearSearchBtn.classList.add('hidden');
                state.search = '';
                state.page = 1;
                loadStudents();
            });
        }

        // Desktop Department Filter
        const deptFilter = document.getElementById('deptFilter');
        if (deptFilter) {
            deptFilter.addEventListener('change', (e) => {
                state.department = e.target.value;
                state.page = 1;
                syncFilterBadges();
                loadStudents();
            });
        }

        // Desktop Semester Filter
        const semFilter = document.getElementById('semFilter');
        if (semFilter) {
            semFilter.addEventListener('change', (e) => {
                state.semester = e.target.value;
                state.page = 1;
                syncFilterBadges();
                loadStudents();
            });
        }

        // Mobile Filter Trigger Button
        const openMobileFilterBtn = document.getElementById('openMobileFilterBtn');
        if (openMobileFilterBtn && studentMobileFilterModal) {
            openMobileFilterBtn.addEventListener('click', () => {
                const mDept = document.getElementById('mobileDeptFilter');
                const mSem = document.getElementById('mobileSemFilter');
                if (mDept) mDept.value = state.department;
                if (mSem) mSem.value = state.semester;
                studentMobileFilterModal.show();
            });
        }

        // Apply Mobile Filters Button
        const applyMobileFilterBtn = document.getElementById('applyMobileFilterBtn');
        if (applyMobileFilterBtn) {
            applyMobileFilterBtn.addEventListener('click', () => {
                const mDept = document.getElementById('mobileDeptFilter');
                const mSem = document.getElementById('mobileSemFilter');
                state.department = mDept ? mDept.value : '';
                state.semester = mSem ? mSem.value : '';
                state.page = 1;

                if (deptFilter) deptFilter.value = state.department;
                if (semFilter) semFilter.value = state.semester;

                syncFilterBadges();
                if (studentMobileFilterModal) studentMobileFilterModal.hide();
                loadStudents();
            });
        }

        // Reset Mobile Filters Button
        const resetMobileFilterBtn = document.getElementById('resetMobileFilterBtn');
        if (resetMobileFilterBtn) {
            resetMobileFilterBtn.addEventListener('click', () => {
                const mDept = document.getElementById('mobileDeptFilter');
                const mSem = document.getElementById('mobileSemFilter');
                if (mDept) mDept.value = '';
                if (mSem) mSem.value = '';
                state.department = '';
                state.semester = '';
                state.page = 1;

                if (deptFilter) deptFilter.value = '';
                if (semFilter) semFilter.value = '';

                syncFilterBadges();
                if (studentMobileFilterModal) studentMobileFilterModal.hide();
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
                const subtitle = document.getElementById('studentModalSubtitle');
                if (subtitle) subtitle.innerText = 'Fill in complete academic and registration details';
                const submitBtn = document.getElementById('studentSubmitBtn');
                if (submitBtn) submitBtn.innerText = 'Register Student';
                document.getElementById('studentFormRecordId').value = '';
                document.getElementById('studentForm').reset();
                document.getElementById('studentEnrollment').disabled = false;
                const stSelect = document.getElementById('studentStatus');
                if (stSelect) stSelect.value = 'active';
                const profChk = document.getElementById('studentProfileComplete');
                if (profChk) profChk.checked = true;
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

    function syncFilterBadges() {
        let activeCount = 0;
        if (state.department) activeCount++;
        if (state.semester) activeCount++;

        const badge = document.getElementById('mobileFilterActiveBadge');
        if (badge) {
            if (activeCount > 0) {
                badge.innerText = activeCount;
                badge.classList.remove('hidden');
            } else {
                badge.classList.add('hidden');
            }
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

            if (cAll) cAll.innerText = allData?.total ?? allData?.data?.total ?? 0;
            if (cPend) cPend.innerText = pendingData?.total ?? pendingData?.data?.total ?? 0;
            if (cAct) cAct.innerText = activeData?.total ?? activeData?.data?.total ?? 0;
            if (cRej) cRej.innerText = rejectedData?.total ?? rejectedData?.data?.total ?? 0;
        } catch (e) {
            console.error('Failed to load status tab counts:', e);
        }
    }

    async function loadStudents() {
        const tbody = document.getElementById('studentsTableBody');
        const mobileCards = document.getElementById('studentsMobileCards');
        if (!tbody) return;

        // Desktop Table Loading State
        tbody.innerHTML = `
            <tr>
                <td colspan="8" class="text-center py-12 text-[#66708F] text-xs">
                    <div class="inline-block animate-spin rounded-full h-5 w-5 border-2 border-[#8B5CF6] border-t-transparent mb-2"></div>
                    <p class="mb-0">Loading students roster...</p>
                </td>
            </tr>
        `;

        // Mobile Skeleton Loading State (Prevents layout jump)
        if (mobileCards) {
            mobileCards.innerHTML = `
                <div class="student-skeleton-card">
                    <div class="flex items-center gap-3">
                        <div class="w-10 h-10 rounded-xl skeleton-shimmer flex-shrink-0"></div>
                        <div class="flex-1 space-y-2">
                            <div class="h-3.5 w-32 skeleton-shimmer"></div>
                            <div class="h-2.5 w-20 skeleton-shimmer"></div>
                        </div>
                        <div class="h-5 w-16 rounded-full skeleton-shimmer"></div>
                    </div>
                    <div class="h-14 rounded-xl skeleton-shimmer"></div>
                    <div class="h-9 rounded-xl skeleton-shimmer"></div>
                </div>
                <div class="student-skeleton-card">
                    <div class="flex items-center gap-3">
                        <div class="w-10 h-10 rounded-xl skeleton-shimmer flex-shrink-0"></div>
                        <div class="flex-1 space-y-2">
                            <div class="h-3.5 w-28 skeleton-shimmer"></div>
                            <div class="h-2.5 w-24 skeleton-shimmer"></div>
                        </div>
                        <div class="h-5 w-16 rounded-full skeleton-shimmer"></div>
                    </div>
                    <div class="h-14 rounded-xl skeleton-shimmer"></div>
                    <div class="h-9 rounded-xl skeleton-shimmer"></div>
                </div>
            `;
        }

        const params = new URLSearchParams({
            page: state.page,
            limit: state.limit
        });
        if (state.search) params.append('search', state.search);
        if (state.status) params.append('status', state.status);
        if (state.department) params.append('filter_department', state.department);
        if (state.semester) params.append('filter_semester', state.semester);

        try {
            const res = await fetch(`/admin/api/crud/students?${params.toString()}`);
            const data = await res.json();
            if (res.ok && (data.status === 'success' || Array.isArray(data.items))) {
                state.items = Array.isArray(data.items)
                    ? data.items
                    : (Array.isArray(data?.data?.items) ? data.data.items : (Array.isArray(data?.data) ? data.data : []));
                state.total = typeof data.total === 'number'
                    ? data.total
                    : (typeof data?.data?.total === 'number' ? data.data.total : state.items.length);
                renderStudentsTable();
                updatePagination();
            } else {
                tbody.innerHTML = `<tr><td colspan="8" class="text-center py-6 text-red-500 text-xs">${escapeHtml(data.message || 'Error loading students')}</td></tr>`;
                if (mobileCards) {
                    mobileCards.innerHTML = `<div class="student-mobile-empty"><p class="text-red-500">${escapeHtml(data.message || 'Error loading students')}</p></div>`;
                }
            }
        } catch (err) {
            console.error('Error loading students:', err);
            tbody.innerHTML = `<tr><td colspan="8" class="text-center py-6 text-red-500 text-xs">${escapeHtml(err.message)}</td></tr>`;
            if (mobileCards) {
                mobileCards.innerHTML = `<div class="student-mobile-empty"><p class="text-red-500">${escapeHtml(err.message)}</p></div>`;
            }
        }
        lucide.createIcons();
    }

    function renderStudentsTable() {
        const tbody = document.getElementById('studentsTableBody');
        const mobileCards = document.getElementById('studentsMobileCards');
        const countBadge = document.getElementById('studentsCountBadge');
        if (countBadge) countBadge.innerText = `${state.total} Students`;

        // Empty State Handler
        if (state.items.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="8" class="text-center py-12 text-[#66708F] text-xs">
                        <i data-lucide="users" class="w-8 h-8 mx-auto mb-2 text-[#8C95AD]"></i>
                        <p class="font-bold text-[#171D3A] mb-1">No students found</p>
                        <p class="mb-0 text-[#66708F]">Try adjusting your search terms or active filters.</p>
                    </td>
                </tr>
            `;
            if (mobileCards) {
                mobileCards.innerHTML = `
                    <div class="student-mobile-empty">
                        <div class="student-mobile-empty-icon">
                            <i data-lucide="user-x" class="w-6 h-6"></i>
                        </div>
                        <h3>No students found</h3>
                        <p>No student records match the active filter or search criteria.</p>
                        ${(state.search || state.department || state.semester || state.status) ? `
                            <button type="button" class="btn-primary-custom text-xs mt-2" onclick="window.clearAllStudentFilters()">
                                <i data-lucide="rotate-ccw" class="w-3.5 h-3.5"></i> Clear All Filters
                            </button>
                        ` : ''}
                    </div>
                `;
            }
            lucide.createIcons();
            return;
        }

        // 1. Render Desktop Table Rows
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
                <tr class="${isPending ? 'bg-amber-50/40' : ''}">
                    <td>
                        <span class="font-mono text-[#8B5CF6] font-bold text-xs">${escapeHtml(enroll)}</span>
                    </td>
                    <td>
                        <div class="flex items-center gap-2.5">
                            <div class="student-avatar ${isPending ? 'bg-amber-100 text-amber-700' : ''}">
                                ${escapeHtml(name.slice(0, 2).toUpperCase())}
                            </div>
                            <div>
                                <p class="text-xs font-bold text-[#171D3A] mb-0">${escapeHtml(name)}</p>
                                <span class="text-[10px] text-[#66708F]">${escapeHtml(s.program || 'BE')}</span>
                            </div>
                        </div>
                    </td>
                    <td class="text-[#171D3A] text-xs">${escapeHtml(dept)}</td>
                    <td><span class="badge-sem">${escapeHtml(sem)}</span></td>
                    <td class="text-[#66708F] text-xs">${escapeHtml(email)}</td>
                    <td class="text-[#66708F] text-xs font-mono">${escapeHtml(createdAt)}</td>
                    <td>${statusBadgeHtml}</td>
                    <td class="text-end">
                        <div class="inline-flex items-center gap-1.5">
                            <button class="p-1.5 rounded-lg bg-white border border-[#E1E5F0] text-[#171D3A] hover:bg-[#E8EBFA]" onclick="window.viewStudent('${escapeQuotes(enroll)}')" title="View Profile">
                                <i data-lucide="eye" class="w-3.5 h-3.5"></i>
                            </button>

                            ${status !== 'active' ? `
                            <button class="px-2 py-1 rounded-lg bg-emerald-50 text-emerald-700 border border-emerald-200 hover:bg-emerald-600 hover:text-white text-[11px] font-bold transition flex items-center gap-1" onclick="window.acceptStudent('${escapeQuotes(enroll)}', '${escapeQuotes(name)}')" title="Accept Student">
                                <i data-lucide="check" class="w-3 h-3"></i> Accept
                            </button>
                            ` : ''}

                            ${status !== 'rejected' ? `
                            <button class="px-2 py-1 rounded-lg bg-red-50 text-red-700 border border-red-200 hover:bg-red-600 hover:text-white text-[11px] font-bold transition flex items-center gap-1" onclick="window.rejectStudent('${escapeQuotes(enroll)}', '${escapeQuotes(name)}')" title="Reject Student">
                                <i data-lucide="x" class="w-3 h-3"></i> Reject
                            </button>
                            ` : ''}

                            <button class="p-1.5 rounded-lg bg-white border border-[#E1E5F0] text-[#171D3A] hover:bg-[#E8EBFA]" onclick="window.editStudent('${escapeQuotes(enroll)}')" title="Edit Student">
                                <i data-lucide="edit-2" class="w-3.5 h-3.5"></i>
                            </button>

                            <button class="p-1.5 rounded-lg bg-white border border-[#E1E5F0] text-red-600 hover:bg-red-50" onclick="window.deleteStudent('${escapeQuotes(enroll)}')" title="Delete Student">
                                <i data-lucide="trash-2" class="w-3.5 h-3.5"></i>
                            </button>
                        </div>
                    </td>
                </tr>
            `;
        }).join('');

        // 2. Render Purpose-Built Mobile Student Cards
        if (mobileCards) {
            mobileCards.innerHTML = state.items.map(s => {
                const name = s.full_name || s.name || 'Unnamed Student';
                const enroll = s.enrollment_no || s.id || '-';
                const dept = s.department || 'General';
                const sem = s.semester ? `Sem ${s.semester}` : 'Sem 1';
                const program = s.program || 'BE';
                const email = s.email || '-';
                const status = (s.status || 'active').toLowerCase();
                const isPending = status === 'pending';

                let badgeHtml = '';
                if (status === 'pending') {
                    badgeHtml = '<span class="badge-status-pending"><i data-lucide="clock" class="w-3 h-3"></i>Pending</span>';
                } else if (status === 'rejected') {
                    badgeHtml = '<span class="badge-status-rejected"><i data-lucide="x-circle" class="w-3 h-3"></i>Rejected</span>';
                } else {
                    badgeHtml = '<span class="badge-status-active"><i data-lucide="check-circle" class="w-3 h-3"></i>Active</span>';
                }

                return `
                    <article class="student-mobile-card ${isPending ? 'is-pending-card' : ''}">
                        <!-- Top Header: Avatar + Student Name + Enrollment + Status -->
                        <div class="student-card-header">
                            <div class="student-card-identity">
                                <div class="student-card-avatar ${isPending ? 'is-pending' : ''}">
                                    ${escapeHtml(name.slice(0, 2).toUpperCase())}
                                </div>
                                <div class="student-card-name-group">
                                    <h3 class="student-card-name">${escapeHtml(name)}</h3>
                                    <p class="student-card-enroll">${escapeHtml(enroll)}</p>
                                </div>
                            </div>
                            <div>${badgeHtml}</div>
                        </div>

                        <!-- Metadata Grid: Department, Semester, Program, Email -->
                        <div class="student-card-grid">
                            <div class="student-grid-item">
                                <span class="student-grid-label">Department</span>
                                <span class="student-grid-value">${escapeHtml(dept)}</span>
                            </div>
                            <div class="student-grid-item">
                                <span class="student-grid-label">Semester &amp; Program</span>
                                <span class="student-grid-value">${escapeHtml(sem)} (${escapeHtml(program)})</span>
                            </div>
                            <div class="student-grid-item" style="grid-column: span 2;">
                                <span class="student-grid-label">Email Address</span>
                                <span class="student-grid-value text-[#66708F]">${escapeHtml(email)}</span>
                            </div>
                        </div>

                        <!-- Bottom Touch Action Buttons (>= 44px) -->
                        <div class="student-card-actions">
                            ${isPending ? `
                                <button type="button" class="student-action-btn is-success" onclick="window.acceptStudent('${escapeQuotes(enroll)}', '${escapeQuotes(name)}')" title="Approve Registration">
                                    <i data-lucide="check" class="w-4 h-4"></i>
                                    <span>Approve</span>
                                </button>
                                <button type="button" class="student-action-btn is-danger" onclick="window.rejectStudent('${escapeQuotes(enroll)}', '${escapeQuotes(name)}')" title="Reject Registration">
                                    <i data-lucide="x" class="w-4 h-4"></i>
                                    <span>Reject</span>
                                </button>
                            ` : ''}

                            <button type="button" class="student-action-btn ${isPending ? '' : 'is-primary'}" onclick="window.viewStudent('${escapeQuotes(enroll)}')" title="View Profile & Audit Trail">
                                <i data-lucide="eye" class="w-4 h-4"></i>
                                <span>View</span>
                            </button>

                            <button type="button" class="student-action-btn" onclick="window.editStudent('${escapeQuotes(enroll)}')" title="Edit Student">
                                <i data-lucide="edit-2" class="w-4 h-4"></i>
                                <span>Edit</span>
                            </button>

                            <button type="button" class="student-action-btn is-danger is-icon-only" onclick="window.deleteStudent('${escapeQuotes(enroll)}')" title="Delete Student">
                                <i data-lucide="trash-2" class="w-4 h-4"></i>
                            </button>
                        </div>
                    </article>
                `;
            }).join('');
        }

        lucide.createIcons();
    }

    window.clearAllStudentFilters = function() {
        state.search = '';
        state.department = '';
        state.semester = '';
        state.status = '';
        state.page = 1;

        const sInput = document.getElementById('studentSearchInput');
        if (sInput) sInput.value = '';
        const cBtn = document.getElementById('clearSearchBtn');
        if (cBtn) cBtn.classList.add('hidden');

        const dFilter = document.getElementById('deptFilter');
        if (dFilter) dFilter.value = '';
        const smFilter = document.getElementById('semFilter');
        if (smFilter) smFilter.value = '';

        document.querySelectorAll('.status-tab-btn').forEach(b => {
            if ((b.getAttribute('data-status') || '') === '') {
                b.classList.add('active');
                b.setAttribute('aria-selected', 'true');
            } else {
                b.classList.remove('active');
                b.setAttribute('aria-selected', 'false');
            }
        });

        syncFilterBadges();
        const currentUrl = new URL(window.location);
        currentUrl.searchParams.delete('status');
        window.history.replaceState({}, '', currentUrl);

        loadStudents();
    };

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
            phone: document.getElementById('studentPhone').value.trim(),
            gender: document.getElementById('studentGender') ? document.getElementById('studentGender').value : 'Male',
            dob: document.getElementById('studentDob') ? document.getElementById('studentDob').value : '',
            address: document.getElementById('studentAddress') ? document.getElementById('studentAddress').value.trim() : '',
            program: document.getElementById('studentProgram').value,
            department: document.getElementById('studentDepartment').value,
            semester: parseInt(document.getElementById('studentSemester').value, 10) || 1,
            division: document.getElementById('studentDivision').value.trim(),
            batch: document.getElementById('studentBatch') ? document.getElementById('studentBatch').value.trim() : '',
            status: document.getElementById('studentStatus') ? document.getElementById('studentStatus').value : 'active',
            is_profile_complete: document.getElementById('studentProfileComplete') ? document.getElementById('studentProfileComplete').checked : true
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
                showAdminToast(data.message || (isEdit ? 'Student updated successfully.' : 'Student registered successfully.'), 'success');
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

        document.getElementById('studentModalTitle').innerText = 'Edit Student';
        const subtitle = document.getElementById('studentModalSubtitle');
        if (subtitle) subtitle.innerText = 'Update complete academic and registration information';
        const submitBtn = document.getElementById('studentSubmitBtn');
        if (submitBtn) submitBtn.innerText = 'Save Changes';

        document.getElementById('studentFormRecordId').value = enroll;
        document.getElementById('studentEnrollment').value = student.enrollment_no || enroll;
        document.getElementById('studentEnrollment').disabled = true;
        document.getElementById('studentFullName').value = student.full_name || student.name || '';
        document.getElementById('studentEmail').value = student.email || '';
        document.getElementById('studentPhone').value = student.phone || student.contact_number || '';
        
        const genderSelect = document.getElementById('studentGender');
        if (genderSelect) genderSelect.value = student.gender || 'Male';

        const dobInput = document.getElementById('studentDob');
        if (dobInput) dobInput.value = student.dob || '';

        const addrInput = document.getElementById('studentAddress');
        if (addrInput) addrInput.value = student.address || '';

        document.getElementById('studentProgram').value = student.program || 'BE';
        document.getElementById('studentDepartment').value = student.department || 'Computer Engineering';
        document.getElementById('studentSemester').value = student.semester || 1;
        document.getElementById('studentDivision').value = student.division || '';

        const batchInput = document.getElementById('studentBatch');
        if (batchInput) batchInput.value = student.batch || '';

        const stSelect = document.getElementById('studentStatus');
        if (stSelect) stSelect.value = student.status || 'active';

        const profChk = document.getElementById('studentProfileComplete');
        if (profChk) profChk.checked = Boolean(student.is_profile_complete);

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
            statusBadge = '<span class="badge-status-pending"><i data-lucide="clock" class="w-3 h-3"></i>PENDING</span>';
        } else if (status === 'rejected') {
            statusBadge = '<span class="badge-status-rejected"><i data-lucide="x-circle" class="w-3 h-3"></i>REJECTED</span>';
        } else {
            statusBadge = '<span class="badge-status-active"><i data-lucide="check-circle" class="w-3 h-3"></i>ACTIVE</span>';
        }

        const name = student.full_name || student.name || 'Student';

        container.innerHTML = `
            <div class="space-y-4">
                <!-- Identity Header Card -->
                <div class="flex items-center justify-between p-3.5 rounded-2xl bg-[#F8F9FE] border border-[#E1E5F0] flex-wrap gap-3">
                    <div class="flex items-center gap-3">
                        <div class="w-12 h-12 rounded-2xl bg-[#E8EBFA] text-[#8B5CF6] font-bold text-base flex items-center justify-center border border-[#8B5CF6]/20">
                            ${escapeHtml(name.slice(0, 2).toUpperCase())}
                        </div>
                        <div>
                            <h4 class="text-sm font-bold text-[#171D3A] mb-0.5">${escapeHtml(name)}</h4>
                            <p class="text-xs text-[#8B5CF6] font-mono mb-0">${escapeHtml(student.enrollment_no || enroll)}</p>
                        </div>
                    </div>
                    <div>${statusBadge}</div>
                </div>

                <!-- 2-Column Metadata Grid -->
                <div class="grid grid-cols-1 sm:grid-cols-2 gap-2.5 text-xs">
                    <div class="p-3 rounded-xl bg-[#F8F9FE] border border-[#E1E5F0]">
                        <span class="text-[#8C95AD] block text-[10px] uppercase font-bold tracking-wider mb-0.5">DEPARTMENT</span>
                        <span class="text-[#171D3A] font-semibold">${escapeHtml(student.department || '-')}</span>
                    </div>
                    <div class="p-3 rounded-xl bg-[#F8F9FE] border border-[#E1E5F0]">
                        <span class="text-[#8C95AD] block text-[10px] uppercase font-bold tracking-wider mb-0.5">PROGRAM &amp; SEMESTER</span>
                        <span class="text-[#171D3A] font-semibold">${escapeHtml(student.program || 'BE')} - Sem ${escapeHtml(String(student.semester || 1))}</span>
                    </div>
                    <div class="p-3 rounded-xl bg-[#F8F9FE] border border-[#E1E5F0]">
                        <span class="text-[#8C95AD] block text-[10px] uppercase font-bold tracking-wider mb-0.5">EMAIL ADDRESS</span>
                        <span class="text-[#171D3A] font-semibold break-all">${escapeHtml(student.email || '-')}</span>
                    </div>
                    <div class="p-3 rounded-xl bg-[#F8F9FE] border border-[#E1E5F0]">
                        <span class="text-[#8C95AD] block text-[10px] uppercase font-bold tracking-wider mb-0.5">CONTACT NUMBER</span>
                        <span class="text-[#171D3A] font-semibold font-mono">${escapeHtml(student.phone || student.contact_number || '-')}</span>
                    </div>
                    <div class="p-3 rounded-xl bg-[#F8F9FE] border border-[#E1E5F0]">
                        <span class="text-[#8C95AD] block text-[10px] uppercase font-bold tracking-wider mb-0.5">CLASS DIVISION / BATCH</span>
                        <span class="text-[#171D3A] font-semibold">${escapeHtml(student.division || 'Not Assigned')}</span>
                    </div>
                    <div class="p-3 rounded-xl bg-[#F8F9FE] border border-[#E1E5F0]">
                        <span class="text-[#8C95AD] block text-[10px] uppercase font-bold tracking-wider mb-0.5">REGISTERED AT</span>
                        <span class="text-[#66708F] font-mono text-[11px]">${student.created_at ? new Date(student.created_at).toLocaleString() : 'N/A'}</span>
                    </div>
                </div>

                <!-- Audit Trail Box -->
                ${status === 'active' && student.approved_by ? `
                    <div class="p-3.5 rounded-xl bg-emerald-50 border border-emerald-200 text-xs">
                        <div class="flex items-center gap-1.5 text-emerald-700 font-bold mb-1">
                            <i data-lucide="shield-check" class="w-4 h-4"></i> Approved Account
                        </div>
                        <p class="text-[#171D3A] mb-0">Approved by <strong class="text-[#171D3A]">${escapeHtml(student.approved_by)}</strong> on ${student.approved_at ? new Date(student.approved_at).toLocaleString() : 'N/A'}</p>
                    </div>
                ` : ''}

                ${status === 'rejected' ? `
                    <div class="p-3.5 rounded-xl bg-red-50 border border-red-200 text-xs">
                        <div class="flex items-center gap-1.5 text-red-700 font-bold mb-1">
                            <i data-lucide="alert-triangle" class="w-4 h-4"></i> Rejection Details
                        </div>
                        <p class="text-[#171D3A] mb-1">Rejected by <strong class="text-[#171D3A]">${escapeHtml(student.rejected_by || 'Admin')}</strong> on ${student.rejected_at ? new Date(student.rejected_at).toLocaleString() : 'N/A'}</p>
                        ${student.rejection_reason ? `<p class="text-red-700 mb-0 font-semibold">Reason: ${escapeHtml(student.rejection_reason)}</p>` : ''}
                    </div>
                ` : ''}
            </div>
        `;

        if (quickActions) {
            quickActions.innerHTML = '';
            if (status !== 'active') {
                quickActions.innerHTML += `
                    <button class="px-3.5 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-bold flex items-center gap-1 shadow-sm" onclick="window.acceptStudent('${escapeQuotes(enroll)}', '${escapeQuotes(name)}')">
                        <i data-lucide="check" class="w-3.5 h-3.5"></i> Approve
                    </button>
                `;
            }
            if (status !== 'rejected') {
                quickActions.innerHTML += `
                    <button class="px-3.5 py-2 rounded-xl bg-red-50 text-red-700 border border-red-200 hover:bg-red-600 hover:text-white text-xs font-bold flex items-center gap-1 transition" onclick="window.rejectStudent('${escapeQuotes(enroll)}', '${escapeQuotes(name)}')">
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

