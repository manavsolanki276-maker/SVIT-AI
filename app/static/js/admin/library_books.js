/**
 * SVIT Admin - Page 20: Library Books Controller
 * Handles accession catalog, ISBN lookup, author/department filtering,
 * book cover upload, and inventory counts.
 */

(function() {
    'use strict';

    const state = {
        search: '',
        category: '',
        page: 1,
        limit: 50,
        total: 0,
        items: [],
        pendingDeleteId: null,
        uploadedCoverUrl: null
    };

    let bookModal = null;
    let bookViewModal = null;
    let bookDeleteModal = null;
    let searchDebounce = null;

    document.addEventListener('DOMContentLoaded', function() {
        const formEl = document.getElementById('bookFormModal');
        const viewEl = document.getElementById('bookViewModal');
        const delEl = document.getElementById('bookDeleteModal');

        if (formEl) bookModal = new bootstrap.Modal(formEl);
        if (viewEl) bookViewModal = new bootstrap.Modal(viewEl);
        if (delEl) bookDeleteModal = new bootstrap.Modal(delEl);

        bindEvents();
        setupCoverUpload();
        loadBooks();
    });

    function bindEvents() {
        const searchInput = document.getElementById('bookSearchInput');
        if (searchInput) {
            searchInput.addEventListener('input', (e) => {
                clearTimeout(searchDebounce);
                searchDebounce = setTimeout(() => {
                    state.search = e.target.value.trim();
                    state.page = 1;
                    loadBooks();
                }, 300);
            });
        }

        const catFilter = document.getElementById('bookCategoryFilter');
        if (catFilter) {
            catFilter.addEventListener('change', (e) => {
                state.category = e.target.value;
                state.page = 1;
                loadBooks();
            });
        }

        const refreshBtn = document.getElementById('refreshBooksBtn');
        if (refreshBtn) refreshBtn.addEventListener('click', loadBooks);

        const limitSelect = document.getElementById('pageLimitSelect');
        if (limitSelect) {
            limitSelect.addEventListener('change', (e) => {
                state.limit = parseInt(e.target.value, 10) || 50;
                state.page = 1;
                loadBooks();
            });
        }

        const prevBtn = document.getElementById('prevPageBtn');
        if (prevBtn) {
            prevBtn.addEventListener('click', () => {
                if (state.page > 1) {
                    state.page--;
                    loadBooks();
                }
            });
        }

        const nextBtn = document.getElementById('nextPageBtn');
        if (nextBtn) {
            nextBtn.addEventListener('click', () => {
                const totalPages = Math.ceil(state.total / state.limit) || 1;
                if (state.page < totalPages) {
                    state.page++;
                    loadBooks();
                }
            });
        }

        const createBtn = document.getElementById('openCreateBookModalBtn');
        if (createBtn) {
            createBtn.addEventListener('click', () => {
                document.getElementById('bookModalTitle').innerText = 'Add Book to Catalog';
                document.getElementById('bookFormRecordId').value = '';
                document.getElementById('bookForm').reset();
                document.getElementById('bookIsbnInput').disabled = false;
                state.uploadedCoverUrl = null;
                resetCoverPreview();
                bookModal.show();
            });
        }

        const form = document.getElementById('bookForm');
        if (form) form.addEventListener('submit', handleBookFormSubmit);

        const confirmDeleteBtn = document.getElementById('confirmDeleteBookBtn');
        if (confirmDeleteBtn) confirmDeleteBtn.addEventListener('click', handleConfirmDelete);
    }

    function setupCoverUpload() {
        const dropZone = document.getElementById('bookCoverDropZone');
        const fileInput = document.getElementById('bookCoverInput');

        if (dropZone && fileInput) {
            dropZone.addEventListener('click', () => fileInput.click());
            dropZone.addEventListener('dragover', (e) => { e.preventDefault(); dropZone.classList.add('border-teal-500'); });
            dropZone.addEventListener('dragleave', () => dropZone.classList.remove('border-teal-500'));
            dropZone.addEventListener('drop', (e) => {
                e.preventDefault();
                dropZone.classList.remove('border-teal-500');
                if (e.dataTransfer.files.length) uploadBookCover(e.dataTransfer.files[0]);
            });
            fileInput.addEventListener('change', (e) => {
                if (e.target.files.length) uploadBookCover(e.target.files[0]);
            });
        }
    }

    async function uploadBookCover(file) {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('category', 'image');

        const preview = document.getElementById('bookCoverPreviewContainer');
        if (preview) {
            preview.innerHTML = '<span class="text-xs text-teal-400">Uploading cover...</span>';
            preview.classList.remove('hidden');
        }

        try {
            const res = await fetch('/admin/api/upload', { method: 'POST', body: formData });
            const data = await res.json();
            if (res.ok && data.status === 'success') {
                state.uploadedCoverUrl = data.file.url;
                if (preview) {
                    preview.innerHTML = `
                        <img src="${data.file.url}" class="w-12 h-16 rounded object-cover border border-teal-500">
                        <span class="text-xs text-emerald-400 font-medium">Cover Attached</span>
                    `;
                }
                showAdminToast('Book cover attached.', 'success');
            } else {
                showAdminToast(data.message || 'Upload failed.', 'error');
                resetCoverPreview();
            }
        } catch (err) {
            showAdminToast(err.message, 'error');
            resetCoverPreview();
        }
    }

    function resetCoverPreview() {
        const preview = document.getElementById('bookCoverPreviewContainer');
        if (preview) {
            preview.innerHTML = '';
            preview.classList.add('hidden');
        }
    }

    async function loadBooks() {
        const tbody = document.getElementById('booksTableBody');
        if (!tbody) return;

        tbody.innerHTML = `
            <tr>
                <td colspan="7" class="text-center py-10 text-gray-400 text-xs">
                    <div class="w-5 h-5 border-2 border-teal-500 border-t-transparent rounded-full animate-spin mx-auto mb-2"></div>
                    Loading accession catalog...
                </td>
            </tr>
        `;

        const params = new URLSearchParams({
            page: state.page,
            limit: state.limit,
            search: state.search
        });
        if (state.category) params.append('filter_category', state.category);

        try {
            const res = await fetch(`/admin/api/crud/library_books?${params.toString()}`);
            const data = await res.json();
            if (data.status === 'success') {
                state.items = data.items || [];
                state.total = data.total || 0;
                renderBooksTable();
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
                btn.className = `px-2 py-1 rounded-lg text-xs font-semibold transition ${state.page === i ? 'bg-teal-600 text-white' : 'bg-[#111827] border border-[#1F2937] text-gray-400 hover:text-white'}`;
                btn.onclick = () => {
                    state.page = i;
                    loadBooks();
                };
                numbersContainer.appendChild(btn);
            }
        }
    }

    function renderBooksTable() {
        const tbody = document.getElementById('booksTableBody');
        const countBadge = document.getElementById('booksCountBadge');
        if (countBadge) countBadge.innerText = `${state.total} Books`;

        if (state.items.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="7" class="text-center py-12 text-gray-400 text-xs">
                        <i data-lucide="book-open" class="w-8 h-8 mx-auto mb-2 text-gray-600"></i>
                        <p class="mb-0">No book titles found.</p>
                    </td>
                </tr>
            `;
            return;
        }

        tbody.innerHTML = state.items.map(b => {
            const id = b.book_id || b.isbn || b.id || '-';
            const title = b.title || b.book_name || 'Book Title';
            const author = b.author || 'Author';
            const cat = b.category || b.department || 'Engineering';
            const total = b.total_copies || b.copies || 5;
            const avail = b.available_copies !== undefined ? b.available_copies : total;
            const shelf = b.shelf_location || b.shelf || 'Rack A-1';
            const cover = b.cover_image || b.image_url;

            return `
                <tr>
                    <td>
                        <div class="flex items-center gap-3">
                            <div class="book-cover-box">
                                ${cover ? `<img src="${cover}" alt="${title}">` : '<i data-lucide="book" class="w-4 h-4 text-teal-400"></i>'}
                            </div>
                            <div>
                                <p class="text-xs font-bold text-white mb-0.5">${title}</p>
                                <span class="text-[11px] text-gray-400">by ${author}</span>
                            </div>
                        </div>
                    </td>
                    <td class="font-mono text-teal-400 font-bold text-xs">${id}</td>
                    <td><span class="px-2 py-0.5 rounded text-[10px] bg-teal-500/20 text-teal-300 font-semibold">${cat}</span></td>
                    <td><span class="badge-shelf">${shelf}</span></td>
                    <td class="text-xs">
                        <span class="text-emerald-400 font-bold">${avail}</span> / <span class="text-gray-400">${total}</span>
                    </td>
                    <td>
                        ${avail > 0 ? 
                            '<span class="px-2 py-0.5 rounded text-[10px] bg-emerald-500/20 text-emerald-300 font-semibold">In Stock</span>' : 
                            '<span class="px-2 py-0.5 rounded text-[10px] bg-red-500/20 text-red-300 font-semibold">All Issued</span>'}
                    </td>
                    <td class="text-end">
                        <div class="inline-flex items-center gap-1.5">
                            <button class="p-1.5 rounded-lg bg-[#0F172A] border border-[#1F2937] text-gray-300 hover:text-white" onclick="window.viewBook('${id}')" title="View Details">
                                <i data-lucide="eye" class="w-3.5 h-3.5"></i>
                            </button>
                            <button class="p-1.5 rounded-lg bg-[#0F172A] border border-[#1F2937] text-gray-300 hover:text-white" onclick="window.editBook('${id}')" title="Edit Book">
                                <i data-lucide="edit-2" class="w-3.5 h-3.5"></i>
                            </button>
                            <button class="p-1.5 rounded-lg bg-[#0F172A] border border-[#1F2937] text-red-400 hover:bg-red-500/20" onclick="window.deleteBook('${id}')" title="Delete">
                                <i data-lucide="trash-2" class="w-3.5 h-3.5"></i>
                            </button>
                        </div>
                    </td>
                </tr>
            `;
        }).join('');
    }

    async function handleBookFormSubmit(e) {
        e.preventDefault();
        const recordId = document.getElementById('bookFormRecordId').value;
        const payload = {
            book_id: document.getElementById('bookIsbnInput').value.trim(),
            isbn: document.getElementById('bookIsbnInput').value.trim(),
            title: document.getElementById('bookTitleInput').value.trim(),
            author: document.getElementById('bookAuthorInput').value.trim(),
            category: document.getElementById('bookCatInput').value,
            department: document.getElementById('bookDeptInput').value,
            total_copies: parseInt(document.getElementById('bookTotalCopiesInput').value, 10) || 5,
            available_copies: parseInt(document.getElementById('bookAvailCopiesInput').value, 10) || 5,
            shelf_location: document.getElementById('bookShelfInput').value.trim()
        };

        if (state.uploadedCoverUrl) payload.cover_image = state.uploadedCoverUrl;

        const isEdit = Boolean(recordId);
        const url = isEdit ? `/admin/api/crud/library_books/${recordId}` : '/admin/api/crud/library_books';
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
                bookModal.hide();
                loadBooks();
            } else {
                showAdminToast(data.message || 'Error saving book.', 'error');
            }
        } catch (err) {
            showAdminToast(err.message, 'error');
        }
    }

    window.editBook = function(id) {
        const item = state.items.find(b => (b.book_id || b.isbn || b.id) === id);
        if (!item) return;

        document.getElementById('bookModalTitle').innerText = 'Edit Book';
        document.getElementById('bookFormRecordId').value = id;
        document.getElementById('bookIsbnInput').value = item.isbn || item.book_id || id;
        document.getElementById('bookIsbnInput').disabled = true;
        document.getElementById('bookTitleInput').value = item.title || item.book_name || '';
        document.getElementById('bookAuthorInput').value = item.author || '';
        document.getElementById('bookCatInput').value = item.category || 'Computer Science';
        document.getElementById('bookDeptInput').value = item.department || 'Computer Engineering';
        document.getElementById('bookTotalCopiesInput').value = item.total_copies || 5;
        document.getElementById('bookAvailCopiesInput').value = item.available_copies !== undefined ? item.available_copies : 5;
        document.getElementById('bookShelfInput').value = item.shelf_location || '';

        state.uploadedCoverUrl = item.cover_image || item.image_url || null;
        if (state.uploadedCoverUrl) {
            const preview = document.getElementById('bookCoverPreviewContainer');
            if (preview) {
                preview.innerHTML = `<img src="${state.uploadedCoverUrl}" class="w-12 h-16 rounded object-cover border border-teal-500">`;
                preview.classList.remove('hidden');
            }
        } else {
            resetCoverPreview();
        }

        bookModal.show();
    };

    window.viewBook = function(id) {
        const item = state.items.find(b => (b.book_id || b.isbn || b.id) === id);
        if (!item) return;

        const container = document.getElementById('bookViewContent');
        if (!container) return;

        container.innerHTML = `
            <div class="space-y-4">
                <div class="flex items-center gap-3.5 p-4 rounded-2xl bg-[#0F172A] border border-[#1F2937]">
                    <div class="w-14 h-20 rounded-lg bg-teal-600/20 border border-teal-500/30 flex items-center justify-center overflow-hidden flex-shrink-0">
                        ${(item.cover_image || item.image_url) ? `<img src="${item.cover_image || item.image_url}" class="w-full h-full object-cover">` : '<i data-lucide="book" class="w-6 h-6 text-teal-400"></i>'}
                    </div>
                    <div>
                        <h3 class="text-base font-bold text-white mb-0.5">${item.title || item.book_name}</h3>
                        <p class="text-xs text-gray-400 mb-0.5">by <strong class="text-white">${item.author}</strong></p>
                        <p class="text-[11px] text-teal-400 font-mono mb-0">ISBN: ${item.isbn || item.book_id || id}</p>
                    </div>
                </div>
                <div class="grid grid-cols-2 gap-3 text-xs">
                    <div class="p-2.5 rounded-lg bg-[#0F172A] border border-[#1F2937]">
                        <span class="text-gray-500 block text-[10px]">SHELF RACK LOCATION</span>
                        <span class="text-teal-300 font-bold">${item.shelf_location || 'Rack A-1'}</span>
                    </div>
                    <div class="p-2.5 rounded-lg bg-[#0F172A] border border-[#1F2937]">
                        <span class="text-gray-500 block text-[10px]">AVAILABLE INVENTORY</span>
                        <span class="text-emerald-400 font-bold">${item.available_copies !== undefined ? item.available_copies : 5} of ${item.total_copies || 5} Available</span>
                    </div>
                </div>
            </div>
        `;

        bookViewModal.show();
    };

    window.deleteBook = function(id) {
        state.pendingDeleteId = id;
        document.getElementById('deleteBookTargetId').innerText = id;
        bookDeleteModal.show();
    };

    async function handleConfirmDelete() {
        if (!state.pendingDeleteId) return;

        try {
            const res = await fetch(`/admin/api/crud/library_books/${state.pendingDeleteId}`, { method: 'DELETE' });
            const data = await res.json();
            if (res.ok && data.status === 'success') {
                showAdminToast(data.message, 'success');
                bookDeleteModal.hide();
                loadBooks();
            } else {
                showAdminToast(data.message || 'Delete failed.', 'error');
            }
        } catch (err) {
            showAdminToast(err.message, 'error');
        }
    }
})();
