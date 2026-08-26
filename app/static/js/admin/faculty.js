/**
 * SVIT Admin - Page 6: Faculty Controller
 * Mobile-first architecture, department & designation filtering, image upload,
 * add/edit modal bottom-sheet, details modal, and deletion.
 */

(function() {
    'use strict';

    const state = {
        search: '',
        department: '',
        designation: '',
        viewMode: 'table', // 'table' or 'grid'
        page: 1,
        limit: 50,
        total: 0,
        items: [],
        pendingDeleteId: null,
        uploadedImageUrl: null
    };

    let facultyFormModal = null;
    let facultyViewModal = null;
    let facultyDeleteModal = null;
    let facultyMobileFilterModal = null;
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

    function getDesignationBadgeClass(desig) {
        const d = (desig || '').toLowerCase();
        if (d.includes('head')) return 'is-head';
        if (d.includes('associate')) return 'is-associate';
        if (d.includes('assistant')) return 'is-assistant';
        if (d.includes('lecturer')) return 'is-lecturer';
        if (d.includes('professor')) return 'is-professor';
        return 'is-assistant';
    }

    document.addEventListener('DOMContentLoaded', function() {
        const formEl = document.getElementById('facultyFormModal');
        const viewEl = document.getElementById('facultyViewModal');
        const delEl = document.getElementById('facultyDeleteModal');
        const filterEl = document.getElementById('facultyMobileFilterModal');

        if (formEl) facultyFormModal = new bootstrap.Modal(formEl);
        if (viewEl) facultyViewModal = new bootstrap.Modal(viewEl);
        if (delEl) facultyDeleteModal = new bootstrap.Modal(delEl);
        if (filterEl) facultyMobileFilterModal = new bootstrap.Modal(filterEl);

        bindEvents();
        setupImageUpload();
        loadFaculty();
    });

    function bindEvents() {
        // Search input with debounce and clear button
        const searchInput = document.getElementById('facultySearchInput');
        const clearSearchBtn = document.getElementById('clearFacultySearchBtn');

        if (searchInput) {
            searchInput.addEventListener('input', (e) => {
                const val = e.target.value;
                if (clearSearchBtn) {
                    clearSearchBtn.classList.toggle('hidden', val.length === 0);
                }
                clearTimeout(searchDebounce);
                searchDebounce = setTimeout(() => {
                    state.search = val.trim();
                    state.page = 1;
                    loadFaculty();
                }, 250);
            });
        }

        if (clearSearchBtn && searchInput) {
            clearSearchBtn.addEventListener('click', () => {
                searchInput.value = '';
                clearSearchBtn.classList.add('hidden');
                state.search = '';
                state.page = 1;
                loadFaculty();
            });
        }

        // Desktop Department Filter
        const deptFilter = document.getElementById('facultyDeptFilter');
        if (deptFilter) {
            deptFilter.addEventListener('change', (e) => {
                state.department = e.target.value;
                state.page = 1;
                syncFilterBadges();
                loadFaculty();
            });
        }

        // Desktop Designation Filter
        const desigFilter = document.getElementById('facultyDesigFilter');
        if (desigFilter) {
            desigFilter.addEventListener('change', (e) => {
                state.designation = e.target.value;
                state.page = 1;
                syncFilterBadges();
                loadFaculty();
            });
        }

        // Mobile Filter Bottom Sheet Trigger
        const openMobileFilterBtn = document.getElementById('openMobileFacultyFilterBtn');
        if (openMobileFilterBtn && facultyMobileFilterModal) {
            openMobileFilterBtn.addEventListener('click', () => {
                const mDept = document.getElementById('mobileFacultyDeptFilter');
                const mDesig = document.getElementById('mobileFacultyDesigFilter');
                if (mDept) mDept.value = state.department;
                if (mDesig) mDesig.value = state.designation;
                facultyMobileFilterModal.show();
            });
        }

        // Apply Mobile Filters
        const applyMobileFilterBtn = document.getElementById('applyMobileFacultyFilterBtn');
        if (applyMobileFilterBtn) {
            applyMobileFilterBtn.addEventListener('click', () => {
                const mDept = document.getElementById('mobileFacultyDeptFilter');
                const mDesig = document.getElementById('mobileFacultyDesigFilter');
                if (mDept) {
                    state.department = mDept.value;
                    if (deptFilter) deptFilter.value = mDept.value;
                }
                if (mDesig) {
                    state.designation = mDesig.value;
                    if (desigFilter) desigFilter.value = mDesig.value;
                }
                state.page = 1;
                syncFilterBadges();
                if (facultyMobileFilterModal) facultyMobileFilterModal.hide();
                loadFaculty();
            });
        }

        // Reset Mobile Filters
        const resetMobileFilterBtn = document.getElementById('resetMobileFacultyFilterBtn');
        if (resetMobileFilterBtn) {
            resetMobileFilterBtn.addEventListener('click', () => {
                const mDept = document.getElementById('mobileFacultyDeptFilter');
                const mDesig = document.getElementById('mobileFacultyDesigFilter');
                if (mDept) mDept.value = '';
                if (mDesig) mDesig.value = '';
                if (deptFilter) deptFilter.value = '';
                if (desigFilter) desigFilter.value = '';
                state.department = '';
                state.designation = '';
                state.page = 1;
                syncFilterBadges();
                if (facultyMobileFilterModal) facultyMobileFilterModal.hide();
                loadFaculty();
            });
        }

        // Refresh Button
        const refreshBtn = document.getElementById('refreshFacultyBtn');
        if (refreshBtn) refreshBtn.addEventListener('click', loadFaculty);

        // Page Limit Select
        const limitSelect = document.getElementById('pageLimitSelect');
        if (limitSelect) {
            limitSelect.addEventListener('change', (e) => {
                state.limit = parseInt(e.target.value, 10) || 50;
                state.page = 1;
                loadFaculty();
            });
        }

        // Pagination Buttons
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

        // Add Faculty Button
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

        // Form Submit
        const form = document.getElementById('facultyForm');
        if (form) form.addEventListener('submit', handleFacultyFormSubmit);

        // Confirm Delete Button
        const confirmDeleteBtn = document.getElementById('confirmDeleteFacultyBtn');
        if (confirmDeleteBtn) confirmDeleteBtn.addEventListener('click', handleConfirmDelete);

        // Edit button inside View Modal
        const editFromViewBtn = document.getElementById('editFromViewModalBtn');
        if (editFromViewBtn) {
            editFromViewBtn.addEventListener('click', () => {
                const curId = editFromViewBtn.dataset.facultyId;
                if (curId) {
                    if (facultyViewModal) facultyViewModal.hide();
                    setTimeout(() => window.editFaculty(curId), 200);
                }
            });
        }

        // View Mode Toggle (Desktop)
        const toggleTableBtn = document.getElementById('viewTableToggleBtn');
        const toggleGridBtn = document.getElementById('viewGridToggleBtn');

        if (toggleTableBtn && toggleGridBtn) {
            toggleTableBtn.addEventListener('click', () => {
                state.viewMode = 'table';
                toggleTableBtn.classList.add('bg-[#8B5CF6]', 'text-white');
                toggleTableBtn.classList.remove('text-[#66708F]');
                toggleGridBtn.classList.remove('bg-[#8B5CF6]', 'text-white');
                toggleGridBtn.classList.add('text-[#66708F]');
                document.getElementById('facultyTableView').classList.remove('hidden');
                document.getElementById('facultyGridView').classList.add('hidden');
                renderFaculty();
            });
            toggleGridBtn.addEventListener('click', () => {
                state.viewMode = 'grid';
                toggleGridBtn.classList.add('bg-[#8B5CF6]', 'text-white');
                toggleGridBtn.classList.remove('text-[#66708F]');
                toggleTableBtn.classList.remove('bg-[#8B5CF6]', 'text-white');
                toggleTableBtn.classList.add('text-[#66708F]');
                document.getElementById('facultyGridView').classList.remove('hidden');
                document.getElementById('facultyTableView').classList.add('hidden');
                renderFaculty();
            });
        }
    }

    function syncFilterBadges() {
        let activeCount = 0;
        if (state.department) activeCount++;
        if (state.designation) activeCount++;

        const badge = document.getElementById('mobileFacultyFilterActiveBadge');
        if (badge) {
            badge.innerText = activeCount;
            badge.classList.toggle('hidden', activeCount === 0);
        }
    }

    function setupImageUpload() {
        const dropZone = document.getElementById('facultyImageDropZone');
        const fileInput = document.getElementById('facultyImageInput');

        if (dropZone && fileInput) {
            dropZone.addEventListener('click', () => fileInput.click());
            dropZone.addEventListener('dragover', (e) => { e.preventDefault(); dropZone.classList.add('border-[#8B5CF6]'); });
            dropZone.addEventListener('dragleave', () => dropZone.classList.remove('border-[#8B5CF6]'));
            dropZone.addEventListener('drop', (e) => {
                e.preventDefault();
                dropZone.classList.remove('border-[#8B5CF6]');
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
            preview.innerHTML = '<span class="text-xs text-[#8B5CF6] font-semibold">Uploading photo...</span>';
            preview.classList.remove('hidden');
        }

        try {
            const res = await fetch('/admin/api/upload', { method: 'POST', body: formData });
            const data = await res.json();
            if (res.ok && data.status === 'success') {
                state.uploadedImageUrl = data.file.url;
                if (preview) {
                    preview.innerHTML = `
                        <img src="${data.file.url}" class="w-14 h-14 rounded-xl object-cover border border-[#8B5CF6] shadow-sm">
                        <span class="text-xs text-emerald-600 font-bold">Photo Attached</span>
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
        const mobileCards = document.getElementById('facultyMobileCards');

        if (tbody) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="8" class="text-center py-10 text-[#66708F] text-xs">
                        <div class="w-5 h-5 border-2 border-[#8B5CF6] border-t-transparent rounded-full animate-spin mx-auto mb-2"></div>
                        Loading faculty roster...
                    </td>
                </tr>
            `;
        }

        if (mobileCards) {
            mobileCards.innerHTML = `
                <div class="faculty-skeleton-card">
                    <div class="flex items-center gap-3">
                        <div class="w-11 h-11 rounded-xl skeleton-shimmer flex-shrink-0"></div>
                        <div class="flex-1 space-y-2">
                            <div class="h-3.5 w-32 skeleton-shimmer"></div>
                            <div class="h-2.5 w-20 skeleton-shimmer"></div>
                        </div>
                        <div class="h-5 w-20 rounded-md skeleton-shimmer"></div>
                    </div>
                    <div class="h-14 rounded-xl skeleton-shimmer"></div>
                    <div class="h-9 rounded-xl skeleton-shimmer"></div>
                </div>
                <div class="faculty-skeleton-card">
                    <div class="flex items-center gap-3">
                        <div class="w-11 h-11 rounded-xl skeleton-shimmer flex-shrink-0"></div>
                        <div class="flex-1 space-y-2">
                            <div class="h-3.5 w-32 skeleton-shimmer"></div>
                            <div class="h-2.5 w-20 skeleton-shimmer"></div>
                        </div>
                        <div class="h-5 w-20 rounded-md skeleton-shimmer"></div>
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
        if (state.department) params.append('filter_department', state.department);
        if (state.designation) params.append('filter_designation', state.designation);

        try {
            const res = await fetch(`/admin/api/crud/faculty?${params.toString()}`);
            const data = await res.json();
            if (res.ok && (data.status === 'success' || Array.isArray(data.items))) {
                state.items = Array.isArray(data.items)
                    ? data.items
                    : (Array.isArray(data?.data?.items) ? data.data.items : (Array.isArray(data?.data) ? data.data : []));
                state.total = typeof data.total === 'number'
                    ? data.total
                    : (typeof data?.data?.total === 'number' ? data.data.total : state.items.length);
                renderFaculty();
                renderPagination(data);
            } else {
                if (tbody) tbody.innerHTML = `<tr><td colspan="8" class="text-center py-6 text-red-500 text-xs">${escapeHtml(data.message || 'Error loading faculty')}</td></tr>`;
                if (mobileCards) mobileCards.innerHTML = `<div class="faculty-mobile-empty"><p class="text-red-500">${escapeHtml(data.message || 'Error loading faculty')}</p></div>`;
            }
        } catch (err) {
            console.error('Error loading faculty:', err);
            if (tbody) tbody.innerHTML = `<tr><td colspan="8" class="text-center py-6 text-red-500 text-xs">${escapeHtml(err.message || 'Connection error')}</td></tr>`;
            if (mobileCards) mobileCards.innerHTML = `<div class="faculty-mobile-empty"><p class="text-red-500">${escapeHtml(err.message || 'Connection error')}</p></div>`;
        }
        lucide.createIcons();
    }

    function renderPagination(data) {
        const start = state.total === 0 ? 0 : (state.page - 1) * state.limit + 1;
        const end = Math.min(state.page * state.limit, state.total);
        const totalPages = (data && data.pages) || Math.ceil(state.total / state.limit) || 1;

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
                btn.type = 'button';
                btn.className = `px-2.5 py-1 rounded-xl text-xs font-bold transition ${state.page === i ? 'bg-[#8B5CF6] text-white shadow-sm' : 'bg-white border border-[#E1E5F0] text-[#66708F] hover:text-[#171D3A]'}`;
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

        // Empty State Handler
        if (state.items.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="8" class="text-center py-12 text-[#66708F] text-xs">
                        <i data-lucide="user-check" class="w-8 h-8 mx-auto mb-2 text-[#8C95AD]"></i>
                        <p class="font-bold text-[#171D3A] mb-1">No faculty members found</p>
                        <p class="mb-0 text-[#66708F]">Try adjusting your search terms or active filters.</p>
                    </td>
                </tr>
            `;
            if (mobileCards) {
                mobileCards.innerHTML = `
                    <div class="faculty-mobile-empty">
                        <div class="faculty-mobile-empty-icon">
                            <i data-lucide="user-x" class="w-6 h-6"></i>
                        </div>
                        <h3>No faculty found</h3>
                        <p>No faculty records match the active filter or search criteria.</p>
                        ${(state.search || state.department || state.designation) ? `
                            <button type="button" class="btn-primary-custom text-xs" onclick="window.clearAllFacultyFilters()">
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
        tbody.innerHTML = state.items.map(f => {
            const name = f.full_name || f.name || 'Professor';
            const fId = f.faculty_id || f.id || '-';
            const desig = f.designation || 'Faculty';
            const dept = f.department || '-';
            const subject = f.subject || '-';
            const email = f.email || '-';
            const cabin = f.cabin || '-';
            const img = f.image_url;
            const badgeCls = getDesignationBadgeClass(desig);

            return `
                <tr>
                    <td>
                        <span class="font-mono text-[#8B5CF6] font-bold text-xs">${escapeHtml(fId)}</span>
                    </td>
                    <td>
                        <div class="flex items-center gap-2.5">
                            <div class="faculty-avatar">
                                ${img ? `<img src="${img}" alt="${escapeHtml(name)}">` : escapeHtml(name.slice(0, 2).toUpperCase())}
                            </div>
                            <div>
                                <p class="text-xs font-bold text-[#171D3A] mb-0">${escapeHtml(name)}</p>
                                <span class="text-[10px] text-[#66708F]">${escapeHtml(f.qualification || 'M.Tech / Ph.D')}</span>
                            </div>
                        </div>
                    </td>
                    <td class="text-[#171D3A] text-xs">${escapeHtml(dept)}</td>
                    <td><span class="badge-designation ${badgeCls}">${escapeHtml(desig)}</span></td>
                    <td class="text-[#171D3A] text-xs">${escapeHtml(subject)}</td>
                    <td class="text-[#66708F] text-xs">${escapeHtml(email)}</td>
                    <td class="text-[#66708F] text-xs font-mono">${escapeHtml(cabin)}</td>
                    <td class="text-end">
                        <div class="inline-flex items-center gap-1.5">
                            <button class="p-1.5 rounded-lg bg-white border border-[#E1E5F0] text-[#171D3A] hover:bg-[#E8EBFA]" onclick="window.viewFaculty('${escapeQuotes(fId)}')" title="View Details">
                                <i data-lucide="eye" class="w-3.5 h-3.5"></i>
                            </button>
                            <button class="p-1.5 rounded-lg bg-white border border-[#E1E5F0] text-[#171D3A] hover:bg-[#E8EBFA]" onclick="window.editFaculty('${escapeQuotes(fId)}')" title="Edit Faculty">
                                <i data-lucide="edit-2" class="w-3.5 h-3.5"></i>
                            </button>
                            <button class="p-1.5 rounded-lg bg-white border border-[#E1E5F0] text-red-600 hover:bg-red-50" onclick="window.deleteFaculty('${escapeQuotes(fId)}')" title="Delete">
                                <i data-lucide="trash-2" class="w-3.5 h-3.5"></i>
                            </button>
                        </div>
                    </td>
                </tr>
            `;
        }).join('');

        // 2. Render Purpose-Built Mobile Cards
        if (mobileCards) {
            mobileCards.innerHTML = state.items.map(f => {
                const name = f.full_name || f.name || 'Professor';
                const fId = f.faculty_id || f.id || '-';
                const desig = f.designation || 'Faculty';
                const dept = f.department || '-';
                const subject = f.subject || '-';
                const cabin = f.cabin || '-';
                const email = f.email || '-';
                const phone = f.phone || '-';
                const img = f.image_url;
                const badgeCls = getDesignationBadgeClass(desig);

                return `
                    <article class="faculty-mobile-card">
                        <!-- Top Header: Avatar + Name + ID + Designation -->
                        <div class="faculty-card-header">
                            <div class="faculty-card-identity">
                                <div class="faculty-avatar">
                                    ${img ? `<img src="${img}" alt="${escapeHtml(name)}">` : escapeHtml(name.slice(0, 2).toUpperCase())}
                                </div>
                                <div class="faculty-card-name-group">
                                    <h3 class="faculty-card-name">${escapeHtml(name)}</h3>
                                    <p class="faculty-card-id">${escapeHtml(fId)}</p>
                                </div>
                            </div>
                            <span class="badge-designation ${badgeCls}">${escapeHtml(desig)}</span>
                        </div>

                        <!-- Metadata Grid: Department, Subject, Cabin, Qualification -->
                        <div class="faculty-card-grid">
                            <div class="faculty-grid-item">
                                <span class="faculty-grid-label">Department</span>
                                <span class="faculty-grid-value">${escapeHtml(dept)}</span>
                            </div>
                            <div class="faculty-grid-item">
                                <span class="faculty-grid-label">Cabin Location</span>
                                <span class="faculty-grid-value">${escapeHtml(cabin)}</span>
                            </div>
                            <div class="faculty-grid-item" style="grid-column: span 2;">
                                <span class="faculty-grid-label">Primary Subject</span>
                                <span class="faculty-grid-value">${escapeHtml(subject)}</span>
                            </div>

                            <!-- Contact Pill Row -->
                            <div class="faculty-grid-contact">
                                <div class="faculty-contact-pill" title="${escapeHtml(email)}">
                                    <i data-lucide="mail" class="w-3.5 h-3.5 text-[#8B5CF6] flex-shrink-0"></i>
                                    <span>${escapeHtml(email)}</span>
                                </div>
                                ${phone !== '-' ? `
                                <div class="faculty-contact-pill" title="${escapeHtml(phone)}">
                                    <i data-lucide="phone" class="w-3.5 h-3.5 text-emerald-600 flex-shrink-0"></i>
                                    <span class="font-mono">${escapeHtml(phone)}</span>
                                </div>
                                ` : ''}
                            </div>
                        </div>

                        <!-- Action Buttons (Clean Balanced SaaS Layout, >= 44px touch targets) -->
                        <div class="faculty-card-actions">
                            <button type="button" class="faculty-action-btn is-primary" onclick="window.viewFaculty('${escapeQuotes(fId)}')" title="View Profile">
                                <i data-lucide="eye" class="w-4 h-4"></i>
                                <span>View Profile</span>
                            </button>
                            <button type="button" class="faculty-action-btn is-secondary" onclick="window.editFaculty('${escapeQuotes(fId)}')" title="Edit Faculty">
                                <i data-lucide="edit-2" class="w-4 h-4"></i>
                                <span>Edit</span>
                            </button>
                            <div class="dropdown faculty-more-dropdown">
                                <button type="button" class="faculty-action-btn is-icon-only is-more" data-bs-toggle="dropdown" aria-expanded="false" title="More options">
                                    <i data-lucide="more-vertical" class="w-4 h-4"></i>
                                </button>
                                <ul class="dropdown-menu dropdown-menu-end shadow-xl border border-[#E1E5F0] rounded-2xl p-1.5 text-xs">
                                    <li>
                                        <button type="button" class="dropdown-item rounded-xl flex items-center gap-2 py-2 px-3 text-[#171D3A] hover:bg-[#E8EBFA] font-medium" onclick="window.viewFaculty('${escapeQuotes(fId)}')">
                                            <i data-lucide="user-check" class="w-3.5 h-3.5 text-[#8B5CF6]"></i>
                                            <span>Full Profile</span>
                                        </button>
                                    </li>
                                    <li>
                                        <button type="button" class="dropdown-item rounded-xl flex items-center gap-2 py-2 px-3 text-[#171D3A] hover:bg-[#E8EBFA] font-medium" onclick="window.editFaculty('${escapeQuotes(fId)}')">
                                            <i data-lucide="edit-2" class="w-3.5 h-3.5 text-[#8B5CF6]"></i>
                                            <span>Edit Details</span>
                                        </button>
                                    </li>
                                    <li><hr class="dropdown-divider my-1 border-[#E1E5F0]"></li>
                                    <li>
                                        <button type="button" class="dropdown-item rounded-xl flex items-center gap-2 py-2 px-3 text-red-600 hover:bg-red-50 font-bold" onclick="window.deleteFaculty('${escapeQuotes(fId)}')">
                                            <i data-lucide="trash-2" class="w-3.5 h-3.5"></i>
                                            <span>Delete Faculty</span>
                                        </button>
                                    </li>
                                </ul>
                            </div>
                        </div>
                    </article>
                `;
            }).join('');
        }

        lucide.createIcons();
    }

    function renderGridView() {
        const grid = document.getElementById('facultyGridContainer');
        if (!grid) return;

        if (state.items.length === 0) {
            grid.innerHTML = `<div class="col-span-full text-center py-12 text-[#66708F] text-xs">No faculty records found.</div>`;
            return;
        }

        grid.innerHTML = state.items.map(f => {
            const name = f.full_name || f.name || 'Professor';
            const fId = f.faculty_id || f.id || '-';
            const desig = f.designation || 'Faculty';
            const dept = f.department || '-';
            const img = f.image_url;
            const badgeCls = getDesignationBadgeClass(desig);

            return `
                <div class="p-4 rounded-2xl bg-white border border-[#E1E5F0] shadow-sm flex flex-col justify-between space-y-3">
                    <div class="flex items-start gap-3">
                        <div class="faculty-avatar">
                            ${img ? `<img src="${img}" class="w-full h-full object-cover">` : escapeHtml(name.slice(0, 2).toUpperCase())}
                        </div>
                        <div class="min-w-0 flex-1">
                            <span class="badge-designation ${badgeCls} mb-1">${escapeHtml(desig)}</span>
                            <h4 class="text-sm font-bold text-[#171D3A] mb-0.5 truncate">${escapeHtml(name)}</h4>
                            <p class="text-[11px] text-[#66708F] mb-0 truncate">${escapeHtml(dept)}</p>
                        </div>
                    </div>
                    <div class="text-xs text-[#66708F] space-y-1.5 pt-2 border-t border-[#E1E5F0]">
                        <div class="flex justify-between"><span class="text-[#8C95AD]">ID:</span> <span class="font-mono text-[#8B5CF6] font-bold">${escapeHtml(fId)}</span></div>
                        <div class="flex justify-between"><span class="text-[#8C95AD]">Cabin:</span> <span class="text-[#171D3A] font-semibold">${escapeHtml(f.cabin || 'Main Dept')}</span></div>
                        <div class="flex justify-between truncate"><span class="text-[#8C95AD]">Email:</span> <span class="text-[#171D3A] truncate">${escapeHtml(f.email || '-')}</span></div>
                    </div>
                    <div class="pt-2 flex justify-end gap-1.5 border-t border-[#E1E5F0]">
                        <button type="button" class="px-3 py-1.5 rounded-xl bg-white border border-[#E1E5F0] text-[#171D3A] text-xs font-semibold hover:bg-[#E8EBFA]" onclick="window.viewFaculty('${escapeQuotes(fId)}')">Details</button>
                        <button type="button" class="btn-primary-custom px-3 py-1.5 text-xs font-bold" onclick="window.editFaculty('${escapeQuotes(fId)}')">Edit</button>
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
                showAdminToast(data.message || (isEdit ? 'Faculty updated.' : 'Faculty registered.'), 'success');
                if (facultyFormModal) facultyFormModal.hide();
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

        if (facultyFormModal) facultyFormModal.show();
    };

    window.viewFaculty = function(fId) {
        const fac = state.items.find(f => (f.faculty_id || f.id) === fId);
        if (!fac) return;

        const container = document.getElementById('facultyViewContent');
        if (!container) return;

        const editBtn = document.getElementById('editFromViewModalBtn');
        if (editBtn) editBtn.dataset.facultyId = fId;

        const badgeCls = getDesignationBadgeClass(fac.designation);

        container.innerHTML = `
            <div class="space-y-4 text-xs">
                <!-- Top Identity Card -->
                <div class="flex items-center gap-3.5 p-4 rounded-2xl bg-[#F8F9FE] border border-[#E1E5F0]">
                    <div class="w-16 h-16 rounded-2xl bg-gradient-to-tr from-[#8B5CF6] to-[#91A7EE] text-white font-bold text-xl flex items-center justify-center overflow-hidden flex-shrink-0 shadow-md shadow-[#8B5CF6]/20">
                        ${fac.image_url ? `<img src="${fac.image_url}" class="w-full h-full object-cover">` : escapeHtml((fac.full_name || fac.name || 'FC').slice(0, 2).toUpperCase())}
                    </div>
                    <div class="min-w-0">
                        <span class="badge-designation ${badgeCls} mb-1">${escapeHtml(fac.designation || 'Faculty')}</span>
                        <h3 class="text-base font-bold text-[#171D3A] mb-0.5 truncate">${escapeHtml(fac.full_name || fac.name)}</h3>
                        <p class="text-xs text-[#8B5CF6] font-mono font-bold mb-0">${escapeHtml(fac.faculty_id || fId)}</p>
                    </div>
                </div>

                <!-- 2-Column Info Grid -->
                <div class="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                    <div class="p-3 rounded-xl bg-[#F8F9FE] border border-[#E1E5F0]">
                        <span class="text-[#8C95AD] block text-[10px] uppercase font-bold tracking-wider mb-0.5">Department</span>
                        <span class="text-[#171D3A] font-bold text-xs">${escapeHtml(fac.department || '-')}</span>
                    </div>
                    <div class="p-3 rounded-xl bg-[#F8F9FE] border border-[#E1E5F0]">
                        <span class="text-[#8C95AD] block text-[10px] uppercase font-bold tracking-wider mb-0.5">Cabin Location</span>
                        <span class="text-[#171D3A] font-bold text-xs">${escapeHtml(fac.cabin || '-')}</span>
                    </div>
                    <div class="p-3 rounded-xl bg-[#F8F9FE] border border-[#E1E5F0]">
                        <span class="text-[#8C95AD] block text-[10px] uppercase font-bold tracking-wider mb-0.5">Primary Subject(s)</span>
                        <span class="text-[#171D3A] font-bold text-xs">${escapeHtml(fac.subject || '-')}</span>
                    </div>
                    <div class="p-3 rounded-xl bg-[#F8F9FE] border border-[#E1E5F0]">
                        <span class="text-[#8C95AD] block text-[10px] uppercase font-bold tracking-wider mb-0.5">Qualification</span>
                        <span class="text-[#171D3A] font-bold text-xs">${escapeHtml(fac.qualification || '-')}</span>
                    </div>
                    <div class="p-3 rounded-xl bg-[#F8F9FE] border border-[#E1E5F0]">
                        <span class="text-[#8C95AD] block text-[10px] uppercase font-bold tracking-wider mb-0.5">Email Address</span>
                        <span class="text-[#171D3A] font-semibold text-xs truncate block">${escapeHtml(fac.email || '-')}</span>
                    </div>
                    <div class="p-3 rounded-xl bg-[#F8F9FE] border border-[#E1E5F0]">
                        <span class="text-[#8C95AD] block text-[10px] uppercase font-bold tracking-wider mb-0.5">Contact Number</span>
                        <span class="text-[#171D3A] font-mono font-semibold text-xs">${escapeHtml(fac.phone || '-')}</span>
                    </div>
                </div>
            </div>
        `;

        if (facultyViewModal) facultyViewModal.show();
        lucide.createIcons();
    };

    window.deleteFaculty = function(fId) {
        state.pendingDeleteId = fId;
        const fac = state.items.find(f => (f.faculty_id || f.id) === fId);
        const nameEl = document.getElementById('deleteFacultyTargetName');
        const idEl = document.getElementById('deleteFacultyTargetId');
        if (nameEl) nameEl.innerText = fac ? (fac.full_name || fac.name) : 'Faculty Member';
        if (idEl) idEl.innerText = fId;
        if (facultyDeleteModal) facultyDeleteModal.show();
    };

    async function handleConfirmDelete() {
        if (!state.pendingDeleteId) return;

        try {
            const res = await fetch(`/admin/api/crud/faculty/${state.pendingDeleteId}`, { method: 'DELETE' });
            const data = await res.json();
            if (res.ok && data.status === 'success') {
                showAdminToast(data.message || 'Faculty record removed.', 'success');
                if (facultyDeleteModal) facultyDeleteModal.hide();
                loadFaculty();
            } else {
                showAdminToast(data.message || 'Failed to delete faculty record.', 'error');
            }
        } catch (err) {
            showAdminToast(err.message, 'error');
        }
    }

    window.clearAllFacultyFilters = function() {
        state.search = '';
        state.department = '';
        state.designation = '';
        state.page = 1;

        const sInput = document.getElementById('facultySearchInput');
        const cBtn = document.getElementById('clearFacultySearchBtn');
        const dF = document.getElementById('facultyDeptFilter');
        const desF = document.getElementById('facultyDesigFilter');
        const mD = document.getElementById('mobileFacultyDeptFilter');
        const mDes = document.getElementById('mobileFacultyDesigFilter');

        if (sInput) sInput.value = '';
        if (cBtn) cBtn.classList.add('hidden');
        if (dF) dF.value = '';
        if (desF) desF.value = '';
        if (mD) mD.value = '';
        if (mDes) mDes.value = '';

        syncFilterBadges();
        loadFaculty();
    };
})();
