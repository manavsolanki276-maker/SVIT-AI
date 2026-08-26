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

        const typeFilter = document.getElementById('subjectTypeFilter');
        if (typeFilter) {
            typeFilter.addEventListener('change', (e) => {
                state.subjectType = e.target.value;
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

        const addBtn = document.getElementById('addSubjectBtn');
        if (addBtn) {
            addBtn.addEventListener('click', () => {
                document.getElementById('subjectModalTitle').innerText = 'Add Subject';
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
                <td colspan="7" class="text-center py-12 text-[#66708F] text-xs">
                    <div class="inline-block animate-spin rounded-full h-5 w-5 border-2 border-[#8B5CF6] border-t-transparent mb-2"></div>
                    <p class="mb-0">Loading subjects catalog...</p>
                </td>
            </tr>
        `;

        const params = new URLSearchParams({
            page: state.page,
            limit: state.limit
        });
        if (state.search) params.append('search', state.search);
        if (state.department) params.append('department', state.department);
        if (state.semester) params.append('semester', state.semester);
        if (state.subjectType) params.append('subject_type', state.subjectType);

        try {
            const res = await fetch(`/admin/api/crud/subjects?${params.toString()}`);
            const data = await res.json();
            if (res.ok && (data.status === 'success' || Array.isArray(data.items))) {
                state.items = Array.isArray(data.items)
                    ? data.items
                    : (Array.isArray(data?.data?.items) ? data.data.items : (Array.isArray(data?.data) ? data.data : []));
                state.total = typeof data.total === 'number'
                    ? data.total
                    : (typeof data?.data?.total === 'number' ? data.data.total : state.items.length);
                renderSubjectsTable();
                renderPagination(data.pages || data?.data?.pages || 1);
            } else {
                showAdminToast(data.message || 'Failed to load subjects.', 'error');
            }
        } catch (err) {
            showAdminToast(err.message, 'error');
        }
    }

    function renderPagination(totalPages) {
        const pagWrapper = document.getElementById('subjectsPagination');
        if (!pagWrapper) return;

        if (totalPages <= 1) {
            pagWrapper.classList.add('hidden');
            return;
        }

        pagWrapper.classList.remove('hidden');
        const start = (state.page - 1) * state.limit + 1;
        const end = Math.min(state.page * state.limit, state.total);
        const infoEl = document.getElementById('subjectsPaginationInfo');
        if (infoEl) infoEl.innerText = `Showing ${start}-${end} of ${state.total} subjects`;

        const prevBtn = document.getElementById('subjectsPrevPageBtn');
        const nextBtn = document.getElementById('subjectsNextPageBtn');

        if (prevBtn) {
            prevBtn.disabled = state.page <= 1;
            prevBtn.onclick = () => {
                if (state.page > 1) {
                    state.page--;
                    loadSubjects();
                }
            };
        }

        if (nextBtn) {
            nextBtn.disabled = state.page >= totalPages;
            nextBtn.onclick = () => {
                if (state.page < totalPages) {
                    state.page++;
                    loadSubjects();
                }
            };
        }

        const numbersContainer = document.getElementById('subjectsPageNumbers');
        if (numbersContainer) {
            numbersContainer.innerHTML = '';
            const maxVisible = 5;
            let startP = Math.max(1, state.page - Math.floor(maxVisible / 2));
            let endP = Math.min(totalPages, startP + maxVisible - 1);
            if (endP - startP < maxVisible - 1) {
                startP = Math.max(1, endP - maxVisible + 1);
            }

            for (let i = startP; i <= endP; i++) {
                const btn = document.createElement('button');
                btn.innerText = i;
                btn.className = `px-2 py-1 rounded-lg text-xs font-semibold transition ${state.page === i ? 'bg-[#8B5CF6] text-white' : 'bg-white border border-[#E1E5F0] text-[#66708F] hover:text-[#171D3A]'}`;
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
        const mobileCards = document.getElementById('subjectsMobileCards');
        const countBadge = document.getElementById('subjectsCountBadge');
        if (countBadge) countBadge.innerText = `${state.total} Subjects`;

        if (state.items.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="7" class="text-center py-12 text-[#66708F] text-xs">
                        <i data-lucide="book" class="w-8 h-8 mx-auto mb-2 text-[#8C95AD]"></i>
                        <p class="mb-0">No subject records found.</p>
                    </td>
                </tr>
            `;
            if (mobileCards) mobileCards.innerHTML = '<div class="admin-mobile-empty">No subject records found.</div>';
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
                        <span class="font-mono text-[#8B5CF6] font-bold text-xs">${escapeHtml(code)}</span>
                    </td>
                    <td>
                        <div class="flex items-center gap-2.5">
                            <div class="w-8 h-8 rounded-lg bg-[#E8EBFA] border border-[#8B5CF6]/30 text-[#8B5CF6] flex items-center justify-center font-bold text-xs">
                                <i data-lucide="book-open" class="w-4 h-4"></i>
                            </div>
                            <div>
                                <p class="text-xs font-bold text-[#171D3A] mb-0">${escapeHtml(name)}</p>
                                <span class="text-[10px] text-[#66708F]">${escapeHtml(s.program || 'BE')}</span>
                            </div>
                        </div>
                    </td>
                    <td class="text-[#171D3A] text-xs">${escapeHtml(dept)}</td>
                    <td><span class="badge-sem">${escapeHtml(sem)}</span></td>
                    <td><span class="badge-subject-type">${escapeHtml(type)}</span></td>
                    <td><span class="badge-credits">${escapeHtml(String(credits))} Credits</span></td>
                    <td class="text-end">
                        <div class="inline-flex items-center gap-1.5">
                            <button class="p-1.5 rounded-lg bg-white border border-[#E1E5F0] text-[#171D3A] hover:bg-[#E8EBFA]" onclick="window.editSubject('${escapeQuotes(id)}')" title="Edit Subject">
                                <i data-lucide="edit-2" class="w-3.5 h-3.5"></i>
                            </button>
                            <button class="p-1.5 rounded-lg bg-white border border-[#E1E5F0] text-red-600 hover:bg-red-50" onclick="window.deleteSubject('${escapeQuotes(id)}')" title="Delete">
                                <i data-lucide="trash-2" class="w-3.5 h-3.5"></i>
                            </button>
                        </div>
                    </td>
                </tr>
            `;
        }).join('');

        if (mobileCards) {
            mobileCards.innerHTML = state.items.map(s => {
                const code = s.subject_code || s.subject_id || '-';
                const name = s.subject_name || s.title || 'Subject';
                const id = s.subject_id || code;
                return `<article class="admin-mobile-record-card subject-mobile-card"><div class="admin-record-heading"><div class="flex items-center gap-3 min-w-0"><div class="admin-record-icon"><i data-lucide="book-open"></i></div><div class="min-w-0"><h3>${escapeHtml(name)}</h3><p>${escapeHtml(s.program || 'BE')}</p></div></div><span class="badge-credits">${escapeHtml(String(s.credits || 4))} Credits</span></div><div class="admin-record-meta"><span><b>Subject Code</b>${escapeHtml(code)}</span><span><b>Department</b>${escapeHtml(s.department || '-')}</span><span><b>Semester</b>Sem ${escapeHtml(String(s.semester || 1))}</span><span><b>Type</b>${escapeHtml(s.subject_type || 'Core Theory')}</span></div><div class="admin-record-actions"><button type="button" onclick="window.editSubject('${escapeQuotes(id)}')" aria-label="Edit ${escapeQuotes(name)}"><i data-lucide="edit-2"></i></button><button type="button" class="is-danger" onclick="window.deleteSubject('${escapeQuotes(id)}')" aria-label="Delete ${escapeQuotes(name)}"><i data-lucide="trash-2"></i></button></div></article>`;
            }).join('');
        }

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
