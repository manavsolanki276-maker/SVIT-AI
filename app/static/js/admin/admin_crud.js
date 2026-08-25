/**
 * app/static/js/admin/admin_crud.js
 * Universal Client-side CRUD Controller for SVIT Admin Panel.
 * Handles AJAX List/Search/Filter/Sort/Pagination, Modals, Drag-and-drop Image/PDF Uploads,
 * In-browser PDF Preview, Delete Confirmations, and Toast notifications.
 */

(function() {
    'use strict';

    const state = {
        moduleKey: window.MODULE_KEY || '',
        config: window.MODULE_CONFIG || {},
        search: '',
        filters: {},
        sortBy: '',
        sortOrder: 1, // 1: Asc, -1: Desc
        page: 1,
        limit: 50,
        total: 0,
        items: [],
        pendingDeleteId: null,
        uploadedAsset: null
    };

    let searchDebounceTimeout = null;
    let crudModal = null;
    let detailsModal = null;
    let deleteModal = null;
    let pdfModal = null;

    // =========================================================================
    // 1. INITIALIZATION & DOM ATTACHMENT
    // =========================================================================
    document.addEventListener('DOMContentLoaded', function() {
        if (!state.moduleKey || !state.config) return;

        // Initialize Bootstrap Modals
        const crudModalEl = document.getElementById('crudFormModal');
        const detailsModalEl = document.getElementById('viewDetailsModal');
        const deleteModalEl = document.getElementById('deleteConfirmModal');
        const pdfModalEl = document.getElementById('pdfPreviewModal');

        if (crudModalEl) crudModal = new bootstrap.Modal(crudModalEl);
        if (detailsModalEl) detailsModal = new bootstrap.Modal(detailsModalEl);
        if (deleteModalEl) deleteModal = new bootstrap.Modal(deleteModalEl);
        if (pdfModalEl) pdfModal = new bootstrap.Modal(pdfModalEl);

        buildTableHeaders();
        buildFilterDropdowns();
        bindEventHandlers();
        loadModuleData();
    });

    // =========================================================================
    // 2. HEADER & FILTER BUILDERS
    // =========================================================================
    function buildTableHeaders() {
        const tr = document.getElementById('tableHeaderRow');
        if (!tr) return;

        tr.innerHTML = '';
        const fields = state.config.fields || [];

        // Check if there is an image field
        const hasImage = fields.some(f => f.type === 'image_upload');
        if (hasImage) {
            const th = document.createElement('th');
            th.innerText = 'PREVIEW';
            th.style.width = '60px';
            tr.appendChild(th);
        }

        // Table visible columns
        fields.forEach(f => {
            if (f.table) {
                const th = document.createElement('th');
                th.innerText = f.label.toUpperCase();
                th.className = 'cursor-pointer hover:text-white transition';
                th.onclick = () => handleColumnSort(f.key);
                tr.appendChild(th);
            }
        });

        // Actions Header
        const actTh = document.createElement('th');
        actTh.innerText = 'ACTIONS';
        actTh.className = 'text-end';
        actTh.style.width = '120px';
        tr.appendChild(actTh);
    }

    function buildFilterDropdowns() {
        const container = document.getElementById('dynamicFiltersContainer');
        if (!container) return;
        container.innerHTML = '';

        const filterKeys = state.config.filter_fields || [];
        const fields = state.config.fields || [];

        filterKeys.forEach(fk => {
            const fieldDef = fields.find(f => f.key === fk);
            if (!fieldDef) return;

            const select = document.createElement('select');
            select.className = 'bg-[#0F172A] border border-[#1F2937] text-gray-300 text-xs rounded-xl px-2.5 py-2 focus:outline-none focus:border-indigo-500';
            select.innerHTML = `<option value="">All ${fieldDef.label}</option>`;

            if (fieldDef.options && Array.isArray(fieldDef.options)) {
                fieldDef.options.forEach(opt => {
                    const optEl = document.createElement('option');
                    optEl.value = opt;
                    optEl.innerText = opt;
                    select.appendChild(optEl);
                });
            }

            select.onchange = (e) => {
                state.filters[fk] = e.target.value;
                state.page = 1;
                loadModuleData();
            };

            container.appendChild(select);
        });
    }

    function bindEventHandlers() {
        // Search Input with debouncing
        const searchInput = document.getElementById('searchInput');
        const clearBtn = document.getElementById('clearSearchBtn');

        if (searchInput) {
            searchInput.addEventListener('input', (e) => {
                const val = e.target.value;
                if (clearBtn) clearBtn.style.display = val ? 'block' : 'none';
                clearTimeout(searchDebounceTimeout);
                searchDebounceTimeout = setTimeout(() => {
                    state.search = val;
                    state.page = 1;
                    loadModuleData();
                }, 300);
            });
        }

        if (clearBtn) {
            clearBtn.addEventListener('click', () => {
                if (searchInput) searchInput.value = '';
                clearBtn.style.display = 'none';
                state.search = '';
                state.page = 1;
                loadModuleData();
            });
        }

        // Sort By Select
        const sortBySelect = document.getElementById('sortBySelect');
        if (sortBySelect) {
            sortBySelect.addEventListener('change', (e) => {
                state.sortBy = e.target.value;
                loadModuleData();
            });
        }

        // Sort Order Button
        const sortOrderBtn = document.getElementById('sortOrderBtn');
        if (sortOrderBtn) {
            sortOrderBtn.addEventListener('click', () => {
                state.sortOrder = state.sortOrder === 1 ? -1 : 1;
                sortOrderBtn.setAttribute('data-order', state.sortOrder);
                loadModuleData();
            });
        }

        // Page Limit Select
        const limitSelect = document.getElementById('pageLimitSelect');
        if (limitSelect) {
            limitSelect.addEventListener('change', (e) => {
                state.limit = parseInt(e.target.value, 10) || 20;
                state.page = 1;
                loadModuleData();
            });
        }

        // Pagination Buttons
        const prevBtn = document.getElementById('prevPageBtn');
        const nextBtn = document.getElementById('nextPageBtn');

        if (prevBtn) {
            prevBtn.addEventListener('click', () => {
                if (state.page > 1) {
                    state.page--;
                    loadModuleData();
                }
            });
        }

        if (nextBtn) {
            nextBtn.addEventListener('click', () => {
                const totalPages = Math.ceil(state.total / state.limit) || 1;
                if (state.page < totalPages) {
                    state.page++;
                    loadModuleData();
                }
            });
        }

        // Refresh Button
        const refreshBtn = document.getElementById('refreshTableBtn');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => loadModuleData());
        }

        // Open Create Modal Button
        const createBtn = document.getElementById('openCreateModalBtn');
        if (createBtn) {
            createBtn.addEventListener('click', () => openCreateModal());
        }

        // Form Submit
        const form = document.getElementById('crudForm');
        if (form) {
            form.addEventListener('submit', handleFormSubmit);
        }

        // Confirm Delete Button
        const confirmDeleteBtn = document.getElementById('confirmDeleteBtn');
        if (confirmDeleteBtn) {
            confirmDeleteBtn.addEventListener('click', executeDelete);
        }
    }

    function handleColumnSort(columnKey) {
        if (state.sortBy === columnKey) {
            state.sortOrder = state.sortOrder === 1 ? -1 : 1;
        } else {
            state.sortBy = columnKey;
            state.sortOrder = 1;
        }
        loadModuleData();
    }

    // =========================================================================
    // 3. DATA LOADING & TABLE RENDERING
    // =========================================================================
    async function loadModuleData() {
        const tbody = document.getElementById('tableBody');
        if (!tbody) return;

        // Render loading state
        tbody.innerHTML = `
            <tr>
                <td colspan="12" class="text-center py-12 text-gray-400 text-xs">
                    <div class="inline-flex items-center gap-3">
                        <div class="w-5 h-5 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin"></div>
                        <span>Loading records...</span>
                    </div>
                </td>
            </tr>
        `;

        // Build query params
        const params = new URLSearchParams({
            search: state.search,
            sort_by: state.sortBy,
            sort_order: state.sortOrder,
            page: state.page,
            limit: state.limit
        });

        for (const [k, v] of Object.entries(state.filters)) {
            if (v) params.append(`filter_${k}`, v);
        }

        try {
            const res = await fetch(`/admin/api/crud/${state.moduleKey}?${params.toString()}`, {
                headers: { 'Accept': 'application/json' }
            });

            if (res.status === 403) {
                tbody.innerHTML = `
                    <tr>
                        <td colspan="12" class="text-center py-10 text-red-400 text-xs">
                            <i data-lucide="shield-alert" class="w-6 h-6 mx-auto mb-2 text-red-500"></i>
                            <strong>403 Forbidden:</strong> You do not have permission to view this module.
                        </td>
                    </tr>
                `;
                lucide.createIcons();
                return;
            }

            const data = await res.json();
            if (data.status === 'success') {
                state.items = data.items || [];
                state.total = data.total || 0;
                renderTableRows(state.items);
                renderPagination(data);
            } else {
                tbody.innerHTML = `
                    <tr>
                        <td colspan="12" class="text-center py-8 text-amber-400 text-xs">
                            ${data.message || 'Error loading records.'}
                        </td>
                    </tr>
                `;
            }
        } catch (err) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="12" class="text-center py-8 text-red-400 text-xs">
                        Failed to connect to server: ${err.message}
                    </td>
                </tr>
            `;
        }
        lucide.createIcons();
    }

    function renderTableRows(items) {
        const tbody = document.getElementById('tableBody');
        const countBadge = document.getElementById('totalItemsBadge');
        if (countBadge) countBadge.innerText = `${state.total} Records`;

        if (!items || items.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="12" class="text-center py-12 text-gray-400">
                        <div class="max-w-xs mx-auto space-y-2">
                            <div class="w-10 h-10 rounded-full bg-gray-800 text-gray-500 flex items-center justify-center mx-auto">
                                <i data-lucide="inbox" class="w-5 h-5"></i>
                            </div>
                            <p class="text-xs font-semibold text-white mb-0">No records found</p>
                            <p class="text-[11px] text-gray-500 mb-2">There are no records matching your current filter criteria.</p>
                            <button onclick="document.getElementById('openCreateModalBtn').click()" class="px-3 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold">
                                + Add First Record
                            </button>
                        </div>
                    </td>
                </tr>
            `;
            lucide.createIcons();
            return;
        }

        const fields = state.config.fields || [];
        const hasImage = fields.some(f => f.type === 'image_upload');
        const idField = state.config.id_field || 'id';

        tbody.innerHTML = items.map(item => {
            const itemId = item[idField] || item.id;
            let imageCell = '';

            if (hasImage) {
                const imgUrl = item.image_url || item.company_logo || item.cover_image || item.poster_url || '';
                if (imgUrl) {
                    imageCell = `
                        <td>
                            <img src="${imgUrl}" alt="Thumbnail" class="w-9 h-9 rounded-lg object-cover border border-[#1F2937] hover:scale-125 transition cursor-pointer" onclick="window.open('${imgUrl}', '_blank')">
                        </td>
                    `;
                } else {
                    imageCell = `
                        <td>
                            <div class="w-9 h-9 rounded-lg bg-gray-800/80 border border-gray-700/50 flex items-center justify-center text-gray-500">
                                <i data-lucide="image" class="w-4 h-4"></i>
                            </div>
                        </td>
                    `;
                }
            }

            const dataCells = fields.filter(f => f.table).map(f => {
                const rawVal = item[f.key];
                let formatted = rawVal !== undefined && rawVal !== null ? rawVal : '-';

                // Boolean Checkbox formatting
                if (f.type === 'checkbox') {
                    formatted = rawVal ? 
                        `<span class="px-2 py-0.5 rounded text-[10px] font-semibold badge-success">Yes</span>` : 
                        `<span class="px-2 py-0.5 rounded text-[10px] text-gray-400">No</span>`;
                }
                // Status / Priority / RAG status badge formatting
                else if (f.key === 'is_urgent' && rawVal) {
                    formatted = `<span class="px-2 py-0.5 rounded text-[10px] font-bold bg-red-600 text-white animate-pulse">URGENT</span>`;
                }
                else if (f.key === 'priority') {
                    if (rawVal === 'Emergency') formatted = `<span class="px-2 py-0.5 rounded text-[10px] font-bold bg-red-600 text-white animate-pulse">Emergency</span>`;
                    else if (rawVal === 'High' || rawVal === 'High Priority') formatted = `<span class="px-2 py-0.5 rounded text-[10px] font-bold badge-high">High</span>`;
                    else formatted = `<span class="px-2 py-0.5 rounded text-[10px] badge-info">${rawVal}</span>`;
                }
                else if (f.key === 'rag_status') {
                    if (rawVal === 'INDEXED') {
                        formatted = `<span class="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 flex items-center gap-1 w-fit"><span class="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>INDEXED</span>`;
                    } else if (rawVal === 'PROCESSING') {
                        formatted = `<span class="px-2 py-0.5 rounded text-[10px] font-bold bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 animate-pulse flex items-center gap-1 w-fit"><span class="w-1.5 h-1.5 rounded-full bg-indigo-400"></span>PROCESSING</span>`;
                    } else if (rawVal === 'FAILED') {
                        formatted = `<span class="px-2 py-0.5 rounded text-[10px] font-bold bg-red-500/20 text-red-300 border border-red-500/30 flex items-center gap-1 w-fit" title="${item.error_message || 'Indexing failed'}"><span class="w-1.5 h-1.5 rounded-full bg-red-400"></span>FAILED</span>`;
                    } else {
                        formatted = `<span class="px-2 py-0.5 rounded text-[10px] text-gray-400 bg-gray-800">${rawVal || '-'}</span>`;
                    }
                }
                else if (f.key === 'status') {
                    if (rawVal === 'Active' || rawVal === 'Published' || rawVal === 'Available') {
                        formatted = `<span class="px-2 py-0.5 rounded text-[10px] font-semibold badge-success">${rawVal}</span>`;
                    } else if (rawVal === 'Upcoming' || rawVal === 'Registration Open') {
                        formatted = `<span class="px-2 py-0.5 rounded text-[10px] font-semibold badge-info">${rawVal}</span>`;
                    } else {
                        formatted = `<span class="px-2 py-0.5 rounded text-[10px] text-gray-400 bg-gray-800">${rawVal}</span>`;
                    }
                }

                return `<td>${formatted}</td>`;
            }).join('');

            // Check if module is document RAG enabled
            const isDocModule = state.moduleKey.includes('document') || Boolean(item.file_url);
            const reindexBtn = isDocModule ? `
                <button class="p-1.5 rounded-lg bg-[#0F172A] border border-[#1F2937] text-teal-400 hover:text-white hover:bg-teal-600 transition btn-reindex-item" data-id="${itemId}" title="Re-index Document into RAG">
                    <i data-lucide="refresh-cw" class="w-3.5 h-3.5"></i>
                </button>
            ` : '';

            // Action Buttons
            const actionCell = `
                <td class="text-end">
                    <div class="inline-flex items-center gap-1.5">
                        <button class="p-1.5 rounded-lg bg-[#0F172A] border border-[#1F2937] text-gray-400 hover:text-white hover:border-gray-500 transition btn-view-item" data-id="${itemId}" title="View Details">
                            <i data-lucide="eye" class="w-3.5 h-3.5"></i>
                        </button>
                        ${reindexBtn}
                        <button class="p-1.5 rounded-lg bg-[#0F172A] border border-[#1F2937] text-indigo-400 hover:text-white hover:bg-indigo-600 transition btn-edit-item" data-id="${itemId}" title="Edit / Replace Record">
                            <i data-lucide="edit-3" class="w-3.5 h-3.5"></i>
                        </button>
                        <button class="p-1.5 rounded-lg bg-[#0F172A] border border-[#1F2937] text-red-400 hover:text-white hover:bg-red-600 transition btn-delete-item" data-id="${itemId}" title="Delete Record">
                            <i data-lucide="trash-2" class="w-3.5 h-3.5"></i>
                        </button>
                    </div>
                </td>
            `;

            return `<tr>${imageCell}${dataCells}${actionCell}</tr>`;
        }).join('');

        // Attach action click handlers
        tbody.querySelectorAll('.btn-view-item').forEach(b => {
            b.onclick = () => openViewModal(b.getAttribute('data-id'));
        });
        tbody.querySelectorAll('.btn-reindex-item').forEach(b => {
            b.onclick = () => triggerReindex(b.getAttribute('data-id'));
        });
        tbody.querySelectorAll('.btn-edit-item').forEach(b => {
            b.onclick = () => openEditModal(b.getAttribute('data-id'));
        });
        tbody.querySelectorAll('.btn-delete-item').forEach(b => {
            b.onclick = () => openDeleteModal(b.getAttribute('data-id'));
        });
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
                    loadModuleData();
                };
                numbersContainer.appendChild(btn);
            }
        }
    }

    // =========================================================================
    // 4. CREATE & EDIT MODAL HANDLERS
    // =========================================================================
    function openCreateModal() {
        const titleEl = document.getElementById('formModalTitle');
        const form = document.getElementById('crudForm');
        const idInput = document.getElementById('formRecordId');

        if (titleEl) titleEl.innerText = `Add New ${state.config.title.slice(0, -1) || 'Record'}`;
        if (idInput) idInput.value = '';
        if (form) form.reset();
        state.uploadedAsset = null;

        renderFormFields({});
        if (crudModal) crudModal.show();
        lucide.createIcons();
    }

    async function openEditModal(itemId) {
        const item = state.items.find(i => (i[state.config.id_field] || i.id) === itemId);
        if (!item) return;

        const titleEl = document.getElementById('formModalTitle');
        const idInput = document.getElementById('formRecordId');

        if (titleEl) titleEl.innerText = `Edit ${state.config.title.slice(0, -1) || 'Record'}`;
        if (idInput) idInput.value = itemId;

        renderFormFields(item);
        if (crudModal) crudModal.show();
        lucide.createIcons();
    }

    function renderFormFields(itemData) {
        const container = document.getElementById('formFieldsContainer');
        if (!container) return;
        container.innerHTML = '';

        const fields = state.config.fields || [];

        fields.forEach(f => {
            const isFullWidth = (f.type === 'textarea' || f.type === 'image_upload' || f.type === 'pdf_upload');
            const colClass = isFullWidth ? 'col-span-1 md:col-span-2' : 'col-span-1';
            const val = itemData[f.key] !== undefined ? itemData[f.key] : '';

            const wrapper = document.createElement('div');
            wrapper.className = `${colClass} space-y-1`;

            let inputHtml = '';

            // 1. Text / Email / Date / Time / Number
            if (['text', 'email', 'number', 'date', 'time'].includes(f.type)) {
                inputHtml = `
                    <label class="text-[11px] font-semibold text-gray-300">${f.label} ${f.required ? '<span class="text-red-400">*</span>' : ''}</label>
                    <input type="${f.type}" name="${f.key}" value="${val}" class="w-full bg-[#0F172A] border border-[#1F2937] rounded-xl px-3 py-2 text-xs text-white placeholder-gray-500 focus:outline-none focus:border-indigo-500" ${f.required ? 'required' : ''}>
                `;
            }
            // 2. Select Dropdown
            else if (f.type === 'select') {
                const options = (f.options || []).map(opt => `
                    <option value="${opt}" ${val === opt ? 'selected' : ''}>${opt}</option>
                `).join('');
                inputHtml = `
                    <label class="text-[11px] font-semibold text-gray-300">${f.label} ${f.required ? '<span class="text-red-400">*</span>' : ''}</label>
                    <select name="${f.key}" class="w-full bg-[#0F172A] border border-[#1F2937] rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-indigo-500" ${f.required ? 'required' : ''}>
                        <option value="">Select ${f.label}...</option>
                        ${options}
                    </select>
                `;
            }
            // 3. Textarea
            else if (f.type === 'textarea') {
                inputHtml = `
                    <label class="text-[11px] font-semibold text-gray-300">${f.label} ${f.required ? '<span class="text-red-400">*</span>' : ''}</label>
                    <textarea name="${f.key}" rows="3" class="w-full bg-[#0F172A] border border-[#1F2937] rounded-xl px-3 py-2 text-xs text-white placeholder-gray-500 focus:outline-none focus:border-indigo-500" ${f.required ? 'required' : ''}>${val}</textarea>
                `;
            }
            // 4. Checkbox
            else if (f.type === 'checkbox') {
                inputHtml = `
                    <div class="flex items-center gap-2 pt-4">
                        <input type="checkbox" name="${f.key}" id="field_${f.key}" ${val ? 'checked' : ''} class="w-4 h-4 rounded bg-[#0F172A] border-[#1F2937] text-indigo-600 focus:ring-0">
                        <label for="field_${f.key}" class="text-xs font-semibold text-gray-300 cursor-pointer">${f.label}</label>
                    </div>
                `;
            }
            // 5. Image Upload Widget
            else if (f.type === 'image_upload') {
                inputHtml = `
                    <label class="text-[11px] font-semibold text-gray-300">${f.label}</label>
                    <div class="drag-drop-zone" id="imageDropzone_${f.key}">
                        <input type="file" id="fileInput_${f.key}" accept="image/jpeg,image/png,image/webp,image/jpg" class="hidden">
                        <input type="hidden" name="${f.key}" id="hidden_${f.key}" value="${val}">
                        <div id="imagePreviewContainer_${f.key}" class="${val ? '' : 'hidden'} flex items-center justify-between p-2 rounded-xl bg-[#090D16] border border-[#1F2937]">
                            <div class="flex items-center gap-3">
                                <img id="previewImg_${f.key}" src="${val}" alt="Preview" class="w-12 h-12 rounded-lg object-cover border border-gray-700">
                                <div>
                                    <p class="text-xs font-semibold text-white mb-0">Image attached</p>
                                    <span class="text-[10px] text-emerald-400 font-medium">Ready</span>
                                </div>
                            </div>
                            <div class="flex items-center gap-2">
                                <button type="button" class="px-2.5 py-1 rounded-lg bg-indigo-600/30 text-indigo-300 text-xs font-semibold hover:bg-indigo-600 hover:text-white" onclick="document.getElementById('fileInput_${f.key}').click()">Replace</button>
                                <button type="button" class="px-2.5 py-1 rounded-lg bg-red-600/30 text-red-300 text-xs font-semibold hover:bg-red-600 hover:text-white" onclick="removeUploadedFile('${f.key}', 'image')">Remove</button>
                            </div>
                        </div>
                        <div id="imageUploadPrompt_${f.key}" class="${val ? 'hidden' : ''} space-y-1">
                            <i data-lucide="upload-cloud" class="w-8 h-8 text-indigo-400 mx-auto"></i>
                            <p class="text-xs font-semibold text-white mb-0">Drag & drop image here or <span class="text-indigo-400 underline">browse</span></p>
                            <p class="text-[10px] text-gray-500 mb-0">Supported formats: JPG, PNG, WEBP (Max 5 MB)</p>
                        </div>
                    </div>
                `;
            }
            // 6. PDF Document Upload Widget
            else if (f.type === 'pdf_upload') {
                const docUrl = itemData.file_url || val || '';
                const docName = itemData.file_name || 'Document.pdf';
                const docSize = itemData.file_size_formatted || '';

                inputHtml = `
                    <label class="text-[11px] font-semibold text-gray-300">${f.label} ${f.required ? '<span class="text-red-400">*</span>' : ''}</label>
                    <div class="drag-drop-zone" id="docDropzone_${f.key}">
                        <input type="file" id="docFileInput_${f.key}" accept="application/pdf,.docx" class="hidden">
                        <input type="hidden" name="file_url" id="hidden_file_url" value="${docUrl}">
                        <input type="hidden" name="file_name" id="hidden_file_name" value="${docName}">
                        <input type="hidden" name="file_size_formatted" id="hidden_file_size" value="${docSize}">

                        <div id="docPreviewContainer_${f.key}" class="${docUrl ? '' : 'hidden'} flex items-center justify-between p-3 rounded-xl bg-[#090D16] border border-[#1F2937]">
                            <div class="flex items-center gap-3">
                                <div class="w-10 h-10 rounded-lg bg-red-500/20 text-red-400 flex items-center justify-center">
                                    <i data-lucide="file-text" class="w-5 h-5"></i>
                                </div>
                                <div class="text-left">
                                    <p id="previewDocName_${f.key}" class="text-xs font-semibold text-white mb-0 truncate max-w-xs">${docName}</p>
                                    <span id="previewDocSize_${f.key}" class="text-[10px] text-gray-400">${docSize || 'PDF Document'}</span>
                                </div>
                            </div>
                            <div class="flex items-center gap-2">
                                <button type="button" class="px-2.5 py-1 rounded-lg bg-indigo-600/30 text-indigo-300 text-xs font-semibold hover:bg-indigo-600 hover:text-white" onclick="document.getElementById('docFileInput_${f.key}').click()">Replace</button>
                                <button type="button" class="px-2.5 py-1 rounded-lg bg-red-600/30 text-red-300 text-xs font-semibold hover:bg-red-600 hover:text-white" onclick="removeUploadedFile('${f.key}', 'document')">Remove</button>
                            </div>
                        </div>

                        <div id="docUploadPrompt_${f.key}" class="${docUrl ? 'hidden' : ''} space-y-1">
                            <i data-lucide="file-up" class="w-8 h-8 text-indigo-400 mx-auto"></i>
                            <p class="text-xs font-semibold text-white mb-0">Drag & drop PDF document or <span class="text-indigo-400 underline">browse</span></p>
                            <p class="text-[10px] text-gray-500 mb-0">Supported formats: PDF, DOCX (Max 15 MB)</p>
                        </div>
                    </div>
                `;
            }

            wrapper.innerHTML = inputHtml;
            container.appendChild(wrapper);

            // Bind Dropzone Event Listeners for Images & Documents
            if (f.type === 'image_upload') {
                bindDropzoneListeners(`imageDropzone_${f.key}`, `fileInput_${f.key}`, f.key, 'image');
            } else if (f.type === 'pdf_upload') {
                bindDropzoneListeners(`docDropzone_${f.key}`, `docFileInput_${f.key}`, f.key, 'document');
            }
        });
    }

    function bindDropzoneListeners(dropzoneId, fileInputId, fieldKey, category) {
        setTimeout(() => {
            const dropzone = document.getElementById(dropzoneId);
            const fileInput = document.getElementById(fileInputId);
            if (!dropzone || !fileInput) return;

            dropzone.onclick = (e) => {
                if (e.target.tagName !== 'BUTTON') fileInput.click();
            };

            dropzone.ondragover = (e) => {
                e.preventDefault();
                dropzone.classList.add('dragover');
            };

            dropzone.ondragleave = () => dropzone.classList.remove('dragover');

            dropzone.ondrop = (e) => {
                e.preventDefault();
                dropzone.classList.remove('dragover');
                if (e.dataTransfer.files && e.dataTransfer.files[0]) {
                    uploadFileViaAjax(e.dataTransfer.files[0], fieldKey, category);
                }
            };

            fileInput.onchange = (e) => {
                if (e.target.files && e.target.files[0]) {
                    uploadFileViaAjax(e.target.files[0], fieldKey, category);
                }
            };
        }, 50);
    }

    async function uploadFileViaAjax(fileObj, fieldKey, category) {
        const formData = new FormData();
        formData.append('file', fileObj);
        formData.append('category', category);

        try {
            showAdminToast(`Uploading ${fileObj.name}...`, 'info');
            const res = await fetch('/admin/api/upload', {
                method: 'POST',
                body: formData
            });

            const data = await res.json();
            if (data.status === 'success' && data.file) {
                showAdminToast('File uploaded successfully!', 'success');
                const fileInfo = data.file;

                if (category === 'image') {
                    const hidden = document.getElementById(`hidden_${fieldKey}`);
                    const previewImg = document.getElementById(`previewImg_${fieldKey}`);
                    const previewCont = document.getElementById(`imagePreviewContainer_${fieldKey}`);
                    const prompt = document.getElementById(`imageUploadPrompt_${fieldKey}`);

                    if (hidden) hidden.value = fileInfo.url;
                    if (previewImg) previewImg.src = fileInfo.url;
                    if (previewCont) previewCont.classList.remove('hidden');
                    if (prompt) prompt.classList.add('hidden');
                } else {
                    const hiddenUrl = document.getElementById('hidden_file_url');
                    const hiddenName = document.getElementById('hidden_file_name');
                    const hiddenSize = document.getElementById('hidden_file_size');
                    const previewName = document.getElementById(`previewDocName_${fieldKey}`);
                    const previewSize = document.getElementById(`previewDocSize_${fieldKey}`);
                    const previewCont = document.getElementById(`docPreviewContainer_${fieldKey}`);
                    const prompt = document.getElementById(`docUploadPrompt_${fieldKey}`);

                    if (hiddenUrl) hiddenUrl.value = fileInfo.url;
                    if (hiddenName) hiddenName.value = fileInfo.original_name;
                    if (hiddenSize) hiddenSize.value = fileInfo.file_size_formatted;
                    if (previewName) previewName.innerText = fileInfo.original_name;
                    if (previewSize) previewSize.innerText = fileInfo.file_size_formatted;
                    if (previewCont) previewCont.classList.remove('hidden');
                    if (prompt) prompt.classList.add('hidden');
                }
            } else {
                showAdminToast(data.message || 'File upload failed.', 'error');
            }
        } catch (err) {
            showAdminToast(`Upload error: ${err.message}`, 'error');
        }
        lucide.createIcons();
    }

    window.removeUploadedFile = function(fieldKey, category) {
        if (category === 'image') {
            const hidden = document.getElementById(`hidden_${fieldKey}`);
            const previewCont = document.getElementById(`imagePreviewContainer_${fieldKey}`);
            const prompt = document.getElementById(`imageUploadPrompt_${fieldKey}`);
            if (hidden) hidden.value = '';
            if (previewCont) previewCont.classList.add('hidden');
            if (prompt) prompt.classList.remove('hidden');
        } else {
            const hiddenUrl = document.getElementById('hidden_file_url');
            const hiddenName = document.getElementById('hidden_file_name');
            const hiddenSize = document.getElementById('hidden_file_size');
            const previewCont = document.getElementById(`docPreviewContainer_${fieldKey}`);
            const prompt = document.getElementById(`docUploadPrompt_${fieldKey}`);
            if (hiddenUrl) hiddenUrl.value = '';
            if (hiddenName) hiddenName.value = '';
            if (hiddenSize) hiddenSize.value = '';
            if (previewCont) previewCont.classList.add('hidden');
            if (prompt) prompt.classList.remove('hidden');
        }
    };

    async function handleFormSubmit(e) {
        e.preventDefault();
        const form = e.target;
        const recordId = document.getElementById('formRecordId').value;
        const isEdit = Boolean(recordId);

        const formData = new FormData(form);
        const payload = {};
        formData.forEach((val, key) => {
            if (key !== 'record_id') {
                payload[key] = val;
            }
        });

        // Set checkboxes
        const checkboxes = form.querySelectorAll('input[type="checkbox"]');
        checkboxes.forEach(cb => {
            payload[cb.name] = cb.checked;
        });

        const spinner = document.getElementById('saveBtnSpinner');
        const btnText = document.getElementById('saveBtnText');
        const saveBtn = document.getElementById('saveRecordBtn');

        if (spinner) spinner.classList.remove('hidden');
        if (btnText) btnText.innerText = isEdit ? 'Updating...' : 'Saving...';
        if (saveBtn) saveBtn.disabled = true;

        try {
            const endpoint = isEdit ? 
                `/admin/api/crud/${state.moduleKey}/${recordId}` : 
                `/admin/api/crud/${state.moduleKey}`;
            
            const method = isEdit ? 'PUT' : 'POST';

            const res = await fetch(endpoint, {
                method: method,
                headers: {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json'
                },
                body: JSON.stringify(payload)
            });

            const data = await res.json();
            if (res.ok && data.status === 'success') {
                showAdminToast(data.message || 'Record saved successfully!', 'success');
                if (crudModal) crudModal.hide();
                loadModuleData();
            } else {
                showAdminToast(data.message || 'Error saving record.', 'error');
            }
        } catch (err) {
            showAdminToast(`Network error: ${err.message}`, 'error');
        } finally {
            if (spinner) spinner.classList.add('hidden');
            if (btnText) btnText.innerText = 'Save Record';
            if (saveBtn) saveBtn.disabled = false;
        }
    }

    // =========================================================================
    // 5. VIEW DETAILS & PDF PREVIEW
    // =========================================================================
    function openViewModal(itemId) {
        const item = state.items.find(i => (i[state.config.id_field] || i.id) === itemId);
        if (!item) return;

        const titleEl = document.getElementById('detailsModalTitle');
        const contentEl = document.getElementById('detailsModalContent');

        if (titleEl) titleEl.innerText = `${state.config.title} Details: ${itemId}`;
        if (!contentEl) return;

        contentEl.innerHTML = '';
        const fields = state.config.fields || [];

        // Show prominent RAG failure alert if status is FAILED
        if (item.rag_status === 'FAILED') {
            const errBox = document.createElement('div');
            errBox.className = 'col-span-1 md:col-span-2 p-3.5 rounded-xl bg-red-950/50 border border-red-800/80 text-red-200';
            errBox.innerHTML = `
                <div class="flex items-center justify-between gap-3 flex-wrap">
                    <div>
                        <span class="text-xs font-bold text-red-300 flex items-center gap-1.5">
                            <i data-lucide="alert-triangle" class="w-4 h-4 text-red-400"></i> RAG Processing Failed
                        </span>
                        <p class="text-[11px] text-gray-300 mb-0 mt-1">Reason: ${item.error_message || 'Unable to extract text or index document into RAG.'}</p>
                    </div>
                    <button type="button" class="px-3 py-1.5 rounded-lg bg-red-600 hover:bg-red-500 text-white font-semibold text-xs transition" onclick="triggerReindex('${itemId}')">
                        <i data-lucide="refresh-cw" class="w-3 h-3 d-inline"></i> Retry
                    </button>
                </div>
            `;
            contentEl.appendChild(errBox);
        }

        fields.forEach(f => {
            const val = item[f.key];
            if (val === undefined || val === null || val === '') return;

            const box = document.createElement('div');
            box.className = (f.type === 'textarea' || f.type === 'image_upload' || f.type === 'pdf_upload') ? 
                            'col-span-1 md:col-span-2 p-2.5 rounded-xl bg-[#090D16] border border-[#1F2937]' : 
                            'p-2.5 rounded-xl bg-[#090D16] border border-[#1F2937]';

            if (f.type === 'image_upload' && val) {
                box.innerHTML = `
                    <span class="text-[10px] text-gray-400 uppercase font-bold block mb-1.5">${f.label}</span>
                    <img src="${val}" alt="Image" class="max-h-48 rounded-xl border border-gray-700 object-cover cursor-pointer" onclick="window.open('${val}', '_blank')">
                `;
            } else if (f.type === 'pdf_upload' || f.key === 'file_url') {
                const docName = item.file_name || 'Academic Document';
                box.innerHTML = `
                    <span class="text-[10px] text-gray-400 uppercase font-bold block mb-1.5">${f.label}</span>
                    <div class="flex items-center justify-between flex-wrap gap-2">
                        <div class="flex items-center gap-2">
                            <i data-lucide="file-text" class="w-5 h-5 text-indigo-400"></i>
                            <span class="font-semibold text-white">${docName} (${item.file_size_formatted || 'PDF'})</span>
                        </div>
                        <div class="flex items-center gap-2">
                            <button type="button" class="px-3 py-1.5 rounded-lg bg-indigo-600 text-white text-xs font-semibold" onclick="openPdfPreviewModal('${val}', '${docName}')">
                                <i data-lucide="eye" class="w-3.5 h-3.5 d-inline"></i> In-Browser Preview
                            </button>
                            <a href="${val}" download class="px-3 py-1.5 rounded-lg bg-gray-700 text-white text-xs font-semibold text-decoration-none">
                                <i data-lucide="download" class="w-3.5 h-3.5 d-inline"></i> Download
                            </a>
                        </div>
                    </div>
                `;
            } else {
                box.innerHTML = `
                    <span class="text-[10px] text-gray-400 uppercase font-bold block">${f.label}</span>
                    <span class="text-white font-medium break-words">${val}</span>
                `;
            }

            contentEl.appendChild(box);
        });

        // Set Audit Fields
        const cBy = document.getElementById('auditCreatedBy');
        const cAt = document.getElementById('auditCreatedAt');
        const uBy = document.getElementById('auditUpdatedBy');
        const uAt = document.getElementById('auditUpdatedAt');

        if (cBy) cBy.innerHTML = `Created by: <span class="text-white font-semibold">${item.created_by || 'admin'}</span>`;
        if (cAt) cAt.innerHTML = `Created at: <span class="text-white font-semibold">${item.created_at ? item.created_at.slice(0, 10) : '-'}</span>`;
        if (uBy) uBy.innerHTML = `Updated by: <span class="text-white font-semibold">${item.updated_by || '-'}</span>`;
        if (uAt) uAt.innerHTML = `Updated at: <span class="text-white font-semibold">${item.updated_at ? item.updated_at.slice(0, 10) : '-'}</span>`;

        if (detailsModal) detailsModal.show();
        lucide.createIcons();
    }

    window.openPdfPreviewModal = function(url, title = 'Document Preview') {
        const titleEl = document.getElementById('pdfPreviewTitle');
        const iframe = document.getElementById('pdfPreviewIframe');
        const downloadBtn = document.getElementById('pdfDownloadBtn');

        if (titleEl) titleEl.innerText = title;
        if (iframe) iframe.src = url;
        if (downloadBtn) {
            downloadBtn.href = url;
            downloadBtn.setAttribute('download', title);
        }

        if (pdfModal) pdfModal.show();
        lucide.createIcons();
    };

    // =========================================================================
    // 6. DELETE RECORD MODAL & EXECUTION
    // =========================================================================
    function openDeleteModal(itemId) {
        state.pendingDeleteId = itemId;
        const msgEl = document.getElementById('deleteModalMessage');
        if (msgEl) {
            msgEl.innerHTML = `Are you sure you want to permanently delete record <strong>"${itemId}"</strong>?`;
        }
        if (deleteModal) deleteModal.show();
        lucide.createIcons();
    }

    async function executeDelete() {
        if (!state.pendingDeleteId) return;

        const btn = document.getElementById('confirmDeleteBtn');
        if (btn) {
            btn.disabled = true;
            btn.innerText = 'Deleting...';
        }

        try {
            const res = await fetch(`/admin/api/crud/${state.moduleKey}/${state.pendingDeleteId}`, {
                method: 'DELETE',
                headers: { 'Accept': 'application/json' }
            });

            const data = await res.json();
            if (res.ok && data.status === 'success') {
                showAdminToast(data.message || 'Record deleted successfully.', 'success');
                if (deleteModal) deleteModal.hide();
                loadModuleData();
            } else {
                showAdminToast(data.message || 'Error deleting record.', 'error');
            }
        } catch (err) {
            showAdminToast(`Network error: ${err.message}`, 'error');
        } finally {
            if (btn) {
                btn.disabled = false;
                btn.innerText = 'Yes, Delete';
            }
            state.pendingDeleteId = null;
        }
    }

    async function triggerReindex(itemId) {
        showAdminToast('Re-indexing document into RAG vector store...', 'info');
        try {
            const res = await fetch(`/admin/api/rag/reindex/${state.moduleKey}/${itemId}`, {
                method: 'POST',
                headers: { 'Accept': 'application/json' }
            });
            const data = await res.json();
            if (res.ok && data.status === 'success') {
                showAdminToast(data.message || 'Document re-indexed successfully!', 'success');
                if (detailsModal) detailsModal.hide();
                loadModuleData();
            } else {
                showAdminToast(data.message || 'Re-indexing failed.', 'error');
            }
        } catch (err) {
            showAdminToast(`Network error: ${err.message}`, 'error');
        }
    }
    window.triggerReindex = triggerReindex;

})();
