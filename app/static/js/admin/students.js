/**
 * SVIT Admin - Page 5: Students Controller
 * Handles student roster querying, department/semester/status filtering,
 * registration modal, profile view modal, and record deletion.
 */

(function() {
    'use strict';

    const state = {
        moduleKey: 'students',
        search: '',
        department: '',
        semester: '',
        status: '',
        page: 1,
        limit: 50,
        total: 0,
        items: [],
        pendingDeleteId: null
    };

    let studentFormModal = null;
    let studentViewModal = null;
    let deleteConfirmModal = null;
    let searchDebounce = null;

    document.addEventListener('DOMContentLoaded', function() {
        const formEl = document.getElementById('studentFormModal');
        const viewEl = document.getElementById('studentViewModal');
        const delEl = document.getElementById('studentDeleteModal');

        if (formEl) studentFormModal = new bootstrap.Modal(formEl);
        if (viewEl) studentViewModal = new bootstrap.Modal(viewEl);
        if (delEl) deleteConfirmModal = new bootstrap.Modal(delEl);

        bindEvents();
        loadStudents();
    });

    function bindEvents() {
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

        const deptFilter = document.getElementById('deptFilter');
        if (deptFilter) {
            deptFilter.addEventListener('change', (e) => {
                state.department = e.target.value;
                state.page = 1;
                loadStudents();
            });
        }

        const semFilter = document.getElementById('semFilter');
        if (semFilter) {
            semFilter.addEventListener('change', (e) => {
                state.semester = e.target.value;
                state.page = 1;
                loadStudents();
            });
        }

        const refreshBtn = document.getElementById('refreshStudentsBtn');
        if (refreshBtn) refreshBtn.addEventListener('click', loadStudents);

        const openCreateBtn = document.getElementById('openCreateStudentModalBtn');
        if (openCreateBtn) {
            openCreateBtn.addEventListener('click', () => {
                document.getElementById('studentModalTitle').innerText = 'Register New Student';
                document.getElementById('studentFormRecordId').value = '';
                document.getElementById('studentForm').reset();
                document.getElementById('studentEnrollment').disabled = false;
                studentFormModal.show();
            });
        }

        const form = document.getElementById('studentForm');
        if (form) form.addEventListener('submit', handleStudentFormSubmit);

        const confirmDeleteBtn = document.getElementById('confirmDeleteStudentBtn');
        if (confirmDeleteBtn) confirmDeleteBtn.addEventListener('click', handleConfirmDelete);

        // Pagination
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
        const countBadge = document.getElementById('studentsCountBadge');
        if (countBadge) countBadge.innerText = `${state.total} Students`;

        if (state.items.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="8" class="text-center py-12 text-gray-400 text-xs">
                        <i data-lucide="users" class="w-8 h-8 mx-auto mb-2 text-gray-600"></i>
                        <p class="mb-0">No student records found matching the query.</p>
                    </td>
                </tr>
            `;
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
            const isComplete = s.is_profile_complete !== false;

            return `
                <tr>
                    <td>
                        <span class="font-mono text-indigo-400 font-bold text-xs">${enroll}</span>
                    </td>
                    <td>
                        <div class="flex items-center gap-2.5">
                            <div class="student-avatar">
                                ${name.slice(0, 2).toUpperCase()}
                            </div>
                            <div>
                                <p class="text-xs font-bold text-white mb-0">${name}</p>
                                <span class="text-[10px] text-gray-500">${s.program || 'BE'}</span>
                            </div>
                        </div>
                    </td>
                    <td class="text-gray-300 text-xs">${dept}</td>
                    <td><span class="badge-sem">${sem}</span></td>
                    <td class="text-gray-300 text-xs">${email}</td>
                    <td class="text-gray-400 text-xs font-mono">${phone}</td>
                    <td>
                        ${isComplete ? 
                            '<span class="badge-profile-complete"><i data-lucide="check" class="w-3 h-3 d-inline mr-0.5"></i>Active</span>' : 
                            '<span class="badge-profile-pending"><i data-lucide="clock" class="w-3 h-3 d-inline mr-0.5"></i>Pending</span>'}
                    </td>
                    <td class="text-end">
                        <div class="inline-flex items-center gap-1.5">
                            <button class="p-1.5 rounded-lg bg-[#0F172A] border border-[#1F2937] text-gray-300 hover:text-white" onclick="window.viewStudent('${enroll}')" title="View Profile">
                                <i data-lucide="eye" class="w-3.5 h-3.5"></i>
                            </button>
                            <button class="p-1.5 rounded-lg bg-[#0F172A] border border-[#1F2937] text-gray-300 hover:text-white" onclick="window.editStudent('${enroll}')" title="Edit Student">
                                <i data-lucide="edit-2" class="w-3.5 h-3.5"></i>
                            </button>
                            <button class="p-1.5 rounded-lg bg-[#0F172A] border border-[#1F2937] text-red-400 hover:bg-red-500/20" onclick="window.deleteStudent('${enroll}')" title="Delete Student">
                                <i data-lucide="trash-2" class="w-3.5 h-3.5"></i>
                            </button>
                        </div>
                    </td>
                </tr>
            `;
        }).join('');

        lucide.createIcons();
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
            phone: document.getElementById('studentPhone').value.trim()
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
                loadStudents();
            } else {
                showAdminToast(data.message || 'Error saving student record.', 'error');
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
        document.getElementById('studentPhone').value = student.phone || '';

        studentFormModal.show();
    };

    window.viewStudent = function(enroll) {
        const student = state.items.find(s => (s.enrollment_no || s.id) === enroll);
        if (!student) return;

        const container = document.getElementById('studentViewContent');
        if (!container) return;

        container.innerHTML = `
            <div class="space-y-3">
                <div class="flex items-center gap-3 p-3 rounded-xl bg-[#0F172A] border border-[#1F2937]">
                    <div class="w-12 h-12 rounded-xl bg-indigo-600/30 text-indigo-400 font-bold text-base flex items-center justify-center">
                        ${(student.full_name || 'ST').slice(0, 2).toUpperCase()}
                    </div>
                    <div>
                        <h4 class="text-sm font-bold text-white mb-0.5">${student.full_name || student.name}</h4>
                        <p class="text-xs text-indigo-400 font-mono mb-0">${student.enrollment_no || enroll}</p>
                    </div>
                </div>
                <div class="grid grid-cols-2 gap-3 text-xs">
                    <div class="p-2.5 rounded-lg bg-[#0F172A] border border-[#1F2937]">
                        <span class="text-gray-500 block text-[10px]">DEPARTMENT</span>
                        <span class="text-white font-medium">${student.department || '-'}</span>
                    </div>
                    <div class="p-2.5 rounded-lg bg-[#0F172A] border border-[#1F2937]">
                        <span class="text-gray-500 block text-[10px]">PROGRAM & SEMESTER</span>
                        <span class="text-white font-medium">${student.program || 'BE'} - Sem ${student.semester || 1}</span>
                    </div>
                    <div class="p-2.5 rounded-lg bg-[#0F172A] border border-[#1F2937]">
                        <span class="text-gray-500 block text-[10px]">EMAIL ADDRESS</span>
                        <span class="text-white font-medium">${student.email || '-'}</span>
                    </div>
                    <div class="p-2.5 rounded-lg bg-[#0F172A] border border-[#1F2937]">
                        <span class="text-gray-500 block text-[10px]">PHONE NUMBER</span>
                        <span class="text-white font-medium font-mono">${student.phone || '-'}</span>
                    </div>
                </div>
            </div>
        `;

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
                loadStudents();
            } else {
                showAdminToast(data.message || 'Failed to delete student.', 'error');
            }
        } catch (err) {
            showAdminToast(err.message, 'error');
        }
    }
})();
