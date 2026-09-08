/**
 * app/static/js/admin/library.js
 * SVIT Central Library Management System Controller
 * Handles books catalog CRUD, circulation ledger (issue/return),
 * registered student members, faceted filtering, and pagination.
 */

document.addEventListener('DOMContentLoaded', () => {
    // --- STATE MANAGEMENT ---
    const state = {
        activeTab: 'books',
        books: {
            page: 1,
            limit: 20,
            search: '',
            department: '',
            availability: '',
            total: 0,
            pages: 1,
            items: []
        },
        issues: {
            page: 1,
            limit: 20,
            search: '',
            status: 'Issued',
            total: 0,
            pages: 1,
            items: []
        },
        members: {
            search: '',
            items: []
        },
        stats: {
            total_books: 0,
            available_books: 0,
            issued_books: 0,
            overdue_books: 0,
            total_members: 0
        }
    };

    // Cache DOM Elements
    const rootContainer = document.querySelector('[data-active-tab]');
    const tabBooksBtn = document.getElementById('tabBooksBtn');
    const tabIssuesBtn = document.getElementById('tabIssuesBtn');
    const tabMembersBtn = document.getElementById('tabMembersBtn');

    const tabBooksContent = document.getElementById('tabBooksContent');
    const tabIssuesContent = document.getElementById('tabIssuesContent');
    const tabMembersContent = document.getElementById('tabMembersContent');

    // Modals
    const bookFormModal = document.getElementById('bookFormModal');
    const issueBookModal = document.getElementById('issueBookModal');
    const returnBookModal = document.getElementById('returnBookModal');
    const viewBookModal = document.getElementById('viewBookModal');
    const deleteBookModal = document.getElementById('deleteBookModal');

    // Initialize Active Tab from template
    if (rootContainer) {
        const initialTab = rootContainer.getAttribute('data-active-tab');
        if (initialTab && ['books', 'issues', 'members'].includes(initialTab)) {
            state.activeTab = initialTab;
        }
    }

    // --- INITIALIZATION ---
    function init() {
        bindEvents();
        switchTab(state.activeTab);
        loadStats();
        loadBooks();
        loadIssues();
        loadMembers();
    }

    // --- TAB SWITCHING ---
    function switchTab(tab) {
        state.activeTab = tab;

        // Reset tab button states
        [tabBooksBtn, tabIssuesBtn, tabMembersBtn].forEach(btn => {
            if (!btn) return;
            btn.classList.remove('active', 'bg-[#E8EBFA]', 'text-[#8B5CF6]');
            btn.classList.add('text-[#66708F]');
        });

        // Hide contents
        if (tabBooksContent) tabBooksContent.classList.add('hidden');
        if (tabIssuesContent) tabIssuesContent.classList.add('hidden');
        if (tabMembersContent) tabMembersContent.classList.add('hidden');

        if (tab === 'books') {
            if (tabBooksBtn) {
                tabBooksBtn.classList.add('active', 'bg-[#E8EBFA]', 'text-[#8B5CF6]');
                tabBooksBtn.classList.remove('text-[#66708F]');
            }
            if (tabBooksContent) tabBooksContent.classList.remove('hidden');
        } else if (tab === 'issues') {
            if (tabIssuesBtn) {
                tabIssuesBtn.classList.add('active', 'bg-[#E8EBFA]', 'text-[#8B5CF6]');
                tabIssuesBtn.classList.remove('text-[#66708F]');
            }
            if (tabIssuesContent) tabIssuesContent.classList.remove('hidden');
            loadIssues();
        } else if (tab === 'members') {
            if (tabMembersBtn) {
                tabMembersBtn.classList.add('active', 'bg-[#E8EBFA]', 'text-[#8B5CF6]');
                tabMembersBtn.classList.remove('text-[#66708F]');
            }
            if (tabMembersContent) tabMembersContent.classList.remove('hidden');
            loadMembers();
        }

        refreshIcons();
    }

    // --- API: STATS ---
    async function loadStats() {
        try {
            const res = await fetch('/admin/api/library/stats');
            if (!res.ok) throw new Error('Failed to fetch stats');
            const data = await res.json();
            if (data.status === 'success' && data.stats) {
                state.stats = data.stats;
                renderStats();
            }
        } catch (err) {
            console.warn('[Library] Stats error:', err);
        }
    }

    function renderStats() {
        const s = state.stats;
        const total = s.total_books || 0;
        const avail = s.available_books || 0;
        const issued = s.issued_books || 0;
        const overdue = s.overdue_books || 0;
        const members = s.total_members || 0;

        const totalEl = document.getElementById('statTotalBooks');
        const availEl = document.getElementById('statAvailableBooks');
        const issuedEl = document.getElementById('statIssuedBooks');
        const overdueEl = document.getElementById('statOverdueBooks');
        const membersEl = document.getElementById('statTotalMembers');
        const badgeEl = document.getElementById('catalogCountBadge');
        const tabBooksCount = document.getElementById('tabBooksCount');

        if (totalEl) totalEl.textContent = Number(total).toLocaleString();
        if (availEl) availEl.textContent = Number(avail).toLocaleString();
        if (issuedEl) issuedEl.textContent = Number(issued).toLocaleString();
        if (overdueEl) overdueEl.textContent = Number(overdue).toLocaleString();
        if (membersEl) membersEl.textContent = Number(members).toLocaleString();
        if (badgeEl) badgeEl.textContent = `${Number(total).toLocaleString()} Titles in System`;
        if (tabBooksCount) tabBooksCount.textContent = Number(total).toLocaleString();
    }

    // --- API: BOOKS CATALOG ---
    async function loadBooks() {
        const tbody = document.getElementById('booksTableBody');
        if (tbody) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="10" class="text-center py-10 text-[#8C95AD]">
                        <div class="flex flex-col items-center justify-center gap-2">
                            <div class="spinner-border spinner-border-sm text-indigo-600" role="status"></div>
                            <span class="text-xs font-semibold">Loading library catalog...</span>
                        </div>
                    </td>
                </tr>
            `;
        }

        try {
            const params = new URLSearchParams({
                page: state.books.page,
                limit: state.books.limit,
                search: state.books.search
            });

            if (state.books.department) {
                params.append('filter_department', state.books.department);
            }
            if (state.books.availability) {
                params.append('filter_availability', state.books.availability);
            }

            const res = await fetch(`/admin/api/crud/library_books?${params.toString()}`);
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            const data = await res.json();

            if (data.status === 'success') {
                state.books.items = data.items || [];
                state.books.total = data.total || 0;
                state.books.pages = data.pages || 1;
                renderBooksTable();
                renderBooksPagination();
            } else {
                showEmptyBooks(data.message || 'No books found');
            }
        } catch (err) {
            console.error('[Library] Load books error:', err);
            showEmptyBooks('Error loading book catalog: ' + err.message);
        }
    }

    function showEmptyBooks(msg) {
        const tbody = document.getElementById('booksTableBody');
        if (!tbody) return;
        tbody.innerHTML = `
            <tr>
                <td colspan="10" class="text-center py-12 text-[#8C95AD]">
                    <div class="flex flex-col items-center justify-center gap-2">
                        <i data-lucide="book-x" class="w-8 h-8 text-[#8C95AD]"></i>
                        <span class="text-xs font-semibold text-[#171D3A]">${escapeHtml(msg)}</span>
                        <span class="text-[11px] text-[#8C95AD]">Try adjusting your search keywords or clearing filters.</span>
                    </div>
                </td>
            </tr>
        `;
        refreshIcons();
    }

    function renderBooksTable() {
        const tbody = document.getElementById('booksTableBody');
        if (!tbody) return;

        if (!state.books.items.length) {
            showEmptyBooks('No books match your search or filter criteria');
            return;
        }

        tbody.innerHTML = state.books.items.map(b => {
            const id = escapeHtml(b.id || b._id || b.book_id || '');
            const title = escapeHtml(b.title || b.book_title || b.name || 'Untitled Book');
            const author = escapeHtml(b.author || b.authors || 'Unknown');
            const dept = escapeHtml(b.department || b.category || 'General');
            const subject = escapeHtml(b.subject || '');
            const shelf = escapeHtml(b.shelf_location || b.shelf || b.location || 'Main Stacks');
            const total = parseInt(b.total_copies ?? 1);
            const avail = parseInt(b.available_copies ?? (total - parseInt(b.issued_copies || 0)));
            const issued = parseInt(b.issued_copies ?? (total - avail));

            let statusBadge = `<span class="badge-stock-avail"><span class="w-1.5 h-1.5 rounded-full bg-emerald-500"></span> Available</span>`;
            if (avail <= 0) {
                statusBadge = `<span class="badge-stock-out"><span class="w-1.5 h-1.5 rounded-full bg-rose-500"></span> Out of Stock</span>`;
            } else if (b.status === 'Reference Only') {
                statusBadge = `<span class="badge-stock-ref"><span class="w-1.5 h-1.5 rounded-full bg-amber-500"></span> Reference</span>`;
            }

            return `
                <tr class="hover:bg-[#F8F9FE]/60 transition border-b border-[#F1F3F9]" data-book-id="${id}">
                    <td data-label="ACCESSION ID" class="font-mono text-xs font-bold text-indigo-600">${id}</td>
                    <td data-label="BOOK TITLE & SUBJECT">
                        <div class="font-bold text-[#171D3A] text-xs">${title}</div>
                        ${subject ? `<div class="text-[11px] text-[#8C95AD] mt-0.5">${subject}</div>` : ''}
                    </td>
                    <td data-label="AUTHOR(S)" class="text-xs text-[#66708F]">${author}</td>
                    <td data-label="DEPARTMENT">
                        <span class="px-2 py-0.5 rounded-md text-[10px] font-semibold bg-[#E8EBFA] text-indigo-700">${dept}</span>
                    </td>
                    <td data-label="SHELF / RACK" class="text-xs text-[#66708F]">${shelf}</td>
                    <td data-label="TOTAL COPIES" class="text-center font-bold text-xs text-[#171D3A]">${total}</td>
                    <td data-label="AVAILABLE" class="text-center font-extrabold text-xs text-emerald-600">${avail}</td>
                    <td data-label="ISSUED" class="text-center font-bold text-xs text-blue-600">${issued}</td>
                    <td data-label="STATUS">${statusBadge}</td>
                    <td data-label="ACTIONS" class="text-end">
                        <div class="flex items-center justify-end gap-1">
                            <button class="view-book-btn p-1.5 rounded-lg text-[#66708F] hover:text-indigo-600 hover:bg-indigo-50" title="View Details" data-book-id="${id}">
                                <i data-lucide="eye" class="w-4 h-4"></i>
                            </button>
                            <button class="edit-book-btn p-1.5 rounded-lg text-[#66708F] hover:text-[#8B5CF6] hover:bg-purple-50" title="Edit Book" data-book-id="${id}">
                                <i data-lucide="edit-3" class="w-4 h-4"></i>
                            </button>
                            ${avail > 0 ? `
                            <button class="issue-book-row-btn p-1.5 rounded-lg text-[#66708F] hover:text-emerald-600 hover:bg-emerald-50" title="Quick Issue" data-book-id="${id}">
                                <i data-lucide="arrow-left-right" class="w-4 h-4"></i>
                            </button>` : ''}
                            <button class="delete-book-btn p-1.5 rounded-lg text-[#66708F] hover:text-rose-600 hover:bg-rose-50" title="Delete Book" data-book-id="${id}">
                                <i data-lucide="trash-2" class="w-4 h-4"></i>
                            </button>
                        </div>
                    </td>
                </tr>
            `;
        }).join('');

        refreshIcons();
    }

    function renderBooksPagination() {
        const info = document.getElementById('booksPaginationInfo');
        const ctrl = document.getElementById('booksPaginationControls');
        if (!info || !ctrl) return;

        const { page, limit, total, pages } = state.books;
        const start = total === 0 ? 0 : (page - 1) * limit + 1;
        const end = Math.min(page * limit, total);

        info.textContent = `Showing ${start} - ${end} of ${total.toLocaleString()} books`;

        let btns = [];

        // Prev button
        btns.push(`
            <button class="page-ctrl-btn" data-page="${page - 1}" ${page <= 1 ? 'disabled' : ''}>
                <i data-lucide="chevron-left" class="w-3.5 h-3.5"></i>
            </button>
        `);

        // Page numbers
        const maxVisible = 5;
        let startPage = Math.max(1, page - 2);
        let endPage = Math.min(pages, startPage + maxVisible - 1);
        if (endPage - startPage < maxVisible - 1) {
            startPage = Math.max(1, endPage - maxVisible + 1);
        }

        if (startPage > 1) {
            btns.push(`<button class="page-ctrl-btn" data-page="1">1</button>`);
            if (startPage > 2) btns.push(`<span class="px-1 text-[#8C95AD]">...</span>`);
        }

        for (let p = startPage; p <= endPage; p++) {
            btns.push(`
                <button class="page-ctrl-btn ${p === page ? 'active' : ''}" data-page="${p}">${p}</button>
            `);
        }

        if (endPage < pages) {
            if (endPage < pages - 1) btns.push(`<span class="px-1 text-[#8C95AD]">...</span>`);
            btns.push(`<button class="page-ctrl-btn" data-page="${pages}">${pages}</button>`);
        }

        // Next button
        btns.push(`
            <button class="page-ctrl-btn" data-page="${page + 1}" ${page >= pages ? 'disabled' : ''}>
                <i data-lucide="chevron-right" class="w-3.5 h-3.5"></i>
            </button>
        `);

        ctrl.innerHTML = btns.join('');
        refreshIcons();
    }

    // --- API: CIRCULATION LEDGER (ISSUES) ---
    async function loadIssues() {
        const tbody = document.getElementById('issuesTableBody');
        if (tbody) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="8" class="text-center py-10 text-[#8C95AD]">
                        <div class="flex flex-col items-center justify-center gap-2">
                            <div class="spinner-border spinner-border-sm text-indigo-600" role="status"></div>
                            <span class="text-xs font-semibold">Loading circulation ledger...</span>
                        </div>
                    </td>
                </tr>
            `;
        }

        try {
            const params = new URLSearchParams({
                page: state.issues.page,
                limit: state.issues.limit,
                search: state.issues.search,
                status: state.issues.status
            });

            const res = await fetch(`/admin/api/library/issues?${params.toString()}`);
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            const data = await res.json();

            if (data.status === 'success') {
                state.issues.items = data.items || [];
                state.issues.total = data.total || 0;
                state.issues.pages = data.pages || 1;

                const tabIssuesCount = document.getElementById('tabIssuesCount');
                if (tabIssuesCount) tabIssuesCount.textContent = (data.total || 0).toLocaleString();

                renderIssuesTable();
                renderIssuesPagination();
            } else {
                showEmptyIssues(data.message || 'No circulation records found');
            }
        } catch (err) {
            console.error('[Library] Load issues error:', err);
            showEmptyIssues('Error loading ledger: ' + err.message);
        }
    }

    function showEmptyIssues(msg) {
        const tbody = document.getElementById('issuesTableBody');
        if (!tbody) return;
        tbody.innerHTML = `
            <tr>
                <td colspan="8" class="text-center py-12 text-[#8C95AD]">
                    <div class="flex flex-col items-center justify-center gap-2">
                        <i data-lucide="inbox" class="w-8 h-8 text-[#8C95AD]"></i>
                        <span class="text-xs font-semibold text-[#171D3A]">${escapeHtml(msg)}</span>
                        <span class="text-[11px] text-[#8C95AD]">No transactions match current status filter.</span>
                    </div>
                </td>
            </tr>
        `;
        refreshIcons();
    }

    function renderIssuesTable() {
        const tbody = document.getElementById('issuesTableBody');
        if (!tbody) return;

        if (!state.issues.items.length) {
            showEmptyIssues('No circulation records found');
            return;
        }

        const todayStr = new Date().toISOString().split('T')[0];

        tbody.innerHTML = state.issues.items.map(it => {
            const id = escapeHtml(it.id || it._id || it.issue_id || '');
            const bookTitle = escapeHtml(it.book_title || it.title || it.book_id || 'Book');
            const bookId = escapeHtml(it.book_id || '');
            const studentName = escapeHtml(it.student_name || it.borrower_name || 'Student');
            const studentEnroll = escapeHtml(it.enrollment_no || it.student_id || '');
            const issueDate = escapeHtml(it.issue_date || it.created_at || '--');
            const dueDate = escapeHtml(it.due_date || '--');
            const returnDate = escapeHtml(it.return_date || '--');
            let status = it.status || 'Issued';

            // Auto overdue badge check
            const isPastDue = (status === 'Issued' && dueDate && dueDate < todayStr);
            if (isPastDue) status = 'Overdue';

            let badgeHtml = `<span class="badge-issue-active"><span class="w-1.5 h-1.5 rounded-full bg-blue-500"></span> Issued</span>`;
            if (status === 'Returned') {
                badgeHtml = `<span class="badge-issue-returned"><span class="w-1.5 h-1.5 rounded-full bg-gray-400"></span> Returned</span>`;
            } else if (status === 'Overdue') {
                badgeHtml = `<span class="badge-issue-overdue"><span class="w-1.5 h-1.5 rounded-full bg-rose-500"></span> Overdue</span>`;
            }

            return `
                <tr class="hover:bg-[#F8F9FE]/60 transition border-b border-[#F1F3F9]">
                    <td data-label="TRANSACTION ID" class="font-mono text-xs font-bold text-indigo-600">${id}</td>
                    <td data-label="BORROWED BOOK">
                        <div class="font-bold text-[#171D3A] text-xs">${bookTitle}</div>
                        <div class="text-[11px] font-mono text-[#8C95AD]">${bookId}</div>
                    </td>
                    <td data-label="STUDENT BORROWER">
                        <div class="font-semibold text-[#171D3A] text-xs">${studentName}</div>
                        <div class="text-[11px] font-mono text-indigo-600">${studentEnroll}</div>
                    </td>
                    <td data-label="ISSUE DATE" class="text-xs text-[#66708F]">${issueDate.slice(0, 10)}</td>
                    <td data-label="DUE DATE" class="text-xs font-semibold ${isPastDue ? 'text-rose-600' : 'text-[#171D3A]'}">${dueDate.slice(0, 10)}</td>
                    <td data-label="RETURN DATE" class="text-xs text-[#66708F]">${returnDate !== '--' ? returnDate.slice(0, 10) : '--'}</td>
                    <td data-label="STATUS">${badgeHtml}</td>
                    <td data-label="ACTION" class="text-end">
                        ${status !== 'Returned' ? `
                            <button class="return-issue-btn px-2.5 py-1 rounded-lg text-xs font-bold bg-emerald-50 text-emerald-700 hover:bg-emerald-600 hover:text-white border border-emerald-200 transition shadow-sm flex items-center gap-1 ml-auto" data-issue-id="${id}" data-book="${bookTitle}" data-student="${studentName}" data-due="${dueDate}">
                                <i data-lucide="check" class="w-3.5 h-3.5"></i> Return
                            </button>
                        ` : `
                            <span class="text-[11px] text-[#8C95AD] italic">Completed</span>
                        `}
                    </td>
                </tr>
            `;
        }).join('');

        refreshIcons();
    }

    function renderIssuesPagination() {
        const info = document.getElementById('issuesPaginationInfo');
        const ctrl = document.getElementById('issuesPaginationControls');
        if (!info || !ctrl) return;

        const { page, limit, total, pages } = state.issues;
        const start = total === 0 ? 0 : (page - 1) * limit + 1;
        const end = Math.min(page * limit, total);

        info.textContent = `Showing ${start} - ${end} of ${total.toLocaleString()} records`;

        let btns = [];
        btns.push(`
            <button class="page-ctrl-btn" data-issue-page="${page - 1}" ${page <= 1 ? 'disabled' : ''}>
                <i data-lucide="chevron-left" class="w-3.5 h-3.5"></i>
            </button>
        `);

        for (let p = 1; p <= pages; p++) {
            if (p === 1 || p === pages || (p >= page - 2 && p <= page + 2)) {
                btns.push(`
                    <button class="page-ctrl-btn ${p === page ? 'active' : ''}" data-issue-page="${p}">${p}</button>
                `);
            } else if (p === page - 3 || p === page + 3) {
                btns.push(`<span class="px-1 text-[#8C95AD]">...</span>`);
            }
        }

        btns.push(`
            <button class="page-ctrl-btn" data-issue-page="${page + 1}" ${page >= pages ? 'disabled' : ''}>
                <i data-lucide="chevron-right" class="w-3.5 h-3.5"></i>
            </button>
        `);

        ctrl.innerHTML = btns.join('');
        refreshIcons();
    }

    // --- API: MEMBERS ---
    async function loadMembers() {
        const tbody = document.getElementById('membersTableBody');
        if (tbody) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="6" class="text-center py-10 text-[#8C95AD]">
                        <div class="flex flex-col items-center justify-center gap-2">
                            <div class="spinner-border spinner-border-sm text-indigo-600" role="status"></div>
                            <span class="text-xs font-semibold">Loading student members...</span>
                        </div>
                    </td>
                </tr>
            `;
        }

        try {
            const params = new URLSearchParams({
                q: state.members.search,
                limit: 50
            });

            const res = await fetch(`/admin/api/library/members?${params.toString()}`);
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            const data = await res.json();

            if (data.status === 'success') {
                state.members.items = data.members || [];
                renderMembersTable();
            } else {
                showEmptyMembers('No registered students found');
            }
        } catch (err) {
            console.error('[Library] Load members error:', err);
            showEmptyMembers('Error loading members: ' + err.message);
        }
    }

    function showEmptyMembers(msg) {
        const tbody = document.getElementById('membersTableBody');
        if (!tbody) return;
        tbody.innerHTML = `
            <tr>
                <td colspan="6" class="text-center py-12 text-[#8C95AD]">
                    <div class="flex flex-col items-center justify-center gap-2">
                        <i data-lucide="users" class="w-8 h-8 text-[#8C95AD]"></i>
                        <span class="text-xs font-semibold text-[#171D3A]">${escapeHtml(msg)}</span>
                    </div>
                </td>
            </tr>
        `;
        refreshIcons();
    }

    function renderMembersTable() {
        const tbody = document.getElementById('membersTableBody');
        if (!tbody) return;

        if (!state.members.items.length) {
            showEmptyMembers('No student members matched search');
            return;
        }

        tbody.innerHTML = state.members.items.map(m => {
            const enroll = escapeHtml(m.enrollment_no || m.id || '');
            const name = escapeHtml(m.name || m.full_name || 'Student');
            const dept = escapeHtml(m.department || 'Computer Engineering');
            const prog = escapeHtml(m.program || 'B.Tech');
            const sem = escapeHtml(String(m.semester || '1'));
            const status = escapeHtml(m.status || 'Active');

            return `
                <tr class="hover:bg-[#F8F9FE]/60 transition border-b border-[#F1F3F9]">
                    <td data-label="ENROLLMENT NUMBER" class="font-mono text-xs font-bold text-indigo-600">${enroll}</td>
                    <td data-label="STUDENT NAME" class="font-bold text-[#171D3A] text-xs">${name}</td>
                    <td data-label="DEPARTMENT" class="text-xs text-[#66708F]">${dept}</td>
                    <td data-label="PROGRAM & SEM">
                        <span class="px-2 py-0.5 rounded-md text-[10px] font-semibold bg-[#F1F3F9] text-[#171D3A]">${prog} (Sem ${sem})</span>
                    </td>
                    <td data-label="STATUS">
                        <span class="px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-50 text-emerald-700 border border-emerald-200">${status}</span>
                    </td>
                    <td data-label="QUICK ACTION" class="text-end">
                        <button class="quick-issue-member-btn px-2.5 py-1 rounded-lg text-xs font-bold bg-indigo-50 text-indigo-700 hover:bg-indigo-600 hover:text-white border border-indigo-200 transition shadow-sm flex items-center gap-1 ml-auto" data-enroll="${enroll}" data-name="${name}">
                            <i data-lucide="arrow-left-right" class="w-3.5 h-3.5"></i> Issue Book
                        </button>
                    </td>
                </tr>
            `;
        }).join('');

        refreshIcons();
    }

    // --- MODAL CONTROLS ---
    function openModal(modal) {
        if (!modal) return;
        modal.classList.remove('hidden');
        refreshIcons();
    }

    function closeModal(modal) {
        if (!modal) return;
        modal.classList.add('hidden');
    }

    // --- BOOK CRUD WORKFLOWS ---
    function openCreateBookModal() {
        const form = document.getElementById('bookForm');
        if (form) form.reset();
        document.getElementById('editBookOriginalId').value = '';
        document.getElementById('formBookId').disabled = false;
        document.getElementById('bookModalTitle').textContent = 'Add New Book';
        document.getElementById('formBookTotalCopies').value = 1;
        document.getElementById('formBookAvailableCopies').value = 1;
        document.getElementById('formBookIssuedCopies').value = 0;
        openModal(bookFormModal);
    }

    async function openEditBookModal(bookId) {
        try {
            const res = await fetch(`/admin/api/crud/library_books/${encodeURIComponent(bookId)}`);
            if (!res.ok) throw new Error('Failed to fetch book');
            const data = await res.json();
            const b = data.item || {};

            document.getElementById('editBookOriginalId').value = b.id || bookId;
            const idInput = document.getElementById('formBookId');
            idInput.value = b.id || bookId;
            idInput.disabled = true; // Lock ID during update

            document.getElementById('bookModalTitle').textContent = 'Edit Book Record';
            document.getElementById('formBookTitle').value = b.title || '';
            document.getElementById('formBookAuthor').value = b.author || '';
            document.getElementById('formBookDepartment').value = b.department || 'Computer Engineering';
            document.getElementById('formBookSubject').value = b.subject || '';
            document.getElementById('formBookIsbn').value = b.isbn || '';
            document.getElementById('formBookShelf').value = b.shelf_location || '';
            document.getElementById('formBookStatus').value = b.status || 'Available';
            document.getElementById('formBookTotalCopies').value = b.total_copies ?? 1;
            document.getElementById('formBookAvailableCopies').value = b.available_copies ?? 1;
            document.getElementById('formBookIssuedCopies').value = b.issued_copies ?? 0;

            openModal(bookFormModal);
        } catch (err) {
            alert('Error loading book details: ' + err.message);
        }
    }

    async function openViewBookModal(bookId) {
        try {
            const res = await fetch(`/admin/api/crud/library_books/${encodeURIComponent(bookId)}`);
            if (!res.ok) throw new Error('Failed to fetch book');
            const data = await res.json();
            const b = data.item || {};

            document.getElementById('viewBookAccession').textContent = `ID: ${b.id || bookId}`;
            document.getElementById('viewBookTitle').textContent = b.title || 'Untitled';
            document.getElementById('viewBookAuthor').textContent = b.author || 'Unknown';
            document.getElementById('viewBookDepartment').textContent = b.department || 'General';
            document.getElementById('viewBookSubject').textContent = b.subject || '--';
            document.getElementById('viewBookIsbn').textContent = b.isbn || '--';
            document.getElementById('viewBookShelf').textContent = b.shelf_location || 'Main Stacks';

            const total = parseInt(b.total_copies ?? 1);
            const avail = parseInt(b.available_copies ?? total);
            const issued = parseInt(b.issued_copies ?? 0);

            document.getElementById('viewBookTotalCopies').textContent = total;
            document.getElementById('viewBookAvailableCopies').textContent = avail;
            document.getElementById('viewBookIssuedCopies').textContent = issued;

            const badgeContainer = document.getElementById('viewBookStatusBadge');
            if (badgeContainer) {
                if (avail > 0) {
                    badgeContainer.innerHTML = `<span class="badge-stock-avail">Available (${avail} in stock)</span>`;
                } else {
                    badgeContainer.innerHTML = `<span class="badge-stock-out">Out of Stock</span>`;
                }
            }

            const issueBtn = document.getElementById('viewBookIssueBtn');
            if (issueBtn) {
                if (avail > 0) {
                    issueBtn.classList.remove('hidden');
                    issueBtn.onclick = () => {
                        closeModal(viewBookModal);
                        openIssueBookModal({ id: b.id || bookId, title: b.title });
                    };
                } else {
                    issueBtn.classList.add('hidden');
                }
            }

            openModal(viewBookModal);
        } catch (err) {
            alert('Error viewing book: ' + err.message);
        }
    }

    function openDeleteBookModal(bookId) {
        const book = state.books.items.find(b => String(b.id || b._id) === String(bookId));
        const title = book ? (book.title || 'Book') : 'Book';
        document.getElementById('deleteBookTitle').textContent = title;
        document.getElementById('deleteBookId').textContent = bookId;

        const confirmBtn = document.getElementById('confirmDeleteBookBtn');
        confirmBtn.onclick = async () => {
            try {
                confirmBtn.disabled = true;
                const res = await fetch(`/admin/api/crud/library_books/${encodeURIComponent(bookId)}`, {
                    method: 'DELETE'
                });
                const data = await res.json();
                if (!res.ok || data.status !== 'success') {
                    throw new Error(data.message || 'Failed to delete book');
                }
                closeModal(deleteBookModal);
                loadBooks();
                loadStats();
            } catch (err) {
                alert('Deletion failed: ' + err.message);
            } finally {
                confirmBtn.disabled = false;
            }
        };

        openModal(deleteBookModal);
    }

    // --- ISSUE / RETURN WORKFLOWS ---
    function openIssueBookModal(preselectedBook = null, preselectedMember = null) {
        const form = document.getElementById('issueBookForm');
        if (form) form.reset();

        // Default Due Date: Today + 14 Days
        const d = new Date();
        d.setDate(d.getDate() + 14);
        const defaultDueStr = d.toISOString().split('T')[0];
        document.getElementById('issueDueDateInput').value = defaultDueStr;

        // Reset Book badge
        if (preselectedBook && preselectedBook.id) {
            document.getElementById('issueSelectedBookId').value = preselectedBook.id;
            document.getElementById('issueSelectedBookText').textContent = `${preselectedBook.title} (${preselectedBook.id})`;
            document.getElementById('issueSelectedBookBadge').classList.remove('hidden');
            document.getElementById('issueBookSearchInput').classList.add('hidden');
        } else {
            document.getElementById('issueSelectedBookId').value = '';
            document.getElementById('issueSelectedBookBadge').classList.add('hidden');
            document.getElementById('issueBookSearchInput').classList.remove('hidden');
        }

        // Reset Student badge
        if (preselectedMember && preselectedMember.enrollment) {
            document.getElementById('issueSelectedEnrollment').value = preselectedMember.enrollment;
            document.getElementById('issueSelectedStudentName').value = preselectedMember.name;
            document.getElementById('issueSelectedStudentText').textContent = `${preselectedMember.name} (${preselectedMember.enrollment})`;
            document.getElementById('issueSelectedStudentBadge').classList.remove('hidden');
            document.getElementById('issueStudentSearchInput').classList.add('hidden');
        } else {
            document.getElementById('issueSelectedEnrollment').value = '';
            document.getElementById('issueSelectedStudentName').value = '';
            document.getElementById('issueSelectedStudentBadge').classList.add('hidden');
            document.getElementById('issueStudentSearchInput').classList.remove('hidden');
        }

        openModal(issueBookModal);
    }

    function openReturnBookModal(issueId, bookTitle, studentName, dueDate) {
        document.getElementById('returnIssueId').value = issueId;
        document.getElementById('returnModalTxId').textContent = issueId;
        document.getElementById('returnModalBookTitle').textContent = bookTitle;
        document.getElementById('returnModalStudentName').textContent = studentName;
        document.getElementById('returnModalDueDate').textContent = dueDate ? dueDate.slice(0, 10) : '--';

        const todayStr = new Date().toISOString().split('T')[0];
        const overdueWarn = document.getElementById('returnOverdueWarning');
        if (dueDate && dueDate < todayStr) {
            overdueWarn.classList.remove('hidden');
        } else {
            overdueWarn.classList.add('hidden');
        }

        const confirmBtn = document.getElementById('confirmReturnBtn');
        confirmBtn.onclick = async () => {
            try {
                confirmBtn.disabled = true;
                const res = await fetch(`/admin/api/library/return/${encodeURIComponent(issueId)}`, {
                    method: 'POST'
                });
                const data = await res.json();
                if (!res.ok || data.status !== 'success') {
                    throw new Error(data.message || 'Failed to reconcile return');
                }
                closeModal(returnBookModal);
                loadIssues();
                loadBooks();
                loadStats();
            } catch (err) {
                alert('Return failed: ' + err.message);
            } finally {
                confirmBtn.disabled = false;
            }
        };

        openModal(returnBookModal);
    }

    // --- AUTOCOMPLETE: BOOK LOOKUP IN ISSUE MODAL ---
    let bookLookupTimeout = null;
    const bookSearchInput = document.getElementById('issueBookSearchInput');
    const bookDropdown = document.getElementById('issueBookDropdown');

    if (bookSearchInput && bookDropdown) {
        bookSearchInput.addEventListener('input', () => {
            clearTimeout(bookLookupTimeout);
            const q = bookSearchInput.value.trim();
            if (q.length < 2) {
                bookDropdown.classList.add('hidden');
                return;
            }
            bookLookupTimeout = setTimeout(async () => {
                try {
                    const res = await fetch(`/admin/api/library/books-lookup?q=${encodeURIComponent(q)}&available_only=true`);
                    const data = await res.json();
                    const books = data.books || [];
                    if (!books.length) {
                        bookDropdown.innerHTML = `<div class="p-3 text-xs text-[#8C95AD] text-center">No available books found matching "${escapeHtml(q)}"</div>`;
                    } else {
                        bookDropdown.innerHTML = books.map(b => `
                            <div class="autocomplete-item" data-book-id="${escapeHtml(b.id)}" data-title="${escapeHtml(b.title)}">
                                <div class="font-bold text-[#171D3A]">${escapeHtml(b.title)}</div>
                                <div class="text-[11px] text-[#8C95AD] flex justify-between">
                                    <span>${escapeHtml(b.author || '')}</span>
                                    <span class="font-mono text-indigo-600 font-bold">${escapeHtml(b.id)}</span>
                                </div>
                            </div>
                        `).join('');
                    }
                    bookDropdown.classList.remove('hidden');
                } catch (err) {
                    console.error('[Library] Autocomplete book error:', err);
                }
            }, 250);
        });

        bookDropdown.addEventListener('click', (e) => {
            const item = e.target.closest('.autocomplete-item');
            if (!item) return;
            const id = item.getAttribute('data-book-id');
            const title = item.getAttribute('data-title');

            document.getElementById('issueSelectedBookId').value = id;
            document.getElementById('issueSelectedBookText').textContent = `${title} (${id})`;
            document.getElementById('issueSelectedBookBadge').classList.remove('hidden');
            bookSearchInput.classList.add('hidden');
            bookDropdown.classList.add('hidden');
            refreshIcons();
        });

        document.getElementById('clearSelectedBookBtn')?.addEventListener('click', () => {
            document.getElementById('issueSelectedBookId').value = '';
            document.getElementById('issueSelectedBookBadge').classList.add('hidden');
            bookSearchInput.classList.remove('hidden');
            bookSearchInput.value = '';
            bookSearchInput.focus();
        });
    }

    // --- AUTOCOMPLETE: STUDENT LOOKUP IN ISSUE MODAL ---
    let studentLookupTimeout = null;
    const studentSearchInput = document.getElementById('issueStudentSearchInput');
    const studentDropdown = document.getElementById('issueStudentDropdown');

    if (studentSearchInput && studentDropdown) {
        studentSearchInput.addEventListener('input', () => {
            clearTimeout(studentLookupTimeout);
            const q = studentSearchInput.value.trim();
            if (q.length < 2) {
                studentDropdown.classList.add('hidden');
                return;
            }
            studentLookupTimeout = setTimeout(async () => {
                try {
                    const res = await fetch(`/admin/api/library/members?q=${encodeURIComponent(q)}`);
                    const data = await res.json();
                    const members = data.members || [];
                    if (!members.length) {
                        studentDropdown.innerHTML = `<div class="p-3 text-xs text-[#8C95AD] text-center">No student found matching "${escapeHtml(q)}"</div>`;
                    } else {
                        studentDropdown.innerHTML = members.map(m => `
                            <div class="autocomplete-item" data-enroll="${escapeHtml(m.enrollment_no)}" data-name="${escapeHtml(m.name)}">
                                <div class="font-bold text-[#171D3A]">${escapeHtml(m.name)}</div>
                                <div class="text-[11px] text-[#8C95AD] flex justify-between">
                                    <span>${escapeHtml(m.department || 'Student')}</span>
                                    <span class="font-mono text-purple-600 font-bold">${escapeHtml(m.enrollment_no)}</span>
                                </div>
                            </div>
                        `).join('');
                    }
                    studentDropdown.classList.remove('hidden');
                } catch (err) {
                    console.error('[Library] Autocomplete student error:', err);
                }
            }, 250);
        });

        studentDropdown.addEventListener('click', (e) => {
            const item = e.target.closest('.autocomplete-item');
            if (!item) return;
            const enroll = item.getAttribute('data-enroll');
            const name = item.getAttribute('data-name');

            document.getElementById('issueSelectedEnrollment').value = enroll;
            document.getElementById('issueSelectedStudentName').value = name;
            document.getElementById('issueSelectedStudentText').textContent = `${name} (${enroll})`;
            document.getElementById('issueSelectedStudentBadge').classList.remove('hidden');
            studentSearchInput.classList.add('hidden');
            studentDropdown.classList.add('hidden');
            refreshIcons();
        });

        document.getElementById('clearSelectedStudentBtn')?.addEventListener('click', () => {
            document.getElementById('issueSelectedEnrollment').value = '';
            document.getElementById('issueSelectedStudentName').value = '';
            document.getElementById('issueSelectedStudentBadge').classList.add('hidden');
            studentSearchInput.classList.remove('hidden');
            studentSearchInput.value = '';
            studentSearchInput.focus();
        });
    }

    // Close autocomplete on click outside
    document.addEventListener('click', (e) => {
        if (bookDropdown && !bookDropdown.contains(e.target) && e.target !== bookSearchInput) {
            bookDropdown.classList.add('hidden');
        }
        if (studentDropdown && !studentDropdown.contains(e.target) && e.target !== studentSearchInput) {
            studentDropdown.classList.add('hidden');
        }
    });

    // --- FORM SUBMIT: BOOK CREATE / UPDATE ---
    const bookForm = document.getElementById('bookForm');
    if (bookForm) {
        bookForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const editId = document.getElementById('editBookOriginalId').value.trim();
            const isEdit = Boolean(editId);

            const payload = {
                id: document.getElementById('formBookId').value.trim(),
                title: document.getElementById('formBookTitle').value.trim(),
                author: document.getElementById('formBookAuthor').value.trim(),
                department: document.getElementById('formBookDepartment').value.trim(),
                subject: document.getElementById('formBookSubject').value.trim(),
                isbn: document.getElementById('formBookIsbn').value.trim(),
                shelf_location: document.getElementById('formBookShelf').value.trim(),
                status: document.getElementById('formBookStatus').value.trim(),
                total_copies: parseInt(document.getElementById('formBookTotalCopies').value) || 1,
                available_copies: parseInt(document.getElementById('formBookAvailableCopies').value) || 1,
                issued_copies: parseInt(document.getElementById('formBookIssuedCopies').value) || 0
            };

            const saveBtn = document.getElementById('saveBookBtn');
            try {
                saveBtn.disabled = true;
                const url = isEdit
                    ? `/admin/api/crud/library_books/${encodeURIComponent(editId)}`
                    : `/admin/api/crud/library_books`;
                const method = isEdit ? 'PUT' : 'POST';

                const res = await fetch(url, {
                    method: method,
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
                const data = await res.json();

                if (!res.ok || data.status !== 'success') {
                    throw new Error(data.message || 'Failed to save book');
                }

                closeModal(bookFormModal);
                loadBooks();
                loadStats();
            } catch (err) {
                alert('Save failed: ' + err.message);
            } finally {
                saveBtn.disabled = false;
            }
        });
    }

    // --- FORM SUBMIT: ISSUE BOOK ---
    const issueForm = document.getElementById('issueBookForm');
    if (issueForm) {
        issueForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const bookId = document.getElementById('issueSelectedBookId').value.trim();
            const studentId = document.getElementById('issueSelectedEnrollment').value.trim();
            const studentName = document.getElementById('issueSelectedStudentName').value.trim();
            const dueDate = document.getElementById('issueDueDateInput').value.trim();
            const notes = document.getElementById('issueNotesInput').value.trim();

            if (!bookId) {
                alert('Please select a book to issue.');
                return;
            }
            if (!studentId) {
                alert('Please select a registered student member.');
                return;
            }

            const confirmBtn = document.getElementById('confirmIssueBtn');
            try {
                confirmBtn.disabled = true;
                const res = await fetch('/admin/api/library/issue', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        book_id: bookId,
                        enrollment_no: studentId,
                        student_name: studentName,
                        due_date: dueDate,
                        notes: notes
                    })
                });
                const data = await res.json();
                if (!res.ok || data.status !== 'success') {
                    throw new Error(data.message || 'Failed to issue book');
                }

                closeModal(issueBookModal);
                switchTab('issues');
                loadIssues();
                loadBooks();
                loadStats();
            } catch (err) {
                alert('Issue failed: ' + err.message);
            } finally {
                confirmBtn.disabled = false;
            }
        });
    }

    // --- EVENT BINDINGS ---
    function bindEvents() {
        // Tab switching buttons
        tabBooksBtn?.addEventListener('click', () => switchTab('books'));
        tabIssuesBtn?.addEventListener('click', () => switchTab('issues'));
        tabMembersBtn?.addEventListener('click', () => switchTab('members'));

        // Modal triggers
        document.getElementById('openCreateBookModalBtn')?.addEventListener('click', openCreateBookModal);
        document.getElementById('openIssueModalBtn')?.addEventListener('click', () => openIssueBookModal());

        // Close modal buttons
        document.querySelectorAll('.close-modal-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                document.querySelectorAll('.library-modal-backdrop').forEach(m => m.classList.add('hidden'));
            });
        });

        // Books Filter & Search
        let bookSearchDebounce = null;
        document.getElementById('bookSearchInput')?.addEventListener('input', (e) => {
            clearTimeout(bookSearchDebounce);
            bookSearchDebounce = setTimeout(() => {
                state.books.search = e.target.value.trim();
                state.books.page = 1;
                loadBooks();
            }, 300);
        });

        document.getElementById('bookDepartmentFilter')?.addEventListener('change', (e) => {
            state.books.department = e.target.value;
            state.books.page = 1;
            loadBooks();
        });

        document.getElementById('bookAvailabilityFilter')?.addEventListener('change', (e) => {
            state.books.availability = e.target.value;
            state.books.page = 1;
            loadBooks();
        });

        document.getElementById('bookPerPageSelect')?.addEventListener('change', (e) => {
            state.books.limit = parseInt(e.target.value) || 20;
            state.books.page = 1;
            loadBooks();
        });

        document.getElementById('resetBookFiltersBtn')?.addEventListener('click', () => {
            const sInput = document.getElementById('bookSearchInput');
            const dSelect = document.getElementById('bookDepartmentFilter');
            const aSelect = document.getElementById('bookAvailabilityFilter');
            if (sInput) sInput.value = '';
            if (dSelect) dSelect.value = '';
            if (aSelect) aSelect.value = '';
            state.books.search = '';
            state.books.department = '';
            state.books.availability = '';
            state.books.page = 1;
            loadBooks();
        });

        document.getElementById('refreshBooksBtn')?.addEventListener('click', () => {
            loadBooks();
            loadStats();
        });

        // Books Table Delegated Action Clicks
        document.getElementById('booksTableBody')?.addEventListener('click', (e) => {
            const viewBtn = e.target.closest('.view-book-btn');
            if (viewBtn) {
                openViewBookModal(viewBtn.getAttribute('data-book-id'));
                return;
            }
            const editBtn = e.target.closest('.edit-book-btn');
            if (editBtn) {
                openEditBookModal(editBtn.getAttribute('data-book-id'));
                return;
            }
            const issueBtn = e.target.closest('.issue-book-row-btn');
            if (issueBtn) {
                const bookId = issueBtn.getAttribute('data-book-id');
                const book = state.books.items.find(b => String(b.id || b._id) === String(bookId));
                openIssueBookModal({ id: bookId, title: book ? book.title : 'Book' });
                return;
            }
            const delBtn = e.target.closest('.delete-book-btn');
            if (delBtn) {
                openDeleteBookModal(delBtn.getAttribute('data-book-id'));
                return;
            }
        });

        // Books Pagination delegated clicks
        document.getElementById('booksPaginationControls')?.addEventListener('click', (e) => {
            const btn = e.target.closest('.page-ctrl-btn');
            if (!btn || btn.disabled) return;
            const p = parseInt(btn.getAttribute('data-page'));
            if (p && p !== state.books.page && p >= 1 && p <= state.books.pages) {
                state.books.page = p;
                loadBooks();
            }
        });

        // Issues Filter & Search
        let issueSearchDebounce = null;
        document.getElementById('issueSearchInput')?.addEventListener('input', (e) => {
            clearTimeout(issueSearchDebounce);
            issueSearchDebounce = setTimeout(() => {
                state.issues.search = e.target.value.trim();
                state.issues.page = 1;
                loadIssues();
            }, 300);
        });

        document.getElementById('issueStatusFilter')?.addEventListener('change', (e) => {
            state.issues.status = e.target.value;
            state.issues.page = 1;
            loadIssues();
        });

        document.getElementById('issuePerPageSelect')?.addEventListener('change', (e) => {
            state.issues.limit = parseInt(e.target.value) || 20;
            state.issues.page = 1;
            loadIssues();
        });

        document.getElementById('refreshIssuesBtn')?.addEventListener('click', () => {
            loadIssues();
            loadStats();
        });

        // Issues Table Delegated Actions
        document.getElementById('issuesTableBody')?.addEventListener('click', (e) => {
            const retBtn = e.target.closest('.return-issue-btn');
            if (retBtn) {
                const issueId = retBtn.getAttribute('data-issue-id');
                const bookTitle = retBtn.getAttribute('data-book');
                const studentName = retBtn.getAttribute('data-student');
                const dueDate = retBtn.getAttribute('data-due');
                openReturnBookModal(issueId, bookTitle, studentName, dueDate);
            }
        });

        // Issues Pagination delegated clicks
        document.getElementById('issuesPaginationControls')?.addEventListener('click', (e) => {
            const btn = e.target.closest('.page-ctrl-btn');
            if (!btn || btn.disabled) return;
            const p = parseInt(btn.getAttribute('data-issue-page'));
            if (p && p !== state.issues.page && p >= 1 && p <= state.issues.pages) {
                state.issues.page = p;
                loadIssues();
            }
        });

        // Members Search
        let memberSearchDebounce = null;
        document.getElementById('memberSearchInput')?.addEventListener('input', (e) => {
            clearTimeout(memberSearchDebounce);
            memberSearchDebounce = setTimeout(() => {
                state.members.search = e.target.value.trim();
                loadMembers();
            }, 300);
        });

        document.getElementById('refreshMembersBtn')?.addEventListener('click', loadMembers);

        // Members Table Delegated Action
        document.getElementById('membersTableBody')?.addEventListener('click', (e) => {
            const qBtn = e.target.closest('.quick-issue-member-btn');
            if (qBtn) {
                const enroll = qBtn.getAttribute('data-enroll');
                const name = qBtn.getAttribute('data-name');
                openIssueBookModal(null, { enrollment: enroll, name: name });
            }
        });
    }

    // --- UTILITIES ---
    function refreshIcons() {
        if (window.lucide && typeof window.lucide.createIcons === 'function') {
            window.lucide.createIcons();
        }
    }

    function escapeHtml(str) {
        if (!str && str !== 0) return '';
        return String(str)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;');
    }

    // Start Controller
    init();
});
