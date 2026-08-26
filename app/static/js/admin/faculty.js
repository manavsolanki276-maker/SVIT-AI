/**
 * SVIT Admin - Page 6: Faculty Controller
 * Handles faculty roster, department & designation filtering, image upload,
 * add/edit modal, details modal, and deletion.
 */

(function() {
    'use strict';

    const state = {
        search: '',
        department: '',
        designation: '',
        viewMode: 'table', // 'table' or 'grid'
        page: 1,
        limit: 20,
        total: 0,
        items: [],
        pendingDeleteId: null,
        uploadedImageUrl: null
    };

    let facultyFormModal = null;
    let facultyViewModal = null;
    let facultyDeleteModal = null;
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
        const formEl = document.getElementById('facultyFormModal');
        const viewEl = document.getElementById('facultyViewModal');
        const delEl = document.getElementById('facultyDeleteModal');

        if (formEl) facultyFormModal = new bootstrap.Modal(formEl);
        if (viewEl) facultyViewModal = new bootstrap.Modal(viewEl);
        if (delEl) facultyDeleteModal = new bootstrap.Modal(delEl);

        bindEvents();
        setupImageUpload();
        loadFaculty();
    });

    function bindEvents() {
        const searchInput = document.getElementById('facultySearchInput');
        if (searchInput) {
            searchInput.addEventListener('input', (e) => {
                clearTimeout(searchDebounce);
                searchDebounce = setTimeout(() => {
                    state.search = e.target.value.trim();
                    state.page = 1;
                    loadFaculty();
                }, 300);
            });
        }

        const deptFilter = document.getElementById('facultyDeptFilter');
        if (deptFilter) {
            deptFilter.addEventListener('change', (e) => {
                state.department = e.target.value;
                state.page = 1;
                loadFaculty();
            });
        }

        const desigFilter = document.getElementById('facultyDesigFilter');
        if (desigFilter) {
            desigFilter.addEventListener('change', (e) => {
                state.designation = e.target.value;
                state.page = 1;
                loadFaculty();
            });
        }

        const refreshBtn = document.getElementById('refreshFacultyBtn');
        if (refreshBtn) refreshBtn.addEventListener('click', loadFaculty);

        const limitSelect = document.getElementById('pageLimitSelect');
        if (limitSelect) {
            limitSelect.addEventListener('change', (e) => {
                state.limit = parseInt(e.target.value, 10) || 50;
                state.page = 1;
                loadFaculty();
            });
        }

        const prevBtn = document.getElementById('prevPageBtn');
        if (prevBtn) {
            prevBtn.addEventListener('click', () => {
                if (state.page > 1) {
                    state.page--;
                    loadFaculty();
                }
            });
        }

        const nextBtn = document.getElementById('nextPageBtn');
        if (nextBtn) {
            nextBtn.addEventListener('click', () => {
                const totalPages = Math.ceil(state.total / state.limit) || 1;
                if (state.page < totalPages) {
                    state.page++;
                    loadFaculty();
                }
            });
        }

        const openCreateBtn = document.getElementById('openCreateFacultyModalBtn');
        if (openCreateBtn) {
            openCreateBtn.addEventListener('click', () => {
                document.getElementById('facultyModalTitle').innerText = 'Add Faculty Member';
                document.getElementById('facultyFormRecordId').value = '';
                document.getElementById('facultyForm').reset();
                document.getElementById('facultyIdInput').disabled = false;
                state.uploadedImageUrl = null;
                resetImagePreview();
                facultyFormModal.show();
            });
        }

        const form = document.getElementById('facultyForm');
        if (form) form.addEventListener('submit', handleFacultyFormSubmit);

        const confirmDeleteBtn = document.getElementById('confirmDeleteFacultyBtn');
        if (confirmDeleteBtn) confirmDeleteBtn.addEventListener('click', handleConfirmDelete);

        // View toggle
        const toggleTableBtn = document.getElementById('viewTableToggleBtn');
        const toggleGridBtn = document.getElementById('viewGridToggleBtn');

        if (toggleTableBtn && toggleGridBtn) {
            toggleTableBtn.addEventListener('click', () => {
                state.viewMode = 'table';
                toggleTableBtn.classList.add('bg-indigo-600', 'text-white');
                toggleGridBtn.classList.remove('bg-indigo-600', 'text-white');
                document.getElementById('facultyTableView').classList.remove('hidden');
                document.getElementById('facultyGridView').classList.add('hidden');
                renderFaculty();
            });
            toggleGridBtn.addEventListener('click', () => {
                state.viewMode = 'grid';
                toggleGridBtn.classList.add('bg-indigo-600', 'text-white');
                toggleTableBtn.classList.remove('bg-indigo-600', 'text-white');
                document.getElementById('facultyGridView').classList.remove('hidden');
                document.getElementById('facultyTableView').classList.add('hidden');
                renderFaculty();
            });
        }
    }

    function setupImageUpload() {
        const dropZone = document.getElementById('facultyImageDropZone');
        const fileInput = document.getElementById('facultyImageInput');

        if (dropZone && fileInput) {
            dropZone.addEventListener('click', () => fileInput.click());
            dropZone.addEventListener('dragover', (e) => { e.preventDefault(); dropZone.classList.add('border-indigo-500'); });
            dropZone.addEventListener('dragleave', () => dropZone.classList.remove('border-indigo-500'));
            dropZone.addEventListener('drop', (e) => {
                e.preventDefault();
                dropZone.classList.remove('border-indigo-500');
                if (e.dataTransfer.files.length) uploadFacultyImage(e.dataTransfer.files[0]);
            });
            fileInput.addEventListener('change', (e) => {
                if (e.target.files.length) uploadFacultyImage(e.target.files[0]);
            });
        }
    }

    async function uploadFacultyImage(file) {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('category', 'image');

        const preview = document.getElementById('facultyImagePreviewContainer');
        if (preview) {
            preview.innerHTML = '<span class="text-xs text-indigo-400">Uploading photo...</span>';
            preview.classList.remove('hidden');
        }

        try {
            const res = await fetch('/admin/api/upload', { method: 'POST', body: formData });
            const data = await res.json();
            if (res.ok && data.status === 'success') {
                state.uploadedImageUrl = data.file.url;
                if (preview) {
                    preview.innerHTML = `
                        <img src="${data.file.url}" class="w-12 h-12 rounded-full object-cover border border-indigo-500">
                        <span class="text-xs text-emerald-400 font-medium">Photo Attached</span>
                    `;
                }
                showAdminToast('Faculty photo attached.', 'success');
            } else {
                showAdminToast(data.message || 'Upload failed.', 'error');
                resetImagePreview();
            }
        } catch (err) {
            showAdminToast(err.message, 'error');
            resetImagePreview();
        }
    }

    function resetImagePreview() {
        const preview = document.getElementById('facultyImagePreviewContainer');
        if (preview) {
            preview.innerHTML = '';
            preview.classList.add('hidden');
        }
    }

    async function loadFaculty() {
        const tbody = document.getElementById('facultyTableBody');
        const grid = document.getElementById('facultyGridContainer');

        if (tbody) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="8" class="text-center py-10 text-gray-400 text-xs">
                        <div class="w-5 h-5 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin mx-auto mb-2"></div>
                        Loading faculty roster...
                    </td>
                </tr>
            `;
        }

        const params = new URLSearchParams({
            page: state.page,
            limit: state.limit,
            search: state.search
        });
        if (state.department) params.append('filter_department', state.department);
        if (state.designation) params.append('filter_designation', state.designation);

        try {
            const res = await fetch(`/admin/api/crud/faculty?${params.toString()}`);
            const data = await res.json();
            if (data.status === 'success') {
                state.items = data.items || [];
                state.total = data.total || 0;
                renderFaculty();
                renderPagination(data);
            } else {
                if (tbody) tbody.innerHTML = `<tr><td colspan="8" class="text-center py-6 text-red-400 text-xs">${data.message}</td></tr>`;
            }
        } catch (err) {
            if (tbody) tbody.innerHTML = `<tr><td colspan="8" class="text-center py-6 text-red-400 text-xs">${err.message}</td></tr>`;
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
                    loadFaculty();
                };
                numbersContainer.appendChild(btn);
            }
        }
    }

    function renderFaculty() {
        const countBadge = document.getElementById('facultyCountBadge');
        if (countBadge) countBadge.innerText = `${state.total} Faculty`;

        if (state.viewMode === 'table') {
            renderTableView();
        } else {
            renderGridView();
        }
        lucide.createIcons();
    }

    function renderTableView() {
        const tbody = document.getElementById('facultyTableBody');
        const mobileCards = document.getElementById('facultyMobileCards');
        if (!tbody) return;

        if (state.items.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="8" class="text-center py-12 text-[#66708F] text-xs">
                        <i data-lucide="user-check" class="w-8 h-8 mx-auto mb-2 text-[#8C95AD]"></i>
                        <p class="mb-0">No faculty records found.</p>
                    </td>
                </tr>
            `;
            if (mobileCards) mobileCards.innerHTML = '<div class="admin-mobile-empty text-center py-8 text-xs text-[#66708F]">No faculty records found.</div>';
            return;
        }

        tbody.innerHTML = state.items.map(f => {
            const name = f.full_name || f.name || 'Professor';
            const fId = f.faculty_id || f.id || '-';
            const desig = f.designation || 'Lecturer';
            const dept = f.department || '-';
            const subject = f.subject || '-';
            const email = f.email || '-';
            const cabin = f.cabin || '-';
            const img = f.image_url;

            return `
                <tr>
                    <td>
                        <span class="font-mono text-[#8B5CF6] font-bold text-xs">${fId}</span>
                    </td>
                    <td>
                        <div class="flex items-center gap-2.5">
                            <div class="faculty-avatar">
                                ${img ? `<img src="${img}" alt="${name}">` : name.slice(0, 2).toUpperCase()}
                            </div>
                            <div>
                                <p class="text-xs font-bold text-[#171D3A] mb-0">${name}</p>
                                <span class="text-[10px] text-[#66708F]">${f.qualification || 'M.Tech / Ph.D'}</span>
                            </div>
                        </div>
                    </td>
                    <td class="text-[#171D3A] text-xs">${dept}</td>
                    <td><span class="badge-designation px-2 py-0.5 rounded text-[10px] bg-[#E8EBFA] text-[#8B5CF6] font-semibold">${desig}</span></td>
                    <td class="text-[#171D3A] text-xs">${subject}</td>
                    <td class="text-[#66708F] text-xs">${email}</td>
                    <td class="text-[#66708F] text-xs font-mono">${cabin}</td>
                    <td class="text-end">
                        <div class="inline-flex items-center gap-1.5">
                            <button class="p-1.5 rounded-lg bg-white border border-[#E1E5F0] text-[#171D3A] hover:bg-[#E8EBFA]" onclick="window.viewFaculty('${fId}')" title="View Details">
                                <i data-lucide="eye" class="w-3.5 h-3.5"></i>
                            </button>
                            <button class="p-1.5 rounded-lg bg-white border border-[#E1E5F0] text-[#171D3A] hover:bg-[#E8EBFA]" onclick="window.editFaculty('${fId}')" title="Edit Faculty">
                                <i data-lucide="edit-2" class="w-3.5 h-3.5"></i>
                            </button>
                            <button class="p-1.5 rounded-lg bg-white border border-[#E1E5F0] text-red-600 hover:bg-red-50" onclick="window.deleteFaculty('${fId}')" title="Delete">
                                <i data-lucide="trash-2" class="w-3.5 h-3.5"></i>
                            </button>
                        </div>
                    </td>
                </tr>
            `;
        }).join('');

        if (mobileCards) {
            mobileCards.innerHTML = state.items.map(f => {
                const name = f.full_name || f.name || 'Professor';
                const fId = f.faculty_id || f.id || '-';
                const desig = f.designation || 'Faculty';
                const dept = f.department || '-';
                const subject = f.subject || '-';
                const cabin = f.cabin || '-';
                const img = f.image_url;

                return `<article class="admin-mobile-record-card faculty-mobile-card">
                    <div class="admin-record-heading">
                        <div class="flex items-center gap-3 min-w-0">
                            <div class="faculty-avatar">${img ? `<img src="${img}" alt="${name}">` : name.slice(0, 2).toUpperCase()}</div>
                            <div class="min-w-0">
                                <h3>${escapeHtml(name)}</h3>
                                <p>${escapeHtml(fId)}</p>
                            </div>
                        </div>
                        <span class="px-2 py-0.5 rounded text-[10px] font-bold bg-[#E8EBFA] text-[#8B5CF6]">${escapeHtml(desig)}</span>
                    </div>
                    <div class="admin-record-meta">
                        <span><b>Department</b>${escapeHtml(dept)}</span>
                        <span><b>Primary Subject</b>${escapeHtml(subject)}</span>
                        <span><b>Cabin</b>${escapeHtml(cabin)}</span>
                        <span><b>Email</b>${escapeHtml(f.email || '-')}</span>
                    </div>
                    <div class="admin-record-actions">
                        <button type="button" onclick="window.viewFaculty('${escapeQuotes(fId)}')" title="View Details">
                            <i data-lucide="eye"></i> <span>Details</span>
                        </button>
                        <button type="button" onclick="window.editFaculty('${escapeQuotes(fId)}')" title="Edit Faculty">
                            <i data-lucide="edit-2"></i> <span>Edit</span>
                        </button>
                        <button type="button" class="is-danger" onclick="window.deleteFaculty('${escapeQuotes(fId)}')" title="Delete Faculty">
                            <i data-lucide="trash-2"></i>
                        </button>
                    </div>
                </article>`;
            }).join('');
        }
    }

    function renderGridView() {
        const grid = document.getElementById('facultyGridContainer');
        if (!grid) return;

        if (state.items.length === 0) {
            grid.innerHTML = `<div class="col-span-full text-center py-10 text-gray-400 text-xs">No faculty records found.</div>`;
            return;
        }

        grid.innerHTML = state.items.map(f => {
            const name = f.full_name || f.name || 'Professor';
            const fId = f.faculty_id || f.id || '-';
            const desig = f.designation || 'Lecturer';
            const dept = f.department || '-';
            const img = f.image_url;

            return `
                <div class="p-4 rounded-2xl bg-white border border-[#E1E5F0] shadow-sm flex flex-col justify-between space-y-3">
                    <div class="flex items-start gap-3">
                        <div class="w-14 h-14 rounded-2xl bg-[#E8EBFA] border border-[#8B5CF6]/30 text-[#8B5CF6] flex items-center justify-center font-bold text-base overflow-hidden flex-shrink-0">
                            ${img ? `<img src="${img}" class="w-full h-full object-cover">` : name.slice(0, 2).toUpperCase()}
                        </div>
                        <div class="min-w-0 flex-1">
                            <span class="badge-designation mb-1 inline-block">${escapeHtml(desig)}</span>
                            <h4 class="text-sm font-bold text-[#171D3A] mb-0.5 truncate">${escapeHtml(name)}</h4>
                            <p class="text-[11px] text-[#66708F] mb-0 truncate">${escapeHtml(dept)}</p>
                        </div>
                    </div>
                    <div class="text-xs text-[#66708F] space-y-1 pt-2 border-t border-[#E1E5F0]">
                        <div class="flex justify-between"><span class="text-[#8C95AD]">ID:</span> <span class="font-mono text-[#8B5CF6]">${escapeHtml(fId)}</span></div>
                        <div class="flex justify-between"><span class="text-[#8C95AD]">Cabin:</span> <span class="text-[#171D3A]">${escapeHtml(f.cabin || 'Main Dept')}</span></div>
                        <div class="flex justify-between truncate"><span class="text-[#8C95AD]">Email:</span> <span class="text-[#171D3A] truncate">${escapeHtml(f.email || '-')}</span></div>
                    </div>
                    <div class="pt-2 flex justify-end gap-1.5 border-t border-[#E1E5F0]">
                        <button class="px-3 py-1.5 rounded-xl bg-white border border-[#E1E5F0] text-[#171D3A] text-xs font-semibold hover:bg-[#E8EBFA]" onclick="window.viewFaculty('${escapeQuotes(fId)}')">Details</button>
                        <button class="btn-primary-custom px-3 py-1 text-xs" onclick="window.editFaculty('${escapeQuotes(fId)}')">Edit</button>
                    </div>
                </div>
            `;
        }).join('');
    }

    async function handleFacultyFormSubmit(e) {
        e.preventDefault();
        const recordId = document.getElementById('facultyFormRecordId').value;
        const payload = {
            faculty_id: document.getElementById('facultyIdInput').value.trim(),
            full_name: document.getElementById('facultyNameInput').value.trim(),
            designation: document.getElementById('facultyDesigInput').value,
            department: document.getElementById('facultyDeptInput').value,
            subject: document.getElementById('facultySubjectInput').value.trim(),
            email: document.getElementById('facultyEmailInput').value.trim(),
            phone: document.getElementById('facultyPhoneInput').value.trim(),
            cabin: document.getElementById('facultyCabinInput').value.trim(),
            qualification: document.getElementById('facultyQualInput').value.trim()
        };

        if (state.uploadedImageUrl) payload.image_url = state.uploadedImageUrl;

        const isEdit = Boolean(recordId);
        const url = isEdit ? `/admin/api/crud/faculty/${recordId}` : '/admin/api/crud/faculty';
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
                facultyFormModal.hide();
                loadFaculty();
            } else {
                showAdminToast(data.message || 'Error saving faculty record.', 'error');
            }
        } catch (err) {
            showAdminToast(err.message, 'error');
        }
    }

    window.editFaculty = function(fId) {
        const fac = state.items.find(f => (f.faculty_id || f.id) === fId);
        if (!fac) return;

        document.getElementById('facultyModalTitle').innerText = 'Edit Faculty Profile';
        document.getElementById('facultyFormRecordId').value = fId;
        document.getElementById('facultyIdInput').value = fac.faculty_id || fId;
        document.getElementById('facultyIdInput').disabled = true;
        document.getElementById('facultyNameInput').value = fac.full_name || fac.name || '';
        document.getElementById('facultyDesigInput').value = fac.designation || 'Assistant Professor';
        document.getElementById('facultyDeptInput').value = fac.department || 'Computer Engineering';
        document.getElementById('facultySubjectInput').value = fac.subject || '';
        document.getElementById('facultyEmailInput').value = fac.email || '';
        document.getElementById('facultyPhoneInput').value = fac.phone || '';
        document.getElementById('facultyCabinInput').value = fac.cabin || '';
        document.getElementById('facultyQualInput').value = fac.qualification || '';

        state.uploadedImageUrl = fac.image_url || null;
        if (fac.image_url) {
            const preview = document.getElementById('facultyImagePreviewContainer');
            if (preview) {
                preview.innerHTML = `<img src="${fac.image_url}" class="w-16 h-16 rounded-xl object-cover border border-[#8B5CF6]">`;
                preview.classList.remove('hidden');
            }
        } else {
            resetImagePreview();
        }

        facultyFormModal.show();
    };

    window.viewFaculty = function(fId) {
        const fac = state.items.find(f => (f.faculty_id || f.id) === fId);
        if (!fac) return;

        const container = document.getElementById('facultyViewContent');
        if (!container) return;

        container.innerHTML = `
            <div class="space-y-4">
                <div class="flex items-center gap-3.5 p-4 rounded-2xl bg-[#F8F9FE] border border-[#E1E5F0]">
                    <div class="w-16 h-16 rounded-2xl bg-[#E8EBFA] border border-[#8B5CF6]/30 text-[#8B5CF6] font-bold text-xl flex items-center justify-center overflow-hidden flex-shrink-0 shadow-sm">
                        ${fac.image_url ? `<img src="${fac.image_url}" class="w-full h-full object-cover">` : (fac.full_name || fac.name || 'FC').slice(0, 2).toUpperCase()}
                    </div>
                    <div>
                        <span class="badge-designation">${escapeHtml(fac.designation || 'Professor')}</span>
                        <h3 class="text-base font-bold text-[#171D3A] mt-1 mb-0">${escapeHtml(fac.full_name || fac.name)}</h3>
                        <p class="text-xs text-[#8B5CF6] font-mono mb-0">${escapeHtml(fac.faculty_id || fId)}</p>
                    </div>
                </div>
                <div class="grid grid-cols-2 gap-3 text-xs">
                    <div class="p-2.5 rounded-xl bg-[#F8F9FE] border border-[#E1E5F0]">
                        <span class="text-[#8C95AD] block text-[10px] uppercase font-semibold">DEPARTMENT</span>
                        <span class="text-[#171D3A] font-semibold">${escapeHtml(fac.department || '-')}</span>
                    </div>
                    <div class="p-2.5 rounded-xl bg-[#F8F9FE] border border-[#E1E5F0]">
                        <span class="text-[#8C95AD] block text-[10px] uppercase font-semibold">CABIN / OFFICE</span>
                        <span class="text-[#171D3A] font-semibold">${escapeHtml(fac.cabin || '-')}</span>
                    </div>
                    <div class="p-2.5 rounded-xl bg-[#F8F9FE] border border-[#E1E5F0]">
                        <span class="text-[#8C95AD] block text-[10px] uppercase font-semibold">PRIMARY SUBJECTS</span>
                        <span class="text-[#171D3A] font-semibold">${escapeHtml(fac.subject || '-')}</span>
                    </div>
                    <div class="p-2.5 rounded-xl bg-[#F8F9FE] border border-[#E1E5F0]">
                        <span class="text-[#8C95AD] block text-[10px] uppercase font-semibold">QUALIFICATION</span>
                        <span class="text-[#171D3A] font-semibold">${escapeHtml(fac.qualification || '-')}</span>
                    </div>
                </div>
            </div>
        `;

        facultyViewModal.show();
    };

    window.deleteFaculty = function(fId) {
        state.pendingDeleteId = fId;
        document.getElementById('deleteFacultyTargetId').innerText = fId;
        facultyDeleteModal.show();
    };

    async function handleConfirmDelete() {
        if (!state.pendingDeleteId) return;

        try {
            const res = await fetch(`/admin/api/crud/faculty/${state.pendingDeleteId}`, { method: 'DELETE' });
            const data = await res.json();
            if (res.ok && data.status === 'success') {
                showAdminToast(data.message, 'success');
                facultyDeleteModal.hide();
                loadFaculty();
            } else {
                showAdminToast(data.message || 'Failed to delete faculty record.', 'error');
            }
        } catch (err) {
            showAdminToast(err.message, 'error');
        }
    }
})();
