/**
 * SVIT Admin - Page 2: Admin Management Controller
 * Handles Administrator account list, search, role/status filtering,
 * creation, updates, password reset, and activation toggle.
 */

(function() {
    'use strict';

    let adminModal = null;
    let resetModal = null;
    let deleteModal = null;
    let allAdmins = [];
    let pendingDeleteAdminId = null;

    document.addEventListener('DOMContentLoaded', function() {
        const adminModalEl = document.getElementById('adminAccountModal');
        const resetModalEl = document.getElementById('resetPasswordModal');
        const deleteModalEl = document.getElementById('deleteAdminConfirmModal');

        if (adminModalEl) adminModal = new bootstrap.Modal(adminModalEl);
        if (resetModalEl) resetModal = new bootstrap.Modal(resetModalEl);
        if (deleteModalEl) deleteModal = new bootstrap.Modal(deleteModalEl);

        bindEvents();
        loadAdminAccounts();
    });

    function bindEvents() {
        const refreshBtn = document.getElementById('refreshAdminsBtn');
        if (refreshBtn) refreshBtn.addEventListener('click', loadAdminAccounts);

        const openCreateBtn = document.getElementById('openCreateAdminModalBtn');
        if (openCreateBtn) {
            openCreateBtn.addEventListener('click', () => {
                document.getElementById('adminModalTitle').innerText = 'Create Administrator Account';
                document.getElementById('editAdminId').value = '';
                document.getElementById('adminAccountForm').reset();
                document.getElementById('adminUsername').disabled = false;
                document.getElementById('passwordFieldGroup').style.display = 'block';
                document.getElementById('adminPassword').required = true;
                adminModal.show();
            });
        }

        const form = document.getElementById('adminAccountForm');
        if (form) form.addEventListener('submit', handleAdminFormSubmit);

        const resetForm = document.getElementById('resetPasswordForm');
        if (resetForm) resetForm.addEventListener('submit', handleResetPasswordSubmit);

        const confirmDeleteBtn = document.getElementById('confirmDeleteAdminBtn');
        if (confirmDeleteBtn) confirmDeleteBtn.addEventListener('click', handleConfirmDeleteAdmin);

        // Search & Filters
        const searchInput = document.getElementById('adminSearchInput');
        if (searchInput) searchInput.addEventListener('input', applyFilters);

        const roleFilter = document.getElementById('adminRoleFilter');
        if (roleFilter) roleFilter.addEventListener('change', applyFilters);

        const statusFilter = document.getElementById('adminStatusFilter');
        if (statusFilter) statusFilter.addEventListener('change', applyFilters);
    }

    async function loadAdminAccounts() {
        const tbody = document.getElementById('adminTableBody');
        if (!tbody) return;

        tbody.innerHTML = `
            <tr>
                <td colspan="7" class="text-center py-10 text-gray-400 text-xs">
                    <div class="w-5 h-5 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin mx-auto mb-2"></div>
                    Loading administrators...
                </td>
            </tr>
        `;

        try {
            const res = await fetch('/admin/api/admins', { headers: { 'Accept': 'application/json' } });
            const data = await res.json();
            if (data.status === 'success') {
                allAdmins = data.admins || [];
                applyFilters();
            } else {
                tbody.innerHTML = `<tr><td colspan="7" class="text-center py-6 text-red-400 text-xs">${data.message}</td></tr>`;
            }
        } catch (err) {
            tbody.innerHTML = `<tr><td colspan="7" class="text-center py-6 text-red-400 text-xs">${err.message}</td></tr>`;
        }
        lucide.createIcons();
    }

    function applyFilters() {
        const search = (document.getElementById('adminSearchInput')?.value || '').toLowerCase().trim();
        const role = (document.getElementById('adminRoleFilter')?.value || '').trim();
        const status = (document.getElementById('adminStatusFilter')?.value || '').trim();

        const filtered = allAdmins.filter(a => {
            const matchSearch = !search ||
                (a.name && a.name.toLowerCase().includes(search)) ||
                (a.username && a.username.toLowerCase().includes(search)) ||
                (a.email && a.email.toLowerCase().includes(search)) ||
                (a.department && a.department.toLowerCase().includes(search));

            const matchRole = !role || a.role === role;
            const matchStatus = !status || (status === 'active' ? a.is_active : !a.is_active);

            return matchSearch && matchRole && matchStatus;
        });

        renderAdminsTable(filtered);
    }

    function renderAdminsTable(admins) {
        const tbody = document.getElementById('adminTableBody');
        const countBadge = document.getElementById('adminCountBadge');
        if (countBadge) countBadge.innerText = `${admins.length} Admins`;

        if (!admins || admins.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="7" class="text-center py-10 text-gray-400 text-xs">
                        <i data-lucide="users-2" class="w-8 h-8 mx-auto mb-2 text-gray-600"></i>
                        <p class="mb-0">No administrator accounts match the criteria.</p>
                    </td>
                </tr>
            `;
            lucide.createIcons();
            return;
        }

        tbody.innerHTML = admins.map(a => `
            <tr>
                <td>
                    <div class="flex items-center gap-3">
                        <div class="admin-avatar-pill">
                            ${(a.username || 'AD').slice(0, 2).toUpperCase()}
                        </div>
                        <div>
                            <p class="text-xs font-bold text-white mb-0">${a.name || a.username}</p>
                            <span class="text-[11px] text-gray-400 font-mono">${a.username}</span>
                        </div>
                    </div>
                </td>
                <td class="text-gray-300 text-xs">${a.email}</td>
                <td>
                    <span class="badge-role">${a.role_display || a.role}</span>
                </td>
                <td class="text-gray-300 text-xs">${a.department || 'Central Admin'}</td>
                <td>
                    ${a.is_active ? 
                        '<span class="badge-status-active"><i data-lucide="check-circle" class="w-3 h-3 d-inline mr-1"></i>Active</span>' : 
                        '<span class="badge-status-disabled"><i data-lucide="slash" class="w-3 h-3 d-inline mr-1"></i>Disabled</span>'}
                </td>
                <td class="text-gray-400 text-xs">${a.last_login ? a.last_login.slice(0, 16).replace('T', ' ') : 'Never'}</td>
                <td class="text-end">
                    <div class="inline-flex items-center gap-1.5">
                        <button class="admin-action-btn" onclick="window.openEditAdminModal('${a.id || a.username}')" title="Edit Admin">
                            <i data-lucide="edit-2" class="w-3.5 h-3.5"></i>
                        </button>
                        <button class="admin-action-btn" onclick="window.openResetModal('${a.id || a.username}', '${a.username}')" title="Reset Password">
                            <i data-lucide="key" class="w-3.5 h-3.5"></i>
                        </button>
                        <button class="admin-action-btn ${a.is_active ? 'text-amber-400' : 'text-emerald-400'}" onclick="window.toggleActiveStatus('${a.id || a.username}', ${!a.is_active})" title="${a.is_active ? 'Deactivate' : 'Activate'}">
                            <i data-lucide="${a.is_active ? 'user-x' : 'user-check'}" class="w-3.5 h-3.5"></i>
                        </button>
                    </div>
                </td>
            </tr>
        `).join('');

        lucide.createIcons();
    }

    async function handleAdminFormSubmit(e) {
        e.preventDefault();
        const editId = document.getElementById('editAdminId').value;
        const payload = {
            name: document.getElementById('adminName').value,
            username: document.getElementById('adminUsername').value,
            email: document.getElementById('adminEmail').value,
            role: document.getElementById('adminRole').value,
            department: document.getElementById('adminDepartment').value,
            status: document.getElementById('adminStatusSelect')?.value || 'active'
        };

        const passwordVal = document.getElementById('adminPassword').value;
        if (passwordVal) payload.password = passwordVal;

        const url = editId ? `/admin/api/admins/${editId}` : '/admin/api/admins';
        const method = editId ? 'PUT' : 'POST';

        try {
            const res = await fetch(url, {
                method: method,
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            const data = await res.json();
            if (res.ok && data.status === 'success') {
                showAdminToast(data.message, 'success');
                adminModal.hide();
                loadAdminAccounts();
            } else {
                showAdminToast(data.message || 'Error saving admin.', 'error');
            }
        } catch (err) {
            showAdminToast(err.message, 'error');
        }
    }

    window.openEditAdminModal = function(id) {
        const admin = allAdmins.find(a => String(a.id) === String(id) || a.username === id);
        if (!admin) return;

        document.getElementById('adminModalTitle').innerText = 'Edit Administrator';
        document.getElementById('editAdminId').value = admin.id || admin.username;
        document.getElementById('adminName').value = admin.name || '';
        document.getElementById('adminUsername').value = admin.username || '';
        document.getElementById('adminUsername').disabled = true;
        document.getElementById('adminEmail').value = admin.email || '';
        document.getElementById('adminRole').value = admin.role || 'academic_admin';
        document.getElementById('adminDepartment').value = admin.department || '';
        document.getElementById('passwordFieldGroup').style.display = 'none';
        document.getElementById('adminPassword').required = false;

        adminModal.show();
    };

    window.openResetModal = function(id, username) {
        document.getElementById('resetAdminId').value = id;
        document.getElementById('resetTargetUsername').innerText = username;
        document.getElementById('resetNewPassword').value = '';
        resetModal.show();
    };

    async function handleResetPasswordSubmit(e) {
        e.preventDefault();
        const id = document.getElementById('resetAdminId').value;
        const newPassword = document.getElementById('resetNewPassword').value;

        try {
            const res = await fetch(`/admin/api/admins/${id}/reset-password`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ new_password: newPassword })
            });
            const data = await res.json();
            if (res.ok && data.status === 'success') {
                showAdminToast(data.message, 'success');
                resetModal.hide();
            } else {
                showAdminToast(data.message || 'Error resetting password.', 'error');
            }
        } catch (err) {
            showAdminToast(err.message, 'error');
        }
    }

    window.toggleActiveStatus = async function(id, newState) {
        try {
            const res = await fetch(`/admin/api/admins/${id}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ is_active: newState })
            });
            const data = await res.json();
            if (res.ok && data.status === 'success') {
                showAdminToast(`Admin account updated.`, 'success');
                loadAdminAccounts();
            } else {
                showAdminToast(data.message || 'Error updating status.', 'error');
            }
        } catch (err) {
            showAdminToast(err.message, 'error');
        }
    };

    function handleConfirmDeleteAdmin() {
        // Confirmation handling
    }
})();
