/**
 * SVIT Admin - Page 10: Placements Controller
 * Handles placement drives, company registrations, packages, department filtering,
 * logo upload, add/edit modal, view details modal, and record deletion.
 */

(function() {
    'use strict';

    const state = {
        search: '',
        department: '',
        status: '',
        page: 1,
        limit: 50,
        total: 0,
        items: [],
        pendingDeleteId: null,
        uploadedLogoUrl: null
    };

    let driveModal = null;
    let driveViewModal = null;
    let driveDeleteModal = null;
    let searchDebounce = null;

    document.addEventListener('DOMContentLoaded', function() {
        const formEl = document.getElementById('placementFormModal');
        const viewEl = document.getElementById('placementViewModal');
        const delEl = document.getElementById('placementDeleteModal');

        if (formEl) driveModal = new bootstrap.Modal(formEl);
        if (viewEl) driveViewModal = new bootstrap.Modal(viewEl);
        if (delEl) driveDeleteModal = new bootstrap.Modal(delEl);

        bindEvents();
        setupLogoUpload();
        loadPlacements();
    });

    function bindEvents() {
        const searchInput = document.getElementById('placementSearchInput');
        if (searchInput) {
            searchInput.addEventListener('input', (e) => {
                clearTimeout(searchDebounce);
                searchDebounce = setTimeout(() => {
                    state.search = e.target.value.trim();
                    state.page = 1;
                    loadPlacements();
                }, 300);
            });
        }

        const deptFilter = document.getElementById('placementDeptFilter');
        if (deptFilter) {
            deptFilter.addEventListener('change', (e) => {
                state.department = e.target.value;
                state.page = 1;
                loadPlacements();
            });
        }

        const statusFilter = document.getElementById('placementStatusFilter');
        if (statusFilter) {
            statusFilter.addEventListener('change', (e) => {
                state.status = e.target.value;
                state.page = 1;
                loadPlacements();
            });
        }

        const refreshBtn = document.getElementById('refreshPlacementsBtn');
        if (refreshBtn) refreshBtn.addEventListener('click', loadPlacements);

        const limitSelect = document.getElementById('pageLimitSelect');
        if (limitSelect) {
            limitSelect.addEventListener('change', (e) => {
                state.limit = parseInt(e.target.value, 10) || 50;
                state.page = 1;
                loadPlacements();
            });
        }

        const prevBtn = document.getElementById('prevPageBtn');
        if (prevBtn) {
            prevBtn.addEventListener('click', () => {
                if (state.page > 1) {
                    state.page--;
                    loadPlacements();
                }
            });
        }

        const nextBtn = document.getElementById('nextPageBtn');
        if (nextBtn) {
            nextBtn.addEventListener('click', () => {
                const totalPages = Math.ceil(state.total / state.limit) || 1;
                if (state.page < totalPages) {
                    state.page++;
                    loadPlacements();
                }
            });
        }

        const createBtn = document.getElementById('openCreatePlacementModalBtn');
        if (createBtn) {
            createBtn.addEventListener('click', () => {
                document.getElementById('placementModalTitle').innerText = 'Add Placement Drive';
                document.getElementById('placementFormRecordId').value = '';
                document.getElementById('placementForm').reset();
                document.getElementById('placementIdInput').disabled = false;
                state.uploadedLogoUrl = null;
                resetLogoPreview();
                driveModal.show();
            });
        }

        const form = document.getElementById('placementForm');
        if (form) form.addEventListener('submit', handlePlacementFormSubmit);

        const confirmDeleteBtn = document.getElementById('confirmDeletePlacementBtn');
        if (confirmDeleteBtn) confirmDeleteBtn.addEventListener('click', handleConfirmDelete);
    }

    function setupLogoUpload() {
        const dropZone = document.getElementById('companyLogoDropZone');
        const fileInput = document.getElementById('companyLogoInput');

        if (dropZone && fileInput) {
            dropZone.addEventListener('click', () => fileInput.click());
            dropZone.addEventListener('dragover', (e) => { e.preventDefault(); dropZone.classList.add('border-indigo-500'); });
            dropZone.addEventListener('dragleave', () => dropZone.classList.remove('border-indigo-500'));
            dropZone.addEventListener('drop', (e) => {
                e.preventDefault();
                dropZone.classList.remove('border-indigo-500');
                if (e.dataTransfer.files.length) uploadCompanyLogo(e.dataTransfer.files[0]);
            });
            fileInput.addEventListener('change', (e) => {
                if (e.target.files.length) uploadCompanyLogo(e.target.files[0]);
            });
        }
    }

    async function uploadCompanyLogo(file) {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('category', 'image');

        const preview = document.getElementById('companyLogoPreviewContainer');
        if (preview) {
            preview.innerHTML = '<span class="text-xs text-indigo-400">Uploading logo...</span>';
            preview.classList.remove('hidden');
        }

        try {
            const res = await fetch('/admin/api/upload', { method: 'POST', body: formData });
            const data = await res.json();
            if (res.ok && data.status === 'success') {
                state.uploadedLogoUrl = data.file.url;
                if (preview) {
                    preview.innerHTML = `
                        <img src="${data.file.url}" class="w-12 h-12 rounded-xl object-contain border border-indigo-500 bg-white p-1">
                        <span class="text-xs text-emerald-400 font-medium">Logo Attached</span>
                    `;
                }
                showAdminToast('Company logo attached.', 'success');
            } else {
                showAdminToast(data.message || 'Upload failed.', 'error');
                resetLogoPreview();
            }
        } catch (err) {
            showAdminToast(err.message, 'error');
            resetLogoPreview();
        }
    }

    function resetLogoPreview() {
        const preview = document.getElementById('companyLogoPreviewContainer');
        if (preview) {
            preview.innerHTML = '';
            preview.classList.add('hidden');
        }
    }

    async function loadPlacements() {
        const tbody = document.getElementById('placementsTableBody');
        if (!tbody) return;

        tbody.innerHTML = `
            <tr>
                <td colspan="7" class="text-center py-10 text-gray-400 text-xs">
                    <div class="w-5 h-5 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin mx-auto mb-2"></div>
                    Loading placement drives...
                </td>
            </tr>
        `;

        const params = new URLSearchParams({
            page: state.page,
            limit: state.limit,
            search: state.search
        });
        if (state.department) params.append('filter_department', state.department);
        if (state.status) params.append('filter_status', state.status);

        try {
            const res = await fetch(`/admin/api/crud/placements?${params.toString()}`);
            const data = await res.json();
            if (data.status === 'success') {
                state.items = data.items || [];
                state.total = data.total || 0;
                renderPlacementsTable();
                renderPagination(data);
                updateStatCards();
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
                    loadPlacements();
                };
                numbersContainer.appendChild(btn);
            }
        }
    }

    function updateStatCards() {
        const countBadge = document.getElementById('placementsCountBadge');
        if (countBadge) countBadge.innerText = `${state.total} Drives`;

        // Calculate highest package
        let maxPkg = 0;
        state.items.forEach(it => {
            const val = parseFloat(it.package_lpa);
            if (!isNaN(val) && val > maxPkg) maxPkg = val;
        });

        const highPkgEl = document.getElementById('statHighestPackage');
        if (highPkgEl && maxPkg > 0) highPkgEl.innerText = `${maxPkg} LPA`;
    }

    function renderPlacementsTable() {
        const tbody = document.getElementById('placementsTableBody');
        if (!tbody) return;

        if (state.items.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="7" class="text-center py-12 text-gray-400 text-xs">
                        <i data-lucide="briefcase" class="w-8 h-8 mx-auto mb-2 text-gray-600"></i>
                        <p class="mb-0">No placement drives found.</p>
                    </td>
                </tr>
            `;
            return;
        }

        tbody.innerHTML = state.items.map(p => {
            const id = p.placement_id || p.id || '-';
            const company = p.company_name || p.title || 'Company';
            const role = p.job_role || 'Software Engineer';
            const pkg = p.package_lpa ? `${p.package_lpa} LPA` : 'Best in Industry';
            const depts = p.department || 'All Departments';
            const date = p.drive_date || '-';
            const deadline = p.registration_deadline || '-';
            const status = p.status || 'Upcoming';
            const logo = p.company_logo;

            const statusClass = status === 'Registration Open' ? 'status-open' :
                                status === 'Completed' ? 'status-completed' : 'status-upcoming';

            return `
                <tr>
                    <td>
                        <div class="flex items-center gap-2.5">
                            <div class="company-logo-box">
                                ${logo ? `<img src="${logo}" alt="${company}">` : '<i data-lucide="building-2" class="w-4 h-4 text-indigo-400"></i>'}
                            </div>
                            <div>
                                <p class="text-xs font-bold text-white mb-0">${company}</p>
                                <span class="text-[10px] text-indigo-400 font-mono">${id}</span>
                            </div>
                        </div>
                    </td>
                    <td class="text-gray-200 font-medium text-xs">${role}</td>
                    <td><span class="badge-package">${pkg}</span></td>
                    <td class="text-gray-300 text-xs">${depts}</td>
                    <td class="text-gray-400 text-xs">${date}</td>
                    <td><span class="badge-drive-status ${statusClass}">${status}</span></td>
                    <td class="text-end">
                        <div class="inline-flex items-center gap-1.5">
                            <button class="p-1.5 rounded-lg bg-[#0F172A] border border-[#1F2937] text-gray-300 hover:text-white" onclick="window.viewPlacement('${id}')" title="View Drive">
                                <i data-lucide="eye" class="w-3.5 h-3.5"></i>
                            </button>
                            <button class="p-1.5 rounded-lg bg-[#0F172A] border border-[#1F2937] text-gray-300 hover:text-white" onclick="window.editPlacement('${id}')" title="Edit Drive">
                                <i data-lucide="edit-2" class="w-3.5 h-3.5"></i>
                            </button>
                            <button class="p-1.5 rounded-lg bg-[#0F172A] border border-[#1F2937] text-red-400 hover:bg-red-500/20" onclick="window.deletePlacement('${id}')" title="Delete">
                                <i data-lucide="trash-2" class="w-3.5 h-3.5"></i>
                            </button>
                        </div>
                    </td>
                </tr>
            `;
        }).join('');
    }

    async function handlePlacementFormSubmit(e) {
        e.preventDefault();
        const recordId = document.getElementById('placementFormRecordId').value;
        const payload = {
            placement_id: document.getElementById('placementIdInput').value.trim(),
            company_name: document.getElementById('placementCompanyInput').value.trim(),
            job_role: document.getElementById('placementRoleInput').value.trim(),
            package_lpa: document.getElementById('placementPkgInput').value.trim(),
            department: document.getElementById('placementDeptInput').value.trim(),
            drive_date: document.getElementById('placementDateInput').value,
            registration_deadline: document.getElementById('placementDeadlineInput').value,
            status: document.getElementById('placementStatusInput').value,
            eligibility: document.getElementById('placementEligInput').value.trim()
        };

        if (state.uploadedLogoUrl) payload.company_logo = state.uploadedLogoUrl;

        const isEdit = Boolean(recordId);
        const url = isEdit ? `/admin/api/crud/placements/${recordId}` : '/admin/api/crud/placements';
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
                driveModal.hide();
                loadPlacements();
            } else {
                showAdminToast(data.message || 'Error saving placement record.', 'error');
            }
        } catch (err) {
            showAdminToast(err.message, 'error');
        }
    }

    window.editPlacement = function(id) {
        const drive = state.items.find(p => (p.placement_id || p.id) === id);
        if (!drive) return;

        document.getElementById('placementModalTitle').innerText = 'Edit Placement Drive';
        document.getElementById('placementFormRecordId').value = id;
        document.getElementById('placementIdInput').value = drive.placement_id || id;
        document.getElementById('placementIdInput').disabled = true;
        document.getElementById('placementCompanyInput').value = drive.company_name || '';
        document.getElementById('placementRoleInput').value = drive.job_role || '';
        document.getElementById('placementPkgInput').value = drive.package_lpa || '';
        document.getElementById('placementDeptInput').value = drive.department || '';
        document.getElementById('placementDateInput').value = drive.drive_date || '';
        document.getElementById('placementDeadlineInput').value = drive.registration_deadline || '';
        document.getElementById('placementStatusInput').value = drive.status || 'Upcoming';
        document.getElementById('placementEligInput').value = drive.eligibility || '';

        state.uploadedLogoUrl = drive.company_logo || null;
        if (drive.company_logo) {
            const preview = document.getElementById('companyLogoPreviewContainer');
            if (preview) {
                preview.innerHTML = `<img src="${drive.company_logo}" class="w-12 h-12 rounded-lg object-contain bg-white/10 p-1 border border-indigo-500/50">`;
                preview.classList.remove('hidden');
            }
        } else {
            resetLogoPreview();
        }

        driveModal.show();
    };

    window.viewPlacement = function(id) {
        const drive = state.items.find(p => (p.placement_id || p.id) === id);
        if (!drive) return;

        const container = document.getElementById('placementViewContent');
        if (!container) return;

        container.innerHTML = `
            <div class="space-y-4">
                <div class="flex items-center gap-3.5 p-4 rounded-2xl bg-[#0F172A] border border-[#1F2937]">
                    <div class="w-14 h-14 rounded-2xl bg-indigo-600/20 border border-indigo-500/30 text-indigo-400 font-bold text-lg flex items-center justify-center overflow-hidden flex-shrink-0">
                        ${drive.company_logo ? `<img src="${drive.company_logo}" class="w-full h-full object-contain p-1">` : '<i data-lucide="briefcase" class="w-7 h-7"></i>'}
                    </div>
                    <div>
                        <h3 class="text-base font-bold text-white mb-0.5">${drive.company_name}</h3>
                        <p class="text-xs text-indigo-400 font-semibold mb-0">${drive.job_role} • <span class="text-emerald-400">${drive.package_lpa} LPA</span></p>
                    </div>
                </div>
                <div class="grid grid-cols-2 gap-3 text-xs">
                    <div class="p-2.5 rounded-lg bg-[#0F172A] border border-[#1F2937]">
                        <span class="text-gray-500 block text-[10px]">ELIGIBLE DEPARTMENTS</span>
                        <span class="text-white font-medium">${drive.department || 'All'}</span>
                    </div>
                    <div class="p-2.5 rounded-lg bg-[#0F172A] border border-[#1F2937]">
                        <span class="text-gray-500 block text-[10px]">DRIVE DATE</span>
                        <span class="text-white font-medium">${drive.drive_date || '-'}</span>
                    </div>
                    <div class="p-2.5 rounded-lg bg-[#0F172A] border border-[#1F2937]">
                        <span class="text-gray-500 block text-[10px]">REGISTRATION DEADLINE</span>
                        <span class="text-white font-medium">${drive.registration_deadline || '-'}</span>
                    </div>
                    <div class="p-2.5 rounded-lg bg-[#0F172A] border border-[#1F2937]">
                        <span class="text-gray-500 block text-[10px]">CURRENT STATUS</span>
                        <span class="text-indigo-300 font-medium">${drive.status || 'Upcoming'}</span>
                    </div>
                </div>
                <div class="p-3 rounded-lg bg-[#0F172A] border border-[#1F2937] text-xs text-gray-300">
                    <span class="text-gray-500 block text-[10px] mb-1">ELIGIBILITY CRITERIA</span>
                    ${drive.eligibility || 'No specific criteria listed.'}
                </div>
            </div>
        `;

        driveViewModal.show();
    };

    window.deletePlacement = function(id) {
        state.pendingDeleteId = id;
        document.getElementById('deletePlacementTargetId').innerText = id;
        driveDeleteModal.show();
    };

    async function handleConfirmDelete() {
        if (!state.pendingDeleteId) return;

        try {
            const res = await fetch(`/admin/api/crud/placements/${state.pendingDeleteId}`, { method: 'DELETE' });
            const data = await res.json();
            if (res.ok && data.status === 'success') {
                showAdminToast(data.message, 'success');
                driveDeleteModal.hide();
                loadPlacements();
            } else {
                showAdminToast(data.message || 'Failed to delete placement drive.', 'error');
            }
        } catch (err) {
            showAdminToast(err.message, 'error');
        }
    }
})();
