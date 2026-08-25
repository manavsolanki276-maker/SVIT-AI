/**
 * SVIT Admin - Page 21: Library Members Controller
 * Library card accounts, membership types (Student, Faculty),
 * loan limits, add/edit modal, and member deletion.
 */

(function() {
    'use strict';

    const state = {
        search: '',
        type: '',
        page: 1,
        limit: 50,
        total: 0,
        items: [],
        pendingDeleteId: null
    };

    let memberModal = null;
    let deleteModal = null;
    let searchDebounce = null;

    document.addEventListener('DOMContentLoaded', function() {
        const formEl = document.getElementById('memberFormModal');
        const delEl = document.getElementById('memberDeleteModal');

        if (formEl) memberModal = new bootstrap.Modal(formEl);
        if (delEl) deleteModal = new bootstrap.Modal(delEl);

        bindEvents();
        loadMembers();
    });

    function bindEvents() {
        const searchInput = document.getElementById('memberSearchInput');
        if (searchInput) {
            searchInput.addEventListener('input', (e) => {
                clearTimeout(searchDebounce);
                searchDebounce = setTimeout(() => {
                    state.search = e.target.value.trim();
                    state.page = 1;
                    loadMembers();
                }, 300);
            });
        }

        const typeFilter = document.getElementById('memberTypeFilter');
        if (typeFilter) {
            typeFilter.addEventListener('change', (e) => {
                state.type = e.target.value;
                state.page = 1;
                loadMembers();
            });
        }

        const refreshBtn = document.getElementById('refreshMembersBtn');
        if (refreshBtn) refreshBtn.addEventListener('click', loadMembers);

        const createBtn = document.getElementById('openCreateMemberModalBtn');
        if (createBtn) {
            createBtn.addEventListener('click', () => {
                document.getElementById('memberModalTitle').innerText = 'Issue Library Membership Card';
                document.getElementById('memberFormRecordId').value = '';
                document.getElementById('memberForm').reset();
                document.getElementById('memberCardNoInput').disabled = false;
                memberModal.show();
            });
        }

        const form = document.getElementById('memberForm');
        if (form) form.addEventListener('submit', handleMemberFormSubmit);

        const confirmDeleteBtn = document.getElementById('confirmDeleteMemberBtn');
        if (confirmDeleteBtn) confirmDeleteBtn.addEventListener('click', handleConfirmDelete);
    }

    async function loadMembers() {
        const tbody = document.getElementById('membersTableBody');
        if (tbody) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="7" class="text-center py-10 text-gray-400 text-xs">
                        <div class="w-5 h-5 border-2 border-teal-500 border-t-transparent rounded-full animate-spin mx-auto mb-2"></div>
                        Loading library card members...
                    </td>
                </tr>
            `;
        }

        const params = new URLSearchParams({
            page: state.page,
            limit: state.limit,
            search: state.search
        });
        if (state.type) params.append('filter_member_type', state.type);

        try {
            const res = await fetch(`/admin/api/crud/library_members?${params.toString()}`);
            const data = await res.json();
            if (data.status === 'success') {
                state.items = data.items || [];
                state.total = data.total || 0;
                renderMembersTable();
            } else {
                if (tbody) tbody.innerHTML = `<tr><td colspan="7" class="text-center py-6 text-red-400 text-xs">${data.message}</td></tr>`;
            }
        } catch (err) {
            if (tbody) tbody.innerHTML = `<tr><td colspan="7" class="text-center py-6 text-red-400 text-xs">${err.message}</td></tr>`;
        }
        lucide.createIcons();
    }

    function renderMembersTable() {
        const tbody = document.getElementById('membersTableBody');
        const countBadge = document.getElementById('membersCountBadge');
        if (countBadge) countBadge.innerText = `${state.total} Members`;

        if (!tbody) return;

        if (state.items.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="7" class="text-center py-12 text-gray-400 text-xs">
                        <i data-lucide="users" class="w-8 h-8 mx-auto mb-2 text-gray-600"></i>
                        <p class="mb-0">No library card members found.</p>
                    </td>
                </tr>
            `;
            return;
        }

        tbody.innerHTML = state.items.map(m => {
            const id = m.member_id || m.id || '-';
            const name = m.name || m.full_name || 'Member';
            const cardNo = m.card_number || m.card_no || id;
            const type = m.member_type || m.type || 'Student';
            const dept = m.department || 'General';
            const maxBooks = m.max_books_allowed || m.max_books || 3;
            const issuedCount = m.currently_issued || 0;
            const status = m.status || 'Active';

            return `
                <tr>
                    <td>
                        <div class="flex items-center gap-2.5">
                            <div class="member-avatar-box">
                                ${name.slice(0, 2).toUpperCase()}
                            </div>
                            <div>
                                <p class="text-xs font-bold text-white mb-0">${name}</p>
                                <span class="text-[10px] text-teal-400 font-mono">${cardNo}</span>
                            </div>
                        </div>
                    </td>
                    <td>
                        <span class="px-2 py-0.5 rounded text-[10px] bg-indigo-500/20 text-indigo-300 font-semibold">${type}</span>
                    </td>
                    <td class="text-gray-300 text-xs">${dept}</td>
                    <td class="text-gray-300 text-xs">${maxBooks} Books Max</td>
                    <td>
                        <span class="text-teal-300 font-bold text-xs">${issuedCount} Issued</span>
                    </td>
                    <td>
                        <span class="px-2 py-0.5 rounded text-[10px] bg-emerald-500/20 text-emerald-300 font-semibold flex items-center gap-1 w-max">
                            <span class="w-1.5 h-1.5 rounded-full bg-emerald-400"></span> ${status}
                        </span>
                    </td>
                    <td class="text-end">
                        <button class="p-1.5 rounded-lg bg-[#0F172A] border border-[#1F2937] text-gray-300 hover:text-white" onclick="window.editMember('${id}')">
                            <i data-lucide="edit-2" class="w-3.5 h-3.5"></i>
                        </button>
                        <button class="p-1.5 rounded-lg bg-[#0F172A] border border-[#1F2937] text-red-400 hover:bg-red-500/20" onclick="window.deleteMember('${id}')">
                            <i data-lucide="trash-2" class="w-3.5 h-3.5"></i>
                        </button>
                    </td>
                </tr>
            `;
        }).join('');

        lucide.createIcons();
    }

    async function handleMemberFormSubmit(e) {
        e.preventDefault();
        const recordId = document.getElementById('memberFormRecordId').value;
        const cardNo = document.getElementById('memberCardNoInput').value.trim();
        const name = document.getElementById('memberNameInput').value.trim();

        const payload = {
            member_id: cardNo || `LIB-MEM-${Date.now()}`,
            name: name,
            card_number: cardNo,
            member_type: document.getElementById('memberTypeSelect').value,
            department: document.getElementById('memberDeptSelect').value,
            max_books_allowed: parseInt(document.getElementById('memberMaxBooksInput').value, 10) || 3,
            email: `${cardNo.toLowerCase()}@svit.ac.in`,
            status: 'Active'
        };

        const isEdit = Boolean(recordId);
        const url = isEdit ? `/admin/api/crud/library_members/${recordId}` : '/admin/api/crud/library_members';
        const method = isEdit ? 'PUT' : 'POST';

        try {
            const res = await fetch(url, {
                method: method,
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            const data = await res.json();
            if (res.ok && data.status === 'success') {
                showAdminToast(data.message || 'Library card saved successfully.', 'success');
                memberModal.hide();
                loadMembers();
            } else {
                showAdminToast(data.message || 'Error saving member.', 'error');
            }
        } catch (err) {
            showAdminToast(err.message, 'error');
        }
    }

    window.editMember = function(id) {
        const item = state.items.find(m => (m.member_id || m.id) === id);
        if (!item) return;

        document.getElementById('memberModalTitle').innerText = 'Edit Membership Card';
        document.getElementById('memberFormRecordId').value = id;
        document.getElementById('memberCardNoInput').value = item.card_number || item.card_no || item.member_id || id;
        document.getElementById('memberCardNoInput').disabled = true;
        document.getElementById('memberNameInput').value = item.name || item.full_name || '';
        document.getElementById('memberTypeSelect').value = item.member_type || item.type || 'Student';
        document.getElementById('memberDeptSelect').value = item.department || 'Computer Engineering';
        document.getElementById('memberMaxBooksInput').value = item.max_books_allowed || item.max_books || 3;

        memberModal.show();
    };

    window.deleteMember = function(id) {
        state.pendingDeleteId = id;
        document.getElementById('deleteMemberTargetId').innerText = id;
        deleteModal.show();
    };

    async function handleConfirmDelete() {
        if (!state.pendingDeleteId) return;

        try {
            const res = await fetch(`/admin/api/crud/library_members/${state.pendingDeleteId}`, { method: 'DELETE' });
            const data = await res.json();
            if (res.ok && data.status === 'success') {
                showAdminToast(data.message || 'Membership card deleted.', 'success');
                deleteModal.hide();
                loadMembers();
            } else {
                showAdminToast(data.message || 'Failed to delete membership card.', 'error');
            }
        } catch (err) {
            showAdminToast(err.message, 'error');
        }
    }
})();
