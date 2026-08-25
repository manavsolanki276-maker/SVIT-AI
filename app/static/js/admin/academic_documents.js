/**
 * SVIT Admin - Page 11: Academic Documents & RAG Vector Knowledge Base Controller
 * Handles academic PDFs/DOCXs, vector database indexing, re-indexing,
 * in-browser PDF preview iframe, document upload, and deletion.
 */

(function() {
    'use strict';

    const state = {
        search: '',
        department: '',
        semester: '',
        category: '',
        page: 1,
        limit: 20,
        total: 0,
        items: [],
        pendingDeleteId: null,
        uploadedDocData: null
    };

    let docUploadModal = null;
    let docPreviewModal = null;
    let docDeleteModal = null;
    let searchDebounce = null;

    document.addEventListener('DOMContentLoaded', function() {
        const formEl = document.getElementById('academicDocModal');
        const prevEl = document.getElementById('academicDocPreviewModal');
        const delEl = document.getElementById('academicDocDeleteModal');

        if (formEl) docUploadModal = new bootstrap.Modal(formEl);
        if (prevEl) docPreviewModal = new bootstrap.Modal(prevEl);
        if (delEl) docDeleteModal = new bootstrap.Modal(delEl);

        bindEvents();
        setupDocFileUpload();
        loadDocuments();
    });

    function bindEvents() {
        const searchInput = document.getElementById('docSearchInput');
        if (searchInput) {
            searchInput.addEventListener('input', (e) => {
                clearTimeout(searchDebounce);
                searchDebounce = setTimeout(() => {
                    state.search = e.target.value.trim();
                    state.page = 1;
                    loadDocuments();
                }, 300);
            });
        }

        const deptFilter = document.getElementById('docDeptFilter');
        if (deptFilter) {
            deptFilter.addEventListener('change', (e) => {
                state.department = e.target.value;
                state.page = 1;
                loadDocuments();
            });
        }

        const semFilter = document.getElementById('docSemFilter');
        if (semFilter) {
            semFilter.addEventListener('change', (e) => {
                state.semester = e.target.value;
                state.page = 1;
                loadDocuments();
            });
        }

        const catFilter = document.getElementById('docCategoryFilter');
        if (catFilter) {
            catFilter.addEventListener('change', (e) => {
                state.category = e.target.value;
                state.page = 1;
                loadDocuments();
            });
        }

        const refreshBtn = document.getElementById('refreshDocsBtn');
        if (refreshBtn) refreshBtn.addEventListener('click', loadDocuments);

        const limitSelect = document.getElementById('pageLimitSelect');
        if (limitSelect) {
            limitSelect.addEventListener('change', (e) => {
                state.limit = parseInt(e.target.value, 10) || 50;
                state.page = 1;
                loadDocuments();
            });
        }

        const prevBtn = document.getElementById('prevPageBtn');
        if (prevBtn) {
            prevBtn.addEventListener('click', () => {
                if (state.page > 1) {
                    state.page--;
                    loadDocuments();
                }
            });
        }

        const nextBtn = document.getElementById('nextPageBtn');
        if (nextBtn) {
            nextBtn.addEventListener('click', () => {
                const totalPages = Math.ceil(state.total / state.limit) || 1;
                if (state.page < totalPages) {
                    state.page++;
                    loadDocuments();
                }
            });
        }

        const uploadBtn = document.getElementById('openUploadDocModalBtn');
        if (uploadBtn) {
            uploadBtn.addEventListener('click', () => {
                document.getElementById('docModalTitle').innerText = 'Upload Academic Document (RAG)';
                document.getElementById('docFormRecordId').value = '';
                document.getElementById('academicDocForm').reset();
                state.uploadedDocData = null;
                resetDocPreview();
                docUploadModal.show();
            });
        }

        const form = document.getElementById('academicDocForm');
        if (form) form.addEventListener('submit', handleDocFormSubmit);

        const confirmDeleteBtn = document.getElementById('confirmDeleteDocBtn');
        if (confirmDeleteBtn) confirmDeleteBtn.addEventListener('click', handleConfirmDelete);
    }

    function setupDocFileUpload() {
        const dropZone = document.getElementById('docFileDropZone');
        const fileInput = document.getElementById('docFileInput');

        if (dropZone && fileInput) {
            dropZone.addEventListener('click', () => fileInput.click());
            dropZone.addEventListener('dragover', (e) => { e.preventDefault(); dropZone.classList.add('border-indigo-500'); });
            dropZone.addEventListener('dragleave', () => dropZone.classList.remove('border-indigo-500'));
            dropZone.addEventListener('drop', (e) => {
                e.preventDefault();
                dropZone.classList.remove('border-indigo-500');
                if (e.dataTransfer.files.length) uploadDocumentFile(e.dataTransfer.files[0]);
            });
            fileInput.addEventListener('change', (e) => {
                if (e.target.files.length) uploadDocumentFile(e.target.files[0]);
            });
        }
    }

    async function uploadDocumentFile(file) {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('category', 'pdf');

        const previewContainer = document.getElementById('docFilePreviewContainer');
        if (previewContainer) {
            previewContainer.innerHTML = '<span class="text-xs text-indigo-400">Uploading PDF document...</span>';
            previewContainer.classList.remove('hidden');
        }

        try {
            const res = await fetch('/admin/api/upload', { method: 'POST', body: formData });
            const data = await res.json();
            if (res.ok && data.status === 'success') {
                state.uploadedDocData = data.file;
                if (previewContainer) {
                    previewContainer.innerHTML = `
                        <div class="flex items-center gap-2 p-2 rounded-lg bg-[#0F172A] border border-emerald-500/50 text-xs">
                            <i data-lucide="file-text" class="w-4 h-4 text-emerald-400"></i>
                            <span class="text-white font-medium">${data.file.file_name}</span>
                            <span class="text-gray-400 text-[10px]">(${data.file.file_size_formatted})</span>
                        </div>
                    `;
                    lucide.createIcons();
                }
                showAdminToast('File uploaded successfully.', 'success');
            } else {
                showAdminToast(data.message || 'File upload failed.', 'error');
                resetDocPreview();
            }
        } catch (err) {
            showAdminToast(err.message, 'error');
            resetDocPreview();
        }
    }

    function resetDocPreview() {
        const preview = document.getElementById('docFilePreviewContainer');
        if (preview) {
            preview.innerHTML = '';
            preview.classList.add('hidden');
        }
    }

    async function loadDocuments() {
        const tbody = document.getElementById('academicDocsTableBody');
        if (!tbody) return;

        tbody.innerHTML = `
            <tr>
                <td colspan="8" class="text-center py-10 text-gray-400 text-xs">
                    <div class="w-5 h-5 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin mx-auto mb-2"></div>
                    Loading academic knowledge base documents...
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
        if (state.category) params.append('filter_category', state.category);

        try {
            const res = await fetch(`/admin/api/crud/academic_documents?${params.toString()}`);
            const data = await res.json();
            if (data.status === 'success') {
                state.items = data.items || [];
                state.total = data.total || 0;
                renderDocumentsTable();
                renderPagination(data);
            } else {
                tbody.innerHTML = `<tr><td colspan="8" class="text-center py-6 text-red-400 text-xs">${data.message}</td></tr>`;
            }
        } catch (err) {
            tbody.innerHTML = `<tr><td colspan="8" class="text-center py-6 text-red-400 text-xs">${err.message}</td></tr>`;
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
                    loadDocuments();
                };
                numbersContainer.appendChild(btn);
            }
        }
    }

    function renderDocumentsTable() {
        const tbody = document.getElementById('academicDocsTableBody');
        const countBadge = document.getElementById('docsCountBadge');
        if (countBadge) countBadge.innerText = `${state.total} Documents`;

        if (state.items.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="8" class="text-center py-12 text-gray-400 text-xs">
                        <i data-lucide="file-text" class="w-8 h-8 mx-auto mb-2 text-gray-600"></i>
                        <p class="mb-0">No academic documents indexed in the system.</p>
                    </td>
                </tr>
            `;
            return;
        }

        tbody.innerHTML = state.items.map(d => {
            const id = d.document_id || d.id || '-';
            const title = d.title || d.file_name || 'Academic Document';
            const dept = d.department || 'General';
            const sem = d.semester ? `Sem ${d.semester}` : 'All Semesters';
            const cat = d.category || 'Syllabus';
            const date = d.uploaded_date || d.publish_date || 'Recent';
            const fileUrl = d.file_url || (d.file ? d.file.file_url : null);
            const ragStatus = d.rag_status || (d.is_indexed ? 'indexed' : 'pending');

            return `
                <tr>
                    <td>
                        <div class="flex items-center gap-2.5">
                            <div class="pdf-icon-badge">
                                <i data-lucide="file-text" class="w-4 h-4"></i>
                            </div>
                            <div>
                                <p class="text-xs font-bold text-white mb-0">${title}</p>
                                <span class="text-[10px] text-gray-400 font-mono">${id}</span>
                            </div>
                        </div>
                    </td>
                    <td class="text-gray-300 text-xs">${dept}</td>
                    <td class="text-gray-300 text-xs">${sem}</td>
                    <td><span class="px-2 py-0.5 rounded text-[10px] bg-indigo-500/20 text-indigo-300 font-semibold">${cat}</span></td>
                    <td class="text-gray-400 text-xs">${date}</td>
                    <td>
                        ${fileUrl ? `
                            <a href="${fileUrl}" target="_blank" class="text-indigo-400 hover:text-indigo-300 text-xs font-medium text-decoration-none flex items-center gap-1">
                                <i data-lucide="external-link" class="w-3.5 h-3.5"></i> PDF
                            </a>
                        ` : '<span class="text-gray-600 text-xs">No File</span>'}
                    </td>
                    <td>
                        ${ragStatus === 'indexed' ? 
                            '<span class="badge-rag-indexed"><i data-lucide="check-circle" class="w-3 h-3"></i>Indexed</span>' : 
                            ragStatus === 'failed' ?
                            '<span class="badge-rag-failed"><i data-lucide="alert-circle" class="w-3 h-3"></i>Failed</span>' :
                            '<span class="badge-rag-pending"><i data-lucide="clock" class="w-3 h-3"></i>Pending</span>'}
                    </td>
                    <td class="text-end">
                        <div class="inline-flex items-center gap-1.5">
                            ${fileUrl ? `
                                <button class="p-1.5 rounded-lg bg-[#0F172A] border border-[#1F2937] text-gray-300 hover:text-white" onclick="window.previewDoc('${fileUrl}', '${title}')" title="Preview Document">
                                    <i data-lucide="eye" class="w-3.5 h-3.5"></i>
                                </button>
                            ` : ''}
                            <button class="p-1.5 rounded-lg bg-[#0F172A] border border-[#1F2937] text-indigo-400 hover:bg-indigo-600/20" onclick="window.reindexDoc('${id}')" title="Re-index Vector DB">
                                <i data-lucide="refresh-cw" class="w-3.5 h-3.5"></i>
                            </button>
                            <button class="p-1.5 rounded-lg bg-[#0F172A] border border-[#1F2937] text-red-400 hover:bg-red-500/20" onclick="window.deleteDoc('${id}')" title="Delete Document">
                                <i data-lucide="trash-2" class="w-3.5 h-3.5"></i>
                            </button>
                        </div>
                    </td>
                </tr>
            `;
        }).join('');
    }

    async function handleDocFormSubmit(e) {
        e.preventDefault();
        const recordId = document.getElementById('docFormRecordId').value;
        const payload = {
            document_id: document.getElementById('docIdInput').value.trim(),
            title: document.getElementById('docTitleInput').value.trim(),
            category: document.getElementById('docCategoryInput').value,
            department: document.getElementById('docDeptInput').value,
            semester: parseInt(document.getElementById('docSemInput').value, 10) || 1,
            description: document.getElementById('docDescInput').value.trim()
        };

        if (state.uploadedDocData) {
            payload.file_url = state.uploadedDocData.url || state.uploadedDocData.file_url;
            payload.file_name = state.uploadedDocData.name || state.uploadedDocData.file_name;
            payload.file_size = state.uploadedDocData.file_size_formatted || state.uploadedDocData.size;
        }

        const isEdit = Boolean(recordId);
        const url = isEdit ? `/admin/api/crud/academic_documents/${recordId}` : '/admin/api/crud/academic_documents';
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
                docUploadModal.hide();
                loadDocuments();
            } else {
                showAdminToast(data.message || 'Error saving document.', 'error');
            }
        } catch (err) {
            showAdminToast(err.message, 'error');
        }
    }

    window.previewDoc = function(url, title) {
        document.getElementById('docPreviewModalTitle').innerText = title;
        document.getElementById('docPreviewIframe').src = url;
        docPreviewModal.show();
    };

    window.reindexDoc = async function(id) {
        try {
            showAdminToast(`Triggering vector re-indexing for ${id}...`, 'info');
            const res = await fetch(`/admin/api/rag/reindex/academic_documents/${id}`, { method: 'POST' });
            const data = await res.json();
            if (res.ok && data.status === 'success') {
                showAdminToast('Document vector embeddings refreshed successfully!', 'success');
                loadDocuments();
            } else {
                showAdminToast(data.message || 'Re-index failed.', 'error');
            }
        } catch (err) {
            showAdminToast(err.message, 'error');
        }
    };

    window.deleteDoc = function(id) {
        state.pendingDeleteId = id;
        document.getElementById('deleteDocTargetId').innerText = id;
        docDeleteModal.show();
    };

    async function handleConfirmDelete() {
        if (!state.pendingDeleteId) return;

        try {
            const res = await fetch(`/admin/api/crud/academic_documents/${state.pendingDeleteId}`, { method: 'DELETE' });
            const data = await res.json();
            if (res.ok && data.status === 'success') {
                showAdminToast(data.message, 'success');
                docDeleteModal.hide();
                loadDocuments();
            } else {
                showAdminToast(data.message || 'Failed to delete document.', 'error');
            }
        } catch (err) {
            showAdminToast(err.message, 'error');
        }
    }
})();
