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
            previewContainer.innerHTML = '<span class="text-xs text-[#8B5CF6]">Uploading PDF document...</span>';
            previewContainer.classList.remove('hidden');
        }

        try {
            const res = await fetch('/admin/api/upload', { method: 'POST', body: formData });
            const data = await res.json();
            if (res.ok && data.status === 'success') {
                state.uploadedDocData = data.file;
                if (previewContainer) {
                    previewContainer.innerHTML = `
                        <div class="flex items-center gap-2.5 p-2.5 rounded-xl bg-emerald-50 border border-emerald-200 text-xs">
                            <i data-lucide="file-text" class="w-4 h-4 text-emerald-600"></i>
                            <span class="text-[#171D3A] font-semibold">${escapeHtml(data.file.file_name)}</span>
                            <span class="text-[#66708F] text-[10px]">(${escapeHtml(data.file.file_size_formatted || '')})</span>
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
        const mobileCards = document.getElementById('academicDocsMobileCards');
        if (!tbody) return;

        tbody.innerHTML = `
            <tr>
                <td colspan="8" class="text-center py-12 text-[#66708F] text-xs">
                    <div class="inline-block animate-spin rounded-full h-5 w-5 border-2 border-[#8B5CF6] border-t-transparent mb-2"></div>
                    <p class="mb-0">Loading academic documents & reports...</p>
                </td>
            </tr>
        `;
        if (mobileCards) mobileCards.innerHTML = '<div class="admin-mobile-empty">Loading documents...</div>';

        const params = new URLSearchParams({
            page: state.page,
            limit: state.limit
        });
        if (state.search) params.append('search', state.search);
        if (state.department) params.append('department', state.department);
        if (state.semester) params.append('semester', state.semester);
        if (state.category) params.append('category', state.category);

        try {
            const res = await fetch(`/admin/api/crud/academic_documents?${params.toString()}`);
            const data = await res.json();
            if (res.ok && (data.status === 'success' || Array.isArray(data.items))) {
                state.items = Array.isArray(data.items)
                    ? data.items
                    : (Array.isArray(data?.data?.items) ? data.data.items : (Array.isArray(data?.data) ? data.data : []));
                state.total = typeof data.total === 'number'
                    ? data.total
                    : (typeof data?.data?.total === 'number' ? data.data.total : state.items.length);
                renderDocumentsTable();
                renderPagination(data.pages || data?.data?.pages || 1);
            } else {
                showAdminToast(data.message || 'Failed to load documents.', 'error');
            }
        } catch (err) {
            showAdminToast(err.message, 'error');
        }
    }

    function renderPagination(totalPages) {
        const pagWrapper = document.getElementById('academicDocsPagination');
        if (!pagWrapper) return;

        if (totalPages <= 1) {
            pagWrapper.classList.add('hidden');
            return;
        }

        pagWrapper.classList.remove('hidden');
        const start = (state.page - 1) * state.limit + 1;
        const end = Math.min(state.page * state.limit, state.total);
        const startEl = document.getElementById('pageStart');
        const endEl = document.getElementById('pageEnd');
        const totalEl = document.getElementById('pageTotal');
        if (startEl) startEl.innerText = start;
        if (endEl) endEl.innerText = end;
        if (totalEl) totalEl.innerText = state.total;

        const prevBtn = document.getElementById('prevPageBtn');
        const nextBtn = document.getElementById('nextPageBtn');

        if (prevBtn) {
            prevBtn.disabled = state.page <= 1;
            prevBtn.onclick = () => {
                if (state.page > 1) {
                    state.page--;
                    loadDocuments();
                }
            };
        }

        if (nextBtn) {
            nextBtn.disabled = state.page >= totalPages;
            nextBtn.onclick = () => {
                if (state.page < totalPages) {
                    state.page++;
                    loadDocuments();
                }
            };
        }

        const numbersContainer = document.getElementById('pageNumbers');
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
                    loadDocuments();
                };
                numbersContainer.appendChild(btn);
            }
        }
    }

    function renderDocumentsTable() {
        const tbody = document.getElementById('academicDocsTableBody');
        const mobileCards = document.getElementById('academicDocsMobileCards');
        const countBadge = document.getElementById('docsCountBadge');
        if (countBadge) countBadge.innerText = `${state.total} Documents`;

        if (state.items.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="8" class="text-center py-12 text-[#66708F] text-xs">
                        <i data-lucide="file-text" class="w-8 h-8 mx-auto mb-2 text-[#8C95AD]"></i>
                        <p class="mb-0">No academic documents indexed in the system.</p>
                    </td>
                </tr>
            `;
            if (mobileCards) mobileCards.innerHTML = '<div class="admin-mobile-empty">No academic documents found matching filters.</div>';
            lucide.createIcons();
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
            const ragStatus = (d.rag_status || (d.is_indexed ? 'indexed' : 'pending')).toLowerCase();

            return `
                <tr>
                    <td>
                        <div class="flex items-center gap-2.5">
                            <div class="pdf-icon-badge">
                                <i data-lucide="file-text" class="w-4 h-4"></i>
                            </div>
                            <div>
                                <p class="text-xs font-bold text-[#171D3A] mb-0">${escapeHtml(title)}</p>
                                <span class="text-[10px] text-[#66708F] font-mono">${escapeHtml(id)}</span>
                            </div>
                        </div>
                    </td>
                    <td class="text-[#171D3A] text-xs">${escapeHtml(dept)}</td>
                    <td class="text-[#66708F] text-xs">${escapeHtml(sem)}</td>
                    <td><span class="px-2 py-0.5 rounded text-[10px] bg-[#E8EBFA] text-[#8B5CF6] font-semibold">${escapeHtml(cat)}</span></td>
                    <td class="text-[#66708F] text-xs">${escapeHtml(date)}</td>
                    <td>
                        ${fileUrl ? `
                            <a href="${fileUrl}" target="_blank" class="text-[#8B5CF6] hover:underline text-xs font-semibold text-decoration-none inline-flex items-center gap-1">
                                <i data-lucide="external-link" class="w-3.5 h-3.5"></i> PDF
                            </a>
                        ` : '<span class="text-[#8C95AD] text-xs">No File</span>'}
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
                                <button class="p-1.5 rounded-lg bg-white border border-[#E1E5F0] text-[#171D3A] hover:bg-[#E8EBFA]" onclick="window.previewDoc('${fileUrl}', '${escapeQuotes(title)}')" title="Preview Document">
                                    <i data-lucide="eye" class="w-3.5 h-3.5"></i>
                                </button>
                            ` : ''}
                            <button class="p-1.5 rounded-lg bg-white border border-[#E1E5F0] text-[#8B5CF6] hover:bg-[#E8EBFA]" onclick="window.reindexDoc('${escapeQuotes(id)}')" title="Re-index Vector DB">
                                <i data-lucide="refresh-cw" class="w-3.5 h-3.5"></i>
                            </button>
                            <button class="p-1.5 rounded-lg bg-white border border-[#E1E5F0] text-red-600 hover:bg-red-50" onclick="window.deleteDoc('${escapeQuotes(id)}')" title="Delete Document">
                                <i data-lucide="trash-2" class="w-3.5 h-3.5"></i>
                            </button>
                        </div>
                    </td>
                </tr>
            `;
        }).join('');

        if (mobileCards) {
            mobileCards.innerHTML = state.items.map(d => {
                const id = d.document_id || d.id || '-';
                const title = d.title || d.file_name || 'Academic Document';
                const dept = d.department || 'General';
                const sem = d.semester ? `Sem ${d.semester}` : 'All Semesters';
                const cat = d.category || 'Syllabus';
                const fileUrl = d.file_url || (d.file ? d.file.file_url : null);
                const ragStatus = (d.rag_status || (d.is_indexed ? 'indexed' : 'pending')).toLowerCase();
                const badge = ragStatus === 'indexed' ? 'badge-rag-indexed' : ragStatus === 'failed' ? 'badge-rag-failed' : 'badge-rag-pending';
                const badgeLabel = ragStatus === 'indexed' ? 'Indexed' : ragStatus === 'failed' ? 'Failed' : 'Pending';

                return `
                    <article class="admin-mobile-record-card">
                        <div class="admin-record-heading">
                            <div class="flex items-center gap-3 min-w-0">
                                <div class="admin-record-icon">
                                    <i data-lucide="file-text"></i>
                                </div>
                                <div class="min-w-0">
                                    <h3>${escapeHtml(title)}</h3>
                                    <p>${escapeHtml(id)}</p>
                                </div>
                            </div>
                            <span class="${badge}">${badgeLabel}</span>
                        </div>
                        <div class="admin-record-meta">
                            <span><b>Category</b>${escapeHtml(cat)}</span>
                            <span><b>Department</b>${escapeHtml(dept)}</span>
                            <span><b>Semester</b>${escapeHtml(sem)}</span>
                        </div>
                        <div class="admin-record-actions">
                            ${fileUrl ? `
                                <button type="button" onclick="window.previewDoc('${fileUrl}', '${escapeQuotes(title)}')" title="Preview PDF">
                                    <i data-lucide="eye"></i> <span>Preview</span>
                                </button>
                                <a href="${fileUrl}" target="_blank" class="p-2 rounded-xl bg-white border border-[#E1E5F0] text-[#171D3A] text-xs font-semibold hover:bg-[#E8EBFA] inline-flex items-center gap-1 text-decoration-none" title="Download PDF">
                                    <i data-lucide="download" class="w-3.5 h-3.5"></i> <span>Download</span>
                                </a>
                            ` : ''}
                            <button type="button" onclick="window.reindexDoc('${escapeQuotes(id)}')" title="Re-index Vector DB">
                                <i data-lucide="refresh-cw"></i> <span>Re-index</span>
                            </button>
                            <button type="button" class="is-danger" onclick="window.deleteDoc('${escapeQuotes(id)}')" title="Delete Document">
                                <i data-lucide="trash-2"></i>
                            </button>
                        </div>
                    </article>
                `;
            }).join('');
        }

        lucide.createIcons();
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
