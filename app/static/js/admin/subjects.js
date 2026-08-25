/**
 * SVIT Admin - Page 8: Subjects Controller
 * Handles subject catalog, department/semester/type filtering,
 * creation, editing, and deletion.
 */

(function() {
    'use strict';

    const state = {
        search: '',
        department: '',
        semester: '',
        subjectType: '',
        page: 1,
        limit: 50,
        total: 0,
        items: [],
        pendingDeleteId: null
    };

    let subjectModal = null;
    let deleteModal = null;
    let searchDebounce = null;

    document.addEventListener('DOMContentLoaded', function() {
        const modalEl = document.getElementById('subjectFormModal');
        const delEl = document.getElementById('subjectDeleteModal');

        if (modalEl) subjectModal = new bootstrap.Modal(modalEl);
        if (delEl) deleteModal = new bootstrap.Modal(delEl);

        bindEvents();
        loadSubjects();
    });

    function bindEvents() {
        const searchInput = document.getElementById('subjectSearchInput');
        if (searchInput) {
            searchInput.addEventListener('input', (e) => {
                clearTimeout(searchDebounce);
                searchDebounce = setTimeout(() => {
                    state.search = e.target.value.trim();
                    state.page = 1;
                    loadSubjects();
                }, 300);
            });
        }

        const deptFilter = document.getElementById('subjectDeptFilter');
        if (deptFilter) {
            deptFilter.addEventListener('change', (e) => {
                state.department = e.target.value;
                state.page = 1;
                loadSubjects();
            });
        }

        const semFilter = document.getElementById('subjectSemFilter');
        if (semFilter) {
            semFilter.addEventListener('change', (e) => {
                state.semester = e.target.value;
                state.page = 1;
                loadSubjects();
            });
        }

        const refreshBtn = document.getElementById('refreshSubjectsBtn');
        if (refreshBtn) refreshBtn.addEventListener('click', loadSubjects);

        const limitSelect = document.getElementById('pageLimitSelect');
        if (limitSelect) {
            limitSelect.addEventListener('change', (e) => {
                state.limit = parseInt(e.target.value, 10) || 50;
                state.page = 1;
                loadSubjects();
            });
        }

        const prevBtn = document.getElementById('prevPageBtn');
        if (prevBtn) {
            prevBtn.addEventListener('click', () => {
                if (state.page > 1) {
                    state.page--;
                    loadSubjects();
                }
            });
        }

        const nextBtn = document.getElementById('nextPageBtn');
        if (nextBtn) {
            nextBtn.addEventListener('click', () => {
                const totalPages = Math.ceil(state.total / state.limit) || 1;
                if (state.page < totalPages) {
                    state.page++;
                    loadSubjects();
                }
            });
        }

        const createBtn = document.getElementById('openCreateSubjectModalBtn');
        if (createBtn) {
            createBtn.addEventListener('click', () => {
                document.getElementById('subjectModalTitle').innerText = 'Add New Subject';
                document.getElementById('subjectFormRecordId').value = '';
                document.getElementById('subjectForm').reset();
                document.getElementById('subjectIdInput').disabled = false;
                subjectModal.show();
            });
        }

        const form = document.getElementById('subjectForm');
        if (form) form.addEventListener('submit', handleSubjectFormSubmit);

        const confirmDeleteBtn = document.getElementById('confirmDeleteSubjectBtn');
        if (confirmDeleteBtn) confirmDeleteBtn.addEventListener('click', handleConfirmDelete);
    }

    async function loadSubjects() {
        const tbody = document.getElementById('subjectsTableBody');
        if (!tbody) return;

        tbody.innerHTML = `
            <tr>
                <td colspan="7" class="text-center py-10 text-gray-400 text-xs">
                    <div class="w-5 h-5 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin mx-auto mb-2"></div>
                    Loading subjects catalog...
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
            const res = await fetch(`/admin/api/crud/subjects?${params.toString()}`);
            const data = await res.json();
            if (data.status === 'success') {
                state.items = data.items || [];
                state.total = data.total || 0;
                renderSubjectsTable();
                renderPagination(data);
            } else {
                tbody.innerHTML = `<tr><td colspan="7" class="text-center py-6 text-red-400 text-xs">${data.message}</td></tr>`;
            }
        } catch (err) {
            tbody.innerHTML = `<tr><td colspan="7" class="text-center py-6 text-red-400 text-xs">${err.message}</td></tr>`;
        }
        lucide.createIcons();
    }

    function renderPagination(data) {
        const start = state.total === 0 ? 0 : (state.page - 1) * state.limit + 1;
        const end = Math.min(state.page * state.limit, state.total);
        const totalPages = data.pages || Math.ceil(state.total / state.limit) || 1;

        const startEl = document.getElementById('pageStart');
        const endEl = document.getElementById('pageEnd');
        const totalEl = document.getElementById('pageTotal');
        const prevBtn = document.getElementById('prevPageBtn');
        const nextBtn = document.getElementById('nextPageBtn');
        const numbersContainer = document.getElementById('pageNumbers');

        if (startEl) startEl.innerText = start;
        if (endEl) endEl.innerText = end;
        if (totalEl) totalEl.innerText = state.total;

        if (prevBtn) prevBtn.disabled = (state.page <= 1);
        if (nextBtn) nextBtn.disabled = (state.page >= totalPages);

        if (numbersContainer) {
            numbersContainer.innerHTML = '';
            const maxVisible = 5;
            let startP = Math.max(1, state.page - 2);
            let endP = Math.min(totalPages, startP + maxVisible - 1);
            if (endP - startP < maxVisible - 1) {
                startP = Math.max(1, endP - maxVisible + 1);
            }

            for (let i = startP; i <= endP; i++) {
                const btn = document.createElement('button');
                btn.innerText = i;
                btn.className = `px-2 py-1 rounded-lg text-xs font-semibold transition ${state.page === i ? 'bg-indigo-600 text-white' : 'bg-[#111827] border border-[#1F2937] text-gray-400 hover:text-white'}`;
                btn.onclick = () => {
                    state.page = i;
                    loadSubjects();
                };
                numbersContainer.appendChild(btn);
            }
        }
    }

    function renderSubjectsTable() {
        const tbody = document.getElementById('subjectsTableBody');
        const countBadge = document.getElementById('subjectsCountBadge');
        if (countBadge) countBadge.innerText = `${state.total} Subjects`;

        if (state.items.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="7" class="text-center py-12 text-gray-400 text-xs">
                        <i data-lucide="book" class="w-8 h-8 mx-auto mb-2 text-gray-600"></i>
                        <p class="mb-0">No subject records found.</p>
                    </td>
                </tr>
            `;
            lucide.createIcons();
            return;
        }

        tbody.innerHTML = state.items.map(s => {
            const code = s.subject_code || s.subject_id || '-';
            const name = s.subject_name || s.title || 'Subject';
            const dept = s.department || '-';
            const sem = s.semester ? `Sem ${s.semester}` : 'Sem 1';
            const credits = s.credits || 4;
            const type = s.subject_type || 'Core Theory';
            const id = s.subject_id || code;

            return `
                <tr>
                    <td>
                        <span class="font-mono text-indigo-400 font-bold text-xs">${code}</span>
                    </td>
                    <td>
                        <div class="flex items-center gap-2.5">
                            <div class="w-8 h-8 rounded-lg bg-indigo-600/10 border border-indigo-500/20 text-indigo-400 flex items-center justify-center font-bold text-xs">
                                <i data-lucide="book-open" class="w-4 h-4"></i>
                            </div>
                            <div>
                                <p class="text-xs font-bold text-white mb-0">${name}</p>
                                <span class="text-[10px] text-gray-500">${s.program || 'BE'}</span>
                            </div>
                        </div>
                    </td>
                    <td class="text-gray-300 text-xs">${dept}</td>
                    <td><span class="px-2 py-0.5 rounded text-[10px] bg-indigo-500/20 text-indigo-300 font-semibold">${sem}</span></td>
                    <td><span class="badge-subject-type">${type}</span></td>
                    <td><span class="badge-credits">${credits} Credits</span></td>
                    <td class="text-end">
                        <div class="inline-flex items-center gap-1.5">
                            <button class="p-1.5 rounded-lg bg-[#0F172A] border border-[#1F2937] text-gray-300 hover:text-white" onclick="window.editSubject('${id}')" title="Edit Subject">
                                <i data-lucide="edit-2" class="w-3.5 h-3.5"></i>
                            </button>
                            <button class="p-1.5 rounded-lg bg-[#0F172A] border border-[#1F2937] text-red-400 hover:bg-red-500/20" onclick="window.deleteSubject('${id}')" title="Delete">
                                <i data-lucide="trash-2" class="w-3.5 h-3.5"></i>
                            </button>
                        </div>
                    </td>
                </tr>
            `;
        }).join('');

        lucide.createIcons();
    }

    async function handleSubjectFormSubmit(e) {
        e.preventDefault();
        const recordId = document.getElementById('subjectFormRecordId').value;
        const payload = {
            subject_id: document.getElementById('subjectIdInput').value.trim(),
            subject_code: document.getElementById('subjectCodeInput').value.trim(),
            subject_name: document.getElementById('subjectNameInput').value.trim(),
            program: document.getElementById('subjectProgramInput').value,
            department: document.getElementById('subjectDeptInput').value,
            semester: parseInt(document.getElementById('subjectSemInput').value, 10) || 1,
            subject_type: document.getElementById('subjectTypeInput').value,
            credits: parseInt(document.getElementById('subjectCreditsInput').value, 10) || 4
        };

        const isEdit = Boolean(recordId);
        const url = isEdit ? `/admin/api/crud/subjects/${recordId}` : '/admin/api/crud/subjects';
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
                subjectModal.hide();
                loadSubjects();
            } else {
                showAdminToast(data.message || 'Error saving subject.', 'error');
            }
        } catch (err) {
            showAdminToast(err.message, 'error');
        }
    }

    window.editSubject = function(id) {
        const sub = state.items.find(s => (s.subject_id || s.subject_code) === id);
        if (!sub) return;

        document.getElementById('subjectModalTitle').innerText = 'Edit Subject';
        document.getElementById('subjectFormRecordId').value = id;
        document.getElementById('subjectIdInput').value = sub.subject_id || id;
        document.getElementById('subjectIdInput').disabled = true;
        document.getElementById('subjectCodeInput').value = sub.subject_code || id;
        document.getElementById('subjectNameInput').value = sub.subject_name || sub.title || '';
        document.getElementById('subjectProgramInput').value = sub.program || 'BE';
        document.getElementById('subjectDeptInput').value = sub.department || 'Computer Engineering';
        document.getElementById('subjectSemInput').value = sub.semester || 1;
        document.getElementById('subjectTypeInput').value = sub.subject_type || 'Core Theory';
        document.getElementById('subjectCreditsInput').value = sub.credits || 4;

        subjectModal.show();
    };

    window.deleteSubject = function(id) {
        state.pendingDeleteId = id;
        document.getElementById('deleteSubjectTargetId').innerText = id;
        deleteModal.show();
    };

    async function handleConfirmDelete() {
        if (!state.pendingDeleteId) return;

        try {
            const res = await fetch(`/admin/api/crud/subjects/${state.pendingDeleteId}`, { method: 'DELETE' });
            const data = await res.json();
            if (res.ok && data.status === 'success') {
                showAdminToast(data.message, 'success');
                deleteModal.hide();
                loadSubjects();
            } else {
                showAdminToast(data.message || 'Failed to delete subject.', 'error');
            }
        } catch (err) {
            showAdminToast(err.message, 'error');
        }
    }
})();
