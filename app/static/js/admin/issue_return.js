/**
 * SVIT Admin - Page 22: Issue / Return Circulation Desk Controller
 * Tab 1: Issue Book (Real book catalog selection, Member card, 14-day due date calculator)
 * Tab 2: Return Book (Barcode lookup, overdue fine calculator)
 * Tab 3: Active Loans & Overdue Tracker (Renew loan, Process Return)
 */

(function() {
    'use strict';

    const state = {
        activeTab: 'issue',
        loans: [],
        books: []
    };

    document.addEventListener('DOMContentLoaded', function() {
        bindEvents();
        setupDefaultDueDate();
        loadBooksCatalog();
        loadLoans();
        renderTab();
    });

    function bindEvents() {
        const tabs = document.querySelectorAll('.circ-nav-tab');
        tabs.forEach(tab => {
            tab.addEventListener('click', () => {
                tabs.forEach(t => t.classList.remove('active'));
                tab.classList.add('active');
                state.activeTab = tab.getAttribute('data-tab');
                renderTab();
            });
        });

        const issueForm = document.getElementById('issueBookForm');
        if (issueForm) issueForm.addEventListener('submit', handleIssueBook);

        const returnLookupBtn = document.getElementById('returnLookupBtn');
        if (returnLookupBtn) returnLookupBtn.addEventListener('click', handleReturnLookup);

        const returnForm = document.getElementById('returnBookForm');
        if (returnForm) returnForm.addEventListener('submit', handleProcessReturn);
    }

    function setupDefaultDueDate() {
        const dueDateInput = document.getElementById('issueDueDate');
        if (dueDateInput) {
            const d = new Date();
            d.setDate(d.getDate() + 14); // 14 days standard loan
            dueDateInput.value = d.toISOString().split('T')[0];
        }
    }

    async function loadBooksCatalog() {
        const select = document.getElementById('issueBookSelect');
        if (!select) return;

        try {
            const res = await fetch('/admin/api/crud/library_books?limit=1000');
            const data = await res.json();
            if (data.status === 'success' && data.items && data.items.length > 0) {
                state.books = data.items;
                select.innerHTML = data.items.map(b => {
                    const title = b.book_title || b.title || 'Book';
                    const isbn = b.isbn || b.book_id || '';
                    const shelf = b.shelf || b.shelf_location || 'Main';
                    const avail = b.available_copies !== undefined ? b.available_copies : 1;
                    return `<option value="${title}" data-book-id="${b.id || b.book_id}" ${avail <= 0 ? 'disabled' : ''}>
                        ${title} — ISBN: ${isbn} (${shelf}) ${avail <= 0 ? '[OUT OF STOCK]' : ''}
                    </option>`;
                }).join('');
            }
        } catch (err) {
            console.error('Error loading book catalog:', err);
        }
    }

    async function loadLoans() {
        const tbody = document.getElementById('activeLoansTableBody');
        if (tbody) {
            tbody.innerHTML = `<tr><td colspan="7" class="text-center py-6 text-gray-400 text-xs">Loading active circulation records...</td></tr>`;
        }

        try {
            const res = await fetch('/admin/api/crud/library_issue_return?limit=500');
            const data = await res.json();
            if (data.status === 'success') {
                state.loans = data.items || [];
                renderLoansTable();
            } else {
                if (tbody) tbody.innerHTML = `<tr><td colspan="7" class="text-center py-6 text-red-400 text-xs">${data.message}</td></tr>`;
            }
        } catch (err) {
            if (tbody) tbody.innerHTML = `<tr><td colspan="7" class="text-center py-6 text-red-400 text-xs">${err.message}</td></tr>`;
        }
        lucide.createIcons();
    }

    function renderTab() {
        document.getElementById('tabIssueContent').classList.add('hidden');
        document.getElementById('tabReturnContent').classList.add('hidden');
        document.getElementById('tabLoansContent').classList.add('hidden');

        if (state.activeTab === 'issue') {
            document.getElementById('tabIssueContent').classList.remove('hidden');
        } else if (state.activeTab === 'return') {
            document.getElementById('tabReturnContent').classList.remove('hidden');
        } else if (state.activeTab === 'loans') {
            document.getElementById('tabLoansContent').classList.remove('hidden');
            renderLoansTable();
        }
        lucide.createIcons();
    }

    async function handleIssueBook(e) {
        e.preventDefault();
        const bookSelect = document.getElementById('issueBookSelect');
        const bookTitle = bookSelect.value;
        const selectedOpt = bookSelect.options[bookSelect.selectedIndex];
        const bookId = selectedOpt ? selectedOpt.getAttribute('data-book-id') : 'BK_001';
        const memberName = document.getElementById('issueMemberCardInput').value.trim();
        const dueDate = document.getElementById('issueDueDate').value;

        const payload = {
            transaction_id: `TXN-${Date.now().toString().slice(-6)}`,
            book_id: bookId || 'BK_001',
            book_title: bookTitle,
            member_id: memberName,
            member_name: memberName,
            issue_date: new Date().toISOString().split('T')[0],
            due_date: dueDate,
            return_date: '',
            fine_amount: 0,
            status: 'Issued'
        };

        try {
            const res = await fetch('/admin/api/crud/library_issue_return', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            const data = await res.json();
            if (res.ok && data.status === 'success') {
                showAdminToast(`Book issued successfully to ${memberName}! Due date: ${dueDate}`, 'success');
                document.getElementById('issueBookForm').reset();
                setupDefaultDueDate();
                loadLoans();
            } else {
                showAdminToast(data.message || 'Failed to issue book.', 'error');
            }
        } catch (err) {
            showAdminToast(err.message, 'error');
        }
    }

    function handleReturnLookup() {
        const cardNo = document.getElementById('returnCardInput').value.trim();
        const loan = state.loans.find(l => {
            const memId = (l.member_id || '').toLowerCase();
            const memName = (l.member_name || '').toLowerCase();
            const txnId = (l.transaction_id || l.id || '').toLowerCase();
            const query = cardNo.toLowerCase();
            return memId.includes(query) || memName.includes(query) || txnId.includes(query);
        });

        const resultBox = document.getElementById('returnResultBox');
        if (!loan) {
            showAdminToast('No active borrowed books found for this card number / member.', 'error');
            if (resultBox) resultBox.classList.add('hidden');
            return;
        }

        const today = new Date().toISOString().split('T')[0];
        const isOverdue = loan.due_date && loan.due_date < today;
        let fine = 0;
        if (isOverdue) {
            const diffDays = Math.ceil((new Date(today) - new Date(loan.due_date)) / (1000 * 60 * 60 * 24));
            fine = Math.max(0, diffDays * 5);
        }

        if (resultBox) {
            document.getElementById('returnBookTitle').innerText = loan.book_title || loan.book || 'Book';
            document.getElementById('returnBorrower').innerText = loan.member_name || loan.member_id || 'Member';
            document.getElementById('returnDueDate').innerText = loan.due_date || '-';
            document.getElementById('returnFineAmount').innerText = fine > 0 ? `₹ ${fine} (Overdue fine @ ₹5/day)` : '₹ 0.00 (On Time)';
            document.getElementById('activeReturnLoanId').value = loan.id || loan.transaction_id;
            resultBox.classList.remove('hidden');
        }
        lucide.createIcons();
    }

    async function handleProcessReturn(e) {
        e.preventDefault();
        const loanId = document.getElementById('activeReturnLoanId').value;
        if (!loanId) return;

        try {
            const res = await fetch(`/admin/api/crud/library_issue_return/${loanId}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    status: 'Returned',
                    return_date: new Date().toISOString().split('T')[0]
                })
            });
            const data = await res.json();
            if (res.ok && data.status === 'success') {
                showAdminToast('Book returned successfully and inventory stock replenished!', 'success');
                document.getElementById('returnResultBox').classList.add('hidden');
                document.getElementById('returnBookForm').reset();
                document.getElementById('returnCardInput').value = '';
                loadLoans();
            } else {
                showAdminToast(data.message || 'Error processing return.', 'error');
            }
        } catch (err) {
            showAdminToast(err.message, 'error');
        }
    }

    function renderLoansTable() {
        const tbody = document.getElementById('activeLoansTableBody');
        if (!tbody) return;

        if (state.loans.length === 0) {
            tbody.innerHTML = `<tr><td colspan="7" class="text-center py-10 text-gray-400 text-xs">No active books currently on loan.</td></tr>`;
            return;
        }

        const today = new Date().toISOString().split('T')[0];

        tbody.innerHTML = state.loans.map(l => {
            const id = l.transaction_id || l.id || '-';
            const book = l.book_title || l.book || 'Book';
            const borrower = l.member_name || l.borrower || 'Member';
            const cardNo = l.member_id || l.card_no || '-';
            const issueDate = l.issue_date || '-';
            const dueDate = l.due_date || '-';
            const isReturned = l.status === 'Returned';
            const isOverdue = !isReturned && dueDate && dueDate < today;
            let daysOverdue = 0;
            let fine = l.fine_amount || 0;
            if (isOverdue) {
                daysOverdue = Math.ceil((new Date(today) - new Date(dueDate)) / (1000 * 60 * 60 * 24));
                fine = daysOverdue * 5;
            }

            return `
                <tr>
                    <td>
                        <span class="font-mono text-teal-400 font-bold text-xs">${id}</span>
                    </td>
                    <td class="font-bold text-white text-xs">${book}</td>
                    <td>
                        <span class="text-gray-200 font-medium text-xs">${borrower}</span>
                        <span class="text-[10px] text-gray-500 font-mono block">${cardNo}</span>
                    </td>
                    <td class="text-gray-400 text-xs">${issueDate}</td>
                    <td class="text-gray-300 text-xs">${dueDate}</td>
                    <td>
                        ${isReturned ? 
                            '<span class="badge-on-time"><i data-lucide="check-circle" class="w-3 h-3 d-inline mr-1"></i>Returned</span>' :
                            (isOverdue ? 
                                `<span class="badge-overdue"><i data-lucide="alert-triangle" class="w-3 h-3 d-inline mr-1"></i>${daysOverdue} Days Overdue (₹${fine})</span>` : 
                                '<span class="badge-on-time"><i data-lucide="check" class="w-3 h-3 d-inline mr-1"></i>Active Loan</span>')}
                    </td>
                    <td class="text-end">
                        ${!isReturned ? `
                            <button class="px-2.5 py-1 rounded-lg bg-teal-600 hover:bg-teal-500 text-white text-xs font-semibold" onclick="window.quickReturnLoan('${id}')">
                                Return
                            </button>
                            <button class="px-2.5 py-1 rounded-lg bg-[#0F172A] border border-[#1F2937] text-gray-300 hover:text-white text-xs" onclick="window.renewLoan('${id}')">
                                Renew
                            </button>
                        ` : '<span class="text-gray-600 text-xs">Completed</span>'}
                    </td>
                </tr>
            `;
        }).join('');

        lucide.createIcons();
    }

    window.quickReturnLoan = async function(id) {
        try {
            const res = await fetch(`/admin/api/crud/library_issue_return/${id}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    status: 'Returned',
                    return_date: new Date().toISOString().split('T')[0]
                })
            });
            const data = await res.json();
            if (res.ok && data.status === 'success') {
                showAdminToast('Book returned and stock restored.', 'success');
                loadLoans();
            } else {
                showAdminToast(data.message || 'Return failed.', 'error');
            }
        } catch (err) {
            showAdminToast(err.message, 'error');
        }
    };

    window.renewLoan = async function(id) {
        const loan = state.loans.find(l => (l.transaction_id || l.id) === id);
        if (loan) {
            const currentDue = loan.due_date || new Date().toISOString().split('T')[0];
            const d = new Date(currentDue);
            d.setDate(d.getDate() + 14);
            const newDue = d.toISOString().split('T')[0];

            try {
                const res = await fetch(`/admin/api/crud/library_issue_return/${id}`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        due_date: newDue,
                        status: 'Issued'
                    })
                });
                const data = await res.json();
                if (res.ok && data.status === 'success') {
                    showAdminToast(`Loan renewed for 14 days! New Due Date: ${newDue}`, 'success');
                    loadLoans();
                } else {
                    showAdminToast(data.message || 'Renewal failed.', 'error');
                }
            } catch (err) {
                showAdminToast(err.message, 'error');
            }
        }
    };
})();
